from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from apps.stores.models import Store


class StoreSerializer(serializers.ModelSerializer):
	class Meta:
		model = Store
		fields = (
			'id', 'amount', 'record_type', 'is_property', 'is_inflow', 'description',
			'action_date')
		validators = [
			UniqueTogetherValidator(
				queryset=Store.objects.all(), fields=['description', 'action_date'],
				message="Invalid input store"
			)
		]
