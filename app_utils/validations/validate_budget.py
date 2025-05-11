from graphql import GraphQLError

from app_utils.constants import BUDGET_STATUSES
from app_utils.database import SaveContextManager, query_runner
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

		conditions = f"""
			user_id='{budget.user.id}' AND (
				("start_date" BETWEEN '{budget.start_date}' AND '{budget.end_date}') OR
				("end_date" BETWEEN '{budget.start_date}' AND '{budget.end_date}') OR
				("start_date" < '{budget.start_date}' AND "end_date" > '{budget.end_date}')
			)
		"""
		if budget_id:
			conditions += f" AND id != '{budget_id}'"
		query = f"SELECT * FROM budgets WHERE {conditions} LIMIT 1"
		budgets = query_runner(pg_query=query)

		if len(budgets) == 1:
			raise GraphQLError(f"""The budget should not take place in the collision date as '{budgets[0]['name']}'""")

		with SaveContextManager(budget, model=Budget):
			return budget
