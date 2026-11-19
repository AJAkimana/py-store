"""
Auth smoke tests through the real GraphQL endpoint, so they cover what schema.execute
skips: the JWT middleware, the refresh-token cookie decorator and the auth backend.
"""
import json
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from graphql_jwt.settings import jwt_settings

from apps.budgets.tests import make_user
from apps.users.backends import SESSION_ENDED_MESSAGE

URL = '/api/d2dstore/'
PASSWORD = 'Correct-Horse-42'
COOKIE = jwt_settings.JWT_REFRESH_TOKEN_COOKIE_NAME

LOGIN = '''
mutation($email: String!, $password: String!) {
  loginUser(email: $email, password: $password) { token mfaRequired user { email } }
}'''
ME = '{ me { email } }'
REFRESH = 'mutation { refreshToken { token } }'
VERIFY = 'mutation($token: String) { verifyToken(token: $token) { payload } }'
LOGOUT = 'mutation { logoutUser { message } }'
USERS = '{ users { __typename } }'


class AuthFlowTests(TestCase):
	def setUp(self):
		self.user = make_user()
		self.user.set_password(PASSWORD)
		self.user.save()

	def gql(self, query, auth=None, **variables):
		headers = {'HTTP_AUTHORIZATION': f'{jwt_settings.JWT_AUTH_HEADER_PREFIX} {auth}'} if auth else {}
		response = self.client.post(
			URL, json.dumps({'query': query, 'variables': variables}),
			content_type='application/json', **headers)
		return response, response.json()

	def login(self):
		response, body = self.gql(LOGIN, email=self.user.email, password=PASSWORD)
		self.assertNotIn('errors', body, body)
		return response, body['data']['loginUser']['token']

	def error_message(self, body):
		self.assertIn('errors', body, body)
		return body['errors'][0]['message']

	def test_login_returns_token_and_sets_httponly_refresh_cookie(self):
		response, body = self.gql(LOGIN, email=self.user.email, password=PASSWORD)

		data = body['data']['loginUser']
		self.assertTrue(data['token'])
		self.assertFalse(data['mfaRequired'])
		self.assertEqual(data['user']['email'], self.user.email)
		cookie = response.cookies[COOKIE]
		self.assertTrue(cookie.value)
		self.assertTrue(cookie['httponly'])
		self.assertNotIn('refreshToken', json.dumps(body))

	def test_wrong_password_is_rejected(self):
		_, body = self.gql(LOGIN, email=self.user.email, password='wrong')
		self.assertEqual(self.error_message(body), 'Invalid credentials')

	def test_access_token_authenticates_login_required_query(self):
		_, token = self.login()
		_, body = self.gql(ME, auth=token)
		self.assertEqual(body['data']['me']['email'], self.user.email)

	def test_login_required_query_without_token_fails(self):
		_, body = self.gql(ME)
		self.assertIn('permission', self.error_message(body).lower())

	def test_superuser_required_query_rejects_regular_user(self):
		_, token = self.login()
		_, body = self.gql(USERS, auth=token)
		self.assertIn('permission', self.error_message(body).lower())

	def test_verify_token_returns_payload(self):
		_, token = self.login()
		_, body = self.gql(VERIFY, token=token)
		self.assertEqual(body['data']['verifyToken']['payload']['email'], self.user.email)

	def test_refresh_rotates_cookie_and_old_cookie_stops_working(self):
		response, _ = self.login()
		old_cookie = response.cookies[COOKIE].value

		response, body = self.gql(REFRESH)
		self.assertNotIn('errors', body, body)
		new_token = body['data']['refreshToken']['token']
		self.assertTrue(new_token)
		self.assertNotEqual(response.cookies[COOKIE].value, old_cookie)
		_, body = self.gql(ME, auth=new_token)
		self.assertEqual(body['data']['me']['email'], self.user.email)

		self.client.cookies[COOKIE] = old_cookie
		_, body = self.gql(REFRESH)
		self.assertEqual(self.error_message(body), 'Invalid refresh token')

	def test_refresh_without_cookie_fails(self):
		_, body = self.gql(REFRESH)
		self.assertEqual(self.error_message(body), 'Refresh token is required')

	def test_logout_clears_cookie_and_revokes_refresh_token(self):
		response, token = self.login()
		old_cookie = response.cookies[COOKIE].value

		response, body = self.gql(LOGOUT, auth=token)
		self.assertEqual(body['data']['logoutUser']['message'], 'Success')
		self.assertEqual(response.cookies[COOKIE].value, '')

		self.client.cookies[COOKIE] = old_cookie
		_, body = self.gql(REFRESH)
		self.assertEqual(self.error_message(body), 'Invalid refresh token')

	def test_token_issued_before_password_change_is_rejected(self):
		_, token = self.login()
		self.user.password_changed_at = timezone.now() + timedelta(seconds=1)
		self.user.save(update_fields=['password_changed_at'])

		_, body = self.gql(ME, auth=token)
		self.assertEqual(self.error_message(body), SESSION_ENDED_MESSAGE)
