# from django.contrib import admin
# from apps.households.models import Household
# from apps.household_members.models import HouseholdMember
#
# admin.site.register(Household)
# admin.site.register(HouseholdMember)

from django.contrib import admin
from django.contrib.admin import ModelAdmin as BaseModelAdmin
from django.utils.translation import gettext_lazy as _

from apps.household_members.models import HouseholdMember
from apps.households.models import Household
from apps.households.forms import HouseholdCreationForm, HouseholdChangeForm, HouseholdMemberCreationForm, \
	HouseholdMemberChangeForm


class HouseholdAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = HouseholdCreationForm
	form = HouseholdChangeForm
	model = Household
	list_display = ['name', 'description']
	list_filter = ['name', 'description']
	fieldsets = (
		(_('Detailed Information'), {'fields': ('name', 'description',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['name', 'description']
		}),
	)
	search_fields = ['name']


class HouseholdMemberAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = HouseholdMemberCreationForm
	form = HouseholdMemberChangeForm
	model = HouseholdMember
	list_display = ['user', 'household', 'access_level']
	list_filter = ['user', 'household', 'access_level']
	fieldsets = (
		(_('Ownership'), {'fields': ('user', 'household',)}),
		(_('Privileges'), {'fields': ('access_level',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['user', 'household', 'access_level']
		}),
	)
	search_fields = ['user', 'household', 'access_level']


admin.site.register(Household, HouseholdAdmin)
admin.site.register(HouseholdMember, HouseholdMemberAdmin)
