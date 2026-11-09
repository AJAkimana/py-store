import graphene
from graphene_django import DjangoObjectType
from apps.users.models import User, UserSettings, Currency


class UserType(DjangoObjectType):
	class Meta:
		model = User
		exclude_fields = ('password', 'previous_passwords', 'password_changed_at')


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
		# Expose theme_mode as a plain 'light' | 'dark' string instead of a generated enum
		convert_choices_to_enum = False

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


class MfaStatusType(graphene.ObjectType):
	"""The user's two-factor status. Never carries secrets."""
	enabled = graphene.Boolean(required=True)
	totp_enabled = graphene.Boolean(required=True)
	email_enabled = graphene.Boolean(required=True)
	methods = graphene.List(graphene.NonNull(graphene.String), required=True)
	preferred_method = graphene.String()
	recovery_codes_remaining = graphene.Int(required=True)


class TotpSetupType(graphene.ObjectType):
	"""Shown once while adding an authenticator app."""
	secret = graphene.String(required=True)
	otpauth_uri = graphene.String(required=True)
	qr_svg = graphene.String(required=True, description='QR code as an SVG data URI')
