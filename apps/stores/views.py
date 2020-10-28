from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, \
	TokenAuthentication
from rest_framework.views import APIView
from apps.stores.models import Store
from apps.properties.serializers import PropDetailSerializer
from apps.stores.serializers import StoreSerializer
from app_utils.helpers import server_response


class StoreView(viewsets.ModelViewSet):
	queryset = Store.objects.all()
	serializer_class = StoreSerializer


class MigrateStoreView(APIView):
	authentication_classes = [TokenAuthentication]
	permission_classes = [IsAuthenticated]
	renderer_classes = [JSONRenderer]
	parser_classes = (JSONParser,)
	
	def post(self, request):
		saved = 0
		not_saved = 0
		prop_saved = 0
		prop_not_saved = 0
		if not request.data:
			return server_response(400, 'Invalid request')
		if 'stores' not in request.data.keys():
			return server_response(400, 'Invalid request stores')
		if not isinstance(request.data['stores'], list):
			return server_response(400, 'Stores has to be a list')
		for store in request.data['stores']:
			serializer = StoreSerializer(data=store)
			if serializer.is_valid():
				serializer.save(user=request.user)
				
				if store['is_property']:
					prop = {
						'title': store['description'],
						'type': 'in' if store['is_inflow'] else 'out',
						'amount': store['amount']
					}
					prop_serializer = PropDetailSerializer(data=prop)
					if prop_serializer.is_valid():
						prop_serializer.save(property_id=store['property_id'])
						prop_saved += 1
					else:
						prop_not_saved += 1
				saved += 1
			else:
				not_saved += 1
		message = f'{saved} stores saved({prop_saved}p), {not_saved} remained({prop_not_saved})'
		
		return server_response(200, message)
