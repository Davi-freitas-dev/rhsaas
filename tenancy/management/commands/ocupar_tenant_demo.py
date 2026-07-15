import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from tenancy.command_guards import (
    demo_public_pool_schema_names,
    ensure_demo_public_pool_schema,
)
from tenancy.management.commands.provisionar_pool_demo import DEFAULT_DOMAIN_SUFFIX
from tenancy.models import DemoTenantSlot, Domain
from tenancy.services_demo_pool import sync_demo_public_user


DEFAULT_LEASE_DAYS = 3
DEFAULT_USERNAME = "demo"


class Command(BaseCommand):
    help = (
        "Ocupa uma vaga livre do pool demo, cria/ativa usuario no tenant correto "
        "e registra lease no DemoTenantSlot."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slot",
            help="Slot temporario, por exemplo demo2. Se omitido, usa o primeiro livre.",
        )
        parser.add_argument("--nome", required=True, help="Nome do testador.")
        parser.add_argument("--email", required=True, help="Email do testador.")
        parser.add_argument(
            "--telefone",
            default="",
            help="Telefone do testador. Opcional.",
        )
        parser.add_argument(
            "--username",
            default=DEFAULT_USERNAME,
            help=f"Username do usuario demo no tenant. Padrao: {DEFAULT_USERNAME}.",
        )
        parser.add_argument(
            "--password-env",
            help=(
                "Nome da variavel de ambiente que contem a senha inicial. "
                "A senha nao e impressa."
            ),
        )
        parser.add_argument(
            "--duration-days",
            type=int,
            default=DEFAULT_LEASE_DAYS,
            help=f"Duracao do lease em dias. Padrao: {DEFAULT_LEASE_DAYS}.",
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "ocupar_tenant_demo deve executar no schema public da plataforma."
            )

        duration_days = options["duration_days"]
        if duration_days < 1:
            raise CommandError("--duration-days deve ser maior ou igual a 1.")

        tester_name = options["nome"].strip()
        tester_email = options["email"].strip()
        tester_phone = options["telefone"].strip()
        username = options["username"].strip()

        if not tester_name:
            raise CommandError("--nome nao pode ficar vazio.")
        if not tester_email:
            raise CommandError("--email nao pode ficar vazio.")
        if not username:
            raise CommandError("--username nao pode ficar vazio.")

        password = self._password_from_env(options.get("password_env"))

        with transaction.atomic():
            slot = self._select_slot(options.get("slot"))
            schema_name = self._validate_slot(slot)
            user_result = self._create_or_activate_user(
                schema_name,
                username=username,
                email=tester_email,
                name=tester_name,
                password=password,
            )
            now = timezone.now()

            slot.assigned_name = tester_name
            slot.assigned_email = tester_email
            slot.assigned_phone = tester_phone
            slot.visitor_key_hash = ""
            slot.network_key_hash = ""
            slot.exchange_token_digest = None
            slot.exchange_token_expires_at = None
            slot.exchange_token_consumed_at = None
            slot.lease_started_at = now
            slot.lease_expires_at = now + timedelta(days=duration_days)
            slot.last_assigned_at = now
            slot.status = DemoTenantSlot.Status.OCUPADO
            slot.full_clean()
            slot.save(
                update_fields=[
                    "assigned_name",
                    "assigned_email",
                    "assigned_phone",
                    "visitor_key_hash",
                    "network_key_hash",
                    "exchange_token_digest",
                    "exchange_token_expires_at",
                    "exchange_token_consumed_at",
                    "lease_started_at",
                    "lease_expires_at",
                    "last_assigned_at",
                    "status",
                    "updated_at",
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Tenant demo ocupado. "
                f"slot={slot.slot_code}; "
                f"usuario={user_result}; "
                f"expira_em={slot.lease_expires_at.isoformat()}."
            )
        )

    def _password_from_env(self, password_env):
        if not password_env:
            return None

        password = os.environ.get(password_env)
        if not password:
            raise CommandError(
                f"A variavel de ambiente {password_env!r} nao esta definida ou esta vazia."
            )
        return password

    def _select_slot(self, requested_slot):
        if requested_slot:
            slot_code = ensure_demo_public_pool_schema(
                requested_slot,
                command_name="ocupar_tenant_demo",
                action="ocupar tenant demo",
            )
            slot = (
                DemoTenantSlot.objects.select_for_update()
                .select_related("tenant")
                .filter(slot_code=slot_code)
                .first()
            )
            if slot is None:
                raise CommandError(f"Slot demo {slot_code} nao existe ou nao foi provisionado.")
            return slot

        slot = (
            DemoTenantSlot.objects.select_for_update()
            .select_related("tenant")
            .filter(
                slot_code__in=demo_public_pool_schema_names(),
                status=DemoTenantSlot.Status.LIVRE,
            )
            .order_by("slot_code")
            .first()
        )
        if slot is None:
            raise CommandError("Nao ha vaga livre no pool demo.")
        ensure_demo_public_pool_schema(
            slot.slot_code,
            command_name="ocupar_tenant_demo",
            action="ocupar tenant demo",
        )
        return slot

    def _validate_slot(self, slot):
        schema_name = ensure_demo_public_pool_schema(
            slot.tenant.schema_name,
            command_name="ocupar_tenant_demo",
            action="ocupar tenant demo",
        )

        if slot.slot_code != schema_name:
            raise CommandError(
                f"Slot {slot.slot_code} aponta para tenant {schema_name}. "
                "O slot deve corresponder ao schema do tenant."
            )

        if slot.status != DemoTenantSlot.Status.LIVRE:
            raise CommandError(f"Slot demo {slot.slot_code} nao esta livre.")

        domain_name = f"{slot.slot_code}.{DEFAULT_DOMAIN_SUFFIX}"
        domain = Domain.objects.select_related("tenant").filter(domain=domain_name).first()
        if domain is None:
            raise CommandError(f"Domain tecnico {domain_name} nao existe.")
        if domain.tenant_id != slot.tenant_id:
            raise CommandError(
                f"Domain tecnico {domain_name} pertence a outro tenant."
            )

        return schema_name

    def _create_or_activate_user(self, schema_name, *, username, email, name, password):
        with schema_context(schema_name):
            User = get_user_model()
            user = User.objects.filter(username=username).first()
            if user is None:
                if password is None:
                    raise CommandError(
                        "Para criar usuario demo novo, informe --password-env com "
                        "uma variavel de ambiente contendo a senha inicial."
                    )
                result = "criado"
            else:
                result = "existente" if user.is_active else "ativado"

        sync_demo_public_user(
            schema_name,
            username=username,
            password=password,
            display_name=name,
            email=email,
        )
        return result
