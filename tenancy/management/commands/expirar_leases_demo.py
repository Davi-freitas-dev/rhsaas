from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from tenancy.command_guards import ensure_demo_pool_schema
from tenancy.management.commands.ocupar_tenant_demo import DEFAULT_USERNAME
from tenancy.management.commands.provisionar_pool_demo import DEFAULT_DOMAIN_SUFFIX
from tenancy.models import DemoTenantSlot, Domain
from tenancy.services_demo_pool import cleanup_demo_tenant_access


class Command(BaseCommand):
    help = (
        "Expira leases vencidos do pool demo, desativando usuario demo no "
        "schema correto sem resetar ou apagar dados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slot",
            help="Slot especifico do pool demo, por exemplo demo1. Se omitido, avalia todos.",
        )
        parser.add_argument(
            "--username",
            default=DEFAULT_USERNAME,
            help=f"Username do usuario demo a desativar. Padrao: {DEFAULT_USERNAME}.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quais leases seriam expirados sem alterar o banco.",
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "expirar_leases_demo deve executar no schema public da plataforma."
            )

        username = options["username"].strip()
        if not username:
            raise CommandError("--username nao pode ficar vazio.")

        now = timezone.now()
        slots = self._select_slots(options.get("slot"), now)
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: nenhum dado sera alterado."))
            for slot in slots:
                self._validate_slot(slot)
                self.stdout.write(f"Expiraria slot={slot.slot_code}; usuario={username}.")
            self.stdout.write(f"Leases vencidos encontrados: {len(slots)}.")
            return

        expired_count = 0
        deactivated_count = 0
        missing_user_count = 0
        sessions_removed = 0
        axes_rows_removed = 0
        cache_keys_removed = 0

        with transaction.atomic():
            locked_slots = self._select_slots(options.get("slot"), now, for_update=True)
            for slot in locked_slots:
                schema_name = self._validate_slot(slot)
                cleanup = cleanup_demo_tenant_access(
                    schema_name,
                    username=username,
                )

                slot.status = DemoTenantSlot.Status.EXPIRADO
                slot.exchange_token_digest = None
                slot.exchange_token_expires_at = None
                slot.exchange_token_consumed_at = None
                slot.full_clean()
                slot.save(
                    update_fields=[
                        "status",
                        "exchange_token_digest",
                        "exchange_token_expires_at",
                        "exchange_token_consumed_at",
                        "updated_at",
                    ]
                )

                expired_count += 1
                if cleanup["user_deactivated"]:
                    deactivated_count += 1
                else:
                    missing_user_count += 1
                sessions_removed += cleanup["sessions_removed"]
                axes_rows_removed += cleanup["axes_rows_removed"]
                cache_keys_removed += cleanup["cache_keys_removed"]

        self.stdout.write(
            self.style.SUCCESS(
                "Leases demo expirados. "
                f"slots={expired_count}; "
                f"usuarios_desativados={deactivated_count}; "
                f"usuarios_ausentes_ou_inativos={missing_user_count}; "
                f"sessoes_removidas={sessions_removed}; "
                f"axes_removidos={axes_rows_removed}; "
                f"cache_removido={cache_keys_removed}."
            )
        )

    def _select_slots(self, requested_slot, now, *, for_update=False):
        queryset = DemoTenantSlot.objects.select_related("tenant").filter(
            status=DemoTenantSlot.Status.OCUPADO,
            lease_expires_at__lt=now,
        )
        if for_update:
            queryset = queryset.select_for_update()

        if requested_slot:
            slot_code = ensure_demo_pool_schema(
                requested_slot,
                command_name="expirar_leases_demo",
                action="expirar lease demo",
            )
            return list(queryset.filter(slot_code=slot_code).order_by("slot_code"))

        return list(queryset.order_by("slot_code"))

    def _validate_slot(self, slot):
        schema_name = ensure_demo_pool_schema(
            slot.tenant.schema_name,
            command_name="expirar_leases_demo",
            action="expirar lease demo",
        )

        if slot.slot_code != schema_name:
            raise CommandError(
                f"Slot {slot.slot_code} aponta para tenant {schema_name}. "
                "O slot deve corresponder ao schema do tenant."
            )

        domain_name = f"{slot.slot_code}.{DEFAULT_DOMAIN_SUFFIX}"
        domain = Domain.objects.select_related("tenant").filter(domain=domain_name).first()
        if domain is None:
            raise CommandError(f"Domain tecnico {domain_name} nao existe.")
        if domain.tenant_id != slot.tenant_id:
            raise CommandError(
                f"Domain tecnico {domain_name} pertence a outro tenant."
            )

        return schema_name
