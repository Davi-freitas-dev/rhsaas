from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


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
