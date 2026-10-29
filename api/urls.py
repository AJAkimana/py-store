from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from rest_framework.documentation import include_docs_urls

from app_utils.refresh_cookie import refresh_token_cookie
from d2dstore.views import AppGraphQLView

core_schema_view = include_docs_urls(title='D2DStore API')

admin.site.site_header = "Day-To-Day Store Admin"
admin.site.site_title = "Day-To-Day Store Admin Portal"
admin.site.index_title = "Welcome to Day-To-Day Store Portal"

urlpatterns = [
	path('admin/', admin.site.urls),
	path('d2dstore/', csrf_exempt(refresh_token_cookie(AppGraphQLView.as_view(graphiql=settings.DEBUG)))),
	path('d2dstore/schema/', core_schema_view),
]
