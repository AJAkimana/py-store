from django.db import migrations


def forwards(apps, schema_editor):
	from apps.budgets.legacy import link_transactions_to_budgets
	link_transactions_to_budgets(apps, schema_editor)


def backwards(apps, schema_editor):
	from apps.budgets.legacy import unlink_transactions_from_budgets
	unlink_transactions_from_budgets(apps, schema_editor)


class Migration(migrations.Migration):

	dependencies = [
		('budgets', '0002_copy_legacy_budgeting'),
		('stores', '0007_store_budget'),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
