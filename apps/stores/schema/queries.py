import graphene
from graphene_django import DjangoObjectType
from django.db.models import Q, Count
from graphql_jwt.decorators import login_required

from apps.stores.models import Store


class StoreType(DjangoObjectType):
    class Meta:
        model = Store


class MonthType(graphene.ObjectType):
    label = graphene.String()
    value = graphene.Int()


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
    def resolve_monthly_store(self, info):
        query = """
            SELECT id, DATE_FORMAT(action_date, '%%b, %%Y') AS label,
            SUM(CASE WHEN is_inflow=0 THEN amount ELSE 0 END) AS value 
            FROM stores_store GROUP BY label, year(action_date) 
            ORDER BY action_date DESC """
        stores = Store.objects.raw(query)
        return stores
