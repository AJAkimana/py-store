import os
import jwt

from django.core.paginator import Paginator
from rest_framework.response import Response
from datetime import datetime
from graphql_jwt.settings import jwt_settings

PAGINATION_DEFAULT = {
  "page_number": 1,
  "page_count": 20,
}


## JWT payload for Hasura
def jwt_payload(user, context=None):
  jwt_datetime = datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA
  jwt_expires = int(jwt_datetime.timestamp())
  payload = {}
  payload['username'] = str(user.email)  # For library compatibility
  payload['sub'] = str(user.id)
  payload['sub_name'] = user.email
  payload['sub_email'] = user.email
  payload['exp'] = jwt_expires
  # payload['https://hasura.io/jwt/claims'] = {}
  # payload['https://hasura.io/jwt/claims']['x-hasura-allowed-roles'] = [user.profile.role]
  # payload['https://hasura.io/jwt/claims']['x-hasura-default-role'] = user.profile.role
  # payload['https://hasura.io/jwt/claims']['x-hasura-user-id'] = str(user.id)
  return payload


def paginate_data(data_set, page_count, page_number):
  """
	Breaks down retrieved records into chunks per page
	:param data_set: Query Set to be paginated
	:param page_count: Number of records in each page.
	:param page_number: The actual page
	:returns a tuple of the paginated record,
	number of pages and the total number of items
	"""
  paginator = Paginator(data_set, page_count)
  page_data = paginator.get_page(page_number)
  num_pages = paginator.num_pages
  total_count = len(data_set)

  result = {
    'page_data': page_data,
    'num_pages': num_pages,
    'total_count': total_count
  }
  return result


def server_response(status_code, message, data=None):
  message_type = 'error' if status_code >= 400 else 'message'
  response_content = {
    'status': status_code,
    message_type: message,
    data: data
  }
  return Response(response_content, status_code)


def get_errors(errors):
  messages = []
  for key, val in errors.items():
    messages.append(f'{key}: {val[0]}')
  return messages[0]


def dict_fetchall(cursor):
  """Return all rows from a cursor as a dict"""
  columns = [col[0] for col in cursor.description]
  return [
    dict(zip(columns, row))
    for row in cursor.fetchall()
  ]


def backup_filename(databasename, servername, datetime, extension, content_type):
  backup_type = 'dev' if os.getenv('DEBUG', 'true') == 'true' else 'prod'
  return f'D2DStore_{backup_type}-{datetime}.{extension}'


def properties_active(is_active):
  active = 'all'
  if is_active and is_active != 'all':
    active = True if is_active == 'yes' else False

  return active


def calculate_percent(gross_salary, percent=3):
  return (percent * gross_salary) / 100


def calculate_tax(gross_salary=0):
  tax = 0
  if 30000 < gross_salary <= 100000:
    tax = 0.2 * gross_salary - 6000
  elif gross_salary > 100000:
    tax = 0.3 * gross_salary - 16000
  return tax


def calculate_gross_salary(net_salary=0):
  gross_salary = net_salary
  if net_salary <= 29010:
    gross_salary = net_salary / 0.967
  elif 29010 < net_salary <= 82700:
    gross_salary = (net_salary - 6000) / 0.767
  elif net_salary > 82700:
    gross_salary = (net_salary - 16000) / 0.667
  return gross_salary
