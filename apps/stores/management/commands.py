from django.core.management.base import BaseCommand
from django.db.models import QuerySet
from django.utils import timezone
from datetime import timedelta

from app_utils.emailing.mailing import template_email, smtp_send_email
from apps.stores.models import Store
from apps.users.models import User


class Command(BaseCommand):
	help = 'Sends a weekly email with a summary of user transactions'

	def handle(self, *args, **kwargs):
		now = timezone.now()
		seven_days_ago = now - timedelta(days=7)

		# Get all users (you can also filter users if needed)
		users = User.objects.all()

		for user in users:
			# Query the transactions from the last 7 days
			filters = {'n_days': seven_days_ago}
			transactions = User.get_user_stores(user, filters)

			if transactions.exists():
				self.send_weekly_email(user, transactions)

	def send_weekly_email(self, user, transactions):
		message = self.generate_email_content(user, transactions)
		subject = "Your Weekly Transaction Summary"
		response = smtp_send_email([user.email], subject, message)
		print('============================')
		print(user.first_name)
		print(response)
		print('============================')

	def generate_email_content(self, user: User, stores: QuerySet[Store]):
		subject = "Your Weekly Transaction Summary"
		full_names = f"{user.first_name} {user.first_name}"
		email_body_content = """
				<table>
					<thead>
						<tr>
							<th>Date</th>
							<th>Description</th>
							<th>Amount</th>
						</tr>
					</thead>
					<tbody>
				"""
		for record in stores:
			email_body_content += f"""
						<tr>
							<td>{record.action_date.strftime('%Y-%m-%d')}</td>
							<td>{record.description}</td>
							<td>{record.amount}</td>
						</tr>
					"""
		email_body_content += """
						</tbody>
					</table>
				"""

		email_body_html = template_email()

		# fill in blanks
		email_body_html = email_body_html.replace("[[email_subject]]", subject)
		email_body_html = email_body_html.replace("[[email_full_names]]", full_names)
		email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

		return email_body_html
