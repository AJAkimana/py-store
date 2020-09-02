from rest_framework import serializers
from apps.properties.models import Property


class PropertySerializer(serializers.ModelSerializer):
	class Meta:
		model = Property
		fields = ('id', 'name', 'price', 'description', 'is_active')
