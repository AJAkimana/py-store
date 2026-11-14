from datetime import date
from decimal import Decimal
from itertools import count

from django.apps import apps as django_apps
from django.db import IntegrityError, transaction
from django.test import TestCase
from graphql import GraphQLError

from apps.budgeting import models as old
from apps.budgets.legacy import migrate_legacy_budgeting
from apps.budgets.models import Budget, BudgetAllocation, BudgetItem, BudgetStatus, ItemActivation
from apps.budgets.owner import BudgetOwner, resolve_owner
from apps.budgets.services import (
	active_budget, allocations_with_spending, budget_totals, change_status, validate_budget,
)
from apps.households.models import Household
from apps.stores.models import Store
from apps.users.models import User

_seq = count()


def make_user(**extra):
	n = next(_seq)
	return User.objects.create(
		first_name='Test', last_name=f'User{n}', middle_name='', user_name=f'user{n}',
		phone=f'0780000{n:03d}', email=f'user{n}@example.com', **extra)


def make_store(user, amount, on, item=None, is_inflow=False, **extra):
	return Store.objects.create(
		user=user, amount=amount, action_date=on, item=item, is_inflow=is_inflow,
		description=f'tx {next(_seq)}', **extra)


def make_budget(user, start, end, status=BudgetStatus.DRAFT, name=None, **allocations):
	budget = Budget.objects.create(
		user=user, created_by=user, name=name or f'Budget {next(_seq)}',
		start_date=start, end_date=end, status=status)
	for item, amount in allocations.items():
		BudgetAllocation.objects.create(budget=budget, item=item_by_name(user, item), amount=amount)
	return budget


def item_by_name(user, name):
	item, _ = BudgetItem.objects.get_or_create(user=user, name=name.capitalize())
	return item


class ConstraintTests(TestCase):
	def setUp(self):
		self.user = make_user()
		self.household = Household.objects.create(name='Home')

	def assertViolates(self, fn):
		with self.assertRaises(IntegrityError), transaction.atomic():
			fn()

	def test_budget_needs_exactly_one_owner(self):
		dates = dict(name='B', start_date=date(2026, 1, 1), end_date=date(2026, 1, 31))
		self.assertViolates(lambda: Budget.objects.create(**dates))
		self.assertViolates(
			lambda: Budget.objects.create(user=self.user, household=self.household, **dates))
		Budget.objects.create(household=self.household, **dates)
		Budget.objects.create(user=self.user, **dates)

	def test_budget_end_not_before_start(self):
		self.assertViolates(lambda: Budget.objects.create(
			user=self.user, name='B', start_date=date(2026, 2, 1), end_date=date(2026, 1, 1)))

	def test_item_names_unique_per_owner_case_insensitive(self):
		BudgetItem.objects.create(name='Transport', user=self.user)
		self.assertViolates(lambda: BudgetItem.objects.create(name='transport', user=self.user))
		BudgetItem.objects.create(name='Transport', user=make_user())
		BudgetItem.objects.create(name='Transport')  # system
		self.assertViolates(lambda: BudgetItem.objects.create(name='TRANSPORT'))

	def test_soft_deleted_item_frees_the_name(self):
		item = BudgetItem.objects.create(name='Rent', user=self.user)
		item.delete()
		BudgetItem.objects.create(name='Rent', user=self.user)

	def test_allocation_unique_per_budget_and_not_negative(self):
		budget = make_budget(self.user, date(2026, 1, 1), date(2026, 1, 31), rent=100)
		rent = item_by_name(self.user, 'rent')
		self.assertViolates(
			lambda: BudgetAllocation.objects.create(budget=budget, item=rent, amount=5))
		food = item_by_name(self.user, 'food')
		self.assertViolates(
			lambda: BudgetAllocation.objects.create(budget=budget, item=food, amount=-1))


class OwnerTests(TestCase):
	def setUp(self):
		self.user = make_user()
		self.other = make_user()

	def test_owner_requires_exactly_one(self):
		with self.assertRaises(ValueError):
			BudgetOwner()
		with self.assertRaises(ValueError):
			BudgetOwner(user=self.user, household=Household.objects.create())

	def test_resolve_owner_defaults_to_user_and_blocks_households(self):
		self.assertEqual(resolve_owner(self.user).user, self.user)
		with self.assertRaises(GraphQLError):
			resolve_owner(self.user, household_id='some-id')

	def test_usable_items(self):
		own = BudgetItem.objects.create(name='Gym', user=self.user)
		BudgetItem.objects.create(name='Archived', user=self.user, is_active=False)
		BudgetItem.objects.create(name='Theirs', user=self.other)
		enabled = BudgetItem.objects.create(name='Transport')
		disabled = BudgetItem.objects.create(name='Rent')
		BudgetItem.objects.create(name='Never enabled')
		ItemActivation.objects.create(item=enabled, user=self.user, enabled=True)
		ItemActivation.objects.create(item=disabled, user=self.user, enabled=False)
		ItemActivation.objects.create(item=disabled, user=self.other, enabled=True)

		usable = set(BudgetOwner(user=self.user).usable_items())
		self.assertEqual(usable, {own, enabled})


class SpendingTests(TestCase):
	def setUp(self):
		self.user = make_user()
		self.budget = make_budget(
			self.user, date(2026, 11, 10), date(2026, 12, 9), transport=50000, rent=200000)
		self.transport = item_by_name(self.user, 'transport')
		self.rent = item_by_name(self.user, 'rent')
		self.food = item_by_name(self.user, 'food')

	def test_spending_follows_the_budget_period_not_the_month(self):
		make_store(self.user, 6000, date(2026, 11, 14), self.transport)
		make_store(self.user, 4000, date(2026, 12, 9), self.transport)  # last day counts
		make_store(self.user, 9999, date(2026, 11, 9), self.transport)  # before period
		make_store(self.user, 9999, date(2026, 12, 10), self.transport)  # after period
		make_store(self.user, 7777, date(2026, 11, 20), self.transport, is_inflow=True)
		make_store(make_user(), 5555, date(2026, 11, 20))  # someone else

		rows = {a.item.name: a for a in allocations_with_spending(self.budget)}
		self.assertEqual(rows['Transport'].spent, Decimal('10000'))
		self.assertEqual(rows['Transport'].remaining, Decimal('40000'))
		self.assertEqual(rows['Rent'].spent, Decimal('0'))

	def test_totals_split_planned_and_unbudgeted(self):
		make_store(self.user, 6000, date(2026, 11, 14), self.transport)
		make_store(self.user, 150000, date(2026, 11, 15), self.rent)
		make_store(self.user, 3000, date(2026, 11, 16), self.food)  # item not in the budget
		make_store(self.user, 1000, date(2026, 11, 16))  # untagged

		totals = budget_totals(self.budget)
		self.assertEqual(totals['allocated'], Decimal('250000'))
		self.assertEqual(totals['spent'], Decimal('156000'))
		self.assertEqual(totals['remaining'], Decimal('94000'))
		self.assertEqual(totals['unbudgeted'], Decimal('4000'))


class StatusTests(TestCase):
	def setUp(self):
		self.user = make_user()

	def test_cannot_activate_empty_budget(self):
		budget = make_budget(self.user, date(2026, 1, 1), date(2026, 1, 31))
		with self.assertRaises(GraphQLError):
			change_status(budget, BudgetStatus.ACTIVE)

	def test_active_budgets_cannot_overlap_but_drafts_can(self):
		make_budget(
			self.user, date(2026, 1, 1), date(2026, 1, 31), status=BudgetStatus.ACTIVE, rent=1)
		draft = make_budget(self.user, date(2026, 1, 15), date(2026, 2, 15), rent=1)
		with self.assertRaises(GraphQLError):
			change_status(draft, BudgetStatus.ACTIVE)

		later = make_budget(self.user, date(2026, 2, 1), date(2026, 2, 10), rent=1)
		change_status(later, BudgetStatus.ACTIVE)  # adjacent, not overlapping
		other_users = make_budget(make_user(), date(2026, 1, 1), date(2026, 3, 1), rent=1)
		change_status(other_users, BudgetStatus.ACTIVE)

	def test_transitions(self):
		budget = make_budget(self.user, date(2026, 1, 1), date(2026, 1, 31), rent=1)
		with self.assertRaises(GraphQLError):
			change_status(budget, BudgetStatus.CLOSED)
		change_status(budget, BudgetStatus.ACTIVE)
		change_status(budget, BudgetStatus.CLOSED)
		with self.assertRaises(GraphQLError):
			change_status(budget, 'approved')

	def test_duplicate_name_rejected(self):
		make_budget(self.user, date(2026, 1, 1), date(2026, 1, 31), name='November')
		dup = Budget(
			user=self.user, name='november', start_date=date(2027, 1, 1), end_date=date(2027, 1, 2))
		with self.assertRaises(GraphQLError):
			validate_budget(dup)

	def test_active_budget_lookup(self):
		budget = make_budget(
			self.user, date(2026, 11, 1), date(2026, 11, 30), status=BudgetStatus.ACTIVE, rent=1)
		owner = BudgetOwner(user=self.user)
		self.assertEqual(active_budget(owner, date(2026, 11, 14)), budget)
		self.assertIsNone(active_budget(owner, date(2026, 12, 1)))


class LegacyMigrationTests(TestCase):
	"""Runs the 0002 data copy against legacy rows built with the old models."""

	def setUp(self):
		self.user = make_user()
		self.other = make_user()
		self.today = date(2026, 11, 14)

		self.sys_transport = old.DefaultBudgetLine.objects.create(name='Transport')
		self.sys_disabled = old.DefaultBudgetLine.objects.create(name='Water', enabled=False)
		old.UserDefaultBudgetLine.objects.create(user=self.user, line=self.sys_transport)
		self.u_rent = old.UserBudgetLine.objects.create(
			name='Rent', user=self.user, amount=Decimal('200000'))

		self.past = old.Budget.objects.create(
			name='October', user=self.user, status='approved',
			start_date=date(2026, 10, 1), end_date=date(2026, 10, 31))
		self.current = old.Budget.objects.create(
			name='November', user=self.user, status='approved', household=None,
			start_date=date(2026, 11, 1), end_date=date(2026, 11, 30))
		self.draft = old.Budget.objects.create(
			name='December', user=self.user, status='pending',
			start_date=date(2026, 12, 1), end_date=date(2026, 12, 31))

		def item(**kw):
			kw.setdefault('user', self.user)
			return old.BudgetItem.objects.create(**kw)

		self.i_transport = item(
			name='Transport', amount=30000, budget=self.current, d_budget_line=self.sys_transport)
		item(name='Transport extra', amount=20000, budget=self.current,
			d_budget_line=self.sys_transport)  # same item twice: summed
		self.i_rent = item(name='Rent', amount=200000, budget=self.current, u_budget_line=self.u_rent)
		self.i_free = item(name=' Gym ', amount=15000, budget=self.past)  # free text
		item(name='Netflix', amount=12000, budget=None, is_recurring=True)  # orphan recurring
		other_sys = old.DefaultBudgetLine.objects.create(name='Electricity')
		self.i_other_sys = item(
			name='Electricity', amount=5000, budget=self.past, d_budget_line=other_sys)

		self.s_transport = make_store(
			self.user, 6000, date(2026, 11, 14), budget_item=self.i_transport)
		self.s_gym = make_store(self.user, 15000, date(2026, 10, 5), budget_item=self.i_free)
		self.s_plain = make_store(self.user, 999, date(2026, 11, 2))

		migrate_legacy_budgeting(django_apps, today=self.today, log=lambda *_: None)

	def test_lines_become_items_with_same_ids(self):
		transport = BudgetItem.objects.get(id=self.sys_transport.id)
		self.assertTrue(transport.is_system)
		self.assertFalse(BudgetItem.objects.get(id=self.sys_disabled.id).is_active)
		rent = BudgetItem.objects.get(id=self.u_rent.id)
		self.assertEqual(rent.user, self.user)
		self.assertEqual(rent.default_amount, Decimal('200000'))

	def test_free_text_and_recurring_items_become_user_items(self):
		gym = BudgetItem.objects.get(user=self.user, name='Gym')
		self.assertEqual(gym.default_amount, 0)
		netflix = BudgetItem.objects.get(user=self.user, name='Netflix')
		self.assertEqual(netflix.default_amount, Decimal('12000'))

	def test_budgets_and_statuses(self):
		self.assertEqual(Budget.objects.get(id=self.past.id).status, BudgetStatus.CLOSED)
		current = Budget.objects.get(id=self.current.id)
		self.assertEqual(current.status, BudgetStatus.ACTIVE)
		self.assertEqual(current.user, self.user)
		self.assertIsNone(current.household)
		self.assertEqual(Budget.objects.get(id=self.draft.id).status, BudgetStatus.DRAFT)

	def test_allocations(self):
		current = {a.item_id: a.amount for a in BudgetAllocation.objects.filter(budget=self.current.id)}
		self.assertEqual(current, {
			self.sys_transport.id: Decimal('50000'),
			self.u_rent.id: Decimal('200000'),
		})
		self.assertFalse(BudgetAllocation.objects.filter(item__name='Netflix').exists())

	def test_stores_are_tagged_with_items(self):
		self.s_transport.refresh_from_db()
		self.s_gym.refresh_from_db()
		self.s_plain.refresh_from_db()
		self.assertEqual(self.s_transport.item_id, self.sys_transport.id)
		self.assertEqual(self.s_gym.item.name, 'Gym')
		self.assertIsNone(self.s_plain.item_id)

	def test_used_system_items_are_enabled_for_the_user(self):
		owner = BudgetOwner(user=self.user)
		names = set(owner.usable_items().values_list('name', flat=True))
		self.assertEqual(names, {'Transport', 'Rent', 'Gym', 'Netflix', 'Electricity'})
		self.assertEqual(ItemActivation.objects.filter(user=self.other).count(), 0)

	def test_spending_after_migration(self):
		budget = Budget.objects.get(id=self.current.id)
		rows = {a.item.name: a.spent for a in allocations_with_spending(budget)}
		self.assertEqual(rows['Transport'], Decimal('6000'))
