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
	
	# def create(self, validated_data):
	# 	"""
	# 	Create and return a new `Store` instance, given the validated data.
	# 	"""
	# 	return Store.objects.create(**validated_data)
	#
	# def update(self, instance, validated_data):
	# 	"""Snippet
	# 	Update and return an existing `Store` instance, given the validated data.
	# 	"""
	# 	instance.amount = validated_data.get('amount', instance.amount)
	# 	instance.record_type = validated_data.get('record_type', instance.record_type)
	# 	instance.is_property = validated_data.get('is_property', instance.is_property)
	# 	instance.is_inflow = validated_data.get('is_inflow', instance.is_inflow)
	# 	instance.description = validated_data.get('description', instance.description)
	# 	instance.action_date = validated_data.get('action_date', instance.action_date)
	# 	instance.save()
	#
	# 	return instance
