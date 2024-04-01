import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.database import get_model_object
from app_utils.model_types.store import BudgetItemInputType, BudgetType
from app_utils.validations.validate_budget import ValidateBudget
from apps.budgeting.models import Budget, BudgetItem
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

		# if budget.status == 'approved' and budget.budget_items == 0:
		# 	raise GraphQLError('Add at least one item')
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
			has_saved = BudgetItem.objects.filter(
				name=item['name'],
				amount=item['amount'], budget=budget).first()
			if not has_saved:
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


class BudgetMutations(graphene.ObjectType):
	create_budget = CreateBudget.Field()
	update_budget = UpdateBudget.Field()
	create_budget_items = CreateBudgetItems.Field()
