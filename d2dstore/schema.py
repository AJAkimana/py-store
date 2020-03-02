import graphene
from apps.stores.schema.queries import StoreQuery
from apps.stores.schema.mutations import StoreMutation
from apps.user.schema import UserMutation


class AppQuery(StoreQuery, graphene.ObjectType):
    pass


class AppMutations(StoreMutation, UserMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
