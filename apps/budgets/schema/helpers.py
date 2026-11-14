from decimal import Decimal, InvalidOperation

from graphql import GraphQLError

from app_utils.helpers import is_valid_uuid
from apps.budgets.models import Budget, BudgetItem
from apps.budgets.owner import resolve_owner


def _require_uuid(value, label):
	if not value or not is_valid_uuid(str(value)):
		raise GraphQLError(f'{label} not found')


def get_owned_budget(user, budget_id, household_id=None) -> Budget:
	owner = resolve_owner(user, household_id)
	_require_uuid(budget_id, 'Budget')
	budget = Budget.objects.filter(owner.filter(), id=budget_id).first()
	if budget is None:
		raise GraphQLError('Budget not found')
	return budget


def get_editable_item(user, item_id, household_id=None) -> BudgetItem:
	"""An item the user may change: their own, or any system item when superuser."""
	_require_uuid(item_id, 'Budget item')
	item = BudgetItem.objects.filter(id=item_id).first()
	if item is None:
		raise GraphQLError('Budget item not found')
	if item.is_system:
		if not user.is_superuser:
			raise GraphQLError("System budget items can only be changed by an administrator")
		return item
	owner = resolve_owner(user, household_id)
	if not BudgetItem.objects.filter(owner.filter(), id=item.id).exists():
		raise GraphQLError('Budget item not found')
	return item


def to_money(value, label='amount') -> Decimal:
	try:
		amount = Decimal(str(value)).quantize(Decimal('0.01'))
	except (InvalidOperation, TypeError, ValueError):
		raise GraphQLError(f'Invalid {label}')
	if amount < 0:
		raise GraphQLError(f"The {label} can't be negative")
	return amount


def clean_text(value, label, required=True, max_length=None) -> str:
	text = (value or '').strip()
	if required and not text:
		raise GraphQLError(f"The {label} can't be empty")
	if max_length and len(text) > max_length:
		raise GraphQLError(f'The {label} must be at most {max_length} characters')
	return text
