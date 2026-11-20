import re
from html import escape, unescape

from django.core.mail import EmailMultiAlternatives
from d2dstore.settings import DEFAULT_FROM_EMAIL, FRONTEND_URL

BRAND_NAME = 'D2DStore'

# Palette, matching the web app's default primary colour.
PRIMARY = '#1976d2'
PRIMARY_DARK = '#115293'
INK = '#0f172a'
TEXT = '#334155'
MUTED = '#64748b'
BORDER = '#e2e8f0'
SURFACE = '#f8fafc'
PAGE_BG = '#f1f5f9'
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MONO = "'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace"

CALLOUT_TONES = {
	'info': ('#eff6ff', PRIMARY),
	'success': ('#f0fdf4', '#16a34a'),
	'warning': ('#fffbeb', '#d97706'),
	'danger': ('#fef2f2', '#dc2626'),
}

# Anything between these markers is left out of the plain-text version.
_TEXT_SKIP = re.compile(r'<!--text-skip-->.*?<!--/text-skip-->', re.S)


def smtp_send_email(to_emails: [str], subject: str, body_html: str, attachments=None, body_text: str = None):
	"""Send an HTML email with a plain-text alternative. Returns {has_error, message}."""
	response = {"has_error": True, "message": "Failed to send email"}
	try:
		message = EmailMultiAlternatives(
			subject=subject,
			body=body_text or html_to_text(body_html),
			from_email=DEFAULT_FROM_EMAIL,
			to=to_emails,
		)
		message.attach_alternative(body_html, 'text/html')
		for path in attachments or []:
			message.attach_file(path)
		message.send(fail_silently=False)
		response["has_error"] = False
		response["message"] = "Successfully sent"
	except Exception as x:  # pylint: disable=broad-exception-caught  # callers check has_error
		response["message"] = "Failed to send email error:" + str(x)
	return response


def html_to_text(html: str) -> str:
	"""Rough plain-text rendering of an email for clients that don't show HTML."""
	text = _TEXT_SKIP.sub('', html)
	text = re.sub(r'<(head|style|script)\b.*?</\1>', '', text, flags=re.S | re.I)
	text = re.sub(r'<a\b[^>]*href="mailto:[^"]*"[^>]*>(.*?)</a>', r'\1', text, flags=re.S | re.I)
	text = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r'\2 (\1)', text, flags=re.S | re.I)
	text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
	text = re.sub(r'</(p|div|h[1-6]|tr|li|table)>', '\n', text, flags=re.I)
	text = re.sub(r'</t[dh]>', '  ', text, flags=re.I)
	text = unescape(re.sub(r'<[^>]+>', '', text))
	lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()]
	return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n'


# ---------------------------------------------------------------------------
# Building blocks for email bodies. All return HTML strings with inline styles,
# since most email clients drop <style> blocks. Values passed as `text` are
# treated as HTML, so escape anything that came from a user first.
# ---------------------------------------------------------------------------

def email_paragraph(text: str, muted: bool = False) -> str:
	color = MUTED if muted else TEXT
	size = '13px' if muted else '15px'
	return f'<p style="margin:0 0 16px; font-size:{size}; line-height:1.6; color:{color};">{text}</p>'


def email_heading(text: str) -> str:
	return f'<h2 style="margin:24px 0 12px; font-size:16px; font-weight:600; color:{INK};">{text}</h2>'


def email_code(code: str) -> str:
	"""A large one-time code, easy to read and copy."""
	return f"""
		<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px;">
			<tr>
				<td align="center" style="background:{SURFACE}; border:1px solid {BORDER}; border-radius:10px; padding:20px 12px;">
					<span style="font-family:{MONO}; font-size:32px; font-weight:700; letter-spacing:10px; color:{INK};">{escape(code)}</span>
				</td>
			</tr>
		</table>"""


def email_button(label: str, url: str) -> str:
	"""A button that also renders in Outlook (padding on the cell, not the link)."""
	return f"""
		<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 24px;">
			<tr>
				<td align="center" bgcolor="{PRIMARY}" style="border-radius:8px;">
					<a href="{escape(url, quote=True)}" target="_blank"
						style="display:inline-block; padding:12px 24px; font-family:{FONT}; font-size:15px; font-weight:600;
						color:#ffffff; text-decoration:none; border-radius:8px; border:1px solid {PRIMARY_DARK};">{label}</a>
				</td>
			</tr>
		</table>"""


def email_callout(text: str, tone: str = 'info') -> str:
	background, accent = CALLOUT_TONES.get(tone, CALLOUT_TONES['info'])
	return f"""
		<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px;">
			<tr>
				<td style="background:{background}; border-left:4px solid {accent}; border-radius:6px; padding:14px 16px;
					font-size:14px; line-height:1.6; color:{TEXT};">{text}</td>
			</tr>
		</table>"""


def email_details(rows: list) -> str:
	"""Label/value pairs, e.g. [('Email', 'a@b.com'), ('Temporary password', 'x7Fq')]."""
	cells = ''
	for index, (label, value) in enumerate(rows):
		divider = f'border-top:1px solid {BORDER};' if index else ''
		cells += f"""
			<tr>
				<td style="padding:10px 16px; font-size:13px; color:{MUTED}; {divider} white-space:nowrap;">{label}</td>
				<td style="padding:10px 16px; font-size:14px; color:{INK}; font-weight:600; {divider} word-break:break-all;">{value}</td>
			</tr>"""
	return f"""
		<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
			style="margin:0 0 24px; background:{SURFACE}; border:1px solid {BORDER}; border-radius:10px; border-collapse:separate;">
			{cells}
		</table>"""


def email_stats(stats: list) -> str:
	"""A row of headline figures, e.g. [('Spent', '120,000'), ('Earned', '300,000')]."""
	width = f'{100 // max(len(stats), 1)}%'
	cells = ''.join(f"""
				<td width="{width}" style="padding:4px;">
					<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
						<tr><td style="background:{SURFACE}; border:1px solid {BORDER}; border-radius:10px; padding:14px 16px;">
							<div style="font-size:12px; text-transform:uppercase; letter-spacing:0.5px; color:{MUTED};">{label}</div>
							<div style="margin-top:4px; font-size:20px; font-weight:700; color:{INK};">{value}</div>
						</td></tr>
					</table>
				</td>""" for label, value in stats)
	return f"""
		<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 16px;">
			<tr>{cells}</tr>
		</table>"""


def email_table(headers: list, rows: list, align: list = None) -> str:
	"""A simple data table. `align` gives each column's alignment ('left' or 'right')."""
	align = align or ['left'] * len(headers)
	head = ''.join(
		f'<th align="{a}" style="padding:10px 12px; font-size:12px; font-weight:600; text-transform:uppercase; '
		f'letter-spacing:0.5px; color:{MUTED}; background:{SURFACE}; border-bottom:1px solid {BORDER};">{h}</th>'
		for h, a in zip(headers, align))
	body = ''.join(
		'<tr>' + ''.join(
			f'<td align="{a}" style="padding:10px 12px; font-size:14px; color:{TEXT}; border-bottom:1px solid {BORDER};">{c}</td>'
			for c, a in zip(row, align)) + '</tr>'
		for row in rows)
	return f"""
		<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
			style="margin:0 0 24px; border:1px solid {BORDER}; border-radius:10px; border-collapse:separate; overflow:hidden;">
			<thead><tr>{head}</tr></thead>
			<tbody>{body}</tbody>
		</table>"""


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def render_email(subject: str, full_names: str, body_html: str, email: str = '', preheader: str = '') -> str:
	"""
	Wrap body HTML in the branded layout.

	subject: shown as the heading (escaped). full_names: used in the greeting (escaped).
	body_html: the message, usually built from the email_* helpers. email: the recipient,
	shown in the footer. preheader: the preview line inbox lists show next to the subject.
	"""
	greeting = f'Hi {escape(full_names)},' if full_names else 'Hi there,'
	recipient = (f'This email was sent to <a href="mailto:{escape(email, quote=True)}" '
		f'style="color:{MUTED}; text-decoration:underline;">{escape(email)}</a>. ') if email else ''
	app_link = (f'<a href="{FRONTEND_URL}" style="color:{MUTED}; text-decoration:underline;">Open {BRAND_NAME}</a>'
		if FRONTEND_URL else BRAND_NAME)
	preheader_html = (f'<!--text-skip--><div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">'
		f'{escape(preheader)}&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;</div><!--/text-skip-->') if preheader else ''

	return f"""<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<meta name="color-scheme" content="light">
	<meta name="supported-color-schemes" content="light">
	<title>{escape(subject)}</title>
</head>
<body style="margin:0; padding:0; background:{PAGE_BG}; font-family:{FONT}; -webkit-font-smoothing:antialiased;">
	{preheader_html}
	<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAGE_BG};">
		<tr>
			<td align="center" style="padding:32px 16px;">
				<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;">
					<!--text-skip-->
					<tr>
						<td style="padding:0 4px 20px;">
							<table role="presentation" cellpadding="0" cellspacing="0" border="0">
								<tr>
									<td width="32" height="32" align="center" bgcolor="{PRIMARY}"
										style="border-radius:8px; font-size:13px; font-weight:800; color:#ffffff; letter-spacing:-0.5px;">D2D</td>
									<td style="padding-left:10px; font-size:17px; font-weight:700; color:{INK}; letter-spacing:-0.2px;">{BRAND_NAME}</td>
								</tr>
							</table>
						</td>
					</tr>
					<!--/text-skip-->
					<tr>
						<td style="background:#ffffff; border:1px solid {BORDER}; border-top:4px solid {PRIMARY}; border-radius:12px; padding:36px 36px 28px;">
							<h1 style="margin:0 0 20px; font-size:22px; line-height:1.3; font-weight:700; color:{INK};">{escape(subject)}</h1>
							<p style="margin:0 0 16px; font-size:15px; line-height:1.6; color:{TEXT};">{greeting}</p>
							{body_html}
							<p style="margin:24px 0 0; padding-top:20px; border-top:1px solid {BORDER}; font-size:14px; line-height:1.6; color:{MUTED};">
								Thanks,<br><span style="color:{INK}; font-weight:600;">The {BRAND_NAME} team</span>
							</p>
						</td>
					</tr>
					<tr>
						<td style="padding:20px 8px 0; font-size:12px; line-height:1.6; color:{MUTED}; text-align:center;">
							{recipient}This inbox isn't monitored, so please don't reply.<br>
							{app_link}
						</td>
					</tr>
				</table>
			</td>
		</tr>
	</table>
</body>
</html>"""


def write_email_file(title, content):
	"""Write rendered HTML to <title>.html, handy for previewing a template in a browser."""
	try:
		file_name = f"{title}.html"
		with open(file_name, "w", encoding="utf-8") as file:
			file.write(content)
		print(f"Content written to {file_name} successfully!")
	except OSError as e:
		print(f"An error occurred: {e}")
