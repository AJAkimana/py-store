import graphene
from django.core.management import call_command, CommandError
from graphene import AbstractType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.model_types.manager import DbBackupType


class ManageSystemQuery(AbstractType):
	db_backup = graphene.Field(DbBackupType)

	@login_required
	def resolve_db_backup(self, **kwargs):
		try:
			call_command('dbbackup')
			print('Db backed up')
			res = {'message': 'Db backed up'}
			return res
		except CommandError as error:
			print(error)
			raise GraphQLError('Error while backup')
