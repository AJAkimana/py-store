"""
Delete one user's application data (transactions, budgets, properties, ...) while keeping
their account: the user, their settings, two-factor setup, sign-in tokens, households and
household memberships. System reference data (currencies, default budget lines, system
budget items) is never touched.

Deleted: rows the user owns, plus rows owned by households where they're the only member.
Data of households shared with other members is kept, since it belongs to them too.

Dry run by default: it only prints what would be deleted. With --execute the database is
always backed up first (dbbackup); if the backup fails nothing is deleted.

	python manage.py purge_user_data --email someone@example.com            # dry run
	python manage.py purge_user_data --email someone@example.com --execute  # asks you to type DELETE
	python manage.py purge_user_data --email someone@example.com --execute --no-input

Rows are removed for good (hard delete), including ones already soft-deleted.
"""
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError, Q

from apps.household_members.models import HouseholdMember
from apps.users.models import User

CONFIRM_WORD = 'DELETE'


def _rows(label, condition):
	# all_objects includes soft-deleted rows; its hard_delete() really deletes
	# (the default manager's delete() only soft-deletes)
	return apps.get_model(label).all_objects.filter(condition)


def _ids(label, condition) -> list:
	# Frozen up front so dependent rows are still found after their parents are deleted
	return list(_rows(label, condition).values_list('pk', flat=True))


def backup_problem() -> str:
	"""Why a backup can't work with the current settings, or '' (catches it before asking to confirm)."""
	storage = settings.STORAGES.get('dbbackup', {})
	if 'dropbox' in storage.get('BACKEND', '').lower():
		if not storage.get('OPTIONS', {}).get('oauth2_access_token'):
			return 'DROPBOX_TOKEN is not set, so the required backup would fail'
	return ''


def solo_households(user: User) -> tuple:
	"""(households where the user is the only current member, households shared with others)."""
	mine = set(HouseholdMember.objects.filter(user=user).values_list('household_id', flat=True))
	shared = set(
		HouseholdMember.objects.filter(household_id__in=mine).exclude(user=user).values_list('household_id', flat=True)
	)
	return list(mine - shared), list(shared)


def build_plan(user: User, solo: list) -> list:
	"""(model label, rows to delete), children before parents because the foreign keys are PROTECT."""
	owned = Q(user=user) | Q(household__in=solo)
	budgets = _ids('budgets.Budget', owned)
	budget_items = _ids('budgets.BudgetItem', owned)  # never system items: those have no owner
	legacy_budgets = _ids('budgeting.Budget', owned)
	properties = _ids('properties.Property', Q(owner=user) | Q(household__in=solo))
	behaviors = _ids('behavior_ip.Behavior', owned)

	plan = (
		('stores.Store', owned),
		('stores.RecurringStore', Q(user=user)),
		('budgets.BudgetAllocation', Q(budget__in=budgets)),
		('budgets.ItemActivation', owned | Q(item__in=budget_items)),
		('budgets.Budget', Q(pk__in=budgets)),
		('budgets.BudgetItem', Q(pk__in=budget_items)),
		('budgeting.BudgetItem', Q(user=user) | Q(budget__in=legacy_budgets)),
		('budgeting.Budget', Q(pk__in=legacy_budgets)),
		('budgeting.UserBudgetLine', Q(user=user)),
		('budgeting.UserDefaultBudgetLine', Q(user=user)),
		('properties.PropDetail', Q(property__in=properties)),
		('properties.Property', Q(pk__in=properties)),
		('behavior_ip.BehaviorScore', Q(behavior__in=behaviors)),
		('behavior_ip.Behavior', Q(pk__in=behaviors)),
	)
	return [(label, _rows(label, condition)) for label, condition in plan]


class Command(BaseCommand):
	help = "Delete one user's data but keep their account and households (dry run by default)"

	def add_arguments(self, parser):
		parser.add_argument('-e', '--email', required=True, help='Email of the user whose data to delete')
		parser.add_argument('--execute', action='store_true', help='Actually delete (otherwise dry run)')
		parser.add_argument('--no-input', action='store_true', help=f"Don't ask to type {CONFIRM_WORD}")

	def handle(self, *args, **options):
		email = options['email'].strip()
		user = User.objects.filter(email__iexact=email).first()
		if user is None:
			raise CommandError(f'No user with email {email}')

		solo, shared = solo_households(user)
		self.stdout.write(f'User: {user.first_name} {user.last_name} <{user.email}>')
		self.stdout.write(f'Households: {len(solo)} only theirs (data deleted), {len(shared)} shared (data kept)')

		plan = build_plan(user, solo)
		counts = [(label, rows.count()) for label, rows in plan]
		total = sum(count for _, count in counts)
		width = max(len(label) for label, _ in counts)
		for label, count in counts:
			self.stdout.write(f'  {label.ljust(width)}  {count}')
		self.stdout.write(f'  {"Total".ljust(width)}  {total}')

		problem = backup_problem()
		if not options['execute']:
			if problem:
				self.stdout.write(self.style.ERROR(f'--execute would stop: {problem}.'))
			self.stdout.write(self.style.WARNING(
				'Dry run: nothing was deleted. Add --execute to back up the database and delete.'))
			return
		if total == 0:
			self.stdout.write(self.style.SUCCESS('Nothing to delete.'))
			return
		if problem:
			raise CommandError(f'{problem}. Nothing was deleted.')

		if not options['no_input']:
			answer = input(f'This permanently deletes {total} rows of {user.email} after backing up the database. '
				f'Type {CONFIRM_WORD} to continue: ')
			if answer.strip() != CONFIRM_WORD:
				raise CommandError('Cancelled, nothing was deleted.')

		self.stdout.write('Backing up the database...')
		try:
			call_command('dbbackup')
		except Exception as error:
			raise CommandError(f'Backup failed, nothing was deleted: {error}')
		self.stdout.write(self.style.SUCCESS('Backup done.'))

		try:
			with transaction.atomic():
				for label, rows in plan:
					deleted, _ = rows.hard_delete()
					self.stdout.write(f'  Deleted {label}: {deleted}')
		except ProtectedError as error:
			# e.g. another user's transaction uses one of this user's budget items
			blockers = sorted({f'{obj._meta.label} {obj.pk}' for obj in list(error.protected_objects)[:10]})
			raise CommandError(
				'Stopped, nothing was deleted: other users\' data still uses some of these rows: '
				+ ', '.join(blockers)
			)
		self.stdout.write(self.style.SUCCESS(f'Done. Deleted {total} rows; the account and households were kept.'))
