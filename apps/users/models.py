import uuid
from typing import Dict, Any

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import gettext_lazy as _

from apps.users.manager import UserManager
from d2dstore.models import BaseModel


class User(AbstractBaseUser, PermissionsMixin):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	first_name = models.CharField(max_length=50, blank=False)
	last_name = models.CharField(max_length=50, blank=False)
	middle_name = models.CharField(max_length=50)
	user_name = models.CharField(max_length=50, unique=True, blank=False)
	phone = models.CharField(max_length=50, unique=True, blank=False)
	profile_picture = models.CharField(max_length=255, null=True)
	email = models.EmailField(_('email address'), unique=True)
	is_staff = models.BooleanField(default=False)
	is_active = models.BooleanField(default=True)
	is_verified = models.BooleanField(default=True)
	previous_passwords = models.TextField()
	# household = models.ForeignKey(Household, related_name='members', on_delete=models.PROTECT, null=True)
	created_at = models.DateTimeField(auto_now_add=True, null=True)
	updated_at = models.DateTimeField(auto_now=True, null=True)

	USERNAME_FIELD = 'email'
	REQUIRED_FIELDS = []

	objects = UserManager()

	class Meta:
		db_table = "users"

	def __str__(self):
		return f'{self.first_name} {self.last_name}'

	def get_previous_passwords(self):
		return self.previous_passwords.split(',')

	def get_user_stores(self, filters: Dict[str, Any]):
		return self.stores.filter(filters)

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

	def get_user_recurring_stores(self, filters):
		return self.recurring_stores.filter(filters)

	def get_user_budgets(self, filters):
		return self.budgets.filter(filters)

	def get_user_behaviors(self, filters):
		return self.behaviors.filter(filters)

	def get_user_budget_items(self, filters):
		return self.budget_items.filter(filters)


class Currency(BaseModel):
	"""
	A minimal ISO-4217 currency model for populating the Default Currency select.
	Seed with common currencies (USD/EUR/GBP, etc.).
	"""
	code = models.CharField(max_length=3, unique=True, help_text="ISO 4217 code, e.g., USD, EUR, GBP.")
	name = models.CharField(max_length=64, help_text="Display name, e.g., US Dollar, Euro.")
	symbol = models.CharField(max_length=8, blank=True, help_text="Optional symbol, e.g., $, €, £.")
	minor_unit = models.PositiveSmallIntegerField(default=2, help_text="Number of decimal places, typically 2.")
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ["code"]

	def __str__(self) -> str:
		return f"{self.code} - {self.name}"


class UserSettings(BaseModel):
	"""
	Per-user settings reflected in the screenshot:
	- Notification toggles: email, push
	- Budget alerts toggle + threshold (when approaching budget limits)
	- Default currency selector
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="settings")

	# Notifications
	email_notifications = models.BooleanField(
		default=False,
		help_text="Get updates and alerts via email.",
	)
	push_notifications = models.BooleanField(
		default=False,
		help_text="Get browser notifications for important updates.",
	)

	# Budget alerts
	budget_alerts_enabled = models.BooleanField(
		default=False,
		help_text="Get notified when approaching budget limits.",
	)
	budget_alert_threshold = models.PositiveSmallIntegerField(
		default=80,
		validators=[MinValueValidator(1), MaxValueValidator(100)],
		help_text="Trigger alert at this percent of budget used (1–100).",
	)

	# Currency settings
	default_currency = models.ForeignKey(
		Currency,
		on_delete=models.PROTECT,
		related_name="default_users_currency",
		null=True,
		blank=True,
		help_text="User's default currency for amounts and budgets.",
	)

	class Meta:
		verbose_name = "User settings"
		verbose_name_plural = "User settings"

	def __str__(self) -> str:
		return f"Settings for {self.user}"
