from django.db import models
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
