from app_utils.validator import validator


def validate_prop_detail_fields(prop_detail, **kwargs):
	"""
	Prop detail Validation, This method takes in instance of prop_detail model
	and kwargs, its validate prop_detail, like title, amount,
	type, special character etc and raise a Graphql if a condition
	is not being met
	Args:
		PropDetail() instance
		kwargs
	returns:
		otherwise a GraphqlError is raised
		:param prop_detail:
	"""
	fields_to_validate = ["title", "amount", "type", "property_id"]

	for key, value in kwargs.items():
		if key in fields_to_validate:
			validator.special_character_validation(value)
		setattr(prop_detail, key, value)
	return prop_detail
