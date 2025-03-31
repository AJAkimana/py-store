import calendar
import os
import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from app_utils.constants import EMAIL_MSGS
from app_utils.emailing.mailing import template_email, smtp_send_email, write_email_file
from app_utils.helpers import get_stores_filter, get_aggregated_in_out
from apps.stores.models import Store
from apps.users.models import User


class Command(BaseCommand):
	help = 'Sends a weekly email with a summary of user transactions'
	today = datetime.today().date()
	FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://store.akimanaja.com')

	def handle(self, *args, **kwargs):

		# Get all users (you can also filter users if needed)
		users = User.objects.all()

		for user in users:
			# Query the transactions from the last 7 days
			filters_dict = {'n_days': 7}
			filters = get_stores_filter(**filters_dict)
			transactions = User.get_user_stores(user, filters)

			if user.email.endswith("@gmail.com"):
				self.send_weekly_email(user, transactions)

	def send_weekly_email(self, user, transactions):
		message = self.generate_email_content(user, transactions)
		subject = "Your Weekly Transaction Summary"
		# if user.email == 'akimanaja17@gmail.com':
		# 	write_email_file('akimanaja', message)
		response = smtp_send_email([user.email], subject, message)
		print('============================')
		print(user.first_name)
		print(response)
		print('============================')

	def get_dates(self, in_days=7):
		seven_days_ago = self.today - timedelta(days=in_days)

		# Format dates as YYYY-MM-DD
		start_date = seven_days_ago.strftime('%Y-%m-%d')
		end_date = self.today.strftime('%Y-%m-%d')
		return [start_date, end_date]

	def generate_email_content(self, user: User, stores: QuerySet[Store]):
		[start_date, end_date] = self.get_dates()
		subject = f"Your Weekly Transaction Summary - {end_date}"

		full_names = f"{user.first_name} {user.first_name}"

		btn_call_action = "so you start recording them"

		btn_styles = """
			display: inline-block; padding: 10px 20px; font-size: 16px; color: white; background-color: #4CAF50;
			text-align: center; text-decoration: none; border-radius: 5px; font-family: Arial, sans-serif;
		"""
		if stores.exists():
			aggregate = get_aggregated_in_out(stores)
			btn_call_action = "to record more or view more records"
			email_body_content = f"""
				<p>Here is a summary your transaction you made this week. From {start_date} - {end_date}</p>
				<h2>A Short Summary</h2>
				<div style="border-color: #2196F3;
					border-left: 6px solid #0090ff; padding:0.01em 16px;
					background-color: #ddffff; font-size:20px">
					<p>You have spent: <b>{aggregate['outflow']}</b>, earned: <b>{aggregate['inflow']}</b></p>
				</div>
				<table class="record-tb">
					<thead>
						<tr class="record-tr">
							<th class="record-td">Date</th>
							<th class="record-td">Description</th>
							<th class="record-td">Amount</th>
						</tr>
					</thead>
					<tbody>
				"""
			for record in stores:
				email_body_content += f"""
							<tr class="record-tr">
								<td class="record-td">{record.action_date.strftime('%Y-%m-%d')}</td>
								<td class="record-td">{record.description}</td>
								<td class="record-td">{record.amount}</td>
							</tr>
						"""
			email_body_content += """
							</tbody>
						</table>
					"""
		else:
			email_body_content = f"""
				<p style="margin:10px;">
					{random.choice(EMAIL_MSGS)}
				</p>
			"""
		email_body_content += f"""
			<p>Click the button below, {btn_call_action}.</p>
			<div style="display: flex;">
				<a href="{self.FRONTEND_URL}/transactions?start_date={start_date}&end_date={end_date}" style="{btn_styles}">
					View the records
				</a>
			</div>
		"""

		email_body_html = template_email(subject, full_names)

		# fill in blanks
		email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

		return email_body_html

	def get_current_month_days(self):
		# Get current year and month
		year = datetime.now().year
		month = datetime.now().month

		# Get the number of days in the current month
		return calendar.monthrange(year, month)[1]
