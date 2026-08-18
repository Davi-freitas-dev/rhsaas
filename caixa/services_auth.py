import math
import secrets
import time

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import signing
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.db import connection
from django.utils.crypto import constant_time_compare, salted_hmac
from django_tenants.utils import get_public_schema_name, schema_context

from config.client_ip import get_axes_client_ip
from tenancy.models import Domain


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


def load_password_reset_tenant_context(value):
    if not isinstance(value, str) or not value:
        return ""

    try:
        payload = signing.loads(
            value,
            salt=PASSWORD_RESET_CONTEXT_SALT,
            max_age=settings.PASSWORD_RESET_TIMEOUT,
        )
    except signing.BadSignature:
        return ""

    schema_name = payload.get("schema") if isinstance(payload, dict) else ""
    return str(schema_name) if isinstance(schema_name, str) else ""


def password_reset_tenant_context_is_valid(value):
    schema_name = load_password_reset_tenant_context(value)
    return bool(schema_name) and constant_time_compare(
        schema_name,
        connection.schema_name,
    )


def resolve_password_reset_target_schema(value):
    """Resolve a signed reset context only from an authorized gateway or its tenant."""

    target_schema = load_password_reset_tenant_context(value)
    public_schema = get_public_schema_name()
    current_schema = connection.schema_name
    gateway_schema = str(
        getattr(settings, "PASSWORD_RESET_GATEWAY_SCHEMA", "") or ""
    ).strip()

    if not target_schema or target_schema == public_schema:
        return ""

    is_target_host = constant_time_compare(target_schema, current_schema)
    is_gateway = current_schema in {public_schema, gateway_schema}
    if not is_target_host and not is_gateway:
        return ""

    with schema_context(public_schema):
        is_registered = Domain.objects.filter(
            tenant__schema_name=target_schema,
            is_primary=True,
        ).exists()

    return target_schema if is_registered else ""


def password_reset_rate_limit_exceeded(request, *, email=""):
    attempts = settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS
    window = settings.PASSWORD_RESET_RATE_LIMIT_WINDOW

    if attempts <= 0 or window <= 0:
        return False

    client_ip = get_axes_client_ip(request) or "unknown"
    identifiers = [f"ip:{client_ip}"]
    email = str(email or "").strip().lower()
    if email:
        identifiers.append(f"email:{email}")

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


def _bounded_timing_seconds(setting_name, maximum_setting_name):
    value = float(getattr(settings, setting_name, 0))
    maximum = float(getattr(settings, maximum_setting_name))
    if not math.isfinite(value) or not math.isfinite(maximum) or maximum < 0:
        return 0
    return min(max(value, 0), maximum)


def equalize_password_reset_response_time(started_at):
    """Apply a bounded response floor after account-dependent reset work."""

    minimum_seconds = _bounded_timing_seconds(
        "PASSWORD_RESET_MIN_RESPONSE_SECONDS",
        "PASSWORD_RESET_MIN_RESPONSE_MAX_SECONDS",
    )
    jitter_seconds = _bounded_timing_seconds(
        "PASSWORD_RESET_RESPONSE_JITTER_SECONDS",
        "PASSWORD_RESET_JITTER_MAX_SECONDS",
    )
    random_jitter = (
        secrets.randbelow(1_000_001) / 1_000_000 * jitter_seconds
        if jitter_seconds
        else 0
    )
    remaining = minimum_seconds + random_jitter - (time.monotonic() - started_at)

    if remaining > 0:
        time.sleep(remaining)
