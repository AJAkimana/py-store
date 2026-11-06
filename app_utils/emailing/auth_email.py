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
