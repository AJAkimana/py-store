import graphene
import graphql_jwt
from graphene_django.debug import DjangoDebug

from apps.households.schema.mutations import HouseholdMutations
from apps.households.schema.queries import HouseholdQuery
from apps.manage_system.schema.mutations import ManageSystemMutations
from apps.stores.schema.queries import StoreQuery
from apps.properties.schema.queries import PropertyQuery
from apps.properties.schema.mutations import PropertyMutations
from apps.stores.schema.mutations import StoreMutations
from apps.users.schema.mutations import UserMutations
from apps.users.schema.queries import UserQuery
from apps.manage_system.schema.queries import ManageSystemQuery


class AppQuery(
	UserQuery,
	StoreQuery,
	PropertyQuery,
	ManageSystemQuery,
	HouseholdQuery,
	graphene.ObjectType
):
	debug = graphene.Field(DjangoDebug, name="_debug")


class AppMutations(
	StoreMutations,
	UserMutations,
	PropertyMutations,
	ManageSystemMutations,
	HouseholdMutations,
	graphene.ObjectType
):
	token_auth = graphql_jwt.ObtainJSONWebToken.Field()
	verify_token = graphql_jwt.Verify.Field()
	refresh_token = graphql_jwt.Refresh.Field()


schema = graphene.Schema(query=AppQuery, mutation=AppMutations)
