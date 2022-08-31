from django.db.models import Q
from graphql import GraphQLError

from app_utils.constants import STORE_CHOICES
from app_utils.database import get_model_object, SaveContextManager
from apps.properties.models import Property
from apps.stores.models import Store
from apps.users.models import User


class ValidateUser:
	def __init__(self, **user_body):
		self.user = user_body

	def validate_and_save_user(self, user):
		"""
    Args:
      user: The user instance

    Returns: new updated user after it has been saved into database
    """
		user_id = self.user.get('id', None)
		for key, value in self.user.items():
			if isinstance(value, str) and value.strip() == '':
				raise GraphQLError(f"The {key} field can't be empty")
			if key == 'id':
				continue
			setattr(user, key, value)

		filters = Q(user_name=self.user['user_name'],
								email=self.user['email'], _connector=Q.OR)
		if user_id:
			filters = (~Q(id=user_id) & filters)

		has_saved = User.objects.filter(filters).first()
		if has_saved:
			raise GraphQLError('User with the same info is already created')

		new_user = User.objects.create_user(**self.user)
		if not user_id:
			new_user.is_verified = False
			new_user.set_password = self.user.get('password')
			new_user.save()
		return new_user
