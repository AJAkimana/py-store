import graphene
from django.db import connection
from graphene import AbstractType
from django.db.models import Q
from graphql_jwt.decorators import login_required
from app_utils.helpers import paginate_data, PAGINATION_DEFAULT, dict_fetchall
from app_utils.model_types.store import StorePaginatorType, \
	MonthType, StoreRatioType
from apps.stores.models import Store
from apps.users.models import User


class StoreQuery(AbstractType):
	stores = graphene.Field(
		StorePaginatorType,
		search=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int(),
		store_type=graphene.String()
	)
	total_inflow = graphene.Int(store_type=graphene.String())
	total_outflow = graphene.Int(store_type=graphene.String())
	store_count = graphene.Int()
	monthly_store = graphene.List(MonthType, is_inflow=graphene.Boolean())
	store_aggregate = graphene.Field(StoreRatioType, store_type=graphene.String())

	@login_required
	def resolve_stores(self, info, search=None, store_type='use', **kwargs):
		page_count = kwargs.get('page_count', PAGINATION_DEFAULT['page_count'])
		page_number = kwargs.get('page_number', PAGINATION_DEFAULT['page_number'])

		user = info.context.user
		stores = User.get_user_stores(user).filter(record_type=store_type)
		if search:
			search_filter = (
					Q(amount__icontains=search) | Q(description__icontains=search)
			)
			stores = stores.filter(search_filter)
		paginated_result = paginate_data(stores, page_count, page_number)
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
		return User.get_user_stores(user).count()

	@login_required
	def resolve_monthly_store(self, info, is_inflow=False):
		user = info.context.user
		table_name = Store._meta.db_table
		pg_query = \
			f"""
			SELECT to_char(date_trunc('month', action_date), 'Mon, YYYY') AS label,
			SUM(amount) AS value
			FROM {table_name} WHERE action_date > (current_date - INTERVAL '24 months') AND
			user_id='{user.id}' AND is_inflow={is_inflow}
			GROUP BY date_trunc('month', action_date)
			ORDER BY date_trunc('month', action_date) DESC;
			"""
		mysql_query = \
			f"""
			SELECT id, DATE_FORMAT(action_date, '%%b, %%Y') AS label,
			SUM(amount) AS value
			FROM {table_name} WHERE user_id='{user.id}' AND is_inflow={is_inflow}
			GROUP BY label, year(action_date)
			ORDER BY action_date DESC
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
