import graphene
from graphene import AbstractType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.model_types.store import HouseholdMemberType
from apps.household_members.models import HouseholdMember


class HouseholdQuery(AbstractType):
	my_house_hold_members = graphene.List(HouseholdMemberType)

	@login_required
	def resolve_my_house_hold_members(self, info):
		user = info.context.user
		household_member = HouseholdMember.objects.filter(user=user).first()
		if household_member is None:
			raise GraphQLError('No household set yet')
		return HouseholdMember.objects.filter(household=household_member.household)
