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
         $budgetId: String, $inflow: Boolean = false) {
  createStore(amount: $amount, actionDate: $date, description: $desc, householdId: $household,
              recordType: "use", isInflow: $inflow, itemId: $itemId, budgetId: $budgetId) {
    store { id item { name } budget { name } }
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

	def test_own_item_cannot_copy_a_common_item(self):
		BudgetItem.objects.create(name='Transport')
		self.assertIn('common item', self.error(CREATE_ITEM, name='transport'))
		BudgetItem.objects.create(name='Retired', is_active=False)
		self.ok(CREATE_ITEM, name='Retired')  # archived common items don't block


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

	def store(self, amount, on, desc, item=None, budget=None, **extra):
		return self.run_gql(
			CREATE_STORE, amount=amount, date=on, desc=desc, household=str(self.household.id),
			itemId=str(item.id) if item else None, budgetId=budget, **extra)

	def test_transactions_count_toward_the_budget_they_are_linked_to(self):
		monthly = self.create(status='active', transport=50000, rent=200000)
		house = self.create(
			name='House', start='2026-06-01', end='2027-06-30', status='active', transport=900000)

		result = self.store(6000, '2026-11-14', 'Moto', self.transport, monthly['id'])
		self.assertIsNone(result.errors, result.errors)
		self.assertEqual(result.data['createStore']['store']['budget'], {'name': 'Nov'})
		self.assertIsNone(self.store(40000, '2026-11-14', 'Truck', self.transport, house['id']).errors)
		self.assertIsNone(self.store(2000, '2026-11-15', 'Snacks').errors)
		self.assertIsNone(self.store(3000, '2026-11-15', 'Bus', self.transport).errors)

		data = self.ok(BUDGET, id=monthly['id'])['budget']
		self.assertEqual(data['allocated'], 250000)
		self.assertEqual(data['spent'], 6000)
		self.assertEqual(data['remaining'], 244000)
		self.assertEqual(data['unbudgeted'], 5000)  # snacks + bus: not linked to any budget
		rows = {a['item']['name']: a for a in data['allocations']}
		self.assertEqual(rows['Transport']['remaining'], 44000)
		self.assertEqual(self.ok(BUDGET, id=house['id'])['budget']['spent'], 40000)

		active = 'query($d: Date) { activeBudgets(date: $d) { name } }'
		names = [b['name'] for b in self.ok(active, d='2026-11-20')['activeBudgets']]
		self.assertEqual(names, ['Nov', 'House'])
		self.assertEqual(self.ok(active, d='2027-03-01')['activeBudgets'], [{'name': 'House'}])

	def test_store_budget_validation(self):
		budget = self.create(status='active', transport=100)
		draft = self.create(name='Draft', transport=100)
		cases = [
			(self.store(1, '2026-11-14', 'a', None, budget['id']), 'Choose which item'),
			(self.store(1, '2026-11-14', 'b', self.rent, budget['id']), "isn't planned"),
			(self.store(1, '2027-01-01', 'c', self.transport, budget['id']), 'outside'),
			(self.store(1, '2026-11-14', 'd', self.transport, draft['id']), 'not active'),
			(self.store(1, '2026-11-14', 'e', self.transport, budget['id'], inflow=True), 'income'),
		]
		for result, message in cases:
			self.assertTrue(result.errors, message)
			self.assertIn(message, str(result.errors[0]))
		theirs = BudgetItem.objects.create(name='Theirs', user=make_user())
		disabled_system = BudgetItem.objects.create(name='Water')
		for item in (theirs, disabled_system):
			self.assertIn('Invalid budget item', str(self.store(1, '2026-11-14', item.name, item).errors[0]))

	def test_editing_a_linked_transaction(self):
		budget = self.create(status='active', transport=100)
		store_id = self.store(5, '2026-11-14', 'Moto', self.transport, budget['id']).data[
			'createStore']['store']['id']
		self.ok('mutation($id: ID!, $s: String!) { setBudgetStatus(id: $id, status: $s) { message } }',
			id=budget['id'], s='closed')
		update = '''mutation($id: String!, $h: String!, $item: String, $budget: String, $amount: Float!) {
		  updateStore(id: $id, amount: $amount, actionDate: "2026-11-14", description: "Moto",
		    householdId: $h, recordType: "use", isInflow: false, itemId: $item, budgetId: $budget) {
		    message } }'''
		args = dict(id=store_id, h=str(self.household.id), item=str(self.transport.id))
		self.ok(update, budget=budget['id'], amount=7, **args)  # same link on a closed budget
		self.ok(update, budget=None, amount=7, **args)  # unlink
		self.assertIsNone(Store.objects.get(id=store_id).budget_id)
		# Linking again isn't allowed: the budget is closed
		self.assertIn('not active', self.error(update, budget=budget['id'], amount=7, **args))

	def test_status_rules(self):
		self.create(name='Nov', status='active', rent=1)
		self.create(name='Mid', start='2026-12-01', end='2026-12-20', status='active', rent=1)
		self.assertIn('at least one item', self.error(
			CREATE_BUDGET, name='Empty', start='2027-01-01', end='2027-01-02', status='active',
			allocations=[]))
		self.assertFalse(Budget.objects.filter(name='Empty').exists())  # rolled back

	def test_deleting_a_budget_keeps_its_transactions(self):
		budget = self.create(status='active', transport=100)
		self.store(5, '2026-11-14', 'Moto', self.transport, budget['id'])
		self.ok('mutation($id: ID!) { deleteBudget(id: $id) { message } }', id=budget['id'])
		store = Store.objects.get(description='Moto')
		self.assertIsNone(store.budget_id)
		self.assertEqual(store.item, self.transport)

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
