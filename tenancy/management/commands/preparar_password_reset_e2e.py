from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from tenancy.models import Domain, Tenant


TENANT_FIXTURES = (
    ("tenant_e2e_a", "Tenant E2E A", "tenant-a.localhost"),
    ("tenant_e2e_b", "Tenant E2E B", "tenant-b.localhost"),
    ("auth_gateway", "Auth Gateway E2E", "gateway.localhost"),
)
SHARED_EMAIL = "password-reset-e2e@example.com"
SHARED_USERNAME = "password-reset-e2e"
INITIAL_PASSWORD = "Senha-inicial-E2E-2026"
SHARED_USER_ID = 900001
RATE_LIMIT_EMAIL = "password-reset-rate-limit-e2e@example.com"
RATE_LIMIT_USERNAME = "password-reset-rate-limit-e2e"


class Command(BaseCommand):
    help = "Prepara tenants descartaveis para o E2E real de recuperacao de senha."

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.PASSWORD_RESET_E2E_ENABLED:
            raise CommandError(
                "O fixture exige DEBUG=True e PASSWORD_RESET_E2E_ENABLED=True."
            )
        if settings.PASSWORD_RESET_GATEWAY_SCHEMA != "auth_gateway":
            raise CommandError(
                "Configure PASSWORD_RESET_GATEWAY_SCHEMA=auth_gateway para o E2E."
            )

        tenants = {}
        for schema_name, name, domain_name in TENANT_FIXTURES:
            tenant, _created = Tenant.objects.get_or_create(
                schema_name=schema_name,
                defaults={"name": name},
            )
            Domain.objects.update_or_create(
                domain=domain_name,
                defaults={"tenant": tenant, "is_primary": True},
            )
            tenants[schema_name] = tenant

        user_ids = []
        for schema_name in ("tenant_e2e_a", "tenant_e2e_b"):
            with schema_context(schema_name):
                user_model = get_user_model()
                user, _created = user_model.objects.update_or_create(
                    pk=SHARED_USER_ID,
                    defaults={
                        "username": SHARED_USERNAME,
                        "email": SHARED_EMAIL,
                    },
                )
                user.email = SHARED_EMAIL
                user.is_active = True
                user.set_password(INITIAL_PASSWORD)
                user.save(update_fields=["email", "is_active", "password"])
                user_ids.append(user.pk)

        with schema_context("tenant_e2e_a"):
            user_model = get_user_model()
            rate_limit_user, _created = user_model.objects.update_or_create(
                username=RATE_LIMIT_USERNAME,
                defaults={"email": RATE_LIMIT_EMAIL},
            )
            rate_limit_user.email = RATE_LIMIT_EMAIL
            rate_limit_user.is_active = True
            rate_limit_user.set_password(INITIAL_PASSWORD)
            rate_limit_user.save(update_fields=["email", "is_active", "password"])

        if len(set(user_ids)) != 1:
            raise CommandError(
                "Os usuarios E2E nao receberam a mesma PK; use um banco descartavel limpo."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Password reset E2E preparado: tenants A/B, gateway e usuarios homologos."
            )
        )
