import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date

from caixa.constants_nomenclatura import VERSAO_REMOCAO_ALIASES_LEGADOS


DEFAULT_OUTPUT_JSON = "pm06-prontidao-migracao-limpeza.json"
DEFAULT_OUTPUT_RECORD = "pm06-prontidao-migracao-limpeza.md"
DEFAULT_PM06_CLOSURE_JSON = "pm06-fechamento.json"
DEFAULT_LEGACY_FREEZE_JSON = "pm06-prontidao-congelamento-legado.json"
DEFAULT_ROLLBACK_CONCILIATION_JSON = "pm06-rollback-conciliacao-janela.json"
DEFAULT_MANUAL_REENTRY_JSON = "pm06-validacao-recadastro-manual.json"
FRONTEND_CANONICAL_VALIDATION_MARKERS = (
    "verify:publish",
    "verify-publish",
    "check:financial-canonical",
    "check-financial-canonical",
    "financial-canonical",
)


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, se a PM-06 pode criar migrations de "
        "limpeza. O comando nao cria nem aplica migrations e nao altera dados."
    )

    def add_arguments(self, parser):
        parser.add_argument("--pm06-fechamento-json", default="")
        parser.add_argument("--congelamento-legado-json", default="")
        parser.add_argument("--rollback-conciliacao-json", default="")
        parser.add_argument("--recadastro-manual-json", default="")
        parser.add_argument("--backup-ref", default="")
        parser.add_argument("--homologacao-ref", default="")
        parser.add_argument("--auditoria-sem-divergencias-ref", default="")
        parser.add_argument("--aceite-operacional-ref", default="")
        parser.add_argument("--rollback-plan-ref", default="")
        parser.add_argument("--conciliation-script-ref", default="")
        parser.add_argument("--migration-plan-ref", default="")
        parser.add_argument("--revisao-semantica", action="store_true")
        parser.add_argument("--revisao-tecnica", action="store_true")
        parser.add_argument("--revisao-extra", action="store_true")
        parser.add_argument("--liberar-criacao-migrations", action="store_true")
        parser.add_argument("--exigir-recadastro-manual", action="store_true")
        parser.add_argument("--diretorio-evidencias", default="")
        parser.add_argument("--salvar-json", "--save-json", default="")
        parser.add_argument("--salvar-registro", "--save-record", default="")
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            action="store_true",
            help="Exige caminhos para salvar JSON e registro markdown.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado consolidado em JSON.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando migrations de limpeza ainda estiverem bloqueadas.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        output_files = _normalizar_arquivos_saida(options)
        payloads, load_checks = _carregar_payloads(evidence_files)
        resultado = validar_prontidao_migracao_limpeza_pm06(
            _normalizar_referencias(options),
            payloads=payloads,
            load_checks=load_checks,
            evidence_files=evidence_files,
            output_files=output_files,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_prontidao_migracao_limpeza_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao de prontidao de migration de limpeza PM-06 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        decision = resultado["cleanupMigrationDecision"]
        self.stdout.write(
            "cleanupMigrationDecision="
            f"{decision['status']}; "
            f"mayCreateCleanupMigrations={decision['mayCreateCleanupMigrations']}; "
            f"mayApplyCleanupMigrations={decision['mayApplyCleanupMigrations']}"
        )
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_prontidao_migracao_limpeza_pm06(
    references,
    *,
    payloads=None,
    load_checks=None,
    evidence_files=None,
    output_files=None,
):
    references = references or {}
    payloads = payloads or {}
    load_checks = load_checks or {"byKey": {}}
    loaders = load_checks.get("byKey") or {}
    evidence_files = evidence_files or {}
    output_files = output_files or {}
    requirements = references.get("requirements") or {}

    checks = [
        _check(
            "inputEvidenceFiles",
            "Arquivos de evidencia de entrada",
            _validar_evidencias_entrada_distintas(evidence_files),
        ),
        _check(
            "pm06Closure",
            "Fechamento PM-06 aprovado",
            _validar_payload_carregado(
                payloads.get("pm06Closure"),
                loaders.get("pm06Closure"),
                "pm06-fechamento-json",
                _validar_payload_fechamento_pm06,
            ),
        ),
        _check(
            "legacyFreeze",
            "Congelamento legado aprovado",
            _validar_payload_carregado(
                payloads.get("legacyFreeze"),
                loaders.get("legacyFreeze"),
                "congelamento-legado-json",
                _validar_payload_congelamento_legado,
            ),
        ),
        _check(
            "rollbackConciliation",
            "Rollback/conciliacao da janela aprovado",
            _validar_payload_carregado(
                payloads.get("rollbackConciliation"),
                loaders.get("rollbackConciliation"),
                "rollback-conciliacao-json",
                _validar_payload_rollback_conciliacao,
            ),
        ),
        _check(
            "manualReentry",
            "Recadastro manual aprovado",
            _validar_evidencia_recadastro_manual(
                payloads.get("manualReentry"),
                loaders.get("manualReentry"),
                requirements.get("manualReentry"),
            ),
        ),
        _check("backup", "Backup da janela", _validar_referencia(references.get("backupRef"), "backup-ref")),
        _check(
            "homologation",
            "Homologacao sem divergencias",
            _validar_referencia(references.get("homologationRef"), "homologacao-ref"),
        ),
        _check(
            "audit",
            "Auditoria sem divergencias",
            _validar_referencia(
                references.get("auditWithoutDivergencesRef"),
                "auditoria-sem-divergencias-ref",
            ),
        ),
        _check(
            "operationalAcceptance",
            "Aceite operacional",
            _validar_referencia(references.get("operationalAcceptanceRef"), "aceite-operacional-ref"),
        ),
        _check(
            "rollbackPlan",
            "Plano de rollback",
            _validar_referencia(references.get("rollbackPlanRef"), "rollback-plan-ref"),
        ),
        _check(
            "conciliationScript",
            "Script/plano de conciliacao",
            _validar_referencia(
                references.get("conciliationScriptRef"),
                "conciliation-script-ref",
            ),
        ),
        _check(
            "migrationPlan",
            "Plano de migration pequena",
            _validar_referencia(references.get("migrationPlanRef"), "migration-plan-ref"),
        ),
        _check(
            "finalReviews",
            "Revisoes finais antes da migration",
            _validar_revisoes_finais(references),
        ),
        _check(
            "explicitRelease",
            "Liberacao explicita de criacao de migrations",
            _validar_flag(
                references.get("releaseMigrationCreation"),
                "liberar-criacao-migrations",
            ),
        ),
        _check(
            "outputEvidenceFiles",
            "Arquivos de evidencia",
            _validar_arquivos_saida(
                output_files,
                exigir=requirements.get("outputEvidenceFiles"),
                input_files=evidence_files,
            ),
        ),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]
    decision = _montar_decisao_migracao_limpeza(ready, issues)

    return {
        "source": "pm06_cleanup_migration_readiness",
        "step": "PM-06",
        "readOnly": True,
        "ready": ready,
        "issues": issues,
        "checks": checks,
        "checksSummary": {
            "ready": ready,
            "total": len(checks),
            "okCount": sum(1 for check in checks if check["ok"]),
            "pending": pending,
            "pendingCount": len(pending),
            "issueCount": len(issues),
        },
        "cleanupMigrationDecision": decision,
        "frontendCanonicalValidationPolicy": _resumir_politica_validacao_frontend(),
        "references": references,
        "evidenceFiles": evidence_files,
        "generatedAt": timezone.now().isoformat(),
        "recommendedCommands": {
            "pm06Closure": (
                "python manage.py validar_fechamento_pm06 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "manualReentryValidation": (
                "python manage.py validar_recadastro_manual_pm06 "
                "--recadastro-json=<pm06-recadastro-manual.json> "
                "--comparar-base-atual "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "rerunCleanupMigrationReadiness": (
                "python manage.py validar_prontidao_migracao_limpeza_pm06 "
                "--pm06-fechamento-json=<pm06-fechamento.json> "
                "--congelamento-legado-json=<pm06-prontidao-congelamento-legado.json> "
                "--rollback-conciliacao-json=<pm06-rollback-conciliacao-janela.json> "
                "--recadastro-manual-json=<pm06-validacao-recadastro-manual.json> "
                "--backup-ref=<backup-ref> "
                "--homologacao-ref=<homologacao-sem-divergencias> "
                "--auditoria-sem-divergencias-ref=<auditoria-sem-divergencias> "
                "--aceite-operacional-ref=<aceite-operacional> "
                "--rollback-plan-ref=<rollback-plan> "
                "--conciliation-script-ref=<script-conciliacao> "
                "--migration-plan-ref=<plano-migration-pequena> "
                "--revisao-semantica --revisao-tecnica --revisao-extra "
                "--liberar-criacao-migrations --exigir-recadastro-manual "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        },
    }


def _normalizar_referencias(options):
    return {
        "backupRef": options.get("backup_ref") or "",
        "homologationRef": options.get("homologacao_ref") or "",
        "auditWithoutDivergencesRef": options.get("auditoria_sem_divergencias_ref") or "",
        "operationalAcceptanceRef": options.get("aceite_operacional_ref") or "",
        "rollbackPlanRef": options.get("rollback_plan_ref") or "",
        "conciliationScriptRef": options.get("conciliation_script_ref") or "",
        "migrationPlanRef": options.get("migration_plan_ref") or "",
        "semanticReview": bool(options.get("revisao_semantica")),
        "technicalReview": bool(options.get("revisao_tecnica")),
        "extraReview": bool(options.get("revisao_extra")),
        "releaseMigrationCreation": bool(options.get("liberar_criacao_migrations")),
        "requirements": {
            "outputEvidenceFiles": bool(options.get("exigir_arquivos_evidencia")),
            "manualReentry": bool(options.get("exigir_recadastro_manual")),
        },
    }


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    base = Path(directory) if directory else None
    evidence_files = {
        "pm06Closure": options.get("pm06_fechamento_json")
        or (str(base / DEFAULT_PM06_CLOSURE_JSON) if base else ""),
        "legacyFreeze": options.get("congelamento_legado_json")
        or (str(base / DEFAULT_LEGACY_FREEZE_JSON) if base else ""),
        "rollbackConciliation": options.get("rollback_conciliacao_json")
        or (str(base / DEFAULT_ROLLBACK_CONCILIATION_JSON) if base else ""),
    }
    manual_reentry = options.get("recadastro_manual_json") or (
        str(base / DEFAULT_MANUAL_REENTRY_JSON)
        if base and options.get("exigir_recadastro_manual")
        else ""
    )
    if manual_reentry or options.get("exigir_recadastro_manual"):
        evidence_files["manualReentry"] = manual_reentry
    return evidence_files


def _normalizar_arquivos_saida(options):
    directory = options.get("diretorio_evidencias") or ""
    output_json = options.get("salvar_json") or ""
    output_record = options.get("salvar_registro") or ""
    if directory:
        base = Path(directory)
        output_json = output_json or str(base / DEFAULT_OUTPUT_JSON)
        output_record = output_record or str(base / DEFAULT_OUTPUT_RECORD)
    return {
        "json": output_json,
        "record": output_record,
    }


def _validar_evidencias_entrada_distintas(evidence_files):
    issues = []
    by_path = {}
    for key, value in (evidence_files or {}).items():
        if not value:
            continue
        if Path(str(value)).suffix.lower() != ".json":
            issues.append(f"evidencia de entrada PM-06 deve usar extensao .json: {key}")
        normalized = _normalizar_caminho_saida(value)
        previous_key = by_path.get(normalized)
        if previous_key:
            issues.append(
                "evidencias de entrada PM-06 usam o mesmo caminho: "
                f"{previous_key} e {key}"
            )
        else:
            by_path[normalized] = key
    return issues


def _carregar_payloads(evidence_files):
    payloads = {}
    checks = {"byKey": {}}
    labels = {
        "pm06Closure": "pm06-fechamento-json",
        "legacyFreeze": "congelamento-legado-json",
        "rollbackConciliation": "rollback-conciliacao-json",
        "manualReentry": "recadastro-manual-json",
    }
    for key, path in evidence_files.items():
        payload, issues = _carregar_json(path, labels.get(key, f"{key}-json"))
        if payload is not None:
            payloads[key] = payload
        checks["byKey"][key] = {"path": path, "issues": issues}
    return payloads, checks


def _carregar_json(path, label):
    if not path:
        return None, [f"{label} nao informado"]
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None, [f"{label} nao encontrado"]
    try:
        return json.loads(file_path.read_text(encoding="utf-8-sig")), []
    except json.JSONDecodeError as error:
        return None, [f"{label} invalido: {error}"]


def _validar_payload_carregado(payload, loader, label, validar_identidade):
    load_issues = (loader or {}).get("issues") or []
    if load_issues:
        return load_issues
    issues = _validar_payload_ready(payload, label)
    if issues:
        return issues
    return validar_identidade(payload, label)


def _validar_evidencia_recadastro_manual(payload, loader, required):
    if not required and not (loader or {}).get("path"):
        return []
    return _validar_payload_carregado(
        payload,
        loader,
        "recadastro-manual-json",
        _validar_payload_recadastro_manual,
    )


def _validar_payload_ready(payload, label):
    if not isinstance(payload, dict):
        return [f"payload {label} ausente ou invalido"]
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return [f"{label} sem lista de issues"]
    if isinstance(issues, list) and issues:
        return [f"{label} contem pendencia: {issue}" for issue in issues]
    if payload.get("ready") is not True:
        return [f"{label} nao aprovado"]
    checks = payload.get("checks")
    if checks is not None:
        if not isinstance(checks, list):
            return [f"{label} checks invalido"]
        check_issues = []
        for check in checks:
            if not isinstance(check, dict):
                check_issues.append(f"{label} contem check invalido")
                continue
            check_key = check.get("key") or "sem-chave"
            check_pending = check.get("issues")
            if check_pending is not None and not isinstance(check_pending, list):
                check_issues.append(
                    f"{label} check {check_key} possui issues invalido"
                )
            elif isinstance(check_pending, list) and check_pending:
                check_issues.extend(
                    f"{label} contem pendencia em check {check_key}: {issue}"
                    for issue in check_pending
                )
            if check.get("ok") is not True:
                check_issues.append(
                    f"{label} contem check nao aprovado: {check_key}"
                )
        if check_issues:
            return check_issues
    summary = payload.get("checksSummary")
    if isinstance(summary, dict):
        summary_issues = []
        pending = summary.get("pending")
        if summary.get("ready") is not True:
            summary_issues.append(f"{label} checksSummary nao aprovado")
        if pending is not None and not isinstance(pending, list):
            summary_issues.append(f"{label} checksSummary pending invalido")
        elif isinstance(pending, list) and pending:
            summary_issues.extend(
                f"{label} contem check pendente: {check}" for check in pending
            )
        if checks is not None and summary.get("total") not in (None, len(checks)):
            summary_issues.append(f"{label} checksSummary total nao confere com checks")
        if checks is not None:
            expected_ok_count = sum(
                1
                for check in checks
                if isinstance(check, dict) and check.get("ok") is True
            )
            if summary.get("okCount") not in (None, expected_ok_count):
                summary_issues.append(
                    f"{label} checksSummary okCount nao confere com checks"
                )
        if summary.get("pendingCount") not in (None, 0):
            summary_issues.append(f"{label} checksSummary pendingCount nao zerado")
        if summary.get("issueCount") not in (None, 0):
            summary_issues.append(f"{label} checksSummary issueCount nao zerado")
        if summary_issues:
            return summary_issues
    return []


def _validar_payload_fechamento_pm06(payload, label):
    issues = []
    if payload.get("source") != "pm06_closure_validation":
        issues.append(f"{label} nao e evidencia de fechamento PM-06")
    if payload.get("step") != "PM-06":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")
    decision = payload.get("closureDecision")
    if not isinstance(decision, dict):
        issues.append(f"{label} decisao de fechamento invalida")
        decision = {}
    issues.extend(_validar_decisao_sem_bloqueios(decision, label, "fechamento"))
    if decision.get("status") != "approved":
        issues.append(f"{label} decisao de fechamento nao aprovada")
    if decision.get("mayMarkCurrentStepDone") not in (None, True):
        issues.append(f"{label} nao marca PM-06 como concluida")
    if decision.get("mayAdvanceSequence") is not True:
        issues.append(f"{label} nao libera sequencia PM-06")
    if decision.get("mayStartNextStep") is not True:
        issues.append(f"{label} nao libera proxima etapa PM-06")
    if decision.get("nextStep") not in (None, "PM-07"):
        issues.append(f"{label} decisao de fechamento nextStep invalido")
    issues.extend(_validar_referencias_fechamento_pm06(payload, label))
    issues.extend(_validar_politica_validacao_frontend(payload, label))
    issues.extend(_validar_politica_financeiro_v3_fechamento(payload, label))
    next_action = payload.get("closureNextAction")
    if next_action is not None:
        if not isinstance(next_action, dict):
            issues.append(f"{label} acao de fechamento invalida")
        else:
            if next_action.get("key") not in (None, "advanceToPm07"):
                issues.append(f"{label} acao de fechamento chave invalida")
            if next_action.get("status") not in (None, "ready"):
                issues.append(f"{label} acao de fechamento status invalido")
            if next_action.get("nextStep") not in (None, "PM-07"):
                issues.append(f"{label} acao de fechamento nextStep invalido")
            if next_action.get("mayAdvanceSequence") not in (None, True):
                issues.append(f"{label} acao de fechamento nao libera sequencia PM-06")
            if next_action.get("mayStartNextStep") not in (None, True):
                issues.append(f"{label} acao de fechamento nao libera proxima etapa PM-06")
    return issues


def _validar_referencias_fechamento_pm06(payload, label):
    references = payload.get("references")
    if references is None:
        return []
    if not isinstance(references, dict):
        return [f"{label} referencias de fechamento invalidas"]
    return _validar_frontend_validacao_ref(
        references.get("frontendValidationRef"),
        label,
    )


def _validar_frontend_validacao_ref(value, label):
    if not str(value or "").strip():
        return [f"{label} frontend-validacao-ref nao informado"]
    normalized = str(value or "").strip().lower()
    if any(marker in normalized for marker in FRONTEND_CANONICAL_VALIDATION_MARKERS):
        return []
    return [
        f"{label} frontend-validacao-ref nao comprova guardrail canonico do frontend"
    ]


def _validar_politica_validacao_frontend(payload, label):
    policy = payload.get("frontendCanonicalValidationPolicy")
    if policy is None:
        return []
    if not isinstance(policy, dict):
        return [f"{label} politica de validacao frontend canonica invalida"]

    issues = []
    if policy.get("required") is not True:
        issues.append(f"{label} politica de validacao frontend nao obrigatoria")

    markers = policy.get("acceptedMarkers")
    if not isinstance(markers, list) or not markers:
        issues.append(f"{label} politica de validacao frontend sem marcadores")
    else:
        normalized_markers = [str(marker).strip().lower() for marker in markers]
        if not any("financial-canonical" in marker for marker in normalized_markers):
            issues.append(
                f"{label} politica de validacao frontend sem marcador financial-canonical"
            )

    rule = str(policy.get("rule") or "").strip().lower()
    if "financial-canonical" not in rule:
        issues.append(
            f"{label} politica de validacao frontend sem regra financial-canonical"
        )

    alias_removal_version = policy.get("aliasRemovalVersion")
    if (
        alias_removal_version is not None
        and alias_removal_version != VERSAO_REMOCAO_ALIASES_LEGADOS
    ):
        issues.append(
            f"{label} politica de validacao frontend com corte de aliases invalido"
        )
    return issues


def _validar_politica_financeiro_v3_fechamento(payload, label):
    policy = payload.get("financeiroV3Policy")
    if policy is None:
        return []
    if not isinstance(policy, dict):
        return [f"{label} politica financeiro-v3 invalida"]

    issues = []
    if policy.get("removeOnlyInVersion") != VERSAO_REMOCAO_ALIASES_LEGADOS:
        issues.append(f"{label} politica financeiro-v3 sem versao de corte esperada")
    if policy.get("currentVersion") == policy.get("removeOnlyInVersion"):
        issues.append(
            f"{label} contrato atual ja esta na versao de remocao de aliases"
        )
    if not str(policy.get("rule") or "").strip():
        issues.append(f"{label} politica financeiro-v3 sem regra documentada")
    return issues


def _resumir_politica_validacao_frontend():
    return {
        "required": True,
        "acceptedMarkers": list(FRONTEND_CANONICAL_VALIDATION_MARKERS),
        "rule": (
            "frontendValidationRef deve comprovar verify:publish/verify-publish "
            "com check:financial-canonical ou execucao direta do check financeiro canonico."
        ),
        "aliasRemovalVersion": VERSAO_REMOCAO_ALIASES_LEGADOS,
        "aliasCompatibilityRule": (
            "Aliases legados permanecem preservados apenas nas bordas de "
            "compatibilidade ate o corte financeiro-v3."
        ),
    }


def _validar_payload_congelamento_legado(payload, label):
    issues = []
    if payload.get("source") != "pm06_legacy_freeze_readiness":
        issues.append(f"{label} nao e evidencia de congelamento legado PM-06")
    if payload.get("step") != "PM-06":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")
    decision = payload.get("freezeDecision")
    if not isinstance(decision, dict):
        issues.append(f"{label} decisao de congelamento invalida")
        decision = {}
    issues.extend(_validar_decisao_sem_bloqueios(decision, label, "congelamento"))
    if decision.get("status") != "approved":
        issues.append(f"{label} decisao de congelamento nao aprovada")
    if decision.get("mayFreezeLegacyWrites") is not True:
        issues.append(f"{label} nao libera congelamento de escrita legada")
    if decision.get("mayCreateCleanupMigrations") is not False:
        issues.append(f"{label} nao preserva bloqueio de migrations de limpeza")
    issues.extend(_validar_referencias_congelamento_legado(payload, label))
    issues.extend(_validar_politica_validacao_frontend(payload, label))
    issues.extend(_validar_escopo_congelamento_financeiro_v3(payload, label))
    return issues


def _validar_payload_rollback_conciliacao(payload, label):
    issues = []
    if payload.get("source") != "pm06_rollback_conciliation_window":
        issues.append(f"{label} nao e evidencia de rollback/conciliacao PM-06")
    if payload.get("step") != "PM-06":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")
    issues.extend(_validar_janela_rollback(payload, label))
    decision = payload.get("rollbackConciliationDecision")
    if not isinstance(decision, dict):
        issues.append(f"{label} decisao de rollback/conciliacao invalida")
        decision = {}
    issues.extend(_validar_decisao_sem_bloqueios(decision, label, "rollback/conciliacao"))
    if decision.get("status") != "approved":
        issues.append(f"{label} decisao de rollback/conciliacao nao aprovada")
    if decision.get("mayUseForCleanupMigrationGate") is not True:
        issues.append(f"{label} nao libera uso no gate de migration de limpeza")
    if decision.get("mayExecuteRollback") is not False:
        issues.append(f"{label} nao preserva bloqueio de execucao de rollback")
    if decision.get("mayExecuteConciliation") is not False:
        issues.append(f"{label} nao preserva bloqueio de execucao de conciliacao")
    issues.extend(_validar_referencias_rollback_conciliacao(payload, label))
    issues.extend(_validar_consistencia_janela_referencias(payload, label))
    issues.extend(_validar_plan_files_rollback(payload, label))
    issues.extend(_validar_consistencia_plan_files_referencias(payload, label))
    return issues


def _validar_payload_recadastro_manual(payload, label):
    issues = []
    if payload.get("source") != "pm06_manual_reentry_readiness":
        issues.append(f"{label} nao e evidencia de recadastro manual PM-06")
    if payload.get("step") != "PM-06":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")

    decision = payload.get("manualReentryDecision")
    if not isinstance(decision, dict):
        issues.append(f"{label} decisao de recadastro manual invalida")
        decision = {}
    if decision.get("status") != "approved":
        issues.append(f"{label} decisao de recadastro manual nao aprovada")
    if decision.get("mayUseForManualReentry") is not True:
        issues.append(f"{label} nao libera uso para recadastro manual")
    if decision.get("mayCleanData") is not False:
        issues.append(f"{label} nao preserva bloqueio de limpeza de dados")
    if decision.get("mayRestoreAutomatically") is not False:
        issues.append(f"{label} nao preserva bloqueio de restauracao automatica")

    comparison = payload.get("currentDatabaseComparison")
    if not isinstance(comparison, dict):
        issues.append(f"{label} sem comparacao com base atual")
    elif comparison.get("compared") is not True:
        issues.append(f"{label} nao comparou pacote com base atual")
    elif comparison.get("differences"):
        issues.append(f"{label} possui divergencias com base atual")

    summary = payload.get("packageSummary")
    if not isinstance(summary, dict):
        issues.append(f"{label} sem packageSummary")
    else:
        for key in (
            "clientsCount",
            "budgetsCount",
            "eventsCount",
            "fixedCostsCount",
            "fcfDebtsCount",
        ):
            if not isinstance(summary.get(key), int):
                issues.append(f"{label} packageSummary.{key} ausente ou invalido")
    return issues


def _validar_referencias_congelamento_legado(payload, label):
    references = payload.get("references")
    if references is None:
        return []
    if not isinstance(references, dict):
        return [f"{label} referencias de congelamento invalidas"]
    return _validar_frontend_validacao_ref(
        references.get("frontendValidationRef"),
        label,
    )


def _validar_escopo_congelamento_financeiro_v3(payload, label):
    scope = payload.get("freezeScope")
    if scope is None:
        return []
    if not isinstance(scope, dict):
        return [f"{label} escopo de congelamento invalido"]

    issues = []
    if scope.get("removeOnlyInVersion") != VERSAO_REMOCAO_ALIASES_LEGADOS:
        issues.append(
            f"{label} escopo de congelamento sem versao de corte esperada"
        )
    if scope.get("currentContractVersion") == scope.get("removeOnlyInVersion"):
        issues.append(
            f"{label} escopo de congelamento ja esta na versao de remocao de aliases"
        )
    if not str(scope.get("aliasRemovalRule") or "").strip():
        issues.append(f"{label} escopo de congelamento sem regra de aliases")
    return issues


def _validar_janela_rollback(payload, label):
    window = payload.get("window")
    if window is None:
        return []
    if not isinstance(window, dict):
        return [f"{label} janela de rollback/conciliacao invalida"]
    issues = []
    if not str(window.get("ref") or "").strip():
        issues.append(f"{label} janela de rollback/conciliacao sem referencia")
    start_value = str(window.get("start") or "").strip()
    end_value = str(window.get("end") or "").strip()
    start = _parse_date_safe(start_value) if start_value else None
    end = _parse_date_safe(end_value) if end_value else None
    if not start_value:
        issues.append(f"{label} janela de rollback/conciliacao sem inicio informado")
    elif start is None:
        issues.append(f"{label} janela de rollback/conciliacao inicio invalido")
    if not end_value:
        issues.append(f"{label} janela de rollback/conciliacao sem fim informado")
    elif end is None:
        issues.append(f"{label} janela de rollback/conciliacao fim invalido")
    if window.get("startValid") is not True:
        issues.append(f"{label} janela de rollback/conciliacao sem inicio valido")
    if window.get("endValid") is not True:
        issues.append(f"{label} janela de rollback/conciliacao sem fim valido")
    if start and end and start > end:
        issues.append(
            f"{label} janela de rollback/conciliacao inicio maior que fim"
        )
    if window.get("ordered") is not True:
        issues.append(f"{label} janela de rollback/conciliacao nao ordenada")
    return issues


def _parse_date_safe(value):
    try:
        return parse_date(value)
    except ValueError:
        return None


def _validar_plan_files_rollback(payload, label):
    plan_files = payload.get("planFiles")
    if plan_files is None:
        return []
    if not isinstance(plan_files, dict):
        return [f"{label} arquivos de plano de rollback invalidos"]
    issues = []
    required_keys = (
        ("rollbackPlan", "rollback"),
        ("conciliationScript", "conciliacao"),
        ("deltaDataPolicy", "politica de dados delta"),
    )
    for key, description in required_keys:
        if not str(plan_files.get(key) or "").strip():
            issues.append(
                f"{label} arquivo de plano de {description} nao informado"
            )
    return issues


def _validar_referencias_rollback_conciliacao(payload, label):
    references = payload.get("references")
    if references is None:
        return []
    if not isinstance(references, dict):
        return [f"{label} referencias de rollback/conciliacao invalidas"]

    issues = []
    required_refs = (
        ("backupRef", "backup-ref"),
        ("windowRef", "codigo-janela-ref"),
        ("windowStart", "janela-inicio"),
        ("windowEnd", "janela-fim"),
        ("rollbackPlanRef", "rollback-plan-ref"),
        ("conciliationScriptRef", "conciliation-script-ref"),
        ("deltaDataPolicyRef", "delta-data-policy-ref"),
        ("ownerRef", "owner-ref"),
        ("homologationRef", "homologacao-ref"),
        ("operationalAcceptanceRef", "aceite-operacional-ref"),
    )
    for key, reference_label in required_refs:
        issues.extend(_validar_referencia(references.get(key), reference_label))
    issues.extend(_validar_janela_referencias_rollback(references))
    issues.extend(_validar_requisitos_referencias_rollback(references))
    issues.extend(_validar_revisoes_finais(references))
    return [f"{label} {issue}" for issue in issues]


def _validar_janela_referencias_rollback(references):
    start_value = str(references.get("windowStart") or "").strip()
    end_value = str(references.get("windowEnd") or "").strip()
    start = _parse_date_safe(start_value) if start_value else None
    end = _parse_date_safe(end_value) if end_value else None

    issues = []
    if start_value and start is None:
        issues.append("janela-inicio invalido")
    if end_value and end is None:
        issues.append("janela-fim invalido")
    if start and end and start > end:
        issues.append("janela-inicio maior que janela-fim")
    return issues


def _validar_requisitos_referencias_rollback(references):
    requirements = references.get("requirements")
    if requirements is None:
        return []
    if not isinstance(requirements, dict):
        return ["requirements de rollback/conciliacao invalidos"]
    issues = []
    if requirements.get("planFiles") is not True:
        issues.append("exigir-arquivos-plano nao confirmado")
    if requirements.get("outputEvidenceFiles") is not True:
        issues.append("exigir-arquivos-evidencia nao confirmado")
    return issues


def _validar_consistencia_janela_referencias(payload, label):
    window = payload.get("window")
    references = payload.get("references")
    if window is None or references is None:
        return []
    if not isinstance(window, dict) or not isinstance(references, dict):
        return []

    issues = []
    expected_pairs = (
        ("ref", "windowRef", "referencia"),
        ("start", "windowStart", "inicio"),
        ("end", "windowEnd", "fim"),
    )
    for window_key, reference_key, description in expected_pairs:
        window_value = str(window.get(window_key) or "").strip()
        reference_value = str(references.get(reference_key) or "").strip()
        if window_value and reference_value and window_value != reference_value:
            issues.append(
                f"{label} janela de rollback/conciliacao {description} diverge das referencias"
            )
    return issues


def _validar_consistencia_plan_files_referencias(payload, label):
    references = payload.get("references")
    plan_files = payload.get("planFiles")
    if references is None or plan_files is None:
        return []
    if not isinstance(references, dict) or not isinstance(plan_files, dict):
        return []

    issues = []
    expected_pairs = (
        ("rollbackPlanRef", "rollbackPlan", "rollback"),
        ("conciliationScriptRef", "conciliationScript", "conciliacao"),
        ("deltaDataPolicyRef", "deltaDataPolicy", "politica de dados delta"),
    )
    for reference_key, plan_key, description in expected_pairs:
        reference_value = str(references.get(reference_key) or "").strip()
        plan_value = str(plan_files.get(plan_key) or "").strip()
        if reference_value and plan_value and reference_value != plan_value:
            issues.append(
                f"{label} arquivo de plano de {description} diverge das referencias"
            )
    return issues


def _validar_decisao_sem_bloqueios(decision, label, decision_label):
    issues = []
    step = decision.get("step")
    if step not in (None, "PM-06"):
        issues.append(f"{label} decisao de {decision_label} step invalido")
    blocked_by = decision.get("blockedBy")
    if blocked_by in (None, []):
        return issues
    if not isinstance(blocked_by, list):
        issues.append(f"{label} decisao de {decision_label} blockedBy invalido")
        return issues
    issues.extend(
        f"{label} decisao de {decision_label} contem bloqueio: {blocker}"
        for blocker in blocked_by
    )
    return issues


def _validar_referencia(value, label):
    return [] if str(value or "").strip() else [f"{label} nao informado"]


def _validar_flag(value, label):
    return [] if bool(value) else [f"{label} nao confirmado"]


def _validar_revisoes_finais(references):
    issues = []
    if not references.get("semanticReview"):
        issues.append("revisao-semantica nao confirmada")
    if not references.get("technicalReview"):
        issues.append("revisao-tecnica nao confirmada")
    if not references.get("extraReview"):
        issues.append("revisao-extra nao confirmada")
    return issues


def _validar_arquivos_saida(output_files, *, exigir=False, input_files=None):
    input_files = input_files or {}
    issues = []
    json_path = output_files.get("json") or ""
    record_path = output_files.get("record") or ""
    if exigir and not json_path:
        issues.append("arquivo JSON de evidencia PM-06 nao informado")
    if exigir and not record_path:
        issues.append("registro markdown de evidencia PM-06 nao informado")
    if json_path:
        issues.extend(
            _validar_caminho_saida(
                json_path,
                "arquivo JSON de evidencia PM-06",
            )
        )
        issues.extend(
            _validar_extensao_saida(
                json_path,
                "arquivo JSON de evidencia PM-06",
                {".json"},
            )
        )
    if record_path:
        issues.extend(
            _validar_caminho_saida(
                record_path,
                "registro markdown de evidencia PM-06",
            )
        )
        issues.extend(
            _validar_extensao_saida(
                record_path,
                "registro markdown de evidencia PM-06",
                {".md", ".markdown"},
            )
        )
    if json_path and record_path and _mesmo_caminho_saida(json_path, record_path):
        issues.append(
            "arquivo JSON e registro markdown de evidencia PM-06 apontam para o mesmo caminho"
        )
    for key, input_path in input_files.items():
        if not input_path:
            continue
        if json_path and _mesmo_caminho_saida(json_path, input_path):
            issues.append(
                f"arquivo JSON de evidencia PM-06 sobrescreve evidencia de entrada: {key}"
            )
        if record_path and _mesmo_caminho_saida(record_path, input_path):
            issues.append(
                f"registro markdown de evidencia PM-06 sobrescreve evidencia de entrada: {key}"
            )
    return issues


def _mesmo_caminho_saida(json_path, record_path):
    return _normalizar_caminho_saida(json_path) == _normalizar_caminho_saida(record_path)


def _normalizar_caminho_saida(value):
    path = Path(str(value)).expanduser()
    try:
        return path.resolve(strict=False)
    except OSError:
        return path


def _validar_caminho_saida(value, label):
    path = Path(str(value)).expanduser()
    if path.exists() and path.is_dir():
        return [f"{label} aponta para diretorio"]
    if path.parent.exists() and not path.parent.is_dir():
        return [f"{label} possui diretorio pai invalido"]
    return []


def _validar_extensao_saida(value, label, extensoes_validas):
    suffix = Path(str(value)).suffix.lower()
    if suffix in extensoes_validas:
        return []
    expected = " ou ".join(sorted(extensoes_validas))
    return [f"{label} deve usar extensao {expected}"]


def _caminho_saida_salvavel(value, extensoes_validas):
    if not value:
        return False
    return not (
        _validar_caminho_saida(value, "arquivo de evidencia PM-06")
        or _validar_extensao_saida(
            value,
            "arquivo de evidencia PM-06",
            extensoes_validas,
        )
    )


def _check(key, label, issues):
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


def _montar_decisao_migracao_limpeza(ready, issues):
    return {
        "status": "approved" if ready else "blocked",
        "step": "PM-06",
        "mayCreateCleanupMigrations": bool(ready),
        "mayApplyCleanupMigrations": False,
        "applyPolicy": (
            "Aplicar migration de limpeza exige revisao dos arquivos gerados, "
            "janela operacional propria, backup vigente e novo smoke pos-migration."
        ),
        "blockedBy": issues,
    }


def _salvar_resultado(resultado):
    if not _arquivos_saida_validos(resultado):
        return

    output_files = resultado.get("outputEvidenceFiles") or {}
    json_path = output_files.get("json")
    record_path = output_files.get("record")
    if json_path and record_path and _mesmo_caminho_saida(json_path, record_path):
        return
    if _caminho_saida_salvavel(json_path, {".json"}):
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if _caminho_saida_salvavel(record_path, {".md", ".markdown"}):
        path = Path(record_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resultado["executionRecord"]["markdown"], encoding="utf-8")


def _arquivos_saida_validos(resultado):
    for check in resultado.get("checks") or []:
        if check.get("key") == "outputEvidenceFiles":
            return check.get("ok") is True
    return True


def _registro_prontidao_migracao_limpeza_pm06(resultado):
    decision = resultado["cleanupMigrationDecision"]
    frontend_policy = resultado.get("frontendCanonicalValidationPolicy") or {}
    lines = [
        "### Registro PM-06 - prontidao de migration de limpeza",
        "",
        f"Data/hora da validacao: {resultado['generatedAt']}",
        f"ready/issues: ready={resultado['ready']}; issues={len(resultado['issues'])}",
        (
            "Checks: "
            f"ok={resultado['checksSummary']['okCount']}; "
            f"pendentes={resultado['checksSummary']['pendingCount']}; "
            f"total={resultado['checksSummary']['total']}"
        ),
        (
            "Decisao: "
            f"status={decision['status']}; "
            f"mayCreateCleanupMigrations={decision['mayCreateCleanupMigrations']}; "
            f"mayApplyCleanupMigrations={decision['mayApplyCleanupMigrations']}"
        ),
        (
            "Politica frontend canonico: "
            f"required={frontend_policy.get('required') is True}; "
            f"acceptedMarkers={','.join(frontend_policy.get('acceptedMarkers') or []) or '-'}; "
            f"aliasRemovalVersion={frontend_policy.get('aliasRemovalVersion') or '-'}"
        ),
        "Detalhe checks: "
        + "; ".join(
            f"{check['key']}={'ok' if check['ok'] else 'pendente'}"
            for check in resultado["checks"]
        ),
        "Pendencias: "
        + ("; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"),
        "Arquivos salvos: "
        f"json={resultado.get('outputEvidenceFiles', {}).get('json') or '-'}; "
        f"registro={resultado.get('outputEvidenceFiles', {}).get('record') or '-'}",
    ]
    return "\n".join(lines)


def _formatar_primeira_issue(resultado):
    if resultado.get("issues"):
        return f"migration de limpeza PM-06 nao aprovada: {resultado['issues'][0]}"
    return "migration de limpeza PM-06 nao aprovada"
