from graphene import ObjectType, List, Int, types
from graphene_django import DjangoObjectType
from apps.properties.models import Property, PropDetail


class DetailType(DjangoObjectType):
	class Meta:
		model = PropDetail


class PropertyType(DjangoObjectType):
	details = List(DetailType)
	details_counts = Int()
	
	class Meta:
		model = Property
	
	def resolve_details(self, info, **kwargs):
		return self.prop_details.all()
	
	def resolve_details_counts(self, info, **kwargs):
		return self.prop_details.count()


class PropertyDetailType(ObjectType):
	count = Int()
	total_amount = Int()
	

class PropPaginatorType(ObjectType):
	page_data = List(PropertyType)
	num_pages = Int()
	total_count = Int()


class MsgSerializer(types.scalars.Scalar):
	@staticmethod
	def serialize(dt):
		return dt
