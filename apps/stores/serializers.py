from rest_framework import serializers
from apps.stores.models import Store


class StoreSerializer(serializers.ModelSerializer):
	class Meta:
		model = Store
		fields = ('id', 'amount', 'record_type', \
		          'is_property', 'is_inflow', 'description', \
		          'action_date')
