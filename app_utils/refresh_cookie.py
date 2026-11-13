from functools import wraps

from graphql_jwt.settings import jwt_settings
from graphql_jwt.utils import delete_cookie, set_cookie


def refresh_token_cookie(view_func):
	"""
	Persist the refresh token in an HttpOnly cookie.

	Mutations set `request.jwt_refresh_token` (a RefreshToken instance) to issue
	a cookie, or `request.delete_refresh_token_cookie` to clear it.
	"""
	@wraps(view_func)
	def wrapped_view(request, *args, **kwargs):
		request.jwt_cookie = True
		response = view_func(request, *args, **kwargs)

		refresh_token = getattr(request, 'jwt_refresh_token', None)
		if refresh_token is not None:
			set_cookie(
				response,
				jwt_settings.JWT_REFRESH_TOKEN_COOKIE_NAME,
				refresh_token.get_token(),
				expires=refresh_token.created + jwt_settings.JWT_REFRESH_EXPIRATION_DELTA,
			)
		elif getattr(request, 'delete_refresh_token_cookie', False):
			delete_cookie(response, jwt_settings.JWT_REFRESH_TOKEN_COOKIE_NAME)

		return response

	return wrapped_view
