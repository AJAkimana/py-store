import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.constants import STORE_CHOICES
from apps.properties.models import PropDetail
from apps.stores.models import Store
from app_utils.model_types.store import StoreInputType, StoreType
from apps.users.models import User


class CreateStore(graphene.Mutation):
	message = graphene.String()
	store = graphene.Field(StoreType)

	class Arguments:
		amount = graphene.Float(required=True)
		record_type = graphene.String(required=True)
		property_id = graphene.String(required=False)
		is_inflow = graphene.Boolean(required=True)
		action_date = graphene.Date(required=True)
		description = graphene.String(required=True)

	@login_required
	def mutate(self, info, **kwargs):
		store_type = [item for item in STORE_CHOICES if item[0] == kwargs['record_type']]
		user = info.context.user
		kwargs['is_property'] = False
		property_id = kwargs['property_id']
		del kwargs['property_id']
		if not store_type:
			raise GraphQLError('Invalid store type')
		has_saved = Store.objects.filter(
			action_date=kwargs['action_date'],
			description=kwargs['description'],
			user=user).first()
		if has_saved:
			raise GraphQLError('The record has already been recorded')
		if property_id:
			the_property = User.get_user_properties(user)\
				.filter(id=property_id).first()
			if the_property:
				new_prop_detail = PropDetail(
					title=kwargs['description'],
					type='in' if kwargs['is_inflow'] else 'out',
					amount=kwargs['amount'],
					property=the_property
				)
				new_prop_detail.save()
				kwargs['is_property'] = True
			else:
				raise GraphQLError('The property does not exist')
		kwargs['user_id'] = user.id
		new_store = Store(**kwargs)
		new_store.save()

		return CreateStore(
			message="Successfully saved",
			store=new_store)


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


class StoreMutation(graphene.ObjectType):
	create_store = CreateStore.Field()
	create_many_stores = CreateManyStores.Field()
