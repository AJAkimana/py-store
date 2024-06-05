from django.contrib import admin
from django.contrib.admin import ModelAdmin as BaseModelAdmin
from django.utils.translation import gettext_lazy as _

from apps.budgeting.forms import BudgetChangeForm, BudgetCreationForm, BudgetItemCreationForm, BudgetItemChangeForm
from apps.budgeting.models import Budget, BudgetItem


class BudgetAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = BudgetCreationForm
	form = BudgetChangeForm
	model = Budget
	list_display = ['name', 'description', 'status', 'start_date', 'end_date']
	list_filter = ['name', 'status', 'start_date', 'end_date']
	fieldsets = (
		(_('Detailed Information'), {'fields': ('name', 'description', 'status',)}),
		(_('Important Dates'), {'fields': ('start_date', 'end_date',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['name', 'description', 'status', 'start_date', 'end_date']
		}),
	)
	search_fields = ['name', 'status']


class BudgetItemAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = BudgetItemCreationForm
	form = BudgetItemChangeForm
	model = BudgetItem
	list_display = ['name', 'amount']
	list_filter = ['name']
	fieldsets = (
		(_('Detailed Information'), {'fields': ('name', 'amount',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['name', 'amount', 'budget']
		}),
	)
	search_fields = ['name']


admin.site.register(Budget, BudgetAdmin)
admin.site.register(BudgetItem, BudgetItemAdmin)
