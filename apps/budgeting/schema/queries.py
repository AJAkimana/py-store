import graphene
from graphql_jwt.decorators import login_required

from app_utils.database import get_model_object
from app_utils.helpers import get_budgets_filter, paginate_data
from app_utils.model_types.store import BudgetPaginatorType, BudgetType
from apps.budgeting.models import Budget
from apps.household_members.helpers import get_member_filter
from apps.users.models import User


class BudgetingQuery(graphene.ObjectType):
	budgets = graphene.Field(
		BudgetPaginatorType,
		search_key=graphene.String(),
		search_start_date=graphene.String(),
		search_end_date=graphene.String(),
		page_count=graphene.Int(),
		page_number=graphene.Int(),
		search_member=graphene.String()
	)
	budget_details = graphene.Field(BudgetType, budget_id=graphene.String(required=True))

	@login_required
	def resolve_budgets(self, info, search_member='', page_count=10, page_number=10, **kwargs):
		user = info.context.user
		search_filter = get_budgets_filter(**kwargs)
		if search_member == '':
			budgets = User.get_user_budgets(user, search_filter)
		else:
			search_filter &= get_member_filter(user, search_member)
			budgets = Budget.objects.filter(search_filter)

		return paginate_data(budgets, page_count, page_number)

	@login_required
	def resolve_budget_details(self, info, budget_id=''):
		user = info.context.user
		budget = get_model_object(Budget, 'id', budget_id)
		# Add budget validation

		return budget
