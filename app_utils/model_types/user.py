import graphene
from graphene_django import DjangoObjectType
from apps.users.models import User, UserSettings


class UserType(DjangoObjectType):
	class Meta:
		model = User
		exclude_fields = ('password', 'previous_passwords')


class WelcomeType(graphene.ObjectType):
	class Meta:
		description = 'Test'
	message = graphene.String()
	fields = 'message'


class PaginatorUserType(graphene.ObjectType):
	page_data = graphene.List(UserType)
	num_pages = graphene.Int()
	total_count = graphene.Int()


class UserSettingsType(DjangoObjectType):
	class Meta:
		model = UserSettings
