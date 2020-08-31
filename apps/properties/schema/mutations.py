import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from apps.properties.models import Property, PropDetail
from apps.users.models import User
from app_utils.model_types.property import PropertyType


class CreateProperty(graphene.Mutation):
	message = graphene.String()
	property = graphene.Field(PropertyType)
	
	class Arguments:
		name = graphene.String(required=True)
		price = graphene.Float(required=True)
		description = graphene.String(required=True)
		cover_image = graphene.String()
		is_active = graphene.Boolean()
		
	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user
		user_properties = User.get_user_properties(user)
		has_saved = user_properties.filter(name=kwargs['name'])
		if has_saved:
			raise GraphQLError('The property already created')
		kwargs['owner_id'] = user.id
		new_property = Property(**kwargs)
		new_property.save()
		
		return CreateProperty(
			message='Property created',
			property=new_property)


class PropertyMutations(graphene.ObjectType):
	create_property = CreateProperty.Field()
