import graphene
from graphene import AbstractType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required, superuser_required

from app_utils.model_types.store import HouseholdMemberType, HouseholdType
from apps.household_members.models import HouseholdMember
from apps.households.models import Household


class HouseholdQuery(AbstractType):
	my_household_memberships = graphene.List(HouseholdMemberType)
	households = graphene.List(HouseholdType)

	@login_required
	def resolve_my_household_memberships(self, info):
		user = info.context.user
		household_members = HouseholdMember.objects.filter(user=user)
		if len(household_members) == 0:
			raise GraphQLError('No household set yet')
		return household_members

	@superuser_required
	def resolve_households(self, info):
		return Household.objects.all()
