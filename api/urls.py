from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

from app_utils.refresh_cookie import refresh_token_cookie
from apps.stores.views import StoreView, MigrateStoreView

core_schema_view = include_docs_urls(title='D2DStore API')

admin.site.site_header = "Day-To-Day Store Admin"
admin.site.site_title = "Day-To-Day Store Admin Portal"
admin.site.index_title = "Welcome to Day-To-Day Store Portal"

router = routers.DefaultRouter()
router.register('', StoreView)

urlpatterns = [
	path('admin/', admin.site.urls),
	path('d2dstore/', csrf_exempt(refresh_token_cookie(GraphQLView.as_view(graphiql=True)))),
	path('stores/', include('apps.stores.urls')),
	path('d2dstore/schema/', core_schema_view),
	path('migration', MigrateStoreView.as_view())
]
