import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.auditar_fonte_escrita_baixas import (
    auditar_fonte_escrita_baixas,
)
from caixa.management.commands.validar_ativacao_canonical_first import (
    formatar_source_id_check,
    montar_comando_descoberta_candidato,
    montar_comandos_regressao_dividas,
    resumir_comandos_orientacao_candidato_controlado,
    resumir_orientacao_candidato_controlado,
    resumir_pendencias_sem_canario,
    validar_ativacao_canonical_first,
)
from caixa.management.commands.validar_operacao_obrigacoes import (
    validar_operacao_obrigacoes,
)
from caixa.contracts_obrigacoes import estado_ativacao_canonical_first
from caixa.services_valores_editaveis import (
    formatar_plano_correcao_valores_editaveis,
    resumir_integridade_valores_editaveis,
)


class Command(BaseCommand):
    help = (
        "Valida uma janela canonical-first por origem e periodo. "
        "Combina readiness, canario opcional e auditoria de baixas geradas."
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
        parser.add_argument("--username")
        parser.add_argument("--source-id", dest="source_id")
        parser.add_argument("--payment-date", dest="payment_date")
        parser.add_argument(
            "--executar-canario",
            action="store_true",
            help="Executa o canario rollback-only antes de validar a janela.",
        )
        parser.add_argument(
            "--exigir-canario",
            action="store_true",
            help="Reprova a janela se o canario rollback-only nao for executado.",
        )
        parser.add_argument(
            "--exigir-source-id-canario",
            action="store_true",
            help=(
                "Reprova a janela se o canario rollback-only for solicitado "
                "sem --source-id explicito."
            ),
        )
        parser.add_argument(
            "--exigir-data-pagamento-canario",
            "--require-canary-payment-date",
            action="store_true",
            help=(
                "Reprova a janela se o canario rollback-only for solicitado "
                "sem --payment-date explicito."
            ),
        )
        parser.add_argument(
            "--exigir-baixa-canonical-first",
            action="store_true",
            help="Reprova a janela se nenhuma baixa canonical-first for encontrada.",
        )
        parser.add_argument(
            "--exigir-data-ativacao",
            action="store_true",
            help=(
                "Reprova a janela se a data inicial da janela canonical-first "
                "nao for informada."
            ),
        )
        parser.add_argument(
            "--exigir-feature-flag-ativa",
            action="store_true",
            help=(
                "Reprova a janela se a feature flag canonical-first nao estiver "
                "ativa para a origem informada."
            ),
        )
        parser.add_argument(
            "--validar-preflight-operacional",
            action="store_true",
            help=(
                "Executa o pre-flight operacional consolidado dentro da validacao "
                "da janela canonical-first."
            ),
        )
        parser.add_argument(
            "--falhar-com-preflight-operacional",
            action="store_true",
            help=(
                "Retorna erro quando o pre-flight operacional consolidado nao "
                "estiver pronto."
            ),
        )
        parser.add_argument(
            "--validar-valores-editaveis",
            action="store_true",
            help="Inclui auditoria read-only de valores editaveis na validacao da janela.",
        )
        parser.add_argument(
            "--falhar-com-valores-editaveis",
            action="store_true",
            help=(
                "Retorna erro quando houver valores editaveis com efeitos "
                "derivados desatualizados."
            ),
        )
        parser.add_argument(
            "--valores-editaveis-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias de valores editaveis retornadas.",
        )
        parser.add_argument(
            "--valores-editaveis-escopo",
            "--editable-values-scope",
            action="append",
            choices=["divida", "evento", "orcamento"],
            default=[],
            help="Limita a auditoria de valores editaveis a um escopo especifico.",
        )
        parser.add_argument(
            "--valores-editaveis-object-id",
            "--editable-values-object-id",
            dest="valores_editaveis_object_ids",
            action="append",
            type=int,
            default=[],
            help="Limita a auditoria de valores editaveis a um ID especifico.",
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
            help="Salva o payload JSON da validacao de janela em um arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown da validacao de janela em um arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help=(
                "Diretorio opcional para gerar arquivos padronizados de "
                "evidencia da validacao PM-03."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os caminhos de evidencia da validacao PM-03 nao "
                "forem informados por --diretorio-evidencias ou caminhos "
                "explicitos."
            ),
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando a janela nao estiver validada.",
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
        payment_date_informada = bool(options.get("payment_date"))
        resultado = validar_janela_canonical_first(
            source=options["source"],
            data_inicial=options.get("data_inicial"),
            data_final=options.get("data_final"),
            username=options.get("username"),
            source_id=options.get("source_id"),
            payment_date=options.get("payment_date") or timezone.localdate().isoformat(),
            executar_canario=options["executar_canario"],
            exigir_canario=options["exigir_canario"],
            exigir_source_id_canario=options["exigir_source_id_canario"],
            exigir_data_pagamento_canario=options[
                "exigir_data_pagamento_canario"
            ],
            payment_date_informada=payment_date_informada,
            exigir_baixa_canonical_first=options["exigir_baixa_canonical_first"],
            exigir_data_ativacao=options["exigir_data_ativacao"],
            exigir_feature_flag_ativa=options["exigir_feature_flag_ativa"],
            validar_preflight_operacional=options["validar_preflight_operacional"],
            falhar_com_preflight_operacional=options[
                "falhar_com_preflight_operacional"
            ],
            limit=options["limit"],
            validar_valores_editaveis=options["validar_valores_editaveis"],
            falhar_com_valores_editaveis=options["falhar_com_valores_editaveis"],
            valores_editaveis_limit=options["valores_editaveis_limit"],
            valores_editaveis_escopos=options["valores_editaveis_escopo"],
            valores_editaveis_object_ids=options["valores_editaveis_object_ids"],
        )
        resultado["evidenceFiles"] = evidence_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_validacao_janela_pm03(resultado),
        }
        _salvar_evidencias_validacao(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        valores_editaveis = resultado["editableValuesIntegrity"]
        if (
            options["falhar_com_valores_editaveis"]
            and valores_editaveis["checked"]
            and not valores_editaveis["consistent"]
        ):
            raise CommandError(
                f"{valores_editaveis['totalIssues']} inconsistencia(s) "
                "de valores editaveis encontrada(s): "
                f"{formatar_primeira_issue_valores_editaveis(valores_editaveis)}"
            )

        preflight = resultado["operationalPreflight"]
        if (
            options["falhar_com_preflight_operacional"]
            and preflight["checked"]
            and not preflight["ready"]
        ):
            raise CommandError(
                "Pre-flight operacional nao esta pronto: "
                f"{formatar_primeira_issue_preflight(preflight)}"
            )

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_janela_nao_validada(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Janela canonical-first validada.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Janela canonical-first com pontos de atencao.")
            )
        self.stdout.write(f"Origem: {resultado['source']}")
        self.stdout.write(f"Periodo: {resultado['period']['startDate'] or '-'} a {resultado['period']['endDate'] or '-'}")
        pendencias = resultado["activation"]["pendingObligations"]
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
        self.stdout.write(
            "Ativacao: " + ("ok" if resultado["activation"]["ready"] else "pendente")
        )
        source_id_check = formatar_source_id_check(
            resultado["activation"]["canary"].get("sourceIdCheck")
        )
        if source_id_check != "-":
            self.stdout.write(f"Canario sourceId: {source_id_check}")
        canary = resultado["activation"]["canary"]
        if canary.get("paymentDateRequired"):
            self.stdout.write(
                "Canario paymentDate: "
                f"required=True; provided={canary.get('paymentDateProvided')}"
            )
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
        self.stdout.write(
            "Feature flag: "
            + (
                "ativa para a origem"
                if resultado["featureFlagValidation"]["activeForSource"]
                else "nao ativa para a origem"
            )
        )
        self.stdout.write(
            "Baixas canonical-first: "
            f"{resultado['canonicalFirstAudit']['canonicalFirst']['count']}"
        )
        auditoria_janela = resultado.get("windowWriteAudit") or {}
        if auditoria_janela:
            self.stdout.write(
                "Baixas na janela: "
                f"total={auditoria_janela['count']}; "
                f"canonicalFirst={auditoria_janela['canonicalFirst']['count']}; "
                f"legacyAdapterSynced={auditoria_janela['legacyAdapterSynced']['count']}"
            )
        self._imprimir_preflight_operacional(resultado["operationalPreflight"])
        self._imprimir_valores_editaveis(resultado["editableValuesIntegrity"])
        self.stdout.write("Roteiro operacional:")
        for grupo, passos in resultado["operationalChecklist"]["commands"].items():
            self.stdout.write(f"{grupo}:")
            for passo in passos:
                self.stdout.write(f"- {passo['command']}")
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

    def _imprimir_valores_editaveis(self, valores_editaveis):
        if not valores_editaveis["checked"]:
            self.stdout.write("Valores editaveis: nao validados nesta execucao.")
            return

        if valores_editaveis["consistent"]:
            self.stdout.write("Valores editaveis: efeitos derivados consistentes.")
            return

        self.stdout.write(
            "Valores editaveis: "
            f"{valores_editaveis['totalIssues']} inconsistencia(s)."
        )
        self._imprimir_filtros_valores_editaveis(valores_editaveis["filters"])
        for linha in formatar_plano_correcao_valores_editaveis(
            valores_editaveis["correctionPlan"]
        ):
            self.stdout.write(linha)

    def _imprimir_filtros_valores_editaveis(self, filtros):
        escopos = filtros.get("scopes") or []
        object_ids = filtros.get("objectIds") or []
        if escopos == ["divida", "evento", "orcamento"] and not object_ids:
            return

        self.stdout.write(
            "Filtros valores editaveis: "
            f"escopos={', '.join(escopos) or '-'}; "
            f"objectIds={', '.join(str(item) for item in object_ids) or '-'}"
        )

    def _imprimir_preflight_operacional(self, preflight):
        if not preflight["checked"]:
            self.stdout.write("Pre-flight operacional: nao validado nesta execucao.")
            return

        if preflight["ready"]:
            self.stdout.write("Pre-flight operacional: ambiente pronto.")
            return

        self.stdout.write("Pre-flight operacional: pontos de atencao.")
        contrato = preflight.get("contract") or {}
        conciliacao = preflight.get("reconciliation") or {}
        canonico = preflight.get("canonicalModeling") or {}
        escrita = preflight.get("canonicalWriteReadiness") or {}
        valores = preflight.get("editableValuesIntegrity") or {}
        self.stdout.write(
            "Resumo pre-flight: "
            f"contrato={'ok' if contrato.get('consistent') else 'pendente'}; "
            f"divergencias={conciliacao.get('divergentCount') or 0}; "
            f"canonico={_status_preflight(canonico, 'consistent')}; "
            f"escrita={_status_preflight(escrita, 'ready')}; "
            f"valoresEditaveis={_status_preflight(valores, 'consistent')}"
        )


def validar_janela_canonical_first(
    source,
    data_inicial=None,
    data_final=None,
    username=None,
    source_id=None,
    payment_date=None,
    executar_canario=False,
    exigir_canario=False,
    exigir_source_id_canario=False,
    exigir_data_pagamento_canario=False,
    payment_date_informada=None,
    exigir_baixa_canonical_first=False,
    exigir_data_ativacao=False,
    exigir_feature_flag_ativa=False,
    validar_preflight_operacional=False,
    falhar_com_preflight_operacional=False,
    limit=20,
    validar_valores_editaveis=False,
    falhar_com_valores_editaveis=False,
    valores_editaveis_limit=20,
    valores_editaveis_escopos=None,
    valores_editaveis_object_ids=None,
):
    ativacao = validar_ativacao_canonical_first(
        source=source,
        username=username,
        source_id=source_id,
        payment_date=payment_date,
        executar_canario=executar_canario,
        exigir_canario=exigir_canario,
        exigir_source_id_canario=exigir_source_id_canario,
        exigir_data_pagamento_canario=exigir_data_pagamento_canario,
        payment_date_informada=payment_date_informada,
        limit=limit,
    )
    auditoria_canonical_first = auditar_fonte_escrita_baixas(
        data_inicial=data_inicial,
        data_final=data_final,
        source=source,
        write_model_source="canonicalFirst",
        exigir_data_ativacao=exigir_data_ativacao,
    )
    auditoria_janela = auditar_fonte_escrita_baixas(
        data_inicial=data_inicial,
        data_final=data_final,
        source=source,
        exigir_data_ativacao=exigir_data_ativacao,
    )
    issues = list(ativacao["issues"])
    write_readiness = ativacao["writeReadiness"]
    flag_ativa_para_origem = (
        write_readiness["featureFlagEnabled"]
        and source in write_readiness["enabledCanonicalFirstSources"]
    )
    validacao_flag = {
        "required": exigir_feature_flag_ativa,
        "featureFlagEnabled": write_readiness["featureFlagEnabled"],
        "enabledSources": write_readiness["enabledCanonicalFirstSources"],
        "activeForSource": flag_ativa_para_origem,
    }
    if exigir_data_ativacao and not data_inicial:
        issues.append("Informe a data de ativacao da janela canonical-first.")
    if exigir_feature_flag_ativa and not flag_ativa_para_origem:
        issues.append(
            "Feature flag canonical-first nao esta ativa para a origem informada."
        )
    if (
        exigir_baixa_canonical_first
        and auditoria_canonical_first["canonicalFirst"]["count"] == 0
    ):
        issues.append("Nenhuma baixa canonical-first encontrada na janela.")
    preflight = executar_preflight_operacional_janela(
        validar=(
            validar_preflight_operacional
            or falhar_com_preflight_operacional
        ),
        limit=limit,
        valores_editaveis_limit=valores_editaveis_limit,
        valores_editaveis_escopos=valores_editaveis_escopos,
        valores_editaveis_object_ids=valores_editaveis_object_ids,
    )
    if preflight["checked"] and not preflight["ready"]:
        issues.append("Pre-flight operacional nao esta pronto.")
    valores_editaveis = resumir_integridade_valores_editaveis(
        validar=validar_valores_editaveis or falhar_com_valores_editaveis,
        limit=valores_editaveis_limit,
        escopos=valores_editaveis_escopos,
        object_ids=valores_editaveis_object_ids,
    )
    if valores_editaveis["checked"] and not valores_editaveis["consistent"]:
        issues.append(
            f"{valores_editaveis['totalIssues']} inconsistencia(s) "
            "de valores editaveis encontrada(s)."
        )
    checklist_payment_date = str(payment_date or "") if payment_date_informada else ""
    checklist = montar_checklist_operacional_janela(
        source=source,
        data_inicial=data_inicial,
        data_final=data_final,
        username=username,
        source_id=source_id,
        payment_date=checklist_payment_date,
        valores_editaveis_escopos=valores_editaveis_escopos,
        valores_editaveis_object_ids=valores_editaveis_object_ids,
    )
    ready = ativacao["ready"] and not issues
    resultado_janela = montar_resultado_janela_canonical_first(
        auditoria_janela,
        issues,
        ready,
        next_action=ativacao.get("nextAction") or {},
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
        "activation": ativacao,
        "activationDecision": ativacao.get("activationDecision") or {},
        "nextAction": ativacao.get("nextAction") or {},
        "operationalGate": ativacao.get("operationalGate") or {},
        "sequencePosition": ativacao.get("sequencePosition") or {},
        "candidateCreationGuidance": (
            ativacao.get("candidateCreationGuidance") or {}
        ),
        "candidateListHealth": ativacao.get("candidateListHealth") or {},
        "featureFlagValidation": validacao_flag,
        "requiresActivationDate": exigir_data_ativacao,
        "canonicalFirstAudit": auditoria_canonical_first,
        "windowWriteAudit": auditoria_janela,
        "windowOutcome": resultado_janela,
        "operationalPreflight": preflight,
        "editableValuesIntegrity": valores_editaveis,
        "operationalChecklist": checklist,
        "issues": issues,
    }


def montar_resultado_janela_canonical_first(
    auditoria,
    issues,
    ready,
    next_action=None,
):
    canonical_count = int((auditoria.get("canonicalFirst") or {}).get("count") or 0)
    legacy_count = int((auditoria.get("legacyAdapterSynced") or {}).get("count") or 0)
    status = "blocked"
    label = "Janela com pendencias"
    detail = issues[0] if issues else "Validacao de janela ainda nao aprovada."

    if ready and canonical_count > 0 and legacy_count == 0:
        status = "approvedCanonicalFirstOnly"
        label = "Janela canonical-first aprovada"
        detail = "Ha baixa canonical-first e nenhuma baixa legada no recorte."
    elif ready and canonical_count > 0:
        status = "approvedWithLegacyTolerance"
        label = "Janela aprovada com baixa canonical-first"
        detail = "Ha baixa canonical-first no recorte; verifique tolerancia a legado."
    elif ready:
        status = "approvedReadOnly"
        label = "Janela validada sem baixa obrigatoria"
        detail = "Validacoes read-only prontas no recorte monitorado."
    elif canonical_count == 0:
        status = "blockedWithoutCanonicalFirst"
        label = "Janela sem baixa canonical-first"
    elif legacy_count > 0:
        status = "blockedWithLegacyWrites"
        label = "Janela com baixa legada"

    note = ""
    if ready and (next_action or {}).get("key") == "awaitCanaryCandidate":
        note = (
            "nextAction descreve o gate de novos canarios pendentes; "
            "nao bloqueia a janela quando ready=True."
        )

    return {
        "status": status,
        "label": label,
        "detail": detail,
        "nextActionScope": "activationGate",
        "nextActionNote": note,
    }


def executar_preflight_operacional_janela(
    validar=False,
    limit=20,
    valores_editaveis_limit=20,
    valores_editaveis_escopos=None,
    valores_editaveis_object_ids=None,
):
    if not validar:
        return {
            "checked": False,
            "ready": None,
        }

    resultado = validar_operacao_obrigacoes(
        {
            "limit": limit,
            "validar_canonico": True,
            "validar_escrita_canonica": True,
            "validar_valores_editaveis": True,
            "canonical_limit": limit,
            "valores_editaveis_limit": valores_editaveis_limit,
            "valores_editaveis_escopo": valores_editaveis_escopos or [],
            "valores_editaveis_object_ids": valores_editaveis_object_ids or [],
        }
    )
    resultado["checked"] = True
    return resultado


def montar_checklist_operacional_janela(
    source,
    data_inicial=None,
    data_final=None,
    username=None,
    source_id=None,
    payment_date=None,
    valores_editaveis_escopos=None,
    valores_editaveis_object_ids=None,
):
    source = str(source or "").strip()
    username = str(username or "<usuario>").strip()
    payment_date = str(payment_date or "<DATA>").strip()
    periodo_args = _periodo_args(data_inicial, data_final)
    periodo_pos_janela_args = _periodo_args(
        data_inicial or "DATA_DA_ATIVACAO",
        data_final,
    )
    source_id_arg = (
        f" --source-id={source_id}"
        if source_id
        else " --source-id=<sourceId-de-canaryCandidates>"
    )
    fontes_habilitadas = sorted(
        set(estado_ativacao_canonical_first()["enabledSources"]) | {source}
    )
    valores_editaveis_args = _valores_editaveis_args(
        valores_editaveis_escopos,
        valores_editaveis_object_ids,
    )
    evidence_dir_args = _diretorio_evidencias_args(source)
    closure_evidence_args = (
        _arquivo_evidencia_args(
            source,
            "validacao-janela-json",
            "pm03-validacao-resultado-janela.json",
        )
    )
    if source == "financiamento_movimentacao":
        closure_evidence_args += _arquivo_evidencia_args(
            source,
            "candidatos-canario-json",
            "pm03-candidatos-canario.json",
        )
        closure_evidence_args += _arquivo_evidencia_args(
            source,
            "regressao-dividas-json",
            "pm03-regressao-dividas-fcf.json",
        )

    pre_window = [
        _passo(
            "canonicalSyncDryRun",
            "python manage.py sincronizar_modelagem_financeira_canonica",
        ),
        _passo(
            "canonicalSyncApply",
            "python manage.py sincronizar_modelagem_financeira_canonica --aplicar",
        ),
        _passo(
            "canonicalParity",
            "python manage.py verificar_paridade_modelagem_canonica --falhar",
        ),
        _passo(
            "operationalPreflight",
            (
                "python manage.py validar_operacao_obrigacoes "
                "--validar-canonico --validar-escrita-canonica "
                f"--validar-valores-editaveis{valores_editaveis_args} --falhar"
            ),
        ),
    ]
    discovery_command = montar_comando_descoberta_candidato(
        source,
        username=username,
        payment_date=payment_date,
    )
    if discovery_command:
        pre_window.append(
            _passo(
                "discoverCanaryCandidate",
                discovery_command,
            )
        )
    for step, command in _passos_regressao_dividas(source):
        pre_window.append(_passo(step, command))
    pre_window.append(
        _passo(
            "validateActivationCanaryRollbackOnly",
            (
                "python manage.py validar_ativacao_canonical_first "
                f"--source={source} --username={username}{source_id_arg} "
                f"--payment-date={payment_date} --executar-canario "
                "--exigir-canario --exigir-source-id-canario "
                "--exigir-data-pagamento-canario"
                f"{evidence_dir_args} --exigir-arquivos-evidencia --json --falhar"
            ),
        )
    )
    active_window = [
        _passo(
            "validateFeatureFlag",
            (
                "python manage.py validar_janela_canonical_first "
                f"--source={source} --validar-preflight-operacional "
                "--falhar-com-preflight-operacional"
                f"{valores_editaveis_args} --exigir-feature-flag-ativa"
                f"{evidence_dir_args} --exigir-arquivos-evidencia --json --falhar"
            ),
        ),
    ]
    post_window = [
        _passo(
            "auditCanonicalFirstSettlements",
            (
                "python manage.py auditar_fonte_escrita_baixas "
                f"--source={source}{periodo_pos_janela_args} "
                "--write-model-source=canonicalFirst --exigir-canonical-first "
                f"--exigir-data-ativacao{evidence_dir_args} "
                "--exigir-arquivos-evidencia --json"
            ),
        ),
        _passo(
            "validateWindowResult",
            (
                "python manage.py validar_janela_canonical_first "
                f"--source={source}{periodo_pos_janela_args} "
                "--validar-preflight-operacional "
                "--falhar-com-preflight-operacional"
                f"{valores_editaveis_args} --exigir-baixa-canonical-first "
                f"--exigir-data-ativacao{evidence_dir_args} "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        ),
        _passo(
            "monitorActiveCanonicalFirst",
            (
                "python manage.py monitorar_janela_canonical_first "
                f"--source={source}{periodo_pos_janela_args} "
                "--exigir-canonical-first --falhar-com-legado-na-janela "
                f"--exigir-data-ativacao{evidence_dir_args} "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        ),
        _passo(
            "businessTotalsAudit",
            (
                "python manage.py auditar_totais_negocio "
                "--falhar-com-divergencia --validar-valores-editaveis "
                f"--falhar-com-valores-editaveis{valores_editaveis_args}"
                f"{evidence_dir_args} --exigir-arquivos-evidencia --json"
            ),
        ),
        _passo(
            "validatePm03Closure",
            (
                "python manage.py validar_fechamento_pm03 "
                f"--source={source}{periodo_pos_janela_args}"
                f"{closure_evidence_args}{evidence_dir_args} "
                "--exigir-validacao-ativacao --json --falhar"
            ),
        ),
    ]
    rollback = [
        _passo(
            "disableCanonicalFirst",
            (
                "Definir CANONICAL_FIRST_SETTLEMENT_ENABLED=False e remover "
                f"{source} de CANONICAL_FIRST_SETTLEMENT_SOURCES."
            ),
            kind="manual",
        ),
        _passo(
            "validateLegacyRead",
            f"python manage.py validar_janela_canonical_first --source={source} --falhar",
            legacy_step="validateLegacyFallback",
        ),
    ]

    return {
        "environment": {
            "CANONICAL_FIRST_SETTLEMENT_ENABLED": "True",
            "CANONICAL_FIRST_SETTLEMENT_SOURCES": ",".join(fontes_habilitadas),
            "sourceToActivate": source,
            "enabledSourcesToKeep": fontes_habilitadas,
        },
        "commands": {
            "preWindow": pre_window,
            "activeWindow": active_window,
            "postWindow": post_window,
            "rollback": rollback,
        },
    }


def _passos_regressao_dividas(source):
    comandos = montar_comandos_regressao_dividas(source)
    if not comandos:
        return []
    nomes = [
        "validateDebtRegressionEvidence",
        "validateDebtCreditorIntegrity",
        "validateDebtAutomaticFcfEntries",
        "validateFinancialDeployPreflight",
    ]
    return list(zip(nomes, comandos))


def _periodo_args(data_inicial, data_final):
    argumentos = []
    if data_inicial:
        argumentos.append(f"--data-inicial={data_inicial}")
    if data_final:
        argumentos.append(f"--data-final={data_final}")
    return (" " + " ".join(argumentos)) if argumentos else ""


def _diretorio_evidencias_args(source):
    return f" --diretorio-evidencias={_diretorio_evidencias_placeholder(source)}"


def _diretorio_evidencias_placeholder(source):
    slug = str(source or "origem").strip().replace("_", "-") or "origem"
    return f"<diretorio-evidencias-pm03-{slug}>"


def _arquivo_evidencia_args(source, option, filename):
    directory = _diretorio_evidencias_placeholder(source)
    return f" --{option}={directory}/{filename}"


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
        base_name = _nome_base_evidencia_validacao(options)
        if not save_json:
            save_json = str(base_path / f"{base_name}.json")
        if not save_record:
            save_record = str(base_path / f"{base_name}.md")

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


def _nome_base_evidencia_validacao(options):
    if options.get("exigir_baixa_canonical_first"):
        return "pm03-validacao-resultado-janela"
    if options.get("exigir_feature_flag_ativa"):
        return "pm03-validacao-feature-flag"
    return "pm03-validacao-janela-canonical-first"


def _salvar_evidencias_validacao(resultado):
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


def _registro_validacao_janela_pm03(resultado):
    periodo = resultado["period"]
    pendencias = resultado["activation"]["pendingObligations"]
    auditoria = resultado["canonicalFirstAudit"]
    auditoria_janela = resultado.get("windowWriteAudit") or auditoria
    preflight = resultado["operationalPreflight"]
    valores = resultado["editableValuesIntegrity"]
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
            "### Registro PM-03 - validacao de janela canonical-first",
            "",
            f"Data/hora da validacao: {resultado['generatedAt']}",
            f"Origem: {resultado['source']}",
            (
                "Periodo validado: "
                f"{periodo['startDate'] or '-'} a {periodo['endDate'] or '-'}"
            ),
            f"ready/issues: ready={resultado['ready']}; issues={issues}",
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
                "Feature flag ativa para origem: "
                f"{resultado['featureFlagValidation']['activeForSource']}"
            ),
            (
                "Pre-flight operacional: "
                f"checked={preflight['checked']}; ready={preflight['ready']}"
            ),
            (
                "Baixas canonical-first: "
                f"count={auditoria['canonicalFirst']['count']}; "
                f"valor={auditoria['canonicalFirst']['outflowAmount']:.2f}"
            ),
            (
                "Baixas na janela: "
                f"total={auditoria_janela['count']}; "
                f"canonicalFirst={auditoria_janela['canonicalFirst']['count']} "
                f"valor={auditoria_janela['canonicalFirst']['outflowAmount']:.2f}; "
                f"legacyAdapterSynced={auditoria_janela['legacyAdapterSynced']['count']} "
                f"valor={auditoria_janela['legacyAdapterSynced']['outflowAmount']:.2f}"
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
                "Candidato controlado: "
                f"{resumir_orientacao_candidato_controlado(resultado.get('candidateCreationGuidance'))}"
            ),
            (
                "Comandos apos candidato: "
                f"{resumir_comandos_orientacao_candidato_controlado(resultado.get('candidateCreationGuidance'))}"
            ),
            (
                "Canario sourceId: "
                f"{formatar_source_id_check(resultado['activation']['canary'].get('sourceIdCheck'))}"
            ),
            (
                "Canario paymentDate: "
                f"required={resultado['activation']['canary'].get('paymentDateRequired')}; "
                f"provided={resultado['activation']['canary'].get('paymentDateProvided')}"
            ),
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
                "Valores editaveis: "
                f"checked={valores['checked']}; "
                f"consistent={valores['consistent']}; "
                f"issues={valores['totalIssues']}"
            ),
            f"Arquivos salvos: {evidence_summary}",
        ]
    )


def _valores_editaveis_args(escopos=None, object_ids=None):
    argumentos = []
    for escopo in escopos or []:
        argumentos.append(f"--valores-editaveis-escopo={escopo}")
    for object_id in object_ids or []:
        argumentos.append(f"--valores-editaveis-object-id={object_id}")
    return (" " + " ".join(argumentos)) if argumentos else ""


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


def _status_preflight(grupo, chave):
    if not grupo.get("checked"):
        return "nao_validado"
    return "ok" if grupo.get(chave) else "pendente"


def formatar_erro_janela_nao_validada(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Janela canonical-first nao validada: {issues[0]}"
    return "Janela canonical-first nao validada."


def formatar_primeira_issue_preflight(preflight):
    contrato = preflight.get("contract") or {}
    inconsistencias = contrato.get("inconsistencies") or []
    if inconsistencias:
        return inconsistencias[0]

    conciliacao = preflight.get("reconciliation") or {}
    itens = conciliacao.get("items") or []
    if itens:
        item = itens[0]
        return (
            f"{item.get('source')}#{item.get('sourceId')} "
            f"{item.get('description') or '-'} "
            f"dif={item.get('realizedAmountDifference')}"
        )

    canonico = preflight.get("canonicalModeling") or {}
    issues_canonicas = canonico.get("issues") or []
    if issues_canonicas:
        issue = issues_canonicas[0]
        return f"{issue['tipo']} {issue['chave']}: {issue['mensagem']}"

    escrita = preflight.get("canonicalWriteReadiness") or {}
    issues_escrita = escrita.get("issues") or []
    if issues_escrita:
        return issues_escrita[0]

    valores = preflight.get("editableValuesIntegrity") or {}
    return formatar_primeira_issue_valores_editaveis(valores)


def formatar_primeira_issue_valores_editaveis(valores_editaveis):
    issues = valores_editaveis.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."
    issue = issues[0]
    return (
        f"{issue['scope']}:{issue['objectId']} "
        f"{issue['code']}: {issue['message']}"
    )


def _passo(step, command, kind="command", legacy_step=None):
    payload = {
        "step": step,
        "kind": kind,
        "command": command,
    }
    if legacy_step:
        payload["legacyStep"] = legacy_step
    return payload
