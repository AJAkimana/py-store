from django.core.management import call_command


def backup_filename():
	try:
		print({'message': 'Db backup starting...'})
		call_command('dbbackup')
		print({'message': 'Db backed up'})
	except Exception as error:
		print('Error backing up')
		print(error)


def send_weekly_summary():
	try:
		print({'message': 'Start sending...'})
		call_command('send_weekly_report')
		print({'message': 'Sent...'})
	except Exception as error:
		print('Error sending summary')
		print(error)
