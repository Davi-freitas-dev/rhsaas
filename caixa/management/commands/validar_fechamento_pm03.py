import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.constants_financeiros import STATUS_REALIZADO, TIPO_FLUXO_SAIDA
from caixa.pm03_sequence import SOURCE_PM03_STEPS, montar_posicao_sequencia_pm03


class Command(BaseCommand):
    help = (
        "Valida o fechamento documental da PM-03 por origem lendo os artefatos "
        "JSON gerados pela validacao, monitoramento e auditorias da janela."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument(
            "--data-inicial",
            "--data-ativacao",
            dest="data_inicial",
            default="",
            help="Data inicial esperada para a janela PM-03.",
        )
        parser.add_argument(
            "--data-final",
            dest="data_final",
            default="",
            help="Data final esperada para a janela PM-03.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help="Diretorio com os JSONs de evidencia PM-03 da origem.",
        )
        parser.add_argument("--validacao-janela-json", default="")
        parser.add_argument("--validacao-ativacao-json", default="")
        parser.add_argument("--monitor-json", default="")
        parser.add_argument("--auditoria-fonte-json", default="")
        parser.add_argument("--auditoria-totais-json", default="")
        parser.add_argument("--candidatos-canario-json", default="")
        parser.add_argument("--regressao-dividas-json", default="")
        parser.add_argument(
            "--exigir-validacao-ativacao",
            action="store_true",
            help=(
                "Exige e valida o artefato de pre-window gerado por "
                "validar_ativacao_canonical_first."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o fechamento em JSON para automacoes.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON do fechamento PM-03 em arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown do fechamento PM-03 em arquivo.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando o fechamento PM-03 nao estiver aprovado.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        output_files = _normalizar_arquivos_saida(options)
        resultado = validar_fechamento_pm03(
            source=options["source"],
            evidence_files=evidence_files,
            output_files=output_files,
            data_inicial=options.get("data_inicial"),
            data_final=options.get("data_final"),
            exigir_validacao_ativacao=(
                options["exigir_validacao_ativacao"]
                or bool(options.get("validacao_ativacao_json"))
            ),
        )
        _salvar_evidencias_fechamento(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_fechamento_pm03(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(self.style.SUCCESS("Fechamento PM-03 aprovado."))
        else:
            self.stdout.write(
                self.style.WARNING("Fechamento PM-03 com pendencias.")
            )
        self.stdout.write(f"Origem: {resultado['source']}")
        decision = resultado.get("closureDecision") or {}
        gate_summary = resultado.get("operationalGateSummary") or {}
        sequence_summary = resultado.get("sequencePositionSummary") or {}
        outcome_summary = resultado.get("windowOutcomeSummary") or {}
        audit_summary = resultado.get("windowWriteAuditSummary") or {}
        activation_canary_summary = resultado.get("activationCanarySummary") or {}
        candidate_summary = resultado.get("candidateActivationSummary") or {}
        list_health_summary = resultado.get("candidateListHealthSummary") or {}
        debt_regression_summary = resultado.get("debtRegressionSummary") or {}
        evidence_checklist = resultado.get("evidenceChecklist") or {}
        checks_summary = resultado.get("checksSummary") or {}
        missing_actions = resultado.get("missingEvidenceActions") or {}
        recommended_commands = resultado.get("recommendedCommands") or {}
        next_action = resultado.get("closureNextAction") or {}
        sequence_transition = resultado.get("sequenceTransition") or {}
        sequence_position = resultado.get("sequencePosition") or {}
        self.stdout.write(
            "Proxima acao fechamento: "
            f"key={next_action.get('key') or '-'}; "
            f"status={next_action.get('status') or '-'}; "
            f"nextStep={next_action.get('nextStep') or '-'}; "
            f"nextSource={next_action.get('nextSource') or '-'}; "
            f"evidence={next_action.get('evidenceKey') or '-'}"
        )
        self.stdout.write(
            "Comandos recomendados: "
            f"nextEvidence={recommended_commands.get('nextMissingEvidence') or '-'}; "
            f"followUp={recommended_commands.get('followUp') or '-'}; "
            f"rerunClosure={recommended_commands.get('rerunClosure') or '-'}; "
            f"nextSequence={recommended_commands.get('nextSequenceValidation') or '-'}"
        )
        self.stdout.write(
            "Transicao da sequencia: "
            f"type={sequence_transition.get('type') or '-'}; "
            f"status={sequence_transition.get('status') or '-'}; "
            f"from={sequence_transition.get('fromStep') or '-'}; "
            f"to={sequence_transition.get('toStep') or '-'}; "
            f"toSource={sequence_transition.get('toSource') or '-'}"
        )
        self.stdout.write(
            "Transicao operacional: "
            f"primary={sequence_transition.get('primaryCommand') or '-'}; "
            f"followUp={sequence_transition.get('followUpCommand') or '-'}; "
            f"checklistReady={sequence_transition.get('reviewChecklistReady')}"
        )
        self.stdout.write(
            "Decisao PM-03: "
            f"status={decision.get('status') or '-'}; "
            f"step={decision.get('step') or '-'}; "
            f"mayMarkCurrentStepDone={decision.get('mayMarkCurrentStepDone')}; "
            f"mayAdvanceSequence={decision.get('mayAdvanceSequence')}; "
            f"nextStep={decision.get('nextStep') or '-'}; "
            f"nextSource={decision.get('nextSource') or '-'}; "
            f"blockedBy={'; '.join(decision.get('blockedBy') or []) or '-'}"
        )
        self.stdout.write(
            "Sequencia PM-03: "
            f"position={sequence_position.get('position') or '-'}"
            f"/{sequence_position.get('totalDirectSteps') or '-'}; "
            f"previous={sequence_position.get('previousStep') or '-'}; "
            f"current={sequence_position.get('step') or '-'}; "
            f"next={sequence_position.get('nextStep') or '-'}"
        )
        self.stdout.write(
            "Sequencia nas evidencias: "
            f"available={sequence_summary.get('available')}; "
            f"steps={','.join(sequence_summary.get('steps') or []) or '-'}; "
            f"positions={','.join(str(item) for item in (sequence_summary.get('positions') or [])) or '-'}; "
            f"consistent={sequence_summary.get('consistent')}; "
            f"matchesExpected={sequence_summary.get('matchesExpected')}"
        )
        self.stdout.write(
            "Gate operacional: "
            f"available={gate_summary.get('available')}; "
            f"steps={','.join(gate_summary.get('currentSteps') or []) or '-'}; "
            f"sources={','.join(gate_summary.get('sources') or []) or '-'}; "
            f"consistentStep={gate_summary.get('consistentStep')}; "
            f"consistentSource={gate_summary.get('consistentSource')}"
        )
        self.stdout.write(
            "Canario de ativacao: "
            f"available={activation_canary_summary.get('available')}; "
            f"executed={activation_canary_summary.get('executed')}; "
            f"synced={activation_canary_summary.get('synced')}; "
            f"sourceId={activation_canary_summary.get('sourceId') or '-'}; "
            f"paymentDate={activation_canary_summary.get('paymentDate') or '-'}; "
            f"matchesActivationDate={activation_canary_summary.get('matchesActivationDate')}"
        )
        self.stdout.write(
            "Candidato x ativacao: "
            f"available={candidate_summary.get('available')}; "
            f"consistent={candidate_summary.get('consistent')}; "
            f"activationSourceId={candidate_summary.get('activationSourceId') or '-'}; "
            f"activationObligationId={candidate_summary.get('activationObligationId') or '-'}"
        )
        self.stdout.write(
            "Saude da lista de candidatos: "
            f"available={list_health_summary.get('available')}; "
            f"statuses={','.join(list_health_summary.get('statuses') or []) or '-'}; "
            f"requiresLimitIncrease={list_health_summary.get('requiresLimitIncrease')}"
        )
        self.stdout.write(
            "Regressao de dividas: "
            f"available={debt_regression_summary.get('available')}; "
            f"status={debt_regression_summary.get('status') or '-'}; "
            f"mayContinuePm03_4={debt_regression_summary.get('mayContinuePm03_4')}"
        )
        self.stdout.write(
            "Resultado da janela: "
            f"available={outcome_summary.get('available')}; "
            f"statuses={','.join(outcome_summary.get('statuses') or []) or '-'}; "
            f"consistentStatus={outcome_summary.get('consistentStatus')}"
        )
        self.stdout.write(
            "Auditoria da janela: "
            f"available={audit_summary.get('available')}; "
            f"consistentCounts={audit_summary.get('consistentCounts')}"
        )
        self.stdout.write(
            "Checklist de evidencias: "
            f"ready={evidence_checklist.get('ready')}; "
            f"required={evidence_checklist.get('requiredCount')}; "
            f"missingRequired={evidence_checklist.get('missingRequiredCount')}"
        )
        self.stdout.write(
            "Resumo checks: "
            f"ready={checks_summary.get('ready')}; "
            f"ok={checks_summary.get('okCount')}; "
            f"pendentes={checks_summary.get('pendingCount')}; "
            f"pendingKeys={','.join(checks_summary.get('pending') or []) or '-'}"
        )
        self.stdout.write(
            "Acoes para evidencias faltantes: "
            f"ready={missing_actions.get('ready')}; "
            f"missing={missing_actions.get('missingCount')}; "
            f"next={((missing_actions.get('nextAction') or {}).get('key')) or '-'}; "
            f"rerun={missing_actions.get('rerunClosureCommand') or '-'}"
        )
        for item in missing_actions.get("items") or []:
            self.stdout.write(f"- {item['key']}: {item['command']}")
        issues = resultado.get("issues") or []
        if issues:
            self.stdout.write("Issues de fechamento:")
            for issue in issues:
                self.stdout.write(f"- {issue}")
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_fechamento_pm03(
    source,
    evidence_files,
    output_files=None,
    data_inicial="",
    data_final="",
    exigir_validacao_ativacao=False,
):
    output_files = output_files or {}
    sequence_position = montar_posicao_sequencia_pm03(source)
    evidence_checklist = montar_checklist_evidencias_fechamento(
        source=source,
        evidence_files=evidence_files,
        exigir_validacao_ativacao=exigir_validacao_ativacao,
    )
    checks = [
        _validar_evidencia_validacao_janela(
            source,
            evidence_files,
            data_inicial=data_inicial,
            data_final=data_final,
        ),
        _validar_evidencia_monitoramento(
            source,
            evidence_files,
            data_inicial=data_inicial,
            data_final=data_final,
        ),
        _validar_evidencia_auditoria_fonte(
            source,
            evidence_files,
            data_inicial=data_inicial,
            data_final=data_final,
        ),
        _validar_evidencia_auditoria_totais(evidence_files),
    ]
    if _deve_validar_evidencia_candidatos_canario(source, evidence_files):
        checks.insert(
            0,
            _validar_evidencia_candidatos_canario(source, evidence_files),
        )
    if _deve_validar_evidencia_regressao_dividas(source, evidence_files):
        checks.insert(
            -1,
            _validar_evidencia_regressao_dividas(source, evidence_files),
        )
    if _deve_validar_evidencia_ativacao(
        evidence_files,
        required=exigir_validacao_ativacao,
    ):
        checks.insert(
            0,
            _validar_evidencia_validacao_ativacao(
                source,
                evidence_files,
                data_inicial=data_inicial if exigir_validacao_ativacao else "",
                required=exigir_validacao_ativacao,
            ),
        )
    candidate_activation_summary = resumir_candidato_ativacao_fechamento(
        evidence_files
    )
    if candidate_activation_summary["available"]:
        checks.append(
            _validar_consistencia_candidato_ativacao(candidate_activation_summary)
        )
    checks_summary = resumir_checks_fechamento(checks)
    missing_evidence_actions = montar_acoes_evidencias_faltantes_fechamento(
        source=source,
        evidence_files=evidence_files,
        evidence_checklist=evidence_checklist,
        data_inicial=data_inicial,
        data_final=data_final,
        exigir_validacao_ativacao=exigir_validacao_ativacao,
    )
    issues = [
        issue
        for check in checks
        for issue in check["issues"]
    ]
    gate_summary = resumir_gate_operacional_fechamento(evidence_files)
    if gate_summary["available"] and not gate_summary["consistentStep"]:
        issues.append("gate operacional inconsistente entre evidencias")
    if gate_summary["available"] and not gate_summary["consistentSource"]:
        issues.append("origem do gate operacional inconsistente entre evidencias")
    sequence_summary = resumir_posicao_sequencia_fechamento(evidence_files)
    expected_sequence_issues = []
    if sequence_summary["available"] and not sequence_summary["consistent"]:
        issues.append("posicao da sequencia PM-03 inconsistente entre evidencias")
    if sequence_summary["available"] and sequence_summary["consistent"]:
        expected_sequence_issues = _coletar_issues_posicao_sequencia_esperada(
            sequence_summary,
            sequence_position,
        )
        issues.extend(expected_sequence_issues)
    sequence_summary["expected"] = _resumir_posicao_sequencia_esperada(
        sequence_position
    )
    sequence_summary["matchesExpected"] = None
    if sequence_summary["available"] and sequence_summary["consistent"]:
        sequence_summary["matchesExpected"] = not expected_sequence_issues
    sequence_summary["expectedIssues"] = expected_sequence_issues
    window_outcome_summary = resumir_resultado_janela_fechamento(evidence_files)
    if (
        window_outcome_summary["available"]
        and not window_outcome_summary["consistentStatus"]
    ):
        issues.append("resultado da janela inconsistente entre evidencias")
    window_audit_summary = resumir_auditoria_janela_fechamento(evidence_files)
    if (
        window_audit_summary["available"]
        and not window_audit_summary["consistentCounts"]
    ):
        issues.append("auditoria da janela inconsistente entre evidencias")
    activation_canary_summary = resumir_canario_ativacao_fechamento(
        evidence_files,
        data_inicial=data_inicial,
    )
    candidate_list_health_summary = resumir_saude_lista_candidatos_fechamento(
        evidence_files
    )
    debt_regression_summary = resumir_regressao_dividas_fechamento(evidence_files)
    resultado = {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "ready": not issues,
        "source": source,
        "period": {
            "startDate": data_inicial or "",
            "endDate": data_final or "",
        },
        "checks": checks,
        "issues": issues,
        "operationalGateSummary": gate_summary,
        "sequencePositionSummary": sequence_summary,
        "windowOutcomeSummary": window_outcome_summary,
        "windowWriteAuditSummary": window_audit_summary,
        "activationCanarySummary": activation_canary_summary,
        "candidateActivationSummary": candidate_activation_summary,
        "candidateListHealthSummary": candidate_list_health_summary,
        "debtRegressionSummary": debt_regression_summary,
        "checksSummary": checks_summary,
        "missingEvidenceActions": missing_evidence_actions,
        "evidenceChecklist": evidence_checklist,
        "sequencePosition": sequence_position,
        "inputEvidenceFiles": evidence_files,
        "outputEvidenceFiles": output_files,
        "requiresActivationValidation": exigir_validacao_ativacao,
    }
    resultado["closureDecision"] = montar_decisao_fechamento_pm03(
        source=source,
        ready=resultado["ready"],
        issues=issues,
        sequence_position=sequence_position,
    )
    resultado["closureNextAction"] = montar_proxima_acao_fechamento_pm03(
        source=source,
        ready=resultado["ready"],
        issues=issues,
        closure_decision=resultado["closureDecision"],
        sequence_position=sequence_position,
        missing_evidence_actions=missing_evidence_actions,
        checks_summary=checks_summary,
    )
    resultado["recommendedCommands"] = montar_comandos_recomendados_fechamento_pm03(
        missing_evidence_actions=missing_evidence_actions,
        closure_next_action=resultado["closureNextAction"],
    )
    resultado["sequenceTransition"] = montar_transicao_sequencia_fechamento_pm03(
        source=source,
        sequence_position=sequence_position,
        closure_next_action=resultado["closureNextAction"],
        recommended_commands=resultado["recommendedCommands"],
        ready=resultado["ready"],
    )
    resultado["executionRecord"] = {
        "format": "markdown",
        "markdown": _registro_fechamento_pm03(resultado),
    }
    return resultado


def montar_comandos_recomendados_fechamento_pm03(
    missing_evidence_actions=None,
    closure_next_action=None,
):
    missing_evidence_actions = missing_evidence_actions or {}
    closure_next_action = closure_next_action or {}
    missing_next = missing_evidence_actions.get("nextAction") or {}
    return {
        "nextMissingEvidence": missing_next.get("command") or "",
        "followUp": (
            closure_next_action.get("followUpCommand")
            or missing_next.get("followUpCommand")
            or ""
        ),
        "rerunClosure": missing_evidence_actions.get("rerunClosureCommand") or "",
        "closureNextAction": closure_next_action.get("key") or "",
        "nextSequenceValidation": _comando_validar_proxima_origem_pm03(
            closure_next_action
        ),
    }


def _comando_validar_proxima_origem_pm03(closure_next_action):
    closure_next_action = closure_next_action or {}
    if closure_next_action.get("key") != "advanceToNextSource":
        return ""
    next_source = str(closure_next_action.get("nextSource") or "").strip()
    if not next_source:
        return ""
    evidence_dir = _diretorio_evidencias_placeholder_pm03(next_source)
    return (
        "python manage.py validar_ativacao_canonical_first "
        f"--source={next_source} "
        f"--diretorio-evidencias={evidence_dir} "
        "--exigir-arquivos-evidencia --json --falhar"
    )


def montar_transicao_sequencia_fechamento_pm03(
    source,
    sequence_position=None,
    closure_next_action=None,
    recommended_commands=None,
    ready=False,
):
    sequence_position = sequence_position or montar_posicao_sequencia_pm03(source)
    closure_next_action = closure_next_action or {}
    recommended_commands = recommended_commands or {}
    action_key = closure_next_action.get("key") or ""
    if not ready:
        transition_type = "blocked"
        status = "blocked"
    elif action_key == "advanceToNextSource":
        transition_type = "nextSource"
        status = "ready"
    elif action_key == "advanceToNextPhase":
        transition_type = "nextPhase"
        status = "ready"
    else:
        transition_type = action_key or "unknown"
        status = closure_next_action.get("status") or "blocked"
    primary_command = _comando_primario_transicao_pm03(
        transition_type=transition_type,
        closure_next_action=closure_next_action,
        recommended_commands=recommended_commands,
    )
    follow_up_command = (
        closure_next_action.get("followUpCommand")
        or recommended_commands.get("followUp")
        or ""
    )
    review_checklist = _montar_checklist_revisao_transicao_pm03(
        ready=ready,
        closure_next_action=closure_next_action,
        sequence_position=sequence_position,
    )
    return {
        "type": transition_type,
        "status": status,
        "source": source,
        "actionKey": action_key,
        "actionLabel": closure_next_action.get("label") or "",
        "detail": closure_next_action.get("detail") or "",
        "blockingIssue": closure_next_action.get("blockingIssue") or "",
        "primaryCommand": primary_command,
        "followUpCommand": follow_up_command,
        "fromStep": sequence_position.get("step") or "",
        "fromSource": sequence_position.get("source") or source,
        "fromLabel": sequence_position.get("label") or "",
        "toStep": closure_next_action.get("nextStep") or "",
        "toSource": closure_next_action.get("nextSource") or "",
        "toLabel": closure_next_action.get("nextLabel") or "",
        "directCanonicalFirstSequenceComplete": bool(
            closure_next_action.get("directCanonicalFirstSequenceComplete")
        ),
        "mayMarkCurrentStepDone": bool(
            closure_next_action.get("mayMarkCurrentStepDone")
        ),
        "mayAdvanceSequence": bool(closure_next_action.get("mayAdvanceSequence")),
        "mayStartNextStep": bool(closure_next_action.get("mayStartNextStep")),
        "nextSequenceValidationCommand": (
            recommended_commands.get("nextSequenceValidation") or ""
        ),
        "requiresOperationalReview": True,
        "reviewChecklist": review_checklist,
        "reviewChecklistReady": all(
            bool(item.get("ok")) for item in review_checklist
            if item.get("required")
        ),
        "reviewLabel": (
            "Revisoes obrigatorias antes de marcar a subetapa como concluida."
        ),
    }


def _comando_primario_transicao_pm03(
    transition_type,
    closure_next_action=None,
    recommended_commands=None,
):
    closure_next_action = closure_next_action or {}
    recommended_commands = recommended_commands or {}
    explicit_command = closure_next_action.get("command") or ""
    if explicit_command:
        return explicit_command
    if transition_type == "nextSource":
        return recommended_commands.get("nextSequenceValidation") or ""
    if transition_type == "blocked":
        return (
            recommended_commands.get("nextMissingEvidence")
            or recommended_commands.get("followUp")
            or ""
        )
    return recommended_commands.get("followUp") or ""


def _montar_checklist_revisao_transicao_pm03(
    ready=False,
    closure_next_action=None,
    sequence_position=None,
):
    closure_next_action = closure_next_action or {}
    sequence_position = sequence_position or {}
    may_start_next_step = bool(closure_next_action.get("mayStartNextStep"))
    return [
        {
            "key": "closureApproved",
            "label": "Fechamento PM-03 aprovado",
            "required": True,
            "ok": bool(ready),
        },
        {
            "key": "evidenceReview",
            "label": "Revisoes obrigatorias conferidas",
            "required": True,
            "ok": bool(ready),
        },
        {
            "key": "markCurrentStepDone",
            "label": "Marcar subetapa atual como concluida",
            "required": True,
            "ok": bool(closure_next_action.get("mayMarkCurrentStepDone")),
            "step": sequence_position.get("step") or "",
            "source": sequence_position.get("source") or "",
        },
        {
            "key": "advanceSequence",
            "label": "Avancar a sequencia planejada",
            "required": True,
            "ok": bool(closure_next_action.get("mayAdvanceSequence")),
            "nextStep": closure_next_action.get("nextStep") or "",
            "nextSource": closure_next_action.get("nextSource") or "",
        },
        {
            "key": "startNextStep",
            "label": "Iniciar a proxima subetapa/fase",
            "required": bool(closure_next_action.get("nextStep")),
            "ok": may_start_next_step,
            "nextStep": closure_next_action.get("nextStep") or "",
            "nextSource": closure_next_action.get("nextSource") or "",
        },
    ]


def montar_proxima_acao_fechamento_pm03(
    source,
    ready,
    issues=None,
    closure_decision=None,
    sequence_position=None,
    missing_evidence_actions=None,
    checks_summary=None,
):
    issues = [str(issue) for issue in (issues or []) if str(issue)]
    closure_decision = closure_decision or {}
    sequence_position = sequence_position or montar_posicao_sequencia_pm03(source)
    missing_evidence_actions = missing_evidence_actions or {}
    checks_summary = checks_summary or {}
    step = SOURCE_PM03_STEPS.get(source, "")
    missing_next = missing_evidence_actions.get("nextAction") or {}
    if missing_next:
        return {
            "key": "generateMissingEvidence",
            "status": "blocked",
            "label": "Gerar evidencia obrigatoria faltante",
            "source": source,
            "step": step,
            "evidenceKey": missing_next.get("key") or "",
            "expectedFile": missing_next.get("expectedFile") or "",
            "command": missing_next.get("command") or "",
            "followUpCommand": missing_next.get("followUpCommand") or "",
            "pendingChecks": checks_summary.get("pending") or [],
            "blockingIssue": issues[0] if issues else "",
            "nextStep": sequence_position.get("nextStep") or "",
            "nextSource": sequence_position.get("nextSource") or "",
            "mayMarkCurrentStepDone": False,
            "mayAdvanceSequence": False,
            "mayStartNextStep": False,
            "detail": (
                "Gerar a primeira evidencia obrigatoria ausente antes de "
                "reexecutar o fechamento PM-03."
            ),
        }
    if not ready:
        follow_up = missing_evidence_actions.get("rerunClosureCommand") or ""
        return {
            "key": "resolveClosureIssues",
            "status": "blocked",
            "label": "Resolver pendencias do fechamento",
            "source": source,
            "step": step,
            "evidenceKey": "",
            "expectedFile": "",
            "command": "",
            "followUpCommand": follow_up,
            "pendingChecks": checks_summary.get("pending") or [],
            "blockingIssue": issues[0] if issues else "",
            "nextStep": sequence_position.get("nextStep") or "",
            "nextSource": sequence_position.get("nextSource") or "",
            "mayMarkCurrentStepDone": False,
            "mayAdvanceSequence": False,
            "mayStartNextStep": False,
            "detail": (
                "Corrigir as issues do fechamento antes de marcar a subetapa "
                "como concluida."
            ),
        }
    sequence_complete = bool(
        sequence_position.get("directCanonicalFirstSequenceComplete")
    )
    key = "advanceToNextPhase" if sequence_complete else "advanceToNextSource"
    label = (
        "Avancar para a proxima fase"
        if sequence_complete
        else "Avancar para a proxima origem"
    )
    return {
        "key": key,
        "status": "ready",
        "label": label,
        "source": source,
        "step": step,
        "evidenceKey": "",
        "expectedFile": "",
        "command": "",
        "followUpCommand": "",
        "pendingChecks": [],
        "blockingIssue": "",
        "nextStep": closure_decision.get("nextStep") or "",
        "nextSource": closure_decision.get("nextSource") or "",
        "nextLabel": closure_decision.get("nextLabel") or "",
        "mayMarkCurrentStepDone": True,
        "mayAdvanceSequence": True,
        "mayStartNextStep": bool(closure_decision.get("mayStartNextStep")),
        "directCanonicalFirstSequenceComplete": sequence_complete,
        "detail": (
            "Fechamento aprovado; marcar a subetapa como concluida e seguir a "
            "sequencia planejada."
        ),
    }


def resumir_checks_fechamento(checks):
    checks = checks or []
    by_key = {}
    ok = []
    pending = []
    for check in checks:
        key = str(check.get("key") or "")
        issues = list(check.get("issues") or [])
        item = {
            "key": key,
            "label": check.get("label") or "",
            "ok": bool(check.get("ok")),
            "issues": issues,
            "issueCount": len(issues),
        }
        by_key[key] = item
        if item["ok"]:
            ok.append(key)
        else:
            pending.append(key)
    pending_count = len(pending)
    return {
        "ready": pending_count == 0,
        "total": len(checks),
        "okCount": len(ok),
        "pendingCount": pending_count,
        "ok": ok,
        "pending": pending,
        "byKey": by_key,
    }


def montar_acoes_evidencias_faltantes_fechamento(
    source,
    evidence_files,
    evidence_checklist,
    data_inicial="",
    data_final="",
    exigir_validacao_ativacao=False,
):
    evidence_files = evidence_files or {}
    evidence_checklist = evidence_checklist or {}
    rerun_closure_command = montar_comando_reexecutar_fechamento_pm03(
        source=source,
        evidence_files=evidence_files,
        data_inicial=data_inicial,
        data_final=data_final,
        exigir_validacao_ativacao=exigir_validacao_ativacao,
    )
    items_by_key = {
        item.get("key"): item
        for item in evidence_checklist.get("items") or []
    }
    actions = []
    for key in evidence_checklist.get("missingRequired") or []:
        checklist_item = items_by_key.get(key) or {}
        command = _comando_evidencia_faltante_pm03(
            key=key,
            source=source,
            evidence_files=evidence_files,
            data_inicial=data_inicial,
            data_final=data_final,
            exigir_validacao_ativacao=exigir_validacao_ativacao,
        )
        actions.append(
            {
                "key": key,
                "label": checklist_item.get("label") or key,
                "kind": "command",
                "expectedFile": checklist_item.get("path") or "",
                "command": command,
                "followUpCommand": rerun_closure_command,
            }
        )
    return {
        "ready": not actions,
        "source": source,
        "step": SOURCE_PM03_STEPS.get(source, ""),
        "missingCount": len(actions),
        "items": actions,
        "byKey": {item["key"]: item for item in actions},
        "nextAction": actions[0] if actions else {},
        "rerunClosureCommand": rerun_closure_command,
    }


def montar_comando_reexecutar_fechamento_pm03(
    source,
    evidence_files,
    data_inicial="",
    data_final="",
    exigir_validacao_ativacao=False,
):
    evidence_files = evidence_files or {}
    args = [
        "python manage.py validar_fechamento_pm03",
        f"--source={source}",
    ]
    if data_inicial:
        args.append(f"--data-inicial={data_inicial}")
    if data_final:
        args.append(f"--data-final={data_final}")
    directory = evidence_files.get("directory") or ""
    if directory:
        args.append(f"--diretorio-evidencias={directory}")
    explicit_paths = [
        ("validacao-janela-json", "windowValidation", True),
        (
            "validacao-ativacao-json",
            "activationValidation",
            bool(exigir_validacao_ativacao),
        ),
        (
            "candidatos-canario-json",
            "candidateDiscovery",
            source == "financiamento_movimentacao",
        ),
        (
            "regressao-dividas-json",
            "debtRegression",
            source == "financiamento_movimentacao",
        ),
    ]
    for option, key, include in explicit_paths:
        path = evidence_files.get(key) or ""
        if include and path:
            args.append(f"--{option}={path}")
    if exigir_validacao_ativacao:
        args.append("--exigir-validacao-ativacao")
    args.extend(["--json", "--falhar"])
    return " ".join(args)


def _comando_evidencia_faltante_pm03(
    key,
    source,
    evidence_files,
    data_inicial="",
    data_final="",
    exigir_validacao_ativacao=False,
):
    evidence_dir = _diretorio_evidencias_ou_placeholder(source, evidence_files)
    data_args = _periodo_args_fechamento(data_inicial or "DATA_DA_ATIVACAO", data_final)
    if key == "activationValidation":
        return (
            "python manage.py validar_ativacao_canonical_first "
            f"--source={source} --username=<usuario> "
            "--source-id=<sourceId-de-canaryCandidates> --payment-date=<DATA> "
            "--executar-canario --exigir-canario --exigir-source-id-canario "
            "--exigir-data-pagamento-canario "
            f"--diretorio-evidencias={evidence_dir} --exigir-arquivos-evidencia "
            "--json --falhar"
        )
    if key == "candidateDiscovery":
        return (
            "python manage.py listar_candidatos_canario_pm03 "
            f"--source={source} --username=<usuario> --payment-date=<DATA> "
            f"--diretorio-evidencias={evidence_dir} --exigir-arquivos-evidencia "
            "--json --falhar"
        )
    if key == "windowValidation":
        return (
            "python manage.py validar_janela_canonical_first "
            f"--source={source}{data_args} --validar-preflight-operacional "
            "--falhar-com-preflight-operacional --exigir-baixa-canonical-first "
            "--exigir-data-ativacao "
            f"--diretorio-evidencias={evidence_dir} --exigir-arquivos-evidencia "
            "--json --falhar"
        )
    if key == "monitor":
        return (
            "python manage.py monitorar_janela_canonical_first "
            f"--source={source}{data_args} --exigir-canonical-first "
            "--falhar-com-legado-na-janela --exigir-data-ativacao "
            f"--diretorio-evidencias={evidence_dir} --exigir-arquivos-evidencia "
            "--json --falhar"
        )
    if key == "sourceAudit":
        return (
            "python manage.py auditar_fonte_escrita_baixas "
            f"--source={source}{data_args} --write-model-source=canonicalFirst "
            "--exigir-canonical-first --exigir-data-ativacao "
            f"--diretorio-evidencias={evidence_dir} --exigir-arquivos-evidencia "
            "--json"
        )
    if key == "debtRegression":
        return (
            "python manage.py validar_regressao_dividas_pm03 "
            f"--source={source} --diretorio-evidencias={evidence_dir} "
            "--exigir-arquivos-evidencia --json --falhar"
        )
    if key == "totalsAudit":
        return (
            "python manage.py auditar_totais_negocio --falhar-com-divergencia "
            "--validar-valores-editaveis --falhar-com-valores-editaveis "
            f"--diretorio-evidencias={evidence_dir} --exigir-arquivos-evidencia "
            "--json"
        )
    return ""


def _periodo_args_fechamento(data_inicial="", data_final=""):
    args = []
    if data_inicial:
        args.append(f"--data-inicial={data_inicial}")
    if data_final:
        args.append(f"--data-final={data_final}")
    return (" " + " ".join(args)) if args else ""


def _diretorio_evidencias_ou_placeholder(source, evidence_files):
    directory = (evidence_files or {}).get("directory") or ""
    if directory:
        return directory
    return _diretorio_evidencias_placeholder_pm03(source)


def _diretorio_evidencias_placeholder_pm03(source):
    slug = str(source or "origem").strip().replace("_", "-") or "origem"
    return f"<diretorio-evidencias-pm03-{slug}>"


def montar_decisao_fechamento_pm03(
    source,
    ready,
    issues=None,
    sequence_position=None,
):
    step = SOURCE_PM03_STEPS.get(source, "")
    sequence_position = sequence_position or montar_posicao_sequencia_pm03(source)
    blocked_by = [str(issue) for issue in (issues or []) if str(issue)]
    if ready:
        detail = (
            "Evidencias obrigatorias aprovadas; marcar a subetapa da origem "
            "como concluida e seguir a sequencia planejada."
        )
        status = "approved"
        label = "Fechamento PM-03 aprovado"
    else:
        detail = (
            "Nao marcar a subetapa como concluida; resolver as pendencias do "
            "fechamento antes de avancar."
        )
        status = "blocked"
        label = "Fechamento PM-03 bloqueado"
    return {
        "status": status,
        "label": label,
        "source": source,
        "step": step,
        "mayMarkCurrentStepDone": bool(ready),
        "mayAdvanceSequence": bool(ready),
        "mayStartNextStep": bool(ready and sequence_position.get("nextStep")),
        "nextStep": sequence_position.get("nextStep") or "",
        "nextSource": sequence_position.get("nextSource") or "",
        "nextLabel": sequence_position.get("nextLabel") or "",
        "directCanonicalFirstSequenceComplete": bool(
            sequence_position.get("directCanonicalFirstSequenceComplete")
        ),
        "blockedNextStepReason": (
            "" if ready else "Fechamento da subetapa atual ainda nao aprovado."
        ),
        "blockedBy": blocked_by,
        "detail": detail,
    }


def montar_checklist_evidencias_fechamento(
    source,
    evidence_files,
    exigir_validacao_ativacao=False,
):
    evidence_files = evidence_files or {}
    definitions = [
        (
            "activationValidation",
            "Validacao de ativacao",
            bool(exigir_validacao_ativacao),
        ),
        ("candidateDiscovery", "Descoberta de candidato", source == "financiamento_movimentacao"),
        ("windowValidation", "Validacao da janela", True),
        ("monitor", "Monitoramento da janela", True),
        ("sourceAudit", "Auditoria de fonte de escrita", True),
        ("debtRegression", "Regressao de dividas FCF", source == "financiamento_movimentacao"),
        ("totalsAudit", "Auditoria de totais", True),
    ]
    items = []
    for key, label, required in definitions:
        path = evidence_files.get(key) or ""
        found = bool(path) and Path(path).expanduser().exists()
        if required and found:
            status = "present"
        elif required:
            status = "missingRequired"
        elif found:
            status = "presentOptional"
        else:
            status = "notRequired"
        items.append(
            {
                "key": key,
                "label": label,
                "required": bool(required),
                "path": path,
                "found": bool(found),
                "status": status,
            }
        )
    missing_required = [
        item["key"]
        for item in items
        if item["required"] and not item["found"]
    ]
    return {
        "source": source,
        "step": SOURCE_PM03_STEPS.get(source, ""),
        "ready": not missing_required,
        "requiredCount": sum(1 for item in items if item["required"]),
        "foundRequiredCount": sum(
            1 for item in items if item["required"] and item["found"]
        ),
        "missingRequiredCount": len(missing_required),
        "missingRequired": missing_required,
        "items": items,
    }


def _deve_validar_evidencia_ativacao(evidence_files, required=False):
    if required:
        return True
    path = evidence_files.get("activationValidation")
    return bool(path and Path(path).expanduser().exists())


def _deve_validar_evidencia_regressao_dividas(source, evidence_files):
    if source == "financiamento_movimentacao":
        return True
    path = evidence_files.get("debtRegression")
    return bool(path and Path(path).expanduser().exists())


def _deve_validar_evidencia_candidatos_canario(source, evidence_files):
    if source == "financiamento_movimentacao":
        return True
    path = evidence_files.get("candidateDiscovery")
    return bool(path and Path(path).expanduser().exists())


def _validar_evidencia_validacao_janela(
    source,
    evidence_files,
    data_inicial="",
    data_final="",
):
    payload, issues = _carregar_json(
        "validacaoJanela",
        evidence_files.get("windowValidation"),
    )
    if payload:
        _exigir(payload.get("source") == source, issues, "origem da validacao nao confere")
        _exigir(payload.get("ready") is True, issues, "validacao da janela nao esta pronta")
        _exigir(
            not payload.get("issues"),
            issues,
            "validacao da janela registrou pendencias",
        )
        feature_flag = payload.get("featureFlagValidation") or {}
        _exigir(
            feature_flag.get("activeForSource") is True,
            issues,
            "feature flag canonical-first nao estava ativa para a origem",
        )
        preflight = payload.get("operationalPreflight") or {}
        _exigir(
            preflight.get("ready") is True,
            issues,
            "pre-flight operacional nao estava pronto na validacao da janela",
        )
        _validar_periodo_payload(
            payload.get("period") or {},
            issues,
            data_inicial=data_inicial,
            data_final=data_final,
            contexto="validacao da janela",
        )
        _validar_window_outcome_payload(
            payload,
            issues,
            contexto="validacao da janela",
        )
        _validar_auditorias_janela_payload(
            payload,
            issues,
            contexto="validacao da janela",
        )
    return _check("windowValidation", "Validacao da janela", issues)


def _validar_evidencia_validacao_ativacao(
    source,
    evidence_files,
    data_inicial="",
    required=False,
):
    path = evidence_files.get("activationValidation")
    if not required and not path:
        return _check(
            "activationValidation",
            "Validacao de ativacao",
            [],
        )

    payload, issues = _carregar_json("validacaoAtivacao", path)
    if payload:
        _exigir(payload.get("source") == source, issues, "origem da ativacao nao confere")
        _exigir(payload.get("ready") is True, issues, "validacao de ativacao nao esta pronta")
        _exigir(
            not payload.get("issues"),
            issues,
            "validacao de ativacao registrou pendencias",
        )
        canary = payload.get("canary") or {}
        _exigir(
            canary.get("required") is True,
            issues,
            "validacao de ativacao nao exigiu canario",
        )
        _exigir(
            canary.get("sourceIdRequired") is True,
            issues,
            "validacao de ativacao nao exigiu sourceId do canario",
        )
        _exigir(
            canary.get("paymentDateRequired") is True,
            issues,
            "validacao de ativacao nao exigiu data de pagamento do canario",
        )
        _exigir(
            canary.get("paymentDateProvided") is True,
            issues,
            "validacao de ativacao nao usou data de pagamento explicita",
        )
        _exigir(
            canary.get("executed") is True,
            issues,
            "validacao de ativacao nao executou canario",
        )
        _exigir(
            canary.get("synced") is True,
            issues,
            "canario de ativacao nao ficou sincronizado",
        )
        canary_result = canary.get("result") or {}
        canary_payment_date = str(canary.get("paymentDate") or "")
        result_payment_date = str(canary_result.get("paymentDate") or "")
        if canary.get("paymentDateRequired") is True:
            _exigir(
                bool(canary_payment_date),
                issues,
                "validacao de ativacao nao registrou data de pagamento do canario",
            )
            if data_inicial:
                _exigir(
                    canary_payment_date == data_inicial,
                    issues,
                    "data de pagamento do canario nao confere com data inicial da janela",
                )
            _exigir(
                result_payment_date == canary_payment_date,
                issues,
                "data de pagamento do resultado do canario nao confere",
            )
        _exigir(
            canary_result.get("canary") is True,
            issues,
            "resultado do canario de ativacao nao marcou canary=True",
        )
        _exigir(
            canary_result.get("rollbackOnly") is True,
            issues,
            "canario de ativacao nao comprovou rollback-only",
        )
        _exigir(
            canary_result.get("writesPersisted") is False,
            issues,
            "canario de ativacao persistiu escrita",
        )
        _exigir(
            canary_result.get("source") == source,
            issues,
            "origem do resultado do canario nao confere",
        )
        canary_item = canary_result.get("item") or {}
        canonical_settlement = canary_result.get("canonicalSettlement") or {}
        requested_realized_amount = _decimal_or_none(
            canary_result.get("requestedRealizedAmount")
        )
        delta_amount = _decimal_or_none(canary_result.get("deltaAmount"))
        canonical_realized_amount = _decimal_or_none(
            canonical_settlement.get("realizedAmount")
        )
        canonical_allocated_amount = _decimal_or_none(
            canonical_settlement.get("allocatedAmount")
        )
        _exigir(
            delta_amount is not None and delta_amount > 0,
            issues,
            "delta do canario de ativacao nao e positivo",
        )
        _exigir(
            requested_realized_amount is not None,
            issues,
            "valor realizado solicitado no canario nao foi registrado",
        )
        _validar_item_resultado_canario(
            source,
            canary_item,
            canary_result,
            canary.get("sourceIdCheck") or {},
            requested_realized_amount,
            issues,
        )
        _exigir(
            _decimais_iguais(canonical_realized_amount, requested_realized_amount),
            issues,
            "valor realizado canonico do canario nao confere",
        )
        _exigir(
            _decimais_iguais(canonical_allocated_amount, requested_realized_amount),
            issues,
            "valor alocado canonico do canario nao confere",
        )
        latest_settlement = canonical_settlement.get("latestSettlement") or {}
        latest_amount = _decimal_or_none(latest_settlement.get("amount"))
        latest_settlement_amount = _decimal_or_none(
            latest_settlement.get("settlementAmount")
        )
        _exigir(
            canonical_settlement.get("available") is True,
            issues,
            "contexto canonico do canario nao esta disponivel",
        )
        _exigir(
            canonical_settlement.get("settlementModel") == "BaixaFinanceira",
            issues,
            "modelo de baixa canonica do canario nao confere",
        )
        _exigir(
            canonical_settlement.get("allocationModel") == "BaixaFinanceiraAlocacao",
            issues,
            "modelo de alocacao canonica do canario nao confere",
        )
        _exigir(
            _int_or_zero(canonical_settlement.get("settlementCount")) > 0,
            issues,
            "canario nao registrou baixa canonica",
        )
        _exigir(
            _int_or_zero(canonical_settlement.get("allocationCount")) > 0,
            issues,
            "canario nao registrou alocacao canonica",
        )
        _exigir(
            bool(latest_settlement),
            issues,
            "canario nao registrou ultima baixa canonica",
        )
        _exigir(
            bool(latest_settlement.get("id")),
            issues,
            "ultima baixa canonica do canario nao possui id",
        )
        _exigir(
            bool(latest_settlement.get("key")),
            issues,
            "ultima baixa canonica do canario nao possui chave",
        )
        _exigir(
            latest_settlement.get("writeModelSource") == "canonicalFirst",
            issues,
            "ultima baixa canonica do canario nao usou canonical-first",
        )
        _exigir(
            latest_settlement.get("status") == STATUS_REALIZADO,
            issues,
            "ultima baixa canonica do canario nao esta realizada",
        )
        _exigir(
            latest_settlement.get("type") == TIPO_FLUXO_SAIDA,
            issues,
            "ultima baixa canonica do canario nao e saida",
        )
        _exigir(
            bool(latest_settlement.get("cashFlowGroup")),
            issues,
            "ultima baixa canonica do canario nao possui fluxo financeiro",
        )
        _exigir(
            bool(latest_settlement.get("nature")),
            issues,
            "ultima baixa canonica do canario nao possui natureza financeira",
        )
        _exigir(
            bool(latest_settlement.get("ledgerEntryId")),
            issues,
            "ultima baixa canonica do canario nao possui lancamento no ledger",
        )
        if canary.get("paymentDateRequired") is True:
            _exigir(
                latest_settlement.get("date") == canary_payment_date,
                issues,
                "data da ultima baixa canonica do canario nao confere",
            )
            _exigir(
                latest_settlement.get("settlementDate") == canary_payment_date,
                issues,
                "data de liquidacao da ultima baixa canonica do canario nao confere",
            )
        _exigir(
            _decimais_iguais(latest_amount, delta_amount),
            issues,
            "valor da ultima baixa canonica do canario nao confere",
        )
        _exigir(
            _decimais_iguais(latest_settlement_amount, delta_amount),
            issues,
            "valor de liquidacao da ultima baixa canonica do canario nao confere",
        )
        _exigir(
            canonical_settlement.get("synced") is True,
            issues,
            "resultado canonico do canario nao ficou sincronizado",
        )
        _exigir(
            canonical_settlement.get("writeModelSource") == "canonicalFirst",
            issues,
            "canario de ativacao nao usou escrita canonical-first",
        )
        source_id_check = canary.get("sourceIdCheck") or {}
        _exigir(
            source_id_check.get("provided") is True,
            issues,
            "validacao de ativacao nao registrou sourceId explicito",
        )
        _exigir(
            source_id_check.get("eligible") is True,
            issues,
            "sourceId do canario nao estava elegivel",
        )
        _exigir(
            str(canary_result.get("sourceId") or "")
            == str(source_id_check.get("sourceId") or ""),
            issues,
            "sourceId do resultado do canario nao confere",
        )
        _exigir(
            str(canary_result.get("obligationId") or "")
            == str(source_id_check.get("obligationId") or ""),
            issues,
            "obrigacao do resultado do canario nao confere",
        )
        _exigir(
            str(canary_result.get("obligationKey") or "")
            == str(source_id_check.get("obligationKey") or ""),
            issues,
            "chave da obrigacao do resultado do canario nao confere",
        )
        _exigir(
            str(canonical_settlement.get("obligationId") or "")
            == str(source_id_check.get("obligationId") or ""),
            issues,
            "obrigacao canonica do canario nao confere",
        )
        _exigir(
            str(canonical_settlement.get("obligationKey") or "")
            == str(source_id_check.get("obligationKey") or ""),
            issues,
            "chave canonica do canario nao confere",
        )
        decision = payload.get("activationDecision") or {}
        activation_list_limit_blocked = _payload_bloqueado_por_limite_candidato(
            payload
        )
        if decision:
            _exigir(
                decision.get("source") == source,
                issues,
                "origem da decisao de ativacao nao confere",
            )
            if decision.get("status") == "blockedCandidateListLimit":
                issues.append(
                    "decisao de ativacao bloqueada por limite da lista de candidatos"
                )
        elif activation_list_limit_blocked:
            issues.append(
                "validacao de ativacao bloqueada por limite da lista de candidatos"
            )
        if decision:
            _exigir(
                decision.get("status") == "readyForAllowlistWindow",
                issues,
                "decisao de ativacao nao liberou allowlist",
            )
            _exigir(
                decision.get("mayActivateAllowlistWindow") is True,
                issues,
                "decisao de ativacao bloqueia allowlist",
            )
            _exigir(
                decision.get("mayRunCanaryRollbackOnly") is False,
                issues,
                "decisao de ativacao ainda indica execucao de canario",
            )
            _exigir(
                decision.get("requiresControlledCandidate") is False,
                issues,
                "decisao de ativacao ainda exige candidato controlado",
            )
            _exigir(
                str(decision.get("selectedSourceId") or "")
                == str(source_id_check.get("sourceId") or ""),
                issues,
                "sourceId da decisao de ativacao nao confere",
            )
            _exigir(
                str(decision.get("selectedObligationId") or "")
                == str(source_id_check.get("obligationId") or ""),
                issues,
                "obrigacao da decisao de ativacao nao confere",
            )
        next_action = payload.get("nextAction") or {}
        _exigir(
            next_action.get("key") == "activateAllowlistWindow",
            issues,
            "validacao de ativacao nao terminou pronta para allowlist",
        )
    return _check("activationValidation", "Validacao de ativacao", issues)


def _validar_evidencia_monitoramento(
    source,
    evidence_files,
    data_inicial="",
    data_final="",
):
    payload, issues = _carregar_json("monitor", evidence_files.get("monitor"))
    if payload:
        _exigir(payload.get("source") == source, issues, "origem do monitor nao confere")
        _exigir(payload.get("ready") is True, issues, "monitoramento nao esta pronto")
        _exigir(not payload.get("issues"), issues, "monitoramento registrou pendencias")
        _exigir(
            payload.get("requiresCanonicalFirst") is True,
            issues,
            "monitor nao exigiu baixa canonical-first",
        )
        _exigir(
            payload.get("failsOnLegacyInWindow") is True,
            issues,
            "monitor nao reprovaria baixa legada na janela",
        )
        _exigir(
            payload.get("requiresActivationDate") is True,
            issues,
            "monitor nao exigiu data de ativacao",
        )
        periodo = payload.get("period") or {}
        _exigir(
            bool(periodo.get("startDate")),
            issues,
            "monitoramento sem data inicial da janela",
        )
        _validar_periodo_payload(
            periodo,
            issues,
            data_inicial=data_inicial,
            data_final=data_final,
            contexto="monitoramento",
        )
        auditoria = payload.get("writeAudit") or {}
        canonical = auditoria.get("canonicalFirst") or {}
        legado = auditoria.get("legacyAdapterSynced") or {}
        _exigir(
            int(canonical.get("count") or 0) > 0,
            issues,
            "monitoramento nao encontrou baixa canonical-first",
        )
        _exigir(
            int(legado.get("count") or 0) == 0,
            issues,
            "monitoramento encontrou baixa legada na janela",
        )
        _validar_window_outcome_payload(
            payload,
            issues,
            contexto="monitoramento",
        )
    return _check("monitor", "Monitoramento da janela", issues)


def _validar_evidencia_auditoria_fonte(
    source,
    evidence_files,
    data_inicial="",
    data_final="",
):
    payload, issues = _carregar_json(
        "auditoriaFonte",
        evidence_files.get("sourceAudit"),
    )
    if payload:
        filtros = payload.get("filters") or {}
        _exigir(
            filtros.get("source") == source,
            issues,
            "origem da auditoria de fonte nao confere",
        )
        _exigir(
            filtros.get("writeModelSource") == "canonicalFirst",
            issues,
            "auditoria de fonte nao filtrou canonicalFirst",
        )
        _exigir(
            not payload.get("issues"),
            issues,
            "auditoria de fonte registrou pendencias",
        )
        canonical = payload.get("canonicalFirst") or {}
        legado = payload.get("legacyAdapterSynced") or {}
        _exigir(
            int(canonical.get("count") or 0) > 0,
            issues,
            "auditoria de fonte nao encontrou baixa canonical-first",
        )
        _exigir(
            int(legado.get("count") or 0) == 0,
            issues,
            "auditoria de fonte encontrou baixa legada no filtro canonicalFirst",
        )
        _validar_periodo_payload(
            {
                "startDate": filtros.get("startDate") or filtros.get("data_inicial"),
                "endDate": filtros.get("endDate") or filtros.get("data_final"),
            },
            issues,
            data_inicial=data_inicial,
            data_final=data_final,
            contexto="auditoria de fonte",
        )
    return _check("sourceAudit", "Auditoria de fonte de escrita", issues)


def _validar_evidencia_auditoria_totais(evidence_files):
    payload, issues = _carregar_json(
        "auditoriaTotais",
        evidence_files.get("totalsAudit"),
    )
    if payload:
        obrigacoes = payload.get("obligations") or {}
        _exigir(
            int(obrigacoes.get("divergentCount") or 0) == 0,
            issues,
            "auditoria de totais encontrou divergencias de obrigacoes",
        )
        valores = payload.get("editableValuesIntegrity") or {}
        _exigir(
            valores.get("checked") is True,
            issues,
            "auditoria de totais nao validou valores editaveis",
        )
        _exigir(
            valores.get("consistent") is True,
            issues,
            "auditoria de totais encontrou valores editaveis inconsistentes",
        )
    return _check("totalsAudit", "Auditoria de totais", issues)


def _validar_evidencia_regressao_dividas(source, evidence_files):
    payload, issues = _carregar_json(
        "regressaoDividas",
        evidence_files.get("debtRegression"),
    )
    if payload:
        _exigir(
            payload.get("source") == source,
            issues,
            "origem da regressao de dividas nao confere",
        )
        _exigir(
            payload.get("ready") is True,
            issues,
            "regressao de dividas nao esta pronta",
        )
        _exigir(
            not payload.get("issues"),
            issues,
            "regressao de dividas registrou pendencias",
        )
        decision = payload.get("regressionDecision") or {}
        if decision:
            _exigir(
                decision.get("status") == "approved",
                issues,
                "decisao da regressao de dividas nao esta aprovada",
            )
            _exigir(
                decision.get("mayContinuePm03_4") is True,
                issues,
                "decisao da regressao de dividas bloqueia PM-03.4",
            )
        credores = payload.get("debtCreditorRegression") or {}
        _exigir(
            (
                credores.get("consistentAfter") is True
                or credores.get("consistent") is True
            ),
            issues,
            "regressao de credores FCF nao ficou consistente",
        )
        entradas = payload.get("debtAutomaticFcfEntryIntegrity") or {}
        _exigir(
            (
                entradas.get("consistent") is True
                or entradas.get("consistentAfter") is True
            ),
            issues,
            "regressao de entradas FCF por divida nao ficou consistente",
        )
        preflight = payload.get("financialPreflight") or {}
        _exigir(
            preflight.get("ready") is True,
            issues,
            "pre-flight financeiro da regressao de dividas nao esta pronto",
        )
    return _check("debtRegression", "Regressao de dividas FCF", issues)


def _validar_evidencia_candidatos_canario(source, evidence_files):
    payload, issues = _carregar_json(
        "candidatosCanario",
        evidence_files.get("candidateDiscovery"),
    )
    if payload:
        _exigir(
            payload.get("source") == source,
            issues,
            "origem da descoberta de candidatos nao confere",
        )
        _exigir(
            payload.get("ready") is True,
            issues,
            "descoberta de candidatos nao esta pronta",
        )
        _exigir(
            not payload.get("issues"),
            issues,
            "descoberta de candidatos registrou pendencias",
        )
        pendencias = payload.get("pendingObligations") or {}
        _exigir(
            int(pendencias.get("canaryEligibleCount") or 0) > 0,
            issues,
            "descoberta de candidatos nao encontrou obrigacao a pagar elegivel",
        )
        _exigir(
            bool(pendencias.get("canaryCandidates") or []),
            issues,
            "descoberta de candidatos nao registrou canaryCandidates",
        )
        next_action = payload.get("nextAction") or {}
        _exigir(
            next_action.get("key") == "runCanaryRollbackOnly",
            issues,
            "descoberta de candidatos nao terminou pronta para canario rollback-only",
        )
        gate = payload.get("operationalGate") or {}
        _exigir(
            gate.get("source") == source,
            issues,
            "origem do gate da descoberta de candidatos nao confere",
        )
        _exigir(
            gate.get("status") == "readyForCanaryRollbackOnly",
            issues,
            "gate da descoberta de candidatos nao ficou pronto para canario",
        )
        decision = payload.get("candidateDecision") or {}
        candidate_list_limit_blocked = _payload_bloqueado_por_limite_candidato(
            payload
        )
        if decision:
            _exigir(
                decision.get("source") == source,
                issues,
                "origem da decisao de candidato nao confere",
            )
            if decision.get("status") == "blockedCandidateListLimit":
                issues.append(
                    "decisao de candidato bloqueada por limite da lista de candidatos"
                )
        elif candidate_list_limit_blocked:
            issues.append(
                "descoberta de candidatos bloqueada por limite da lista de candidatos"
            )
        if decision:
            _exigir(
                decision.get("status") == "readyForCanaryRollbackOnly",
                issues,
                "decisao de candidato nao esta pronta para canario",
            )
            _exigir(
                decision.get("mayRunCanaryRollbackOnly") is True,
                issues,
                "decisao de candidato bloqueia canario rollback-only",
            )
            candidate_pairs = {
                (
                    str(candidate.get("sourceId") or ""),
                    str(candidate.get("obligationId") or ""),
                )
                for candidate in pendencias.get("canaryCandidates") or []
            }
            selected_pair = (
                str(decision.get("selectedSourceId") or ""),
                str(decision.get("selectedObligationId") or ""),
            )
            _exigir(
                selected_pair in candidate_pairs,
                issues,
                "decisao de candidato selecionou sourceId/obrigacao fora dos candidatos",
            )
    return _check("candidateDiscovery", "Descoberta de candidato", issues)


def _payload_bloqueado_por_limite_candidato(payload):
    payload = payload or {}
    decision_status = (
        (payload.get("activationDecision") or {}).get("status")
        or (payload.get("candidateDecision") or {}).get("status")
        or ""
    )
    next_key = (payload.get("nextAction") or {}).get("key") or ""
    gate_status = (payload.get("operationalGate") or {}).get("status") or ""
    list_health_status = (payload.get("candidateListHealth") or {}).get("status") or ""
    pendencias = payload.get("pendingObligations") or {}
    eligible_count = _inteiro_seguro(pendencias.get("canaryEligibleCount"))
    returned_count = _inteiro_seguro(
        pendencias.get("canaryCandidatesReturnedCount")
        or len(pendencias.get("canaryCandidates") or [])
    )
    truncated = bool(pendencias.get("canaryCandidatesTruncated"))
    hidden_by_limit = eligible_count > 0 and returned_count == 0 and truncated
    return (
        decision_status == "blockedCandidateListLimit"
        or next_key == "expandCanaryCandidateList"
        or gate_status == "blockedCandidateListLimit"
        or list_health_status == "blockedByLimit"
        or hidden_by_limit
    )


def _inteiro_seguro(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _carregar_json(label, path):
    if not path:
        return None, [f"{label}: arquivo nao informado"]
    target = Path(path).expanduser()
    if not target.exists():
        return None, [f"{label}: arquivo nao encontrado: {path}"]
    try:
        return json.loads(target.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"{label}: JSON invalido: {exc}"]


def resumir_gate_operacional_fechamento(evidence_files):
    fontes = {
        "activationValidation": evidence_files.get("activationValidation"),
        "candidateDiscovery": evidence_files.get("candidateDiscovery"),
        "debtRegression": evidence_files.get("debtRegression"),
        "windowValidation": evidence_files.get("windowValidation"),
        "monitor": evidence_files.get("monitor"),
    }
    gates = {}
    for key, path in fontes.items():
        payload = _carregar_json_opcional(path)
        gate = _extrair_gate_operacional(payload)
        if gate:
            gates[key] = {
                "currentStep": gate.get("currentStep") or "",
                "status": gate.get("status") or "",
                "statusLabel": gate.get("statusLabel") or "",
                "source": gate.get("source") or "",
                "canaryCandidateCount": gate.get("canaryCandidateCount"),
            }

    steps = sorted(
        {
            gate.get("currentStep") or ""
            for gate in gates.values()
            if gate.get("currentStep")
        }
    )
    statuses = sorted(
        {
            gate.get("status") or ""
            for gate in gates.values()
            if gate.get("status")
        }
    )
    sources = sorted(
        {
            gate.get("source") or ""
            for gate in gates.values()
            if gate.get("source")
        }
    )
    return {
        "available": bool(gates),
        "consistentStep": len(steps) <= 1,
        "consistentSource": len(sources) <= 1,
        "currentSteps": steps,
        "sources": sources,
        "statuses": statuses,
        "byEvidence": gates,
    }


def resumir_posicao_sequencia_fechamento(evidence_files):
    fontes = {
        "activationValidation": evidence_files.get("activationValidation"),
        "candidateDiscovery": evidence_files.get("candidateDiscovery"),
        "debtRegression": evidence_files.get("debtRegression"),
        "windowValidation": evidence_files.get("windowValidation"),
        "monitor": evidence_files.get("monitor"),
    }
    positions_by_evidence = {}
    for key, path in fontes.items():
        payload = _carregar_json_opcional(path)
        position = _extrair_posicao_sequencia(payload)
        if position:
            position_index = _normalizar_indice_posicao_sequencia(
                position.get("position")
            )
            positions_by_evidence[key] = {
                "source": position.get("source") or "",
                "step": position.get("step") or "",
                "position": position_index,
                "rawPosition": position.get("position"),
                "positionValid": position_index > 0,
                "previousStep": position.get("previousStep") or "",
                "nextStep": position.get("nextStep") or "",
                "nextSource": position.get("nextSource") or "",
                "isLastDirectStep": bool(position.get("isLastDirectStep")),
            }

    sources = sorted(
        {position.get("source") or "" for position in positions_by_evidence.values()}
    )
    steps = sorted(
        {position.get("step") or "" for position in positions_by_evidence.values()}
    )
    positions = sorted(
        {position.get("position") or 0 for position in positions_by_evidence.values()}
    )
    next_steps = sorted(
        {position.get("nextStep") or "" for position in positions_by_evidence.values()}
    )
    next_sources = sorted(
        {
            position.get("nextSource") or ""
            for position in positions_by_evidence.values()
        }
    )
    consistent = (
        len(sources) <= 1
        and len(steps) <= 1
        and len(positions) <= 1
        and len(next_steps) <= 1
        and len(next_sources) <= 1
    )
    return {
        "available": bool(positions_by_evidence),
        "consistent": consistent,
        "consistentSource": len(sources) <= 1,
        "consistentStep": len(steps) <= 1,
        "consistentPosition": len(positions) <= 1,
        "consistentNextStep": len(next_steps) <= 1,
        "consistentNextSource": len(next_sources) <= 1,
        "sources": sources,
        "steps": steps,
        "positions": positions,
        "nextSteps": next_steps,
        "nextSources": next_sources,
        "byEvidence": positions_by_evidence,
    }


def _normalizar_indice_posicao_sequencia(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _coletar_issues_posicao_sequencia_esperada(sequence_summary, expected_position):
    issues = []
    expected_source = expected_position.get("source") or ""
    expected_step = expected_position.get("step") or ""
    expected_position_index = expected_position.get("position") or 0
    expected_next_step = expected_position.get("nextStep") or ""
    expected_next_source = expected_position.get("nextSource") or ""
    evidencias_posicao_malformada = sorted(
        key
        for key, position in (sequence_summary.get("byEvidence") or {}).items()
        if not position.get("positionValid", True)
    )

    if sequence_summary.get("sources") != [expected_source]:
        issues.append("origem da sequencia PM-03 nas evidencias nao confere")
    if sequence_summary.get("steps") != [expected_step]:
        issues.append("etapa da sequencia PM-03 nas evidencias nao confere")
    if evidencias_posicao_malformada:
        issues.append(
            "posicao da sequencia PM-03 malformada nas evidencias: "
            + ", ".join(evidencias_posicao_malformada)
        )
    if sequence_summary.get("positions") != [expected_position_index]:
        issues.append("posicao da sequencia PM-03 nas evidencias nao confere")
    if sequence_summary.get("nextSteps") != [expected_next_step]:
        issues.append("proxima etapa da sequencia PM-03 nas evidencias nao confere")
    if sequence_summary.get("nextSources") != [expected_next_source]:
        issues.append("proxima origem da sequencia PM-03 nas evidencias nao confere")
    return issues


def _resumir_posicao_sequencia_esperada(sequence_position):
    return {
        "source": sequence_position.get("source") or "",
        "step": sequence_position.get("step") or "",
        "position": sequence_position.get("position") or 0,
        "nextStep": sequence_position.get("nextStep") or "",
        "nextSource": sequence_position.get("nextSource") or "",
    }


def resumir_resultado_janela_fechamento(evidence_files):
    fontes = {
        "windowValidation": evidence_files.get("windowValidation"),
        "monitor": evidence_files.get("monitor"),
    }
    outcomes = {}
    for key, path in fontes.items():
        payload = _carregar_json_opcional(path)
        outcome = (payload or {}).get("windowOutcome") or {}
        if outcome:
            outcomes[key] = {
                "status": outcome.get("status") or "",
                "label": outcome.get("label") or "",
                "nextActionScope": outcome.get("nextActionScope") or "",
                "nextActionNote": outcome.get("nextActionNote") or "",
            }

    statuses = sorted(
        {
            outcome.get("status") or ""
            for outcome in outcomes.values()
            if outcome.get("status")
        }
    )
    return {
        "available": bool(outcomes),
        "consistentStatus": len(statuses) <= 1,
        "statuses": statuses,
        "byEvidence": outcomes,
    }


def resumir_auditoria_janela_fechamento(evidence_files):
    fontes = {
        "windowValidation": (
            evidence_files.get("windowValidation"),
            "windowWriteAudit",
        ),
        "monitor": (
            evidence_files.get("monitor"),
            "writeAudit",
        ),
    }
    audits = {}
    for key, (path, field) in fontes.items():
        payload = _carregar_json_opcional(path)
        audit = (payload or {}).get(field) or {}
        if audit:
            audits[key] = _resumir_auditoria_janela_payload(audit)

    fingerprints = sorted(
        {
            (
                audit.get("count"),
                audit.get("canonicalFirstCount"),
                audit.get("legacyAdapterSyncedCount"),
            )
            for audit in audits.values()
        }
    )
    return {
        "available": bool(audits),
        "consistentCounts": len(fingerprints) <= 1,
        "byEvidence": audits,
    }


def _resumir_auditoria_janela_payload(audit):
    canonical = audit.get("canonicalFirst") or {}
    legado = audit.get("legacyAdapterSynced") or {}
    return {
        "count": int(audit.get("count") or 0),
        "canonicalFirstCount": int(canonical.get("count") or 0),
        "legacyAdapterSyncedCount": int(legado.get("count") or 0),
    }


def resumir_candidato_ativacao_fechamento(evidence_files):
    discovery = _carregar_json_opcional(evidence_files.get("candidateDiscovery"))
    activation = _carregar_json_opcional(evidence_files.get("activationValidation"))
    if not discovery or not activation:
        return {
            "available": False,
            "consistent": True,
            "activationSourceId": "",
            "activationObligationId": "",
            "candidateSourceIds": [],
            "candidateObligationIds": [],
        }

    canary = activation.get("canary") or {}
    source_id_check = canary.get("sourceIdCheck") or {}
    canary_result = canary.get("result") or {}
    activation_source_id = str(
        source_id_check.get("sourceId") or canary_result.get("sourceId") or ""
    )
    activation_obligation_id = str(
        source_id_check.get("obligationId")
        or canary_result.get("obligationId")
        or ""
    )
    candidates = (
        (discovery.get("pendingObligations") or {}).get("canaryCandidates")
        or []
    )
    candidate_source_ids = [
        str(candidate.get("sourceId") or "")
        for candidate in candidates
        if str(candidate.get("sourceId") or "")
    ]
    candidate_obligation_ids = [
        str(candidate.get("obligationId") or "")
        for candidate in candidates
        if str(candidate.get("obligationId") or "")
    ]
    matches = [
        candidate
        for candidate in candidates
        if str(candidate.get("sourceId") or "") == activation_source_id
    ]
    if activation_obligation_id:
        matches = [
            candidate
            for candidate in matches
            if str(candidate.get("obligationId") or "") == activation_obligation_id
        ]

    return {
        "available": True,
        "consistent": bool(activation_source_id and matches),
        "activationSourceId": activation_source_id,
        "activationObligationId": activation_obligation_id,
        "candidateSourceIds": candidate_source_ids,
        "candidateObligationIds": candidate_obligation_ids,
    }


def resumir_canario_ativacao_fechamento(evidence_files, data_inicial=""):
    activation = _carregar_json_opcional(evidence_files.get("activationValidation"))
    if not activation:
        return {
            "available": False,
            "required": None,
            "executed": None,
            "synced": None,
            "sourceId": "",
            "obligationId": "",
            "obligationKey": "",
            "paymentDate": "",
            "writeModelSource": "",
            "rollbackOnly": None,
            "writesPersisted": None,
            "activationDecisionStatus": "",
            "expectedActivationDate": data_inicial or "",
            "matchesActivationDate": None,
        }

    canary = activation.get("canary") or {}
    source_id_check = canary.get("sourceIdCheck") or {}
    result = canary.get("result") or {}
    canonical = result.get("canonicalSettlement") or {}
    decision = activation.get("activationDecision") or {}
    payment_date = str(canary.get("paymentDate") or result.get("paymentDate") or "")
    matches_activation_date = None
    if data_inicial:
        matches_activation_date = bool(payment_date and payment_date == data_inicial)
    return {
        "available": True,
        "required": canary.get("required"),
        "sourceIdRequired": canary.get("sourceIdRequired"),
        "paymentDateRequired": canary.get("paymentDateRequired"),
        "paymentDateProvided": canary.get("paymentDateProvided"),
        "executed": canary.get("executed"),
        "synced": canary.get("synced"),
        "sourceId": str(
            source_id_check.get("sourceId") or result.get("sourceId") or ""
        ),
        "obligationId": str(
            source_id_check.get("obligationId")
            or result.get("obligationId")
            or canonical.get("obligationId")
            or ""
        ),
        "obligationKey": str(
            source_id_check.get("obligationKey")
            or result.get("obligationKey")
            or canonical.get("obligationKey")
            or ""
        ),
        "paymentDate": payment_date,
        "expectedActivationDate": data_inicial or "",
        "matchesActivationDate": matches_activation_date,
        "writeModelSource": canonical.get("writeModelSource") or "",
        "rollbackOnly": result.get("rollbackOnly"),
        "writesPersisted": result.get("writesPersisted"),
        "activationDecisionStatus": decision.get("status") or "",
        "mayActivateAllowlistWindow": decision.get("mayActivateAllowlistWindow"),
    }


def resumir_saude_lista_candidatos_fechamento(evidence_files):
    fontes = {
        "activationValidation": evidence_files.get("activationValidation"),
        "candidateDiscovery": evidence_files.get("candidateDiscovery"),
        "windowValidation": evidence_files.get("windowValidation"),
        "monitor": evidence_files.get("monitor"),
    }
    by_evidence = {}
    for key, path in fontes.items():
        payload = _carregar_json_opcional(path)
        health = (payload or {}).get("candidateListHealth") or {}
        if health:
            by_evidence[key] = {
                "status": health.get("status") or "",
                "recommendedAction": health.get("recommendedAction") or "",
                "eligibleCount": _inteiro_seguro(health.get("eligibleCount")),
                "returnedCount": _inteiro_seguro(health.get("returnedCount")),
                "limit": _inteiro_seguro(health.get("limit")),
                "hasSelectableCandidate": bool(
                    health.get("hasSelectableCandidate")
                ),
                "requiresLimitIncrease": bool(
                    health.get("requiresLimitIncrease")
                ),
            }
    statuses = sorted(
        {
            item.get("status") or ""
            for item in by_evidence.values()
            if item.get("status")
        }
    )
    recommended_actions = sorted(
        {
            item.get("recommendedAction") or ""
            for item in by_evidence.values()
            if item.get("recommendedAction")
        }
    )
    return {
        "available": bool(by_evidence),
        "statuses": statuses,
        "recommendedActions": recommended_actions,
        "requiresLimitIncrease": any(
            item.get("requiresLimitIncrease") for item in by_evidence.values()
        ),
        "hasBlockedByLimit": any(
            item.get("status") == "blockedByLimit"
            for item in by_evidence.values()
        ),
        "byEvidence": by_evidence,
    }


def resumir_regressao_dividas_fechamento(evidence_files):
    payload = _carregar_json_opcional(evidence_files.get("debtRegression"))
    if not payload:
        return {
            "available": False,
            "status": "",
            "mayContinuePm03_4": None,
            "blockedBy": [],
            "ready": None,
            "issuesCount": 0,
        }

    decision = payload.get("regressionDecision") or {}
    credores = payload.get("debtCreditorRegression") or {}
    entradas = payload.get("debtAutomaticFcfEntryIntegrity") or {}
    preflight = payload.get("financialPreflight") or {}
    status = decision.get("status") or (
        "approved" if payload.get("ready") is True else "blocked"
    )
    return {
        "available": True,
        "status": status,
        "source": payload.get("source") or "",
        "step": decision.get("step") or "",
        "label": decision.get("label") or "",
        "mayContinuePm03_4": decision.get("mayContinuePm03_4"),
        "requiredBefore": decision.get("requiredBefore") or [],
        "blockedBy": decision.get("blockedBy") or [],
        "ready": payload.get("ready"),
        "issuesCount": len(payload.get("issues") or []),
        "debtCreditorConsistent": (
            credores.get("consistentAfter") is True
            or credores.get("consistent") is True
        ),
        "debtAutomaticFcfEntryConsistent": (
            entradas.get("consistent") is True
            or entradas.get("consistentAfter") is True
        ),
        "financialPreflightReady": preflight.get("ready"),
    }


def _validar_consistencia_candidato_ativacao(summary):
    issues = []
    if not summary.get("consistent"):
        issues.append(
            "canario de ativacao nao corresponde aos candidatos descobertos"
        )
    return _check("candidateActivation", "Candidato x ativacao", issues)


def _carregar_json_opcional(path):
    if not path:
        return None
    target = Path(path).expanduser()
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _extrair_gate_operacional(payload):
    if not isinstance(payload, dict):
        return {}
    gate = payload.get("operationalGate") or {}
    if gate:
        return gate
    activation = payload.get("activation") or {}
    return activation.get("operationalGate") or {}


def _extrair_posicao_sequencia(payload):
    if not isinstance(payload, dict):
        return {}
    position = payload.get("sequencePosition") or {}
    if position:
        return position
    gate = payload.get("operationalGate") or {}
    position = gate.get("sequencePosition") or {}
    if position:
        return position
    activation = payload.get("activation") or {}
    position = activation.get("sequencePosition") or {}
    if position:
        return position
    activation_gate = activation.get("operationalGate") or {}
    return activation_gate.get("sequencePosition") or {}


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias", "")
    base_path = Path(directory).expanduser() if directory else None
    if base_path and base_path.exists() and not base_path.is_dir():
        raise CommandError("--diretorio-evidencias deve apontar para um diretorio")

    def resolve(option_name, default_name, fallback_name=""):
        explicit = options.get(option_name) or ""
        if explicit:
            return explicit
        if base_path:
            default_path = base_path / default_name
            if default_path.exists():
                return str(default_path)
            if fallback_name:
                fallback_path = base_path / fallback_name
                if fallback_path.exists():
                    return str(fallback_path)
            return str(default_path)
        return ""

    return {
        "directory": directory,
        "windowValidation": resolve(
            "validacao_janela_json",
            "pm03-validacao-resultado-janela.json",
            fallback_name="pm03-validacao-feature-flag.json",
        ),
        "activationValidation": resolve(
            "validacao_ativacao_json",
            "pm03-validacao-ativacao-canonical-first.json",
        ),
        "monitor": resolve("monitor_json", "pm03-monitor-canonical-first.json"),
        "sourceAudit": resolve(
            "auditoria_fonte_json",
            "pm03-auditoria-fonte-escrita.json",
        ),
        "totalsAudit": resolve(
            "auditoria_totais_json",
            "pm03-auditoria-totais-negocio.json",
        ),
        "candidateDiscovery": resolve(
            "candidatos_canario_json",
            "pm03-candidatos-canario.json",
        ),
        "debtRegression": resolve(
            "regressao_dividas_json",
            "pm03-regressao-dividas-fcf.json",
        ),
    }


def _normalizar_arquivos_saida(options):
    directory = options.get("diretorio_evidencias", "")
    base_path = Path(directory).expanduser() if directory else None
    save_json = options.get("salvar_json", "")
    save_record = options.get("salvar_registro", "")
    if base_path:
        if not save_json:
            save_json = str(base_path / "pm03-fechamento-canonical-first.json")
        if not save_record:
            save_record = str(base_path / "pm03-fechamento-canonical-first.md")
    return {
        "json": save_json,
        "record": save_record,
    }


def _salvar_evidencias_fechamento(resultado):
    output_files = resultado.get("outputEvidenceFiles") or {}
    json_path = output_files.get("json")
    record_path = output_files.get("record")
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


def _check(key, label, issues):
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


def _exigir(condition, issues, message):
    if not condition:
        issues.append(message)


def _validar_window_outcome_payload(payload, issues, contexto):
    outcome = (payload or {}).get("windowOutcome") or {}
    if not outcome:
        return
    status = str(outcome.get("status") or "")
    _exigir(bool(status), issues, f"{contexto}: windowOutcome sem status")
    _exigir(
        status.startswith("approved"),
        issues,
        f"{contexto}: windowOutcome nao aprovado",
    )
    _exigir(
        status != "approvedWithLegacyTolerance",
        issues,
        f"{contexto}: windowOutcome indicou tolerancia a legado",
    )
    scope = str(outcome.get("nextActionScope") or "")
    if scope:
        _exigir(
            scope == "activationGate",
            issues,
            f"{contexto}: windowOutcome nextActionScope invalido",
        )


def _validar_auditorias_janela_payload(payload, issues, contexto):
    canonical_audit = (payload or {}).get("canonicalFirstAudit") or {}
    if canonical_audit:
        canonical = canonical_audit.get("canonicalFirst") or {}
        _exigir(
            int(canonical.get("count") or 0) > 0,
            issues,
            f"{contexto}: canonicalFirstAudit nao encontrou baixa canonical-first",
        )

    window_audit = (payload or {}).get("windowWriteAudit") or {}
    if window_audit:
        canonical = window_audit.get("canonicalFirst") or {}
        legado = window_audit.get("legacyAdapterSynced") or {}
        _exigir(
            int(canonical.get("count") or 0) > 0,
            issues,
            f"{contexto}: windowWriteAudit nao encontrou baixa canonical-first",
        )
        _exigir(
            int(legado.get("count") or 0) == 0,
            issues,
            f"{contexto}: windowWriteAudit encontrou baixa legada na janela",
        )


def _decimal_or_none(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _decimais_iguais(first, second):
    return first is not None and second is not None and first == second


def _int_or_zero(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _primeiro_valor(dados, *chaves):
    for chave in chaves:
        if chave in dados:
            return dados.get(chave)
    return None


def _validar_item_resultado_canario(
    source,
    item,
    canary_result,
    source_id_check,
    requested_realized_amount,
    issues,
):
    _exigir(
        isinstance(item, dict) and bool(item),
        issues,
        "item atualizado do canario nao foi registrado",
    )
    if not isinstance(item, dict):
        return

    _exigir(
        item.get("source") == source,
        issues,
        "origem do item atualizado do canario nao confere",
    )
    _exigir(
        str(_primeiro_valor(item, "sourceId", "source_id", "originId") or "")
        == str(source_id_check.get("sourceId") or canary_result.get("sourceId") or ""),
        issues,
        "sourceId do item atualizado do canario nao confere",
    )
    realized_amount = _decimal_or_none(
        _primeiro_valor(
            item,
            "realizedAmount",
            "paidAmount",
            "valor_realizado",
            "valor_pago",
        )
    )
    ledger_realized_amount = _decimal_or_none(
        _primeiro_valor(
            item,
            "ledgerRealizedAmount",
            "valor_realizado_ledger",
        )
    )
    _exigir(
        _decimais_iguais(realized_amount, requested_realized_amount),
        issues,
        "valor realizado do item atualizado do canario nao confere",
    )
    _exigir(
        _decimais_iguais(ledger_realized_amount, requested_realized_amount),
        issues,
        "valor realizado no ledger do item atualizado do canario nao confere",
    )
    _exigir(
        item.get("isLedgerReconciled") is True or item.get("conciliado_ledger") is True,
        issues,
        "item atualizado do canario nao ficou conciliado com ledger",
    )


def _validar_periodo_payload(
    payload_periodo,
    issues,
    data_inicial="",
    data_final="",
    contexto="janela",
):
    if data_inicial:
        _exigir(
            payload_periodo.get("startDate") == data_inicial,
            issues,
            f"{contexto}: data inicial nao confere",
        )
    if data_final:
        _exigir(
            payload_periodo.get("endDate") == data_final,
            issues,
            f"{contexto}: data final nao confere",
        )


def _registro_fechamento_pm03(resultado):
    issues = "; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"
    checks = "; ".join(
        f"{check['key']}={'ok' if check['ok'] else 'pendente'}"
        for check in resultado["checks"]
    )
    input_files = resultado.get("inputEvidenceFiles") or {}
    output_files = resultado.get("outputEvidenceFiles") or {}
    gate_summary = resultado.get("operationalGateSummary") or {}
    sequence_summary = resultado.get("sequencePositionSummary") or {}
    outcome_summary = resultado.get("windowOutcomeSummary") or {}
    audit_summary = resultado.get("windowWriteAuditSummary") or {}
    activation_canary_summary = resultado.get("activationCanarySummary") or {}
    candidate_summary = resultado.get("candidateActivationSummary") or {}
    list_health_summary = resultado.get("candidateListHealthSummary") or {}
    debt_regression_summary = resultado.get("debtRegressionSummary") or {}
    evidence_checklist = resultado.get("evidenceChecklist") or {}
    checks_summary = resultado.get("checksSummary") or {}
    missing_actions = resultado.get("missingEvidenceActions") or {}
    recommended_commands = resultado.get("recommendedCommands") or {}
    next_action = resultado.get("closureNextAction") or {}
    sequence_transition = resultado.get("sequenceTransition") or {}
    sequence_position = resultado.get("sequencePosition") or {}
    decision = resultado.get("closureDecision") or {}
    return "\n".join(
        [
            "### Registro PM-03 - fechamento de evidencias",
            "",
            f"Data/hora do fechamento: {resultado['generatedAt']}",
            f"Origem: {resultado['source']}",
            (
                "Periodo esperado: "
                f"{resultado['period']['startDate'] or '-'} a "
                f"{resultado['period']['endDate'] or '-'}"
            ),
            f"ready/issues: ready={resultado['ready']}; issues={issues}",
            f"Checks: {checks}",
            (
                "Resumo checks: "
                f"ready={checks_summary.get('ready')}; "
                f"ok={checks_summary.get('okCount')}; "
                f"pendentes={checks_summary.get('pendingCount')}; "
                f"pendingKeys={','.join(checks_summary.get('pending') or []) or '-'}"
            ),
            (
                "Acoes para evidencias faltantes: "
                f"ready={missing_actions.get('ready')}; "
                f"missing={missing_actions.get('missingCount')}; "
                f"next={((missing_actions.get('nextAction') or {}).get('key')) or '-'}; "
                f"command={((missing_actions.get('nextAction') or {}).get('command')) or '-'}; "
                f"rerun={missing_actions.get('rerunClosureCommand') or '-'}"
            ),
            (
                "Proxima acao fechamento: "
                f"key={next_action.get('key') or '-'}; "
                f"status={next_action.get('status') or '-'}; "
                f"nextStep={next_action.get('nextStep') or '-'}; "
                f"nextSource={next_action.get('nextSource') or '-'}; "
                f"evidence={next_action.get('evidenceKey') or '-'}; "
                f"command={next_action.get('command') or '-'}; "
                f"followUp={next_action.get('followUpCommand') or '-'}"
            ),
            (
                "Comandos recomendados: "
                f"nextEvidence={recommended_commands.get('nextMissingEvidence') or '-'}; "
                f"followUp={recommended_commands.get('followUp') or '-'}; "
                f"rerunClosure={recommended_commands.get('rerunClosure') or '-'}; "
                f"nextSequence={recommended_commands.get('nextSequenceValidation') or '-'}"
            ),
            (
                "Transicao da sequencia: "
                f"type={sequence_transition.get('type') or '-'}; "
                f"status={sequence_transition.get('status') or '-'}; "
                f"from={sequence_transition.get('fromStep') or '-'}; "
                f"to={sequence_transition.get('toStep') or '-'}; "
                f"toSource={sequence_transition.get('toSource') or '-'}"
            ),
            (
                "Transicao operacional: "
                f"primary={sequence_transition.get('primaryCommand') or '-'}; "
                f"followUp={sequence_transition.get('followUpCommand') or '-'}; "
                f"checklistReady={sequence_transition.get('reviewChecklistReady')}"
            ),
            (
                "Decisao PM-03: "
                f"status={decision.get('status') or '-'}; "
                f"step={decision.get('step') or '-'}; "
                f"mayMarkCurrentStepDone={decision.get('mayMarkCurrentStepDone')}; "
                f"mayAdvanceSequence={decision.get('mayAdvanceSequence')}; "
                f"nextStep={decision.get('nextStep') or '-'}; "
                f"nextSource={decision.get('nextSource') or '-'}; "
                f"blockedBy={'; '.join(decision.get('blockedBy') or []) or '-'}"
            ),
            (
                "Gate operacional: "
                f"available={gate_summary.get('available')}; "
                f"steps={','.join(gate_summary.get('currentSteps') or []) or '-'}; "
                f"sources={','.join(gate_summary.get('sources') or []) or '-'}; "
                f"statuses={','.join(gate_summary.get('statuses') or []) or '-'}; "
                f"consistentStep={gate_summary.get('consistentStep')}; "
                f"consistentSource={gate_summary.get('consistentSource')}"
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
            (
                "Sequencia nas evidencias: "
                f"available={sequence_summary.get('available')}; "
                f"steps={','.join(sequence_summary.get('steps') or []) or '-'}; "
                f"positions={','.join(str(item) for item in (sequence_summary.get('positions') or [])) or '-'}; "
                f"consistent={sequence_summary.get('consistent')}; "
                f"matchesExpected={sequence_summary.get('matchesExpected')}"
            ),
            (
                "Candidato x ativacao: "
                f"available={candidate_summary.get('available')}; "
                f"consistent={candidate_summary.get('consistent')}; "
                f"activationSourceId={candidate_summary.get('activationSourceId') or '-'}; "
                f"activationObligationId={candidate_summary.get('activationObligationId') or '-'}"
            ),
            (
                "Canario de ativacao: "
                f"available={activation_canary_summary.get('available')}; "
                f"executed={activation_canary_summary.get('executed')}; "
                f"synced={activation_canary_summary.get('synced')}; "
                f"sourceId={activation_canary_summary.get('sourceId') or '-'}; "
                f"paymentDate={activation_canary_summary.get('paymentDate') or '-'}; "
                f"matchesActivationDate={activation_canary_summary.get('matchesActivationDate')}; "
                f"writeModelSource={activation_canary_summary.get('writeModelSource') or '-'}"
            ),
            (
                "Saude da lista de candidatos: "
                f"available={list_health_summary.get('available')}; "
                f"statuses={','.join(list_health_summary.get('statuses') or []) or '-'}; "
                f"actions={','.join(list_health_summary.get('recommendedActions') or []) or '-'}; "
                f"requiresLimitIncrease={list_health_summary.get('requiresLimitIncrease')}"
            ),
            (
                "Regressao de dividas: "
                f"available={debt_regression_summary.get('available')}; "
                f"status={debt_regression_summary.get('status') or '-'}; "
                f"mayContinuePm03_4={debt_regression_summary.get('mayContinuePm03_4')}; "
                f"credores={debt_regression_summary.get('debtCreditorConsistent')}; "
                f"entradasFcf={debt_regression_summary.get('debtAutomaticFcfEntryConsistent')}; "
                f"preflight={debt_regression_summary.get('financialPreflightReady')}"
            ),
            (
                "Resultado da janela: "
                f"available={outcome_summary.get('available')}; "
                f"statuses={','.join(outcome_summary.get('statuses') or []) or '-'}; "
                f"consistentStatus={outcome_summary.get('consistentStatus')}"
            ),
            (
                "Auditoria da janela: "
                f"available={audit_summary.get('available')}; "
                f"consistentCounts={audit_summary.get('consistentCounts')}"
            ),
            (
                "Checklist de evidencias: "
                f"ready={evidence_checklist.get('ready')}; "
                f"required={evidence_checklist.get('requiredCount')}; "
                f"foundRequired={evidence_checklist.get('foundRequiredCount')}; "
                f"missingRequired={','.join(evidence_checklist.get('missingRequired') or []) or '-'}"
            ),
            (
                "Evidencias lidas: "
                f"diretorio={input_files.get('directory') or '-'}; "
                f"ativacao={input_files.get('activationValidation') or '-'}; "
                f"candidatos={input_files.get('candidateDiscovery') or '-'}; "
                f"validacao={input_files.get('windowValidation') or '-'}; "
                f"monitor={input_files.get('monitor') or '-'}; "
                f"fonte={input_files.get('sourceAudit') or '-'}; "
                f"totais={input_files.get('totalsAudit') or '-'}; "
                f"regressaoDividas={input_files.get('debtRegression') or '-'}"
            ),
            (
                "Arquivos salvos: "
                f"json={output_files.get('json') or '-'}; "
                f"registro={output_files.get('record') or '-'}"
            ),
            (
                "Decisao: marcar a subetapa da origem como concluida somente "
                "se ready=True e apos as revisoes obrigatorias."
            ),
        ]
    )


def formatar_erro_fechamento_pm03(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Fechamento PM-03 nao aprovado: {issues[0]}"
    return "Fechamento PM-03 nao aprovado."
