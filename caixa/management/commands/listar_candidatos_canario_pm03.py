import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.validar_ativacao_canonical_first import (
    anotar_orientacao_candidato_controlado,
    montar_comandos_recomendados,
    montar_gate_operacional,
    montar_orientacao_candidato_controlado,
    montar_proxima_acao,
    resumir_comandos_orientacao_candidato_controlado,
    resumir_orientacao_candidato_controlado,
    resumir_obrigacoes_pendentes,
    resumir_saude_lista_candidatos,
)
from caixa.pm03_sequence import montar_posicao_sequencia_pm03


class Command(BaseCommand):
    help = (
        "Lista candidatos reais/controlados para canario rollback-only PM-03 "
        "usando a mesma regra dos validadores canonical-first."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de candidatos e pendencias sem canario retornados.",
        )
        parser.add_argument(
            "--username",
            default="",
            help="Usuario usado para preencher o comando de canario sugerido.",
        )
        parser.add_argument(
            "--payment-date",
            "--data-pagamento",
            dest="payment_date",
            default="",
            help="Data de pagamento usada para preencher o comando de canario sugerido.",
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
            help="Salva o payload JSON da descoberta em arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown da descoberta em arquivo.",
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
            help="Retorna erro quando nenhum candidato a pagar estiver disponivel.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        if options["exigir_arquivos_evidencia"]:
            _exigir_arquivos_evidencia(evidence_files)

        resultado = listar_candidatos_canario_pm03(
            source=options["source"],
            limit=options["limit"],
            username=options.get("username"),
            payment_date=options.get("payment_date"),
        )
        resultado["evidenceFiles"] = evidence_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_candidatos_canario_pm03(resultado),
        }
        _salvar_evidencias_candidatos(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_candidatos_canario_pm03(resultado))

    def _imprimir_relatorio(self, resultado):
        pendencias = resultado["pendingObligations"]
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Candidato PM-03 para canario encontrado.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Nenhum candidato PM-03 para canario encontrado.")
            )
        self.stdout.write(f"Origem: {resultado['source']}")
        decision = resultado.get("candidateDecision") or {}
        self.stdout.write(
            "Decisao candidato: "
            f"status={decision.get('status') or '-'}; "
            f"step={decision.get('step') or '-'}; "
            f"mayRunCanaryRollbackOnly={decision.get('mayRunCanaryRollbackOnly')}; "
            f"selectedSourceId={decision.get('selectedSourceId') or '-'}; "
            f"blockedBy={'; '.join(decision.get('blockedBy') or []) or '-'}"
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
            "Pendencias: "
            f"total={pendencias['count']}; "
            f"a pagar={pendencias['payableCount']}; "
            f"a receber={pendencias['receivableCount']}; "
            f"canario={pendencias['canaryEligibleCount']}"
        )
        self.stdout.write(
            "Listagem: "
            f"candidatos={pendencias.get('canaryCandidatesReturnedCount')}/"
            f"{pendencias.get('canaryEligibleCount')}; "
            f"truncada={pendencias.get('canaryCandidatesTruncated')}; "
            f"semCanario={pendencias.get('nonCanaryPendingItemsReturnedCount')}/"
            f"{pendencias.get('nonCanaryPendingCount')}; "
            f"semCanarioTruncada={pendencias.get('nonCanaryPendingItemsTruncated')}"
        )
        candidate_list_health = resultado.get("candidateListHealth") or {}
        if candidate_list_health:
            self.stdout.write(
                "Saude da lista: "
                f"status={candidate_list_health.get('status') or '-'}; "
                f"acao={candidate_list_health.get('recommendedAction') or '-'}; "
                f"detalhe={candidate_list_health.get('detail') or '-'}"
            )
        for candidato in pendencias.get("canaryCandidates") or []:
            self.stdout.write(
                "- candidato: "
                f"sourceId={candidato['sourceId']}; "
                f"obrigacao={candidato['obligationId']}; "
                f"pendente={candidato['pendingAmount']}; "
                f"vencimento={candidato['dueDate']}; "
                f"descricao={candidato['description']}"
            )
        for item in pendencias.get("nonCanaryPendingItems") or []:
            self.stdout.write(
                "- sem canario: "
                f"sourceId={item['sourceId']}; "
                f"obrigacao={item['obligationId']}; "
                f"tipo={item['obligationType']}; "
                f"motivo={item['ineligibilityReason']}"
            )
        orientacao = resultado.get("candidateCreationGuidance") or {}
        if orientacao.get("available") and not pendencias.get("canaryCandidates"):
            self.stdout.write("Orientacao para candidato controlado:")
            self.stdout.write(f"- admin: {orientacao.get('adminPath')}")
            self.stdout.write(
                "- acao: "
                f"{orientacao.get('recommendedAction')}; "
                f"requiredForNextCanary={orientacao.get('requiredForNextCanary')}"
            )
            self.stdout.write(f"- motivo: {orientacao.get('reason')}")
            for criterion in orientacao.get("criteria") or []:
                self.stdout.write(f"- criterio: {criterion}")
            for field, value in (orientacao.get("suggestedFields") or {}).items():
                self.stdout.write(f"- {field}: {value}")
            for index, command in enumerate(
                orientacao.get("afterCreateCommands") or [],
                start=1,
            ):
                self.stdout.write(f"- apos criar {index}: {command}")
        comando_canario = (
            (resultado.get("recommendedCommands") or {}).get("canaryRollbackOnly")
            or ""
        )
        if comando_canario:
            self.stdout.write(f"Canario sugerido: {comando_canario}")


def listar_candidatos_canario_pm03(
    source,
    limit=20,
    username=None,
    payment_date=None,
):
    if limit < 0:
        raise CommandError("--limit deve ser maior ou igual a 0.")

    source = str(source or "").strip()
    pendencias = resumir_obrigacoes_pendentes(source, limit=limit)
    comandos = montar_comandos_recomendados(
        source=source,
        username=username,
        payment_date=payment_date,
        pending_summary=pendencias,
    )
    canary = {
        "executed": False,
        "synced": None,
    }
    next_action = montar_proxima_acao(
        issues=[],
        pending_summary=pendencias,
        canary=canary,
        recommended_commands=comandos,
    )
    gate = montar_gate_operacional(
        source=source,
        pending_summary=pendencias,
        canary=canary,
        next_action=next_action,
        candidate_discovery_command=comandos.get("candidateDiscovery"),
    )
    issues = _coletar_issues_candidatos(pendencias)
    orientacao = montar_orientacao_candidato_controlado(
        source=source,
        payment_date=payment_date,
        candidate_discovery_command=comandos.get("candidateDiscovery"),
        after_create_commands=comandos.get("afterControlledCandidateCreate"),
    )
    orientacao = anotar_orientacao_candidato_controlado(orientacao, pendencias)
    candidate_decision = montar_decisao_candidato_pm03(
        source=source,
        pending_summary=pendencias,
        issues=issues,
        next_action=next_action,
        operational_gate=gate,
        recommended_commands=comandos,
    )
    return {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "source": source,
        "ready": not issues,
        "issues": issues,
        "candidateDecision": candidate_decision,
        "pendingObligations": pendencias,
        "candidateListHealth": resumir_saude_lista_candidatos(pendencias),
        "candidateCreationGuidance": orientacao,
        "nextAction": next_action,
        "operationalGate": gate,
        "sequencePosition": montar_posicao_sequencia_pm03(source),
        "recommendedCommands": comandos,
    }


def _coletar_issues_candidatos(pendencias):
    canary_count = int(pendencias.get("canaryEligibleCount") or 0)
    returned_count = int(pendencias.get("canaryCandidatesReturnedCount") or 0)
    if canary_count > 0 and returned_count == 0:
        return [
            (
                "Ha obrigacao a pagar elegivel para canario, mas o limite de "
                "listagem nao retornou nenhum candidato; reexecute com "
                "--limit maior que 0."
            )
        ]
    if canary_count > 0:
        return []
    if int(pendencias.get("nonCanaryPendingCount") or 0) > 0:
        return [
            (
                "Ha pendencia na origem, mas nenhuma obrigacao a pagar elegivel "
                "para canario rollback-only."
            )
        ]
    return ["Nenhuma obrigacao a pagar pendente elegivel para canario rollback-only."]


def montar_decisao_candidato_pm03(
    source,
    pending_summary,
    issues=None,
    next_action=None,
    operational_gate=None,
    recommended_commands=None,
):
    pending_summary = pending_summary or {}
    issues = [str(issue) for issue in (issues or []) if str(issue)]
    candidates = pending_summary.get("canaryCandidates") or []
    first_candidate = candidates[0] if candidates else {}
    next_action = next_action or {}
    operational_gate = operational_gate or {}
    recommended_commands = recommended_commands or {}
    may_run = (
        not issues
        and int(pending_summary.get("canaryEligibleCount") or 0) > 0
        and bool(candidates)
        and next_action.get("key") == "runCanaryRollbackOnly"
        and operational_gate.get("status") == "readyForCanaryRollbackOnly"
    )
    if may_run:
        status = "readyForCanaryRollbackOnly"
        label = "Candidato pronto para canario rollback-only"
        detail = "Usar o sourceId selecionado no canario rollback-only."
        suggested_command = recommended_commands.get("canaryRollbackOnly") or ""
    elif next_action.get("key") == "expandCanaryCandidateList":
        status = "blockedCandidateListLimit"
        label = "Lista de candidatos sem sourceId retornado"
        detail = (
            "Reexecutar a descoberta com --limit maior que 0 antes de tentar "
            "o canario rollback-only."
        )
        suggested_command = (
            next_action.get("suggestedCommand")
            or recommended_commands.get("candidateDiscovery")
            or ""
        )
    else:
        status = "blocked"
        label = "Candidato para canario bloqueado"
        detail = (
            "Nao executar canario rollback-only antes de obter uma obrigacao "
            "a pagar pendente elegivel."
        )
        suggested_command = recommended_commands.get("canaryRollbackOnly") or ""
    return {
        "status": status,
        "label": label,
        "source": source,
        "step": operational_gate.get("currentStep") or "",
        "mayRunCanaryRollbackOnly": may_run,
        "selectedSourceId": str(first_candidate.get("sourceId") or ""),
        "selectedObligationId": str(first_candidate.get("obligationId") or ""),
        "candidateCount": int(pending_summary.get("canaryEligibleCount") or 0),
        "nonCanaryPendingCount": int(
            pending_summary.get("nonCanaryPendingCount") or 0
        ),
        "blockedBy": [] if may_run else issues,
        "suggestedCommand": suggested_command,
        "detail": detail,
    }


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias", "")
    save_json = options.get("salvar_json", "")
    save_record = options.get("salvar_registro", "")

    if directory:
        base_path = Path(directory).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError("--diretorio-evidencias deve apontar para um diretorio")
        if not save_json:
            save_json = str(base_path / "pm03-candidatos-canario.json")
        if not save_record:
            save_record = str(base_path / "pm03-candidatos-canario.md")

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


def _salvar_evidencias_candidatos(resultado):
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


def _registro_candidatos_canario_pm03(resultado):
    pendencias = resultado["pendingObligations"]
    gate = resultado.get("operationalGate") or {}
    decision = resultado.get("candidateDecision") or {}
    sequence_position = resultado.get("sequencePosition") or {}
    candidate_list_health = resultado.get("candidateListHealth") or {}
    issues = "; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"
    evidence_files = resultado.get("evidenceFiles") or {}
    return "\n".join(
        [
            "### Registro PM-03 - candidatos para canario rollback-only",
            "",
            f"Data/hora da descoberta: {resultado['generatedAt']}",
            f"Origem: {resultado['source']}",
            f"ready/issues: ready={resultado['ready']}; issues={issues}",
            (
                "Decisao candidato: "
                f"status={decision.get('status') or '-'}; "
                f"step={decision.get('step') or '-'}; "
                f"mayRunCanaryRollbackOnly={decision.get('mayRunCanaryRollbackOnly')}; "
                f"selectedSourceId={decision.get('selectedSourceId') or '-'}; "
                f"blockedBy={'; '.join(decision.get('blockedBy') or []) or '-'}"
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
                "Listagem: "
                f"candidatos={pendencias.get('canaryCandidatesReturnedCount')}/"
                f"{pendencias.get('canaryEligibleCount')}; "
                f"truncada={pendencias.get('canaryCandidatesTruncated')}; "
                f"semCanario={pendencias.get('nonCanaryPendingItemsReturnedCount')}/"
                f"{pendencias.get('nonCanaryPendingCount')}; "
                f"semCanarioTruncada={pendencias.get('nonCanaryPendingItemsTruncated')}"
            ),
            (
                "Saude da lista: "
                f"status={candidate_list_health.get('status') or '-'}; "
                f"retornados={candidate_list_health.get('returnedCount')}; "
                f"elegiveis={candidate_list_health.get('eligibleCount')}; "
                f"limite={candidate_list_health.get('limit')}; "
                f"truncada={candidate_list_health.get('truncated')}; "
                f"acao={candidate_list_health.get('recommendedAction') or '-'}"
            ),
            f"Candidatos canario: {_resumir_candidatos(pendencias)}",
            f"Pendencias sem canario: {_resumir_pendencias_sem_canario(pendencias)}",
            f"Candidato controlado: {_resumir_orientacao_controlada(resultado)}",
            (
                "Comandos apos candidato: "
                f"{resumir_comandos_orientacao_candidato_controlado(resultado.get('candidateCreationGuidance'))}"
            ),
            (
                "Canario sugerido: "
                f"{(resultado.get('recommendedCommands') or {}).get('canaryRollbackOnly') or '-'}"
            ),
            (
                "Arquivos salvos: "
                f"diretorio={evidence_files.get('directory') or '-'}; "
                f"json={evidence_files.get('json') or '-'}; "
                f"registro={evidence_files.get('record') or '-'}"
            ),
            (
                "Proxima acao: "
                f"{(resultado.get('nextAction') or {}).get('key') or '-'}; "
                f"{(resultado.get('nextAction') or {}).get('detail') or '-'}"
            ),
        ]
    )


def _resumir_candidatos(pendencias):
    candidatos = pendencias.get("canaryCandidates") or []
    if not candidatos:
        return "-"
    return "; ".join(
        (
            f"sourceId={item['sourceId']} obrigacao={item['obligationId']} "
            f"pendente={item['pendingAmount']} vencimento={item['dueDate']}"
        )
        for item in candidatos
    )


def _resumir_pendencias_sem_canario(pendencias):
    itens = pendencias.get("nonCanaryPendingItems") or []
    if not itens:
        return "-"
    return "; ".join(
        (
            f"sourceId={item['sourceId']} obrigacao={item['obligationId']} "
            f"tipo={item['obligationType']} motivo={item['ineligibilityReason']}"
        )
        for item in itens
    )


def _resumir_orientacao_controlada(resultado):
    return resumir_orientacao_candidato_controlado(
        resultado.get("candidateCreationGuidance")
    )


def formatar_erro_candidatos_canario_pm03(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Candidato PM-03 para canario nao encontrado: {issues[0]}"
    return "Candidato PM-03 para canario nao encontrado."
