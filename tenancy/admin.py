from django.contrib import admin
from django_tenants.admin import TenantAdminMixin

from .models import DemoTenantSlot, Domain, Tenant


@admin.register(Tenant)
class TenantAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = ("name", "schema_name", "created_at")
    search_fields = ("name", "schema_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain", "tenant__name", "tenant__schema_name")


@admin.register(DemoTenantSlot)
class DemoTenantSlotAdmin(admin.ModelAdmin):
    list_display = (
        "slot_code",
        "tenant",
        "status",
        "lease_started_at",
        "lease_expires_at",
        "max_storage_mb",
    )
    list_filter = ("status",)
    search_fields = (
        "slot_code",
        "tenant__name",
        "tenant__schema_name",
        "assigned_name",
        "assigned_email",
    )
    readonly_fields = ("created_at", "updated_at")
