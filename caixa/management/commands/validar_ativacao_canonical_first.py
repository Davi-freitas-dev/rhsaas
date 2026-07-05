import json
from pathlib import Path

from django.core.exceptions import FieldError, PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.contracts_obrigacoes import (
    CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
    estado_ativacao_canonical_first,
)
from caixa.management.commands.testar_baixa_canonical_first import (
    testar_baixa_canonical_first,
)
from caixa.management.commands.verificar_prontidao_escrita_canonica import (
    verificar_prontidao_escrita_canonica,
)
from caixa.models import ObrigacaoFinanceira
from caixa.pm03_sequence import SOURCE_PM03_STEPS, montar_posicao_sequencia_pm03
from caixa.services_modelagem_canonica import (
    verificar_paridade_modelagem_financeira_canonica,
)
from tenancy.command_guards import ensure_tenant_schema

CANARY_CANDIDATE_LIMIT = 5
PM03_DIRECT_SOURCE_STEPS = SOURCE_PM03_STEPS


class Command(BaseCommand):
    help = (
        "Valida se uma origem pode entrar em uma janela controlada de "
        "canonical-first. O comando e somente leitura; o canario usa rollback."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--username")
        parser.add_argument("--source-id", dest="source_id")
        parser.add_argument("--payment-date", dest="payment_date")
        parser.add_argument(
            "--executar-canario",
            action="store_true",
            help="Executa o canario rollback-only para a origem informada.",
        )
        parser.add_argument(
            "--exigir-canario",
            action="store_true",
            help=(
                "Marca a validacao como pendente se o canario rollback-only "
                "nao for executado com sucesso."
            ),
        )
        parser.add_argument(
            "--exigir-source-id-canario",
            action="store_true",
            help=(
                "Reprova a validacao se o canario for solicitado sem "
                "--source-id explicito."
            ),
        )
        parser.add_argument(
            "--exigir-data-pagamento-canario",
            "--require-canary-payment-date",
            action="store_true",
            help=(
                "Reprova a validacao se o canario for solicitado sem "
                "--payment-date explicito."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON para automacoes.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON da validacao de ativacao em um arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown da validacao de ativacao em um arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help=(
                "Diretorio opcional para gerar arquivos padronizados de "
                "evidencia da ativacao PM-03."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os caminhos de evidencia da ativacao PM-03 nao "
                "forem informados por --diretorio-evidencias ou caminhos "
                "explicitos."
            ),
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando a origem nao estiver pronta para a janela.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias canonicas avaliadas.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("validar_ativacao_canonical_first", action="validar dados operacionais")
        evidence_files = _normalizar_arquivos_evidencia(options)
        if options["exigir_arquivos_evidencia"]:
            _exigir_arquivos_evidencia(evidence_files)

        payment_date_informada = bool(options.get("payment_date"))
        try:
            resultado = validar_ativacao_canonical_first(
                source=options["source"],
                username=options.get("username"),
                source_id=options.get("source_id"),
                payment_date=(
                    options.get("payment_date") or timezone.localdate().isoformat()
                ),
                executar_canario=options["executar_canario"],
                exigir_canario=options["exigir_canario"],
                exigir_source_id_canario=options["exigir_source_id_canario"],
                exigir_data_pagamento_canario=options[
                    "exigir_data_pagamento_canario"
                ],
                payment_date_informada=payment_date_informada,
                limit=options["limit"],
            )
        except (ValidationError, PermissionDenied) as exc:
            raise CommandError(_formatar_erro(exc)) from exc

        resultado["evidenceFiles"] = evidence_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_ativacao_pm03(resultado),
        }
        _salvar_evidencias_ativacao(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_ativacao_nao_pronta(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Ativacao canonical-first pronta para janela.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Ativacao canonical-first com pontos de atencao."
                )
            )

        self.stdout.write(f"Origem: {resultado['source']}")
        pendencias = resultado["pendingObligations"]
        self.stdout.write(
            "Obrigacoes pendentes: "
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
                f"retornados={candidate_list_health.get('returnedCount')}; "
                f"elegiveis={candidate_list_health.get('eligibleCount')}; "
                f"acao={candidate_list_health.get('recommendedAction') or '-'}"
            )
        self._imprimir_candidatos_canario(pendencias)
        self._imprimir_pendencias_sem_canario(pendencias)
        self.stdout.write(
            "Paridade canonica: "
            + ("ok" if resultado["canonicalParity"]["consistent"] else "pendente")
        )
        self.stdout.write(
            "Prontidao de escrita: "
            + ("ok" if resultado["writeReadiness"]["ready"] else "pendente")
        )

        if resultado["canary"]["executed"]:
            self.stdout.write(
                "Canario rollback-only: "
                + ("ok" if resultado["canary"]["synced"] else "pendente")
            )
        elif resultado["canary"].get("required"):
            self.stdout.write("Canario rollback-only: exigido e nao executado")
        else:
            self.stdout.write("Canario rollback-only: nao executado")
        source_id_check = formatar_source_id_check(
            resultado["canary"].get("sourceIdCheck")
        )
        if source_id_check != "-":
            self.stdout.write(f"Canario sourceId: {source_id_check}")
        if resultado["canary"].get("paymentDateRequired"):
            self.stdout.write(
                "Canario paymentDate: "
                f"required=True; "
                f"provided={resultado['canary'].get('paymentDateProvided')}; "
                f"date={resultado['canary'].get('paymentDate') or '-'}"
            )

        for issue in resultado["issues"]:
            self.stdout.write(f"- {issue}")

        self.stdout.write(
            "Env sugerido: "
            f"CANONICAL_FIRST_SETTLEMENT_ENABLED=True; "
            "CANONICAL_FIRST_SETTLEMENT_SOURCES="
            f"{resultado['recommendedEnvironment']['CANONICAL_FIRST_SETTLEMENT_SOURCES']}"
        )
        comando_canario = (resultado.get("recommendedCommands") or {}).get(
            "canaryRollbackOnly"
        )
        if comando_canario:
            self.stdout.write(f"Canario sugerido: {comando_canario}")
        comando_descoberta = (resultado.get("recommendedCommands") or {}).get(
            "candidateDiscovery"
        )
        if comando_descoberta:
            self.stdout.write(f"Descobrir candidato: {comando_descoberta}")
        comandos_regressao = (resultado.get("recommendedCommands") or {}).get(
            "debtRegression"
        ) or []
        if comandos_regressao:
            self.stdout.write(f"Regressao obrigatoria: {comandos_regressao[0]}")
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
                f"step={decisao.get('step') or '-'}; "
                "mayRunCanaryRollbackOnly="
                f"{decisao.get('mayRunCanaryRollbackOnly')}; "
                "mayActivateAllowlistWindow="
                f"{decisao.get('mayActivateAllowlistWindow')}; "
                "requiresControlledCandidate="
                f"{decisao.get('requiresControlledCandidate')}; "
                f"blockedBy={'; '.join(decisao.get('blockedBy') or []) or '-'}"
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
        gate = resultado.get("operationalGate") or {}
        if gate:
            self.stdout.write(
                "Gate operacional: "
                f"{gate.get('currentStep') or '-'}; "
                f"{gate.get('statusLabel') or gate.get('status') or '-'}"
            )
            allowed = gate.get("allowedActions") or []
            if allowed:
                self.stdout.write(f"Acao permitida: {allowed[0]}")
            blocked = gate.get("blockedActions") or []
            if blocked:
                self.stdout.write(f"Acao bloqueada: {blocked[0]}")

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

    def _imprimir_pendencias_sem_canario(self, pendencias):
        itens = pendencias.get("nonCanaryPendingItems") or []
        if not itens:
            return

        self.stdout.write("Pendencias sem canario:")
        for item in itens:
            self.stdout.write(
                "- "
                f"sourceId={item['sourceId']}; "
                f"obrigacao={item['obligationId']}; "
                f"tipo={item['obligationType']}; "
                f"pendente={item['pendingAmount']}; "
                f"motivo={item['ineligibilityReason']}"
            )


def validar_ativacao_canonical_first(
    source,
    username=None,
    source_id=None,
    payment_date=None,
    executar_canario=False,
    exigir_canario=False,
    exigir_source_id_canario=False,
    exigir_data_pagamento_canario=False,
    payment_date_informada=None,
    limit=20,
):
    source = str(source or "").strip()
    source_id = str(source_id or "").strip()
    payment_date_informada = (
        bool(payment_date) if payment_date_informada is None else payment_date_informada
    )
    payment_date_explicita = str(payment_date or "") if payment_date_informada else ""
    issues = []

    write_readiness = verificar_prontidao_escrita_canonica()
    canonical_parity = verificar_paridade_modelagem_financeira_canonica(limit=limit)
    pending_summary = resumir_obrigacoes_pendentes(source)
    source_id_check = checar_source_id_canario(source, source_id)
    canary = {
        "required": exigir_canario,
        "sourceIdRequired": exigir_source_id_canario,
        "paymentDateRequired": exigir_data_pagamento_canario,
        "paymentDateProvided": payment_date_informada,
        "paymentDate": payment_date_explicita,
        "sourceIdCheck": source_id_check,
        "executed": False,
        "synced": None,
        "result": None,
        "error": "",
    }

    if source not in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES:
        issues.append(
            f"{source}: origem nao suporta janela canonical-first direta."
        )

    if not write_readiness["ready"]:
        issues.extend(write_readiness["inconsistencies"])

    if not canonical_parity["consistent"]:
        total = sum(
            grupo["missing"] + grupo["divergent"] + grupo["extra"]
            for grupo in (
                canonical_parity["obrigacoes"],
                canonical_parity["baixas"],
                canonical_parity["alocacoes"],
            )
        )
        issues.append(f"Paridade canonica possui {total} inconsistencia(s).")

    if source_id_check["provided"] and not source_id_check["eligible"]:
        issues.append(source_id_check["issue"])

    if executar_canario:
        if not username:
            issues.append("Informe --username para executar o canario.")
        elif exigir_source_id_canario and not source_id:
            issues.append(
                "Informe --source-id para executar canario rollback-only controlado."
            )
        elif exigir_data_pagamento_canario and not payment_date_informada:
            issues.append(
                "Informe --payment-date para executar canario rollback-only com data explicita."
            )
        elif source_id_check["provided"] and not source_id_check["eligible"]:
            pass
        elif source in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES:
            try:
                canary_result = testar_baixa_canonical_first(
                    username=username,
                    source=source,
                    source_id=source_id,
                    payment_date=payment_date,
                )
                canary = {
                    "required": exigir_canario,
                    "sourceIdRequired": exigir_source_id_canario,
                    "paymentDateRequired": exigir_data_pagamento_canario,
                    "paymentDateProvided": payment_date_informada,
                    "paymentDate": payment_date_explicita,
                    "sourceIdCheck": source_id_check,
                    "executed": True,
                    "synced": canary_result["canonicalSettlement"]["synced"],
                    "result": canary_result,
                    "error": "",
                }
                if not canary["synced"]:
                    issues.append("Canario rollback-only nao ficou sincronizado.")
            except (ValidationError, PermissionDenied) as exc:
                canary = {
                    "required": exigir_canario,
                    "sourceIdRequired": exigir_source_id_canario,
                    "paymentDateRequired": exigir_data_pagamento_canario,
                    "paymentDateProvided": payment_date_informada,
                    "paymentDate": payment_date_explicita,
                    "sourceIdCheck": source_id_check,
                    "executed": True,
                    "synced": False,
                    "result": None,
                    "error": _formatar_erro(exc),
                }
                issues.append(f"Canario rollback-only falhou: {canary['error']}")

    if exigir_canario and not canary["executed"]:
        issues.append("Canario rollback-only exigido, mas nao executado.")

    ambiente_recomendado = montar_ambiente_recomendado(source)
    comandos_recomendados = montar_comandos_recomendados(
        source=source,
        username=username,
        source_id=source_id,
        payment_date=payment_date_explicita,
        pending_summary=pending_summary,
    )
    proxima_acao = montar_proxima_acao(
        issues=issues,
        pending_summary=pending_summary,
        canary=canary,
        recommended_commands=comandos_recomendados,
    )
    gate_operacional = montar_gate_operacional(
        source=source,
        pending_summary=pending_summary,
        canary=canary,
        next_action=proxima_acao,
        candidate_discovery_command=comandos_recomendados.get("candidateDiscovery"),
    )
    orientacao_candidato = montar_orientacao_candidato_controlado(
        source=source,
        payment_date=payment_date_explicita,
        candidate_discovery_command=comandos_recomendados.get("candidateDiscovery"),
        after_create_commands=comandos_recomendados.get(
            "afterControlledCandidateCreate"
        ),
    )
    orientacao_candidato = anotar_orientacao_candidato_controlado(
        orientacao_candidato,
        pending_summary,
    )
    saude_lista_candidatos = resumir_saude_lista_candidatos(pending_summary)
    decisao_ativacao = montar_decisao_ativacao_pm03(
        source=source,
        issues=issues,
        pending_summary=pending_summary,
        canary=canary,
        next_action=proxima_acao,
        operational_gate=gate_operacional,
        recommended_commands=comandos_recomendados,
    )

    return {
        "ready": not issues,
        "source": source,
        "recommendedEnvironment": ambiente_recomendado,
        "recommendedCommands": comandos_recomendados,
        "activationDecision": decisao_ativacao,
        "nextAction": proxima_acao,
        "operationalGate": gate_operacional,
        "sequencePosition": montar_posicao_sequencia_pm03(source),
        "candidateCreationGuidance": orientacao_candidato,
        "candidateListHealth": saude_lista_candidatos,
        "pendingObligations": {
            **pending_summary,
            "requiresCanaryData": (
                executar_canario and pending_summary["canaryEligibleCount"] == 0
            ),
        },
        "writeReadiness": {
            "ready": write_readiness["ready"],
            "featureFlagEnabled": write_readiness["featureFlagEnabled"],
            "featureFlagSources": write_readiness["featureFlagSources"],
            "currentWriteMode": write_readiness["currentWriteMode"],
            "targetWriteMode": write_readiness["targetWriteMode"],
            "directCanonicalFirstSources": write_readiness[
                "directCanonicalFirstSources"
            ],
            "adapterOnlySources": write_readiness["adapterOnlySources"],
            "pm04DecisionMatrix": write_readiness["pm04DecisionMatrix"],
            "enabledCanonicalFirstSources": write_readiness[
                "enabledCanonicalFirstSources"
            ],
            "invalidFeatureFlagSources": write_readiness[
                "invalidFeatureFlagSources"
            ],
            "issues": write_readiness["inconsistencies"],
        },
        "canonicalParity": {
            "consistent": canonical_parity["consistent"],
            "obrigacoes": canonical_parity["obrigacoes"],
            "baixas": canonical_parity["baixas"],
            "alocacoes": canonical_parity["alocacoes"],
            "issues": canonical_parity["issues"],
        },
        "canary": canary,
        "issues": issues,
    }


def montar_gate_operacional(
    source,
    pending_summary,
    canary,
    next_action,
    candidate_discovery_command=None,
):
    source = str(source or "").strip()
    current_step = PM03_DIRECT_SOURCE_STEPS.get(source, "PM-03")
    next_key = (next_action or {}).get("key") or ""
    canary_count = int((pending_summary or {}).get("canaryEligibleCount") or 0)
    status = "blockedValidationIssues"
    status_label = "Corrigir pendencias de validacao"
    allowed_actions = [
        "Corrigir as pendencias indicadas e repetir a validacao read-only.",
    ]

    if next_key == "activateAllowlistWindow":
        status = "readyForAllowlistWindow"
        status_label = "Canario sincronizado; janela allowlist pode ser aberta"
        allowed_actions = [
            "Abrir janela controlada com backup, flag, allowlist e auditorias.",
            "Executar uma baixa real controlada somente depois da flag ativa.",
            "Validar auditoria, monitoramento e fechamento PM-03 ready=True.",
        ]
    elif next_key == "runCanaryRollbackOnly":
        status = "readyForCanaryRollbackOnly"
        status_label = "Candidato disponivel para canario rollback-only"
        allowed_actions = [
            "Executar canario rollback-only com --source-id e --payment-date explicitos.",
            "Salvar evidencias da validacao de ativacao no diretorio PM-03 da origem.",
        ]
    elif next_key == "awaitCanaryCandidate":
        status = "blockedAwaitingCanaryCandidate"
        status_label = "Bloqueada por falta de candidato real/controlado"
        allowed_actions = _acoes_permitidas_sem_candidato(source)
    elif next_key == "expandCanaryCandidateList":
        status = "blockedCandidateListLimit"
        status_label = "Reexecutar descoberta com limite maior"
        allowed_actions = [
            "Reexecutar a descoberta de candidato com --limit maior que 0.",
            "Selecionar um source-id retornado em canaryCandidates.",
            "Repetir a validacao de ativacao antes de qualquer allowlist.",
        ]
    elif next_key == "fixCanarySourceId":
        status = "blockedInvalidCanarySourceId"
        status_label = "Corrigir source-id do canario"
        allowed_actions = [
            "Escolher um source-id presente em canaryCandidates.",
            "Repetir a validacao de ativacao antes de qualquer allowlist.",
        ]

    return {
        "currentStep": current_step,
        "source": source,
        "sequencePosition": montar_posicao_sequencia_pm03(source),
        "status": status,
        "statusLabel": status_label,
        "entryGate": _gate_entrada_pm03(source),
        "exitGate": _gate_saida_pm03(source),
        "canaryCandidateCriteria": _criterios_candidato_canario_pm03(source),
        "sequenceNote": _nota_sequencia_pm03(source),
        "canaryCandidateCount": canary_count,
        "canaryExecuted": bool((canary or {}).get("executed")),
        "canarySynced": (canary or {}).get("synced"),
        "allowedActions": allowed_actions,
        "blockedActions": _acoes_bloqueadas_pm03(source, status),
        "candidateDiscoveryCommand": (
            candidate_discovery_command or montar_comando_descoberta_candidato(source)
        ),
        "debtRegressionRequired": source == "financiamento_movimentacao",
        "debtRegressionCommands": montar_comandos_regressao_dividas(source),
        "evidenceRequired": [
            "validacao de ativacao com canario rollback-only",
            "validacao de feature flag ou resultado da janela",
            "auditoria de fonte de escrita",
            "monitoramento sem legado na janela",
            "auditoria de totais de negocio",
            "fechamento PM-03 ready=True",
        ],
    }


def montar_decisao_ativacao_pm03(
    source,
    issues,
    pending_summary,
    canary,
    next_action,
    operational_gate,
    recommended_commands,
):
    issues = [str(issue) for issue in (issues or []) if str(issue)]
    pending_summary = pending_summary or {}
    canary = canary or {}
    next_action = next_action or {}
    operational_gate = operational_gate or {}
    recommended_commands = recommended_commands or {}
    candidates = pending_summary.get("canaryCandidates") or []
    first_candidate = candidates[0] if candidates else {}
    source_id_check = canary.get("sourceIdCheck") or {}
    result = canary.get("result") or {}

    selected_source_id = (
        str(source_id_check.get("sourceId") or "")
        or str(result.get("sourceId") or "")
        or str(first_candidate.get("sourceId") or "")
    )
    selected_obligation_id = (
        str(source_id_check.get("obligationId") or "")
        or str(result.get("obligationId") or "")
        or str(first_candidate.get("obligationId") or "")
    )
    next_key = next_action.get("key") or ""
    may_activate = bool(canary.get("executed") and canary.get("synced") and not issues)
    may_run = (
        not issues
        and not may_activate
        and next_key == "runCanaryRollbackOnly"
        and int(pending_summary.get("canaryEligibleCount") or 0) > 0
        and bool(candidates)
    )
    requires_candidate = (
        not may_activate
        and not may_run
        and int(pending_summary.get("canaryEligibleCount") or 0) == 0
    )

    if may_activate:
        status = "readyForAllowlistWindow"
        label = "Canario validado; janela de allowlist liberada"
        detail = (
            "Canario rollback-only sincronizado; pode ativar a origem na "
            "janela controlada."
        )
        blocked_by = []
    elif may_run:
        status = "readyForCanaryRollbackOnly"
        label = "Candidato pronto para canario rollback-only"
        detail = "Executar o canario rollback-only com sourceId e data explicitos."
        blocked_by = []
    elif next_key == "fixCanarySourceId":
        status = "blockedFixCanarySourceId"
        label = "Corrigir sourceId do canario"
        detail = next_action.get("detail") or "sourceId do canario nao elegivel."
        blocked_by = issues or [detail]
    elif next_key == "awaitCanaryCandidate":
        status = "awaitCanaryCandidate"
        label = "Aguardar ou criar candidato controlado"
        detail = next_action.get("detail") or "Nenhum candidato elegivel para canario."
        blocked_by = issues or [detail]
    elif next_key == "expandCanaryCandidateList":
        status = "blockedCandidateListLimit"
        label = "Reexecutar descoberta com limite maior"
        detail = (
            next_action.get("detail")
            or "Lista de candidatos nao retornou sourceId selecionavel."
        )
        blocked_by = issues or [detail]
    else:
        status = "blocked"
        label = "Ativacao PM-03 bloqueada"
        detail = next_action.get("detail") or "Resolver pendencias antes de continuar."
        blocked_by = issues or [detail]

    return {
        "status": status,
        "label": label,
        "source": source,
        "step": operational_gate.get("currentStep") or "",
        "mayRunCanaryRollbackOnly": may_run,
        "mayActivateAllowlistWindow": may_activate,
        "requiresControlledCandidate": requires_candidate,
        "selectedSourceId": selected_source_id,
        "selectedObligationId": selected_obligation_id,
        "canaryExecuted": bool(canary.get("executed")),
        "canarySynced": canary.get("synced"),
        "blockedBy": blocked_by,
        "suggestedCommand": _comando_sugerido_decisao_ativacao(
            may_run=may_run,
            next_action=next_action,
            recommended_commands=recommended_commands,
        ),
        "detail": detail,
    }


def _comando_sugerido_decisao_ativacao(may_run, next_action, recommended_commands):
    if may_run:
        return recommended_commands.get("canaryRollbackOnly") or ""
    if (next_action or {}).get("key") == "expandCanaryCandidateList":
        return (
            (next_action or {}).get("suggestedCommand")
            or (recommended_commands or {}).get("candidateDiscovery")
            or ""
        )
    return ""


def _acoes_permitidas_sem_candidato(source):
    if source == "investimento":
        return [
            (
                "Confirmar, criar ou aguardar investimento FCI real/controlado "
                "a pagar com saldo pendente no servidor/homologacao."
            ),
            "Repetir as validacoes read-only de PM-03.3 sem ampliar allowlist.",
        ]
    if source == "financiamento_movimentacao":
        return [
            (
                "Confirmar, criar ou aguardar movimentacao FCF real/controlada "
                "a pagar com saldo pendente no servidor/homologacao."
            ),
            (
                "Reexecutar regressao de dividas emprestimo/financiamento "
                "antes de qualquer allowlist."
            ),
        ]
    return [
        "Confirmar, criar ou aguardar obrigacao a pagar real/controlada pendente.",
        "Repetir as validacoes read-only sem ampliar allowlist.",
    ]


def _gate_entrada_pm03(source):
    if source == "investimento":
        return (
            "Existir investimento FCI real/controlado de saida, pendente, "
            "com source-id e payment-date explicitos para canario rollback-only."
        )
    if source == "financiamento_movimentacao":
        return (
            "PM-03.3 concluida e existencia de movimentacao FCF real/controlada de saida "
            "a pagar, pendente, com source-id e payment-date explicitos."
        )
    return (
        "Origem direta com obrigacao a pagar pendente, paridade canonica "
        "consistente e pre-flight operacional pronto."
    )


def _gate_saida_pm03(source):
    return (
        "Canario rollback-only sincronizado, allowlist controlada, primeira "
        "baixa real canonicalFirst auditada, monitoramento sem legado, totais "
        "de negocio consistentes e fechamento PM-03 ready=True."
    )


def _criterios_candidato_canario_pm03(source):
    criterios_comuns = [
        "obrigacao canonica do tipo pagar",
        "valor_pendente maior que zero",
        "source-id informado explicitamente",
        "payment-date informado explicitamente",
    ]
    if source == "investimento":
        return [
            "Investimento.tipo_fluxo=saida",
            "investimento nao cancelado",
            *criterios_comuns,
        ]
    if source == "financiamento_movimentacao":
        return [
            "Movimentacao FCF tipo_fluxo=saida",
            "movimentacao nao cancelada",
            "PM-03.3 investimento concluida",
            *criterios_comuns,
        ]
    return criterios_comuns


def _nota_sequencia_pm03(source):
    if source == "investimento":
        return (
            "PM-03.3 e o ponto de retomada atual; PM-03.4 e PM-04 permanecem "
            "bloqueadas para ativacao ate este gate fechar."
        )
    if source == "financiamento_movimentacao":
        return (
            "PM-03.4 e o ponto de retomada atual apos o fechamento da PM-03.3; "
            "PM-04 permanece bloqueada ate este gate fechar."
        )
    return (
        "A origem atual deve fechar seu gate antes de qualquer avanco "
        "operacional para subetapa futura."
    )


def _acoes_bloqueadas_pm03(source, status):
    blocked = []
    if status != "readyForAllowlistWindow":
        blocked.append("Adicionar a origem na allowlist canonical-first.")
    if status not in {"readyForCanaryRollbackOnly", "readyForAllowlistWindow"}:
        blocked.append(
            "Executar canario sem candidato, --source-id e --payment-date explicitos."
        )
    if status != "readyForAllowlistWindow":
        blocked.append("Fazer baixa real canonical-first da origem.")
    blocked.append("Marcar a subetapa como concluida antes do fechamento PM-03.")
    if source == "investimento":
        blocked.append("Ativar PM-03.4 ou iniciar PM-04 antes de concluir PM-03.3.")
    elif source == "financiamento_movimentacao":
        blocked.append(
            "Iniciar PM-04 ou marcar PM-03.4 concluida antes de caso FCF, "
            "regressao de dividas e fechamento PM-03."
        )
    else:
        blocked.append("Avancar etapa futura enquanto o gate atual estiver aberto.")
    return blocked


def contar_obrigacoes_pendentes(source):
    return resumir_obrigacoes_pendentes(source)["count"]


def montar_ambiente_recomendado(source):
    source = str(source or "").strip()
    fontes_ativas = estado_ativacao_canonical_first()["enabledSources"]
    fontes_recomendadas = sorted(set(fontes_ativas) | ({source} if source else set()))
    return {
        "CANONICAL_FIRST_SETTLEMENT_ENABLED": "True",
        "CANONICAL_FIRST_SETTLEMENT_SOURCES": ",".join(fontes_recomendadas),
        "sourceToActivate": source,
        "enabledSourcesToKeep": fontes_ativas,
    }


def montar_comandos_recomendados(
    source,
    username=None,
    source_id=None,
    payment_date=None,
    pending_summary=None,
):
    source = str(source or "").strip()
    pending_summary = pending_summary or {}
    candidatos = pending_summary.get("canaryCandidates") or []
    source_id_recomendado = source_id or (
        candidatos[0].get("sourceId") if candidatos else ""
    )
    slug = source.replace("_", "-") or "origem"

    commands = {
        "canaryRollbackOnly": (
            "python manage.py validar_ativacao_canonical_first "
            f"--source={source} "
            f"--username={username or '<usuario>'} "
            f"--source-id={source_id_recomendado or '<sourceId-de-canaryCandidates>'} "
            f"--payment-date={payment_date or '<DATA>'} "
            "--executar-canario --exigir-canario --exigir-source-id-canario "
            "--exigir-data-pagamento-canario "
            f"--diretorio-evidencias=<diretorio-evidencias-pm03-{slug}> "
            "--exigir-arquivos-evidencia --json --falhar"
        ),
    }
    candidate_discovery = montar_comando_descoberta_candidato(
        source,
        username=username,
        payment_date=payment_date,
    )
    if candidate_discovery:
        commands["candidateDiscovery"] = candidate_discovery
    debt_regression = montar_comandos_regressao_dividas(source)
    if debt_regression:
        commands["debtRegression"] = debt_regression
    after_create = montar_comandos_pos_criacao_candidato_controlado(
        source=source,
        candidate_discovery_command=candidate_discovery,
        debt_regression_commands=debt_regression,
        canary_command=commands["canaryRollbackOnly"],
    )
    if after_create:
        commands["afterControlledCandidateCreate"] = after_create
    return commands


def montar_comando_descoberta_candidato(source, username=None, payment_date=None):
    if source in {"investimento", "financiamento_movimentacao"}:
        slug = source.replace("_", "-")
        parts = [
            "python manage.py listar_candidatos_canario_pm03",
            f"--source={source}",
        ]
        if username:
            parts.append(f"--username={username}")
        if payment_date:
            parts.append(f"--payment-date={payment_date}")
        parts.extend(
            [
                f"--diretorio-evidencias=<diretorio-evidencias-pm03-{slug}>",
                "--exigir-arquivos-evidencia",
                "--json",
                "--falhar",
            ]
        )
        return " ".join(parts)
    return ""


def montar_comandos_regressao_dividas(source):
    if source != "financiamento_movimentacao":
        return []
    slug = source.replace("_", "-")
    return [
        (
            "python manage.py validar_regressao_dividas_pm03 "
            f"--source={source} "
            f"--diretorio-evidencias=<diretorio-evidencias-pm03-{slug}> "
            "--exigir-arquivos-evidencia --json --falhar"
        ),
        "python manage.py sincronizar_credores_dividas_fcf --json --falhar-com-pendencia",
        "python manage.py sincronizar_entradas_fcf_dividas --json --falhar-com-pendencia",
        "python manage.py validar_preflight_deploy_financeiro --falhar --json",
    ]


def montar_comandos_pos_criacao_candidato_controlado(
    source,
    candidate_discovery_command="",
    debt_regression_commands=None,
    canary_command="",
):
    source = str(source or "").strip()
    if source not in {"investimento", "financiamento_movimentacao"}:
        return []

    commands = [
        "python manage.py sincronizar_modelagem_financeira_canonica --aplicar --json",
        "python manage.py verificar_paridade_modelagem_canonica --json --falhar",
        (
            "python manage.py validar_operacao_obrigacoes "
            "--validar-canonico --validar-escrita-canonica "
            "--validar-valores-editaveis --json --falhar"
        ),
    ]
    if candidate_discovery_command:
        commands.append(candidate_discovery_command)
    commands.extend(debt_regression_commands or [])
    if canary_command:
        commands.append(canary_command)
    return commands


def montar_orientacao_candidato_controlado(
    source,
    payment_date=None,
    candidate_discovery_command="",
    after_create_commands=None,
):
    source = str(source or "").strip()
    data_referencia = str(payment_date or "<DATA>").strip() or "<DATA>"
    if source == "investimento":
        fields = {
            "descricao": f"CANARIO PM-03.3 investimento saida {data_referencia}",
            "categoria": "software",
            "tipo_fluxo": "saida",
            "valor_previsto": "1.00",
            "valor_realizado": "0.00",
            "data_prevista": data_referencia,
            "data_realizacao": "",
            "status": "planejado",
            "ativo": "True",
        }
        criteria = [
            "usar tipo_fluxo=saida para gerar obrigacao a pagar",
            "tipo_fluxo=entrada gera obrigacao a receber e nao vira candidato rollback-only",
            "manter valor_realizado=0.00 para preservar saldo pendente",
            "nao marcar baixa manual antes do canario rollback-only",
        ]
        admin_path = "/admin/caixa/investimento/add/"
        step = "PM-03.3"
    elif source == "financiamento_movimentacao":
        fields = {
            "descricao": (
                f"CANARIO PM-03.4 financiamento_movimentacao saida {data_referencia}"
            ),
            "categoria": "emprestimo",
            "tipo_fluxo": "saida",
            "valor_previsto": "1.00",
            "valor_realizado": "0.00",
            "data_prevista": data_referencia,
            "data_realizacao": "",
            "status": "planejado",
            "ativo": "True",
        }
        criteria = [
            "usar tipo_fluxo=saida para gerar obrigacao a pagar FCF",
            "tipo_fluxo=entrada gera obrigacao a receber FCF e nao vira candidato rollback-only",
            "manter valor_realizado=0.00 para preservar saldo pendente",
            "nao associar a entrada automatica de divida; a PM-03.4 testa a saida",
            "rodar a regressao de dividas antes de ampliar allowlist",
        ]
        admin_path = "/admin/caixa/financiamentomovimentacao/add/"
        step = "PM-03.4"
    else:
        return {
            "available": False,
            "source": source,
            "step": "",
            "adminPath": "",
            "criteria": [],
            "suggestedFields": {},
            "afterCreateCommands": [],
        }

    after_create = after_create_commands
    if after_create is None:
        after_create = montar_comandos_pos_criacao_candidato_controlado(
            source=source,
            candidate_discovery_command=candidate_discovery_command,
            debt_regression_commands=montar_comandos_regressao_dividas(source),
            canary_command="",
        )

    return {
        "available": True,
        "source": source,
        "step": step,
        "adminPath": admin_path,
        "criteria": criteria,
        "suggestedFields": fields,
        "afterCreateCommands": after_create,
    }


def anotar_orientacao_candidato_controlado(orientacao, pending_summary):
    orientacao = dict(orientacao or {})
    canary_count = int((pending_summary or {}).get("canaryEligibleCount") or 0)
    returned_canary_count = int(
        (pending_summary or {}).get("canaryCandidatesReturnedCount")
        if (pending_summary or {}).get("canaryCandidatesReturnedCount") is not None
        else len((pending_summary or {}).get("canaryCandidates") or [])
    )
    non_canary_count = int((pending_summary or {}).get("nonCanaryPendingCount") or 0)
    has_ready_candidate = canary_count > 0 and returned_canary_count > 0
    has_hidden_candidate = canary_count > 0 and returned_canary_count == 0
    available = bool(orientacao.get("available"))
    required_for_next_canary = (
        available and not has_ready_candidate and not has_hidden_candidate
    )

    if not available:
        action = "notAvailable"
        reason = "Origem sem orientacao de candidato controlado."
    elif has_ready_candidate:
        action = "useExistingCandidate"
        reason = "Ja ha candidato a pagar elegivel para canario rollback-only."
    elif has_hidden_candidate:
        action = "expandCandidateList"
        reason = (
            "Ha candidato a pagar elegivel, mas a listagem nao retornou "
            "sourceId; reexecutar a descoberta com limite maior."
        )
    elif non_canary_count > 0:
        action = "createControlledCandidate"
        reason = (
            "Ha pendencias na origem, mas nenhuma a pagar elegivel; criar "
            "candidato controlado para o proximo canario."
        )
    else:
        action = "createControlledCandidate"
        reason = (
            "Nao ha obrigacao a pagar pendente; criar candidato controlado "
            "para o proximo canario."
        )

    orientacao.update(
        {
            "hasReadyCandidate": has_ready_candidate,
            "hasHiddenCandidate": has_hidden_candidate,
            "canaryCandidateCount": canary_count,
            "canaryCandidatesReturnedCount": returned_canary_count,
            "nonCanaryPendingCount": non_canary_count,
            "requiredForNextCanary": required_for_next_canary,
            "recommendedAction": action,
            "reason": reason,
        }
    )
    return orientacao


def montar_proxima_acao(
    issues,
    pending_summary,
    canary,
    recommended_commands,
):
    canary_count = int(pending_summary.get("canaryEligibleCount") or 0)
    returned_canary_count = int(
        pending_summary.get("canaryCandidatesReturnedCount")
        if pending_summary.get("canaryCandidatesReturnedCount") is not None
        else len(pending_summary.get("canaryCandidates") or [])
    )
    non_canary_count = int(pending_summary.get("nonCanaryPendingCount") or 0)
    source_id_check = canary.get("sourceIdCheck") or {}

    if source_id_check.get("provided") and source_id_check.get("eligible") is False:
        return {
            "key": "fixCanarySourceId",
            "label": "Corrigir sourceId do canario",
            "detail": source_id_check.get("issue") or "sourceId nao elegivel.",
            "suggestedCommand": "",
        }

    if canary.get("executed") and canary.get("synced") and not issues:
        return {
            "key": "activateAllowlistWindow",
            "label": "Ativar origem na allowlist da janela",
            "detail": (
                "Canario rollback-only sincronizado; avancar para a janela "
                "controlada com backup, flag e auditorias."
            ),
            "suggestedCommand": "",
        }

    if canary_count > 0 and returned_canary_count == 0:
        return {
            "key": "expandCanaryCandidateList",
            "label": "Reexecutar descoberta com limite maior",
            "detail": (
                "Ha obrigacao a pagar pendente elegivel para canario, mas o "
                "limite de listagem nao retornou nenhum sourceId."
            ),
            "suggestedCommand": (
                recommended_commands.get("candidateDiscovery")
                if recommended_commands
                else ""
            ),
        }

    if canary_count > 0:
        return {
            "key": "runCanaryRollbackOnly",
            "label": "Executar canario rollback-only",
            "detail": "Ha obrigacao a pagar pendente elegivel para canario.",
            "suggestedCommand": (
                recommended_commands.get("canaryRollbackOnly")
                if recommended_commands
                else ""
            ),
        }

    if not issues:
        if non_canary_count > 0:
            return {
                "key": "awaitCanaryCandidate",
                "label": "Aguardar ou criar pendencia controlada",
                "detail": (
                    "A validacao read-only esta pronta e ha pendencia(s) na "
                    "origem, mas nenhuma e obrigacao a pagar elegivel para "
                    "canario rollback-only."
                ),
                "suggestedCommand": "",
            }
        return {
            "key": "awaitCanaryCandidate",
            "label": "Aguardar ou criar pendencia controlada",
            "detail": (
                "A validacao read-only esta pronta, mas nao ha obrigacao a "
                "pagar pendente para canario rollback-only."
            ),
            "suggestedCommand": "",
        }

    return {
        "key": "fixValidationIssues",
        "label": "Corrigir pendencias de validacao",
        "detail": issues[0] if issues else "Validacao pendente.",
        "suggestedCommand": "",
    }


def resumir_obrigacoes_pendentes(source, limit=CANARY_CANDIDATE_LIMIT):
    limit = CANARY_CANDIDATE_LIMIT if limit is None else int(limit)
    if not source:
        return {
            "count": 0,
            "payableCount": 0,
            "receivableCount": 0,
            "canaryEligibleCount": 0,
            "canaryCandidates": [],
            "canaryCandidatesLimit": max(limit, 0),
            "canaryCandidatesReturnedCount": 0,
            "canaryCandidatesTruncated": False,
            "nonCanaryPendingCount": 0,
            "nonCanaryPendingItems": [],
            "nonCanaryPendingItemsReturnedCount": 0,
            "nonCanaryPendingItemsTruncated": False,
        }
    safe_limit = max(limit, 0)
    query = ObrigacaoFinanceira.objects.filter(
        origem=source,
        valor_pendente__gt=0,
    )
    payable_query = query.filter(tipo=ObrigacaoFinanceira.TIPO_PAGAR).order_by(
        "data_vencimento",
        "id",
    )
    non_canary_query = query.exclude(
        tipo=ObrigacaoFinanceira.TIPO_PAGAR
    ).order_by(
        "data_vencimento",
        "id",
    )
    payable_count = payable_query.count()
    receivable_count = query.filter(tipo=ObrigacaoFinanceira.TIPO_RECEBER).count()
    non_canary_count = non_canary_query.count()
    canary_candidates = [
        serializar_candidato_canario(source, obrigacao)
        for obrigacao in payable_query[:safe_limit]
    ]
    non_canary_items = [
        serializar_pendencia_sem_canario(source, obrigacao)
        for obrigacao in non_canary_query[:safe_limit]
    ]
    return {
        "count": payable_count + receivable_count,
        "payableCount": payable_count,
        "receivableCount": receivable_count,
        "canaryEligibleCount": payable_count,
        "canaryCandidates": canary_candidates,
        "canaryCandidatesLimit": safe_limit,
        "canaryCandidatesReturnedCount": len(canary_candidates),
        "canaryCandidatesTruncated": payable_count > len(canary_candidates),
        "nonCanaryPendingCount": non_canary_count,
        "nonCanaryPendingItems": non_canary_items,
        "nonCanaryPendingItemsReturnedCount": len(non_canary_items),
        "nonCanaryPendingItemsTruncated": non_canary_count > len(non_canary_items),
    }


def resumir_saude_lista_candidatos(pending_summary):
    pending_summary = pending_summary or {}
    candidates = pending_summary.get("canaryCandidates") or []
    eligible_count = _int_safe(pending_summary.get("canaryEligibleCount"))
    returned_count = _int_safe(
        pending_summary.get("canaryCandidatesReturnedCount")
        if pending_summary.get("canaryCandidatesReturnedCount") is not None
        else len(candidates)
    )
    limit = _int_safe(pending_summary.get("canaryCandidatesLimit"))
    truncated = bool(pending_summary.get("canaryCandidatesTruncated"))
    non_canary_count = _int_safe(pending_summary.get("nonCanaryPendingCount"))
    non_canary_returned = _int_safe(
        pending_summary.get("nonCanaryPendingItemsReturnedCount")
    )
    has_selectable_candidate = bool(candidates)
    hidden_by_limit = eligible_count > 0 and returned_count == 0 and truncated

    if hidden_by_limit:
        status = "blockedByLimit"
        recommended_action = "expandCandidateList"
        detail = (
            "Ha candidato elegivel, mas nenhum sourceId foi retornado pela "
            "listagem atual; reexecute com --limit maior que 0."
        )
    elif has_selectable_candidate and truncated:
        status = "readyTruncated"
        recommended_action = "useReturnedCandidateOrIncreaseLimit"
        detail = (
            "Ha candidato selecionavel, mas a lista foi truncada; use um "
            "sourceId retornado ou aumente o limite para comparar mais opcoes."
        )
    elif has_selectable_candidate:
        status = "ready"
        recommended_action = "useReturnedCandidate"
        detail = "Ha candidato selecionavel para canario rollback-only."
    elif non_canary_count > 0:
        status = "onlyNonCanaryPending"
        recommended_action = "createControlledCandidate"
        detail = (
            "Ha pendencia na origem, mas nenhuma obrigacao a pagar elegivel "
            "para canario rollback-only."
        )
    else:
        status = "empty"
        recommended_action = "createOrAwaitCandidate"
        detail = "Nao ha obrigacao a pagar pendente elegivel para canario."

    return {
        "status": status,
        "eligibleCount": eligible_count,
        "returnedCount": returned_count,
        "limit": limit,
        "truncated": truncated,
        "hasSelectableCandidate": has_selectable_candidate,
        "hiddenByLimit": hidden_by_limit,
        "requiresLimitIncrease": hidden_by_limit,
        "nonCanaryPendingCount": non_canary_count,
        "nonCanaryReturnedCount": non_canary_returned,
        "nonCanaryTruncated": bool(
            pending_summary.get("nonCanaryPendingItemsTruncated")
        ),
        "recommendedAction": recommended_action,
        "detail": detail,
    }


def _int_safe(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def serializar_candidato_canario(source, obrigacao):
    source_id = getattr(obrigacao, f"{source}_id", None)
    return {
        "obligationId": obrigacao.id,
        "obligationKey": obrigacao.chave_origem or "",
        "source": source,
        "sourceId": source_id,
        "sourceDetail": obrigacao.detalhe_origem or "",
        "description": obrigacao.descricao,
        "reference": obrigacao.referencia or "",
        "dueDate": obrigacao.data_vencimento.isoformat(),
        "plannedAmount": str(obrigacao.valor_previsto),
        "realizedAmount": str(obrigacao.valor_realizado),
        "pendingAmount": str(obrigacao.valor_pendente),
        "status": obrigacao.status,
    }


def serializar_pendencia_sem_canario(source, obrigacao):
    payload = serializar_candidato_canario(source, obrigacao)
    payload["obligationType"] = obrigacao.tipo
    payload["ineligibilityReason"] = motivo_pendencia_sem_canario(source, obrigacao)
    return payload


def motivo_pendencia_sem_canario(source, obrigacao):
    if obrigacao.tipo == ObrigacaoFinanceira.TIPO_RECEBER:
        if source == "investimento":
            return (
                "Investimento FCI de entrada gera obrigacao a receber; "
                "PM-03.3 exige investimento de saida/a pagar."
            )
        if source == "financiamento_movimentacao":
            return (
                "Movimentacao FCF de entrada gera obrigacao a receber; "
                "PM-03.4 exige movimentacao de saida/a pagar."
            )
        return (
            "Obrigacao do tipo receber; canario rollback-only exige "
            "obrigacao do tipo pagar."
        )
    return "Obrigacao pendente nao elegivel para canario rollback-only."


def checar_source_id_canario(source, source_id):
    payload = {
        "provided": bool(source_id),
        "sourceId": source_id or "",
        "eligible": None,
        "obligationId": None,
        "obligationKey": "",
        "pendingAmount": "",
        "issue": "",
    }
    if not source_id:
        return payload
    if source not in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES:
        return payload

    try:
        obrigacao = (
            ObrigacaoFinanceira.objects.filter(
                origem=source,
                **{f"{source}_id": source_id},
            )
            .order_by("id")
            .first()
        )
    except (FieldError, TypeError, ValueError):
        payload["eligible"] = False
        payload["issue"] = f"sourceId={source_id} invalido para {source}."
        return payload

    if not obrigacao:
        payload["eligible"] = False
        payload["issue"] = (
            f"sourceId={source_id} nao corresponde a obrigacao canonica "
            f"da origem {source}."
        )
        return payload

    payload.update(
        {
            "obligationId": obrigacao.id,
            "obligationKey": obrigacao.chave_origem or "",
            "pendingAmount": str(obrigacao.valor_pendente),
        }
    )
    if obrigacao.tipo != ObrigacaoFinanceira.TIPO_PAGAR:
        payload["eligible"] = False
        payload["issue"] = (
            f"sourceId={source_id} nao e obrigacao a pagar elegivel ao canario."
        )
        return payload
    if obrigacao.valor_pendente <= 0:
        payload["eligible"] = False
        payload["issue"] = (
            f"sourceId={source_id} nao possui saldo pendente para canario."
        )
        return payload

    payload["eligible"] = True
    return payload


def formatar_source_id_check(source_id_check):
    if not source_id_check or not source_id_check.get("provided"):
        return "-"

    partes = [
        f"sourceId={source_id_check.get('sourceId') or '-'}",
        f"elegivel={source_id_check.get('eligible')}",
    ]
    if source_id_check.get("obligationId"):
        partes.append(f"obrigacao={source_id_check['obligationId']}")
    if source_id_check.get("pendingAmount"):
        partes.append(f"pendente={source_id_check['pendingAmount']}")
    if source_id_check.get("issue"):
        partes.append(f"issue={source_id_check['issue']}")
    return "; ".join(partes)


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    json_path = options.get("salvar_json") or ""
    record_path = options.get("salvar_registro") or ""

    if directory:
        base = Path(directory).expanduser()
        json_path = json_path or str(base / "pm03-validacao-ativacao-canonical-first.json")
        record_path = record_path or str(base / "pm03-validacao-ativacao-canonical-first.md")

    return {
        "directory": directory,
        "json": str(Path(json_path).expanduser()) if json_path else "",
        "record": str(Path(record_path).expanduser()) if record_path else "",
    }


def _exigir_arquivos_evidencia(evidence_files):
    if not evidence_files.get("json") or not evidence_files.get("record"):
        raise CommandError(
            "Informe arquivos de evidencia PM-03 de ativacao com "
            "--diretorio-evidencias ou --salvar-json/--salvar-registro."
        )


def _salvar_evidencias_ativacao(resultado):
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


def _registro_ativacao_pm03(resultado):
    pendencias = resultado["pendingObligations"]
    canary = resultado["canary"]
    gate = resultado.get("operationalGate") or {}
    decisao = resultado.get("activationDecision") or {}
    sequence_position = resultado.get("sequencePosition") or {}
    issues = "; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"
    evidence_files = resultado.get("evidenceFiles") or {}
    candidate_list_health = resultado.get("candidateListHealth") or {}
    evidence_summary = (
        f"diretorio={evidence_files.get('directory') or '-'}; "
        f"json={evidence_files.get('json') or '-'}; "
        f"registro={evidence_files.get('record') or '-'}"
    )
    ambiente = resultado["recommendedEnvironment"]

    return "\n".join(
        [
            "### Registro PM-03 - validacao de ativacao canonical-first",
            "",
            f"Data/hora da validacao: {timezone.now().isoformat()}",
            f"Origem: {resultado['source']}",
            f"ready/issues: ready={resultado['ready']}; issues={issues}",
            (
                "Decisao ativacao: "
                f"status={decisao.get('status') or '-'}; "
                f"step={decisao.get('step') or '-'}; "
                "mayRunCanaryRollbackOnly="
                f"{decisao.get('mayRunCanaryRollbackOnly')}; "
                "mayActivateAllowlistWindow="
                f"{decisao.get('mayActivateAllowlistWindow')}; "
                "requiresControlledCandidate="
                f"{decisao.get('requiresControlledCandidate')}; "
                f"blockedBy={'; '.join(decisao.get('blockedBy') or []) or '-'}"
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
                f"limite={candidate_list_health.get('limit')}; "
                f"truncada={candidate_list_health.get('truncated')}; "
                f"acao={candidate_list_health.get('recommendedAction') or '-'}"
            ),
            f"Candidatos canario: {_resumir_candidatos_canario(pendencias)}",
            f"Pendencias sem canario: {resumir_pendencias_sem_canario(pendencias)}",
            (
                "Canario rollback-only: "
                f"required={canary['required']}; "
                f"sourceIdRequired={canary['sourceIdRequired']}; "
                f"paymentDateRequired={canary['paymentDateRequired']}; "
                f"paymentDateProvided={canary['paymentDateProvided']}; "
                f"paymentDate={canary.get('paymentDate') or '-'}; "
                f"executed={canary['executed']}; "
                f"synced={canary['synced']}"
            ),
            f"Canario sourceId: {formatar_source_id_check(canary.get('sourceIdCheck'))}",
            (
                "Canario sugerido: "
                f"{(resultado.get('recommendedCommands') or {}).get('canaryRollbackOnly') or '-'}"
            ),
            (
                "Descoberta candidato: "
                f"{(resultado.get('recommendedCommands') or {}).get('candidateDiscovery') or '-'}"
            ),
            (
                "Regressao dividas: "
                f"{_resumir_lista((resultado.get('recommendedCommands') or {}).get('debtRegression'))}"
            ),
            (
                "Candidato controlado: "
                f"{resumir_orientacao_candidato_controlado(resultado.get('candidateCreationGuidance'))}"
            ),
            (
                "Comandos apos candidato: "
                f"{resumir_comandos_orientacao_candidato_controlado(resultado.get('candidateCreationGuidance'))}"
            ),
            (
                "Paridade canonica: "
                f"consistent={resultado['canonicalParity']['consistent']}"
            ),
            f"Prontidao de escrita: ready={resultado['writeReadiness']['ready']}",
            (
                "Env sugerido: "
                "CANONICAL_FIRST_SETTLEMENT_ENABLED=True; "
                "CANONICAL_FIRST_SETTLEMENT_SOURCES="
                f"{ambiente['CANONICAL_FIRST_SETTLEMENT_SOURCES']}"
            ),
            f"Arquivos salvos: {evidence_summary}",
            (
                "Proxima acao: "
                f"{(resultado.get('nextAction') or {}).get('key') or '-'}; "
                f"{(resultado.get('nextAction') or {}).get('detail') or '-'}"
            ),
            f"Acao permitida: {_resumir_lista(gate.get('allowedActions'))}",
            f"Acoes bloqueadas: {_resumir_lista(gate.get('blockedActions'))}",
        ]
    )


def _resumir_lista(items):
    items = [str(item) for item in (items or []) if str(item)]
    if not items:
        return "-"
    return " | ".join(items)


def resumir_orientacao_candidato_controlado(orientacao):
    orientacao = orientacao or {}
    if not orientacao.get("available"):
        return "-"
    fields = orientacao.get("suggestedFields") or {}
    principais = [
        f"{field}={fields[field]}"
        for field in (
            "descricao",
            "categoria",
            "tipo_fluxo",
            "valor_previsto",
            "valor_realizado",
            "data_prevista",
        )
        if field in fields
    ]
    criterios = orientacao.get("criteria") or []
    return (
        f"admin={orientacao.get('adminPath') or '-'}; "
        f"campos={'; '.join(principais) or '-'}; "
        f"requiredForNextCanary={orientacao.get('requiredForNextCanary')}; "
        f"acao={orientacao.get('recommendedAction') or '-'}; "
        f"criterios={' | '.join(criterios) or '-'}"
    )


def resumir_comandos_orientacao_candidato_controlado(orientacao):
    return _resumir_lista((orientacao or {}).get("afterCreateCommands"))


def resumir_pendencias_sem_canario(pendencias):
    itens = pendencias.get("nonCanaryPendingItems") or []
    if not itens:
        return "-"
    return "; ".join(
        (
            f"sourceId={item['sourceId']} "
            f"obrigacao={item['obligationId']} "
            f"tipo={item['obligationType']} "
            f"pendente={item['pendingAmount']} "
            f"motivo={item['ineligibilityReason']}"
        )
        for item in itens
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


def _formatar_erro(exc):
    if hasattr(exc, "message_dict"):
        partes = []
        for campo, mensagens in exc.message_dict.items():
            partes.append(f"{campo}: {'; '.join(mensagens)}")
        return "; ".join(partes)
    if hasattr(exc, "messages"):
        return "; ".join(exc.messages)
    return str(exc)


def formatar_erro_ativacao_nao_pronta(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return (
            "Ativacao canonical-first nao esta pronta para a origem informada: "
            f"{issues[0]}"
        )
    return "Ativacao canonical-first nao esta pronta para a origem informada."
