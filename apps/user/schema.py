import graphene
from graphene_django import DjangoObjectType

from apps.user.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User


class RegisterUser(graphene.Mutation):
    """
    This is a mutation used to create new user
    """
    user = graphene.Field(UserType)
    success = graphene.String()

    class Arguments:
        email = graphene.String()
        user_name = graphene.String()
        password = graphene.String()

    def mutate(self, info, **kwargs):
        new_user = User.objects.create_user(**kwargs)
        new_user.set_password = kwargs.get('password')
        new_user.save()

        return RegisterUser(success='Success', user=new_user)


class UserMutation(graphene.ObjectType):
    register_user = RegisterUser.Field()
