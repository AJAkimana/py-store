"""
One-off copy of the legacy `apps.budgeting` data into `apps.budgets`.

Called from migration 0002 with the historical app registry; kept here so tests can
run it against fixtures. Old rows are left untouched, so the old API keeps working
until it is removed.

Mapping
- DefaultBudgetLine        -> BudgetItem (system), same id
- UserBudgetLine           -> BudgetItem (owned by the user), same id, amount -> default_amount
- UserDefaultBudgetLine    -> ItemActivation
- Budget                   -> Budget (owned by the user), same id; approved -> active/closed,
                              draft/pending -> draft. The old `household` column only recorded
                              where the budget was created, so it is not copied as owner.
- BudgetItem in a budget   -> BudgetAllocation (amounts of the same item in one budget summed)
- BudgetItem without a line-> a user BudgetItem created from its name
- BudgetItem without budget (old "recurring" items) -> default_amount of its item
- Store.budget_item        -> Store.item
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal


def _clean_name(name):
	return (name or '').strip()[:100] or 'Unnamed'


class _Migrator:
	def __init__(self, apps, today=None, log=print):
		self.today = today or date.today()
		self.log = log
		self.Item = apps.get_model('budgets', 'BudgetItem')
		self.Activation = apps.get_model('budgets', 'ItemActivation')
		self.Budget = apps.get_model('budgets', 'Budget')
		self.Allocation = apps.get_model('budgets', 'BudgetAllocation')
		self.Store = apps.get_model('stores', 'Store')
		self.OldDefaultLine = apps.get_model('budgeting', 'DefaultBudgetLine')
		self.OldUserDefaultLine = apps.get_model('budgeting', 'UserDefaultBudgetLine')
		self.OldUserLine = apps.get_model('budgeting', 'UserBudgetLine')
		self.OldBudget = apps.get_model('budgeting', 'Budget')
		self.OldItem = apps.get_model('budgeting', 'BudgetItem')

		self.items = {}  # id -> new BudgetItem
		self.alive_items = {}  # (user_id | None, lower(name)) -> new BudgetItem
		self.line_map = {}  # old line id -> new item id
		self.old_item_map = {}  # old budgeting.BudgetItem id -> new item id
		self.activations = {}  # (item_id, user_id) -> enabled
		self.budget_ids = set()

	# --- items -------------------------------------------------------------------------

	def _item(self, *, id=None, name, user_id, description='', default_amount=0,
			is_active=True, deleted_at=None, created_at=None):
		"""Create an item, or reuse the alive one with the same owner and name."""
		name = _clean_name(name)
		key = (user_id, name.lower())
		if deleted_at is None and key in self.alive_items:
			existing = self.alive_items[key]
			if is_active and not existing.is_active:
				existing.is_active = True
				existing.save(update_fields=['is_active'])
			return existing
		fields = dict(
			name=name, user_id=user_id, description=description or '',
			default_amount=Decimal(str(default_amount or 0)), is_active=is_active,
			deleted_at=deleted_at,
		)
		if id is not None:
			fields['id'] = id
		if created_at is not None:
			fields['created_at'] = created_at
		item = self.Item._base_manager.create(**fields)
		self.items[item.id] = item
		if deleted_at is None:
			self.alive_items[key] = item
		return item

	def migrate_lines(self):
		for line in self.OldDefaultLine._base_manager.order_by('created_at'):
			item = self._item(
				id=line.id, name=line.name, user_id=None, description=line.description,
				is_active=line.active and line.enabled, deleted_at=line.deleted_at,
				created_at=line.created_at)
			self.line_map[line.id] = item.id

		for line in self.OldUserLine._base_manager.order_by('created_at'):
			item = self._item(
				id=line.id, name=line.name, user_id=line.user_id, description=line.description,
				default_amount=line.amount, is_active=line.active and line.enabled,
				deleted_at=line.deleted_at, created_at=line.created_at)
			self.line_map[line.id] = item.id

		for udl in self.OldUserDefaultLine._base_manager.filter(deleted_at__isnull=True):
			key = (self.line_map[udl.line_id], udl.user_id)
			self.activations[key] = self.activations.get(key, False) or udl.enabled

	# --- budgets -----------------------------------------------------------------------

	def _status(self, old):
		if old.status == 'approved':
			return 'closed' if old.end_date < self.today else 'active'
		return 'draft'

	def migrate_budgets(self):
		taken = defaultdict(set)  # user_id -> lower(names) of alive budgets
		skipped = 0
		for old in self.OldBudget._base_manager.order_by('start_date', 'created_at'):
			if old.user_id is None:
				skipped += 1
				continue
			name = _clean_name(old.name)
			if old.deleted_at is None:
				base, n = name, 2
				while name.lower() in taken[old.user_id]:
					name = f'{base[:94]} ({n})'
					n += 1
				taken[old.user_id].add(name.lower())
			self.Budget._base_manager.create(
				id=old.id, name=name, description=old.description or '',
				start_date=old.start_date, end_date=max(old.start_date, old.end_date),
				status=self._status(old), user_id=old.user_id, created_by_id=old.user_id,
				deleted_at=old.deleted_at, created_at=old.created_at)
			self.budget_ids.add(old.id)
		if skipped:
			self.log(f'  budgets: skipped {skipped} legacy budget(s) without a user')

	# --- budget items -> allocations ---------------------------------------------------

	def migrate_budget_items(self):
		allocations = defaultdict(Decimal)  # (budget_id, item_id) -> amount
		skipped = 0
		for old in self.OldItem._base_manager.select_related('budget').order_by('created_at'):
			owner_id = old.user_id or (old.budget.user_id if old.budget_id else None)
			line_id = old.d_budget_line_id or old.u_budget_line_id
			if line_id:
				item_id = self.line_map[line_id]
			elif owner_id:
				item_id = self._item(name=old.name, user_id=owner_id).id
			else:
				skipped += 1
				continue
			self.old_item_map[old.id] = item_id
			item = self.items[item_id]
			if item.user_id is None and owner_id:
				self.activations.setdefault((item_id, owner_id), True)

			if old.deleted_at is not None:
				continue
			amount = Decimal(str(old.amount or 0))
			if old.budget_id in self.budget_ids:
				allocations[(old.budget_id, item_id)] += amount
			elif old.budget_id is None and item.user_id and not item.default_amount:
				item.default_amount = max(amount, Decimal('0'))
				item.save(update_fields=['default_amount'])

		self.Allocation._base_manager.bulk_create([
			self.Allocation(budget_id=budget_id, item_id=item_id, amount=max(amount, Decimal('0')))
			for (budget_id, item_id), amount in allocations.items()
		])
		if skipped:
			self.log(f'  budget items: skipped {skipped} legacy item(s) without an owner')

	# --- transactions ------------------------------------------------------------------

	def migrate_stores(self):
		by_item = defaultdict(list)
		for store_id, old_item_id, user_id in self.Store._base_manager.filter(
				budget_item__isnull=False).values_list('id', 'budget_item_id', 'user_id'):
			item_id = self.old_item_map.get(old_item_id)
			if item_id is None:
				continue
			by_item[item_id].append(store_id)
			if self.items[item_id].user_id is None:
				self.activations.setdefault((item_id, user_id), True)
		for item_id, store_ids in by_item.items():
			self.Store._base_manager.filter(id__in=store_ids).update(item_id=item_id)
		return sum(len(ids) for ids in by_item.values())

	def save_activations(self):
		self.Activation._base_manager.bulk_create([
			self.Activation(item_id=item_id, user_id=user_id, enabled=enabled)
			for (item_id, user_id), enabled in self.activations.items()
		])

	def run(self):
		self.migrate_lines()
		self.migrate_budgets()
		self.migrate_budget_items()
		stores = self.migrate_stores()
		self.save_activations()
		self.log(
			f'  budgets: migrated {len(self.items)} items, {len(self.budget_ids)} budgets, '
			f'{self.Allocation._base_manager.count()} allocations, {len(self.activations)} activations, '
			f'{stores} tagged transactions')


def migrate_legacy_budgeting(apps, schema_editor=None, today=None, log=print):
	_Migrator(apps, today=today, log=log).run()


def undo_legacy_budgeting(apps, schema_editor=None):
	apps.get_model('stores', 'Store')._base_manager.update(item=None)
	for model in ('BudgetAllocation', 'ItemActivation', 'Budget', 'BudgetItem'):
		apps.get_model('budgets', model)._base_manager.all().delete()
