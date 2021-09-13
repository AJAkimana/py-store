import graphene
from graphql_jwt import ObtainJSONWebToken, Verify, Refresh

from apps.manage_system.schema.mutations import ManageSystemMutations
from apps.stores.schema.queries import StoreQuery
from apps.properties.schema.queries import PropertyQuery
from apps.properties.schema.mutations import PropertyMutations
from apps.stores.schema.mutations import StoreMutation
from apps.users.schema.mutations import UserMutation
from apps.users.schema.queries import UserQuery
from apps.manage_system.schema.queries import ManageSystemQuery


class AppQuery(
	UserQuery,
	StoreQuery,
	PropertyQuery,
	ManageSystemQuery,
	graphene.ObjectType
):
	pass


class AppMutations(
	StoreMutation,
	UserMutation,
	PropertyMutations,
	ManageSystemMutations,
	graphene.ObjectType
):
	token_auth = ObtainJSONWebToken.Field()
	verify_token = Verify.Field()
	refresh_token = Refresh.Field()


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
