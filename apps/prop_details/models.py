from django.db import models
from d2dstore.models import BaseModel
from app_utils.constants import AMOUNT_TYPES
from apps.properties.models import Property


class PropDetails(BaseModel):
	title = models.CharField(max_length=255, blank=False)
	amount = models.FloatField(blank=False)
	type = models.CharField(choices=AMOUNT_TYPES, default='out', blank=False, max_length=10)
	property = models.ForeignKey(Property, on_delete=models.CASCADE)

	def __str__(self):
		return self.title

	class Meta:
		ordering = ['title']
