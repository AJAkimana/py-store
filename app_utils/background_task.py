import os

from django.core.management import call_command
# from django_cron import CronJobBase, Schedule


# class BackupDb(CronJobBase):
# 	RUN_EVERY_MINS = 2  # every 2 hours
#
# 	schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
# 	code = 'store.backup_db'  # a unique code

def backup_filename():
	try:
		print({'message': 'Db backup starting...'})
		call_command('dbbackup')
		res = {'message': 'Db backed up'}
		print(res)
	except Exception as error:
		print(error)
