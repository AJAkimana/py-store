from django.db.models import Q
from graphql import GraphQLError

from app_utils.constants import BUDGET_STATUSES
from app_utils.database import SaveContextManager
from apps.budgeting.models import Budget


class ValidateBudget:
	def __init__(self, **budget_body: Budget):
		self.budget = budget_body

	def validate_and_save(self, budget: Budget):
		"""
    Args:
      budget: The store instance

    Returns: new updated budget after it has been saved into database
    """
		budget_id = self.budget.get('id', None)
		for key, value in self.budget.items():
			if isinstance(value, str) and value.strip() == '':
				raise GraphQLError(f"The {key} field can't be empty")
			if key == 'id':
				continue
			setattr(budget, key, value)

		status = [item for item in BUDGET_STATUSES if item[0] == self.budget['status']]
		if not status:
			raise GraphQLError('Invalid budget status')

		filters = Q(
			name=budget.name if budget.name else self.budget['name'],
			user=budget.user
		)
		if budget_id:
			filters = (~Q(id=budget_id) & filters)

		has_saved = Budget.objects.filter(filters).first()
		if has_saved:
			raise GraphQLError('The record has already been recorded')

		with SaveContextManager(budget, model=Budget):
			return budget
