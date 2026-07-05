import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.validar_preflight_deploy_financeiro import (
    validar_preflight_deploy_financeiro,
)
from caixa.pm03_sequence import montar_posicao_sequencia_pm03
from caixa.services_dividas import sincronizar_credores_dividas_fcf
from caixa.services_dividas_fcf import resumir_integridade_entradas_fcf_dividas
from tenancy.command_guards import ensure_tenant_schema


SOURCE_PM03_4 = "financiamento_movimentacao"


class Command(BaseCommand):
    help = (
        "Gera a evidencia agregada de regressao de dividas FCF exigida na PM-03.4 "
        "antes de promover financiamento_movimentacao para canonical-first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=SOURCE_PM03_4,
            help="Origem PM-03 em validacao. Para esta regressao use financiamento_movimentacao.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de pendencias detalhadas retornadas.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime a regressao em JSON para automacoes.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON da regressao em arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown da regressao em arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help="Diretorio opcional para gerar arquivos padronizados de evidencia PM-03.",
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os caminhos de evidencia PM-03 nao forem informados "
                "por --diretorio-evidencias ou caminhos explicitos."
            ),
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando a regressao de dividas FCF nao estiver aprovada.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("validar_regressao_dividas_pm03", action="validar dados operacionais")
        evidence_files = _normalizar_arquivos_evidencia(options)
        if options["exigir_arquivos_evidencia"]:
            _exigir_arquivos_evidencia(evidence_files)

        resultado = validar_regressao_dividas_pm03(
            source=options.get("source"),
            limit=options.get("limit", 20),
        )
        resultado["evidenceFiles"] = evidence_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_regressao_dividas_pm03(resultado),
        }
        _salvar_evidencias_regressao(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_regressao_dividas_pm03(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(self.style.SUCCESS("Regressao PM-03 de dividas FCF aprovada."))
        else:
            self.stdout.write(
                self.style.WARNING("Regressao PM-03 de dividas FCF com pendencias.")
            )
        self.stdout.write(f"Origem: {resultado['source']}")
        decision = resultado.get("regressionDecision") or {}
        sequence_position = resultado.get("sequencePosition") or {}
        self.stdout.write(
            "Decisao regressao: "
            f"status={decision.get('status') or '-'}; "
            f"step={decision.get('step') or '-'}; "
            f"mayContinuePm03_4={decision.get('mayContinuePm03_4')}; "
            f"blockedBy={'; '.join(decision.get('blockedBy') or []) or '-'}"
        )
        self.stdout.write(
            "Sequencia PM-03: "
            f"position={sequence_position.get('position')}/"
            f"{sequence_position.get('totalDirectSteps')}; "
            f"previous={sequence_position.get('previousStep') or '-'}; "
            f"current={sequence_position.get('step') or '-'}; "
            f"next={sequence_position.get('nextStep') or '-'}"
        )
        self.stdout.write(
            "Credores FCF: "
            f"consistentAfter={resultado['debtCreditorRegression'].get('consistentAfter')}"
        )
        self.stdout.write(
            "Entradas automaticas FCF: "
            f"consistent={resultado['debtAutomaticFcfEntryIntegrity'].get('consistent')}"
        )
        self.stdout.write(
            "Pre-flight financeiro: "
            f"ready={resultado['financialPreflight'].get('ready')}"
        )
        for issue in resultado["issues"]:
            self.stdout.write(f"- {issue}")


def validar_regressao_dividas_pm03(source=SOURCE_PM03_4, limit=20):
    if limit < 0:
        raise CommandError("--limit deve ser maior ou igual a 0.")

    source = str(source or "").strip()
    credores = sincronizar_credores_dividas_fcf(aplicar=False, limit=limit)
    entradas_fcf = resumir_integridade_entradas_fcf_dividas(limit=limit)
    preflight = validar_preflight_deploy_financeiro(
        {
            "credores_dividas_limit": limit,
            "entradas_fcf_dividas_limit": limit,
        }
    )
    issues = _coletar_issues_regressao_dividas_pm03(
        source=source,
        credores=credores,
        entradas_fcf=entradas_fcf,
        preflight=preflight,
    )

    resultado = {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "source": source,
        "ready": not issues,
        "issues": issues,
        "sequencePosition": montar_posicao_sequencia_pm03(source),
        "debtCreditorRegression": credores,
        "debtAutomaticFcfEntryIntegrity": entradas_fcf,
        "financialPreflight": preflight,
    }
    resultado["regressionDecision"] = montar_decisao_regressao_dividas_pm03(
        source=source,
        ready=resultado["ready"],
        issues=issues,
    )
    return resultado


def montar_decisao_regressao_dividas_pm03(source, ready, issues=None):
    blocked_by = [str(issue) for issue in (issues or []) if str(issue)]
    if ready:
        return {
            "status": "approved",
            "label": "Regressao de dividas FCF aprovada",
            "source": source,
            "step": "PM-03.4",
            "mayContinuePm03_4": True,
            "requiredBefore": [
                "validateActivationCanaryRollbackOnly",
                "activateAllowlistWindow",
            ],
            "blockedBy": [],
            "detail": (
                "Regressao de dividas FCF pronta para compor o pacote de "
                "evidencias da PM-03.4."
            ),
        }
    return {
        "status": "blocked",
        "label": "Regressao de dividas FCF bloqueada",
        "source": source,
        "step": "PM-03.4",
        "mayContinuePm03_4": False,
        "requiredBefore": [
            "validateActivationCanaryRollbackOnly",
            "activateAllowlistWindow",
        ],
        "blockedBy": blocked_by,
        "detail": (
            "Nao continuar a PM-03.4 antes de resolver a regressao de dividas "
            "FCF."
        ),
    }


def _coletar_issues_regressao_dividas_pm03(source, credores, entradas_fcf, preflight):
    issues = []
    if source != SOURCE_PM03_4:
        issues.append(
            "regressao de dividas PM-03 deve ser usada com source=financiamento_movimentacao"
        )
    if credores.get("consistentAfter") is not True:
        issues.append(
            "credores de dividas FCF nao ficaram consistentes em dry-run: "
            f"pendencias={credores.get('remainingIssues')}"
        )
    if entradas_fcf.get("consistent") is not True:
        issues.append(
            "entradas FCF automaticas de dividas possuem pendencias: "
            f"pendencias={entradas_fcf.get('totalIssues')}"
        )
    if preflight.get("ready") is not True:
        preflight_issues = preflight.get("issues") or []
        detail = preflight_issues[0] if preflight_issues else "consulte o pre-flight financeiro"
        issues.append(f"pre-flight financeiro nao aprovado: {detail}")
    return issues


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias", "")
    save_json = options.get("salvar_json", "")
    save_record = options.get("salvar_registro", "")

    if directory:
        base_path = Path(directory).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError("--diretorio-evidencias deve apontar para um diretorio")
        if not save_json:
            save_json = str(base_path / "pm03-regressao-dividas-fcf.json")
        if not save_record:
            save_record = str(base_path / "pm03-regressao-dividas-fcf.md")

    return {
        "directory": directory,
        "json": save_json,
        "record": save_record,
    }


def _exigir_arquivos_evidencia(evidence_files):
    missing = [
        label
        for label, path in (
            ("json", evidence_files.get("json")),
            ("record", evidence_files.get("record")),
        )
        if not path
    ]
    if missing:
        raise CommandError(
            "arquivos de evidencia PM-03 incompletos: " + ", ".join(missing)
        )


def _salvar_evidencias_regressao(resultado):
    evidence_files = resultado.get("evidenceFiles") or {}
    json_path = evidence_files.get("json")
    record_path = evidence_files.get("record")

    if json_path:
        _salvar_texto(
            json_path,
            json.dumps(resultado, ensure_ascii=False, sort_keys=True, indent=2),
        )
    if record_path:
        _salvar_texto(record_path, resultado["executionRecord"]["markdown"])


def _salvar_texto(path, content):
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _registro_regressao_dividas_pm03(resultado):
    issues = "; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"
    credores = resultado["debtCreditorRegression"]
    entradas = resultado["debtAutomaticFcfEntryIntegrity"]
    preflight = resultado["financialPreflight"]
    decision = resultado.get("regressionDecision") or {}
    sequence_position = resultado.get("sequencePosition") or {}
    evidence_files = resultado.get("evidenceFiles") or {}
    return "\n".join(
        [
            "### Registro PM-03 - regressao de dividas FCF",
            "",
            f"Data/hora da regressao: {resultado['generatedAt']}",
            f"Origem: {resultado['source']}",
            f"ready/issues: ready={resultado['ready']}; issues={issues}",
            (
                "Decisao regressao: "
                f"status={decision.get('status') or '-'}; "
                f"step={decision.get('step') or '-'}; "
                f"mayContinuePm03_4={decision.get('mayContinuePm03_4')}; "
                f"blockedBy={'; '.join(decision.get('blockedBy') or []) or '-'}"
            ),
            (
                "Sequencia PM-03: "
                f"position={sequence_position.get('position')}/"
                f"{sequence_position.get('totalDirectSteps')}; "
                f"previous={sequence_position.get('previousStep') or '-'}; "
                f"current={sequence_position.get('step') or '-'}; "
                f"next={sequence_position.get('nextStep') or '-'}"
            ),
            (
                "Credores de dividas FCF: "
                f"mode={credores.get('mode')}; "
                f"pending={credores.get('pendingCount')}; "
                f"remaining={credores.get('remainingIssues')}; "
                f"consistentAfter={credores.get('consistentAfter')}"
            ),
            (
                "Entradas FCF automaticas de dividas: "
                f"checked={entradas.get('checked')}; "
                f"issues={entradas.get('totalIssues')}; "
                f"consistent={entradas.get('consistent')}"
            ),
            (
                "Pre-flight financeiro: "
                f"ready={preflight.get('ready')}; "
                f"issues={len(preflight.get('issues') or [])}"
            ),
            (
                "Arquivos salvos: "
                f"diretorio={evidence_files.get('directory') or '-'}; "
                f"json={evidence_files.get('json') or '-'}; "
                f"registro={evidence_files.get('record') or '-'}"
            ),
        ]
    )


def formatar_erro_regressao_dividas_pm03(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Regressao PM-03 de dividas FCF nao aprovada: {issues[0]}"
    return "Regressao PM-03 de dividas FCF nao aprovada."
