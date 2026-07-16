import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    schema_exists,
)

from tenancy.command_guards import ensure_demo_permanent_tenant_schema
from tenancy.management.commands.provisionar_pool_demo import DEFAULT_DOMAIN_SUFFIX
from tenancy.models import DemoTenantSlot, Domain, Tenant
from tenancy.services_demo_pool import (
    DEMO_PUBLIC_USERNAME,
    seed_demo_tenant,
    sync_demo_permanent_user,
)
from caixa.demo_seed import inspect_demo_seed_readiness, validate_demo_seed_readiness


class Command(BaseCommand):
    help = (
        "Garante seed e usuario minimo no tenant demo permanente sem criar lease "
        "ou DemoTenantSlot."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=DEMO_PUBLIC_USERNAME,
            help=f"Usuario permanente. Padrao: {DEMO_PUBLIC_USERNAME}.",
        )
        parser.add_argument(
            "--password-env",
            help=(
                "Variavel de ambiente com a senha. Pode ser omitida somente se "
                "o usuario existente ja possuir senha utilizavel."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida a estrutura e o usuario sem alterar dados.",
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "preparar_demo_permanente deve executar no schema public."
            )

        schema_name = ensure_demo_permanent_tenant_schema(
            settings.DEMO_PERMANENT_TENANT_SCHEMA,
        )
        username = options["username"].strip()
        if not username:
            raise CommandError("--username nao pode ficar vazio.")

        tenant = Tenant.objects.filter(schema_name=schema_name).first()
        if tenant is None or not schema_exists(schema_name):
            raise CommandError(
                f"Tenant permanente {schema_name} ainda nao foi provisionado."
            )
        expected_domain = f"{schema_name}.{DEFAULT_DOMAIN_SUFFIX}"
        domain = Domain.objects.filter(domain=expected_domain, tenant=tenant).first()
        if domain is None:
            raise CommandError(
                f"Domain tecnico do tenant permanente nao foi provisionado: "
                f"{expected_domain}."
            )
        if DemoTenantSlot.objects.filter(slot_code=schema_name).exists():
            raise CommandError(
                f"O tenant permanente {schema_name} ainda possui DemoTenantSlot; "
                "aplique a migration de separacao da pool."
            )

        with schema_context(schema_name):
            user = get_user_model().objects.filter(username=username).first()
            user_ready = bool(user and user.is_active and user.has_usable_password())

        if options["dry_run"]:
            readiness = inspect_demo_seed_readiness(schema_name=schema_name)
            self.stdout.write(
                self.style.WARNING("DRY-RUN: nenhum dado sera alterado.")
            )
            self.stdout.write(
                f"Tenant permanente validado: schema={schema_name}; "
                f"usuario_pronto={'sim' if user_ready else 'nao'}; "
                f"seed_pronto={'sim' if readiness.ready else 'nao'}."
            )
            return

        password = self._password_from_env(options.get("password_env"))
        seed_demo_tenant(schema_name)
        validate_demo_seed_readiness(schema_name=schema_name)
        try:
            sync_demo_permanent_user(
                schema_name,
                username=username,
                password=password,
            )
        except Exception as exc:
            raise CommandError(
                "Nao foi possivel preparar o usuario da demo permanente."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo permanente preparada. schema={schema_name}; "
                "seed=idempotente; usuario=minimo."
            )
        )

    @staticmethod
    def _password_from_env(password_env):
        if not password_env:
            return None
        password = os.environ.get(password_env)
        if not password:
            raise CommandError(
                f"A variavel de ambiente {password_env!r} nao esta definida ou vazia."
            )
        return password
