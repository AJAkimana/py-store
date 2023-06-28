from django.db.models import Q
from graphql import GraphQLError

from apps.households.models import Household
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
		configure_household = self.user.get('configure_household', None)
		for key, value in self.user.items():
			if key == 'id' or (key == 'password' and user_id is not None):
				continue
			if isinstance(value, str) and value.strip() == '':
				raise GraphQLError(f"The {key} field can't be empty")
			setattr(user, key, value)

		filters = Q(
			user_name=self.user['user_name'],
			email=self.user['email'],
			phone=self.user['phone'],
			_connector=Q.OR
		)
		if user_id:
			filters = (~Q(id=user_id) & filters)

		has_saved = User.objects.filter(filters).first()
		if has_saved:
			raise GraphQLError('User with the same info is already created')

		if self.user.get('password', None) is not None:
			user.set_password(self.user.get('password'))
			user.is_verified = False
		user.save()
		print('Excuted', user.household_set.count(), configure_household)
		if user.household_set.count() == 0 and configure_household:
			new_household = Household.objects.create(
				name=f"{user.user_name} family",
				created_by=user,
			)
			new_household.members.add(user, through_defaults={'access_level': 1})
		return user
