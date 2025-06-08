from datetime import date

import graphene
from django.db.models import Q
from graphql_jwt.decorators import login_required

from app_utils.helpers import get_budgets_filter, paginate_data, is_valid_uuid
from app_utils.model_types.store import BudgetPaginatorType, BudgetDetailType
from apps.budgeting.models import Budget, BudgetItem
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

		recurring_items = list(BudgetItem.objects.filter(is_recurring=True))
		budget_items.extend(recurring_items)

		return {
			"budget_items": budget_items
		}
