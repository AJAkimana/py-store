import graphene
import graphql_jwt
from graphql_jwt import ObtainJSONWebToken

from apps.stores.schema.queries import StoreQuery
from apps.properties.schema.queries import PropertyQuery
from apps.properties.schema.mutations import PropertyMutations
from apps.stores.schema.mutations import StoreMutation
from apps.users.schema.mutations import UserMutation
from apps.users.schema.queries import UserQuery


class AppQuery(UserQuery, StoreQuery, PropertyQuery, graphene.ObjectType):
	pass


class AppMutations(
	StoreMutation,
	UserMutation,
	PropertyMutations,
	graphene.ObjectType):
	token_auth = ObtainJSONWebToken.Field()
	verify_token = graphql_jwt.Verify.Field()
	refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
