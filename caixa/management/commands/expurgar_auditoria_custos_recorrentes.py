import uuid

from django.core.management.base import BaseCommand
from django.utils import timezone

from caixa.models_custo_fixo import AuditoriaCustoRecorrente
from caixa.services_auditoria_recorrencias import (
    RETENCAO_AUDITORIA,
    expurgar_auditoria_recorrencias,
    registrar_evento_auditoria_recorrente,
)
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Remove somente eventos de auditoria recorrente com mais de 400 dias. "
        "Não deve ser agendado em produção antes do gate operacional."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Informa a quantidade elegível sem remover registros.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("expurgar_auditoria_custos_recorrentes")
        agora = timezone.now()
        limite = agora - RETENCAO_AUDITORIA
        elegiveis = AuditoriaCustoRecorrente.objects.filter(
            last_occurred_at__lt=limite
        ).count()
        if options["dry_run"]:
            self.stdout.write(
                f"dryRun=true eligibleForDeletion={elegiveis} deleted=0"
            )
            return

        removidos = expurgar_auditoria_recorrencias(agora=agora)
        correlation_id = uuid.uuid4()
        registrar_evento_auditoria_recorrente(
            tipo_evento=AuditoriaCustoRecorrente.TIPO_EXPURGO,
            origem=AuditoriaCustoRecorrente.ORIGEM_COMMAND,
            status=AuditoriaCustoRecorrente.STATUS_SUCESSO,
            codigo_motivo=AuditoriaCustoRecorrente.MOTIVO_EXPURGO,
            correlation_id=correlation_id,
        )
        self.stdout.write(
            "dryRun=false "
            f"eligibleForDeletion={elegiveis} deleted={removidos} "
            f"correlationId={correlation_id}"
        )
