"""
Budget rules and spending calculations.

Budgets of one owner may overlap (eg: a monthly budget next to a house-building budget),
so a transaction says which budget it belongs to: `Store.budget` plus `Store.item`.
Spending is never stored; it is the sum of the expenses linked to a budget.
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
	"""Expenses linked to the budget."""
	return Store.objects.filter(budget=budget, is_inflow=False)


def _total(queryset) -> Decimal:
	return Decimal(str(queryset.aggregate(total=Sum('amount'))['total'] or 0))


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
	"""allocated / spent / remaining for a budget, plus `unbudgeted`: the owner's expenses
	within the period that aren't linked to any budget."""
	allocated = budget.allocations.aggregate(total=Sum('amount'))['total'] or Decimal('0')
	spent = _total(budget_expenses(budget))
	unbudgeted = _total(Store.objects.filter(
		owner_of(budget).store_filter(),
		is_inflow=False,
		budget__isnull=True,
		action_date__range=(budget.start_date, budget.end_date),
	))
	return {
		'allocated': allocated,
		'spent': spent,
		'remaining': allocated - spent,
		'unbudgeted': unbudgeted,
	}


def active_budgets(owner: BudgetOwner, on: date = None):
	"""The owner's active budgets covering a date (today by default); they may overlap."""
	on = on or date.today()
	return Budget.objects.filter(
		owner.filter(), status=BudgetStatus.ACTIVE, start_date__lte=on, end_date__gte=on,
	).order_by('end_date', 'name')


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
	duplicate = Budget.objects.filter(
		owner_of(budget).filter(), name__iexact=budget.name.strip()).exclude(id=budget.id)
	if duplicate.exists():
		raise GraphQLError(f"A budget named '{budget.name.strip()}' already exists")
	if budget.pk:
		outside = Store.objects.filter(budget=budget).exclude(
			action_date__range=(budget.start_date, budget.end_date)).count()
		if outside:
			raise GraphQLError(
				f'{outside} transaction(s) linked to this budget would fall outside the new '
				'period. Move or unlink them first.')


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
	if new_status == BudgetStatus.DRAFT and Store.objects.filter(budget=budget).exists():
		raise GraphQLError(
			"This budget already has transactions; close it instead of moving it back to draft")
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


def validate_transaction_budget(owner: BudgetOwner, budget_id, item_id, action_date) -> Budget:
	"""Check a transaction may be linked to a budget and one of its items."""
	budget = Budget.objects.filter(owner.filter(), id=budget_id).first()
	if budget is None:
		raise GraphQLError('Budget not found')
	if budget.status != BudgetStatus.ACTIVE:
		raise GraphQLError(f"'{budget.name}' is not active; only active budgets take transactions")
	if not budget.start_date <= action_date <= budget.end_date:
		raise GraphQLError(
			f"The date is outside '{budget.name}' ({budget.start_date} → {budget.end_date})")
	if not item_id:
		raise GraphQLError(f"Choose which item of '{budget.name}' this expense is for")
	if not budget.allocations.filter(item_id=item_id).exists():
		raise GraphQLError(f"That item isn't planned in '{budget.name}'")
	return budget


def set_allocations(budget: Budget, allocations) -> None:
	"""Replace a budget's allocations with `allocations` = [(item_id, Decimal amount)].

	Items already allocated keep their row (amount updated); others are added or removed.
	Items that already have transactions in this budget can't be removed.
	"""
	ensure_editable(budget)
	owner = owner_of(budget)
	wanted = {}
	for item_id, amount in allocations:
		key = str(item_id)
		if key in wanted:
			raise GraphQLError('Each item can only appear once in a budget')
		wanted[key] = amount
	existing = {str(a.item_id): a for a in BudgetAllocation.objects.filter(
		budget=budget).select_related('item')}
	new_ids = set(wanted) - set(existing)
	if new_ids:
		usable = {str(i) for i in owner.usable_items().filter(id__in=new_ids).values_list('id', flat=True)}
		if usable != new_ids:
			raise GraphQLError('Invalid budget item')
	if budget.status == BudgetStatus.ACTIVE and not wanted:
		raise GraphQLError("An active budget needs at least one item")
	removed = [existing[key] for key in set(existing) - set(wanted)]
	used = {str(i) for i in Store.objects.filter(
		budget=budget, item_id__in=[a.item_id for a in removed]).values_list('item_id', flat=True)}
	if used:
		names = ', '.join(sorted(existing[key].item.name for key in used))
		raise GraphQLError(f"{names} already have transactions in this budget and can't be removed")

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
