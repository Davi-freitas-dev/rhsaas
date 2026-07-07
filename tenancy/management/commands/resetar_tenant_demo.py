import hashlib
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    schema_exists,
)

from caixa.permissions import PERMISSION_PROFILES, sincronizar_grupos_permissoes
from caixa.tenant_files import artifacts_root_for_schema
from tenancy.command_guards import (
    ensure_demo_pool_reset_confirmation,
    ensure_demo_pool_schema,
)
from tenancy.management.commands.provisionar_pool_demo import DEFAULT_DOMAIN_SUFFIX
from tenancy.models import DemoTenantSlot, Domain


ALLOWED_RESET_STATUSES = {
    DemoTenantSlot.Status.EXPIRADO,
    DemoTenantSlot.Status.BLOQUEADO,
}
REQUIRED_TENANT_TABLES = (
    "django_migrations",
    "auth_user",
    "auth_group",
    "django_session",
)
DEMO_RESET_LOCK_PREFIX = "rhsaas:demo-reset:"


@dataclass(frozen=True)
class ResetPlan:
    slot_id: int
    slot_code: str
    tenant_id: int
    domain_name: str
    status: str


class Command(BaseCommand):
    help = (
        "Reseta um tenant do pool demo, recriando somente o schema validado "
        "e liberando o DemoTenantSlot apos sucesso completo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slot",
            required=True,
            help="Slot do pool demo a resetar, por exemplo demo1.",
        )
        parser.add_argument(
            "--confirm",
            required=True,
            help='Confirmacao forte no formato: "RESETAR demoN".',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria resetado sem alterar banco ou schema.",
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "resetar_tenant_demo deve executar no schema public da plataforma."
            )

        slot_code = ensure_demo_pool_reset_confirmation(
            options["slot"],
            options["confirm"],
            command_name="resetar_tenant_demo",
        )
        dry_run = options["dry_run"]

        with transaction.atomic():
            slot = self._get_locked_slot(slot_code)
            plan = self._validate_slot(slot)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: nenhum dado sera alterado."))
            self.stdout.write(
                "Resetaria tenant demo. "
                f"slot={plan.slot_code}; "
                f"status_atual={plan.status}; "
                f"domain={plan.domain_name}."
            )
            return

        with self._demo_reset_advisory_lock(slot_code):
            with transaction.atomic():
                slot = self._get_locked_slot(slot_code)
                plan = self._validate_slot(slot)
                self._mark_reset_in_progress(slot)

            sessions_removed = 0
            try:
                sessions_removed = self._delete_tenant_sessions(plan.slot_code)
                self._drop_schema(plan.slot_code)
                self._recreate_schema(slot.tenant, verbosity=options.get("verbosity", 1))
                self._validate_recreated_schema(plan.slot_code)
                self._sync_minimal_seed(plan.slot_code)
                artifacts_removed = self._delete_tenant_artifacts(plan.slot_code)
                self._release_slot(plan.slot_id, plan.slot_code)
            except Exception as exc:
                self._mark_slot_blocked(plan.slot_id)
                raise CommandError(
                    "Reset do tenant demo falhou; slot mantido como bloqueado."
                ) from exc
            finally:
                connection.set_schema_to_public()

        self.stdout.write(
            self.style.SUCCESS(
                "Tenant demo resetado. "
                f"slot={plan.slot_code}; "
                f"sessoes_removidas={sessions_removed}; "
                f"artefatos_removidos={artifacts_removed}; "
                "status=livre."
            )
        )

    def _get_locked_slot(self, slot_code):
        slot = (
            DemoTenantSlot.objects.select_for_update()
            .select_related("tenant")
            .filter(slot_code=slot_code)
            .first()
        )
        if slot is None:
            raise CommandError(f"Slot demo {slot_code} nao existe ou nao foi provisionado.")
        return slot

    @contextmanager
    def _demo_reset_advisory_lock(self, schema_name):
        lock_key = self._advisory_lock_key(schema_name)
        connection.set_schema_to_public()
        acquired = self._acquire_demo_reset_lock(lock_key)
        if not acquired:
            raise CommandError(
                f"Ja existe reset em andamento para o slot {schema_name}."
            )

        try:
            yield
        finally:
            connection.set_schema_to_public()
            self._release_demo_reset_lock(lock_key)

    def _advisory_lock_key(self, schema_name):
        digest = hashlib.blake2b(
            f"{DEMO_RESET_LOCK_PREFIX}{schema_name}".encode("ascii"),
            digest_size=8,
        ).digest()
        value = int.from_bytes(digest, byteorder="big", signed=False)
        if value >= 2**63:
            value -= 2**64
        return value

    def _acquire_demo_reset_lock(self, lock_key):
        with connection.cursor() as cursor:
            cursor.execute("select pg_try_advisory_lock(%s)", [lock_key])
            return bool(cursor.fetchone()[0])

    def _release_demo_reset_lock(self, lock_key):
        with connection.cursor() as cursor:
            cursor.execute("select pg_advisory_unlock(%s)", [lock_key])

    def _validate_slot(self, slot):
        slot_code = ensure_demo_pool_schema(
            slot.tenant.schema_name,
            command_name="resetar_tenant_demo",
            action="resetar tenant demo",
        )

        if slot.slot_code != slot_code:
            raise CommandError(
                f"Slot {slot.slot_code} aponta para tenant {slot_code}. "
                "O slot deve corresponder ao schema do tenant."
            )

        if slot.status not in ALLOWED_RESET_STATUSES:
            raise CommandError(
                "resetar_tenant_demo permite reset apenas de slots com status "
                "expirado ou bloqueado."
            )

        domain_name = f"{slot.slot_code}.{DEFAULT_DOMAIN_SUFFIX}"
        domain = Domain.objects.select_related("tenant").filter(domain=domain_name).first()
        if domain is None:
            raise CommandError(f"Domain tecnico {domain_name} nao existe.")
        if domain.tenant_id != slot.tenant_id:
            raise CommandError(
                f"Domain tecnico {domain_name} pertence a outro tenant."
            )
        if domain.tenant.schema_name != slot.slot_code:
            raise CommandError(
                f"Domain tecnico {domain_name} aponta para schema inconsistente."
            )

        if not schema_exists(slot.slot_code):
            raise CommandError(f"Schema {slot.slot_code} nao existe no banco.")

        return ResetPlan(
            slot_id=slot.pk,
            slot_code=slot.slot_code,
            tenant_id=slot.tenant_id,
            domain_name=domain_name,
            status=slot.status,
        )

    def _mark_reset_in_progress(self, slot):
        slot.status = DemoTenantSlot.Status.BLOQUEADO
        slot.notes = "Reset demo em andamento."
        slot.full_clean()
        slot.save(update_fields=["status", "notes", "updated_at"])

    def _delete_tenant_sessions(self, schema_name):
        with schema_context(schema_name):
            sessions_removed, _details = Session.objects.all().delete()
            return sessions_removed

    def _drop_schema(self, schema_name):
        connection.set_schema_to_public()
        if not schema_exists(schema_name):
            raise CommandError(f"Schema {schema_name} nao existe no banco.")

        with connection.cursor() as cursor:
            cursor.execute(
                f"DROP SCHEMA {connection.ops.quote_name(schema_name)} CASCADE"
            )
        connection.set_schema_to_public()

    def _recreate_schema(self, tenant, *, verbosity):
        connection.set_schema_to_public()
        tenant.create_schema(check_if_exists=False, verbosity=verbosity)
        connection.set_schema_to_public()

    def _validate_recreated_schema(self, schema_name):
        if not schema_exists(schema_name):
            raise CommandError(f"Schema {schema_name} nao foi recriado.")

        missing_tables = [
            table_name
            for table_name in REQUIRED_TENANT_TABLES
            if not self._tenant_table_exists(schema_name, table_name)
        ]
        if missing_tables:
            raise CommandError(
                f"Schema {schema_name} foi recriado sem tabelas essenciais."
            )

    def _tenant_table_exists(self, schema_name, table_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select exists(
                    select 1
                    from information_schema.tables
                    where table_schema = %s
                      and table_name = %s
                      and table_type = 'BASE TABLE'
                )
                """,
                [schema_name, table_name],
            )
            return bool(cursor.fetchone()[0])

    def _sync_minimal_seed(self, schema_name):
        with schema_context(schema_name):
            sincronizar_grupos_permissoes()
            missing_groups = set(PERMISSION_PROFILES) - set(
                Group.objects.filter(name__in=PERMISSION_PROFILES).values_list(
                    "name",
                    flat=True,
                )
            )
            if missing_groups:
                raise CommandError(
                    f"Seed minimo de grupos nao foi recriado para {schema_name}."
                )

    def _delete_tenant_artifacts(self, schema_name):
        schema_name = ensure_demo_pool_schema(
            schema_name,
            command_name="resetar_tenant_demo",
            action="limpar artefatos tenant-scoped",
        )
        tenant_artifacts_root = artifacts_root_for_schema(schema_name)
        tenants_root = (Path(settings.BASE_DIR) / "backups" / "tenants").resolve()
        resolved_artifacts_root = tenant_artifacts_root.resolve()

        try:
            resolved_artifacts_root.relative_to(tenants_root)
        except ValueError as exc:
            raise CommandError(
                f"Diretorio de artefatos de {schema_name} fora da raiz tenant-scoped."
            ) from exc

        if resolved_artifacts_root == tenants_root:
            raise CommandError("Recusa limpar a raiz de artefatos de tenants.")

        if tenant_artifacts_root.is_symlink():
            raise CommandError(
                f"Diretorio de artefatos de {schema_name} nao e uma pasta segura."
            )

        if not tenant_artifacts_root.exists():
            return 0

        if not tenant_artifacts_root.is_dir():
            raise CommandError(
                f"Diretorio de artefatos de {schema_name} nao e uma pasta segura."
            )

        removed_count = sum(1 for _path in tenant_artifacts_root.rglob("*"))
        shutil.rmtree(tenant_artifacts_root)
        return removed_count

    def _release_slot(self, slot_id, schema_name):
        with transaction.atomic():
            slot = (
                DemoTenantSlot.objects.select_for_update()
                .select_related("tenant")
                .get(pk=slot_id)
            )
            if slot.slot_code != schema_name or slot.tenant.schema_name != schema_name:
                raise CommandError("DemoTenantSlot mudou durante o reset.")

            slot.status = DemoTenantSlot.Status.LIVRE
            slot.assigned_name = ""
            slot.assigned_email = ""
            slot.assigned_phone = ""
            slot.lease_started_at = None
            slot.lease_expires_at = None
            slot.last_reset_at = timezone.now()
            slot.notes = ""
            slot.full_clean()
            slot.save(
                update_fields=[
                    "status",
                    "assigned_name",
                    "assigned_email",
                    "assigned_phone",
                    "lease_started_at",
                    "lease_expires_at",
                    "last_reset_at",
                    "notes",
                    "updated_at",
                ]
            )

    def _mark_slot_blocked(self, slot_id):
        connection.set_schema_to_public()
        with transaction.atomic():
            slot = DemoTenantSlot.objects.select_for_update().get(pk=slot_id)
            slot.status = DemoTenantSlot.Status.BLOQUEADO
            slot.notes = "Reset demo falhou; revisar manualmente antes de liberar."
            slot.full_clean()
            slot.save(update_fields=["status", "notes", "updated_at"])
