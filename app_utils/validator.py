import re

from graphql import GraphQLError

from app_utils.common_messages import ERROR_MESSAGES


class Validator:
	"""
	All validations of fields within the system
	fields:
			email(str): email
			mobile(str): mobile number
			string(str): characters
			new_password(str): password
			field(str): field
			value(str): value
	"""

	def __init__(self):
		self.email = None
		self.string = None
		self.value = None
		self.field = None
		self.mobile = None
		self.password = None

	def validate_email(self, email):
		self.email = email.strip()

		if not re.match(r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]{2,5}$', self.email):
			raise GraphQLError(ERROR_MESSAGES['invalid_email'])
		return self.email

	def special_character_validation(self, string):
		self.string = re.search(r'[^a-zA-Z0-9.,\-\s]+', string)
		if self.string:
			raise GraphQLError(ERROR_MESSAGES['character_not_allowed'])

	def validate_empty_field(self, field, value):
		"""
		Utility method to check if a field value is blank
		and return an error message if it is so.
		"""
		self.value = value
		self.field = field
		if self.value == "":
			message = "{} field cannot be blank!".format(self.field)
			raise GraphQLError(message)

	def validate_mobile(self, mobile):
		"""
		Validate a string on mobile number
		Arguments:
				mobile_number {string} -- [string mobile number format]
		"""
		self.mobile = mobile.strip()
		example = "mobile number (ex. +2346787646)"
		if not re.match(r'(^[+0-9]{1,3})*([0-9]{10,11}$)', self.mobile):
			raise GraphQLError(ERROR_MESSAGES["invalid_mobile"].format(example))
		return self.mobile

	def validate_password(self, password):
		self.password = password.strip()
		regex = re.match('(?=.{8,100})(?=.*[A-Z])(?=.*[0-9])', self.password)
		if not regex:
			raise GraphQLError(ERROR_MESSAGES["password_not_valid"])
		return self.password


validator = Validator()
