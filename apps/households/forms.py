from django.contrib.auth.forms import (
	UserChangeForm as BaseUserChangeForm,
	UserCreationForm as BaseUserCreationForm)
from apps.households.models import Household
from apps.household_members.models import HouseholdMember


class HouseholdForm:
	class Meta:
		model = Household
		fields = ['name', 'description']
		error_class = "error"


class HouseholdMemberForm:
	class Meta:
		model = HouseholdMember
		fields = ['user', 'household', 'access_level']
		error_class = "error"


class HouseholdCreationForm(BaseUserCreationForm, HouseholdForm):
	pass


class HouseholdChangeForm(BaseUserChangeForm, HouseholdForm):
	pass


class HouseholdMemberCreationForm(BaseUserCreationForm, HouseholdMemberForm):
	pass


class HouseholdMemberChangeForm(BaseUserChangeForm, HouseholdMemberForm):
	pass
