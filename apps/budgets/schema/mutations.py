import graphene
from django.db import transaction
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from apps.budgets.models import Budget, BudgetItem, BudgetStatus, ItemActivation
from apps.budgets.owner import resolve_owner
from apps.budgets.schema.helpers import (
	clean_text, get_editable_item, get_owned_budget, to_money,
)
from apps.budgets.schema.types import AllocationInput, BudgetItemType, BudgetType
from apps.budgets.services import (
	change_status, ensure_editable, set_allocations, validate_budget,
)
from apps.stores.models import Store


def _allocations(raw):
	return [(a.item_id, to_money(a.amount)) for a in (raw or [])]


# --- budget items -------------------------------------------------------------------


class CreateBudgetItem(graphene.Mutation):
	"""Create an item for the owner, or a system item (admins, `isSystem: true`).
	Re-creating an archived item with the same name brings it back."""
	message = graphene.String()
	item = graphene.Field(BudgetItemType)

	class Arguments:
		name = graphene.String(required=True)
		description = graphene.String()
		default_amount = graphene.Float()
		is_system = graphene.Boolean(default_value=False)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, name, description=None, default_amount=None, is_system=False,
			household_id=None):
		user = info.context.user
		name = clean_text(name, 'name', max_length=100)
		if is_system:
			if not user.is_superuser:
				raise GraphQLError('Only administrators can create system budget items')
			scope = BudgetItem.objects.filter(user__isnull=True, household__isnull=True)
			item = BudgetItem()
		else:
			owner = resolve_owner(user, household_id)
			scope = BudgetItem.objects.filter(owner.filter())
			item = owner.assign(BudgetItem())

		if not is_system:
			common = BudgetItem.objects.filter(
				user__isnull=True, household__isnull=True, is_active=True, name__iexact=name).first()
			if common:
				raise GraphQLError(
					f"'{common.name}' is a common item. Switch it on under common items instead "
					"of creating your own copy.")
		existing = scope.filter(name__iexact=name).first()
		if existing and existing.is_active:
			raise GraphQLError(f"The budget item '{existing.name}' already exists")
		item = existing or item
		item.name = name
		item.is_active = True
		if description is not None or not existing:
			item.description = clean_text(description, 'description', required=False)
		if default_amount is not None:
			item.default_amount = to_money(default_amount, 'default amount')
		item.save()
		return CreateBudgetItem(message='Successfully saved', item=item)


class UpdateBudgetItem(graphene.Mutation):
	message = graphene.String()
	item = graphene.Field(BudgetItemType)

	class Arguments:
		id = graphene.ID(required=True)
		name = graphene.String()
		description = graphene.String()
		default_amount = graphene.Float()
		is_active = graphene.Boolean()
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, id, household_id=None, **fields):
		item = get_editable_item(info.context.user, id, household_id)
		if fields.get('name') is not None:
			name = clean_text(fields['name'], 'name', max_length=100)
			duplicate = BudgetItem.objects.filter(
				user=item.user, household=item.household, name__iexact=name).exclude(id=item.id)
			if duplicate.exists():
				raise GraphQLError(f"The budget item '{name}' already exists")
			item.name = name
		if fields.get('description') is not None:
			item.description = clean_text(fields['description'], 'description', required=False)
		if fields.get('default_amount') is not None:
			item.default_amount = to_money(fields['default_amount'], 'default amount')
		if fields.get('is_active') is not None:
			item.is_active = fields['is_active']
		item.save()
		return UpdateBudgetItem(message='Successfully updated', item=item)


class DeleteBudgetItem(graphene.Mutation):
	"""Delete an item. Items already used in budgets or transactions are archived instead,
	so history keeps its labels."""
	message = graphene.String()
	archived = graphene.Boolean()

	class Arguments:
		id = graphene.ID(required=True)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, id, household_id=None):
		item = get_editable_item(info.context.user, id, household_id)
		in_use = item.allocations.exists() or Store.all_objects.filter(item=item).exists()
		if in_use:
			item.is_active = False
			item.save(update_fields=['is_active'])
			return DeleteBudgetItem(message='Archived: the item is used in budgets or transactions',
				archived=True)
		item.hard_delete()
		return DeleteBudgetItem(message='Successfully deleted', archived=False)


class SetSystemItemEnabled(graphene.Mutation):
	"""Switch a system item on or off for the owner's account."""
	message = graphene.String()
	item = graphene.Field(BudgetItemType)

	class Arguments:
		item_id = graphene.ID(required=True)
		enabled = graphene.Boolean(required=True)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, item_id, enabled, household_id=None):
		owner = resolve_owner(info.context.user, household_id)
		item = BudgetItem.objects.filter(
			id=item_id, user__isnull=True, household__isnull=True, is_active=True).first()
		if item is None:
			raise GraphQLError('System budget item not found')
		activation = ItemActivation.objects.filter(owner.filter(), item=item).first()
		if activation is None:
			activation = owner.assign(ItemActivation(item=item))
		activation.enabled = enabled
		activation.save()
		item.enabled = enabled
		return SetSystemItemEnabled(
			message='Enabled' if enabled else 'Disabled', item=item)


# --- budgets ------------------------------------------------------------------------


class CreateBudget(graphene.Mutation):
	"""Create a budget for any period. It starts as a draft unless `status: "active"`."""
	message = graphene.String()
	budget = graphene.Field(BudgetType)

	class Arguments:
		name = graphene.String(required=True)
		description = graphene.String()
		start_date = graphene.Date(required=True)
		end_date = graphene.Date(required=True)
		allocations = graphene.List(graphene.NonNull(AllocationInput))
		status = graphene.String(default_value=BudgetStatus.DRAFT)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, name, start_date, end_date, description=None, allocations=None,
			status=BudgetStatus.DRAFT, household_id=None):
		user = info.context.user
		owner = resolve_owner(user, household_id)
		budget = owner.assign(Budget(
			name=clean_text(name, 'name', max_length=100),
			description=clean_text(description, 'description', required=False),
			start_date=start_date, end_date=end_date, status=BudgetStatus.DRAFT, created_by=user))
		with transaction.atomic():
			validate_budget(budget)
			budget.save()
			set_allocations(budget, _allocations(allocations))
			change_status(budget, status)
		return CreateBudget(message='Successfully saved', budget=budget)


class UpdateBudget(graphene.Mutation):
	"""Update a budget's details. Closed budgets must be reopened first."""
	message = graphene.String()
	budget = graphene.Field(BudgetType)

	class Arguments:
		id = graphene.ID(required=True)
		name = graphene.String()
		description = graphene.String()
		start_date = graphene.Date()
		end_date = graphene.Date()
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, id, household_id=None, **fields):
		budget = get_owned_budget(info.context.user, id, household_id)
		ensure_editable(budget)
		if fields.get('name') is not None:
			budget.name = clean_text(fields['name'], 'name', max_length=100)
		if fields.get('description') is not None:
			budget.description = clean_text(fields['description'], 'description', required=False)
		if fields.get('start_date') is not None:
			budget.start_date = fields['start_date']
		if fields.get('end_date') is not None:
			budget.end_date = fields['end_date']
		validate_budget(budget)
		budget.save()
		return UpdateBudget(message='Successfully updated', budget=budget)


class SetBudgetAllocations(graphene.Mutation):
	"""Replace the items and amounts a budget plans for."""
	message = graphene.String()
	budget = graphene.Field(BudgetType)

	class Arguments:
		budget_id = graphene.ID(required=True)
		allocations = graphene.List(graphene.NonNull(AllocationInput), required=True)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, budget_id, allocations, household_id=None):
		budget = get_owned_budget(info.context.user, budget_id, household_id)
		with transaction.atomic():
			set_allocations(budget, _allocations(allocations))
		return SetBudgetAllocations(message='Successfully saved', budget=budget)


class SetBudgetStatus(graphene.Mutation):
	"""draft → active → closed. Active budgets of one owner can't overlap."""
	message = graphene.String()
	budget = graphene.Field(BudgetType)

	class Arguments:
		id = graphene.ID(required=True)
		status = graphene.String(required=True)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, id, status, household_id=None):
		budget = get_owned_budget(info.context.user, id, household_id)
		change_status(budget, status)
		return SetBudgetStatus(message=f'Budget is now {budget.status}', budget=budget)


class CopyBudget(graphene.Mutation):
	"""Start a new draft budget for another period with the same items and amounts.
	Items the owner can no longer use are left out."""
	message = graphene.String()
	budget = graphene.Field(BudgetType)

	class Arguments:
		id = graphene.ID(required=True)
		name = graphene.String(required=True)
		start_date = graphene.Date(required=True)
		end_date = graphene.Date(required=True)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, id, name, start_date, end_date, household_id=None):
		user = info.context.user
		source = get_owned_budget(user, id, household_id)
		owner = resolve_owner(user, household_id)
		usable = set(owner.usable_items().values_list('id', flat=True))
		budget = owner.assign(Budget(
			name=clean_text(name, 'name', max_length=100), description=source.description,
			start_date=start_date, end_date=end_date, created_by=user))
		with transaction.atomic():
			validate_budget(budget)
			budget.save()
			set_allocations(budget, [
				(a.item_id, a.amount) for a in source.allocations.all() if a.item_id in usable])
		return CopyBudget(message='Successfully copied', budget=budget)


class DeleteBudget(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		id = graphene.ID(required=True)
		household_id = graphene.ID()

	@login_required
	def mutate(self, info, id, household_id=None):
		budget = get_owned_budget(info.context.user, id, household_id)
		with transaction.atomic():
			# Transactions are kept; they just no longer count toward a budget
			Store.all_objects.filter(budget=budget).update(budget=None)
			budget.delete()
		return DeleteBudget(message='Successfully deleted')


class BudgetMutations(graphene.ObjectType):
	create_budget_item = CreateBudgetItem.Field()
	update_budget_item = UpdateBudgetItem.Field()
	delete_budget_item = DeleteBudgetItem.Field()
	set_system_item_enabled = SetSystemItemEnabled.Field()
	create_budget = CreateBudget.Field()
	update_budget = UpdateBudget.Field()
	set_budget_allocations = SetBudgetAllocations.Field()
	set_budget_status = SetBudgetStatus.Field()
	copy_budget = CopyBudget.Field()
	delete_budget = DeleteBudget.Field()
