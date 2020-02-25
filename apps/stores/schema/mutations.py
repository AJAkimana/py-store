import graphene
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
        user_id = graphene.Int()

    def mutate(self, info, **kwargs):
        store = Store(**kwargs)
        store.save()

        return CreateStore(message="Success", new_store=store)


class StoreMutation(graphene.ObjectType):
    create_store = CreateStore.Field()
