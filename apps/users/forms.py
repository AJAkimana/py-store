from django.contrib.auth.forms import (
	UserChangeForm as BaseUserChangeForm,
	UserCreationForm as BaseUserCreationForm)
from .models import User, Currency


class UserCreationForm(BaseUserCreationForm):
	class Meta:
		model = User
		fields = ['first_name', 'last_name', 'middle_name', 'phone', 'user_name', 'email']
		error_class = "error"


class UserChangeForm(BaseUserChangeForm):
	class Meta:
		model = User
		fields = ['first_name', 'last_name', 'middle_name', 'phone', 'user_name', 'email']
		error_class = 'error'


class CurrencyCreationForm(BaseUserCreationForm):
	class Meta:
		model = Currency
		fields = ['name', 'code', 'symbol', 'minor_unit', 'is_active']
		error_class = "error"


class CurrencyChangeForm(BaseUserChangeForm):
	class Meta:
		model = Currency
		fields = ['name', 'code', 'symbol', 'minor_unit', 'is_active']
		error_class = 'error'

