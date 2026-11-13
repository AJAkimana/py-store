"""
User management for the administrator: invite (create), update, disable/enable.

There is a single administrator (the superuser). Only regular users are managed here;
the administrator's own account is managed from Settings and can't be changed here.

New users get an emailed temporary password and must choose their own at first
sign-in ('password_change_required' on login, then set_initial_password).
"""
import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app_utils.emailing.auth_email import (
	send_user_invite_email, send_account_disabled_email, send_email_changed_email,
)
from app_utils.emailing.background import send_after_commit
from apps.households.models import Household
from apps.users.models import User
from apps.users.session import end_all_sessions
from d2dstore.logger import logger

EDITABLE_FIELDS = ('first_name', 'last_name', 'user_name', 'email', 'phone')
INVITE_RESEND_INTERVAL = timedelta(seconds=60)
PASSWORD_CHANGE_TOKEN_TTL = timedelta(minutes=15)
HOUSEHOLD_ADMIN_ACCESS_LEVEL = 1

_PASSWORD_CHANGE_SALT = 'apps.users.initial-password'
_USER_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_.-]{3,50}$')
_PHONE_PATTERN = re.compile(r'^\+?[0-9 ()-]{6,30}$')
# No look-alike characters (0/O, 1/l/I), so it's easy to type from an email
_TEMP_PASSWORD_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'


class UserManagementError(Exception):
	pass


def _ensure_admin(actor: User):
	if not (actor and actor.is_authenticated and actor.is_superuser):
		raise UserManagementError('Only the administrator can manage users')


def _get_managed_user(user_id) -> User:
	"""A regular (non-admin) user; the administrator can't be managed from here."""
	user = User.objects.filter(pk=user_id, is_superuser=False).first() if user_id else None
	if user is None:
		raise UserManagementError('User not found')
	return user


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _clean_fields(fields: dict, user: User = None) -> dict:
	"""Trim, validate and check uniqueness of the given fields (only those present)."""
	cleaned = {}
	for key in EDITABLE_FIELDS:
		if key not in fields or fields[key] is None:
			continue
		value = str(fields[key]).strip()
		label = key.replace('_', ' ')
		if not value:
			raise UserManagementError(f'The {label} is required')
		if len(value) > 50 and key != 'email':
			raise UserManagementError(f'The {label} must be 50 characters or fewer')
		cleaned[key] = value

	if 'email' in cleaned:
		cleaned['email'] = cleaned['email'].lower()
		try:
			validate_email(cleaned['email'])
		except ValidationError:
			raise UserManagementError('Enter a valid email address')
	if 'user_name' in cleaned and not _USER_NAME_PATTERN.match(cleaned['user_name']):
		raise UserManagementError('The user name must be 3-50 letters, numbers, dots, dashes or underscores')
	if 'phone' in cleaned and not _PHONE_PATTERN.match(cleaned['phone']):
		raise UserManagementError('Enter a valid phone number')

	others = User.objects.exclude(pk=user.pk) if user else User.objects.all()
	unique_checks = (
		('email', 'email__iexact', 'This email is already used by another account'),
		('user_name', 'user_name__iexact', 'This user name is already taken'),
		('phone', 'phone', 'This phone number is already used by another account'),
	)
	for key, lookup, message in unique_checks:
		if key in cleaned and others.filter(**{lookup: cleaned[key]}).exists():
			raise UserManagementError(message)
	return cleaned


# ---------------------------------------------------------------------------
# Invites
# ---------------------------------------------------------------------------

def _new_temp_password() -> str:
	raw = ''.join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(12))
	return f'{raw[:4]}-{raw[4:8]}-{raw[8:]}'


def _issue_invite(user: User) -> bool:
	"""
	Give the user a new temporary password and email it. Returns whether the email was
	sent. Any previous temporary password stops working.
	"""
	temp_password = _new_temp_password()
	now = timezone.now()
	user.set_password(temp_password)
	user.is_verified = False
	user.invited_at = now
	user.temp_password_expires_at = now + timedelta(days=settings.INVITE_PASSWORD_VALID_DAYS)
	user.save(update_fields=['password', 'is_verified', 'invited_at', 'temp_password_expires_at'])

	if settings.DEBUG:
		# Development only, so invites can be tested without SMTP
		logger.info(f'[Invite] Temporary password for {user.email}: {temp_password}')

	sent = send_user_invite_email(
		user, temp_password, f'{settings.FRONTEND_URL}/login', settings.INVITE_PASSWORD_VALID_DAYS,
	)
	if sent['has_error']:
		logger.warning(f'[Invite] Email to {user.email} failed: {sent["message"]}')
		return False
	return True


def create_user(actor: User, **fields) -> tuple:
	"""
	Create a regular user with their own household (they're its admin) and email them
	an invite with a temporary password. Returns (user, invite_sent).
	"""
	_ensure_admin(actor)
	missing = [key.replace('_', ' ') for key in EDITABLE_FIELDS if not (fields.get(key) or '').strip()]
	if missing:
		raise UserManagementError(f'Missing: {", ".join(missing)}')
	cleaned = _clean_fields(fields)

	with transaction.atomic():
		user = User(**cleaned, middle_name='', previous_passwords='', is_active=True)
		user.set_unusable_password()
		user.save()
		household = Household.objects.create(name=f"{user.first_name}'s household", created_by=user)
		household.members.add(user, through_defaults={'access_level': HOUSEHOLD_ADMIN_ACCESS_LEVEL})

	# Outside the transaction so a mail failure doesn't undo the account; the admin can resend
	return user, _issue_invite(user)


def resend_invite(actor: User, user_id) -> bool:
	"""New temporary password for a user who hasn't set their own yet. Returns invite_sent."""
	_ensure_admin(actor)
	user = _get_managed_user(user_id)
	if user.is_verified:
		raise UserManagementError('This user has already set their password')
	if not user.is_active:
		raise UserManagementError('Enable this user before sending a new invite')
	if user.invited_at and timezone.now() - user.invited_at < INVITE_RESEND_INTERVAL:
		raise UserManagementError('An invite was just sent. Wait a minute before sending another')
	return _issue_invite(user)


# ---------------------------------------------------------------------------
# Update and disable
# ---------------------------------------------------------------------------

def update_user(actor: User, user_id, **fields) -> tuple:
	"""
	Change the given fields. A new email signs the user out everywhere and notifies the
	old address; a pending invite is re-sent to the new address. Returns (user, invite_sent),
	where invite_sent is None when no invite was due.
	"""
	_ensure_admin(actor)
	user = _get_managed_user(user_id)
	cleaned = _clean_fields(fields, user=user)
	old_email = user.email
	email_changed = 'email' in cleaned and cleaned['email'] != old_email.lower()

	with transaction.atomic():
		for key, value in cleaned.items():
			setattr(user, key, value)
		user.save(update_fields=list(cleaned) or None)
		if email_changed:
			end_all_sessions(user)
			send_after_commit(send_email_changed_email, user, old_email, description='email change notice')

	invite_sent = None
	if email_changed and not user.is_verified and user.is_active:
		invite_sent = _issue_invite(user)
	return user, invite_sent


def set_user_active(actor: User, user_id, active: bool) -> User:
	"""Disable (sign out everywhere, keep data) or re-enable a user."""
	_ensure_admin(actor)
	user = _get_managed_user(user_id)
	if user.pk == actor.pk:
		raise UserManagementError("You can't disable your own account")
	if user.is_active == active:
		return user

	with transaction.atomic():
		user.is_active = active
		user.deactivated_at = None if active else timezone.now()
		user.deactivated_by = None if active else actor
		user.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by'])
		if not active:
			end_all_sessions(user)
			send_after_commit(send_account_disabled_email, user, description='account disabled notice')
	return user


def filter_managed_users(search: str = None, status: str = None):
	users = User.objects.filter(is_superuser=False).select_related('mfa', 'deactivated_by')
	if status == 'active':
		users = users.filter(is_active=True, is_verified=True)
	elif status == 'invited':
		users = users.filter(is_active=True, is_verified=False)
	elif status == 'disabled':
		users = users.filter(is_active=False)
	if search:
		users = users.filter(
			Q(first_name__icontains=search) | Q(last_name__icontains=search)
			| Q(user_name__icontains=search) | Q(phone__icontains=search) | Q(email__icontains=search)
		)
	return users.order_by('first_name', 'last_name')


# ---------------------------------------------------------------------------
# First sign-in: replace the temporary password
# ---------------------------------------------------------------------------

def _password_fingerprint(user: User) -> str:
	# Changes whenever the password does, so a used or outdated token stops working
	return user.password[-16:]


def password_change_token(user: User) -> str:
	return signing.dumps({'u': str(user.pk), 'p': _password_fingerprint(user)}, salt=_PASSWORD_CHANGE_SALT)


def temp_password_expired(user: User) -> bool:
	return bool(user.temp_password_expires_at and user.temp_password_expires_at <= timezone.now())


def set_initial_password(token: str, new_password: str) -> User:
	"""
	Replace the temporary password after the user signed in with it. The token comes
	from the login response. Doesn't sign in: the client signs in with the new password.
	"""
	invalid = UserManagementError('This link has expired. Sign in again with your temporary password.')
	try:
		data = signing.loads(token or '', salt=_PASSWORD_CHANGE_SALT,
												 max_age=PASSWORD_CHANGE_TOKEN_TTL.total_seconds())
	except signing.BadSignature:
		raise invalid

	user = User.objects.filter(pk=data.get('u'), is_active=True, is_verified=False).first()
	if user is None or data.get('p') != _password_fingerprint(user) or temp_password_expired(user):
		raise invalid
	if user.check_password(new_password or ''):
		raise UserManagementError('Choose a password different from the temporary one')
	try:
		validate_password(new_password or '', user)
	except ValidationError as error:
		raise UserManagementError(' '.join(error.messages))

	user.set_password(new_password)
	user.is_verified = True
	user.temp_password_expires_at = None
	user.save(update_fields=['password', 'is_verified', 'temp_password_expires_at'])
	return user
