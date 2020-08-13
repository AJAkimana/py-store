import graphene
from graphene_django import DjangoObjectType
from apps.users.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude_fields = ('password', 'previous_passwords')


class PaginatorUserType(graphene.ObjectType):
    page_data = graphene.List(UserType)
    num_pages = graphene.Int()
    total_count = graphene.Int()
