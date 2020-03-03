import graphene
from graphene_django import DjangoObjectType
from django.db.models import Q
from graphql_jwt.decorators import login_required

from apps.stores.models import Store


class StoreType(DjangoObjectType):
    class Meta:
        model = Store


class StoreQuery(graphene.ObjectType):
    stores = graphene.List(StoreType, search=graphene.String())

    @login_required
    def resolve_stores(self, info, search=None, **kwargs):
        # import pdb
        # pdb.set_trace()
        if search:
            search_filter = (Q(amount__icontains=search) |
                             Q(description__icontains=search))
            return Store.objects.filter(search_filter)
        return Store.objects.all()
