import graphene
from django.db import connection
from django.db.models import Q
from graphql_jwt.decorators import login_required, superuser_required

from app_utils.background_task import send_weekly_summary, send_monthly_summary
from app_utils.helpers import paginate_data, dict_fetchall, get_aggregated_in_out, get_stores_filter
from app_utils.model_types.store import StorePaginatorType, \
	MonthType, StoreRatioType, RecurringStorePaginatorType
from apps.household_members.helpers import get_member_filter
from apps.stores.models import Store
from apps.users.models import User


class StoreQuery(graphene.ObjectType):
	stores = graphene.Field(
		StorePaginatorType,
		search_key=graphene.String(),
		search_date_from=graphene.String(),
		search_date_to=graphene.String(),
		search_type=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int(),
		store_type=graphene.String(),
		search_member=graphene.String()
	)
	total_inflow = graphene.Int(store_type=graphene.String())
	total_outflow = graphene.Int(store_type=graphene.String())
	store_count = graphene.Int()
	monthly_store = graphene.List(MonthType, is_inflow=graphene.Boolean(), time=graphene.String())
	store_aggregate = graphene.Field(StoreRatioType, store_type=graphene.String())
	recurring_stores = graphene.Field(
		RecurringStorePaginatorType,
		search_key=graphene.Argument(graphene.String, required=False),
	)
	trigger_store_report = graphene.String(report_type=graphene.String())

	@login_required
	def resolve_stores(self, info, search_member='', page_count=10, page_number=1, **kwargs):
		user = info.context.user
		search_filter = get_stores_filter(**kwargs)
		if search_member == '':
			stores = User.get_user_stores(user, search_filter)
		else:
			search_filter &= get_member_filter(user, search_member)
			stores = Store.objects.filter(search_filter)

		paginated_result = paginate_data(stores, page_count, page_number)
		paginated_result['aggregate'] = get_aggregated_in_out(stores)
		return paginated_result

	@login_required
	def resolve_total_inflow(self, info, store_type='use', **kwargs):
		user = info.context.user
		return User.get_store_total_amount(user, store_type)

	@login_required
	def resolve_total_outflow(self, info, store_type='use', **kwargs):
		user = info.context.user
		return User.get_store_total_amount(user, store_type, False)

	@login_required
	def resolve_store_count(self, info):
		user = info.context.user
		filters = get_stores_filter()
		return User.get_user_stores(user, filters).count()

	@login_required
	def resolve_monthly_store(self, info, is_inflow=False, time='2_years'):
		user = info.context.user
		table_name = Store._meta.db_table
		date_condition = "action_date > (CURRENT_DATE - INTERVAL '24 months')"
		custom_column = "date_trunc('month', action_date)"
		column_label = f"""to_char({custom_column}, 'Mon, YYYY')"""
		if time == '1_year':
			date_condition = "action_date > (CURRENT_DATE - INTERVAL '12 months')"
		if time == 'last_year':
			date_condition = "action_date >= date_trunc('year', CURRENT_DATE - interval '1' YEAR)"
			date_condition += " AND action_date < date_trunc('year', CURRENT_DATE)"
		if time == 'current_year':
			date_condition = 'extract (year FROM action_date) = extract (year FROM CURRENT_DATE)'
		if time == 'last_month':
			custom_column = 'action_date'
			column_label = f"""to_char({custom_column}, 'Mon-DD')"""
			date_condition = "action_date >= date_trunc('month', CURRENT_DATE - interval '1' MONTH)"
			date_condition += " AND action_date < date_trunc('month', CURRENT_DATE)"
		if time == 'current_month':
			custom_column = 'action_date'
			column_label = f"""to_char({custom_column}, 'Mon-DD')"""
			date_condition = 'extract (month FROM action_date) = extract (month FROM CURRENT_DATE)'
			date_condition += ' AND extract (year FROM action_date) = extract (year FROM CURRENT_DATE)'
		pg_query = \
			f"""
			SELECT {column_label} AS label, SUM(amount) AS value
			FROM {table_name} WHERE user_id='{user.id}' AND is_inflow={is_inflow} AND {date_condition}
			GROUP BY {custom_column}
			ORDER BY {custom_column} DESC;
			"""
		mysql_query = \
			f"""
			SELECT 'D2DStore' AS project;
			"""
		query = pg_query if connection.vendor == 'postgresql' else mysql_query

		with connection.cursor() as cursor:
			cursor.execute(query)
			stores = dict_fetchall(cursor)

		return stores

	@login_required
	def resolve_store_aggregate(self, info, store_type='use', **kwargs):
		user = info.context.user
		aggregate = User.get_store_aggregate(user, store_type)

		return aggregate

	@login_required
	def resolve_recurring_stores(self, info, search_key):
		user = info.context.user
		filters = Q(name__icontains=search_key)
		stores = User.get_user_recurring_stores(user, filters)

		paginated_result = paginate_data(stores, page_count=10, page_number=1)
		return paginated_result

	@superuser_required
	def resolve_trigger_store_report(self, info, report_type='weekly'):
		if report_type == 'weekly':
			send_weekly_summary()
		elif report_type == 'monthly':
			send_monthly_summary(is_manual=True)
		return 'Report triggered successfully'
