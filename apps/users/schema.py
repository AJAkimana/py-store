import graphene
from django.contrib.auth import authenticate
from graphql_jwt.decorators import login_required
from django.contrib.auth.models import update_last_login
from graphene_django import DjangoObjectType
from graphql import GraphQLError
from graphql_jwt.utils import jwt_payload, jwt_encode

from app_utils.database import get_model_object
from apps.users.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User


class RegisterUser(graphene.Mutation):
    """
    This is a mutation used to create new users
    """
    user = graphene.Field(UserType)
    message = graphene.String()

    class Arguments:
        email = graphene.String()
        user_name = graphene.String()
        password = graphene.String()

    def mutate(self, info, **kwargs):
        new_user = User.objects.create_user(**kwargs)
        new_user.set_password = kwargs.get('password')
        new_user.save()

        return RegisterUser(message='Success', user=new_user)


class LoginUser(graphene.Mutation):
    """
    Login a users with their credentials

    args:
        password(str): users's registered password
        email(str): users's registered email

    returns:
        message(str): success messsage confirming login
        token(str): JWT authorization token used to validate the login
        user(obj): 'User' object containing details of the logged in users
    """
    message = graphene.String()
    token = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        email = graphene.String()
        password = graphene.String()

    def mutate(self, info, email, password, **kwargs):
        user_auth = authenticate(email=email, password=password)
        if user_auth is None:
            raise GraphQLError('Invalid credentials')
        user = get_model_object(User, 'email', email)
        update_last_login(sender=User, user=user)
        user_payload = jwt_payload(user_auth)
        token = jwt_encode(user_payload)

        return LoginUser(message='Success', token=token, user=user)


class UserMutation(graphene.ObjectType):
    register_user = RegisterUser.Field()
    login_user = LoginUser.Field()


class UserQuery(graphene.AbstractType):
    me = graphene.Field(UserType)
    
    @login_required
    def resolve_me(self, info, **kwargs):
        return info.context.user
