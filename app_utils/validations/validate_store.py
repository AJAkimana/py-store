import datetime

from django.db.models import Q
from graphql import GraphQLError

from app_utils.constants import STORE_CHOICES
from app_utils.database import get_model_object, SaveContextManager
from apps.properties.models import Property, PropDetail
from apps.stores.models import Store


class ValidateStore:
  def __init__(self, **store_body):
    self.store = store_body

  def validate_and_save_store(self, store):
    property_id = self.store.pop('property_id', None)
    store_id = self.store.get('id', None)
    store_description = store.description
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
    has_saved = Store.objects.filter(filters).first()
    if has_saved:
      raise GraphQLError('The record has already been recorded')
    if property_id:
      property = Property.objects.get(id=property_id)
      store.property = property
    # delete_product = save_product = is_product = False
    # if not property_id and (store_id and store.property):
    #   delete_product = True
    # if store.property and store.property.id != property_id:
    #   delete_product = True
    #   save_product = True
    # if property_id and not store_id:
    #   save_product = True
    # if delete_product:
    #   PropDetail.objects.get(
    #     property=store.property,
    #     title=store_description,
    #     created_at__date=store.updated_at.date()
    #   ).delete()
    #   store.property = None
    # if save_product:
    #   is_product = True
    #   property = get_model_object(Property, 'id', property_id)
    #   store.property = property
    # store.is_property = is_product

    with SaveContextManager(store, model=Store):
      return store
