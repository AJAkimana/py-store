from graphql_jwt.backends import JSONWebTokenBackend
from graphql_jwt.exceptions import JSONWebTokenError
from graphql_jwt.utils import get_credentials, get_payload

# The UI signs the user out when it sees this message (ui/src/graphql/utils/links.ts)
SESSION_ENDED_MESSAGE = 'Your session has ended. Please sign in again.'


class SessionAwareJSONWebTokenBackend(JSONWebTokenBackend):
	"""
	JWT auth that also rejects access tokens issued before the user's last password
	reset, so a reset signs out every device right away instead of when tokens expire.
	"""

	def authenticate(self, request=None, **kwargs):
		user = super().authenticate(request=request, **kwargs)
		if user is None or not user.password_changed_at:
			return user

		payload = get_payload(get_credentials(request, **kwargs), request)
		issued_at = payload.get('origIat')
		# origIat has whole-second precision, so a token from the same second is rejected too
		if issued_at is None or issued_at <= int(user.password_changed_at.timestamp()):
			raise JSONWebTokenError(SESSION_ENDED_MESSAGE)
		return user
