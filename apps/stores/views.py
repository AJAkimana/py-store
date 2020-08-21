from django.shortcuts import render
from rest_framework import viewsets
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication,\
	TokenAuthentication
from rest_framework.views import APIView
from apps.stores.models import Store
from apps.stores.serializers import StoreSerializer
from app_utils.helpers import server_response


class StoreView(viewsets.ModelViewSet):
	queryset = Store.objects.all()
	serializer_class = StoreSerializer


class MigrateStoreView(APIView):
	authentication_classes = [SessionAuthentication, TokenAuthentication]
	permission_classes = [IsAuthenticated]
	renderer_classes = [JSONRenderer]
	parser_classes = (JSONParser, )
	
	def post(self, request):
		saved = 0
		not_saved = 0
		for store in request.data['stores']:
			serializer = StoreSerializer(data=store)
			if serializer.is_valid():
				serializer.save(user=request.user)
				saved += 1
			else:
				not_saved += 1
		message = f'{saved} stores saved, {not_saved} remained'
		
		return server_response(200, message)
