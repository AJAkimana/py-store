import graphene
from django.db.models import Q
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.database import get_model_object
from app_utils.model_types.store import BudgetItemInputType, BudgetType, BudgetLineType
from app_utils.validations.validate_budget import ValidateBudget
from apps.budgeting.models import Budget, BudgetItem, DefaultBudgetLine, UserBudgetLine
from apps.households.models import Household


class CreateEditBudget(graphene.Mutation):
	message = graphene.String()
	budget = graphene.Field(BudgetType)

	class Arguments:
		name = graphene.String(required=True)
		status = graphene.String(required=False)
		start_date = graphene.Date(required=True)
		end_date = graphene.Date(required=True)
		description = graphene.String(required=False)
		household_id = graphene.String(required=True)
		items = graphene.List(BudgetItemInputType)

	def mutate(self, into, **kwargs):
		pass


class CreateBudget(CreateEditBudget):
	"""
	Mutation to create a budget. Inherits from 'CreateEditBudget' class
	"""
	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user

		household = get_model_object(Household, 'id', kwargs['household_id'])
		budget = Budget(user=user, household=household)
		validator = ValidateBudget(**kwargs)

		new_budget = validator.validate_and_save(budget)

		return CreateBudget(message='Successfully saved', budget=new_budget)


class UpdateBudget(CreateEditBudget):
	"""
	Mutation to update a budget. Inherits from 'CreateEditBudget' class
	"""
	class Arguments(CreateEditBudget.Arguments):
		id = graphene.String(required=True)
		name = graphene.String(required=False)
		start_date = graphene.Date(required=False)
		end_date = graphene.Date(required=False)
		household_id = graphene.String(required=False)

	@login_required
	def mutate(self, info, **kwargs):
		budget = get_model_object(Budget, 'id', kwargs.get('id'))
		validator = ValidateBudget(**kwargs)

		if kwargs['status'] == 'approved' and len(budget.budget_items.all()) == 0:
			raise GraphQLError('Add at least one item')
		updated_budget = validator.validate_and_save(budget)
		return UpdateBudget(message='Successfully update', budget=updated_budget)


class CreateBudgetItems(graphene.Mutation):
	message = graphene.String()
	total_saved = graphene.Int()
	total_not_saved = graphene.Int()

	class Arguments:
		items = graphene.List(BudgetItemInputType)
		budget_id = graphene.String()

	@login_required
	def mutate(self, info, **kwargs):
		budget = get_model_object(Budget, 'id', kwargs['budget_id'])
		saved = 0
		not_saved = 0

		if budget.status == 'approved':
			raise GraphQLError("You can add items to the approved budget")
		for item in kwargs['items']:
			item['user_id'] = info.context.user.id
			has_saved = BudgetItem.objects.filter(
				name=item['name'],
				amount=item['amount'], user=budget.user).first()
			if not has_saved:
				if not item['is_recurring']:
					item['budget_id'] = kwargs['budget_id']
				BudgetItem(**item).save()
				saved += 1
			else:
				not_saved += 1

		return CreateBudgetItems(
			message="Success",
			total_saved=saved,
			total_not_saved=not_saved
		)


class CreateBudgetLine(graphene.Mutation):
	message = graphene.String()
	budget_line = graphene.Field(BudgetLineType)

	class Arguments:
		name = graphene.String(required=True)
		description = graphene.String(required=False)
		amount = graphene.Float(required=False)
		active = graphene.Boolean(required=False)
		is_system = graphene.Boolean(required=False)

	@login_required
	def mutate(self, info, is_system,  **kwargs):
		user = info.context.user
		name = kwargs.get('name', '')
		if not name.strip():
			raise GraphQLError("The 'name' field can't be empty")

		name = name.strip().capitalize()
		BudgetLine = DefaultBudgetLine if is_system else UserBudgetLine
		filters = Q(name=name)
		if not is_system:
			filters &= Q(user=user)
		budget_line = BudgetLine.objects.filter(filters).first()

		if budget_line:
			if budget_line.active:
				raise GraphQLError(f"The budget line with name '{name}' already exists")
			else:
				budget_line.active = True
				budget_line.enabled = True
				budget_line.save()
		else:
			budget_line = BudgetLine(
				name=name,
				description=kwargs.get('description', kwargs['name']),
				active=kwargs.get('active', True),
			)
			if not is_system:
				budget_line.user = info.context.user
				budget_line.amount = kwargs.get('amount', 0.0)
			budget_line.save()

		return CreateBudgetLine(
			message='Successfully saved',
			budget_line=BudgetLineType(
				id=budget_line.id,
				name=budget_line.name,
				description=budget_line.description,
				amount=0.0 if is_system else budget_line.amount,
				is_system=is_system,
				enabled=budget_line.enabled
			)
		)


class DeleteBudgetLine(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		id = graphene.String(required=True)
		is_system = graphene.Boolean(required=True)

	@login_required
	def mutate(self, info, id, is_system=False, **kwargs):
		BudgetLine = DefaultBudgetLine if is_system else UserBudgetLine
		budget_line = get_model_object(BudgetLine, 'id', id)
		if not budget_line:
			raise GraphQLError('Budget line not found')
		budget_filter = Q(d_budget_line__id=id) if is_system else Q(u_budget_line__id=id)
		budget_items = BudgetItem.objects.filter(budget_filter)
		if budget_items.exists():
			budget_line.active = False
			budget_line.enabled = False
			budget_line.save()
		else:
			budget_line.hard_delete()
		return DeleteBudgetLine(message='Successfully deleted')


class EnableBudgetLine(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		id = graphene.String(required=True)
		is_system = graphene.Boolean(required=True)

	@login_required
	def mutate(self, info, id, is_system=False, **kwargs):
		BudgetLine = DefaultBudgetLine if is_system else UserBudgetLine
		budget_line = get_model_object(BudgetLine, 'id', id)
		if not budget_line:
			raise GraphQLError('Budget line not found')
		budget_line.enabled = not budget_line.enabled
		budget_line.save()
		return EnableBudgetLine(message='Successfully enabled')

class BudgetMutations(graphene.ObjectType):
	create_budget = CreateBudget.Field()
	update_budget = UpdateBudget.Field()
	create_budget_items = CreateBudgetItems.Field()
	create_budget_line = CreateBudgetLine.Field()
	delete_budget_line = DeleteBudgetLine.Field()
	enable_budget_line = EnableBudgetLine.Field()
