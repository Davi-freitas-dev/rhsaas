import logging

from django.db import connection, transaction
from django.http import JsonResponse
from django.utils.cache import add_never_cache_headers

from tenancy.services_demo_storage import (
    DEMO_STORAGE_QUOTA_ERROR_CODE,
    DEMO_STORAGE_QUOTA_MESSAGE,
    acquire_demo_storage_quota_transaction_lock,
    demo_storage_quota_applies,
    get_cached_demo_storage_quota_status,
    get_demo_storage_quota_status,
)


logger = logging.getLogger(__name__)

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
EXEMPT_PATH_PREFIXES = (
    "/admin/",
    "/api/auth/",
    "/api/demo/",
    "/login/",
    "/logout/",
    "/password-reset/",
    "/reset/",
)


def demo_storage_quota_exceeded_response(status):
    response = JsonResponse(
        {
            "detail": DEMO_STORAGE_QUOTA_MESSAGE,
            "code": DEMO_STORAGE_QUOTA_ERROR_CODE,
            "storageQuota": status.as_payload(),
        },
        status=403,
        json_dumps_params={"ensure_ascii": False},
    )
    add_never_cache_headers(response)
    return response


class DemoStorageQuotaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        schema_name = getattr(connection, "schema_name", "")
        if not self._must_guard(request, schema_name):
            return self.get_response(request)

        with transaction.atomic():
            acquire_demo_storage_quota_transaction_lock(schema_name)
            cached_status = get_cached_demo_storage_quota_status()
            if cached_status is not None and cached_status.exceeded:
                return demo_storage_quota_exceeded_response(cached_status)

            response = self.get_response(request)
            if connection.needs_rollback:
                return response

            measured_status = get_demo_storage_quota_status(
                schema_name=schema_name,
                use_cache=False,
            )
            if measured_status.applies and measured_status.exceeded:
                transaction.set_rollback(True)
                logger.warning(
                    "demo_storage_quota_exceeded schema=%s used_bytes=%s max_bytes=%s",
                    schema_name,
                    measured_status.used_bytes,
                    measured_status.max_bytes,
                )
                return demo_storage_quota_exceeded_response(measured_status)

            return response

    def _must_guard(self, request, schema_name):
        if request.method.upper() in SAFE_METHODS:
            return False
        if any(request.path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES):
            return False
        return demo_storage_quota_applies(request.user, schema_name)
