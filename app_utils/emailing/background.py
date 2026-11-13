import threading

from django.db import transaction

from d2dstore.logger import logger


def send_after_commit(send, *args, description: str = 'email'):
	"""
	Run an email sender (returning {has_error, message}) in a background thread once
	the current transaction commits, so SMTP doesn't slow the request. Failures are
	only logged.
	"""
	def run():
		try:
			result = send(*args)
			if result and result.get('has_error'):
				logger.warning(f'Could not send {description}: {result.get("message")}')
		except Exception as error:  # never let an email break the request
			logger.warning(f'Could not send {description}: {error}')

	transaction.on_commit(lambda: threading.Thread(target=run, daemon=True).start())
