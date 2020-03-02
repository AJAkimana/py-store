import graphene
from graphene_django import DjangoObjectType
from apps.stores.models import Store


class StoreType(DjangoObjectType):
    class Meta:
        model = Store


class StoreQuery(graphene.ObjectType):
    stores = graphene.List(StoreType)

    def resolve_stores(self, info, **kwargs):
        return Store.objects.all()
