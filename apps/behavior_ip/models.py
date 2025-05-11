from django.db import models

# Create your models here.
from django.utils.timezone import now

from app_utils.constants import BEHAVIOR_CHOICES
from apps.households.models import Household
from apps.users.models import User
from d2dstore.models import BaseModel


class Behavior(BaseModel):
	name = models.CharField(blank=False, max_length=200)
	description = models.CharField(blank=False, max_length=255, null=True)
	weight = models.FloatField(default=100)
	user = models.ForeignKey(
		User,
		related_name='behaviors',
		on_delete=models.PROTECT,
		null=True
	)
	household = models.ForeignKey(
		Household,
		related_name='behaviors',
		on_delete=models.PROTECT,
		null=True
	)

	class Meta:
		db_table = "behaviors"
		ordering = ['-created_at']
		unique_together = ['name', 'user']

	def __str__(self):
		return f'{self.name}({self.weight})'


class BehaviorScore(BaseModel):
	action_date = models.DateField(blank=False, null=False, default=now)
	score = models.FloatField()
	description = models.CharField(blank=False, max_length=255, null=True)
	rate = models.CharField(
		max_length=20,
		choices=BEHAVIOR_CHOICES,
		default='good'
	)
	behavior = models.ForeignKey(
		Behavior,
		related_name='scores',
		on_delete=models.PROTECT
	)

	class Meta:
		db_table = "behavior_scores"

	def __str__(self):
		return f'{self.behavior}=>{self.score}=>{self.action_date}'
