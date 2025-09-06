import graphene
from graphene_django import DjangoObjectType
from apps.users.models import User, UserSettings, Currency


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

	email_notifications_help_text = graphene.String()
	push_notifications_help_text = graphene.String()
	budget_alerts_enabled_help_text = graphene.String()
	budget_alert_threshold_help_text = graphene.String()

	def resolve_email_notifications_help_text(self, info):
		return UserSettings._meta.get_field("email_notifications").help_text

	def resolve_push_notifications_help_text(self, info):
		return UserSettings._meta.get_field("push_notifications").help_text

	def resolve_budget_alerts_enabled_help_text(self, info):
		return UserSettings._meta.get_field("budget_alerts_enabled").help_text

	def resolve_budget_alert_threshold_help_text(self, info):
		return UserSettings._meta.get_field("budget_alert_threshold").help_text


class CurrencyType(DjangoObjectType):
		class Meta:
			model = Currency
