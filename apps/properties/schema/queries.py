import graphene
from django.db.models import Q
from apps.properties.models import Property
from apps.users.models import User
from app_utils.model_types.property import PropPaginatorType,\
	PropertyDetailType
from app_utils.helpers import PAGINATION_DEFAULT, paginate_data, properties_active
from graphql_jwt.decorators import login_required


class PropertyQuery(graphene.ObjectType):
	properties = graphene.Field(
		PropPaginatorType,
		search=graphene.String(),
		is_active=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int())
	properties_detail = graphene.Field(
		PropertyDetailType,
		is_active=graphene.String()
	)

	@login_required
	def resolve_properties(self, info, search=None, **kwargs):
		page_count = kwargs.get('page_count', PAGINATION_DEFAULT['page_count'])
		page_number = kwargs.get('page_number', PAGINATION_DEFAULT['page_number'])
		user = info.context.user
		active = properties_active(kwargs.get('is_active', 'all'))

		properties = User.get_user_properties(user, active)
		if search:
			search_filter = (Q(name__icontains=search))
			properties = properties.filter(search_filter)
		paginated_result = paginate_data(properties, page_count, page_number)
		return paginated_result

	@login_required
	def resolve_properties_detail(self, info, is_active=None, **kwargs):
		user = info.context.user
		active = properties_active(is_active)

		total_count = User.get_user_properties(user, active).count()
		total_value = User.get_properties_total_value(user, active)
		return {'count': total_count, 'total_amount': total_value}
