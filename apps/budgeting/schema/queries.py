from datetime import date

import graphene
from django.db.models import Q
from graphql_jwt.decorators import login_required

from app_utils.helpers import get_budgets_filter, paginate_data, is_valid_uuid
from app_utils.model_types.store import BudgetPaginatorType, BudgetDetailType, UserBudgetLineType, \
    DefaultBudgetLineType, BudgetLineType
from apps.budgeting.models import Budget, BudgetItem, DefaultBudgetLine, UserBudgetLine, UserDefaultBudgetLine
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
    current_budget = graphene.Field(
        BudgetDetailType, budget_id=graphene.String())
    default_budget_lines = graphene.List(DefaultBudgetLineType)
    user_budget_lines = graphene.List(
        UserBudgetLineType, active=graphene.Boolean())
    all_budget_lines = graphene.List(
        BudgetLineType, is_global_setup=graphene.Boolean(), is_app_setup=graphene.Boolean())

    @login_required
    def resolve_budgets(self, info, search_member='', page_count=10, page_number=1, **kwargs):
        user = info.context.user
        search_filter = get_budgets_filter(**kwargs)
        if search_member == '':
            budgets = User.get_user_budgets(user, search_filter)
        else:
            search_filter &= get_member_filter(user, search_member)
            budgets = Budget.objects.filter(search_filter)

        return paginate_data(budgets, page_count, page_number)

    @login_required
    def resolve_current_budget(self, info, budget_id=None):
        user = info.context.user
        search_filter = Q(user=user)
        if budget_id is not None and is_valid_uuid(budget_id):
            search_filter &= Q(id=budget_id)
        else:
            today = date.today()
            search_filter &= Q(start_date__lte=today,
                               end_date__gte=today, status='approved')

        budget = Budget.objects.filter(search_filter).first()
        recurring_items = []
        if budget is not None:
            recurring_items = list(budget.budget_items.all())
            _budget = budget.__dict__
            _budget['budget_items'] = recurring_items

            return _budget

        return {
            "name": budget.name if budget else "Not set",
            "budget_items": recurring_items
        }

    @login_required
    def resolve_default_budget_lines(self, info):
        return DefaultBudgetLine.objects.filter(active=True)

    @login_required
    def resolve_user_budget_lines(self, info, active=None):
        user = info.context.user
        filters = Q(user=user)
        if active is not None:
            filters &= Q(active=active)

        return UserBudgetLine.objects.filter(filters)

    @login_required
    def resolve_all_budget_lines(self, info, is_global_setup=False, is_app_setup=False):
        user = info.context.user
        is_setup = is_global_setup and user.is_superuser
        default_filter = Q() if is_setup else Q(enabled=True)
        default_lines = DefaultBudgetLine.objects.filter(default_filter)

        if is_setup:
            return [to_line_type(line, is_system=True) for line in default_lines]

        user_lines = UserBudgetLine.objects.filter(user=user)
        user_default_filter = Q(user=user) if is_app_setup else Q(
            user=user, enabled=True)
        user_default_lines = UserDefaultBudgetLine.objects.filter(
            user_default_filter).select_related('line')

        if is_app_setup:
            user_default_map = {udl.line.id: udl for udl in user_default_lines}
            default_line_types = []
            for dl in default_lines:
                # Find if there's a user default line for this default line
                udl = user_default_map.get(dl.id)
                if udl:
                    # If found, use its enabled status
                    udl.line.enabled = udl.enabled
                    default_line_types.append(
                        to_line_type(udl.line, is_system=True))
                else:
                    # If not found, use the default line as is
                    dl.enabled = False
                    default_line_types.append(to_line_type(dl, is_system=True))
        else:
            default_line_types = [
                to_line_type(udl.line, is_system=True) for udl in user_default_lines
            ]

        user_line_types = [to_line_type(line) for line in user_lines]
        return default_line_types + user_line_types


def to_line_type(line, is_system=False):
    return BudgetLineType(
        id=line.id,
        name=line.name,
        description=line.description,
        amount=0,
        is_system=is_system,
        enabled=line.enabled
    )
