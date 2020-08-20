"""d2dstore URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from rest_framework.documentation import include_docs_urls

core_schema_view = include_docs_urls(title='D2DStore API')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('d2dstore/', csrf_exempt(GraphQLView.as_view(graphiql=True))),
    path('stores/', include('apps.stores.urls')),
    path('d2dstore/schema/', core_schema_view)
]
