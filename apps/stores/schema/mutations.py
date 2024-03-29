import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required, superuser_required

from app_utils.constants import STORE_CHOICES
from app_utils.database import get_model_object
from app_utils.validations.validate_store import ValidateStore
from apps.households.models import Household
from apps.properties.models import PropDetail
from apps.stores.models import Store, RecurringStore
from app_utils.model_types.store import StoreInputType, StoreType


class CreateEditStore(graphene.Mutation):
	message = graphene.String()
	store = graphene.Field(StoreType)

	class Arguments:
		amount = graphene.Float(required=True)
		record_type = graphene.String(required=True)
		property_id = graphene.String(required=False)
		is_inflow = graphene.Boolean(required=True)
		action_date = graphene.Date(required=True)
		description = graphene.String(required=True)
		is_recurring = graphene.Boolean(required=False)
		household_id = graphene.String(required=True)

	def mutate(self, into, **kwargs):
		pass


class CreateStore(CreateEditStore):
	"""
	Mutation to create a store. Inherits from 'CreateEditStore' class
	"""
	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user

		household = get_model_object(Household, 'id', kwargs['household_id'])
		store = Store(user=user, household=household)
		validator = ValidateStore(**kwargs)

		new_store = validator.validate_and_save_store(store)

		if kwargs['is_recurring']:
			RecurringStore.objects.get_or_create(user=user, name=kwargs['description'])
		return CreateStore(message='Successfully saved', store=new_store)


class UpdateStore(CreateEditStore):
	"""
	Mutation to update a store. Inherits from 'CreateEditStore' class
	"""
	class Arguments(CreateEditStore.Arguments):
		id = graphene.String(required=True)

	@login_required
	def mutate(self, info, **kwargs):
		store = get_model_object(Store, 'id', kwargs.get('id'))
		validator = ValidateStore(**kwargs)

		updated_store = validator.validate_and_save_store(store)
		return UpdateStore(message='Successfully update', store=updated_store)


class CreateManyStores(graphene.Mutation):
	message = graphene.String()
	total_saved = graphene.Int()
	total_not_saved = graphene.Int()

	class Arguments:
		stores = graphene.List(StoreInputType)

	@login_required
	def mutate(self, info, **kwargs):
		saved = 0
		not_saved = 0
		stores = kwargs['stores']
		for store in stores:
			store_type = [item for item in STORE_CHOICES if item[0] == store['record_type']]
			if not store_type:
				raise GraphQLError('Invalid store type')
			has_saved = Store.objects.filter(
				action_date=store['action_date'],
				description=store['description']).first()
			if not has_saved:
				store['user_id'] = info.context.user.id
				new_store = Store(**store)
				new_store.save()
				saved += 1
			else:
				not_saved += 1

		return CreateManyStores(
			message="stores successfully saved",
			total_saved=saved,
			total_not_saved=not_saved)


class MigrateStoreProperties(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		pass

	@superuser_required
	def mutate(self, info, **kwargs):
		stores = Store.objects.filter(is_property=True)
		fields_to_update = ['property_id', 'is_property']
		for store in stores:
			prop_detail = PropDetail.objects.filter(
				title=store.description,
				amount=store.amount,
				created_at__date=store.updated_at.date()).first()
			if prop_detail:
				store.property_id = prop_detail.property_id
				store.is_property = False

			else:
				print('Failed store======>')
				print(store)
				break
		Store.objects.bulk_update(stores, fields_to_update, batch_size=500)

		return MigrateStoreProperties(message=f"{len(stores)} stores successfully migrated")


class StoreMutations(graphene.ObjectType):
	create_store = CreateStore.Field()
	update_store = UpdateStore.Field()
	create_many_stores = CreateManyStores.Field()
	migrate_store_properties = MigrateStoreProperties.Field()
