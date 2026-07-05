import re

from django.core.cache.backends.base import default_key_func
from django.db import connection
from django_tenants.utils import get_public_schema_name


_UNSAFE_CACHE_KEY_PART = re.compile(r"[^A-Za-z0-9_.-]+")


def current_schema_name():
    return getattr(connection, "schema_name", None) or get_public_schema_name()


def _safe_cache_key_part(value):
    return _UNSAFE_CACHE_KEY_PART.sub("_", str(value or get_public_schema_name()))


def tenant_cache_key(key, key_prefix, version):
    schema_name = _safe_cache_key_part(current_schema_name())
    tenant_prefix = f"{key_prefix}:{schema_name}" if key_prefix else schema_name
    return default_key_func(key, tenant_prefix, version)
