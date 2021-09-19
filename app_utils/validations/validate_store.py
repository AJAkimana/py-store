from graphql import GraphQLError

from app_utils.constants import STORE_CHOICES
from apps.stores.models import Store


class ValidateStore:
  def __init__(self, store_body):
    self.store = store_body

  def validate_create(self, user):
    store_type = [item for item in STORE_CHOICES if item[0] == self.store['record_type']]
    if not store_type:
      raise GraphQLError('Invalid store type')
    has_saved = Store.objects.filter(
      action_date=self.store['action_date'],
      description=self.store['description'],
      user=user
    ).first()
    if has_saved:
      raise GraphQLError('The record has already been recorded')
