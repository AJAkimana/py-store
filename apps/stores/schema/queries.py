import graphene
from graphene import relay
from graphene_django import DjangoObjectType
from django.db.models import Q, Count
from graphql_jwt.decorators import login_required

from apps.stores.models import Store


class StoreType(DjangoObjectType):
    class Meta:
        model = Store


class MonthType(DjangoObjectType):
    class Meta:
        model = Store
        fields = {
            'action_date': ['exact', 'action_date__month'],
            'action_date': ['exact', 'action_date__year']
        }
        interfaces = (relay.Node,)


class StoreQuery(graphene.AbstractType):
    stores = graphene.List(StoreType, search=graphene.String(), store_type=graphene.String())
    total_inflow = graphene.Int(store_type=graphene.String())
    total_outflow = graphene.Int(store_type=graphene.String())
    store_count = graphene.Int()
    monthly_store = graphene.List(MonthType)

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

    @login_required
    def resolve_store_count(self):
        return Store.objects.count()

    @login_required
    def resolve_monthly_store(self):
        monthly_stores = Store.objects \
            .values() \
            .annotate(count=Count('pk'))
        import pdb
        pdb.set_trace()
        return monthly_stores
