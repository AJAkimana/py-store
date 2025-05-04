import calendar
import os
import random
from datetime import datetime, timedelta, date

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from app_utils.constants import EMAIL_MSGS
from app_utils.emailing.mailing import template_email, smtp_send_email
from app_utils.helpers import get_stores_filter, get_aggregated_in_out, paginate_data
from apps.stores.models import Store
from apps.users.models import User


class Command(BaseCommand):
	help = 'Sends a weekly email with a summary of user transactions'
	today = datetime.today().date()
	FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://store.akimanaja.com')

	def add_arguments(self, parser):
		parser.add_argument('-t', '--type', type=str, help='Type of email to send', default='weekly')

	def handle(self, *args, **kwargs):
		report_type = kwargs.get('type')
		reports = {'weekly': 7, 'monthly': self.get_last_n_days()}
		n_days = reports[report_type]
		self.stdout.write(self.style.HTTP_INFO(f"Sending {report_type} report for the last {n_days} days"))
		# Get all users (you can also filter users if needed)
		users = User.objects.all()

		# Query the transactions from the last n_days days
		filters_dict = {'n_days': n_days}
		for user in users:
			filters = get_stores_filter(**filters_dict)
			transactions = User.get_user_stores(user, filters)

			if user.email.endswith("@gmail.com"):
				self.send_weekly_email(user, transactions, n_days)

	def send_weekly_email(self, user, stores, n_days=7):
		message = self.generate_email_content(user, stores, n_days)
		subject = f"Your {self.get_report_type(n_days)} Transaction Summary"

		self.stdout.write('============================')
		response = smtp_send_email([user.email], subject, message)
		if response["has_error"]:
			self.stdout.write(self.style.ERROR(f"Error sending email to {user.email}"))
			self.stdout.write(self.style.ERROR(f"""====={response["message"]}====="""))
		else:
			self.stdout.write(self.style.SUCCESS(f"Email sent to {user.email}"))
		self.stdout.write('============================')

	def get_dates(self, in_days=7):
		days_ago = self.today - timedelta(days=in_days)

		# Format dates as YYYY-MM-DD
		start_date = days_ago.strftime('%Y-%m-%d')
		end_date = self.today.strftime('%Y-%m-%d')
		return [start_date, end_date]

	def generate_email_content(self, user: User, stores: QuerySet[Store], n_days=7):
		[start_date, end_date] = self.get_dates(n_days)
		report_type = 'week' if n_days == 7 else 'month'
		subject = f"Your {self.get_report_type(n_days)} Transaction Summary - {end_date}"

		full_names = f"{user.first_name} {user.last_name}"

		btn_call_action = "so you start recording them"

		btn_styles = """
			display: inline-block; padding: 10px 20px; font-size: 16px; color: white; background-color: #4CAF50;
			text-align: center; text-decoration: none; border-radius: 5px; font-family: Arial, sans-serif;
		"""
		if stores.exists():
			aggregate = get_aggregated_in_out(stores)
			paginated_result = paginate_data(stores, 10, 1)
			btn_call_action = "to record more or view more records"
			email_body_content = f"""
				<p>Here is a summary your transaction you made this {report_type}. From {start_date} - {end_date}</p>
				<h2>A Short Summary</h2>
				<div style="border-color: #2196F3;
					border-left: 6px solid #0090ff; padding:0.01em 16px;
					background-color: #ddffff; font-size:20px">
					<p>You have spent: <b>{aggregate['outflow']}</b>, earned: <b>{aggregate['inflow']}</b>
					<br/>
					Total records is: <b>{paginated_result['total_count']}</b></p>
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
			for record in paginated_result['page_data'].object_list:
				email_body_content += f"""
							<tr class="record-tr">
								<td class="record-td">{record.action_date.strftime('%Y-%m-%d')}</td>
								<td class="record-td">{record.description}</td>
								<td class="record-td">{record.amount}</td>
							</tr>
						"""
			if paginated_result['total_count'] > 10:
				email_body_content += f"""
							<tr class="record-tr">
								<td class="record-td" colspan="3">
									And {paginated_result['total_count'] - 10} more records...
								</td>
							</tr>
						"""
			email_body_content += """
							</tbody>
						</table>
					"""
		else:
			email_body_content = f"""
				<p style="margin:10px;">
					{random.choice(EMAIL_MSGS).replace('[type]', report_type)}
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

		email_body_html = template_email(subject, full_names, user.email)

		# fill in blanks
		email_body_html = email_body_html.replace("[[email_body_content]]", email_body_content)

		return email_body_html

	def get_report_type(self, n_days=7):
		if n_days == 7:
			return 'Weekly'
		return 'Monthly'

	def get_last_n_days(self):
		today = date.today()

		if today.day < 10:
			# Get the number of days in the previous month
			first_day_of_current_month = today.replace(day=1)
			last_month = first_day_of_current_month - timedelta(days=1)
			n_days = calendar.monthrange(last_month.year, last_month.month)[1]
		else:
			# Get the difference between the 1st day and today
			n_days = today.day - 1

		# last_n_days = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(n_days)]
		return n_days
