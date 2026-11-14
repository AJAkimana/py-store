"""
Budget rules and spending calculations.

Spending is never stored: a transaction counts toward a budget when it is an
expense of the budget's owner, tagged with an item, and dated within the
budget's period.
"""
from datetime import date
from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Cast, Coalesce
from graphql import GraphQLError

from apps.budgets.models import Budget, BudgetAllocation, BudgetStatus
from apps.budgets.owner import BudgetOwner
from apps.stores.models import Store

MONEY = DecimalField(max_digits=14, decimal_places=2)
ZERO = Value(Decimal('0'), output_field=MONEY)


def owner_of(budget: Budget) -> BudgetOwner:
	if budget.user_id:
		return BudgetOwner(user=budget.user)
	return BudgetOwner(household=budget.household)


def budget_expenses(budget: Budget):
	"""All expenses of the budget's owner within its period (tagged or not)."""
	return Store.objects.filter(
		owner_of(budget).store_filter(),
		is_inflow=False,
		action_date__range=(budget.start_date, budget.end_date),
	)


def allocations_with_spending(budget: Budget):
	"""The budget's allocations annotated with `spent` and `remaining`."""
	spent = (
		budget_expenses(budget)
		.filter(item=OuterRef('item'))
		.values('item')
		.annotate(total=Sum('amount'))
		.values('total')
	)
	spent_value = Coalesce(Cast(Subquery(spent), MONEY), ZERO)
	return (
		BudgetAllocation.objects.filter(budget=budget)
		.select_related('item')
		.annotate(spent=spent_value)
		.annotate(remaining=Cast('amount', MONEY) - spent_value)
	)


def budget_totals(budget: Budget) -> dict:
	"""allocated / spent (on planned items) / unbudgeted (everything else) for a budget."""
	allocated = budget.allocations.aggregate(total=Sum('amount'))['total'] or Decimal('0')
	planned_items = budget.allocations.values('item_id')
	expenses = budget_expenses(budget)
	spent = expenses.filter(item_id__in=planned_items).aggregate(total=Sum('amount'))['total'] or 0
	unbudgeted = expenses.exclude(item_id__in=planned_items).aggregate(
		total=Sum('amount'))['total'] or 0
	spent, unbudgeted = Decimal(str(spent)), Decimal(str(unbudgeted))
	return {
		'allocated': allocated,
		'spent': spent,
		'remaining': allocated - spent,
		'unbudgeted': unbudgeted,
	}


def active_budget(owner: BudgetOwner, on: date = None):
	"""The owner's active budget covering a date (today by default)."""
	on = on or date.today()
	return Budget.objects.filter(
		owner.filter(), status=BudgetStatus.ACTIVE, start_date__lte=on, end_date__gte=on,
	).first()


def overlapping_active_budget(budget: Budget):
	"""Another active budget of the same owner whose period overlaps this one."""
	return (
		Budget.objects.filter(
			owner_of(budget).filter(),
			status=BudgetStatus.ACTIVE,
			start_date__lte=budget.end_date,
			end_date__gte=budget.start_date,
		)
		.exclude(id=budget.id)
		.first()
	)


ALLOWED_TRANSITIONS = {
	BudgetStatus.DRAFT: {BudgetStatus.ACTIVE},
	BudgetStatus.ACTIVE: {BudgetStatus.DRAFT, BudgetStatus.CLOSED},
	BudgetStatus.CLOSED: {BudgetStatus.ACTIVE},
}


def validate_budget(budget: Budget):
	"""Rules checked whenever a budget is saved."""
	if not budget.name or not budget.name.strip():
		raise GraphQLError("The budget name can't be empty")
	if budget.end_date < budget.start_date:
		raise GraphQLError('The end date must be on or after the start date')
	if budget.status == BudgetStatus.ACTIVE:
		other = overlapping_active_budget(budget)
		if other:
			raise GraphQLError(
				f"This period overlaps the active budget '{other.name}' "
				f"({other.start_date} → {other.end_date})")
	duplicate = Budget.objects.filter(
		owner_of(budget).filter(), name__iexact=budget.name.strip()).exclude(id=budget.id)
	if duplicate.exists():
		raise GraphQLError(f"A budget named '{budget.name.strip()}' already exists")


def change_status(budget: Budget, new_status: str) -> Budget:
	"""Move a budget through draft → active → closed, enforcing the rules."""
	if new_status not in BudgetStatus.values:
		raise GraphQLError('Invalid budget status')
	if new_status == budget.status:
		return budget
	if new_status not in ALLOWED_TRANSITIONS[BudgetStatus(budget.status)]:
		raise GraphQLError(f"A {budget.status} budget can't become {new_status}")
	if new_status == BudgetStatus.ACTIVE and not budget.allocations.exists():
		raise GraphQLError('Add at least one item before activating the budget')
	budget.status = new_status
	validate_budget(budget)
	budget.save()
	return budget


def ensure_editable(budget: Budget):
	if budget.status == BudgetStatus.CLOSED:
		raise GraphQLError("A closed budget can't be changed; reopen it first")


def validate_item_usable(owner: BudgetOwner, item_id) -> None:
	"""Raise unless the item is one the owner may use (own or enabled system item)."""
	if not owner.usable_items().filter(id=item_id).exists():
		raise GraphQLError('Invalid budget item')


def set_allocations(budget: Budget, allocations) -> None:
	"""Replace a budget's allocations with `allocations` = [(item_id, Decimal amount)].

	Items already allocated keep their row (amount updated); others are added or removed.
	"""
	ensure_editable(budget)
	owner = owner_of(budget)
	wanted = {}
	for item_id, amount in allocations:
		key = str(item_id)
		if key in wanted:
			raise GraphQLError('Each item can only appear once in a budget')
		wanted[key] = amount
	existing = {str(a.item_id): a for a in BudgetAllocation.objects.filter(budget=budget)}
	new_ids = set(wanted) - set(existing)
	if new_ids:
		usable = {str(i) for i in owner.usable_items().filter(id__in=new_ids).values_list('id', flat=True)}
		if usable != new_ids:
			raise GraphQLError('Invalid budget item')
	if budget.status == BudgetStatus.ACTIVE and not wanted:
		raise GraphQLError("An active budget needs at least one item")

	BudgetAllocation.objects.filter(budget=budget).exclude(
		item_id__in=list(wanted)).hard_delete()
	for key, amount in wanted.items():
		if key in existing:
			allocation = existing[key]
			if allocation.amount != amount:
				allocation.amount = amount
				allocation.save(update_fields=['amount'])
		else:
			BudgetAllocation.objects.create(budget=budget, item_id=key, amount=amount)
