from django.contrib.auth.models import update_last_login
from django.utils import timezone
from graphql_jwt.refresh_token.utils import get_refresh_token_model
from graphql_jwt.settings import jwt_settings
from graphql_jwt.shortcuts import get_token, create_refresh_token
from rest_framework.authtoken.models import Token

from apps.users.models import User

RefreshToken = get_refresh_token_model()


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


def revoke_refresh_tokens(user: User, keep_token: str = None) -> int:
	"""
	Sign the user out of other sessions by revoking their refresh tokens, optionally
	keeping one (the current cookie). Access tokens already issued stay valid until
	they expire (JWT_EXPIRATION_DELTA).
	"""
	tokens = RefreshToken.objects.filter(user=user, revoked__isnull=True)
	if keep_token:
		tokens = tokens.exclude(token=keep_token)
	return tokens.update(revoked=timezone.now())


def current_refresh_token(info) -> str:
	return info.context.COOKIES.get(jwt_settings.JWT_REFRESH_TOKEN_COOKIE_NAME)
