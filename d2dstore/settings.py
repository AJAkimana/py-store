"""
Django settings for d2dstore project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

from dotenv import load_dotenv

from app_utils.helpers import backup_filename

load_dotenv(os.path.abspath('app.env'))
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.getenv('DEBUG', '') == 'true')

ALLOWED_HOSTS = ['.akimanaja.com', '165.227.5.239', 'localhost']

# Application definition

INSTALLED_APPS = [
	'django_crontab',  # For automatic job
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'rest_framework.authtoken',
	'corsheaders',
	'graphene_django',
	'api',
	'apps.users',
	'apps.stores',
	'apps.houses',
	'apps.properties',
	'dbbackup',  # django-dbbackup
]

MIDDLEWARE = [
	'corsheaders.middleware.CorsMiddleware',
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware'
]

ROOT_URLCONF = 'd2dstore.urls'

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [os.path.join(BASE_DIR, 'frontend')],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'd2dstore.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
	'default': {
		# 'ENGINE': 'django.db.backends.mysql',
		# 'OPTIONS': {
		#     'read_default_file': os.getenv('MYSQL_CONFIG'),
		# },

		'ENGINE': 'django.db.backends.postgresql_psycopg2',
		'NAME': os.getenv("DB_NAME", ''),
		'USER': os.getenv("DB_USER", ''),
		'PASSWORD': os.getenv("DB_PASSWORD", ''),
		'HOST': os.getenv("DB_HOST", '127.0.0.1'),
		'PORT': os.getenv("DB_PORT", '5432'),
	}
}

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]

GRAPHENE = {
	'SCHEMA': 'd2dstore.schema.schema',
	"MIDDLEWARE": [
		"graphql_jwt.middleware.JSONWebTokenMiddleware"
	],
}
REST_FRAMEWORK = {
	'DEFAULT_RENDERER_CLASSES': [
		'rest_framework.renderers.JSONRenderer',
		'rest_framework.renderers.BrowsableAPIRenderer',
	],
	'DEFAULT_AUTHENTICATION_CLASSES': [
		'rest_framework.authentication.BasicAuthentication',
		# 'rest_framework.authentication.SessionAuthentication',
	],
	'DEFAULT_PARSER_CLASSES': (
		'rest_framework.parsers.JSONParser',
	)
}
AUTHENTICATION_BACKENDS = [
	'graphql_jwt.backends.JSONWebTokenBackend',
	'django.contrib.auth.backends.ModelBackend',
]
AUTH_USER_MODEL = 'users.User'
CORS_ORIGIN_WHITELIST = (
	'http://localhost:8000',
	'http://localhost:3000'
)
# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Kigali'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Set up to The URL to api
# USE_X_FORWARDED_HOST = True
# FORCE_SCRIPT_NAME = '/api'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_ROOT = os.getenv('ROOT_STATIC_DI', '')
STATIC_URL = '/assets/'
STATICFILES_DIRS = [
	os.getenv('ROOT_STATIC_DI', '')
]

# Backup database
# DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE = 'storages.backends.dropbox.DropBoxStorage'
DBBACKUP_STORAGE_OPTIONS = {
	'oauth2_access_token': os.getenv('DROPBOX_TOKEN', ''),
	# 'location': os.getenv('DB_BACKUP_ZONE', None)
}
DBBACKUP_FILENAME_TEMPLATE = backup_filename
CRONJOBS = [
	('0 0 * * 0', 'api.cron.backup_db')
]

SECURE_HSTS_SECONDS = os.getenv('SH_SECONDS', 3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = bool(os.getenv('SHI_SUB_DOM', '') == 'true')
SECURE_CONTENT_TYPE_NOSNIFF = bool(os.getenv('SCT_NOSNIFF', '') == 'true')
SECURE_BROWSER_XSS_FILTER = bool(os.getenv('SBX_FILTER', '') == 'true')
SECURE_SSL_REDIRECT = bool(os.getenv('S_SSL_REDIRECT', '') == 'true')
SESSION_COOKIE_SECURE = bool(os.getenv('S_C_SECURE', '') == 'true')
CSRF_COOKIE_SECURE = bool(os.getenv('CSRF_C_SECURE', '') == 'true')
X_FRAME_OPTIONS = os.getenv('X_FRAME', 'DENY')
SECURE_HSTS_PRELOAD = bool(os.getenv('SH_PRELOAD', '') == 'true')
