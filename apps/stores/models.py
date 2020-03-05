from django.db import models
from django.db.models import Q

from d2dstore.models import BaseModel
from app_utils.constants import STORE_CHOICES
from apps.user.models import User


class Store(BaseModel):
    amount = models.FloatField()
    record_type = models.CharField(
        max_length=20,
        choices=STORE_CHOICES,
        default='use')
    is_property = models.BooleanField(default=False)
    is_inflow = models.BooleanField(default=False)
    description = models.CharField(max_length=200, default='*Home expense')
    user = models.ForeignKey(User, related_name='stores', on_delete=models.CASCADE)

    def get_total(self, store_type='use', is_inflow=False):
        store_filter = (Q(record_type=store_type, is_inflow=is_inflow))
        total = sum([store.amount for store in self.objects.filter(store_filter)])
        return total
