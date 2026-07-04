import sys
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent
IS_RUNNING_TESTS = any(
    arg == "test" or Path(arg).name.startswith("pytest") for arg in sys.argv
)

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")


def env_optional_str(name):
    value = env(name, default="")
    return value or None


def env_runtime_str(name, default):
    if IS_RUNNING_TESTS:
        return default

    return env(name, default=default)


# Core
DEBUG = env.bool("DEBUG", default=True)
ENABLE_API_DOCS = env.bool("ENABLE_API_DOCS", default=DEBUG)
DEFAULT_INSECURE_SECRET_KEY = "fedfedcvedc"
SECRET_KEY = env("SECRET_KEY", default=DEFAULT_INSECURE_SECRET_KEY)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
if not DEBUG and (not SECRET_KEY or SECRET_KEY == DEFAULT_INSECURE_SECRET_KEY):
    raise ImproperlyConfigured("Defina SECRET_KEY no .env de producao.")
if not DEBUG and "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS nao deve conter '*' em producao.")

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=(
        ["http://localhost:3000", "http://127.0.0.1:3000"]
        if DEBUG
        else []
    ),
)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=(
        ["http://localhost:3000", "http://127.0.0.1:3000"]
        if DEBUG
        else []
    ),
)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
NEXT_FRONTEND_URL = env("NEXT_FRONTEND_URL", default="http://localhost:3000" if DEBUG else "")
NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED = env.bool(
    "NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED",
    default=False,
)
NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES = env.list(
    "NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES",
    default=[],
)
RESEND_API_KEY = env("RESEND_API_KEY", default="")
CANONICAL_FIRST_SETTLEMENT_ENABLED = env.bool(
    "CANONICAL_FIRST_SETTLEMENT_ENABLED",
    default=False,
)
CANONICAL_FIRST_SETTLEMENT_SOURCES = env.list(
    "CANONICAL_FIRST_SETTLEMENT_SOURCES",
    default=[],
)


# Aplicacoes
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "caixa",
    "simple_history",
    "axes",
]


# API schema/documentacao
DEFAULT_DRF_THROTTLE_ANON_RATE = "100000/day" if IS_RUNNING_TESTS else "120/minute"
DEFAULT_DRF_THROTTLE_USER_RATE = "100000/day" if IS_RUNNING_TESTS else "1200/minute"
DEFAULT_DRF_THROTTLE_AUTH_LOGIN_RATE = (
    "100000/day" if IS_RUNNING_TESTS else "20/minute"
)
DRF_THROTTLE_ANON_RATE = env_runtime_str(
    "DRF_THROTTLE_ANON_RATE",
    DEFAULT_DRF_THROTTLE_ANON_RATE,
)
DRF_THROTTLE_USER_RATE = env_runtime_str(
    "DRF_THROTTLE_USER_RATE",
    DEFAULT_DRF_THROTTLE_USER_RATE,
)
DRF_THROTTLE_AUTH_LOGIN_RATE = env_runtime_str(
    "DRF_THROTTLE_AUTH_LOGIN_RATE",
    DEFAULT_DRF_THROTTLE_AUTH_LOGIN_RATE,
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": DRF_THROTTLE_ANON_RATE,
        "user": DRF_THROTTLE_USER_RATE,
        "auth_login": DRF_THROTTLE_AUTH_LOGIN_RATE,
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Controle de Caixa API",
    "DESCRIPTION": "Schema OpenAPI inicial para validacao incremental.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "caixa.middleware.SecurityHeadersMiddleware",
    "caixa.middleware.ConfiguredCorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "axes.middleware.AxesMiddleware",
]


# URLs e templates
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

if not DEBUG:
    TEMPLATES[0]["APP_DIRS"] = False
    TEMPLATES[0]["OPTIONS"]["loaders"] = [
        (
            "django.template.loaders.cached.Loader",
            [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        ),
    ]

WSGI_APPLICATION = "config.wsgi.application"


# Banco de dados
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int(
    "DB_CONN_MAX_AGE",
    default=60 if not DEBUG else 0,
)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = env.bool(
    "DB_CONN_HEALTH_CHECKS",
    default=not DEBUG,
)


# Cache
CACHES = {
    "default": {
        "BACKEND": env(
            "CACHE_BACKEND",
            default="django.core.cache.backends.locmem.LocMemCache",
        ),
        "LOCATION": env("CACHE_LOCATION", default="controledecaixa-cache"),
    }
}


# Autenticacao e sessao
LOGIN_URL = "caixa:login"
LOGIN_REDIRECT_URL = "caixa:dashboard_financeiro"
LOGOUT_REDIRECT_URL = "caixa:login"

SESSION_ENGINE = env(
    "SESSION_ENGINE",
    default=(
        "django.contrib.sessions.backends.cached_db"
        if not DEBUG
        else "django.contrib.sessions.backends.db"
    ),
)
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=1800)
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool("SESSION_EXPIRE_AT_BROWSER_CLOSE", default=True)
SESSION_SAVE_EVERY_REQUEST = env.bool("SESSION_SAVE_EVERY_REQUEST", default=DEBUG)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_DOMAIN = env_optional_str("SESSION_COOKIE_DOMAIN")

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_DOMAIN = env_optional_str("CSRF_COOKIE_DOMAIN")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]
PASSWORD_RESET_TIMEOUT = env.int("PASSWORD_RESET_TIMEOUT", default=3600)
PASSWORD_RESET_RATE_LIMIT_ATTEMPTS = env.int("PASSWORD_RESET_RATE_LIMIT_ATTEMPTS", default=5)
PASSWORD_RESET_RATE_LIMIT_WINDOW = env.int("PASSWORD_RESET_RATE_LIMIT_WINDOW", default=3600)
PASSWORD_RESET_TRUST_X_FORWARDED_FOR = env.bool("PASSWORD_RESET_TRUST_X_FORWARDED_FOR", default=False)

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS = True

# Seguranca
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = env("SECURE_REFERRER_POLICY", default="same-origin")
SECURE_SSL_REDIRECT = env.bool(
    "SECURE_SSL_REDIRECT",
    default=not (DEBUG or IS_RUNNING_TESTS),
)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=not DEBUG,
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=not DEBUG)

if env.bool("SECURE_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "manifest-src 'self'; "
    "worker-src 'self'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "object-src 'none'; "
    "require-trusted-types-for 'script'; "
    "trusted-types default rhremoto"
)
if env.bool("CSP_UPGRADE_INSECURE_REQUESTS", default=not DEBUG):
    CONTENT_SECURITY_POLICY = f"{CONTENT_SECURITY_POLICY}; upgrade-insecure-requests"
CSP_EXCLUDED_PATH_PREFIXES = env.list("CSP_EXCLUDED_PATH_PREFIXES", default=["/admin/"])
PERMISSIONS_POLICY = env(
    "PERMISSIONS_POLICY",
    default="geolocation=(), microphone=(), camera=()",
)
CROSS_ORIGIN_OPENER_POLICY = env("CROSS_ORIGIN_OPENER_POLICY", default="same-origin")
CROSS_ORIGIN_RESOURCE_POLICY = env("CROSS_ORIGIN_RESOURCE_POLICY", default="same-origin")
X_PERMITTED_CROSS_DOMAIN_POLICIES = env("X_PERMITTED_CROSS_DOMAIN_POLICIES", default="none")


# E-mail
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="smtp.resend.com")
EMAIL_PORT = int(env("EMAIL_PORT", default=587))
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="resend")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Painel Financeiro RH Remoto <nao-responder@seudominio.com>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL


# Internacionalizacao
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Maceio"
USE_I18N = True
USE_TZ = True


# Arquivos estaticos
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_MAX_AGE = env.int("WHITENOISE_MAX_AGE", default=31536000 if not DEBUG else 0)
STATICFILES_STORAGE_BACKEND = (
    "django.contrib.staticfiles.storage.StaticFilesStorage"
    if DEBUG or IS_RUNNING_TESTS
    else "whitenoise.storage.CompressedManifestStaticFilesStorage"
)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": STATICFILES_STORAGE_BACKEND,
    },
}


# Logging
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
        "simple": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose" if not DEBUG else "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "caixa": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
