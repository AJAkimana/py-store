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


class StoreView(viewsets.ModelViewSet):
	queryset = Store.objects.all()
	serializer_class = StoreSerializer


class MigrateStoreView(APIView):
	authentication_classes = [SessionAuthentication, TokenAuthentication]
	permission_classes = [IsAuthenticated]
	renderer_classes = [JSONRenderer]
	parser_classes = (JSONParser, )
	
	def post(self, request):
		for store in request.data['stores']:
			print(store)
		response = {
			"message": "Request accepted",
			"user": request.data,
			"status": status.HTTP_200_OK
		}
		return Response(response, status.HTTP_200_OK)
