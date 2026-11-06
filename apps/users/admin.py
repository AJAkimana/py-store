from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from apps.users.models import User, Currency, UserMfa
from apps.users.forms import UserChangeForm, UserCreationForm, CurrencyChangeForm, CurrencyCreationForm


@admin.register(UserMfa)
class UserMfaAdmin(admin.ModelAdmin):
	"""Read-only 2FA status. The TOTP secret is never shown."""
	list_display = ['user', 'totp_enabled', 'email_otp_enabled', 'preferred_method', 'updated_at']
	list_filter = ['email_otp_enabled', 'preferred_method']
	search_fields = ['user__email', 'user__user_name']
	fields = ['user', 'totp_confirmed_at', 'email_otp_enabled', 'preferred_method', 'created_at', 'updated_at']
	readonly_fields = fields

	@admin.display(boolean=True, description='Authenticator app')
	def totp_enabled(self, obj):
		return obj.totp_enabled

	def has_add_permission(self, request):
		return False

	def has_change_permission(self, request, obj=None):
		return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	ordering = ["id"]
	add_form = UserCreationForm
	form = UserChangeForm
	model = User
	list_display = ['user_name', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']
	list_filter = ['user_name', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']
	fieldsets = (
		(_('Login Credentials'), {'fields': ('user_name', 'email', 'password',)}),
		(_('Personal Information'), {'fields': ('first_name', 'last_name',)}),
		(_('Permissions and Groups'), {
			'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions',)
		}),
		(_('Important Dates'), {'fields': ('last_login',)}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('user_name', 'first_name', 'last_name', 'email', 'is_active', 'is_staff')
		}),
	)
	search_fields = ['user_name', 'first_name', 'last_name', 'email']


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
	add_form = CurrencyCreationForm
	form = CurrencyChangeForm
	model = Currency
	list_display = ['name', 'code', 'symbol', 'minor_unit', 'is_active']
	list_filter = ['name', 'code', 'is_active']
	fieldsets = (
		(_('Detailed Information'), {'fields': ('name', 'code', 'symbol', 'minor_unit', 'is_active')}),
	)
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ['name', 'code', 'symbol', 'minor_unit', 'is_active']
		}),
	)
	search_fields = ['name', 'code']
