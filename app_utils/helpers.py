from django.core.paginator import Paginator
from rest_framework.response import Response

PAGINATION_DEFAULT = {
	"page_number": 1,
	"page_count": 20,
}


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
