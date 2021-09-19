from django.db import models
from django.utils.timezone import now

from apps.properties.models import Property
from d2dstore.models import BaseModel
from app_utils.constants import STORE_CHOICES
from apps.users.models import User


class Store(BaseModel):
	amount = models.FloatField()
	record_type = models.CharField(
		max_length=20,
		choices=STORE_CHOICES,
		default='use')
	is_property = models.BooleanField(default=False)
	is_inflow = models.BooleanField(default=False)
	description = models.CharField(max_length=200, default='*Home expense')
	action_date = models.DateField(blank=False, null=False, default=now)
	user = models.ForeignKey(User, related_name='stores', on_delete=models.PROTECT)
	property = models.ForeignKey(Property, on_delete=models.PROTECT, null=True)

	class Meta:
		db_table = "stores"
		ordering = ['-action_date']
		unique_together = ['description', 'action_date', 'user']

	def __str__(self):
		return self.description
