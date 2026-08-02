from django.core.management.base import BaseCommand, CommandError

from tenancy.command_guards import ensure_tenant_schema

from ...services_idempotencia import (
    RETENCAO_IDEMPOTENCIA_PADRAO_DIAS,
    expurgar_requisicoes_idempotentes_recorrencia,
)


class Command(BaseCommand):
    help = (
        "Remove requisições idempotentes recorrentes fora da janela de retry "
        "no schema tenant atual."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--retencao-dias",
            type=int,
            default=RETENCAO_IDEMPOTENCIA_PADRAO_DIAS,
            help="Dias a preservar; mínimo de um dia.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Informa a quantidade sem remover registros.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("expurgar_requisicoes_idempotentes_recorrencia")
        try:
            quantidade = expurgar_requisicoes_idempotentes_recorrencia(
                retencao_dias=options["retencao_dias"],
                dry_run=options["dry_run"],
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        acao = "wouldRemove" if options["dry_run"] else "removed"
        self.stdout.write(
            f"idempotencyRequests{acao[0].upper()}{acao[1:]}={quantidade}; "
            f"retentionDays={options['retencao_dias']}; dryRun={options['dry_run']}"
        )
