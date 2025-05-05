from datetime import date

from django.db.models import Q
from graphql import GraphQLError

from apps.behavior_ip.models import Behavior, BehaviorScore


class ValidateBehavior:
	def __init__(self, **behavior_body: Behavior):
		self.behavior = behavior_body

	def validate_and_save(self, behavior: Behavior):
		"""
    Args:
      budget: The store instance

    Returns: new updated budget after it has been saved into database
    """
		behavior_id = self.behavior.get('id', None)
		for key, value in self.behavior.items():
			if isinstance(value, str) and value.strip() == '':
				raise GraphQLError(f"The {key} field can't be empty")
			if key == 'id':
				continue
			setattr(behavior, key, value)

		filters = Q(name__icontains=behavior.name, user=behavior.user)
		if behavior_id:
			filters = (~Q(id=behavior_id) & filters)
		alike_behaviors = Behavior.objects.filter(filters)

		if not alike_behaviors.exists():
			the_behavior = Behavior.objects.create(**self.behavior)
		elif len(alike_behaviors) == 1:
			the_behavior = alike_behaviors.first()
		else:
			raise GraphQLError(f"Too many behaviors with the same name")

		score = BehaviorScore.objects.filter(behavior=the_behavior, action_date__date=date(behavior.action_date)).first()
		if score:
			raise GraphQLError(f"Behavior score already exists for the date {behavior.action_date}")

		return BehaviorScore.objects.create(behavior=the_behavior, **self.behavior)
