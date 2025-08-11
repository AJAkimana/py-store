from django.db import models
from django.utils.timezone import now

from app_utils.constants import BUDGET_STATUSES
from apps.households.models import Household
from apps.users.models import User
from d2dstore.models import BaseModel


class DefaultBudgetLine(BaseModel):
	"""System-wide default budget line templates for new users to pick."""
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	active = models.BooleanField(default=True)

	class Meta:
		db_table = "default_budget_lines"
		ordering = ['name']
		unique_together = ['name']

	def __str__(self):
		return self.name


class UserBudgetLine(BaseModel):
	"""User-specific recurring budget lines (user’s default lines)."""
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	active = models.BooleanField(default=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	user = models.ForeignKey(User, related_name='user_budget_lines', on_delete=models.PROTECT)


	class Meta:
		db_table = "user_budget_lines"
		ordering = ['name']
		unique_together = ['name', 'user']

	def __str__(self):
		return self.name


class Budget(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	description = models.CharField(blank=False, max_length=200, null=True)
	status = models.CharField(
		max_length=20,
		choices=BUDGET_STATUSES,
		default='draft'
	)
	start_date = models.DateField(blank=False, null=False, default=now)
	end_date = models.DateField(blank=False, null=False, default=now)
	user = models.ForeignKey(
		User,
		related_name='budgets',
		on_delete=models.PROTECT,
		null=True
	)
	household = models.ForeignKey(
		Household,
		related_name='budgets',
		on_delete=models.PROTECT,
		null=True
	)

	class Meta:
		db_table = "budgets"
		ordering = ['-start_date']
		unique_together = ['name', 'user']

	def __str__(self):
		return f'{self.name}=>({self.user})'


class BudgetItem(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	amount = models.FloatField()
	budget = models.ForeignKey(
		Budget,
		related_name='budget_items',
		on_delete=models.PROTECT,
		null=True
	)
	is_recurring = models.BooleanField(default=False)
	user = models.ForeignKey(
		User,
		related_name='user_budget_items',
		on_delete=models.PROTECT,
		null=True
	)
	u_budget_line = models.ForeignKey(
		UserBudgetLine, null=True, blank=True,
		related_name='u_budget_items',
		on_delete=models.PROTECT
	)
	d_budget_line = models.ForeignKey(
		DefaultBudgetLine,
		null=True, blank=True,
		related_name='d_budget_items',
		on_delete=models.PROTECT
	)

	class Meta:
		db_table = "budget_items"
		ordering = ['name']
		unique_together = ['name', 'amount', 'budget']

	def __str__(self):
		return f'{self.name}=>{self.amount}'
