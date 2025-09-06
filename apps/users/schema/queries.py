import graphene
from graphql_jwt.decorators import login_required,\
	superuser_required
from django.db.models import Q
from app_utils.model_types.user import UserType, \
	PaginatorUserType, WelcomeType, UserSettingsType, CurrencyType
from app_utils.helpers import PAGINATION_DEFAULT, paginate_data
from apps.users.models import User, Currency, UserSettings


class UserQuery(graphene.ObjectType):
	me = graphene.Field(UserType)
	welcome = graphene.Field(WelcomeType)
	users = graphene.Field(
		PaginatorUserType,
		search=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int())
	user_settings = graphene.Field(UserSettingsType)
	currencies = graphene.List(CurrencyType)

	@login_required
	def resolve_me(self, info, **kwargs):
		return info.context.user

	@login_required
	@superuser_required
	def resolve_users(self, info, search=None, **kwargs):
		page_count = kwargs.get('page_count', PAGINATION_DEFAULT['page_count'])
		page_number = kwargs.get('page_number', PAGINATION_DEFAULT['page_number'])
		users = User.objects.filter(is_superuser=False).order_by('first_name')
		if search:
			search_filter = (
					Q(first_name__icontains=search) |
					Q(last_name__icontains=search) |
					Q(user_name__icontains=search) |
					Q(phone__icontains=search) |
					Q(email__icontains=search))
			users = users.filter(search_filter)
		paginated_result = paginate_data(users, page_count, page_number)
		return paginated_result

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
				default_currency=None
			)
		return settings

	@login_required
	def resolve_currencies(self, info, **kwargs):
		return Currency.objects.all()
