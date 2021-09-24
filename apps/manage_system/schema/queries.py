import graphene
from django.core.management import call_command, CommandError
from graphene import AbstractType
from graphql import GraphQLError
from graphql_jwt.decorators import login_required, superuser_required

from app_utils.helpers import paginate_data, PAGINATION_DEFAULT
from app_utils.model_types.manager import DbBackupType
from app_utils.model_types.store import SalaryPaginatorType
from apps.manage_system.models import Salary
from apps.stores.models import Store


class ManageSystemQuery(AbstractType):
	db_backup = graphene.Field(DbBackupType)
	salaries = graphene.Field(
		SalaryPaginatorType,
		created_at=graphene.Date(),
		page_count=graphene.Int(),
		page_number=graphene.Int(),
	)

	@login_required
	def resolve_db_backup(self, info, **kwargs):
		try:
			call_command('dbbackup')
			# print('Db backed up')
			res = {'message': 'Db backed up'}
			return res
		except CommandError as error:
			# print(error)
			raise GraphQLError('Error while backup')

	@superuser_required
	def resolve_salaries(self, info, created_at=None, **kwargs):
		page_count = kwargs.get('page_count', PAGINATION_DEFAULT['page_count'])
		page_number = kwargs.get('page_number', PAGINATION_DEFAULT['page_number'])
		salaries = Salary.objects.all()
		paginated_result = paginate_data(salaries, page_count, page_number)

		return paginated_result
