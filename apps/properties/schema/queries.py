import graphene
from graphene_django import DjangoObjectType
from django.db.models import Q
from apps.properties.models import Property
from graphql_jwt.decorators import login_required


class PropertyType(DjangoObjectType):
	class Meta:
		model = Property


class PropertyQuery(graphene.AbstractType):
	properties = graphene.List(PropertyType, search=graphene.String())

	@login_required
	def resolve_properties(self, info, search=None, **kwargs):
		if search:
			search_filter = (Q(name__icontains=search))
			return Property.objects.filter(search_filter)
		return Property.objects.all()
