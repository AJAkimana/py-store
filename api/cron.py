from django.core.management import call_command, CommandError


def backup_db():
	print("Clone")
	try:
		call_command('dbbackup')
	except CommandError as error:
		print(error)
