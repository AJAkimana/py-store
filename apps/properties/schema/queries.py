import graphene
from graphene_django import DjangoObjectType
from apps.properties.models import Property
from graphql_jwt.decorators import login_required


class PropertyType(DjangoObjectType):
	class Meta:
		model = Property


class PropertyQuery(graphene.AbstractType):
	properties = graphene.List(PropertyType, search=graphene.String())

	@login_required
	def resolve_properties(self, info, search=None, **kwargs):
		return Property.objects()
