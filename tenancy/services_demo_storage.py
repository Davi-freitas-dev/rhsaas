import hashlib
from dataclasses import asdict, dataclass

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from caixa.demo_policy import is_demo_public_user
from tenancy.models import DemoTenantSlot


DEMO_STORAGE_QUOTA_CACHE_KEY = "demo-storage-quota:v1"
DEMO_STORAGE_QUOTA_ERROR_CODE = "demo_storage_quota_exceeded"
DEMO_STORAGE_QUOTA_MESSAGE = (
    "A demonstração atingiu o limite de armazenamento temporário. "
    "Aguarde o reset automático ou tente novamente mais tarde."
)


@dataclass(frozen=True)
class DemoStorageQuotaStatus:
    applies: bool
    used_bytes: int
    max_storage_mb: int
    exceeded: bool
    measured_at: str

    @property
    def max_bytes(self):
        return self.max_storage_mb * 1024 * 1024

    def as_payload(self):
        return {
            "applies": self.applies,
            "usedBytes": self.used_bytes,
            "maxBytes": self.max_bytes,
            "maxStorageMb": self.max_storage_mb,
            "exceeded": self.exceeded,
            "measuredAt": self.measured_at,
        }


def current_schema_name():
    return getattr(connection, "schema_name", None) or get_public_schema_name()


def demo_storage_quota_applies(user, schema_name=None):
    schema_name = schema_name or current_schema_name()
    if schema_name not in frozenset(settings.DEMO_PUBLIC_POOL_SLOTS):
        return False
    if not user or user.is_staff or user.is_superuser:
        return False
    return is_demo_public_user(user)


def measure_schema_storage_bytes(schema_name):
    if schema_name not in frozenset(settings.DEMO_PUBLIC_POOL_SLOTS):
        raise ValueError("A medição de quota aceita somente schemas da pool pública.")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COALESCE(SUM(pg_total_relation_size(c.oid)), 0)::bigint
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = %s
               AND c.relkind IN ('r', 'm', 'p')
            """,
            [schema_name],
        )
        return int(cursor.fetchone()[0] or 0)


def _slot_storage_limit_mb(schema_name):
    with schema_context(get_public_schema_name()):
        return (
            DemoTenantSlot.objects.filter(
                slot_code=schema_name,
                tenant__schema_name=schema_name,
            )
            .values_list("max_storage_mb", flat=True)
            .first()
        )


def _status_from_values(*, used_bytes, max_storage_mb, measured_at=None):
    measured_at = measured_at or timezone.now().isoformat()
    max_bytes = int(max_storage_mb) * 1024 * 1024
    return DemoStorageQuotaStatus(
        applies=True,
        used_bytes=int(used_bytes),
        max_storage_mb=int(max_storage_mb),
        exceeded=int(used_bytes) >= max_bytes,
        measured_at=measured_at,
    )


def _status_from_cache(cached):
    if not isinstance(cached, dict):
        return None
    required_keys = {
        "applies",
        "used_bytes",
        "max_storage_mb",
        "exceeded",
        "measured_at",
    }
    if set(cached) != required_keys or cached.get("applies") is not True:
        return None
    try:
        return DemoStorageQuotaStatus(**cached)
    except (TypeError, ValueError):
        return None


def get_cached_demo_storage_quota_status():
    return _status_from_cache(cache.get(DEMO_STORAGE_QUOTA_CACHE_KEY))


def cache_demo_storage_quota_status(status):
    cache.set(
        DEMO_STORAGE_QUOTA_CACHE_KEY,
        asdict(status),
        timeout=settings.DEMO_STORAGE_QUOTA_CACHE_SECONDS,
    )


def clear_demo_storage_quota_cache():
    cache.delete(DEMO_STORAGE_QUOTA_CACHE_KEY)


def get_demo_storage_quota_status(*, schema_name=None, use_cache=True):
    schema_name = schema_name or current_schema_name()
    if schema_name not in frozenset(settings.DEMO_PUBLIC_POOL_SLOTS):
        return DemoStorageQuotaStatus(
            applies=False,
            used_bytes=0,
            max_storage_mb=0,
            exceeded=False,
            measured_at=timezone.now().isoformat(),
        )

    if use_cache:
        cached = get_cached_demo_storage_quota_status()
        if cached is not None:
            return cached

    max_storage_mb = _slot_storage_limit_mb(schema_name)
    if max_storage_mb is None:
        return DemoStorageQuotaStatus(
            applies=False,
            used_bytes=0,
            max_storage_mb=0,
            exceeded=False,
            measured_at=timezone.now().isoformat(),
        )

    status = _status_from_values(
        used_bytes=measure_schema_storage_bytes(schema_name),
        max_storage_mb=max_storage_mb,
    )
    cache_demo_storage_quota_status(status)
    return status


def demo_storage_quota_lock_key(schema_name):
    digest = hashlib.blake2b(
        f"rhsaas:demo-storage-quota:{schema_name}".encode("ascii"),
        digest_size=8,
    ).digest()
    value = int.from_bytes(digest, byteorder="big", signed=False)
    return value - 2**64 if value >= 2**63 else value


def acquire_demo_storage_quota_transaction_lock(schema_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s)",
            [demo_storage_quota_lock_key(schema_name)],
        )
