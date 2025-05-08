from datetime import date

from django.db.models import Q
# from django.utils.timezone import now
from graphql import GraphQLError

from apps.behavior_ip.models import Behavior, BehaviorScore


def get_score(rate: str, count: int):
	if rate == 'so-so':
		return 0
	multi = 1 if rate == 'good' else -1
	return 100 / (count + 1) * multi


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
			the_behavior = Behavior.objects.create(
				name=behavior.name,
				description=behavior.name,
				user=behavior.user,
				household=behavior.household
			)
		elif len(alike_behaviors) == 1:
			the_behavior = alike_behaviors.first()
		else:
			raise GraphQLError(f"Too many behaviors with the same name")
		scores = BehaviorScore.objects.filter(behavior=the_behavior, action_date=self.behavior['action_date'])

		score_count = len(scores)
		if scores.exists():
			for s in scores:
				if s.rate != 'so-so':
					new_score = get_score(s.rate, score_count)
					s.score = new_score
					s.save()

		new_score = get_score(self.behavior['rate'], score_count)
		return BehaviorScore.objects.create(
			behavior=the_behavior,
			score=new_score,
			rate=self.behavior['rate'],
			description=self.behavior['description']
		)
