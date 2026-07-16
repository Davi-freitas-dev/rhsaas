import math

from django.http import JsonResponse
from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

from config.client_ip import get_axes_client_ip
from tenancy.demo_visitor import (
    mark_demo_lease_resume_only,
    read_demo_visitor_identifier,
)


def current_schema_name():
    return getattr(connection, "schema_name", None) or get_public_schema_name()


class TenantThrottleMixin:
    def get_tenant_ident(self, request, ident):
        request_tenant = getattr(request, "tenant", None)
        schema_name = (
            getattr(request_tenant, "schema_name", None) or current_schema_name()
        )
        return f"{schema_name}:{ident}"


class TenantAnonRateThrottle(TenantThrottleMixin, AnonRateThrottle):
    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return None

        ident = self.get_tenant_ident(request, f"ip:{self.get_ident(request)}")
        return self.cache_format % {"scope": self.scope, "ident": ident}


class TenantUserRateThrottle(TenantThrottleMixin, UserRateThrottle):
    def get_cache_key(self, request, view):
        ip_address = self.get_ident(request)
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            ident = f"user:{user.pk}:ip:{ip_address}"
        else:
            ident = f"anon:ip:{ip_address}"

        ident = self.get_tenant_ident(request, ident)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AuthLoginRateThrottle(TenantUserRateThrottle):
    scope = "auth_login"


class TenantScopedOperationRateThrottle(TenantThrottleMixin, SimpleRateThrottle):
    def get_cache_key(self, request, view):
        ip_address = self.get_ident(request)
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            ident = f"user:{user.pk}:ip:{ip_address}"
        else:
            ident = f"anon:ip:{ip_address}"

        ident = self.get_tenant_ident(request, ident)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class BackupCreateRateThrottle(TenantScopedOperationRateThrottle):
    scope = "backup_create"


class BackupDownloadRateThrottle(TenantScopedOperationRateThrottle):
    scope = "backup_download"


class ExportCsvRateThrottle(TenantScopedOperationRateThrottle):
    scope = "export_csv"


class DemoTrustedClientIpThrottleMixin:
    def get_ident(self, request):
        django_request = getattr(request, "_request", request)
        return get_axes_client_ip(django_request) or super().get_ident(request)


class DemoLeaseResumeRateThrottle(SimpleRateThrottle):
    scope = "demo_lease_resume"

    def get_cache_key(self, request, view):
        django_request = getattr(request, "_request", request)
        visitor_identifier = read_demo_visitor_identifier(django_request)
        if not visitor_identifier:
            return None

        from tenancy.services_demo_pool import hash_demo_identifier

        visitor_hash = hash_demo_identifier("visitor", visitor_identifier)
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"visitor:{visitor_hash}",
        }


class DemoStatusRateThrottle(
    DemoTrustedClientIpThrottleMixin,
    TenantScopedOperationRateThrottle,
):
    scope = "demo_status"


class DemoLeaseRateThrottle(
    DemoTrustedClientIpThrottleMixin,
    TenantScopedOperationRateThrottle,
):
    scope = "demo_lease"

    def allow_request(self, request, view):
        self._resume_throttle = None
        django_request = getattr(request, "_request", request)
        visitor_identifier = read_demo_visitor_identifier(django_request)

        if visitor_identifier:
            from tenancy.services_demo_pool import has_active_demo_lease

            if has_active_demo_lease(visitor_identifier=visitor_identifier):
                resume_throttle = DemoLeaseResumeRateThrottle()
                self._resume_throttle = resume_throttle
                allowed = resume_throttle.allow_request(request, view)
                if allowed:
                    mark_demo_lease_resume_only(django_request)
                return allowed

        return super().allow_request(request, view)

    def wait(self):
        if self._resume_throttle is not None:
            return self._resume_throttle.wait()
        return super().wait()


class DemoExchangeRateThrottle(
    DemoTrustedClientIpThrottleMixin,
    TenantScopedOperationRateThrottle,
):
    scope = "demo_exchange"


def django_rate_limited_response(wait=None):
    response = JsonResponse({"detail": "Request was throttled."}, status=429)
    if wait is not None:
        response["Retry-After"] = str(max(1, math.ceil(wait)))
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def check_django_rate_limit(request, throttle_class):
    throttle = throttle_class()
    if throttle.allow_request(request, None):
        return None

    return django_rate_limited_response(throttle.wait())
