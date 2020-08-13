import graphene
from graphql_jwt.decorators import login_required
from app_utils.model_types.user import UserType


class UserQuery(graphene.AbstractType):
	me = graphene.Field(UserType)
	
	@login_required
	def resolve_me(self, info, **kwargs):
		return info.context.user
