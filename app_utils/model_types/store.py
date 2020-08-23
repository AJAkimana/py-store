import graphene
from graphene_django import DjangoObjectType
from apps.stores.models import Store


class StoreType(DjangoObjectType):
	class Meta:
		model = Store


class StoreInputType(graphene.InputObjectType):
	amount = graphene.Float()
	record_type = graphene.String()
	is_property = graphene.Boolean()
	is_inflow = graphene.Boolean()
	action_date = graphene.Date()
	description = graphene.String()


class StorePaginatorType(graphene.ObjectType):
	page_data = graphene.List(StoreType)
	num_pages = graphene.Int()
	total_count = graphene.Int()


class MonthType(graphene.ObjectType):
	label = graphene.String()
	value = graphene.Int()


class StoreRatioType(graphene.ObjectType):
	inflow = graphene.Int()
	outflow = graphene.Int()
	percent = graphene.Float()
