from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name

from tenancy.command_guards import (
    ensure_demo_pool_schema,
    is_demo_public_pool_schema,
)
from tenancy.models import DEMO_SLOT_CODES, DemoTenantSlot, Domain, Tenant


DEFAULT_DOMAIN_SUFFIX = "api-demo-rh.taquiondev.com.br"
MAX_SLOTS = len(DEMO_SLOT_CODES)


@dataclass(frozen=True)
class SlotPlan:
    slot_code: str
    is_public_pool_slot: bool
    tenant: Tenant | None
    domain: Domain | None
    slot: DemoTenantSlot | None

    @property
    def domain_name(self):
        return f"{self.slot_code}.{DEFAULT_DOMAIN_SUFFIX}"

    @property
    def tenant_name(self):
        number = self.slot_code.removeprefix("demo")
        return f"Demo {number}"


class Command(BaseCommand):
    help = (
        "Provisiona tenants demo1...demo10 de forma idempotente. Cria Tenant "
        "e Domain para todos, mas DemoTenantSlot somente para a pool publica."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--slots",
            type=int,
            default=MAX_SLOTS,
            help="Quantidade de slots demo a provisionar. Padrao: 10.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria criado sem alterar o banco.",
        )

    def handle(self, *args, **options):
        slots = options["slots"]
        dry_run = options["dry_run"]

        if slots < 1 or slots > MAX_SLOTS:
            raise CommandError(f"--slots deve estar entre 1 e {MAX_SLOTS}.")

        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "provisionar_pool_demo deve executar no schema public da plataforma."
            )

        slot_codes = DEMO_SLOT_CODES[:slots]
        plans = [self._build_slot_plan(slot_code) for slot_code in slot_codes]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: nenhum dado sera alterado."))
            for plan in plans:
                self._print_plan(plan)
            return

        created = {"tenant": 0, "domain": 0, "slot": 0}
        existing = {"tenant": 0, "domain": 0, "slot": 0}
        permanent = 0

        for plan in plans:
            tenant = plan.tenant
            if tenant is None:
                tenant = Tenant(schema_name=plan.slot_code, name=plan.tenant_name)
                tenant.save(verbosity=options.get("verbosity", 1))
                created["tenant"] += 1
                self.stdout.write(f"Tenant criado: {plan.slot_code}")
            else:
                existing["tenant"] += 1

            if plan.domain is None:
                Domain.objects.create(
                    tenant=tenant,
                    domain=plan.domain_name,
                    is_primary=True,
                )
                created["domain"] += 1
                self.stdout.write(f"Domain criado: {plan.domain_name}")
            else:
                existing["domain"] += 1

            if not plan.is_public_pool_slot:
                permanent += 1
                self.stdout.write(
                    f"Tenant permanente preservado sem DemoTenantSlot: {plan.slot_code}"
                )
            elif plan.slot is None:
                DemoTenantSlot.objects.create(
                    tenant=tenant,
                    slot_code=plan.slot_code,
                    status=DemoTenantSlot.Status.LIVRE,
                    max_storage_mb=50,
                )
                created["slot"] += 1
                self.stdout.write(f"DemoTenantSlot criado: {plan.slot_code}")
            else:
                existing["slot"] += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Pool demo provisionado. "
                f"Tenants criados={created['tenant']} existentes={existing['tenant']}; "
                f"Domains criados={created['domain']} existentes={existing['domain']}; "
                f"Slots criados={created['slot']} existentes={existing['slot']}; "
                f"tenants_permanentes={permanent}."
            )
        )

    def _build_slot_plan(self, slot_code):
        ensure_demo_pool_schema(
            slot_code,
            command_name="provisionar_pool_demo",
            action="provisionar pool demo",
        )
        domain_name = f"{slot_code}.{DEFAULT_DOMAIN_SUFFIX}"

        tenant = Tenant.objects.filter(schema_name=slot_code).first()
        domain = Domain.objects.select_related("tenant").filter(domain=domain_name).first()
        slot = (
            DemoTenantSlot.objects.select_related("tenant")
            .filter(slot_code=slot_code)
            .first()
        )
        is_public_pool_slot = is_demo_public_pool_schema(slot_code)

        if not is_public_pool_slot and slot is not None:
            raise CommandError(
                f"O tenant permanente {slot_code} ainda possui DemoTenantSlot. "
                "Aplique a migration que o remove da pool antes de provisionar."
            )

        if domain is not None and domain.tenant.schema_name != slot_code:
            raise CommandError(
                f"Domain tecnico {domain_name} ja pertence ao tenant "
                f"{domain.tenant.schema_name}."
            )

        if slot is not None and slot.tenant.schema_name != slot_code:
            raise CommandError(
                f"DemoTenantSlot {slot_code} ja pertence ao tenant "
                f"{slot.tenant.schema_name}."
            )

        if tenant is not None:
            tenant_slot = getattr(tenant, "demo_slot", None)
            if tenant_slot is not None and tenant_slot.slot_code != slot_code:
                raise CommandError(
                    f"Tenant {slot_code} ja possui slot demo "
                    f"{tenant_slot.slot_code}."
                )

        return SlotPlan(
            slot_code=slot_code,
            is_public_pool_slot=is_public_pool_slot,
            tenant=tenant,
            domain=domain,
            slot=slot,
        )

    def _print_plan(self, plan):
        actions = []
        actions.append("tenant existente" if plan.tenant else "criaria tenant")
        actions.append("domain existente" if plan.domain else "criaria domain")
        if plan.is_public_pool_slot:
            actions.append("slot existente" if plan.slot else "criaria slot")
        else:
            actions.append("tenant permanente; sem slot de pool")
        self.stdout.write(f"{plan.slot_code}: {', '.join(actions)}")
