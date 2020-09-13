import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required
from apps.properties.models import Property, PropDetail
from apps.users.models import User
from apps.properties.serializers import PropertySerializer, PropDetailSerializer
from app_utils.model_types.property import PropertyType, DetailType, MsgSerializer
from app_utils.helpers import get_errors
from app_utils.database import get_model_object


class CreateProperty(graphene.Mutation):
	message = MsgSerializer()
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
		
		serializer = PropertySerializer(data=kwargs)
		
		if serializer.is_valid():
			new_property = serializer.save(owner=user)
			message = "The property created"
		else:
			message = get_errors(serializer.errors)
			raise GraphQLError(message)
		
		return CreateProperty(message=message, property=new_property)


class AddPropDetail(graphene.Mutation):
	message = MsgSerializer()
	new_detail = graphene.Field(DetailType)
	
	class Arguments:
		title = graphene.String(required=True)
		is_inflow = graphene.Boolean(required=True)
		amount = graphene.Float(required=True)
		property_id = graphene.Int(required=True)
	
	@login_required
	def mutate(self, info, property_id, **kwargs):
		the_property = get_model_object(Property, 'id', property_id)
		
		kwargs['type'] = 'in' if kwargs['is_inflow'] else 'out'
		serializer = PropDetailSerializer(data=kwargs)
		
		if serializer.is_valid():
			new_detail = serializer.save(property_id=the_property.id)
			message = 'The prop detail has successfully added'
		else:
			message = get_errors(serializer.errors)
			raise GraphQLError(message)
		return AddPropDetail(message=message, new_detail=new_detail)


class PropertyMutations(graphene.ObjectType):
	create_property = CreateProperty.Field()
	add_prop_detail = AddPropDetail.Field()
