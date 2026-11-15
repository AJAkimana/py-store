from django.db import migrations


def forwards(apps, schema_editor):
	from apps.budgets.legacy import migrate_legacy_budgeting
	migrate_legacy_budgeting(apps, schema_editor)


def backwards(apps, schema_editor):
	from apps.budgets.legacy import undo_legacy_budgeting
	undo_legacy_budgeting(apps, schema_editor)


class Migration(migrations.Migration):

	dependencies = [
		('budgets', '0001_initial'),
		('budgeting', '0009_userdefaultbudgetline'),
		('stores', '0006_store_item'),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
