from django.db import models

# Create your models here.
from app_utils.constants import SALARY_TYPES
from d2dstore.models import BaseModel


class Salary(BaseModel):
	pension = models.FloatField()
	maternity = models.FloatField()
	tax = models.FloatField()
	net_salary = models.FloatField()
	gross_salary = models.FloatField()
	net_pay = models.FloatField()
	client_ip = models.CharField(max_length=20, default='')
	city = models.CharField(max_length=20, default='')
	country = models.CharField(max_length=20, default='')
	lat = models.CharField(max_length=20, default='')
	long = models.CharField(max_length=20, default='')

	class Meta:
		db_table = 'salaries'
		ordering = ['-created_at']


class Facility(BaseModel):
	is_constant = models.FloatField()
	amount = models.FloatField()
	percent_amount = models.FloatField()
	percent_field = models.FloatField()
	percent_field_type = models.CharField(max_length=20, choices=SALARY_TYPES, default='gs')
	salary = models.ForeignKey(Salary, related_name='facilities', on_delete=models.PROTECT, null=True)

	class Meta:
		db_table = 'facilities'
		ordering = ['-created_at']
