from django.db import models
from django.utils.timezone import now

from app_utils.constants import BUDGET_STATUSES
from d2dstore.models import BaseModel


class Budget(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	status = models.CharField(
		max_length=20,
		choices=BUDGET_STATUSES,
		default='draft'
	)
	start_date = models.DateField(blank=False, null=False, default=now)
	end_date = models.DateField(blank=False, null=False, default=now)


class BudgetItem(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	amount = models.FloatField()
