import calendar
from datetime import date

import graphene
from graphene_django import DjangoObjectType

from apps.behavior_ip.models import Behavior
from apps.budgeting.models import Budget, BudgetItem
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


class BehaviorType(DjangoObjectType):
	class Meta:
		model = Behavior


class BudgetType(DjangoObjectType):
	class Meta:
		model = Budget

	amount = graphene.Float(required=True)
	amount_spent = graphene.Float(required=True)

	def resolve_amount(self, info, **kwargs):
		return sum([it.amount for it in self.budget_items.all()])

	def resolve_amount_spent(self, info, **kwargs):
		amount = 0
		for it in self.budget_items.all():
			amount += sum([store.amount for store in it.stores.all()])
		return amount


class BudgetItemType(DjangoObjectType):
	class Meta:
		model = BudgetItem

	amount_spent = graphene.Float(required=True)

	def resolve_amount_spent(self, info, **kwargs):
		# Filter stores using 1st day of the month and current date
		today = date.today()
		first_day = today.replace(day=1)
		today = date.today()
		last_day = calendar.monthrange(today.year, today.month)[1]
		last_day_of_month = date(today.year, today.month, last_day)
		all_stores = self.stores.filter(action_date__gte=first_day, action_date__lte=last_day_of_month)
		return sum([store.amount for store in all_stores])


class BudgetDetailType(graphene.ObjectType):
	name = graphene.String()
	amount = graphene.Float()
	amount_spent = graphene.Float()
	description = graphene.String()
	start_date = graphene.Date()
	end_date = graphene.Date()
	status = graphene.String()
	budget_items = graphene.List(BudgetItemType)


class BehaviorType(DjangoObjectType):
	class Meta:
		model = Behavior


class PaginatorType(graphene.ObjectType):
	num_pages = graphene.Int()
	total_count = graphene.Int()


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


class BudgetItemInputType(graphene.InputObjectType):
	name = graphene.String()
	amount = graphene.Float()
	is_recurring = graphene.Boolean()


class StorePaginatorType(PaginatorType):
	page_data = graphene.List(StoreType)
	aggregate = graphene.Field(AggregatedInOutFlow)


class RecurringStorePaginatorType(PaginatorType):
	page_data = graphene.List(RecurringStoreType)


class BehaviorPaginatorType(PaginatorType):
	page_data = graphene.List(BehaviorType)


class HouseholdPaginatorType(PaginatorType):
	page_data = graphene.List(HouseholdType)


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


class SalaryPaginatorType(PaginatorType):
	page_data = graphene.List(SalaryType)


class BudgetPaginatorType(PaginatorType):
	page_data = graphene.List(BudgetType)
