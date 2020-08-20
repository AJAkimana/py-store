import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.constants import STORE_CHOICES
from apps.stores.models import Store
from app_utils.model_types.store import StoreInputType


class CreateStore(graphene.Mutation):
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
		print(f'{stores}  ==========')
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
		
		return CreateStore(
			message="stores successfully saved",
			total_saved=saved,
			total_not_saved=not_saved)


class StoreMutation(graphene.ObjectType):
	create_store = CreateStore.Field()
