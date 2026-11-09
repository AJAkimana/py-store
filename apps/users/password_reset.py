"""
Forgotten password: email a one-time code, then set a new password with it.

Reuses the email-code challenges from 'apps.users.mfa' (expiry, attempt limit,
resend throttle). Nothing here reveals whether an email has an account, and a reset
never signs the user in: they sign in afterwards, so two-factor still applies.
"""
import uuid

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.users import mfa
from apps.users.models import User, MfaChallenge, MfaChallengePurpose, MfaMethod
from apps.users.session import revoke_refresh_tokens
from d2dstore.logger import logger

PURPOSE = MfaChallengePurpose.PASSWORD_RESET


def _fake_token() -> str:
	# Looks like a real token but matches no challenge, so confirming always fails
	return mfa.sign_challenge(MfaChallenge(id=uuid.uuid4()))


def _send_quietly(challenge: MfaChallenge):
	# Throttle and SMTP errors stay server-side: the response must look the same either way
	try:
		mfa.send_email_code(challenge)
	except mfa.MfaError as error:
		logger.info(f'[Password reset] Code not sent to {challenge.user.email}: {error}')


def request_password_reset(email: str) -> str:
	"""
	Email a reset code if an active account uses this email. Always returns a token,
	so callers can't tell whether the account exists. Calling it again resends the
	code (at most once a minute and MAX_EMAIL_SENDS times per code).
	"""
	user = User.objects.filter(email__iexact=(email or '').strip(), is_active=True).first()
	if user is None:
		return _fake_token()

	now = timezone.now()
	open_challenge = MfaChallenge.objects.filter(
		user=user, purpose=PURPOSE, consumed_at__isnull=True,
		expires_at__gt=now, attempts__lt=mfa.MAX_ATTEMPTS,
	).first()
	if open_challenge:
		_send_quietly(open_challenge)
		return mfa.sign_challenge(open_challenge)

	# A used-up code was sent less than a minute ago: don't send another yet
	recent = MfaChallenge.objects.filter(
		user=user, purpose=PURPOSE, last_sent_at__gt=now - mfa.RESEND_INTERVAL,
	).first()
	if recent:
		return mfa.sign_challenge(recent)

	challenge = mfa.create_challenge(user, PURPOSE)
	_send_quietly(challenge)
	return mfa.sign_challenge(challenge)


def reset_password_with_code(reset_token: str, code: str, new_password: str):
	"""
	Set a new password with a reset code and sign out every device, including the
	one making the request: refresh tokens and REST tokens are revoked, and access
	tokens issued before now are rejected (see SessionAwareJSONWebTokenBackend).
	Emails the user an alert.
	"""
	challenge = mfa.load_challenge(reset_token, PURPOSE)
	user = challenge.user
	if not user.is_active:
		raise mfa.MfaError(mfa.INVALID_CODE_MESSAGE)

	try:
		validate_password(new_password or '', user)
	except ValidationError as error:
		raise mfa.MfaError(' '.join(error.messages))

	mfa.verify_challenge_or_raise(challenge, MfaMethod.EMAIL.value, code)

	with transaction.atomic():
		user.set_password(new_password)
		# Proving access to the email is enough to clear "create a new password first"
		user.is_verified = True
		user.password_changed_at = timezone.now()
		user.save(update_fields=['password', 'is_verified', 'password_changed_at'])
		revoke_refresh_tokens(user)
		Token.objects.filter(user=user).delete()
		mfa.notify_mfa_change(user, 'password_reset')
	return user
