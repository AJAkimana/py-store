from django.contrib import admin
from django.contrib.admin import ModelAdmin as BaseModelAdmin
from django.utils.translation import gettext_lazy as _
from apps.stores.models import Store
from apps.stores.forms import StoreChangeForm, StoreCreationForm


class StoreAdmin(BaseModelAdmin):
	ordering = ["action_date"]
	add_form = StoreCreationForm
	form = StoreChangeForm
	model = Store
	list_display = ['amount', 'record_type', 'description', 'is_property', 'is_inflow', 'action_date', 'user']
	list_filter = ['record_type', 'is_property', 'is_inflow', 'user']
	fieldsets = (
		(_('Amount Information'), {'fields': ('amount', 'is_inflow', 'is_property')}),
		(_('Detailed Information'), {'fields': ('description', 'record_type',)}),
		(_('Store OwnerShip'), {'fields': ('user',)}),
		(_('Important Dates'), {'fields': ('action_date',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('amount', 'record_type', 'description', 'is_property', 'is_inflow', 'action_date', 'user')
		}),
	)
	search_fields = ['amount', 'description']


admin.site.register(Store, StoreAdmin)
