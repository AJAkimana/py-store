import graphene
from graphene_django import DjangoObjectType

from apps.household_members.models import HouseholdMember
from apps.households.models import Household
from apps.manage_system.models import Salary
from apps.stores.models import Store, RecurringStore


class StoreType(DjangoObjectType):
	class Meta:
		model = Store


class RecurringStoreType(DjangoObjectType):
	class Meta:
		model = RecurringStore


class HouseholdType(DjangoObjectType):
	class Meta:
		model = Household


class HouseholdMemberType(DjangoObjectType):
	class Meta:
		model = HouseholdMember


class AggregatedInOutFlow(graphene.ObjectType):
	inflow = graphene.Float()
	outflow = graphene.Float()
	diff = graphene.Float()


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
	aggregate = graphene.Field(AggregatedInOutFlow)


class RecurringStorePaginatorType(graphene.ObjectType):
	page_data = graphene.List(RecurringStoreType)
	num_pages = graphene.Int()
	total_count = graphene.Int()


class HouseholdPaginatorType(graphene.ObjectType):
	page_data = graphene.List(HouseholdType)
	num_pages = graphene.Int()
	total_count = graphene.Int()


class MonthType(graphene.ObjectType):
	label = graphene.String()
	value = graphene.Int()


class StoreRatioType(graphene.ObjectType):
	inflow = graphene.Int()
	outflow = graphene.Int()
	percent = graphene.Float()


class FacilityType(graphene.InputObjectType):
	is_constant = graphene.Boolean()
	amount = graphene.Float()
	percent_amount = graphene.Float()
	percent_field = graphene.String()


class SalaryType(DjangoObjectType):
	class Meta:
		model = Salary
		# fields = '__all__'
	# gross_salary = graphene.Float()
	# net_salary = graphene.Float()
	# net_pay = graphene.Float()
	# pension = graphene.Float()
	# maternity = graphene.Float()
	# facilities = graphene.Float()
	# tax = graphene.Float()


class SalaryPaginatorType(graphene.ObjectType):
	page_data = graphene.List(SalaryType)
	num_pages = graphene.Int()
	total_count = graphene.Int()
