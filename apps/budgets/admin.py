from django.contrib import admin

from apps.budgets.models import Budget, BudgetAllocation, BudgetItem, ItemActivation


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
	list_display = ['name', 'user', 'household', 'default_amount', 'is_active']
	list_filter = ['is_active', ('user', admin.EmptyFieldListFilter)]
	search_fields = ['name', 'user__email']
	raw_id_fields = ['user', 'household']


@admin.register(ItemActivation)
class ItemActivationAdmin(admin.ModelAdmin):
	list_display = ['item', 'user', 'household', 'enabled']
	list_filter = ['enabled']
	search_fields = ['item__name', 'user__email']
	raw_id_fields = ['item', 'user', 'household']


class BudgetAllocationInline(admin.TabularInline):
	model = BudgetAllocation
	extra = 0
	raw_id_fields = ['item']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
	list_display = ['name', 'user', 'household', 'status', 'start_date', 'end_date']
	list_filter = ['status']
	search_fields = ['name', 'user__email']
	raw_id_fields = ['user', 'household', 'created_by']
	inlines = [BudgetAllocationInline]
