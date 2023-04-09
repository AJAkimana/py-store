import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.model_types.store import HouseholdType
from apps.household_members.models import HouseholdMember
from apps.households.models import Household


class CreateEditHousehold(graphene.Mutation):
	message = graphene.String()
	household = graphene.Field(HouseholdType)

	class Arguments:
		name = graphene.String(required=True)
		description = graphene.String(required=True)

	def mutate(self, into, **kwargs):
		pass


class CreateHousehold(CreateEditHousehold):
	"""
	Mutation to create a household. Inherits from 'CreateEditHousehold' class
	"""

	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user
		has_created = HouseholdMember.objects.filter(user=user, household__name=kwargs['name']).first()
		if has_created:
			raise GraphQLError('You have already set a household')
		new_household = Household.objects.create(**kwargs)

		new_household.members.add(user, through_defaults={'access_level': 1})

		return CreateHousehold(message='Successfully saved', household=new_household)


class HouseholdMutations(graphene.ObjectType):
	create_household = CreateHousehold.Field()
