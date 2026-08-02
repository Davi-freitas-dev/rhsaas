import uuid
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from caixa.models_custo_fixo import AuditoriaCustoRecorrente
from caixa.models_servidores import Servidor
from caixa.services_ativacao_mensalistas import (
    CONFIRMACAO_ATIVACAO,
    ativar_mensalista_existente,
    avaliar_mensalista_para_ativacao,
)
from caixa.services_auditoria_recorrencias import (
    registrar_evento_auditoria_recorrente,
)
from caixa.services_custos_recorrentes import inicio_do_mes
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Avalia ou ativa planos salariais de mensalistas existentes. "
        "Exige corte explícito e confirmação forte para qualquer escrita."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-corte",
            required=True,
            help="Data autorizada inicial no formato AAAA-MM-DD.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Avalia todos os candidatos sem realizar nenhuma escrita.",
        )
        parser.add_argument(
            "--confirmar",
            default="",
            help=f"Para escrever, informe exatamente {CONFIRMACAO_ATIVACAO}.",
        )
        parser.add_argument(
            "--servidor-id",
            action="append",
            type=int,
            dest="servidores_ids",
            help="Limita a execução a um servidor; pode ser repetido.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("ativar_mensalistas_existentes")
        data_corte = self._parse_data_corte(options["data_corte"])
        dry_run = options["dry_run"]
        if not dry_run and options["confirmar"] != CONFIRMACAO_ATIVACAO:
            raise CommandError(
                "Escrita recusada. Use --confirmar "
                f"{CONFIRMACAO_ATIVACAO} após revisar o dry-run."
            )

        servidores = Servidor.objects.filter(
            tipo_vinculo=Servidor.VINCULO_MENSALISTA
        )
        ids = list(dict.fromkeys(options.get("servidores_ids") or []))
        if ids:
            servidores = servidores.filter(pk__in=ids)
        servidores = list(servidores.order_by("pk"))
        correlation_id = uuid.uuid4()
        resultados = []

        for servidor in servidores:
            if dry_run:
                resultado = avaliar_mensalista_para_ativacao(
                    servidor,
                    data_corte=data_corte,
                )
            else:
                try:
                    resultado = ativar_mensalista_existente(
                        servidor,
                        data_corte=data_corte,
                        correlation_id=correlation_id,
                    )
                except Exception as error:
                    resultado = {
                        "status": "error",
                        "reason": "ACTIVATION_FAILED",
                    }
                    registrar_evento_auditoria_recorrente(
                        tipo_evento=AuditoriaCustoRecorrente.TIPO_ATIVACAO,
                        origem=AuditoriaCustoRecorrente.ORIGEM_ATIVACAO,
                        competencia=inicio_do_mes(data_corte),
                        status=AuditoriaCustoRecorrente.STATUS_FALHA,
                        codigo_motivo=(
                            AuditoriaCustoRecorrente.MOTIVO_ATIVACAO_FALHA
                        ),
                        correlation_id=correlation_id,
                    )
                    self.stderr.write(
                        "Falha segura na ativação "
                        f"serverId={servidor.pk} "
                        f"exceptionClass={error.__class__.__name__}"
                    )
            resultados.append({"serverId": servidor.pk, **resultado})

        contagens = {
            status: sum(item["status"] == status for item in resultados)
            for status in [
                "eligible",
                "activated",
                "alreadyConfigured",
                "blocked",
                "invalid",
                "error",
            ]
        }
        self.stdout.write(
            f"dryRun={'true' if dry_run else 'false'} "
            f"cutoff={data_corte.isoformat()} candidates={len(servidores)} "
            + " ".join(f"{chave}={valor}" for chave, valor in contagens.items())
            + f" correlationId={correlation_id}"
        )
        for item in resultados:
            self.stdout.write(
                f"serverId={item['serverId']} status={item['status']} "
                f"reason={item.get('reason') or '-'}"
            )
        if contagens["error"]:
            raise CommandError(
                f"A ativação terminou com {contagens['error']} erro(s)."
            )

    @staticmethod
    def _parse_data_corte(raw):
        try:
            data_corte = date.fromisoformat(raw)
        except (TypeError, ValueError) as error:
            raise CommandError(
                "Use --data-corte no formato AAAA-MM-DD."
            ) from error
        if data_corte.isoformat() != raw:
            raise CommandError(
                "Use --data-corte no formato AAAA-MM-DD."
            )
        return data_corte
