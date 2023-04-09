from django.db import models

from apps.users.models import User
from d2dstore.models import BaseModel


class Household(BaseModel):
	name = models.CharField(blank=False, max_length=255, default='Our house')
	description = models.CharField(
		blank=False, max_length=255, default='Our family')
	created_by = models.ForeignKey(User, related_name='creator', on_delete=models.PROTECT, null=True)
	members = models.ManyToManyField(User, through='household_members.HouseholdMember')

	def __str__(self):
		return self.name

	class Meta:
		db_table = "households"
		ordering = ['name']
