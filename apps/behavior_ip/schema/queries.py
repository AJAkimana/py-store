import graphene
from django.db.models import Q
from graphql_jwt.decorators import login_required

from app_utils.helpers import paginate_data
from app_utils.model_types.store import BehaviorPaginatorType
from apps.users.models import User


class BehaviorQuery(graphene.ObjectType):
	behaviors_list = graphene.Field(
		BehaviorPaginatorType,
		search_key=graphene.Argument(graphene.String, required=False),
	)

	@login_required
	def resolve_behaviors_list(self, info, search_key):
		user = info.context.user
		filters = Q(name__icontains=search_key)
		behaviors = User.get_user_behaviors(user, filters)

		paginated_result = paginate_data(behaviors, page_count=10, page_number=1)
		return paginated_result
