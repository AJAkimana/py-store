import graphene
from django.db.models import Q
from apps.properties.models import Property
from apps.users.models import User
from app_utils.model_types.property import PropertyType, PropertyDetailType
from graphql_jwt.decorators import login_required


class PropertyQuery(graphene.ObjectType):
	properties = graphene.List(PropertyType, search=graphene.String())
	properties_detail = graphene.Field(PropertyDetailType)
	
	@login_required
	def resolve_properties(self, info, search=None, **kwargs):
		user = info.context.user
		properties = User.get_user_properties(user)
		if search:
			search_filter = (Q(name__icontains=search))
			return properties.filter(search_filter)
		return properties
	
	@login_required
	def resolve_properties_detail(self, info, **kwargs):
		user = info.context.user
		total_count = User.get_user_properties(user).count()
		total_value = Property.get_total_price(Property, user=user)
		return {'count': total_count, 'total_amount': total_value}
