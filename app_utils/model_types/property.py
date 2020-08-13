import graphene
from graphene import ObjectType
from graphene_django import DjangoObjectType
from apps.properties.models import Property, PropDetail


class DetailType(DjangoObjectType):
	class Meta:
		model = PropDetail


class PropertyType(DjangoObjectType):
	details = graphene.List(DetailType)
	details_counts = graphene.Int()
	
	class Meta:
		model = Property
	
	def resolve_details(self, info, **kwargs):
		return self.prop_details.all()
	
	def resolve_details_counts(self, info, **kwargs):
		return self.prop_details.count()


class PropertyDetailType(ObjectType):
	count = graphene.Int()
	total_amount = graphene.Int()