from django.db import models
from d2dstore.models import BaseModel
from apps.users.models import User


class House(BaseModel):
	name = models.CharField(blank=False, max_length=255, default='Our house')
	owner = models.ForeignKey(User, on_delete=models.CASCADE)

	def __str__(self):
		return self.name

	class Meta:
		ordering = ['name']
