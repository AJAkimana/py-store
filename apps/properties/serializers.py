from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.properties.models import Property, PropDetail


class PropertySerializer(serializers.ModelSerializer):
	class Meta:
		model = Property
		fields = ('id', 'name', 'price', 'description', 'is_active')


class PropDetailSerializer(serializers.ModelSerializer):
	class Meta:
		model = PropDetail
		fields = ('id', 'title', 'amount', 'type')
		validators = [
			UniqueTogetherValidator(
				queryset=PropDetail.objects.all(), fields=['title', 'amount', 'type'],
				message="Invalid input prop detail"
			)
		]
