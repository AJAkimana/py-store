from django.contrib import admin
from django.contrib.admin import ModelAdmin as BaseModelAdmin
from django.utils.translation import gettext_lazy as _

from apps.properties.forms import PropertyChangeForm, PropertyCreationForm, property_fields
from apps.properties.models import Property


@admin.register(Property)
class PropertyAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = PropertyCreationForm
	form = PropertyChangeForm
	model = Property
	list_display = ['name', 'price', 'description', 'owner', 'is_active', 'display_detail']
	list_filter = ['owner', 'is_active']
	fieldsets = (
		(_('Property Information'), {'fields': [('name', 'description', 'is_active'), ]}),
		(_('Amount Information'), {'fields': ('price',)}),
		(_('Property OwnerShip'), {'fields': ('owner',)}),
		(_('Important Dates'), {'fields': ('created_at', 'updated_at',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': [('name', 'price'), 'description', ('owner', 'is_active')]
		}),
	)
	search_fields = ['price', 'name']


# admin.site.register(PropDetail)
