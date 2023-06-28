from django.db import models

# Create your models here.
from django.db import models

from app_utils.constants import MEMBER_ACCESS_LEVELS
from apps.households.models import Household
from d2dstore.models import BaseModel
from apps.users.models import User


class HouseholdMember(BaseModel):
    user = models.ForeignKey(
        User, related_name='member', on_delete=models.PROTECT)
    household = models.ForeignKey(
        Household, related_name='family', on_delete=models.PROTECT)
    access_level = models.FloatField(choices=MEMBER_ACCESS_LEVELS, default=3)

    def __str__(self):
        return f'''{self.user.email}=>{self.household.name}'''

    class Meta:
        db_table = 'household_members'
        ordering = ['access_level']
        unique_together = ['user', 'household']
