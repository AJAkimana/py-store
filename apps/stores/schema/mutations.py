import graphene
from graphql import GraphQLError
from graphql_jwt.decorators import login_required

from app_utils.constants import STORE_CHOICES
from apps.stores.models import Store
from apps.stores.schema.queries import StoreType


class CreateStore(graphene.Mutation):
    message = graphene.String()
    new_store = graphene.Field(StoreType)

    class Arguments:
        amount = graphene.Float()
        record_type = graphene.String()
        is_property = graphene.Boolean()
        is_inflow = graphene.Boolean()
        description = graphene.String()

    @login_required
    def mutate(self, info, **kwargs):
        kwargs['user_id'] = info.context.user.id
        store_type = [item for item in STORE_CHOICES if item[0] == kwargs['record_type']]
        if not store_type:
            raise GraphQLError('Invalid store type')
        store = Store(**kwargs)
        store.save()

        return CreateStore(message="Success", new_store=store)


class StoreMutation(graphene.ObjectType):
    create_store = CreateStore.Field()
