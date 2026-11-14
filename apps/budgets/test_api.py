from datetime import date
from types import SimpleNamespace

from django.test import TestCase

from apps.budgets.models import Budget, BudgetItem, BudgetStatus, ItemActivation
from apps.budgets.tests import make_store, make_user
from apps.household_members.models import HouseholdMember
from apps.households.models import Household
from apps.stores.models import Store
from d2dstore.schema import schema


class GraphQLTestCase(TestCase):
	def setUp(self):
		self.user = make_user()
		self.household = Household.objects.create(name='Home')
		HouseholdMember.objects.create(user=self.user, household=self.household, access_level=1)

	def run_gql(self, query, user=None, **variables):
		result = schema.execute(
			query, variable_values=variables,
			context_value=SimpleNamespace(user=user or self.user, META={}, COOKIES={}))
		return result

	def ok(self, query, user=None, **variables):
		result = self.run_gql(query, user=user, **variables)
		self.assertIsNone(result.errors, result.errors)
		return result.data

	def error(self, query, user=None, **variables):
		result = self.run_gql(query, user=user, **variables)
		self.assertTrue(result.errors, 'expected an error')
		return str(result.errors[0])


CREATE_ITEM = '''
mutation($name: String!, $isSystem: Boolean, $defaultAmount: Float) {
  createBudgetItem(name: $name, isSystem: $isSystem, defaultAmount: $defaultAmount) {
    item { id name isSystem enabled defaultAmount }
  }
}'''
ITEMS = '''
query($all: Boolean) { budgetItems(includeDisabled: $all) { id name isSystem enabled isActive } }'''
ENABLE = '''
mutation($id: ID!, $on: Boolean!) { setSystemItemEnabled(itemId: $id, enabled: $on) { item { enabled } } }'''
CREATE_BUDGET = '''
mutation($name: String!, $start: Date!, $end: Date!, $allocations: [AllocationInput!], $status: String) {
  createBudget(name: $name, startDate: $start, endDate: $end, allocations: $allocations, status: $status) {
    budget { id status allocated spent remaining unbudgeted
      allocations { amount spent remaining item { name } } }
  }
}'''
BUDGET = '''
query($id: ID!) { budget(id: $id) { name status allocated spent remaining unbudgeted
  allocations { amount spent remaining item { name } } } }'''
CREATE_STORE = '''
mutation($amount: Float!, $date: Date!, $desc: String!, $household: String!, $itemId: String,
         $inflow: Boolean = false) {
  createStore(amount: $amount, actionDate: $date, description: $desc, householdId: $household,
              recordType: "use", isInflow: $inflow, itemId: $itemId) {
    store { id item { name } }
  }
}'''


class BudgetItemApiTests(GraphQLTestCase):
	def test_user_items_and_system_items_flow(self):
		admin = make_user(is_superuser=True)
		transport = self.ok(CREATE_ITEM, user=admin, name='transport', isSystem=True)
		transport_id = transport['createBudgetItem']['item']['id']
		self.assertIn('administrators', self.error(CREATE_ITEM, name='Rent', isSystem=True))

		self.ok(CREATE_ITEM, name='Gym', defaultAmount=15000)
		self.assertIn('already exists', self.error(CREATE_ITEM, name='gym'))

		usable = {i['name'] for i in self.ok(ITEMS)['budgetItems']}
		self.assertEqual(usable, {'Gym'})
		settings_view = {i['name']: i['enabled'] for i in self.ok(ITEMS, all=True)['budgetItems']}
		self.assertEqual(settings_view, {'Gym': True, 'transport': False})

		self.ok(ENABLE, id=transport_id, on=True)
		usable = {i['name'] for i in self.ok(ITEMS)['budgetItems']}
		self.assertEqual(usable, {'Gym', 'transport'})
		self.ok(ENABLE, id=transport_id, on=False)
		self.assertEqual(ItemActivation.objects.get(user=self.user).enabled, False)

	def test_users_cannot_touch_others_items(self):
		theirs = BudgetItem.objects.create(name='Theirs', user=make_user())
		system = BudgetItem.objects.create(name='Transport')
		update = 'mutation($id: ID!) { updateBudgetItem(id: $id, name: "X") { item { name } } }'
		self.assertIn('not found', self.error(update, id=str(theirs.id)))
		self.assertIn('administrator', self.error(update, id=str(system.id)))

	def test_delete_archives_items_in_use(self):
		used = BudgetItem.objects.create(name='Food', user=self.user)
		unused = BudgetItem.objects.create(name='Spare', user=self.user)
		make_store(self.user, 100, date(2026, 11, 1), used)
		delete = 'mutation($id: ID!) { deleteBudgetItem(id: $id) { archived } }'
		self.assertTrue(self.ok(delete, id=str(used.id))['deleteBudgetItem']['archived'])
		self.assertFalse(self.ok(delete, id=str(unused.id))['deleteBudgetItem']['archived'])
		used.refresh_from_db()
		self.assertFalse(used.is_active)
		self.assertFalse(BudgetItem.all_objects.filter(id=unused.id).exists())

		recreate = self.ok(CREATE_ITEM, name='food')['createBudgetItem']['item']
		self.assertEqual(recreate['id'], str(used.id))  # archived item comes back


class BudgetApiTests(GraphQLTestCase):
	def setUp(self):
		super().setUp()
		self.transport = BudgetItem.objects.create(name='Transport', user=self.user)
		self.rent = BudgetItem.objects.create(name='Rent', user=self.user)

	def allocations(self, **amounts):
		items = {'transport': self.transport, 'rent': self.rent}
		return [{'itemId': str(items[k].id), 'amount': v} for k, v in amounts.items()]

	def create(self, name='Nov', start='2026-11-10', end='2026-12-09', status='draft', **amounts):
		data = self.ok(
			CREATE_BUDGET, name=name, start=start, end=end, status=status,
			allocations=self.allocations(**amounts))
		return data['createBudget']['budget']

	def test_daily_transactions_count_toward_the_budget_covering_their_date(self):
		budget = self.create(status='active', transport=50000, rent=200000)
		self.assertEqual(budget['status'], 'active')

		self.ok(CREATE_STORE, amount=6000, date='2026-11-14', desc='Moto',
			household=str(self.household.id), itemId=str(self.transport.id))
		self.ok(CREATE_STORE, amount=2000, date='2026-11-15', desc='Snacks',
			household=str(self.household.id))
		self.ok(CREATE_STORE, amount=9000, date='2026-12-15', desc='Bus later',
			household=str(self.household.id), itemId=str(self.transport.id))

		data = self.ok(BUDGET, id=budget['id'])['budget']
		self.assertEqual(data['allocated'], 250000)
		self.assertEqual(data['spent'], 6000)
		self.assertEqual(data['remaining'], 244000)
		self.assertEqual(data['unbudgeted'], 2000)
		rows = {a['item']['name']: a for a in data['allocations']}
		self.assertEqual(rows['Transport']['remaining'], 44000)

	def test_store_item_validation(self):
		theirs = BudgetItem.objects.create(name='Theirs', user=make_user())
		disabled_system = BudgetItem.objects.create(name='Water')
		for item in (theirs, disabled_system):
			self.assertIn('Invalid budget item', self.error(
				CREATE_STORE, amount=1, date='2026-11-14', desc=f'x {item.name}',
				household=str(self.household.id), itemId=str(item.id)))
		self.assertIn("income", self.error(
			CREATE_STORE, amount=1, date='2026-11-14', desc='Salary', inflow=True,
			household=str(self.household.id), itemId=str(self.transport.id)))

	def test_overlap_and_status_rules(self):
		self.create(name='Nov', status='active', rent=1)
		self.assertIn('overlaps', self.error(
			CREATE_BUDGET, name='Mid', start='2026-12-01', end='2026-12-20', status='active',
			allocations=self.allocations(rent=1)))
		self.assertFalse(Budget.objects.filter(name='Mid').exists())  # rolled back
		self.assertIn('at least one item', self.error(
			CREATE_BUDGET, name='Empty', start='2027-01-01', end='2027-01-02', status='active',
			allocations=[]))

	def test_set_allocations_copy_and_close(self):
		budget = self.create(transport=100)
		set_alloc = '''mutation($id: ID!, $a: [AllocationInput!]!) {
		  setBudgetAllocations(budgetId: $id, allocations: $a) { budget { allocated } } }'''
		data = self.ok(set_alloc, id=budget['id'], a=self.allocations(transport=300, rent=700))
		self.assertEqual(data['setBudgetAllocations']['budget']['allocated'], 1000)
		self.assertIn('once', self.error(
			set_alloc, id=budget['id'], a=self.allocations(rent=1) + self.allocations(rent=2)))

		copy = '''mutation($id: ID!) { copyBudget(id: $id, name: "Dec", startDate: "2026-12-10",
		  endDate: "2027-01-31") { budget { status allocated } } }'''
		copied = self.ok(copy, id=budget['id'])['copyBudget']['budget']
		self.assertEqual(copied, {'status': 'draft', 'allocated': 1000.0})

		status = 'mutation($id: ID!, $s: String!) { setBudgetStatus(id: $id, status: $s) { budget { status } } }'
		self.ok(status, id=budget['id'], s='active')
		self.ok(status, id=budget['id'], s='closed')
		self.assertIn('closed', self.error(set_alloc, id=budget['id'], a=self.allocations(rent=1)))

	def test_budgets_are_private_and_filterable(self):
		mine = self.create(name='November', transport=1)
		other = make_user()
		self.assertIn('not found', self.error(BUDGET, user=other, id=mine['id']))
		listing = '''query($q: String, $from: Date, $to: Date) {
		  budgets(searchKey: $q, dateFrom: $from, dateTo: $to) { totalCount pageData { name } } }'''
		self.assertEqual(self.ok(listing, q='nov')['budgets']['totalCount'], 1)
		self.assertEqual(self.ok(listing, user=other)['budgets']['totalCount'], 0)
		self.assertEqual(
			self.ok(listing, **{'from': '2027-01-01', 'to': '2027-02-01'})['budgets']['totalCount'], 0)
		self.assertEqual(
			self.ok(listing, **{'from': '2026-12-01', 'to': '2026-12-01'})['budgets']['totalCount'], 1)

	def test_household_scope_is_reserved(self):
		query = 'query($h: ID) { budgets(householdId: $h) { totalCount } }'
		self.assertIn('not available yet', self.error(query, h=str(self.household.id)))

	def test_active_budget_query(self):
		self.create(status='active', rent=1)
		query = 'query($d: Date) { activeBudget(date: $d) { name } }'
		self.assertEqual(self.ok(query, d='2026-11-20')['activeBudget'], {'name': 'Nov'})
		self.assertIsNone(self.ok(query, d='2027-03-01')['activeBudget'])
		self.assertEqual(Budget.objects.get(name='Nov').status, BudgetStatus.ACTIVE)
		self.assertEqual(Store.objects.count(), 0)
