from d2dstore.manager import BaseManager


class StoreManager(BaseManager):
	"""
	Custom manager store model
	"""

	def __init__(self, *args, **kwargs):
		super(StoreManager, self).__init__(*args, **kwargs)

	def get_query_set(self):
		query_set = super().get_queryset()
		return query_set
