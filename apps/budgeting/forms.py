from django.contrib.auth.forms import (
	UserChangeForm as BaseUserChangeForm,
	UserCreationForm as BaseUserCreationForm)
from apps.budgeting.models import Budget, BudgetItem


class BudgetForm:
	class Meta:
		model = Budget
		fields = ['name', 'description', 'status', 'start_date', 'end_date']
		error_class = "error"


class BudgetItemForm:
	class Meta:
		model = BudgetItem
		fields = ['name', 'amount', 'budget']
		error_class = "error"


class BudgetCreationForm(BaseUserCreationForm, BudgetForm):
	pass


class BudgetChangeForm(BaseUserChangeForm, BudgetForm):
	pass


class BudgetItemCreationForm(BaseUserCreationForm, BudgetItemForm):
	pass


class BudgetItemChangeForm(BaseUserChangeForm, BudgetItemForm):
	pass
