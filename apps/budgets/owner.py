"""
Who a budget, budget item or activation belongs to.

All owner-dependent filtering goes through BudgetOwner, so turning on household
budgets later only means implementing the household branch of resolve_owner.
"""
from dataclasses import dataclass
from typing import Optional

from django.db.models import Q, QuerySet
from graphql import GraphQLError

from apps.households.models import Household
from apps.users.models import User


@dataclass(frozen=True)
class BudgetOwner:
	user: Optional[User] = None
	household: Optional[Household] = None

	def __post_init__(self):
		if (self.user is None) == (self.household is None):
			raise ValueError('A budget owner is exactly one of user or household')

	@property
	def is_household(self) -> bool:
		return self.household is not None

	def filter(self, prefix: str = '') -> Q:
		"""Rows owned by this owner (Budget, BudgetItem, ItemActivation)."""
		if self.user is not None:
			return Q(**{f'{prefix}user': self.user, f'{prefix}household__isnull': True})
		return Q(**{f'{prefix}household': self.household, f'{prefix}user__isnull': True})

	def store_filter(self) -> Q:
		"""Transactions that count toward this owner's budgets."""
		if self.user is not None:
			return Q(user=self.user)
		return Q(household=self.household)

	def assign(self, instance):
		"""Set the owner columns on a new Budget / BudgetItem / ItemActivation."""
		instance.user = self.user
		instance.household = self.household
		return instance

	def usable_items(self) -> QuerySet:
		"""Items this owner can budget for and tag transactions with:
		own active items plus the system items they have enabled."""
		from apps.budgets.models import BudgetItem

		enabled_system = Q(
			user__isnull=True, household__isnull=True,
			activations__enabled=True, activations__deleted_at__isnull=True,
		) & self.filter(prefix='activations__')
		return BudgetItem.objects.filter(
			Q(is_active=True) & (self.filter() | enabled_system)).distinct()


def resolve_owner(user: User, household_id: Optional[str] = None) -> BudgetOwner:
	"""The owner a request acts on. Omitting household_id means the user's own data."""
	if not household_id:
		return BudgetOwner(user=user)
	# Later: check HouseholdMember membership/access_level, then return BudgetOwner(household=...)
	raise GraphQLError('Household budgets are not available yet')
