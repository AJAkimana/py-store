from django.db.models import Q
from graphql import GraphQLError

from apps.household_members.models import HouseholdMember


def get_member_filter(user, search_member):
	search_filter = Q()
	if search_member == 'all':
		member = HouseholdMember.objects.filter(user=user).first()
		if member.access_level == 1:
			search_filter &= Q(household=member.household)
	else:
		household_member = HouseholdMember.objects.filter(user_id=search_member).first()
		if household_member is None:
			raise GraphQLError(f"The member is not found")
		user_membership = HouseholdMember.objects.filter(user=user, household=household_member.household).first()
		if user_membership is None:
			raise GraphQLError(f"You are not a family member of {household_member}")

		search_filter &= Q(user=user_membership.user)

	return search_filter
