from datetime import date

import graphene
from django.db.models import Q
from graphql_jwt.decorators import login_required, superuser_required

from app_utils.helpers import paginate_data
from apps.budgets.models import Budget, BudgetItem, BudgetStatus, ItemActivation
from apps.budgets.owner import resolve_owner
from apps.budgets.schema.helpers import get_owned_budget
from apps.budgets.schema.types import BudgetItemType, BudgetPaginatorType, BudgetType
from apps.budgets.services import active_budget


class BudgetQuery(graphene.ObjectType):
	budget_items = graphene.List(
		graphene.NonNull(BudgetItemType), required=True,
		household_id=graphene.ID(),
		include_disabled=graphene.Boolean(
			default_value=False,
			description='Settings view: also list archived own items and every system item, '
			'with `enabled` showing whether the owner switched it on.'),
		description='Items the owner can budget for and tag transactions with.',
	)
	system_budget_items = graphene.List(
		graphene.NonNull(BudgetItemType), required=True,
		description='Admin: every system item, including inactive ones.')
	budgets = graphene.Field(
		BudgetPaginatorType,
		household_id=graphene.ID(),
		search_key=graphene.String(),
		status=graphene.String(),
		date_from=graphene.Date(description='Budgets whose period overlaps date_from..date_to'),
		date_to=graphene.Date(),
		page_count=graphene.Int(default_value=10),
		page_number=graphene.Int(default_value=1),
	)
	budget = graphene.Field(BudgetType, id=graphene.ID(required=True), household_id=graphene.ID())
	active_budget = graphene.Field(
		BudgetType, household_id=graphene.ID(), date=graphene.Date(),
		description='The active budget covering a date (today by default), if any.')

	@login_required
	def resolve_budget_items(self, info, household_id=None, include_disabled=False):
		owner = resolve_owner(info.context.user, household_id)
		if not include_disabled:
			return list(owner.usable_items())

		own = list(BudgetItem.objects.filter(owner.filter()))
		enabled_ids = set(
			ItemActivation.objects.filter(owner.filter(), enabled=True).values_list('item_id', flat=True))
		system = list(BudgetItem.objects.filter(
			user__isnull=True, household__isnull=True, is_active=True))
		for item in system:
			item.enabled = item.id in enabled_ids
		return sorted(system + own, key=lambda i: i.name.lower())

	@superuser_required
	def resolve_system_budget_items(self, info):
		return BudgetItem.objects.filter(user__isnull=True, household__isnull=True)

	@login_required
	def resolve_budgets(
			self, info, household_id=None, search_key='', status='', date_from=None, date_to=None,
			page_count=10, page_number=1):
		owner = resolve_owner(info.context.user, household_id)
		filters = owner.filter()
		if search_key and search_key.strip():
			filters &= Q(name__icontains=search_key.strip()) | Q(
				description__icontains=search_key.strip())
		if status in BudgetStatus.values:
			filters &= Q(status=status)
		if date_from:
			filters &= Q(end_date__gte=date_from)
		if date_to:
			filters &= Q(start_date__lte=date_to)
		return paginate_data(Budget.objects.filter(filters), page_count, page_number)

	@login_required
	def resolve_budget(self, info, id, household_id=None):
		return get_owned_budget(info.context.user, id, household_id)

	@login_required
	def resolve_active_budget(self, info, household_id=None, date=None):
		owner = resolve_owner(info.context.user, household_id)
		return active_budget(owner, date or _today())


def _today():
	return date.today()
