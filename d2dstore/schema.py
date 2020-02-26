import graphene
from apps.stores.schema.queries import StoreQuery
from apps.stores.schema.mutations import StoreMutation


class AppQuery(StoreQuery, graphene.ObjectType):
    pass


class AppMutations(StoreMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
