"""
Delete all application data (transactions, budgets, properties, ...) while keeping the
accounts: users, their settings, two-factor setup, sign-in tokens, households and household
memberships, plus system reference data (currencies, default budget lines, system budget items).

Dry run by default: it only prints what would be deleted.

	python manage.py purge_user_data                  # dry run, shows counts
	python manage.py purge_user_data --execute        # asks you to type DELETE, then deletes
	python manage.py purge_user_data --execute --backup --no-input

Rows are removed for good (hard delete), including ones already soft-deleted.
"""
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

# Children before parents, because the foreign keys are PROTECT.
# Each entry: (model label, filter limiting what is deleted, or None for every row)
PURGE_PLAN = (
	('stores.Store', None),
	('stores.RecurringStore', None),
	('budgets.BudgetAllocation', None),
	('budgets.Budget', None),
	('budgets.ItemActivation', None),
	# System items (no owner) are reference data and stay
	('budgets.BudgetItem', Q(user__isnull=False) | Q(household__isnull=False)),
	('budgeting.BudgetItem', None),
	('budgeting.Budget', None),
	('budgeting.UserBudgetLine', None),
	('budgeting.UserDefaultBudgetLine', None),
	('properties.PropDetail', None),
	('properties.Property', None),
	('behavior_ip.BehaviorScore', None),
	('behavior_ip.Behavior', None),
	('manage_system.Facility', None),
	('manage_system.Salary', None),
)

CONFIRM_WORD = 'DELETE'


class Command(BaseCommand):
	help = 'Delete all application data but keep users, households and system reference data (dry run by default)'

	def add_arguments(self, parser):
		parser.add_argument('--execute', action='store_true', help='Actually delete (otherwise dry run)')
		parser.add_argument('--no-input', action='store_true', help=f"Don't ask to type {CONFIRM_WORD}")
		parser.add_argument('--backup', action='store_true', help='Run dbbackup first and stop if it fails')

	def handle(self, *args, **options):
		plan = [(label, self._queryset(label, condition)) for label, condition in PURGE_PLAN]
		counts = [(label, queryset.count()) for label, queryset in plan]
		total = sum(count for _, count in counts)

		width = max(len(label) for label, _ in counts)
		for label, count in counts:
			self.stdout.write(f'  {label.ljust(width)}  {count}')
		self.stdout.write(f'  {"Total".ljust(width)}  {total}')

		if not options['execute']:
			self.stdout.write(self.style.WARNING('Dry run: nothing was deleted. Add --execute to delete.'))
			return
		if total == 0:
			self.stdout.write(self.style.SUCCESS('Nothing to delete.'))
			return

		if not options['no_input']:
			answer = input(f'This permanently deletes {total} rows. Type {CONFIRM_WORD} to continue: ')
			if answer.strip() != CONFIRM_WORD:
				raise CommandError('Cancelled, nothing was deleted.')

		if options['backup']:
			self.stdout.write('Backing up the database...')
			try:
				call_command('dbbackup')
			except Exception as error:
				raise CommandError(f'Backup failed, nothing was deleted: {error}')

		with transaction.atomic():
			for label, queryset in plan:
				deleted, _ = queryset.hard_delete()
				self.stdout.write(f'  Deleted {label}: {deleted}')
		self.stdout.write(self.style.SUCCESS(f'Done. Deleted {total} rows; users and households were kept.'))

	@staticmethod
	def _queryset(label, condition):
		# all_objects includes soft-deleted rows; its hard_delete() really deletes
		# (the default manager's delete() only soft-deletes)
		queryset = apps.get_model(label).all_objects.all()
		return queryset.filter(condition) if condition is not None else queryset
