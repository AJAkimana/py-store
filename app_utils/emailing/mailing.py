from django.core.mail import send_mail, EmailMessage
from d2dstore.settings import EMAIL_HOST_USER, DEFAULT_FROM_EMAIL


def smtp_send_email(to_emails: [str], subject: str, body_html: str, attachments=None):
	response = {"has_error": True, "message": "Failed to send email"}
	try:

		# Decide what to use if it has attachments
		if attachments is None:
			send_mail(
				subject=subject,
				message=body_html,
				html_message=body_html,
				from_email=DEFAULT_FROM_EMAIL,
				recipient_list=to_emails,
				fail_silently=False)
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


def template_email(subject="", full_names=""):
	"""
		Replace: [[email_full_names]], [[email_subject]], [[email_body_content]]

		Returns:

		"""
	table_style = """
		background-color:white; border-collapse:collapse; border-spacing:0; border:1px solid #d2d2d2;
		margin:20px; text-align:justify;
	"""
	body_div_styles = """
		font-family: 'Roboto', 'Arial', sans-serif; padding: 2rem; line-height: 1.8; color: #333; background: #fff;
		border-radius: 4px; shadow: 0 .5rem 1rem rgba(0,0,0,.15)
	"""
	styles = """
		.record-tb {
			font-family: arial, sans-serif;
			border-collapse: collapse;
			width: 100%;
		}

		.record-td {
			border: 1px solid #dddddd;
			text-align: left;
			padding: 8px;
		}

		.record-tr:nth-child(even) {
			background-color: #dddddd;
		}
	"""

	html = f"""
	<html>
		<head>
			<title>{subject}</title>
			<style>
				{styles}
			</style>
		</head>
		<body style="padding: 1rem; background: #f1f1f1">
			<div style="{body_div_styles}">
				<table border="1" cellspacing="0" style="{table_style}">
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
																	{subject}
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
																<div>
																	<img src='[[email_site_logo]]' style="border-width:0px; height:57px; width:144px" />
																</div>
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
														<div style="margin-bottom:14pt; margin-top:14pt">Dear {full_names},</div>
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
													<div>
														<span style="color:#6f6f6f; font-size:x-small; font-size:11px">
															This email is sent to {full_names}.</span>
														</div>
												</td>
											</tr>
										</tbody>
									</table>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</body>
		</html>
		"""
	html = html.replace("[[email_site_logo]]", '')
	return html
