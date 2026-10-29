from graphql import GraphQLError


class BaseValidator:
	def __init__(self, model, **body):
		self.body = body
		self.model = model

	def check_empty_fields(self, exclude=None):
		exclude = exclude or []
		for key, value in self.body.items():
			if key in exclude:
				continue
			if isinstance(value, str) and value.strip() == '':
				raise GraphQLError(f"The {key} field can't be empty")
			setattr(self.model, key, value)

	def check_duplicate(self, filter_fields: list[str]):
		filter_fields = {field: self.body[field] for field in filter_fields if field in self.body}
		instance_id = self.body.get('id', None)
		qs = self.model.objects.filter(**filter_fields)
		if instance_id is not None:
			qs = qs.exclude(id=instance_id)
		if qs.exists():
			fields_str = ', '.join(f"{k}={v}" for k, v in filter_fields.items())
			raise GraphQLError(f"A {self.model.__name__} with these fields already exists: {fields_str}.")
