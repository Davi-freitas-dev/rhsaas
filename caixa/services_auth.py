from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.db import connection
from django.utils.crypto import constant_time_compare, salted_hmac


PASSWORD_RESET_CONTEXT_SALT = "rhsaas.password-reset.tenant-context"


class TenantPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        base_value = super()._make_hash_value(user, timestamp)
        return f"{base_value}:{connection.schema_name}"


tenant_password_reset_token_generator = TenantPasswordResetTokenGenerator()


def create_password_reset_tenant_context():
    return signing.dumps(
        {"schema": connection.schema_name},
        salt=PASSWORD_RESET_CONTEXT_SALT,
        compress=True,
    )


def password_reset_tenant_context_is_valid(value):
    if not isinstance(value, str) or not value:
        return False

    try:
        payload = signing.loads(
            value,
            salt=PASSWORD_RESET_CONTEXT_SALT,
            max_age=settings.PASSWORD_RESET_TIMEOUT,
        )
    except signing.BadSignature:
        return False

    schema_name = payload.get("schema") if isinstance(payload, dict) else ""
    return constant_time_compare(str(schema_name), connection.schema_name)


def password_reset_rate_limit_exceeded(request, *, email=""):
    attempts = settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS
    window = settings.PASSWORD_RESET_RATE_LIMIT_WINDOW

    if attempts <= 0 or window <= 0:
        return False

    identifiers = [_client_ip(request)]
    email = str(email or "").strip().lower()
    if email:
        identifiers.append(email)

    return any(_increment_attempts(identifier, attempts, window) for identifier in identifiers)


def _increment_attempts(identifier, attempts, window):
    cache_key = _cache_key(identifier)
    added = cache.add(cache_key, 1, window)
    if added:
        return False

    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window)
        return False
    except InvalidCacheBackendError:
        return False

    return count > attempts


def _cache_key(identifier):
    digest = salted_hmac("password-reset-rate-limit", identifier).hexdigest()
    return f"password-reset:{digest}"


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if settings.PASSWORD_RESET_TRUST_X_FORWARDED_FOR and forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "")
