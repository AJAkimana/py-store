import graphene
import graphql_jwt
from graphql_jwt import ObtainJSONWebToken

from apps.stores.schema.queries import StoreQuery
from apps.properties.schema.queries import PropertyQuery
from apps.stores.schema.mutations import StoreMutation
from apps.users.schema import UserMutation


class AppQuery(StoreQuery, PropertyQuery,  graphene.ObjectType):
    pass


class AppMutations(StoreMutation, UserMutation, graphene.ObjectType):
    token_auth = ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
