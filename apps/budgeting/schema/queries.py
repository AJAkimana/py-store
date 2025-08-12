from datetime import date

import graphene
from django.db.models import Q
from graphql_jwt.decorators import login_required

from app_utils.helpers import get_budgets_filter, paginate_data, is_valid_uuid
from app_utils.model_types.store import BudgetPaginatorType, BudgetDetailType, UserBudgetLineType, \
	DefaultBudgetLineType, BudgetLineType
from apps.budgeting.models import Budget, BudgetItem, DefaultBudgetLine, UserBudgetLine
from apps.household_members.helpers import get_member_filter
from apps.users.models import User


class BudgetingQuery(graphene.ObjectType):
	budgets = graphene.Field(
		BudgetPaginatorType,
		search_key=graphene.String(),
		search_start_date=graphene.String(),
		search_end_date=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int(),
		search_member=graphene.String()
	)
	current_budget = graphene.Field(BudgetDetailType, budget_id=graphene.String())
	default_budget_lines = graphene.List(DefaultBudgetLineType)
	user_budget_lines = graphene.List(UserBudgetLineType, active=graphene.Boolean())
	all_budget_lines = graphene.List(BudgetLineType, is_system_setup=graphene.Boolean())

	@login_required
	def resolve_budgets(self, info, search_member='', page_count=10, page_number=1, **kwargs):
		user = info.context.user
		search_filter = get_budgets_filter(**kwargs)
		if search_member == '':
			budgets = User.get_user_budgets(user, search_filter)
		else:
			search_filter &= get_member_filter(user, search_member)
			budgets = Budget.objects.filter(search_filter)

		return paginate_data(budgets, page_count, page_number)

	@login_required
	def resolve_current_budget(self, info, budget_id=None):
		user = info.context.user
		search_filter = Q(user=user)
		if budget_id is not None and is_valid_uuid(budget_id):
			search_filter &= Q(id=budget_id)
		else:
			today = date.today()
			search_filter &= Q(start_date__lte=today, end_date__gte=today, status='approved')

		budget = Budget.objects.filter(search_filter).first()
		recurring_items = []
		if budget is not None:
			recurring_items = budget.budget_items.filter(is_recurring=True)
			budget.budget_items.append(recurring_items)
			return budget

		return {
			"name": budget.name if budget else "Not set",
			"budget_items": recurring_items
		}

	@login_required
	def resolve_current_budget(self, info, budget_id=None):
		user = info.context.user
		search_filter = Q(user=user)
		if budget_id is not None and is_valid_uuid(budget_id):
			search_filter &= Q(id=budget_id)
		else:
			today = date.today()
			search_filter &= Q(start_date__lte=today, end_date__gte=today, status='approved')

		budget = Budget.objects.filter(search_filter).first()
		budget_items = []
		if budget is not None:
			budget_items = list(budget.budget_items.all())

		recurring_items = list(BudgetItem.objects.filter(is_recurring=True, user_id=user.id))
		budget_items.extend(recurring_items)

		return {
			"budget_items": budget_items
		}

	@login_required
	def resolve_default_budget_lines(self, info):
		return DefaultBudgetLine.objects.filter(active=True)

	@login_required
	def resolve_user_budget_lines(self, info, active=None):
		user = info.context.user
		filters = Q(user=user)
		if active is not None:
			filters &= Q(active=active)

		return UserBudgetLine.objects.filter(filters)

	@login_required
	def resolve_all_budget_lines(self, info, is_system_setup=False):
		user = info.context.user
		default_lines = DefaultBudgetLine.objects.filter(active=True)
		all_lines = []
		user_lines = UserBudgetLine.objects.none()
		is_setup = is_system_setup and user.is_superuser
		if is_setup:
			user_lines = UserBudgetLine.objects.filter(user=user)
		for line in default_lines:
			enabled = line.active
			if not is_setup:
				enabled = user_lines.filter(name=line.name).exists()
			all_lines.append(BudgetLineType(
				id=line.id,
				name=line.name,
				description=line.description,
				amount=0,
				is_system=True,
				enabled=enabled
			))

		if is_setup:
			return all_lines

		for line in user_lines:
			if not any(l.name == line.name for l in all_lines):
				all_lines.append(BudgetLineType(
					id=line.id,
					name=line.name,
					description=line.description,
					amount=line.amount,
					is_system=False,
					enabled=line.active
				))

		return all_lines
