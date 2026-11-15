import calendar
import os
import random
from datetime import datetime, timedelta, date
from html import escape

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from app_utils.constants import EMAIL_MSGS
from app_utils.emailing.mailing import (
	render_email, smtp_send_email, email_paragraph, email_heading, email_stats, email_table, email_button,
)
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

		full_names = f"{user.first_name} {user.last_name}".strip()
		records_url = f"{self.FRONTEND_URL}/transactions?start_date={start_date}&end_date={end_date}"

		if stores.exists():
			aggregate = get_aggregated_in_out(stores)
			paginated_result = paginate_data(stores, 10, 1)
			total = paginated_result['total_count']
			preheader = f"You spent {self.money(aggregate['outflow'])} and earned {self.money(aggregate['inflow'])} this {report_type}."
			rows = [
				[
					record.action_date.strftime('%b %d'),
					escape(record.description),
					f'<span style="color:{"#16a34a" if record.is_inflow else "inherit"}; font-weight:600;">'
					f'{"+" if record.is_inflow else ""}{self.money(record.amount)}</span>',
				]
				for record in paginated_result['page_data'].object_list
			]
			email_body_content = (
				email_paragraph(f"Here's a summary of your transactions this {report_type}, "
					f"from <strong>{start_date}</strong> to <strong>{end_date}</strong>.")
				+ email_stats([
					('Spent', self.money(aggregate['outflow'])),
					('Earned', self.money(aggregate['inflow'])),
					('Records', f'{total:,}'),
				])
				+ email_heading('Latest records')
				+ email_table(['Date', 'Description', 'Amount'], rows, align=['left', 'left', 'right'])
			)
			if total > 10:
				email_body_content += email_paragraph(f'And {total - 10:,} more records.', muted=True)
			email_body_content += email_button('View all records', records_url)
		else:
			preheader = f"No transactions recorded this {report_type}."
			email_body_content = (
				email_paragraph(escape(random.choice(EMAIL_MSGS).replace('[type]', report_type)))
				+ email_button('Start recording', records_url)
			)

		return render_email(subject, full_names, email_body_content, email=user.email, preheader=preheader)

	@staticmethod
	def money(value):
		return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.2f}'

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
