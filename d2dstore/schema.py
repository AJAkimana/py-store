import graphene
import graphql_jwt
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
	token_auth = graphql_jwt.ObtainJSONWebToken.Field()
	verify_token = graphql_jwt.Verify.Field()
	refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
