from django.db import models
from app_utils.constants import AMOUNT_TYPES
from apps.households.models import Household
from d2dstore.models import BaseModel
from apps.users.models import User


class Property(BaseModel):
	name = models.CharField(blank=False, max_length=50)
	price = models.FloatField(blank=False)
	description = models.CharField(max_length=255, default='Asset')
	cover_image = models.CharField(
		max_length=255, default='/images/products/product_1.png')
	owner = models.ForeignKey(
		User, related_name='properties', on_delete=models.CASCADE)
	is_active = models.BooleanField(default=True)
	household = models.ForeignKey(
		Household, related_name='properties', on_delete=models.PROTECT, null=True)

	def __str__(self):
		return self.name

	class Meta:
		db_table = "properties"
		ordering = ['name']
		unique_together = ['name', 'owner']
		verbose_name_plural = "Properties"

	def display_detail(self):
		"""Create a string for the property details. This is required to be displayed in Admin"""
		inflow = sum(
			[p_detail.amount for p_detail in self.prop_details.filter(type='in')])
		outflow = sum(
			[p_detail.amount for p_detail in self.prop_details.filter(type='out')])

		return f"{inflow if inflow > 0 else '-'}/{outflow if outflow > 0 else '-'}"

	display_detail.short_description = 'Transactions(IN/OUT)'


class PropDetail(BaseModel):
	title = models.CharField(max_length=255, blank=False)
	amount = models.FloatField(blank=False)
	type = models.CharField(choices=AMOUNT_TYPES,
													default='out', blank=False, max_length=10)
	property = models.ForeignKey(
		Property, related_name='prop_details', on_delete=models.PROTECT, null=True)

	def __str__(self):
		return self.title

	class Meta:
		ordering = ['title']
		db_table = "property_details"
		verbose_name_plural = "Property Details"
