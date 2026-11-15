from django.db.models import Q
from graphql import GraphQLError

from app_utils.constants import STORE_CHOICES
from app_utils.database import get_model_object, SaveContextManager
from app_utils.helpers import is_valid_uuid
from apps.budgets.owner import BudgetOwner
from apps.budgets.services import validate_item_usable, validate_transaction_budget
from apps.properties.models import Property
from apps.stores.models import Store


class ValidateStore:
	def __init__(self, **store_body: Store):
		self.store = store_body

	def validate_and_save_store(self, store: Store):
		"""
    Args:
      store: The store instance

    Returns: new updated store after it has been saved into database
    """
		property_id = self.store.pop('property_id', None)
		item_id = self.store.pop('item_id', None)
		budget_id = self.store.pop('budget_id', None)
		notes = self.store.pop('notes', None)
		self.store.pop('is_recurring', None)
		store_id = self.store.get('id', None)
		amount = self.store.get('amount', "")
		if amount <= 0:
			raise GraphQLError(f"Invalid amount")
		if (item_id or budget_id) and self.store.get('is_inflow'):
			raise GraphQLError("An income can't be linked to a budget or budget item")
		if notes is not None:
			store.notes = notes.strip()
		for key, value in self.store.items():
			if isinstance(value, str) and value.strip() == '':
				raise GraphQLError(f"The {key} field can't be empty")
			if key == 'id':
				continue
			setattr(store, key, value)

		store_type = [item for item in STORE_CHOICES if item[0] == self.store['record_type']]
		if not store_type:
			raise GraphQLError('Invalid store type')

		filters = Q(
			action_date=self.store['action_date'],
			description=self.store['description'],
			user=store.user
		)
		if store_id:
			filters = (~Q(id=store_id) & filters)
			if store.property and not property_id:
				store.property = None
			if store.item_id and not item_id:
				store.item = None
			if store.budget_id and not budget_id:
				store.budget = None

		has_saved = Store.objects.filter(filters).first()
		if has_saved:
			raise GraphQLError('The record has already been recorded')
		if property_id:
			prop = get_model_object(Property, 'id', property_id)
			if prop.owner != store.user:
				raise GraphQLError('Invalid asset')
			store.property = prop
		self.link_budget(store, budget_id, item_id)
		with SaveContextManager(store, model=Store):
			return store

	@staticmethod
	def link_budget(store: Store, budget_id, item_id):
		"""Tag the expense with an item and, optionally, the budget it counts toward.
		Budgets may overlap, so the budget is never guessed from the date."""
		for value, label in ((item_id, 'budget item'), (budget_id, 'budget')):
			if value and not is_valid_uuid(str(value)):
				raise GraphQLError(f'Invalid {label}')
		owner = BudgetOwner(user=store.user)
		unchanged = (
			str(budget_id or '') == str(store.budget_id or '')
			and str(item_id or '') == str(store.item_id or '')
		)
		# Re-saving an existing link is allowed even if the budget closed or the item was
		# archived since, as long as the date still fits the budget.
		if budget_id:
			date_moved_outside = unchanged and not (
				store.budget.start_date <= store.action_date <= store.budget.end_date)
			if not unchanged or date_moved_outside:
				validate_transaction_budget(owner, budget_id, item_id, store.action_date)
		elif item_id and str(item_id) != str(store.item_id or ''):
			validate_item_usable(owner, item_id)
		store.item_id = item_id or None
		store.budget_id = budget_id or None
