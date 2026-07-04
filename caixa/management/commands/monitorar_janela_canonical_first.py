import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.auditar_fonte_escrita_baixas import (
    auditar_fonte_escrita_baixas,
)
from caixa.management.commands.validar_janela_canonical_first import (
    montar_resultado_janela_canonical_first,
    validar_janela_canonical_first,
)
from caixa.management.commands.validar_ativacao_canonical_first import (
    resumir_pendencias_sem_canario,
)


class Command(BaseCommand):
    help = (
        "Monitora uma janela canonical-first ativa por origem. "
        "Combina feature flag, pre-flight operacional e auditoria de baixas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument(
            "--data-inicial",
            "--data-ativacao",
            dest="data_inicial",
            help=(
                "Inicio da janela de auditoria. Use a data em que a origem "
                "foi ativada em canonical-first."
            ),
        )
        parser.add_argument("--data-final", dest="data_final")
        parser.add_argument(
            "--exigir-canonical-first",
            action="store_true",
            help="Reprova o monitoramento se a janela nao tiver baixa canonical-first.",
        )
        parser.add_argument(
            "--falhar-com-legado-na-janela",
            action="store_true",
            help=(
                "Retorna erro quando houver baixa legacyAdapterSynced no mesmo "
                "recorte monitorado."
            ),
        )
        parser.add_argument(
            "--exigir-data-ativacao",
            action="store_true",
            help=(
                "Reprova o monitoramento se a data inicial da janela "
                "canonical-first nao for informada."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o monitoramento em JSON para automacoes.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON do monitoramento em um arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown do monitoramento em um arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help=(
                "Diretorio opcional para gerar arquivos padronizados de "
                "evidencia PM-03."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os caminhos de evidencia PM-03 nao forem "
                "informados por --diretorio-evidencias ou caminhos explicitos."
            ),
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando o monitoramento nao estiver aprovado.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias canonicas avaliadas.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        if options["exigir_arquivos_evidencia"]:
            _exigir_arquivos_evidencia(evidence_files)
        resultado = monitorar_janela_canonical_first(
            source=options["source"],
            data_inicial=options.get("data_inicial"),
            data_final=options.get("data_final"),
            exigir_canonical_first=options["exigir_canonical_first"],
            falhar_com_legado_na_janela=options["falhar_com_legado_na_janela"],
            exigir_data_ativacao=options["exigir_data_ativacao"],
            limit=options["limit"],
        )
        resultado["evidenceFiles"] = evidence_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_monitoramento_pm03(resultado),
        }
        _salvar_evidencias_monitoramento(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_monitoramento_nao_aprovado(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Monitoramento canonical-first aprovado.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Monitoramento canonical-first com pontos de atencao."
                )
            )

        periodo = resultado["period"]
        self.stdout.write(f"Origem: {resultado['source']}")
        self.stdout.write(
            f"Periodo: {periodo['startDate'] or '-'} a {periodo['endDate'] or '-'}"
        )
        if not periodo["startDate"]:
            self.stdout.write(
                "Janela: informe --data-inicial=DATA_DA_ATIVACAO "
                "para nao misturar baixas legadas anteriores a ativacao."
            )
        self.stdout.write(
            "Feature flag: "
            + (
                "ativa para a origem"
                if resultado["featureFlagValidation"]["activeForSource"]
                else "nao ativa para a origem"
            )
        )
        self.stdout.write(
            "Pre-flight operacional: "
            + (
                "ambiente pronto"
                if resultado["operationalPreflight"]["ready"]
                else "pontos de atencao"
            )
        )

        auditoria = resultado["writeAudit"]
        self.stdout.write(
            "Baixas na janela: "
            f"total={auditoria['count']}; "
            f"canonicalFirst={auditoria['canonicalFirst']['count']} "
            f"valor={auditoria['canonicalFirst']['outflowAmount']:.2f}; "
            f"legacyAdapterSynced={auditoria['legacyAdapterSynced']['count']} "
            f"valor={auditoria['legacyAdapterSynced']['outflowAmount']:.2f}"
        )
        pendencias = resultado["pendingObligations"]
        self.stdout.write(
            "Pendencias: "
            f"total={pendencias['count']}; "
            f"a pagar={pendencias['payableCount']}; "
            f"a receber={pendencias['receivableCount']}; "
            f"canario={pendencias['canaryEligibleCount']}"
        )
        candidate_list_health = resultado.get("candidateListHealth") or {}
        if candidate_list_health:
            self.stdout.write(
                "Lista de candidatos: "
                f"status={candidate_list_health.get('status') or '-'}; "
                f"acao={candidate_list_health.get('recommendedAction') or '-'}"
            )
        self._imprimir_candidatos_canario(pendencias)
        proxima_acao = resultado.get("nextAction") or {}
        if proxima_acao:
            self.stdout.write(
                "Proxima acao: "
                f"{proxima_acao.get('label')}; "
                f"{proxima_acao.get('detail')}"
            )
        decisao = resultado.get("activationDecision") or {}
        if decisao:
            self.stdout.write(
                "Decisao ativacao: "
                f"status={decisao.get('status') or '-'}; "
                "mayRunCanaryRollbackOnly="
                f"{decisao.get('mayRunCanaryRollbackOnly')}; "
                "mayActivateAllowlistWindow="
                f"{decisao.get('mayActivateAllowlistWindow')}; "
                "requiresControlledCandidate="
                f"{decisao.get('requiresControlledCandidate')}"
            )
        outcome = resultado.get("windowOutcome") or {}
        if outcome:
            self.stdout.write(
                "Resultado da janela: "
                f"{outcome.get('label')}; {outcome.get('detail')}"
            )
            note = outcome.get("nextActionNote")
            if note:
                self.stdout.write(f"Nota nextAction: {note}")
        gate = resultado.get("operationalGate") or {}
        if gate:
            self.stdout.write(
                "Gate operacional: "
                f"{gate.get('currentStep') or '-'}; "
                f"{gate.get('statusLabel') or gate.get('status') or '-'}"
            )
        sequence_position = resultado.get("sequencePosition") or {}
        if sequence_position:
            self.stdout.write(
                "Sequencia PM-03: "
                f"position={sequence_position.get('position') or '-'}"
                f"/{sequence_position.get('totalDirectSteps') or '-'}; "
                f"previous={sequence_position.get('previousStep') or '-'}; "
                f"current={sequence_position.get('step') or '-'}; "
                f"next={sequence_position.get('nextStep') or '-'}"
            )
        for issue in resultado["issues"]:
            self.stdout.write(f"- {issue}")

    def _imprimir_candidatos_canario(self, pendencias):
        candidatos = pendencias.get("canaryCandidates") or []
        if not candidatos:
            return

        self.stdout.write("Candidatos para canario rollback-only:")
        for candidato in candidatos:
            self.stdout.write(
                "- "
                f"sourceId={candidato['sourceId']}; "
                f"obrigacao={candidato['obligationId']}; "
                f"vencimento={candidato['dueDate']}; "
                f"pendente={candidato['pendingAmount']}; "
                f"descricao={candidato['description']}"
            )


def monitorar_janela_canonical_first(
    source,
    data_inicial=None,
    data_final=None,
    exigir_canonical_first=False,
    falhar_com_legado_na_janela=False,
    exigir_data_ativacao=False,
    limit=20,
):
    validacao = validar_janela_canonical_first(
        source=source,
        data_inicial=data_inicial,
        data_final=data_final,
        exigir_feature_flag_ativa=True,
        validar_preflight_operacional=True,
        falhar_com_preflight_operacional=True,
        limit=limit,
    )
    auditoria = auditar_fonte_escrita_baixas(
        data_inicial=data_inicial,
        data_final=data_final,
        source=source,
    )
    issues = list(validacao["issues"])

    if exigir_data_ativacao and not data_inicial:
        issues.append("Informe a data de ativacao da janela canonical-first.")

    if exigir_canonical_first and auditoria["canonicalFirst"]["count"] == 0:
        issues.append("Nenhuma baixa canonical-first encontrada na janela.")

    if (
        falhar_com_legado_na_janela
        and auditoria["legacyAdapterSynced"]["count"] > 0
    ):
        issues.append("Baixas legadas encontradas na janela canonical-first ativa.")

    ready = validacao["ready"] and not issues
    outcome = montar_resultado_janela_canonical_first(
        auditoria,
        issues,
        ready,
        next_action=validacao.get("nextAction") or {},
    )

    return {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "ready": ready,
        "source": source,
        "period": {
            "startDate": data_inicial or "",
            "endDate": data_final or "",
        },
        "windowGuidance": {
            "activationDateRecommended": True,
            "message": (
                "A data inicial delimita apenas a auditoria da janela "
                "canonical-first; ela nao altera a forma de gravacao das baixas."
            ),
        },
        "featureFlagValidation": validacao["featureFlagValidation"],
        "activationDecision": validacao.get("activationDecision") or {},
        "nextAction": validacao.get("nextAction") or {},
        "operationalGate": validacao.get("operationalGate") or {},
        "sequencePosition": validacao.get("sequencePosition") or {},
        "pendingObligations": validacao["activation"]["pendingObligations"],
        "candidateListHealth": validacao.get("candidateListHealth") or {},
        "operationalPreflight": validacao["operationalPreflight"],
        "writeAudit": auditoria,
        "windowOutcome": outcome,
        "requiresCanonicalFirst": exigir_canonical_first,
        "failsOnLegacyInWindow": falhar_com_legado_na_janela,
        "requiresActivationDate": exigir_data_ativacao,
        "issues": issues,
    }


def formatar_erro_monitoramento_nao_aprovado(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Monitoramento canonical-first nao aprovado: {issues[0]}"
    return "Monitoramento canonical-first nao aprovado."


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias", "")
    save_json = options.get("salvar_json", "")
    save_record = options.get("salvar_registro", "")

    if directory:
        base_path = Path(directory).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError(
                "--diretorio-evidencias deve apontar para um diretorio"
            )
        if not save_json:
            save_json = str(base_path / "pm03-monitor-canonical-first.json")
        if not save_record:
            save_record = str(base_path / "pm03-monitor-canonical-first.md")

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


def _salvar_evidencias_monitoramento(resultado):
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


def _registro_monitoramento_pm03(resultado):
    auditoria = resultado["writeAudit"]
    pendencias = resultado["pendingObligations"]
    periodo = resultado["period"]
    gate = resultado.get("operationalGate") or {}
    sequence_position = resultado.get("sequencePosition") or {}
    candidate_list_health = resultado.get("candidateListHealth") or {}
    issues = "; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"
    evidence_files = resultado.get("evidenceFiles") or {}
    evidence_summary = (
        f"diretorio={evidence_files.get('directory') or '-'}; "
        f"json={evidence_files.get('json') or '-'}; "
        f"registro={evidence_files.get('record') or '-'}"
    )

    return "\n".join(
        [
            "### Registro PM-03 - monitoramento canonical-first",
            "",
            f"Data/hora do monitoramento: {resultado['generatedAt']}",
            f"Origem: {resultado['source']}",
            (
                "Periodo monitorado: "
                f"{periodo['startDate'] or '-'} a {periodo['endDate'] or '-'}"
            ),
            (
                "Feature flag ativa para origem: "
                f"{resultado['featureFlagValidation']['activeForSource']}"
            ),
            (
                "Pre-flight operacional pronto: "
                f"{resultado['operationalPreflight']['ready']}"
            ),
            (
                "Baixas na janela: "
                f"total={auditoria['count']}; "
                f"canonicalFirst={auditoria['canonicalFirst']['count']} "
                f"valor={auditoria['canonicalFirst']['outflowAmount']:.2f}; "
                f"legacyAdapterSynced={auditoria['legacyAdapterSynced']['count']} "
                f"valor={auditoria['legacyAdapterSynced']['outflowAmount']:.2f}"
            ),
            (
                "Pendencias: "
                f"total={pendencias['count']}; "
                f"a pagar={pendencias['payableCount']}; "
                f"a receber={pendencias['receivableCount']}; "
                f"canario={pendencias['canaryEligibleCount']}"
            ),
            (
                "Lista candidatos: "
                f"status={candidate_list_health.get('status') or '-'}; "
                f"retornados={candidate_list_health.get('returnedCount')}; "
                f"elegiveis={candidate_list_health.get('eligibleCount')}; "
                f"acao={candidate_list_health.get('recommendedAction') or '-'}"
            ),
            f"Candidatos canario: {_resumir_candidatos_canario(pendencias)}",
            f"Pendencias sem canario: {resumir_pendencias_sem_canario(pendencias)}",
            (
                "Proxima acao: "
                f"{(resultado.get('nextAction') or {}).get('key') or '-'}; "
                f"{(resultado.get('nextAction') or {}).get('detail') or '-'}"
            ),
            (
                "Decisao ativacao: "
                f"status={(resultado.get('activationDecision') or {}).get('status') or '-'}; "
                "mayRunCanaryRollbackOnly="
                f"{(resultado.get('activationDecision') or {}).get('mayRunCanaryRollbackOnly')}; "
                "mayActivateAllowlistWindow="
                f"{(resultado.get('activationDecision') or {}).get('mayActivateAllowlistWindow')}; "
                "requiresControlledCandidate="
                f"{(resultado.get('activationDecision') or {}).get('requiresControlledCandidate')}"
            ),
            (
                "Resultado da janela: "
                f"{(resultado.get('windowOutcome') or {}).get('status') or '-'}; "
                f"{(resultado.get('windowOutcome') or {}).get('detail') or '-'}"
            ),
            (
                "Nota nextAction: "
                f"{(resultado.get('windowOutcome') or {}).get('nextActionNote') or '-'}"
            ),
            (
                "Gate operacional: "
                f"step={gate.get('currentStep') or '-'}; "
                f"status={gate.get('status') or '-'}; "
                f"{gate.get('statusLabel') or '-'}"
            ),
            (
                "Sequencia PM-03: "
                f"position={sequence_position.get('position') or '-'}/"
                f"{sequence_position.get('totalDirectSteps') or '-'}; "
                f"previous={sequence_position.get('previousStep') or '-'}; "
                f"current={sequence_position.get('step') or '-'}; "
                f"next={sequence_position.get('nextStep') or '-'}; "
                f"nextSource={sequence_position.get('nextSource') or '-'}"
            ),
            f"requiresCanonicalFirst: {resultado['requiresCanonicalFirst']}",
            f"failsOnLegacyInWindow: {resultado['failsOnLegacyInWindow']}",
            f"requiresActivationDate: {resultado['requiresActivationDate']}",
            f"ready/issues: ready={resultado['ready']}; issues={issues}",
            f"Arquivos salvos: {evidence_summary}",
            (
                f"Decisao: manter `{resultado['source']}` na allowlist "
                "somente se ready=True apos revisoes."
            ),
        ]
    )


def _resumir_candidatos_canario(pendencias):
    candidatos = pendencias.get("canaryCandidates") or []
    if not candidatos:
        return "-"
    return "; ".join(
        (
            f"sourceId={candidato['sourceId']} "
            f"obrigacao={candidato['obligationId']} "
            f"pendente={candidato['pendingAmount']} "
            f"vencimento={candidato['dueDate']}"
        )
        for candidato in candidatos
    )
