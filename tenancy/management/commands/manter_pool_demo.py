from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name

from tenancy.command_guards import (
    ensure_demo_pool_schema,
    is_demo_public_pool_schema,
)
from tenancy.models import DemoTenantSlot
from tenancy.services_demo_pool import expire_due_demo_leases


class Command(BaseCommand):
    help = "Expira, limpa e reseta leases vencidos da pool demo publica."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slot",
            help="Restringe a manutencao a um slot temporario demo2...demo10.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Lista leases vencidos sem alterar schemas ou banco.",
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError("manter_pool_demo deve executar no schema public.")

        slot_code = options.get("slot")
        if slot_code:
            slot_code = ensure_demo_pool_schema(
                slot_code,
                command_name="manter_pool_demo",
                action="manter pool demo",
            )
            if not is_demo_public_pool_schema(slot_code):
                self.stdout.write(
                    self.style.WARNING(
                        f"Slot ignorado: {slot_code} e o tenant demo permanente."
                    )
                )
                return

        dry_run = options["dry_run"]
        if dry_run:
            expired_slot_codes = expire_due_demo_leases(
                slot_code=slot_code,
                dry_run=True,
            )
            self.stdout.write(self.style.WARNING("DRY-RUN: nenhuma alteracao realizada."))
            for expired_slot_code in expired_slot_codes:
                self.stdout.write(f"Expiraria e resetaria slot={expired_slot_code}.")
            self.stdout.write(f"Leases vencidos encontrados: {len(expired_slot_codes)}.")
            return

        expiration_results = expire_due_demo_leases(slot_code=slot_code)
        reset_count = 0
        for result in expiration_results:
            try:
                call_command(
                    "resetar_tenant_demo",
                    slot=result.slot_code,
                    confirm=f"RESETAR {result.slot_code}",
                    verbosity=options.get("verbosity", 1),
                    stdout=self.stdout,
                    stderr=self.stderr,
                )
                reset_count += 1
            except Exception as exc:
                connection.set_schema_to_public()
                DemoTenantSlot.objects.filter(
                    slot_code=result.slot_code,
                    status=DemoTenantSlot.Status.EXPIRADO,
                ).update(
                    status=DemoTenantSlot.Status.BLOQUEADO,
                    notes="Manutencao automatica falhou; revisar antes de liberar.",
                )
                raise CommandError(
                    f"Manutencao falhou; slot {result.slot_code} ficou bloqueado."
                ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Manutencao da pool concluida. "
                f"leases_expirados={len(expiration_results)}; "
                f"slots_resetados={reset_count}."
            )
        )
