from django.db import models
from d2dstore.models import BaseModel
from app_utils.constants import STORE_CHOICES
from apps.user.models import User


class Store(BaseModel):
    amount = models.FloatField()
    record_type = models.CharField(
        max_length=20,
        choices=STORE_CHOICES,
        default='Store')
    is_property = models.BooleanField(default=False)
    is_inflow = models.BooleanField(default=False)
    description = models.CharField(max_length=200, default='*Home expense')
    user = models.ForeignKey(User, related_name='store', on_delete=models.CASCADE)

    def get_total_in(self):
        pass
