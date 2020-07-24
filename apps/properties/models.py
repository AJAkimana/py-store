from django.db import models
from app_utils.constants import AMOUNT_TYPES
from d2dstore.models import BaseModel
from apps.users.models import User


class Property(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	price = models.FloatField(blank=False)
	owner = models.ForeignKey(User, related_name='properties', on_delete=models.CASCADE)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return self.name

	class Meta:
		ordering = ['name']


class PropDetail(BaseModel):
	title = models.CharField(max_length=255, blank=False)
	amount = models.FloatField(blank=False)
	type = models.CharField(choices=AMOUNT_TYPES, default='out', blank=False, max_length=10)
	property = models.ForeignKey(Property, on_delete=models.CASCADE)

	def __str__(self):
		return self.title

	class Meta:
		ordering = ['title']