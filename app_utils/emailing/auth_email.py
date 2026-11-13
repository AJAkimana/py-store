from app_utils.emailing.mailing import smtp_send_email, template_email


def send_test_email():
	subject = "Course schedule remainder. {} to {}"
	full_names = 'Akimana Jean'
	email_body_content = "This is a test email"
	email_body_html = template_email()
	email_body_plain_text = """
					<div style="margin-bottom:14pt; margin-top:14pt">Dear """ + full_names + """,</div>
					<div style="margin-bottom:14pt; margin-top:14pt">""" + email_body_content + """</div>
							<br />
							Best regards!<br />D2DStore Team
						</div>
					</div>"""

	# fill in blanks
	email_body_html = email_body_html.replace("[[email_subject]]", subject)
	email_body_html = email_body_html.replace("[[email_full_names]]", full_names)
	email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

	return smtp_send_email(['akimanaja17@gmail.com'], 'Testing email', email_body_plain_text, email_body_html)


MFA_EVENT_MESSAGES = {
	'totp_enabled': ('Authenticator app added', 'An authenticator app was added to your account for two-factor authentication.'),
	'email_enabled': ('Email codes turned on', 'Email codes were turned on for two-factor authentication on your account.'),
	'disabled': ('Two-factor authentication turned off', 'Two-factor authentication was turned off for your account. Signing in now only needs your password.'),
	'recovery_regenerated': ('New recovery codes created', 'New recovery codes were created for your account. Your old codes no longer work.'),
	'recovery_used': ('Recovery code used to sign in', 'Someone signed in to your account with a recovery code. Other sessions were signed out.'),
	'password_reset': ('Password changed', 'Your password was reset with a code sent to this email, and every device was signed out.'),
}


def send_password_reset_code_email(user, code: str, valid_minutes: int):
	"""Email a password reset code. Returns smtp_send_email's {has_error, message}."""
	subject = 'Reset your D2DStore password'
	full_names = f'{user.first_name} {user.last_name}'.strip() or user.email
	email_body_content = f"""
		<div style="margin-bottom:14pt">Use this code to reset your password:</div>
		<div style="font-size:24pt; font-weight:bold; letter-spacing:6px; margin-bottom:14pt">{code}</div>
		<div style="margin-bottom:14pt">It expires in {valid_minutes} minutes.
		If you didn't ask to reset your password, you can ignore this email.</div>
	"""
	email_body_html = template_email()
	email_body_html = email_body_html.replace("[[email_subject]]", subject)
	email_body_html = email_body_html.replace("[[email_full_names]]", full_names)
	email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

	return smtp_send_email([user.email], subject, email_body_html)


def send_mfa_change_email(user, event: str):
	"""Tell the user about a change to their two-factor settings."""
	subject, message = MFA_EVENT_MESSAGES[event]
	full_names = f'{user.first_name} {user.last_name}'.strip() or user.email
	email_body_content = f"""
		<div style="margin-bottom:14pt">{message}</div>
		<div style="margin-bottom:14pt">If this wasn't you, change your password right away
		and review your security settings.</div>
	"""
	email_body_html = template_email()
	email_body_html = email_body_html.replace("[[email_subject]]", subject)
	email_body_html = email_body_html.replace("[[email_full_names]]", full_names)
	email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

	return smtp_send_email([user.email], f'D2DStore security alert: {subject}', email_body_html)


def send_mfa_code_email(user, code: str, valid_minutes: int):
	"""Email a one-time verification code. Returns smtp_send_email's {has_error, message}."""
	subject = 'Your D2DStore verification code'
	full_names = f'{user.first_name} {user.last_name}'.strip() or user.email
	email_body_content = f"""
		<div style="margin-bottom:14pt">Use this code to finish signing in:</div>
		<div style="font-size:24pt; font-weight:bold; letter-spacing:6px; margin-bottom:14pt">{code}</div>
		<div style="margin-bottom:14pt">It expires in {valid_minutes} minutes.
		If you didn't try to sign in, change your password.</div>
	"""
	email_body_html = template_email()
	email_body_html = email_body_html.replace("[[email_subject]]", subject)
	email_body_html = email_body_html.replace("[[email_full_names]]", full_names)
	email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

	return smtp_send_email([user.email], subject, email_body_html)


def _render_email(subject: str, full_names: str, email_body_content: str) -> str:
	email_body_html = template_email()
	email_body_html = email_body_html.replace("[[email_subject]]", subject)
	email_body_html = email_body_html.replace("[[email_full_names]]", full_names)
	return email_body_html.replace("[[email_body_content]]", email_body_content)


def _full_names(user) -> str:
	return f'{user.first_name} {user.last_name}'.strip() or user.email


def send_user_invite_email(user, temp_password: str, login_url: str, valid_days: int):
	"""Invite a new user with their temporary password. Returns {has_error, message}."""
	subject = "You've been invited to D2DStore"
	email_body_content = f"""
		<div style="margin-bottom:14pt">An account was created for you. Sign in with:</div>
		<div style="margin-bottom:6pt">Email: <strong>{user.email}</strong></div>
		<div style="margin-bottom:14pt">Temporary password:
			<strong style="font-size:16pt; letter-spacing:2px">{temp_password}</strong></div>
		<div style="margin-bottom:14pt"><a href="{login_url}">Sign in to D2DStore</a></div>
		<div style="margin-bottom:14pt">You'll be asked to choose your own password when you first
		sign in. The temporary password expires in {valid_days} days.</div>
	"""
	return smtp_send_email([user.email], subject, _render_email(subject, _full_names(user), email_body_content))


def send_account_disabled_email(user):
	subject = 'Your D2DStore account was disabled'
	email_body_content = """
		<div style="margin-bottom:14pt">Your account was disabled by an administrator and you
		were signed out. Your data is kept. Contact your administrator if you think this is a mistake.</div>
	"""
	return smtp_send_email([user.email], subject, _render_email(subject, _full_names(user), email_body_content))


def send_email_changed_email(user, old_email: str):
	"""Sent to the old address when an administrator changes the account's email."""
	subject = 'Your D2DStore email address was changed'
	email_body_content = f"""
		<div style="margin-bottom:14pt">An administrator changed the email address on your account
		to <strong>{user.email}</strong>, and you were signed out. Sign in with the new address.</div>
	"""
	return smtp_send_email([old_email], subject, _render_email(subject, _full_names(user), email_body_content))
