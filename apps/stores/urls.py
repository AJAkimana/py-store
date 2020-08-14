from django.urls import path, include
from rest_framework import routers
from apps.stores.views import StoreView

router = routers.DefaultRouter()
router.register('stores', StoreView)

urlpatterns = [
    path('', include(router.urls))
]
