from django.shortcuts import render
from rest_framework import viewsets
from apps.stores.models import Store
from apps.stores.serializers import StoreSerializer


class StoreView(viewsets.ModelViewSet):
	queryset = Store.objects.all()
	serializer_class = StoreSerializer

