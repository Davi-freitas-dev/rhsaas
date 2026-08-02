from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.models_custo_fixo import AuditoriaCustoRecorrente
from caixa.services_custos_recorrentes import (
    materializar_competencia,
    recuperar_competencias_ausentes,
)
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Materializa, de forma idempotente, os planos de custos recorrentes "
        "e salários elegíveis para uma competência."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--competencia",
            help=(
                "Competência única no formato AAAA-MM. Quando omitida, recupera "
                "todas as competências ausentes até o mês local atual."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a execução sem gravar custos, obrigações ou lançamentos.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("materializar_custos_recorrentes")
        competencia = self._parse_competencia(options.get("competencia"))
        if competencia is None:
            resultado = recuperar_competencias_ausentes(
                competencia_limite=timezone.localdate(),
                dry_run=options["dry_run"],
                origem=AuditoriaCustoRecorrente.ORIGEM_COMMAND,
            )
            periodo = f"até {resultado['throughCompetence'][:7]}"
        else:
            resultado = materializar_competencia(
                competencia=competencia,
                dry_run=options["dry_run"],
                origem=AuditoriaCustoRecorrente.ORIGEM_COMMAND,
            )
            periodo = f"competência {resultado['competence'][:7]}"
        modo = "SIMULAÇÃO" if resultado["dryRun"] else "EXECUÇÃO"
        contagens = resultado["counts"]
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{modo} — {periodo}"
            )
        )
        self.stdout.write(
            "criados={created} criaria={wouldCreate} existentes={alreadyMaterialized} "
            "ignorados={ignored} bloqueados={blocked} erros={error}".format(**contagens)
        )
        for item in resultado["results"]:
            detalhe = (
                item.get("reasonLabel")
                or item.get("reason")
                or ""
            )
            self.stdout.write(
                f"plano={item['planId']} status={item['status']} "
                f"competencia={item['competence']} {detalhe}".rstrip()
            )
        if contagens["error"]:
            raise CommandError(
                f"A materialização terminou com {contagens['error']} erro(s)."
            )

    @staticmethod
    def _parse_competencia(raw):
        if not raw:
            return None
        try:
            ano_texto, mes_texto = raw.strip().split("-", 1)
            competencia = date(int(ano_texto), int(mes_texto), 1)
        except (AttributeError, TypeError, ValueError) as error:
            raise CommandError("Use --competencia no formato AAAA-MM.") from error
        if len(raw.strip()) != 7:
            raise CommandError("Use --competencia no formato AAAA-MM.")
        return competencia
