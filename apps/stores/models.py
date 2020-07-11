from django.db import models
from django.db.models import Q
from django.utils.timezone import now

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
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ['action_date']

    def get_total(self, store_type='use', is_inflow=False):
        store_filter = (Q(record_type=store_type, is_inflow=is_inflow))
        total = sum([store.amount for store in self.objects.filter(store_filter)])
        return total

