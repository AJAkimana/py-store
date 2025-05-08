from django.contrib import admin
from django.contrib.admin import ModelAdmin as BaseModelAdmin
from django.utils.translation import gettext_lazy as _

from apps.behavior_ip.forms import BehaviorCreationForm, BehaviorChangeForm, BehaviorScoreChangeForm, \
	BehaviorScoreCreationForm
from apps.behavior_ip.models import Behavior, BehaviorScore


@admin.register(Behavior)
class BehaviorAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = BehaviorCreationForm
	form = BehaviorChangeForm
	model = Behavior
	list_display = ['name', 'description', 'weight', 'user']
	list_filter = ['name', 'description', 'weight']
	fieldsets = (
		(_('Detailed Information'), {'fields': ('name', 'description', 'weight',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['name', 'description', 'weight', 'user']
		}),
	)
	search_fields = ['name']


@admin.register(BehaviorScore)
class BehaviorScoreAdmin(BaseModelAdmin):
	ordering = ["created_at"]
	add_form = BehaviorScoreCreationForm
	form = BehaviorScoreChangeForm
	model = BehaviorScore
	list_display = ['score', 'rate', 'action_date', 'behavior']
	list_filter = ['behavior', 'rate', 'action_date']
	fieldsets = (
		(_('Detailed Information'), {'fields': ('rate', 'score', 'action_date', 'behavior',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['behavior', 'rate', 'score', 'action_date']
		}),
	)
	search_fields = ['score']


