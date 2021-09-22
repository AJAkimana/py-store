from django.db.models import Q
from graphql import GraphQLError

from app_utils.constants import STORE_CHOICES
from app_utils.database import get_model_object, SaveContextManager
from apps.properties.models import Property
from apps.stores.models import Store


class ValidateStore:
  def __init__(self, **store_body):
    self.store = store_body

  def validate_and_save_store(self, store):
    """
    Args:
      store: The store instance

    Returns: new updated store after it has been saved into database
    """
    property_id = self.store.pop('property_id', None)
    store_id = self.store.get('id', None)
    for key, value in self.store.items():
      if isinstance(value, str) and value.strip() == '':
        raise GraphQLError(f"The {key} field can't be empty")
      if key == 'id':
        continue
      setattr(store, key, value)

    store_type = [item for item in STORE_CHOICES if item[0] == self.store['record_type']]
    if not store_type:
      raise GraphQLError('Invalid store type')

    filters = Q(action_date=self.store['action_date'],
                description=self.store['description'],
                user=store.user)
    if store_id:
      filters = (~Q(id=store_id) & filters)
      if store.property and not property_id:
        store.property = None

    has_saved = Store.objects.filter(filters).first()
    if has_saved:
      raise GraphQLError('The record has already been recorded')
    if property_id:
      property = get_model_object(Property, 'id', property_id)
      store.property = property

    with SaveContextManager(store, model=Store):
      return store
