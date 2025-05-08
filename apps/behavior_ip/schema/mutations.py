import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.database import get_model_object
from app_utils.model_types.store import BehaviorType
from app_utils.validations.validate_behavior import ValidateBehavior
from apps.behavior_ip.models import Behavior
from apps.households.models import Household


class CreateEditBehavior(graphene.Mutation):
	message = graphene.String()
	behavior = graphene.Field(BehaviorType)

	class Arguments:
		name = graphene.String(required=True)
		rate = graphene.String(required=False)
		household_id = graphene.String(required=False)
		action_date = graphene.Date(required=True)

	def mutate(self, into, **kwargs):
		pass


class EvaluateBehavior(CreateEditBehavior):
	"""
	Mutation to create a budget. Inherits from 'CreateEditBehavior' class
	"""
	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user

		household = get_model_object(Household, 'id', kwargs['household_id'])
		behavior = Behavior(user=user, household=household)
		validator = ValidateBehavior(**kwargs)

		new_behavior = validator.validate_and_save(behavior)

		return CreateEditBehavior(message='Successfully saved', behavior=new_behavior)


class BehaviorMutations(graphene.ObjectType):
	evaluateBehavior = EvaluateBehavior.Field()
