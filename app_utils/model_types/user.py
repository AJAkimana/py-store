import graphene
from graphene_django import DjangoObjectType
from apps.users.models import User, UserSettings, Currency


class UserType(DjangoObjectType):
	class Meta:
		model = User
		exclude_fields = (
			'password', 'previous_passwords', 'password_changed_at',
			'invited_at', 'temp_password_expires_at', 'deactivated_at', 'deactivated_by',
		)


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


class ManagedUserType(graphene.ObjectType):
	"""A user as the administrator sees them in user management."""
	id = graphene.ID(required=True)
	first_name = graphene.String()
	last_name = graphene.String()
	user_name = graphene.String()
	email = graphene.String()
	phone = graphene.String()
	is_active = graphene.Boolean(required=True)
	invite_pending = graphene.Boolean(required=True, description="Hasn't replaced the temporary password yet")
	invite_expired = graphene.Boolean(required=True)
	invited_at = graphene.DateTime()
	temp_password_expires_at = graphene.DateTime()
	last_login = graphene.DateTime()
	created_at = graphene.DateTime()
	deactivated_at = graphene.DateTime()
	deactivated_by_name = graphene.String()
	mfa_enabled = graphene.Boolean(required=True)

	def resolve_invite_pending(user, info):
		return not user.is_verified

	def resolve_invite_expired(user, info):
		from apps.users.user_management import temp_password_expired
		return not user.is_verified and temp_password_expired(user)

	def resolve_deactivated_by_name(user, info):
		by = user.deactivated_by
		return (f'{by.first_name} {by.last_name}'.strip() or by.email) if by else None

	def resolve_mfa_enabled(user, info):
		mfa = getattr(user, 'mfa', None)
		return bool(mfa and mfa.is_enabled)


class PaginatorManagedUserType(graphene.ObjectType):
	page_data = graphene.List(graphene.NonNull(ManagedUserType), required=True)
	num_pages = graphene.Int(required=True)
	total_count = graphene.Int(required=True)
