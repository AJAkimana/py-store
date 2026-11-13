import graphene
from graphql_jwt.decorators import login_required, \
	superuser_required
from django.db.models import Q
from app_utils.model_types.user import UserType, \
	PaginatorManagedUserType, WelcomeType, UserSettingsType, CurrencyType, MfaStatusType
from app_utils.helpers import PAGINATION_DEFAULT, paginate_data
from apps.users.mfa import get_mfa_status
from apps.users.user_management import filter_managed_users
from apps.users.models import User, Currency, UserSettings, ThemeMode, \
	DEFAULT_PRIMARY_COLOR, DEFAULT_SECONDARY_COLOR


class UserQuery(graphene.ObjectType):
	me = graphene.Field(UserType)
	welcome = graphene.Field(WelcomeType)
	users = graphene.Field(
		PaginatorManagedUserType,
		search=graphene.String(),
		status=graphene.String(description="'active', 'invited' or 'disabled'; all when empty"),
		page_count=graphene.Int(),
		page_number=graphene.Int())
	user_settings = graphene.Field(UserSettingsType)
	currencies = graphene.List(CurrencyType)
	mfa_status = graphene.Field(MfaStatusType, required=True)

	@login_required
	def resolve_mfa_status(self, info, **kwargs):
		return MfaStatusType(**get_mfa_status(info.context.user))

	@login_required
	def resolve_me(self, info, **kwargs):
		return info.context.user

	@login_required
	@superuser_required
	def resolve_users(self, info, search=None, status=None, **kwargs):
		# Regular users only: the administrator manages their own account in Settings
		page_count = kwargs.get('page_count', PAGINATION_DEFAULT['page_count'])
		page_number = kwargs.get('page_number', PAGINATION_DEFAULT['page_number'])
		return paginate_data(filter_managed_users(search, status), page_count, page_number)

	def resolve_welcome(self, info, **kwargs):
		message = 'Welcome to the D2DStore system'
		return {'message': message}

	@login_required
	def resolve_user_settings(self, info, **kwargs):
		user = info.context.user
		settings = user.settings if hasattr(user, 'settings') else None
		if settings is None:
			# Default settings
			return UserSettingsType(
				email_notifications=True,
				email_notifications_help_text=UserSettings._meta.get_field("email_notifications").help_text,
				push_notifications=True,
				push_notifications_help_text=UserSettings._meta.get_field("push_notifications").help_text,
				budget_alerts_enabled=True,
				budget_alerts_enabled_help_text=UserSettings._meta.get_field("budget_alerts_enabled").help_text,
				budget_alert_threshold=80,
				budget_alert_threshold_help_text=UserSettings._meta.get_field("budget_alert_threshold").help_text,
				default_currency=None,
				theme_mode=ThemeMode.LIGHT.value,
				primary_color=DEFAULT_PRIMARY_COLOR,
				secondary_color=DEFAULT_SECONDARY_COLOR,
			)
		return settings

	@login_required
	def resolve_currencies(self, info, **kwargs):
		return Currency.objects.all()
