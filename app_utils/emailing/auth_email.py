from html import escape

from app_utils.emailing.mailing import (
	render_email, smtp_send_email, email_paragraph, email_code, email_button, email_callout, email_details,
)

MFA_EVENT_MESSAGES = {
	'totp_enabled': ('Authenticator app added', 'An authenticator app was added to your account for two-factor authentication.'),
	'email_enabled': ('Email codes turned on', 'Email codes were turned on for two-factor authentication on your account.'),
	'disabled': ('Two-factor authentication turned off', 'Two-factor authentication was turned off for your account. Signing in now only needs your password.'),
	'recovery_regenerated': ('New recovery codes created', 'New recovery codes were created for your account. Your old codes no longer work.'),
	'recovery_used': ('Recovery code used to sign in', 'Someone signed in to your account with a recovery code. Other sessions were signed out.'),
	'password_reset': ('Password changed', 'Your password was reset with a code sent to this email, and every device was signed out.'),
}


def _full_names(user) -> str:
	return f'{user.first_name} {user.last_name}'.strip() or user.email


def _send(user, subject: str, body_html: str, preheader: str, to_email: str = None, email_subject: str = None):
	"""Render the branded email for `user` and send it. Returns {has_error, message}."""
	to_email = to_email or user.email
	html = render_email(subject, _full_names(user), body_html, email=to_email, preheader=preheader)
	return smtp_send_email([to_email], email_subject or subject, html)


def send_test_email():
	user_email = 'akimanaja17@gmail.com'
	subject = 'Test email'
	body = email_paragraph('This is a test email from D2DStore. If you can read this, email delivery is working.')
	html = render_email(subject, 'Akimana Jean', body, email=user_email, preheader='Email delivery is working.')
	return smtp_send_email([user_email], 'Testing email', html)


def send_password_reset_code_email(user, code: str, valid_minutes: int):
	"""Email a password reset code. Returns smtp_send_email's {has_error, message}."""
	body = (
		email_paragraph('Use this code to reset your password:')
		+ email_code(code)
		+ email_paragraph(f'It expires in <strong>{valid_minutes} minutes</strong>.')
		+ email_paragraph("If you didn't ask to reset your password, you can ignore this email.", muted=True)
	)
	return _send(user, 'Reset your D2DStore password', body, f'Your password reset code is {code}.')


def send_mfa_code_email(user, code: str, valid_minutes: int):
	"""Email a one-time verification code. Returns smtp_send_email's {has_error, message}."""
	body = (
		email_paragraph('Use this code to finish signing in:')
		+ email_code(code)
		+ email_paragraph(f'It expires in <strong>{valid_minutes} minutes</strong>.')
		+ email_paragraph("If you didn't try to sign in, change your password right away.", muted=True)
	)
	return _send(user, 'Your D2DStore verification code', body, f'Your verification code is {code}.')


def send_mfa_change_email(user, event: str):
	"""Tell the user about a change to their two-factor settings."""
	subject, message = MFA_EVENT_MESSAGES[event]
	body = (
		email_paragraph(message)
		+ email_callout("<strong>Wasn't you?</strong> Change your password right away and review your "
			"security settings.", tone='warning')
	)
	return _send(user, subject, body, message, email_subject=f'D2DStore security alert: {subject}')


def send_user_invite_email(user, temp_password: str, login_url: str, valid_days: int):
	"""Invite a new user with their temporary password. Returns {has_error, message}."""
	body = (
		email_paragraph('An account was created for you on D2DStore. Sign in with these details:')
		+ email_details([
			('Email', escape(user.email)),
			('Temporary password', f'<span style="font-family:Menlo, Consolas, monospace; letter-spacing:1px;">'
				f'{escape(temp_password)}</span>'),
		])
		+ email_button('Sign in to D2DStore', login_url)
		+ email_paragraph(f"You'll be asked to choose your own password when you first sign in. "
			f"The temporary password expires in <strong>{valid_days} days</strong>.", muted=True)
	)
	return _send(user, "You've been invited to D2DStore", body, 'Your account is ready. Sign in to get started.')


def send_admin_password_reset_email(user, temp_password: str, login_url: str, valid_days: int):
	"""An administrator reset the user's password; give them a temporary one. Returns {has_error, message}."""
	body = (
		email_paragraph('An administrator reset the password on your account, and you were signed out. '
			'Sign in with this temporary password:')
		+ email_details([
			('Email', escape(user.email)),
			('Temporary password', f'<span style="font-family:Menlo, Consolas, monospace; letter-spacing:1px;">'
				f'{escape(temp_password)}</span>'),
		])
		+ email_button('Sign in to D2DStore', login_url)
		+ email_paragraph(f"You'll be asked to choose a new password when you sign in. "
			f"The temporary password expires in <strong>{valid_days} days</strong>.", muted=True)
		+ email_callout("<strong>Didn't ask for this?</strong> Contact your administrator.", tone='warning')
	)
	return _send(user, 'Your D2DStore password was reset', body,
		'An administrator reset your password. Sign in with your temporary password.')


def send_account_disabled_email(user):
	body = (
		email_paragraph('Your account was disabled by an administrator and you were signed out. Your data is kept.')
		+ email_paragraph('Contact your administrator if you think this is a mistake.', muted=True)
	)
	return _send(user, 'Your D2DStore account was disabled', body, 'An administrator disabled your account.')


def send_email_changed_email(user, old_email: str):
	"""Sent to the old address when an administrator changes the account's email."""
	body = (
		email_paragraph('An administrator changed the email address on your account, and you were signed out.')
		+ email_details([('Old email', escape(old_email)), ('New email', escape(user.email))])
		+ email_paragraph('Sign in with the new address from now on.', muted=True)
	)
	return _send(user, 'Your D2DStore email address was changed', body,
		'Your account now uses a different email address.', to_email=old_email)
