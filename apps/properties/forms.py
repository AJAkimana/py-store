from django.contrib.auth.forms import (
	UserChangeForm as BaseUserChangeForm,
	UserCreationForm as BaseUserCreationForm)

from apps.properties.models import Property

property_fields = ['name', 'price', 'description', 'owner', 'is_active']


class PropertyCreationForm(BaseUserCreationForm):
	class Meta:
		model = Property
		fields = property_fields
		error_class = "error"


class PropertyChangeForm(BaseUserChangeForm):
	class Meta:
		model = Property
		fields = property_fields
		error_class = 'error'
