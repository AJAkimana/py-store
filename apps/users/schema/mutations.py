import graphene
from django.contrib.auth import authenticate, logout
from graphql_jwt.decorators import login_required, superuser_required
from rest_framework.authtoken.models import Token
from django.core.exceptions import ValidationError
from graphql import GraphQLError
# from graphql_jwt.utils import jwt_payload, jwt_encode
from graphql_jwt.shortcuts import get_token, create_refresh_token, get_refresh_token
from graphql_jwt.exceptions import JSONWebTokenError
from graphql_jwt.settings import jwt_settings
from app_utils.database import get_model_object
from app_utils.emailing.auth_email import send_test_email
from apps.users.models import User, UserSettings, Currency, MfaMethod
from apps.users.session import issue_session, revoke_refresh_tokens, current_refresh_token
from app_utils.model_types.user import UserType, MfaStatusType, TotpSetupType, ManagedUserType
from apps.users import mfa, password_reset, user_management

APPEARANCE_FIELDS = ('theme_mode', 'primary_color', 'secondary_color')


class LoginUser(graphene.Mutation):
	"""
Login a users with their credentials

args:
password(str): user's registered password
email(str): user's registered email

returns:
message(str): success messsage confirming login
token(str): JWT authorization token used to validate the login
rest_token(str): JWT token used to validate REST endpoint access
user(obj): 'User' object containing details of the logged in users

The refresh token is set as an HttpOnly cookie, never returned in the body.

When two-factor authentication is on, no session is issued: the response has
mfa_required=True and an mfa_token to send to 'verifyMfaLogin' with the code.

When the user signed in with an invite's temporary password, no session is issued:
the response has password_change_required=True and a password_change_token to send
to 'setInitialPassword', after which the client signs in with the new password.
"""
	message = graphene.String()
	token = graphene.String()
	rest_token = graphene.String()
	user = graphene.Field(UserType)
	mfa_required = graphene.Boolean(required=True)
	mfa_token = graphene.String()
	mfa_methods = graphene.List(graphene.NonNull(graphene.String))
	mfa_default_method = graphene.String()
	password_change_required = graphene.Boolean(required=True)
	password_change_token = graphene.String()

	class Arguments:
		email = graphene.String()
		password = graphene.String()

	def mutate(self, info, email, password, **kwargs):
		user_auth = authenticate(email=email, password=password)

		if user_auth is None:
			raise GraphQLError('Invalid credentials')

		if not user_auth.is_verified:
			if user_management.temp_password_expired(user_auth):
				raise GraphQLError('Your temporary password has expired. Ask your administrator to send a new invite.')
			return LoginUser(
				message='Choose your own password to continue',
				mfa_required=False,
				password_change_required=True,
				password_change_token=user_management.password_change_token(user_auth),
			)

		if mfa.is_mfa_enabled(user_auth):
			try:
				challenge = mfa.start_login_challenge(user_auth)
			except mfa.MfaError as error:
				raise GraphQLError(str(error))
			# No user details until the second factor passes
			return LoginUser(
				message='Enter your verification code',
				mfa_required=True,
				mfa_token=challenge['mfa_token'],
				mfa_methods=challenge['methods'],
				mfa_default_method=challenge['default_method'],
				password_change_required=False,
			)

		token, rest_token = issue_session(info, user_auth)
		return LoginUser(message='Success', token=token, rest_token=rest_token,
										 user=user_auth, mfa_required=False, password_change_required=False)


class VerifyMfaLogin(graphene.Mutation):
	"""
	Second login step. 'method' is 'totp', 'email' or 'recovery'.
	On success it issues the session exactly like 'loginUser'.
	"""
	message = graphene.String()
	token = graphene.String()
	rest_token = graphene.String()
	user = graphene.Field(UserType)

	class Arguments:
		mfa_token = graphene.String(required=True)
		method = graphene.String(required=True)
		code = graphene.String(required=True)

	def mutate(self, info, mfa_token, method, code):
		try:
			user = mfa.verify_login(mfa_token, method, code)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		if not user.is_active:
			raise GraphQLError('Invalid credentials')

		# A recovery code means the usual factor may be lost or stolen: end other sessions
		if method == MfaMethod.RECOVERY:
			revoke_refresh_tokens(user)
		token, rest_token = issue_session(info, user)
		return VerifyMfaLogin(message='Success', token=token, rest_token=rest_token, user=user)


class RefreshToken(graphene.Mutation):
	"""
Issue a new JWT using the refresh token cookie.
The refresh token is rotated: the old one is revoked and a new cookie is set.
"""
	token = graphene.String()

	def mutate(self, info, **kwargs):
		context = info.context
		cookie_token = context.COOKIES.get(jwt_settings.JWT_REFRESH_TOKEN_COOKIE_NAME)
		if not cookie_token:
			raise GraphQLError('Refresh token is required')

		try:
			old_refresh_token = get_refresh_token(cookie_token, context)
		except JSONWebTokenError:
			context.delete_refresh_token_cookie = True
			raise GraphQLError('Invalid refresh token')

		if old_refresh_token.is_expired(context):
			old_refresh_token.revoke(context)
			context.delete_refresh_token_cookie = True
			raise GraphQLError('Refresh token is expired')

		user = old_refresh_token.user
		old_refresh_token.revoke(context)
		context.jwt_refresh_token = create_refresh_token(user)

		return RefreshToken(token=get_token(user))


class UpdateUserProfile(graphene.Mutation):
	"""
	Update the logged-in user's own profile. Only the fields sent are changed.
	Passwords are changed through 'ResetPassword', which checks the old one.
	"""
	user = graphene.Field(UserType)
	message = graphene.String()

	class Arguments:
		first_name = graphene.String()
		last_name = graphene.String()
		phone = graphene.String()

	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user

		for key, value in kwargs.items():
			if value is None:
				continue
			value = value.strip()
			if not value:
				raise GraphQLError(f"The {key.replace('_', ' ')} field can't be empty")
			setattr(user, key, value)

		if kwargs.get('phone') and User.objects.filter(phone=user.phone).exclude(id=user.id).exists():
			raise GraphQLError('This phone number is already used by another account')

		user.save()
		return UpdateUserProfile(message='Profile updated successfully', user=user)


class ResetPassword(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		email = graphene.String()
		old_password = graphene.String()
		new_password = graphene.String()

	def mutate(self, info, email, old_password, new_password, **kwargs):
		if old_password == new_password:
			raise GraphQLError('You cannot set the same password')
		user_auth = authenticate(email=email, password=old_password)
		if not user_auth:
			raise GraphQLError('Oops, we dont know you!!')
		if not user_auth.is_active:
			raise GraphQLError(
				'Oops, you are not allowed to perform this action.')

		user = get_model_object(User, 'email', email)
		user.is_verified = True
		user.set_password(new_password)
		user.save()

		if info.context.user.is_anonymous is False:
			Token.objects.filter(user=info.context.user).delete()

		return ResetPassword(message='Success')


class LogoutUser(graphene.Mutation):
	message = graphene.String()

	def mutate(self, info, **kwargs):
		cookie_token = info.context.COOKIES.get(jwt_settings.JWT_REFRESH_TOKEN_COOKIE_NAME)
		if cookie_token:
			try:
				get_refresh_token(cookie_token, info.context).revoke(info.context)
			except JSONWebTokenError:
				pass  # Already revoked or unknown, nothing to invalidate
		info.context.delete_refresh_token_cookie = True
		if not info.context.user.is_anonymous:
			Token.objects.filter(user=info.context.user).delete()

		return LogoutUser(message='Success')


class SendConfirmationEmail(graphene.Mutation):
	message = graphene.String()
	has_error = graphene.Boolean()

	def mutate(self, info, **kwargs):
		sent = send_test_email()
		return SendConfirmationEmail(message=sent['message'], has_error=sent['has_error'])


class ConfigureUserSettings(graphene.Mutation):
	"""
	This mutation is used to configure user settings like notifications, alert thresholds,
	default currency and appearance (theme mode and accent colors).
	"""
	message = graphene.String()

	class Arguments:
		email_notifications = graphene.Boolean(required=False)
		push_notifications = graphene.Boolean(required=False)
		budget_alerts_enabled = graphene.Boolean(required=False)
		budget_alert_threshold = graphene.Int(required=False)
		default_currency = graphene.String(required=False)
		theme_mode = graphene.String(required=False)
		primary_color = graphene.String(required=False)
		secondary_color = graphene.String(required=False)

	@login_required
	def mutate(self, info, **kwargs):
		user = info.context.user

		if not hasattr(user, 'settings'):
			user.settings = UserSettings(user=user)
		for key, value in kwargs.items():
			if value is not None:
				new_value = value
				if key == 'default_currency':
					new_value = get_model_object(Currency, 'id', value)
				elif key in ('primary_color', 'secondary_color'):
					new_value = value.lower()
				setattr(user.settings, key, new_value)

		# Only the appearance fields are validated here; the rest keep their existing behavior
		try:
			user.settings.clean_fields(exclude=[
				field.name for field in UserSettings._meta.fields if field.name not in APPEARANCE_FIELDS
			])
		except ValidationError as error:
			messages = [f"{field}: {' '.join(errors)}" for field, errors in error.message_dict.items()]
			raise GraphQLError('; '.join(messages))

		user.settings.save()
		return ConfigureUserSettings(message='Settings updated successfully')


class StartTotpSetup(graphene.Mutation):
	"""
	Begin adding an authenticator app. Asks for the password again so a stolen
	session can't attach the attacker's app and lock the owner out.
	The returned secret only works after 'confirmTotpSetup'.
	"""
	setup = graphene.Field(TotpSetupType)

	class Arguments:
		password = graphene.String(required=True)

	@login_required
	def mutate(self, info, password):
		user = info.context.user
		if not user.check_password(password):
			raise GraphQLError('Incorrect password')
		try:
			setup = mfa.start_totp_setup(user)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return StartTotpSetup(setup=TotpSetupType(**setup))


class ConfirmTotpSetup(graphene.Mutation):
	"""
	Turn the authenticator app on with a code from it. 'recoveryCodes' is filled only
	when this is the account's first 2FA method; show the codes once, they aren't stored.
	"""
	message = graphene.String()
	recovery_codes = graphene.List(graphene.NonNull(graphene.String), required=True)
	status = graphene.Field(MfaStatusType)

	class Arguments:
		code = graphene.String(required=True)

	@login_required
	def mutate(self, info, code):
		user = info.context.user
		try:
			recovery_codes = mfa.confirm_totp_setup(user, code)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return ConfirmTotpSetup(
			message='Authenticator app turned on',
			recovery_codes=recovery_codes,
			status=MfaStatusType(**mfa.get_mfa_status(user)),
		)


class StartEmailOtpSetup(graphene.Mutation):
	"""
	Email a code to the account's address. Send it back with the returned
	'setupToken' to 'confirmEmailOtpSetup'. No password needed: only the mailbox
	owner can read the code, so a stolen session can't turn this on by itself.
	"""
	message = graphene.String()
	setup_token = graphene.String()

	@login_required
	def mutate(self, info):
		try:
			setup_token = mfa.start_email_setup(info.context.user)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return StartEmailOtpSetup(message='We sent a code to your email', setup_token=setup_token)


class ResendEmailOtpSetupCode(graphene.Mutation):
	message = graphene.String()

	class Arguments:
		setup_token = graphene.String(required=True)

	@login_required
	def mutate(self, info, setup_token):
		try:
			mfa.resend_email_setup_code(info.context.user, setup_token)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return ResendEmailOtpSetupCode(message='We sent a new code')


class ConfirmEmailOtpSetup(graphene.Mutation):
	"""Turn email codes on. 'recoveryCodes' is filled only for the account's first 2FA method."""
	message = graphene.String()
	recovery_codes = graphene.List(graphene.NonNull(graphene.String), required=True)
	status = graphene.Field(MfaStatusType)

	class Arguments:
		setup_token = graphene.String(required=True)
		code = graphene.String(required=True)

	@login_required
	def mutate(self, info, setup_token, code):
		user = info.context.user
		try:
			recovery_codes = mfa.confirm_email_setup(user, setup_token, code)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return ConfirmEmailOtpSetup(
			message='Email codes turned on',
			recovery_codes=recovery_codes,
			status=MfaStatusType(**mfa.get_mfa_status(user)),
		)


class SetPreferredMfaMethod(graphene.Mutation):
	"""Choose which method the login screen starts with: 'totp' or 'email'."""
	message = graphene.String()
	status = graphene.Field(MfaStatusType)

	class Arguments:
		method = graphene.String(required=True)

	@login_required
	def mutate(self, info, method):
		user = info.context.user
		try:
			mfa.set_preferred_method(user, method)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return SetPreferredMfaMethod(message='Default method updated', status=MfaStatusType(**mfa.get_mfa_status(user)))


class ResendMfaEmailCode(graphene.Mutation):
	"""
	Public: during login, email a code for the pending challenge. Also used when the
	user switches from the authenticator app to email. Limited to one send a minute.
	"""
	message = graphene.String()

	class Arguments:
		mfa_token = graphene.String(required=True)

	def mutate(self, info, mfa_token):
		try:
			mfa.resend_login_email_code(mfa_token)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return ResendMfaEmailCode(message='We sent a code to your email')


class SendMfaActionEmailCode(graphene.Mutation):
	"""
	Email a code to confirm turning 2FA off or replacing recovery codes.
	Without 'actionToken' it starts a new check; with it, it resends the code.
	"""
	message = graphene.String()
	action_token = graphene.String()

	class Arguments:
		action_token = graphene.String()

	@login_required
	def mutate(self, info, action_token=None):
		user = info.context.user
		try:
			if action_token:
				mfa.resend_sensitive_email_code(user, action_token)
			else:
				action_token = mfa.start_sensitive_email_challenge(user)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return SendMfaActionEmailCode(message='We sent a code to your email', action_token=action_token)


class DisableMfa(graphene.Mutation):
	"""
	Turn two-factor authentication off. Needs the password and a current code
	('method' is 'totp', 'email' with 'actionToken', or 'recovery').
	Other sessions are signed out.
	"""
	message = graphene.String()
	status = graphene.Field(MfaStatusType)

	class Arguments:
		password = graphene.String(required=True)
		method = graphene.String(required=True)
		code = graphene.String(required=True)
		action_token = graphene.String()

	@login_required
	def mutate(self, info, password, method, code, action_token=None):
		user = info.context.user
		try:
			mfa.disable_mfa_checked(user, password, method, code, action_token)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		revoke_refresh_tokens(user, keep_token=current_refresh_token(info))
		return DisableMfa(
			message='Two-factor authentication turned off',
			status=MfaStatusType(**mfa.get_mfa_status(user)),
		)


class RegenerateRecoveryCodes(graphene.Mutation):
	"""Replace all recovery codes after checking a current code. Show the new ones once."""
	message = graphene.String()
	recovery_codes = graphene.List(graphene.NonNull(graphene.String), required=True)
	status = graphene.Field(MfaStatusType)

	class Arguments:
		method = graphene.String(required=True)
		code = graphene.String(required=True)
		action_token = graphene.String()

	@login_required
	def mutate(self, info, method, code, action_token=None):
		user = info.context.user
		try:
			recovery_codes = mfa.regenerate_recovery_codes_checked(user, method, code, action_token)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		return RegenerateRecoveryCodes(
			message='New recovery codes created',
			recovery_codes=recovery_codes,
			status=MfaStatusType(**mfa.get_mfa_status(user)),
		)


class RequestPasswordReset(graphene.Mutation):
	"""
	Public: email a password reset code. The response is the same whether or not
	the email has an account. Call again to resend (at most once a minute).
	"""
	message = graphene.String()
	reset_token = graphene.String()

	class Arguments:
		email = graphene.String(required=True)

	def mutate(self, info, email):
		return RequestPasswordReset(
			message='If an account uses this email, we sent a code to it.',
			reset_token=password_reset.request_password_reset(email),
		)


class ResetPasswordWithCode(graphene.Mutation):
	"""
	Public: set a new password with the emailed code. Doesn't sign in, and signs out
	every device, including the one making the request.
	"""
	message = graphene.String()

	class Arguments:
		reset_token = graphene.String(required=True)
		code = graphene.String(required=True)
		new_password = graphene.String(required=True)

	def mutate(self, info, reset_token, code, new_password):
		try:
			password_reset.reset_password_with_code(reset_token, code, new_password)
		except mfa.MfaError as error:
			raise GraphQLError(str(error))
		# This device is signed out too: clear its refresh cookie
		info.context.delete_refresh_token_cookie = True
		return ResetPasswordWithCode(message='Your password was reset. Sign in with your new password.')


class SetInitialPassword(graphene.Mutation):
	"""
	Public: replace an invite's temporary password, with the token from 'loginUser'.
	Doesn't sign in; sign in again with the new password.
	"""
	message = graphene.String()

	class Arguments:
		password_change_token = graphene.String(required=True)
		new_password = graphene.String(required=True)

	def mutate(self, info, password_change_token, new_password):
		try:
			user_management.set_initial_password(password_change_token, new_password)
		except user_management.UserManagementError as error:
			raise GraphQLError(str(error))
		return SetInitialPassword(message='Password set')


class UserInput(graphene.InputObjectType):
	first_name = graphene.String()
	last_name = graphene.String()
	user_name = graphene.String()
	email = graphene.String()
	phone = graphene.String()


class CreateUser(graphene.Mutation):
	"""
	Administrator: create a regular user with their own household and email them an
	invite with a temporary password. If 'inviteSent' is false, resend the invite.
	"""
	message = graphene.String()
	user = graphene.Field(ManagedUserType)
	invite_sent = graphene.Boolean(required=True)

	class Arguments:
		input = UserInput(required=True)

	@login_required
	@superuser_required
	def mutate(self, info, input):
		try:
			user, invite_sent = user_management.create_user(info.context.user, **input)
		except user_management.UserManagementError as error:
			raise GraphQLError(str(error))
		message = 'User created and invited' if invite_sent else \
			"User created, but the invite email couldn't be sent. Try resending it."
		return CreateUser(message=message, user=user, invite_sent=invite_sent)


class UpdateUser(graphene.Mutation):
	"""
	Administrator: change a user's details (only fields sent). A new email signs the
	user out everywhere; a pending invite is re-sent to it ('inviteSent').
	"""
	message = graphene.String()
	user = graphene.Field(ManagedUserType)
	invite_sent = graphene.Boolean()

	class Arguments:
		id = graphene.ID(required=True)
		input = UserInput(required=True)

	@login_required
	@superuser_required
	def mutate(self, info, id, input):
		try:
			user, invite_sent = user_management.update_user(info.context.user, id, **input)
		except user_management.UserManagementError as error:
			raise GraphQLError(str(error))
		return UpdateUser(message='User updated', user=user, invite_sent=invite_sent)


class SetUserActive(graphene.Mutation):
	"""Administrator: disable (signs out everywhere, keeps data) or re-enable a user."""
	message = graphene.String()
	user = graphene.Field(ManagedUserType)

	class Arguments:
		id = graphene.ID(required=True)
		active = graphene.Boolean(required=True)

	@login_required
	@superuser_required
	def mutate(self, info, id, active):
		try:
			user = user_management.set_user_active(info.context.user, id, active)
		except user_management.UserManagementError as error:
			raise GraphQLError(str(error))
		return SetUserActive(message='User enabled' if active else 'User disabled', user=user)


class ResendUserInvite(graphene.Mutation):
	"""Administrator: email a new temporary password to a user who hasn't signed in yet."""
	message = graphene.String()
	user = graphene.Field(ManagedUserType)
	invite_sent = graphene.Boolean(required=True)

	class Arguments:
		id = graphene.ID(required=True)

	@login_required
	@superuser_required
	def mutate(self, info, id):
		try:
			invite_sent = user_management.resend_invite(info.context.user, id)
		except user_management.UserManagementError as error:
			raise GraphQLError(str(error))
		message = 'Invite sent' if invite_sent else "The invite email couldn't be sent. Try again later."
		return ResendUserInvite(message=message, user=user_management.User.objects.get(pk=id), invite_sent=invite_sent)


class UserMutations(graphene.ObjectType):
	login_user = LoginUser.Field()
	verify_mfa_login = VerifyMfaLogin.Field()
	reset_password = ResetPassword.Field()
	update_user_profile = UpdateUserProfile.Field()
	logout_user = LogoutUser.Field()
	refresh_token = RefreshToken.Field()
	send_confirmation_email = SendConfirmationEmail.Field()
	configure_user_settings = ConfigureUserSettings.Field()
	start_totp_setup = StartTotpSetup.Field()
	confirm_totp_setup = ConfirmTotpSetup.Field()
	start_email_otp_setup = StartEmailOtpSetup.Field()
	resend_email_otp_setup_code = ResendEmailOtpSetupCode.Field()
	confirm_email_otp_setup = ConfirmEmailOtpSetup.Field()
	set_preferred_mfa_method = SetPreferredMfaMethod.Field()
	resend_mfa_email_code = ResendMfaEmailCode.Field()
	send_mfa_action_email_code = SendMfaActionEmailCode.Field()
	disable_mfa = DisableMfa.Field()
	regenerate_recovery_codes = RegenerateRecoveryCodes.Field()
	request_password_reset = RequestPasswordReset.Field()
	reset_password_with_code = ResetPasswordWithCode.Field()
	set_initial_password = SetInitialPassword.Field()
	create_user = CreateUser.Field()
	update_user = UpdateUser.Field()
	set_user_active = SetUserActive.Field()
	resend_user_invite = ResendUserInvite.Field()
