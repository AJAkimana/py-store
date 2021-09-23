from django.db import models

# Create your models here.
from d2dstore.models import BaseModel


class Salary(BaseModel):
  pension = models.FloatField()
  maternity = models.FloatField()
  tax = models.FloatField()
  net_salary = models.FloatField()
  gross_salary = models.FloatField()
  net_pay = models.FloatField()

  class Meta:
    db_table = 'salaries'
    ordering = ['-created_at']


class Facility(BaseModel):
  is_constant = models.FloatField()
  amount = models.FloatField()
  percent_amount = models.FloatField()
  percent_field = models.FloatField()

  class Meta:
    db_table = 'facilities'
    ordering = ['-created_at']
