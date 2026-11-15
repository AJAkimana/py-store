"""
GraphQL types for budgeting.

Plain ObjectTypes (not DjangoObjectType) on purpose: registering the models with
graphene-django would add reverse fields such as `ownedBudgets` to UserType and
HouseholdType and expose budgets wherever a user or household is shown.
Money is returned as Float, which is what the UI expects.
"""
import graphene

from apps.budgets.services import allocations_with_spending, budget_totals


def _money(value):
	return float(value) if value is not None else 0.0


class BudgetItemType(graphene.ObjectType):
	id = graphene.ID(required=True)
	name = graphene.String(required=True)
	description = graphene.String()
	default_amount = graphene.Float()
	is_active = graphene.Boolean()
	is_system = graphene.Boolean(description='Managed by admins; users enable it for their account.')
	enabled = graphene.Boolean(
		description="Whether the owner can use it: their own active items, or system items they enabled.")

	def resolve_default_amount(item, info):
		return _money(item.default_amount)

	def resolve_enabled(item, info):
		# Set by the resolver that knows the owner (see queries); own items fall back to is_active.
		return getattr(item, 'enabled', item.is_active)


class BudgetAllocationType(graphene.ObjectType):
	id = graphene.ID(required=True)
	item = graphene.Field(BudgetItemType, required=True)
	amount = graphene.Float()
	spent = graphene.Float()
	remaining = graphene.Float()

	def resolve_amount(allocation, info):
		return _money(allocation.amount)

	def resolve_spent(allocation, info):
		return _money(getattr(allocation, 'spent', 0))

	def resolve_remaining(allocation, info):
		return _money(getattr(allocation, 'remaining', allocation.amount))


class BudgetType(graphene.ObjectType):
	id = graphene.ID(required=True)
	name = graphene.String(required=True)
	description = graphene.String()
	start_date = graphene.Date()
	end_date = graphene.Date()
	status = graphene.String(description='draft | active | closed')
	is_household = graphene.Boolean()
	allocated = graphene.Float(description='Total planned across items')
	spent = graphene.Float(description='Expenses on planned items within the period')
	remaining = graphene.Float()
	unbudgeted = graphene.Float(
		description='Expenses within the period on items not in this budget, or untagged')
	allocations = graphene.List(graphene.NonNull(BudgetAllocationType), required=True)

	@staticmethod
	def _totals(budget):
		if not hasattr(budget, '_totals_cache'):
			budget._totals_cache = budget_totals(budget)
		return budget._totals_cache

	def resolve_is_household(budget, info):
		return budget.household_id is not None

	def resolve_allocated(budget, info):
		return _money(BudgetType._totals(budget)['allocated'])

	def resolve_spent(budget, info):
		return _money(BudgetType._totals(budget)['spent'])

	def resolve_remaining(budget, info):
		return _money(BudgetType._totals(budget)['remaining'])

	def resolve_unbudgeted(budget, info):
		return _money(BudgetType._totals(budget)['unbudgeted'])

	def resolve_allocations(budget, info):
		return allocations_with_spending(budget)


class BudgetPaginatorType(graphene.ObjectType):
	num_pages = graphene.Int()
	total_count = graphene.Int()
	page_data = graphene.List(graphene.NonNull(BudgetType))


class AllocationInput(graphene.InputObjectType):
	item_id = graphene.ID(required=True)
	amount = graphene.Float(required=True)
