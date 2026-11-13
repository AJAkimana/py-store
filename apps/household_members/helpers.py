from django.db.models import Q
from graphql import GraphQLError

from app_utils.database import get_model_object
from apps.household_members.models import HouseholdMember
from apps.households.models import Household


def get_member_filter(user, search_member):
	search_filter = Q()
	if search_member == 'all':
		member = HouseholdMember.objects.filter(user=user).first()
		if member is not None and member.access_level == 1:
			search_filter &= Q(household=member.household)
		else:
			# Only the household owner sees every member's records
			search_filter &= Q(user=user)
	else:
		household_member = HouseholdMember.objects.filter(user_id=search_member).first()
		if household_member is None:
			raise GraphQLError(f"The member is not found")
		user_membership = HouseholdMember.objects.filter(user=user, household=household_member.household).first()
		if user_membership is None:
			raise GraphQLError(f"You are not a family member of {household_member}")

		search_filter &= Q(user=user_membership.user)

	return search_filter


def get_user_household(user, household_id):
	"""Get a household by id, only if the user is one of its members."""
	user_households = Household.objects.filter(family__user=user, family__deleted_at=None)
	return get_model_object(Household, 'id', household_id, manager_query=user_households)
