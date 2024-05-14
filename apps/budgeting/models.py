from django.db import models
from django.utils.timezone import now

from app_utils.constants import BUDGET_STATUSES
from apps.households.models import Household
from apps.users.models import User
from d2dstore.models import BaseModel


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


class BudgetItem(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	amount = models.FloatField()
	budget = models.ForeignKey(
		Budget,
		related_name='budget_items',
		on_delete=models.PROTECT
	)

	class Meta:
		db_table = "budget_items"
		ordering = ['name']
		unique_together = ['name', 'amount', 'budget']
