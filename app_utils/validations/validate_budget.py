from graphql import GraphQLError

from app_utils.constants import BUDGET_STATUSES
from app_utils.database import SaveContextManager, query_runner, get_model_object
from django.db import transaction
from app_utils.validations.base_validator import BaseValidator
from apps.budgeting.models import Budget, DefaultBudgetLine, UserBudgetLine, BudgetItem


class ValidateBudget:
  def __init__(self, **budget_body:Budget):
    self.budget = budget_body

  def validate_and_save(self, budget:Budget):
    """
    Args:
      budget: The store instance

    Returns: new updated budget after it has been saved into database
    """
    # Validate and assign budget fields
    budget_id = self.budget.get('id', None)
    for key, value in self.budget.items():
      if isinstance(value, str) and value.strip() == '':
        raise GraphQLError(f"The {key} field can't be empty")
      # don't set items here; handled separately
      if key in ('id', 'items'):
        continue
      setattr(budget, key, value)

    # Validate status
    status = [
	    item for item in BUDGET_STATUSES if item[0] == getattr(self.budget, 'status', self.budget.get('status'))
    ]
    if not status:
      raise GraphQLError('Invalid budget status')

    # Check date collisions for same user
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

    if len(budgets) > 0:
      raise GraphQLError(f"The budget should not take place in the collision date as '{budgets[0]['name']}'")

    # Save budget (create or update)
    with SaveContextManager(budget, model=Budget):
      # budget is saved and has an id now
      pass

    # Handle items if provided in payload
    items_payload = self.budget.get('items', None)
    if items_payload is None:
      return budget

    # Basic items validation
    self.validate()
    # Ensure we work in a transaction for items operations
    with transaction.atomic():
      # Refresh items queryset
      existing_items = {
        itm.id: itm for itm in budget.budget_items.all()
      } if budget.id else {}
      incoming_ids = set([i.get('id') for i in items_payload if i.get('id')])

      # Determine deletes: existing ids not present in incoming
      to_delete_ids = set(existing_items.keys()) - incoming_ids
      self.delete_items(list(to_delete_ids))

      # Split incoming into create and update
      to_create = [i for i in items_payload if not i.get('id')]
      to_update = [i for i in items_payload if i.get('id')]

      self.create_items(budget, to_create)
      self.edit_items(budget, to_update)

    return budget

  def validate(self):
    """Validate budget body and items (basic checks)."""
    # budget-level basic validation already applied in validate_and_save
    items = self.budget.get('items', [])
    for idx, item in enumerate(items):
      if not item.get('name') or str(item.get('name')).strip() == '':
        raise GraphQLError(f"Item at index {idx} must have a name")
      amount = item.get('amount')
      try:
        amount_f = float(amount)
      except Exception:
        raise GraphQLError(f"Item '{item.get('name')}' has invalid amount")
      if amount_f < 0:
        raise GraphQLError(f"Item '{item.get('name')}' amount must be non-negative")

  def create_items(self, budget: Budget, items: list):
    """Create new BudgetItem instances and attach to budget."""
    for item in items:
      bi = BudgetItem()
      bi.name = item.get('name')
      bi.amount = item.get('amount', 0)
      bi.is_recurring = item.get('is_recurring', False)
      bi.budget = budget
      # Optionally set relations if provided
      if item.get('user'):
        bi.user_id = item.get('user')
      if item.get('u_budget_line'):
        bi.u_budget_line_id = item.get('u_budget_line')
      if item.get('d_budget_line'):
        bi.d_budget_line_id = item.get('d_budget_line')
      with SaveContextManager(bi, model=BudgetItem):
        pass

  def edit_items(self, budget: Budget, items: list):
    """Update existing BudgetItem instances based on incoming payload."""
    for item in items:
      item_id = item.get('id')
      if not item_id:
        continue
      bi = get_model_object(BudgetItem, 'id', item_id)
      # ensure belongs to budget
      if bi.budget_id != budget.id:
        raise GraphQLError(f"Item id {item_id} does not belong to this budget")
      # update fields
      for key in ('name', 'amount', 'is_recurring'):
        if key in item:
          setattr(bi, key, item.get(key))
      # relations
      if 'user' in item:
        bi.user_id = item.get('user')
      if 'u_budget_line' in item:
        bi.u_budget_line_id = item.get('u_budget_line')
      if 'd_budget_line' in item:
        bi.d_budget_line_id = item.get('d_budget_line')
      with SaveContextManager(bi, model=BudgetItem):
        pass

  def delete_items(self, ids: list):
    """Delete BudgetItem instances by ids."""
    for iid in ids:
      bi = get_model_object(BudgetItem, 'id', iid)
      # deletion; rely on model delete (perhaps soft-delete)
      bi.delete()


class ValidateDefaultBudgetLine(BaseValidator):
  def validate_and_save(self, budget_line: DefaultBudgetLine):
    self.check_empty_fields(exclude=['id'])

    self.check_duplicate(filter_fields=['name'])
    with SaveContextManager(budget_line, model=DefaultBudgetLine):
      return budget_line


class ValidateUserBudgetLine(BaseValidator):
  def validate_and_save(self, budget_line: UserBudgetLine):
    self.check_empty_fields(exclude=['id'])

    self.check_duplicate(filter_fields=['name', 'user'])
    with SaveContextManager(budget_line, model=UserBudgetLine):
      return budget_line
