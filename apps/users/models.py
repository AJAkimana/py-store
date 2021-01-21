import uuid
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import gettext_lazy as _

from apps.users.manager import UserManager


class User(AbstractBaseUser, PermissionsMixin):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	first_name = models.CharField(max_length=50, blank=False)
	last_name = models.CharField(max_length=50, blank=False)
	middle_name = models.CharField(max_length=50)
	user_name = models.CharField(max_length=50, unique=True, blank=False)
	phone = models.CharField(max_length=50, blank=True)
	profile_picture = models.CharField(max_length=255, null=True)
	email = models.EmailField(_('email address'), unique=True)
	is_staff = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	previous_passwords = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True, null=True)
	updated_at = models.DateTimeField(auto_now=True, null=True)

	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = []

	objects = UserManager()

	def __str__(self):
		return f'{self.first_name} {self.last_name}'

	def get_previous_passwords(self):
		return self.previous_passwords.split(',')

	def get_user_stores(self):
		return self.stores.all()

	def get_store_total_amount(self, store_type='use', is_inflow=True):
		store_filter = (Q(record_type=store_type, is_inflow=is_inflow))
		total = sum([store.amount for store in self.stores.filter(store_filter)])
		return total

	def get_store_aggregate(self, store_type='use'):
		percent = 0
		inflow = self.get_store_total_amount(store_type=store_type)
		outflow = self.get_store_total_amount(store_type=store_type, is_inflow=False)
		properties_total_value = self.get_properties_total_value(active=False)
		total_expenses = outflow + properties_total_value

		if inflow != 0:
			percent = (total_expenses / inflow) * 100

		record = {'inflow': inflow, 'outflow': total_expenses, 'percent': round(percent, 2)}
		return record

	def get_user_properties(self, active='all'):
		if active == 'all':
			return self.properties.all()

		q_filter = Q(is_active=active)
		return self.properties.filter(q_filter)

	def get_properties_total_value(self, active='all'):
		total = sum([prop.price for prop in self.get_user_properties(active=active)])
		return total
