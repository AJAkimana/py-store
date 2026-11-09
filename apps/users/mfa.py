"""
Two-factor authentication service: TOTP (authenticator app), email codes and recovery codes.

Mutations call these functions and turn 'MfaError' into a GraphQLError. Nothing here
issues a session; that happens in 'apps.users.session.issue_session' once a check passes.
"""
import base64
import hashlib
import hmac
import secrets
import threading
from datetime import timedelta

import pyotp
import segno
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app_utils.emailing.auth_email import send_mfa_code_email, send_mfa_change_email
from d2dstore.logger import logger
from apps.users.models import (
	User, UserMfa, MfaMethod, MfaChallenge, MfaChallengePurpose, MfaRecoveryCode,
)

CHALLENGE_TTL = timedelta(minutes=10)
EMAIL_CODE_DIGITS = 6
MAX_ATTEMPTS = 5
MAX_EMAIL_SENDS = 5
RESEND_INTERVAL = timedelta(seconds=60)
RECOVERY_CODE_COUNT = 10
# Per-user limit across login challenges, so logging in again doesn't give fresh guesses
MAX_FAILED_LOGIN_CODES = 10
LOGIN_LOCK_DURATION = timedelta(minutes=15)
TOTP_VALID_WINDOW = 1  # accept the previous and next 30 s step for clock drift

_SIGNER_SALT = 'apps.users.mfa.challenge'
_RECOVERY_ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'  # no 0/o, 1/l/i

# One message for every failed check, so callers can't tell an expired
# challenge from a wrong code or a used recovery code
INVALID_CODE_MESSAGE = 'Invalid or expired verification code'


class MfaError(Exception):
	pass


# ---------------------------------------------------------------------------
# Secrets and hashing
# ---------------------------------------------------------------------------

def _fernet() -> Fernet:
	key = settings.MFA_ENCRYPTION_KEY
	if not key:
		if not settings.DEBUG:
			raise ImproperlyConfigured('MFA_ENCRYPTION_KEY must be set when DEBUG is off')
		# Development only: derive a stable key from SECRET_KEY
		digest = hashlib.sha256(f'{settings.SECRET_KEY}:mfa-encryption'.encode()).digest()
		key = base64.urlsafe_b64encode(digest)
	return Fernet(key)


def encrypt_secret(secret: str) -> str:
	return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
	try:
		return _fernet().decrypt(token.encode()).decode()
	except InvalidToken as error:
		raise ImproperlyConfigured('Cannot decrypt a TOTP secret; was MFA_ENCRYPTION_KEY changed?') from error


def _normalize_code(code: str) -> str:
	return ''.join((code or '').split()).replace('-', '').lower()


def hash_code(code: str) -> str:
	"""
	Keyed HMAC-SHA256. Email codes are short-lived and attempt-limited, and recovery
	codes are random, so a slow password hash isn't needed and an HMAC lets recovery
	codes be looked up directly.
	"""
	key = f'{settings.SECRET_KEY}:mfa-code'.encode()
	return hmac.new(key, _normalize_code(code).encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# User MFA state
# ---------------------------------------------------------------------------

def get_user_mfa(user: User):
	"""Return the user's UserMfa, or None if 2FA was never set up."""
	return UserMfa.objects.filter(user=user).first()


def is_mfa_enabled(user: User) -> bool:
	mfa = get_user_mfa(user)
	return bool(mfa and mfa.is_enabled)


def get_mfa_status(user: User) -> dict:
	"""Public 2FA status for the settings page. Never includes secrets."""
	mfa = get_user_mfa(user)
	methods = mfa.enabled_methods if mfa else []
	return {
		'enabled': bool(methods),
		'totp_enabled': MfaMethod.TOTP.value in methods,
		'email_enabled': MfaMethod.EMAIL.value in methods,
		'methods': methods,
		'preferred_method': mfa.default_method if mfa and methods else None,
		'recovery_codes_remaining': recovery_codes_remaining(user) if methods else 0,
	}


def _get_or_create_mfa(user: User) -> UserMfa:
	mfa, _ = UserMfa.objects.get_or_create(user=user)
	return mfa


def _save_mfa(mfa: UserMfa, fields: list):
	# BaseModel.updated_at isn't auto_now, so keep it current here
	mfa.updated_at = timezone.now()
	mfa.save(update_fields=[*fields, 'updated_at'])


# ---------------------------------------------------------------------------
# Recovery codes
# ---------------------------------------------------------------------------

def _new_recovery_code() -> str:
	raw = ''.join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
	return f'{raw[:5]}-{raw[5:]}'


@transaction.atomic
def generate_recovery_codes(user: User) -> list:
	"""Replace the user's recovery codes. The plain codes are returned once and never stored."""
	MfaRecoveryCode.all_objects.filter(user=user).hard_delete()
	codes = set()
	while len(codes) < RECOVERY_CODE_COUNT:
		codes.add(_new_recovery_code())
	codes = sorted(codes)
	MfaRecoveryCode.objects.bulk_create(
		[MfaRecoveryCode(user=user, code_hash=hash_code(code)) for code in codes]
	)
	return codes


def recovery_codes_remaining(user: User) -> int:
	return MfaRecoveryCode.objects.filter(user=user, used_at__isnull=True).count()


def use_recovery_code(user: User, code: str) -> bool:
	if not _normalize_code(code):
		return False
	# Conditional update so two requests can't both spend the same code
	updated = MfaRecoveryCode.objects.filter(
		user=user, code_hash=hash_code(code), used_at__isnull=True,
	).update(used_at=timezone.now())
	return updated == 1


# ---------------------------------------------------------------------------
# TOTP (authenticator app)
# ---------------------------------------------------------------------------

def _match_totp_step(secret: str, code: str):
	"""Return the time step the code belongs to, or None."""
	code = _normalize_code(code)
	if not code.isdigit():
		return None
	totp = pyotp.TOTP(secret)
	current = totp.timecode(timezone.now())
	for step in range(current - TOTP_VALID_WINDOW, current + TOTP_VALID_WINDOW + 1):
		if hmac.compare_digest(totp.generate_otp(step), code):
			return step
	return None


def _accept_totp(mfa: UserMfa, code: str) -> bool:
	"""Check a code against the stored secret and record its step so it can't be reused."""
	if not mfa.totp_secret_encrypted:
		return False
	step = _match_totp_step(decrypt_secret(mfa.totp_secret_encrypted), code)
	if step is None:
		return False
	# Only one request can move the step forward, which blocks replays and races
	updated = UserMfa.objects.filter(pk=mfa.pk).filter(
		Q(totp_last_used_step__isnull=True) | Q(totp_last_used_step__lt=step)
	).update(totp_last_used_step=step, updated_at=timezone.now())
	if updated:
		mfa.totp_last_used_step = step
	return updated == 1


def verify_totp(user: User, code: str) -> bool:
	mfa = get_user_mfa(user)
	return bool(mfa and mfa.totp_enabled and _accept_totp(mfa, code))


def start_totp_setup(user: User) -> dict:
	"""
	Create a new pending secret. Returns the secret, the otpauth:// URI and a QR code
	(SVG data URI) for the authenticator app. TOTP stays off until confirm_totp_setup.
	"""
	mfa = _get_or_create_mfa(user)
	if mfa.totp_enabled:
		raise MfaError('The authenticator app is already set up. Turn it off before adding a new one.')

	secret = pyotp.random_base32()
	mfa.totp_secret_encrypted = encrypt_secret(secret)
	mfa.totp_confirmed_at = None
	mfa.totp_last_used_step = None
	_save_mfa(mfa, ['totp_secret_encrypted', 'totp_confirmed_at', 'totp_last_used_step'])

	uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.MFA_ISSUER_NAME)
	qr_svg = segno.make(uri, error='m').svg_data_uri(scale=5, border=2)
	return {'secret': secret, 'otpauth_uri': uri, 'qr_svg': qr_svg}


@transaction.atomic
def confirm_totp_setup(user: User, code: str) -> list:
	"""
	Turn TOTP on once the user proves their app works. Returns new recovery codes
	if this is the user's first 2FA method, otherwise an empty list.
	"""
	mfa = UserMfa.objects.select_for_update().filter(user=user).first()
	if not mfa or not mfa.totp_secret_encrypted:
		raise MfaError('Start the authenticator app setup first')
	if mfa.totp_enabled:
		raise MfaError('The authenticator app is already set up')

	was_enabled = mfa.is_enabled
	if not _accept_totp(mfa, code):
		raise MfaError(INVALID_CODE_MESSAGE)

	mfa.totp_confirmed_at = timezone.now()
	if not mfa.preferred_method:
		mfa.preferred_method = MfaMethod.TOTP.value
	_save_mfa(mfa, ['totp_confirmed_at', 'preferred_method'])
	notify_mfa_change(user, 'totp_enabled')
	return [] if was_enabled else generate_recovery_codes(user)


# ---------------------------------------------------------------------------
# Challenges and email codes
# ---------------------------------------------------------------------------

def sign_challenge(challenge: MfaChallenge) -> str:
	return signing.TimestampSigner(salt=_SIGNER_SALT).sign(str(challenge.id))


def load_challenge(token: str, purpose: str, user: User = None) -> MfaChallenge:
	"""
	Resolve a signed challenge token. Raises MfaError if the token is tampered with,
	expired, used up or for another purpose (or another user, when 'user' is given).
	"""
	try:
		challenge_id = signing.TimestampSigner(salt=_SIGNER_SALT).unsign(
			token or '', max_age=CHALLENGE_TTL,
		)
	except signing.BadSignature:
		raise MfaError(INVALID_CODE_MESSAGE)

	challenge = MfaChallenge.objects.select_related('user').filter(id=challenge_id, purpose=purpose).first()
	if (
		challenge is None
		or challenge.consumed_at is not None
		or challenge.expires_at <= timezone.now()
		or challenge.attempts >= MAX_ATTEMPTS
		or (user is not None and challenge.user_id != user.pk)
	):
		raise MfaError(INVALID_CODE_MESSAGE)
	return challenge


def create_challenge(user: User, purpose: str) -> MfaChallenge:
	# A user has at most one open challenge per purpose
	MfaChallenge.all_objects.filter(user=user, purpose=purpose).hard_delete()
	return MfaChallenge.objects.create(
		user=user, purpose=purpose, expires_at=timezone.now() + CHALLENGE_TTL,
	)


def send_email_code(challenge: MfaChallenge):
	"""Generate a fresh code for the challenge and email it. Throttled per challenge."""
	now = timezone.now()
	if challenge.last_sent_at and now - challenge.last_sent_at < RESEND_INTERVAL:
		wait = int((RESEND_INTERVAL - (now - challenge.last_sent_at)).total_seconds()) + 1
		raise MfaError(f'Please wait {wait} seconds before requesting a new code')
	if challenge.send_count >= MAX_EMAIL_SENDS:
		raise MfaError('Too many codes requested. Sign in again to get a new one.')

	code = f'{secrets.randbelow(10 ** EMAIL_CODE_DIGITS):0{EMAIL_CODE_DIGITS}d}'
	challenge.code_hash = hash_code(code)
	challenge.last_sent_at = now
	challenge.send_count += 1
	# A new code also restarts the expiry and the attempt count
	challenge.expires_at = now + CHALLENGE_TTL
	challenge.attempts = 0
	challenge.updated_at = now
	challenge.save(update_fields=[
		'code_hash', 'last_sent_at', 'send_count', 'expires_at', 'attempts', 'updated_at',
	])

	if settings.DEBUG:
		# Development only, so the flow works without SMTP. Never runs with DEBUG off
		logger.info(f'[MFA] Email code for {challenge.user.email}: {code}')

	sent = send_mfa_code_email(challenge.user, code, int(CHALLENGE_TTL.total_seconds() // 60))
	if sent['has_error']:
		if settings.DEBUG:
			logger.warning(f'[MFA] Email not sent ({sent["message"]}); use the code logged above')
			return
		raise MfaError('We could not send the verification email. Try again or use another method.')


def _check_email_code(challenge: MfaChallenge, code: str) -> bool:
	if not challenge.code_hash or not _normalize_code(code):
		return False
	return hmac.compare_digest(challenge.code_hash, hash_code(code))


@transaction.atomic
def verify_challenge(challenge: MfaChallenge, method: str, code: str) -> User:
	"""
	Check a code against a challenge and consume it on success. Every attempt counts
	toward MAX_ATTEMPTS, whatever the method. Returns the challenge's user.
	"""
	# Lock the row so concurrent attempts are counted one by one
	challenge = MfaChallenge.objects.select_for_update().select_related('user').get(pk=challenge.pk)
	if challenge.consumed_at is not None or challenge.expires_at <= timezone.now() \
		or challenge.attempts >= MAX_ATTEMPTS:
		raise MfaError(INVALID_CODE_MESSAGE)

	challenge.attempts += 1
	challenge.updated_at = timezone.now()
	challenge.save(update_fields=['attempts', 'updated_at'])

	user = challenge.user
	mfa = get_user_mfa(user)
	enabled = mfa.enabled_methods if mfa else []

	if challenge.purpose == MfaChallengePurpose.SETUP_EMAIL:
		ok = method == MfaMethod.EMAIL and _check_email_code(challenge, code)
	elif method == MfaMethod.TOTP:
		ok = MfaMethod.TOTP.value in enabled and _accept_totp(mfa, code)
	elif method == MfaMethod.EMAIL:
		ok = MfaMethod.EMAIL.value in enabled and _check_email_code(challenge, code)
	elif method == MfaMethod.RECOVERY:
		ok = bool(enabled) and use_recovery_code(user, code)
	else:
		ok = False

	counts_toward_lock = challenge.purpose in _LOCKED_PURPOSES and mfa
	if not ok:
		if counts_toward_lock:
			_record_failed_code(mfa)
		# Return instead of raising so the transaction commits the counted attempt
		return None

	challenge.consumed_at = timezone.now()
	challenge.save(update_fields=['consumed_at'])
	if counts_toward_lock:
		_reset_failed_codes(mfa)
	return user


# Challenges that check an already-enabled factor share the per-user failure lock
_LOCKED_PURPOSES = (MfaChallengePurpose.LOGIN, MfaChallengePurpose.SENSITIVE)


def _record_failed_code(mfa: UserMfa):
	mfa = UserMfa.objects.select_for_update().get(pk=mfa.pk)
	mfa.failed_attempts += 1
	if mfa.failed_attempts >= MAX_FAILED_LOGIN_CODES:
		mfa.failed_attempts = 0
		mfa.locked_until = timezone.now() + LOGIN_LOCK_DURATION
		# Drop open challenges so the lock applies right away
		MfaChallenge.all_objects.filter(user_id=mfa.user_id, purpose__in=_LOCKED_PURPOSES).hard_delete()
	_save_mfa(mfa, ['failed_attempts', 'locked_until'])


def _reset_failed_codes(mfa: UserMfa):
	if mfa.failed_attempts or mfa.locked_until:
		UserMfa.objects.filter(pk=mfa.pk).update(failed_attempts=0, locked_until=None)


def _ensure_not_locked(mfa: UserMfa):
	if mfa.locked_until and mfa.locked_until > timezone.now():
		minutes = int((mfa.locked_until - timezone.now()).total_seconds() // 60) + 1
		raise MfaError(f'Too many incorrect codes. Try again in {minutes} minutes.')


def verify_challenge_or_raise(challenge: MfaChallenge, method: str, code: str) -> User:
	user = verify_challenge(challenge, method, code)
	if user is None:
		raise MfaError(INVALID_CODE_MESSAGE)
	return user


# ---------------------------------------------------------------------------
# Login and email setup flows
# ---------------------------------------------------------------------------

def start_login_challenge(user: User) -> dict:
	"""
	Call after the password check when 2FA is on. Sends the email code right away if
	email is the default method. Returns what the login mutation sends to the client.
	"""
	mfa = get_user_mfa(user)
	if not mfa or not mfa.is_enabled:
		raise MfaError('Two-factor authentication is not enabled for this account')
	_ensure_not_locked(mfa)

	challenge = create_challenge(user, MfaChallengePurpose.LOGIN)
	if mfa.default_method == MfaMethod.EMAIL:
		send_email_code(challenge)
	return {
		'mfa_token': sign_challenge(challenge),
		'methods': mfa.enabled_methods,
		'default_method': mfa.default_method,
	}


def resend_login_email_code(mfa_token: str):
	"""Send (or resend) the login code by email; also used when switching to email."""
	challenge = load_challenge(mfa_token, MfaChallengePurpose.LOGIN)
	mfa = get_user_mfa(challenge.user)
	if not mfa or not mfa.email_otp_enabled:
		raise MfaError('Email codes are not enabled for this account')
	_ensure_not_locked(mfa)
	send_email_code(challenge)


def verify_login(mfa_token: str, method: str, code: str) -> User:
	"""Second login step. Returns the user to issue a session for."""
	challenge = load_challenge(mfa_token, MfaChallengePurpose.LOGIN)
	mfa = get_user_mfa(challenge.user)
	if mfa:
		_ensure_not_locked(mfa)
	user = verify_challenge_or_raise(challenge, method, code)
	if method == MfaMethod.RECOVERY:
		notify_mfa_change(user, 'recovery_used')
	return user


def start_email_setup(user: User) -> str:
	"""Email a code to prove the address works. Returns the token for confirm_email_setup."""
	mfa = get_user_mfa(user)
	if mfa and mfa.email_otp_enabled:
		raise MfaError('Email codes are already turned on')
	challenge = create_challenge(user, MfaChallengePurpose.SETUP_EMAIL)
	send_email_code(challenge)
	return sign_challenge(challenge)


def resend_email_setup_code(user: User, setup_token: str):
	send_email_code(load_challenge(setup_token, MfaChallengePurpose.SETUP_EMAIL, user=user))


@transaction.atomic
def confirm_email_setup(user: User, setup_token: str, code: str) -> list:
	"""Turn email codes on. Returns new recovery codes if this is the first 2FA method."""
	challenge = load_challenge(setup_token, MfaChallengePurpose.SETUP_EMAIL, user=user)
	verify_challenge_or_raise(challenge, MfaMethod.EMAIL.value, code)

	mfa = _get_or_create_mfa(user)
	was_enabled = mfa.is_enabled
	mfa.email_otp_enabled = True
	if not mfa.preferred_method:
		mfa.preferred_method = MfaMethod.EMAIL.value
	_save_mfa(mfa, ['email_otp_enabled', 'preferred_method'])
	notify_mfa_change(user, 'email_enabled')
	return [] if was_enabled else generate_recovery_codes(user)


def set_preferred_method(user: User, method: str):
	mfa = get_user_mfa(user)
	if not mfa or method not in mfa.enabled_methods:
		raise MfaError('That method is not turned on')
	mfa.preferred_method = method
	_save_mfa(mfa, ['preferred_method'])


# ---------------------------------------------------------------------------
# Sensitive actions: turning 2FA off and replacing recovery codes
# ---------------------------------------------------------------------------

def start_sensitive_email_challenge(user: User) -> str:
	"""Email a code to confirm a sensitive action. Returns the token to send back with it."""
	mfa = get_user_mfa(user)
	if not mfa or not mfa.email_otp_enabled:
		raise MfaError('Email codes are not turned on')
	_ensure_not_locked(mfa)
	challenge = create_challenge(user, MfaChallengePurpose.SENSITIVE)
	send_email_code(challenge)
	return sign_challenge(challenge)


def resend_sensitive_email_code(user: User, action_token: str):
	mfa = get_user_mfa(user)
	if mfa:
		_ensure_not_locked(mfa)
	send_email_code(load_challenge(action_token, MfaChallengePurpose.SENSITIVE, user=user))


def verify_current_factor(user: User, method: str, code: str, action_token: str = None):
	"""
	Re-check a factor the user already has, before a sensitive action. 'email' needs the
	token from start_sensitive_email_challenge. Failures count toward the per-user lock.
	"""
	mfa = get_user_mfa(user)
	if not mfa or not mfa.is_enabled:
		raise MfaError('Two-factor authentication is not turned on')
	_ensure_not_locked(mfa)

	if method == MfaMethod.EMAIL:
		challenge = load_challenge(action_token, MfaChallengePurpose.SENSITIVE, user=user)
		verify_challenge_or_raise(challenge, method, code)
		return

	with transaction.atomic():
		if method == MfaMethod.TOTP:
			ok = mfa.totp_enabled and _accept_totp(mfa, code)
		elif method == MfaMethod.RECOVERY:
			ok = use_recovery_code(user, code)
		else:
			ok = False
		if ok:
			_reset_failed_codes(mfa)
		else:
			_record_failed_code(mfa)
	if not ok:
		raise MfaError(INVALID_CODE_MESSAGE)


def disable_mfa_checked(user: User, password: str, method: str, code: str, action_token: str = None):
	"""Turn 2FA off after checking the password and a current factor."""
	if not user.check_password(password or ''):
		raise MfaError('Incorrect password')
	verify_current_factor(user, method, code, action_token)
	with transaction.atomic():
		disable_mfa(user)
		notify_mfa_change(user, 'disabled')


def regenerate_recovery_codes_checked(user: User, method: str, code: str, action_token: str = None) -> list:
	"""Replace recovery codes after checking a current factor. Old codes stop working."""
	verify_current_factor(user, method, code, action_token)
	with transaction.atomic():
		codes = generate_recovery_codes(user)
		notify_mfa_change(user, 'recovery_regenerated')
	return codes


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notify_mfa_change(user: User, event: str):
	"""
	Email the user about a 2FA change once the transaction commits. Sent from a
	background thread so SMTP doesn't slow the request; failures are only logged.
	"""
	def send():
		try:
			result = send_mfa_change_email(user, event)
			if result['has_error']:
				logger.warning(f'[MFA] Could not send "{event}" alert to {user.email}: {result["message"]}')
		except Exception as error:  # never let an alert break the request
			logger.warning(f'[MFA] Could not send "{event}" alert to {user.email}: {error}')

	transaction.on_commit(lambda: threading.Thread(target=send, daemon=True).start())


@transaction.atomic
def disable_mfa(user: User):
	"""
	Turn every method off and drop recovery codes and open challenges.
	No checks here: use disable_mfa_checked from user-facing code.
	"""
	UserMfa.objects.filter(user=user).update(
		totp_secret_encrypted='', totp_confirmed_at=None, totp_last_used_step=None,
		email_otp_enabled=False, preferred_method='', failed_attempts=0, locked_until=None,
		updated_at=timezone.now(),
	)
	MfaRecoveryCode.all_objects.filter(user=user).hard_delete()
	MfaChallenge.all_objects.filter(user=user).hard_delete()


def delete_expired_challenges() -> int:
	"""Housekeeping, meant for a future cron job (not scheduled yet)."""
	deleted, _ = MfaChallenge.all_objects.filter(
		Q(expires_at__lte=timezone.now()) | Q(consumed_at__isnull=False)
	).hard_delete()
	return deleted
