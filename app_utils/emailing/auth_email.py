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
