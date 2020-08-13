import graphene
from django.db.models import Q
from apps.properties.models import Property
from apps.users.models import User
from app_utils.model_types.property import PropPaginatorType,\
	PropertyDetailType
from app_utils.helpers import PAGINATION_DEFAULT, paginate_data
from graphql_jwt.decorators import login_required


class PropertyQuery(graphene.ObjectType):
	properties = graphene.Field(
		PropPaginatorType,
		search=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int())
	properties_detail = graphene.Field(PropertyDetailType)
	
	@login_required
	def resolve_properties(self, info, search=None, **kwargs):
		page_count = kwargs.get('page_count', PAGINATION_DEFAULT['page_count'])
		page_number = kwargs.get('page_number', PAGINATION_DEFAULT['page_number'])
		user = info.context.user
		properties = User.get_user_properties(user)
		if search:
			search_filter = (Q(name__icontains=search))
			properties = properties.filter(search_filter)
		paginated_result = paginate_data(properties, page_count, page_number)
		return paginated_result
	
	@login_required
	def resolve_properties_detail(self, info, **kwargs):
		user = info.context.user
		total_count = User.get_user_properties(user).count()
		total_value = Property.get_total_price(Property, user=user)
		return {'count': total_count, 'total_amount': total_value}
