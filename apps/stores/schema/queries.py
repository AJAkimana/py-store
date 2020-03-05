import graphene
from graphene_django import DjangoObjectType
from django.db.models import Q
from graphql_jwt.decorators import login_required

from apps.stores.models import Store


class StoreType(DjangoObjectType):
    class Meta:
        model = Store


class StoreQuery(graphene.AbstractType):
    stores = graphene.List(StoreType, search=graphene.String(), store_type=graphene.String())
    total_inflow = graphene.Int(store_type=graphene.String())
    total_outflow = graphene.Int(store_type=graphene.String())

    @login_required
    def resolve_stores(self, info, search=None, store_type='use', **kwargs):
        if search:
            search_filter = (Q(amount__icontains=search) |
                             Q(description__icontains=search))
            return Store.objects.filter(search_filter)
        return Store.objects.filter(record_type=store_type)

    @staticmethod
    @login_required
    def resolve_total_inflow(self, info, store_type='use', **kwargs):
        return Store.get_total(Store, store_type=store_type, is_inflow=True)

    @staticmethod
    @login_required
    def resolve_total_outflow(self, info, store_type='use', **kwargs):
        return Store.get_total(Store, store_type=store_type, is_inflow=False)
