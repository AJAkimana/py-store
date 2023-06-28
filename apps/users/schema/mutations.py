import graphene
from django.contrib.auth import authenticate, logout
from graphql_jwt.decorators import login_required, superuser_required
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import update_last_login
from graphql import GraphQLError
# from graphql_jwt.utils import jwt_payload, jwt_encode
from graphql_jwt.shortcuts import get_token
from app_utils.database import get_model_object
from app_utils.validations.validate_user import ValidateUser
from apps.users.models import User
from app_utils.model_types.user import UserType


class RegisterUser(graphene.Mutation):
	"""
    This is a mutation used to create new users
    """
	user = graphene.Field(UserType)
	message = graphene.String()

	class Arguments:
		email = graphene.String()
		phone = graphene.String()
		user_name = graphene.String()
		password = graphene.String()
		configure_household = graphene.Boolean()

	@login_required
	@superuser_required
	def mutate(self, info, **kwargs):
		user = User()
		validator = ValidateUser(**kwargs)
		new_user = validator.validate_and_save_user(user)

		return RegisterUser(message='Success', user=new_user)


class UpdateRegisteredUser(RegisterUser):
	"""
  This is a mutation used to update new users
  """

	class Arguments(RegisterUser.Arguments):
		id = graphene.String(required=True)

	@login_required
	@superuser_required
	def mutate(self, info, **kwargs):
		user = get_model_object(User, 'id', kwargs.get('id'))
		validator = ValidateUser(**kwargs)

		updated_user = validator.validate_and_save_user(user)
		return UpdateRegisteredUser(message='Successfully update', user=updated_user)


class LoginUser(graphene.Mutation):
	"""
    Login a users with their credentials

    args:
        password(str): users's registered password
        email(str): users's registered email

    returns:
        message(str): success messsage confirming login
        token(str): JWT authorization token used to validate the login
        rest_token(str): JWT token used to validate REST endpoint access
        user(obj): 'User' object containing details of the logged in users
    """
	message = graphene.String()
	token = graphene.String()
	rest_token = graphene.String()
	user = graphene.Field(UserType)

	class Arguments:
		email = graphene.String()
		password = graphene.String()

	def mutate(self, info, email, password, **kwargs):
		user_auth = authenticate(email=email, password=password)
		if user_auth is None:
			raise GraphQLError('Invalid credentials')
		user = get_model_object(User, 'email', email)
		if not user.is_verified:
			raise GraphQLError('Create a new password first', user_auth)
		update_last_login(sender=User, user=user)
		# user_payload = jwt_payload(user_auth)
		token = get_token(user)
		rest_payload = Token.objects.get_or_create(user=user_auth)
		rest_token = rest_payload[0]

		return LoginUser(message='Success', token=token,
										 rest_token=rest_token, user=user)


class UpdateUserProfile(graphene.Mutation):
	"""
    This is a mutation used to create new users
    """
	user = graphene.Field(UserType)
	message = graphene.String()

	class Arguments:
		first_name = graphene.String()
		last_name = graphene.String()
		phone = graphene.String()
		password = graphene.String()
		only_password = graphene.Boolean()

	@login_required
	def mutate(self, info, **kwargs):
		user = info.context
		validator = ValidateUser(**kwargs)
		new_user = validator.validate_and_save_user(user)

		return UpdateUserProfile(message='Success', user=new_user)


class ResetPassword(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		email = graphene.String()
		old_password = graphene.String()
		new_password = graphene.String()

	def mutate(self, info, email, old_password, new_password, **kwargs):
		if old_password == new_password:
			raise GraphQLError('You cannot set the same password')
		user_auth = authenticate(email=email, password=old_password)
		if not user_auth:
			raise GraphQLError('Oops, we dont know you!!')
		if not user_auth.is_active:
			raise GraphQLError('Oops, you are not allowed to perform this action.')

		user = get_model_object(User, 'email', email)
		user.is_verified = True
		user.set_password(new_password)
		user.save()

		if info.context.user.is_anonymous is False:
			Token.objects.filter(user=info.context.user).delete()

		return ResetPassword(message='Success')


class LogoutUser(graphene.Mutation):
	message = graphene.String()

	def mutate(self, info, **kwargs):
		Token.objects.filter(user=info.context.user).delete()

		return LogoutUser(message='Success')


class UserMutations(graphene.ObjectType):
	login_user = LoginUser.Field()
	reset_password = ResetPassword.Field()
	update_user_profile = UpdateUserProfile.Field()
	register_user = RegisterUser.Field()
	update_registered_user = UpdateRegisteredUser.Field()
	logout_user = LogoutUser.Field()
