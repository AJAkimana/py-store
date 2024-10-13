from django.core.mail import send_mail, EmailMessage
from d2dstore.settings import EMAIL_HOST_USER, DEFAULT_FROM_EMAIL


def smtp_send_email(to_emails: [str], subject: str, body_html: str, attachments=None):
	response = {"has_error": True, "message": "Failed to send email"}
	try:

		# Decide what to use if it has attachments
		if attachments is None:
			send_mail(subject, body_html, DEFAULT_FROM_EMAIL, to_emails, fail_silently=False)
		else:
			obj_mail = EmailMessage(subject, body_html, EMAIL_HOST_USER, to_emails)
			obj_mail.content_subtype = "html"

			# add attachments
			for x in attachments:
				obj_mail.attach_file(x)
			obj_mail.send(False)
		response["has_error"] = False
		response["message"] = "Successfully sent"
	except Exception as x:
		response["message"] = "Failed to send email error:" + str(x)
	return response


def template_email():
	"""
	Replace: [[email_full_names]], [[email_subject]], [[email_body_content]]

	Returns:

	"""
	html = """
		<table
				border="1"
				cellspacing="0"
				style="background-color:white; border-collapse:collapse; border-spacing:0; border:1px solid #d2d2d2; margin:20px; text-align:justify; width:600px"
			>
				<tbody>
					<tr>
						<td>
							<table style="border-bottom:6px solid green; width:100%">
								<tbody>
									<tr>
										<td>
											<table align="left" border="0">
												<tbody>
													<tr>
														<td>
															<div style="margin-bottom:10px"><span style="color:green">&nbsp;</span></div>
															[[email_subject]]
														</td>
													</tr>
												</tbody>
											</table>
										</td>
										<td>
										<table border="0" style="height:30px; width:49px">
											<tbody>
												<tr>
													<td style="vertical-align:middle">
														<div><img src='[[email_site_logo]]' style="border-width:0px; height:57px; width:144px" /></div>
													</td>
												</tr>
											</tbody>
										</table>
										</td>
									</tr>
								</tbody>
							</table>
							<table style="width:100%">
								<tbody>
									<tr>
										<td>
											<div>
												<div style="margin-bottom:14pt; margin-top:14pt">Dear [[email_full_names]],</div>
												<div style="margin-bottom:14pt; margin-top:14pt">
													[[email_body_content]]
													<br />
													Best regards!<br />
													D2DStore Team
												</div>
											</div>
										</td>
									</tr>
								</tbody>
							</table>
							<img src='[[email_site_logo]]' style="border-width:0px; height:57px; width:144px" />
							<table style="height:45px; width:242px">
								<tbody>
									<tr>
										<td style="vertical-align:middle">
											<div><strong>Do Not Reply to this email</strong></div>
											<div><span style="color:#6f6f6f; font-size:x-small"><span style="font-size:11px">This email is sent to [[email_full_names]].</span></span></div>
										</td>
									</tr>
								</tbody>
							</table>
						</td>
					</tr>
				</tbody>
			</table>
		"""
	html = html.replace("[[email_site_logo]]", '')
	return html
