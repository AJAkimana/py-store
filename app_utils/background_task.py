import calendar

from django.core.management import call_command
from django.utils.timezone import now


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
		print({'message': 'Start sending weekly report...'})
		call_command('send_transaction_report', "-t", "weekly")
		print({'message': 'Weekly report Sent...'})
	except Exception as error:
		print('Error sending summary')
		print(error)


def send_monthly_summary(is_manual=False):
	today = now().date()
	last_day = calendar.monthrange(today.year, today.month)[1]  # Get last day of the month

	if today.day == last_day or is_manual:
		try:
			print({'message': 'Start sending monthly report...'})
			call_command('send_transaction_report', "-t", "monthly")
			print({'message': 'Monthly report Sent...'})
		except Exception as error:
			print('Error sending summary')
			print(error)
