from graphene import ObjectType, List, Int


class PaginatorType(ObjectType):
	def __init__(self, model):
		self.model = model
		
	def page_data(self):
		return List(self.model)
	
	def num_pages(self):
		return Int(self)
	
	def total_count(self):
		return Int(self)