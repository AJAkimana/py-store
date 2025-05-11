from django.contrib.auth.forms import (
	UserChangeForm as BaseUserChangeForm,
	UserCreationForm as BaseUserCreationForm)

from apps.behavior_ip.models import Behavior, BehaviorScore


class BehaviorForm:
	class Meta:
		model = Behavior
		fields = ['name', 'description', 'weight', 'user']
		error_class = "error"


class BehaviorScoreForm:
	class Meta:
		model = BehaviorScore
		fields = ['score', 'rate', 'action_date', 'behavior']
		error_class = "error"


class BehaviorCreationForm(BaseUserCreationForm, BehaviorForm):
	pass


class BehaviorChangeForm(BaseUserChangeForm, BehaviorForm):
	pass


class BehaviorScoreCreationForm(BaseUserCreationForm, BehaviorScoreForm):
	pass


class BehaviorScoreChangeForm(BaseUserChangeForm, BehaviorScoreForm):
	pass
