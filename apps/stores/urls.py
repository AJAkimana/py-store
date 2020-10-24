from django.urls import path, include
from rest_framework import routers
from apps.stores.views import StoreView, MigrateStoreView

router = routers.DefaultRouter()
router.register('', StoreView)

urlpatterns = [
    path('', include(router.urls)),
    path('migration', MigrateStoreView.as_view())
]
