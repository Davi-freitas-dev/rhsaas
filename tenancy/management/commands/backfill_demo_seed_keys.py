from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name, schema_context, schema_exists

from caixa.demo_seed import (
    DEMO_SEED_SPEC,
    inspect_demo_seed_readiness,
    match_legacy_demo_seed,
    validate_demo_seed_readiness,
)
from tenancy.command_guards import ensure_demo_pool_schema


TEST_SCHEMA_NAME = "rh_teste"


class Command(BaseCommand):
    help = (
        "Marca, de forma controlada, as chaves do seed em um schema demo legado. "
        "Nao reconhece dados por um unico campo e nunca opera no schema public."
    )

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida candidatos sem gravar nenhuma chave.",
        )
        parser.add_argument(
            "--confirm",
            help='Confirmacao forte para escrita: "MARCAR-SEED demoN".',
        )
        parser.add_argument(
            "--allow-test-schema",
            action="store_true",
            help="Permite exclusivamente o schema rh_teste em ambiente controlado.",
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        public_schema = get_public_schema_name()
        if connection.schema_name != public_schema:
            raise CommandError(
                "backfill_demo_seed_keys deve iniciar no schema public."
            )

        schema_name = str(options["schema"] or "").strip().lower()
        if schema_name == public_schema:
            raise CommandError("O schema public nunca pode receber chaves de seed demo.")
        if schema_name == TEST_SCHEMA_NAME:
            if not options["allow_test_schema"]:
                raise CommandError(
                    "rh_teste exige --allow-test-schema explicito."
                )
        else:
            schema_name = ensure_demo_pool_schema(
                schema_name,
                command_name="backfill_demo_seed_keys",
                action="marcar seed legado",
            )

        if not schema_exists(schema_name):
            raise CommandError(f"Schema permitido nao existe: {schema_name}.")

        dry_run = options["dry_run"]
        if not dry_run and options.get("confirm") != f"MARCAR-SEED {schema_name}":
            raise CommandError(
                f'Escrita exige --confirm "MARCAR-SEED {schema_name}".'
            )

        try:
            with schema_context(schema_name):
                readiness = inspect_demo_seed_readiness()
                if readiness.ready:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Schema {schema_name} ja possui seed pronto; nenhuma alteracao."
                        )
                    )
                    return
                if any(
                    entry["model"].objects.exclude(
                        demo_seed_key__isnull=True
                    ).exists()
                    for entry in DEMO_SEED_SPEC.values()
                ):
                    raise CommandError(
                        "Schema possui marcacao parcial ou desconhecida; revise ou resete."
                    )

                matches = match_legacy_demo_seed()
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            "DRY-RUN: conjunto legado e relacoes correspondem; "
                            "nenhuma chave foi gravada."
                        )
                    )
                    for name, entry in DEMO_SEED_SPEC.items():
                        self.stdout.write(f"{name}: {entry['key']}")
                    return

                with transaction.atomic():
                    for name, entry in DEMO_SEED_SPEC.items():
                        model = entry["model"]
                        candidate = model.objects.select_for_update().get(
                            pk=matches[name].pk
                        )
                        if candidate.demo_seed_key is not None:
                            raise CommandError(
                                "Candidato mudou durante o backfill; nenhuma alteracao aplicada."
                            )
                        model.objects.filter(pk=candidate.pk).update(
                            demo_seed_key=entry["key"]
                        )
                    validate_demo_seed_readiness()
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                "Seed legado ambiguo ou inconsistente; nada foi alterado. "
                "Resete o schema ou revise-o manualmente."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Chaves seed aplicadas e validadas no schema {schema_name}."
            )
        )
