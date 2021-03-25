from django.contrib.auth.forms import (
	UserChangeForm as BaseUserChangeForm,
	UserCreationForm as BaseUserCreationForm)
from apps.stores.models import Store


class StoreCreationForm(BaseUserCreationForm):
	class Meta:
		model = Store
		fields = ['amount', 'record_type', 'description', 'is_property', 'is_inflow', 'action_date', 'user']
		error_class = "error"


class StoreChangeForm(BaseUserChangeForm):
	class Meta:
		model = Store
		fields = ['amount', 'record_type', 'description', 'is_property', 'is_inflow', 'action_date', 'user']
		error_class = 'error'
