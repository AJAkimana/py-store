import uuid
from typing import Dict, Any

from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
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
	# Set when the password is reset; access tokens issued before it are rejected
	password_changed_at = models.DateTimeField(null=True, blank=True)
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
		verbose_name = "Currency"
		verbose_name_plural = "Currencies"

	def __str__(self) -> str:
		return f"{self.code} - {self.name}"


DEFAULT_PRIMARY_COLOR = '#1976d2'
DEFAULT_SECONDARY_COLOR = '#0288d1'
hex_color_validator = RegexValidator(r'^#[0-9a-fA-F]{6}$', 'Enter a color as #rrggbb.')


class ThemeMode(models.TextChoices):
	LIGHT = 'light', 'Light'
	DARK = 'dark', 'Dark'


class UserSettings(BaseModel):
	"""
	Per-user settings reflected in the screenshot:
	- Notification toggles: email, push
	- Budget alerts toggle + threshold (when approaching budget limits)
	- Default currency selector
	- Appearance: theme mode and accent colors
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

	# Appearance
	theme_mode = models.CharField(
		max_length=10,
		choices=ThemeMode.choices,
		default=ThemeMode.LIGHT,
		help_text="Light or dark interface.",
	)
	primary_color = models.CharField(
		max_length=7,
		default=DEFAULT_PRIMARY_COLOR,
		validators=[hex_color_validator],
		help_text="Main accent color as a #rrggbb hex value.",
	)
	secondary_color = models.CharField(
		max_length=7,
		default=DEFAULT_SECONDARY_COLOR,
		validators=[hex_color_validator],
		help_text="Supporting accent color as a #rrggbb hex value.",
	)

	class Meta:
		verbose_name = "User settings"
		verbose_name_plural = "User settings"

	def __str__(self) -> str:
		return f"Settings for {self.user}"


class MfaMethod(models.TextChoices):
	TOTP = 'totp', 'Authenticator app'
	EMAIL = 'email', 'Email code'
	RECOVERY = 'recovery', 'Recovery code'


class UserMfa(BaseModel):
	"""
	Two-factor authentication state for a user. Kept off the 'User' model so the
	secret can never leak through 'UserType'. Never expose this model over GraphQL.

	Don't soft-delete it: the row would still hold the one-to-one slot (and the secret).
	Turning 2FA off resets the fields instead.
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mfa')

	# Authenticator app (TOTP). The secret is Fernet-encrypted; it is set during setup
	# and only counts as enabled once a code has been confirmed.
	totp_secret_encrypted = models.TextField(blank=True, default='')
	totp_confirmed_at = models.DateTimeField(null=True, blank=True)
	# Last accepted TOTP time step, so a code can't be replayed inside its window
	totp_last_used_step = models.BigIntegerField(null=True, blank=True)

	# Failed login codes across challenges; a fresh login doesn't reset them
	failed_attempts = models.PositiveSmallIntegerField(default=0)
	locked_until = models.DateTimeField(null=True, blank=True)

	email_otp_enabled = models.BooleanField(default=False)
	preferred_method = models.CharField(
		max_length=10,
		choices=[(MfaMethod.TOTP.value, MfaMethod.TOTP.label), (MfaMethod.EMAIL.value, MfaMethod.EMAIL.label)],
		blank=True,
		default='',
	)

	class Meta:
		db_table = 'user_mfa'
		verbose_name = 'User two-factor settings'
		verbose_name_plural = 'User two-factor settings'

	def __str__(self) -> str:
		return f'2FA for {self.user}'

	@property
	def totp_enabled(self) -> bool:
		return bool(self.totp_secret_encrypted and self.totp_confirmed_at)

	@property
	def enabled_methods(self) -> list:
		methods = []
		if self.totp_enabled:
			methods.append(MfaMethod.TOTP.value)
		if self.email_otp_enabled:
			methods.append(MfaMethod.EMAIL.value)
		return methods

	@property
	def is_enabled(self) -> bool:
		return bool(self.enabled_methods)

	@property
	def default_method(self) -> str:
		methods = self.enabled_methods
		if self.preferred_method in methods:
			return self.preferred_method
		return methods[0] if methods else ''


class MfaChallengePurpose(models.TextChoices):
	LOGIN = 'login', 'Login'
	SETUP_EMAIL = 'setup_email', 'Email setup'
	# Re-checking the second factor before turning 2FA off or replacing recovery codes
	SENSITIVE = 'sensitive', 'Sensitive action'
	PASSWORD_RESET = 'password_reset', 'Password reset'


class MfaChallenge(BaseModel):
	"""
	A pending second-factor check (a login waiting for its code, or an email setup).
	Email codes are stored as an HMAC, never in plain text. Rows are hard-deleted.
	"""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mfa_challenges')
	purpose = models.CharField(max_length=20, choices=MfaChallengePurpose.choices)
	code_hash = models.CharField(max_length=128, blank=True, default='')
	expires_at = models.DateTimeField()
	attempts = models.PositiveSmallIntegerField(default=0)
	send_count = models.PositiveSmallIntegerField(default=0)
	last_sent_at = models.DateTimeField(null=True, blank=True)
	consumed_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = 'user_mfa_challenges'
		indexes = [models.Index(fields=['expires_at'])]

	def __str__(self) -> str:
		return f'{self.get_purpose_display()} challenge for {self.user}'


class MfaRecoveryCode(BaseModel):
	"""Single-use backup code; only its HMAC is stored. Rows are hard-deleted."""
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mfa_recovery_codes')
	code_hash = models.CharField(max_length=128)
	used_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		db_table = 'user_mfa_recovery_codes'
		constraints = [
			models.UniqueConstraint(fields=['user', 'code_hash'], name='unique_user_recovery_code'),
		]

	def __str__(self) -> str:
		return f'Recovery code for {self.user}'
