import graphene
from graphene_django import DjangoObjectType
from apps.stores.models import Store
from apps.user.models import User


class StoreType(DjangoObjectType):
    class Meta:
        model = Store


class UserType(DjangoObjectType):
    class Meta:
        model = User


class StoreQuery(graphene.ObjectType):
    stores = graphene.List(StoreType)

    def resolve_stores(self, info, **kwargs):
        return Store.objects.all()
