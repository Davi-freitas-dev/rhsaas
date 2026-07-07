from django.core.exceptions import ValidationError
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


DEMO_SLOT_CODES = tuple(f"demo{index}" for index in range(1, 11))
DEMO_SLOT_STATUSES = ("livre", "ocupado", "expirado", "bloqueado")


class Tenant(TenantMixin):
    name = models.CharField(max_length=150, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass


class DemoTenantSlot(models.Model):
    class Status(models.TextChoices):
        LIVRE = "livre", "Livre"
        OCUPADO = "ocupado", "Ocupado"
        EXPIRADO = "expirado", "Expirado"
        BLOQUEADO = "bloqueado", "Bloqueado"

    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name="demo_slot",
    )
    slot_code = models.CharField(max_length=10, unique=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.LIVRE,
    )
    assigned_name = models.CharField(max_length=150, blank=True)
    assigned_email = models.EmailField(blank=True)
    assigned_phone = models.CharField(max_length=30, blank=True)
    lease_started_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    last_reset_at = models.DateTimeField(null=True, blank=True)
    last_assigned_at = models.DateTimeField(null=True, blank=True)
    max_storage_mb = models.PositiveIntegerField(default=50)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slot_code"]
        indexes = [
            models.Index(
                fields=["status", "lease_expires_at"],
                name="demo_slot_status_exp_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(slot_code__in=DEMO_SLOT_CODES),
                name="demo_slot_code_allowed",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=DEMO_SLOT_STATUSES),
                name="demo_slot_status_allowed",
            ),
            models.CheckConstraint(
                condition=models.Q(max_storage_mb__gte=1)
                & models.Q(max_storage_mb__lte=50),
                name="demo_slot_storage_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(lease_started_at__isnull=True)
                    | models.Q(lease_expires_at__isnull=True)
                    | models.Q(lease_expires_at__gt=models.F("lease_started_at"))
                ),
                name="demo_slot_lease_order",
            ),
        ]

    def clean(self):
        super().clean()
        if self.tenant_id and self.tenant.schema_name != self.slot_code:
            raise ValidationError(
                {"slot_code": "O slot demo deve corresponder ao schema do tenant."}
            )

    def __str__(self):
        return f"{self.slot_code} ({self.get_status_display()})"
