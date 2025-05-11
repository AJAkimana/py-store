from django.db.models import Q
from graphql import GraphQLError

from app_utils.constants import STORE_CHOICES
from app_utils.database import get_model_object, SaveContextManager
from apps.budgeting.models import BudgetItem
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
		budget_item_id = self.store.pop('budget_item_id', None)
		store_id = self.store.get('id', None)
		amount = self.store.get('amount', "")
		if amount <= 0:
			raise GraphQLError(f"Invalid amount")
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
			if store.budget_item and not budget_item_id:
				store.budget_item = None

		has_saved = Store.objects.filter(filters).first()
		if has_saved:
			raise GraphQLError('The record has already been recorded')
		if property_id:
			store.property = get_model_object(Property, 'id', property_id)
		if budget_item_id:
			store.budget_item = get_model_object(BudgetItem, 'id', budget_item_id)
		with SaveContextManager(store, model=Store):
			return store
