from graphene import ObjectType, List, Int, String, Float
from graphene_django import DjangoObjectType
from apps.stores.models import Store


class StoreType(DjangoObjectType):
	class Meta:
		model = Store


class StorePaginatorType(ObjectType):
	page_data = List(StoreType)
	num_pages = Int()
	total_count = Int()


class MonthType(ObjectType):
	label = String()
	value = Int()


class StoreRatioType(ObjectType):
	inflow = Int()
	outflow = Int()
	percent = Float()