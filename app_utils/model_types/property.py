import graphene
from graphene_django import DjangoObjectType
from apps.properties.models import Property, PropDetail


class DetailType(DjangoObjectType):
	class Meta:
		model = PropDetail


class PropertyType(DjangoObjectType):
	details_counts = graphene.Int()
	details_ins = graphene.Int()
	details_outs = graphene.Int()

	class Meta:
		model = Property

	def resolve_details_counts(self, info, **kwargs):
		return self.prop_details.count()

	def resolve_details_ins(self, info, **kwargs):
		total = sum([prop.amount for prop in self.prop_details.filter(type='in')])
		return total

	def resolve_details_outs(self, info, **kwargs):
		total = sum([prop.amount for prop in self.prop_details.filter(type='out')])
		return total


class PropertyDetailType(graphene.ObjectType):
	count = graphene.Int()
	total_amount = graphene.Int()


class PropPaginatorType(graphene.ObjectType):
	page_data = graphene.List(PropertyType)
	num_pages = graphene.Int()
	total_count = graphene.Int()


class MsgSerializer(graphene.types.scalars.Scalar):
	@staticmethod
	def serialize(dt):
		return dt
