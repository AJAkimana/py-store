from django.contrib.auth.models import update_last_login
from graphql_jwt.shortcuts import get_token, create_refresh_token
from rest_framework.authtoken.models import Token

from apps.users.models import User


def issue_session(info, user: User):
	"""
	Log the user in: record the login, set the refresh-token cookie and
	return (access token, REST token). Call this only once every factor has passed.
	"""
	update_last_login(sender=User, user=user)
	token = get_token(user)
	info.context.jwt_refresh_token = create_refresh_token(user)
	rest_token, _ = Token.objects.get_or_create(user=user)
	return token, rest_token
