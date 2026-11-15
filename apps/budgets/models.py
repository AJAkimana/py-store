"""
Budgeting, revamped.

- BudgetItem: the catalogue of things money is planned for ("Transport", "Rent").
  System items (no owner) are managed by admins and enabled per owner through
  ItemActivation; owners can also create their own items.
- Budget: a plan over any period (start_date..end_date), owned by a user or a household.
- BudgetAllocation: how much a budget plans for one item.
- Transactions (stores.Store) point at a BudgetItem. The budget a transaction counts
  toward is derived from its date, never stored.

Every owned row has two nullable owner columns (user, household); the database
enforces who may own what. Only user ownership is wired up for now
(see apps/budgets/owner.py).
"""
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.households.models import Household
from apps.users.models import User
from d2dstore.models import BaseModel

ALIVE = Q(deleted_at__isnull=True)
USER_OWNED = Q(user__isnull=False, household__isnull=True)
HOUSEHOLD_OWNED = Q(user__isnull=True, household__isnull=False)
NO_OWNER = Q(user__isnull=True, household__isnull=True)


class BudgetStatus(models.TextChoices):
	DRAFT = 'draft', 'Draft'
	ACTIVE = 'active', 'Active'
	CLOSED = 'closed', 'Closed'


class BudgetItem(BaseModel):
	"""A budget item: system-wide (no owner), or owned by a user or a household."""
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True, default='')
	default_amount = models.DecimalField(
		max_digits=14, decimal_places=2, default=0,
		help_text='Pre-fills allocations when this item is added to a budget.')
	is_active = models.BooleanField(default=True)
	user = models.ForeignKey(
		User, null=True, blank=True, related_name='budget_catalog_items', on_delete=models.PROTECT)
	household = models.ForeignKey(
		Household, null=True, blank=True, related_name='budget_catalog_items',
		on_delete=models.PROTECT)

	class Meta:
		db_table = 'budgets_item'
		ordering = ['name']
		constraints = [
			models.CheckConstraint(
				check=USER_OWNED | HOUSEHOLD_OWNED | NO_OWNER, name='budget_item_at_most_one_owner'),
			models.UniqueConstraint(
				Lower('name'), 'user', condition=ALIVE & USER_OWNED,
				name='budget_item_unique_name_per_user'),
			models.UniqueConstraint(
				Lower('name'), 'household', condition=ALIVE & HOUSEHOLD_OWNED,
				name='budget_item_unique_name_per_household'),
			models.UniqueConstraint(
				Lower('name'), condition=ALIVE & NO_OWNER, name='budget_item_unique_system_name'),
		]

	@property
	def is_system(self):
		return self.user_id is None and self.household_id is None

	def __str__(self):
		return self.name


class ItemActivation(BaseModel):
	"""An owner's on/off switch for a system BudgetItem."""
	item = models.ForeignKey(BudgetItem, related_name='activations', on_delete=models.CASCADE)
	enabled = models.BooleanField(default=True)
	user = models.ForeignKey(
		User, null=True, blank=True, related_name='budget_item_activations',
		on_delete=models.CASCADE)
	household = models.ForeignKey(
		Household, null=True, blank=True, related_name='budget_item_activations',
		on_delete=models.CASCADE)

	class Meta:
		db_table = 'budgets_item_activation'
		constraints = [
			models.CheckConstraint(
				check=USER_OWNED | HOUSEHOLD_OWNED, name='item_activation_single_owner'),
			models.UniqueConstraint(
				fields=['item', 'user'], condition=USER_OWNED, name='item_activation_unique_user'),
			models.UniqueConstraint(
				fields=['item', 'household'], condition=HOUSEHOLD_OWNED,
				name='item_activation_unique_household'),
		]

	def __str__(self):
		return f'{self.user or self.household} => {self.item} ({"on" if self.enabled else "off"})'


class Budget(BaseModel):
	"""A spending plan over any period, owned by exactly one user or household."""
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True, default='')
	start_date = models.DateField()
	end_date = models.DateField()
	status = models.CharField(
		max_length=10, choices=BudgetStatus.choices, default=BudgetStatus.DRAFT)
	user = models.ForeignKey(
		User, null=True, blank=True, related_name='owned_budgets', on_delete=models.PROTECT)
	household = models.ForeignKey(
		Household, null=True, blank=True, related_name='owned_budgets', on_delete=models.PROTECT)
	created_by = models.ForeignKey(
		User, null=True, related_name='created_budgets', on_delete=models.PROTECT)

	class Meta:
		db_table = 'budgets_budget'
		ordering = ['-start_date']
		constraints = [
			models.CheckConstraint(check=USER_OWNED | HOUSEHOLD_OWNED, name='budget_single_owner'),
			models.CheckConstraint(
				check=Q(end_date__gte=models.F('start_date')), name='budget_end_after_start'),
			models.UniqueConstraint(
				Lower('name'), 'user', condition=ALIVE & USER_OWNED,
				name='budget_unique_name_per_user'),
			models.UniqueConstraint(
				Lower('name'), 'household', condition=ALIVE & HOUSEHOLD_OWNED,
				name='budget_unique_name_per_household'),
		]

	def __str__(self):
		return f'{self.name} ({self.start_date} → {self.end_date})'


class BudgetAllocation(BaseModel):
	"""The amount a budget plans for one item, e.g. November budget: Transport = 50,000."""
	budget = models.ForeignKey(Budget, related_name='allocations', on_delete=models.CASCADE)
	item = models.ForeignKey(BudgetItem, related_name='allocations', on_delete=models.PROTECT)
	amount = models.DecimalField(max_digits=14, decimal_places=2)

	class Meta:
		db_table = 'budgets_allocation'
		ordering = ['item__name']
		constraints = [
			models.CheckConstraint(check=Q(amount__gte=0), name='allocation_amount_not_negative'),
			models.UniqueConstraint(
				fields=['budget', 'item'], condition=ALIVE, name='allocation_unique_item_per_budget'),
		]

	def __str__(self):
		return f'{self.budget.name}: {self.item.name} = {self.amount}'
