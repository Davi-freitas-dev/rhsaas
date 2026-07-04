import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date

from caixa.constants_nomenclatura import (
    VERSAO_REMOCAO_ALIASES_LEGADOS,
    montar_metadados_nomenclatura_financeira,
)


DEFAULT_OUTPUT_JSON = "pm06-fechamento.json"
DEFAULT_OUTPUT_RECORD = "pm06-fechamento.md"
DEFAULT_PM06_PREPARATION_JSON = "pm06-validacao-backup-rollback.json"
DEFAULT_REDIRECTS_JSON = "pm06-redirect-next-legado.json"
DEFAULT_LEGACY_FREEZE_JSON = "pm06-prontidao-congelamento-legado.json"
DEFAULT_ROLLBACK_CONCILIATION_JSON = "pm06-rollback-conciliacao-janela.json"
FRONTEND_CANONICAL_VALIDATION_MARKERS = (
    "verify:publish",
    "verify-publish",
    "check:financial-canonical",
    "check-financial-canonical",
    "financial-canonical",
)


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, se a PM-06 pode liberar a PM-07. "
        "O comando nao altera dados, flags, rotas, aliases, migrations ou templates."
    )

    def add_arguments(self, parser):
        parser.add_argument("--pm06-preparacao-json", default="")
        parser.add_argument("--redirects-json", default="")
        parser.add_argument("--congelamento-legado-json", default="")
        parser.add_argument("--rollback-conciliacao-json", default="")
        parser.add_argument("--frontend-validacao-ref", default="")
        parser.add_argument("--aceite-operacional-ref", default="")
        parser.add_argument(
            "--itens-consolidacao-resolvidos",
            action="store_true",
            help=(
                "Confirma que consolidacao, politica financeiro-v3, "
                "compatibilidade e limpeza foram concluidas ou formalmente "
                "marcadas como nao aplicaveis."
            ),
        )
        parser.add_argument(
            "--backup-rollback-registrados",
            action="store_true",
            help="Confirma backup, tag, rollback e conciliacao registrados no plano.",
        )
        parser.add_argument("--revisao-semantica", action="store_true")
        parser.add_argument("--revisao-tecnica", action="store_true")
        parser.add_argument("--revisao-extra", action="store_true")
        parser.add_argument(
            "--evidencias-atualizadas",
            action="store_true",
            help="Confirma evidencias, validacoes e registro de execucao atualizados.",
        )
        parser.add_argument(
            "--liberar-pm07",
            action="store_true",
            help="Confirmacao explicita de que a proxima PM pode ser PM-07.",
        )
        parser.add_argument("--diretorio-evidencias", default="")
        parser.add_argument("--salvar-json", "--save-json", default="")
        parser.add_argument("--salvar-registro", "--save-record", default="")
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            action="store_true",
            help="Exige caminhos para salvar JSON e registro markdown do gate.",
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
            help="Retorna erro quando o fechamento da PM-06 nao estiver aprovado.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        output_files = _normalizar_arquivos_saida(options)
        payloads, load_checks = _carregar_payloads(evidence_files)
        resultado = validar_fechamento_pm06(
            _normalizar_referencias(options),
            payloads=payloads,
            load_checks=load_checks,
            output_files=output_files,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_fechamento_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao fechamento PM-06 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        decision = resultado["closureDecision"]
        self.stdout.write(
            "closureDecision="
            f"{decision['status']}; "
            f"mayAdvanceSequence={decision['mayAdvanceSequence']}; "
            f"nextStep={decision['nextStep']}"
        )
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_fechamento_pm06(references, *, payloads=None, load_checks=None, output_files=None):
    payloads = payloads or {}
    load_checks = load_checks or {"byKey": {}}
    loaders = load_checks.get("byKey") or {}
    output_files = output_files or {}
    requirements = references.get("requirements") or {}
    nomenclature = montar_metadados_nomenclatura_financeira()
    financeiro_v3_policy = _resumir_politica_financeiro_v3(nomenclature)
    frontend_validation_policy = _resumir_politica_validacao_frontend()

    checks = [
        _check(
            "inputEvidenceFiles",
            "Arquivos de evidencia de entrada",
            _validar_evidencias_entrada_distintas(
                evidence_files_from_references(references),
            ),
        ),
        _check(
            "pm06Preparation",
            "Gate PM-06.2 backup/tag/rollback",
            _validar_payload_carregado(
                payloads.get("pm06Preparation"),
                loaders.get("pm06Preparation"),
                "pm06-preparacao-json",
                _validar_payload_preparacao_pm06,
            ),
        ),
        _check(
            "redirects",
            "Redirects/readonly PM-06",
            _validar_payload_carregado(
                payloads.get("redirects"),
                loaders.get("redirects"),
                "redirects-json",
                _validar_payload_redirects,
            ),
        ),
        _check(
            "frontendValidation",
            "Validacao frontend publicada",
            _validar_frontend_validacao_ref(
                references.get("frontendValidationRef")
            ),
        ),
        _check(
            "legacyFreezeReadiness",
            "Prontidao de congelamento legado",
            _validar_payload_carregado(
                payloads.get("legacyFreeze"),
                loaders.get("legacyFreeze"),
                "congelamento-legado-json",
                _validar_payload_congelamento_legado,
            ),
        ),
        _check(
            "rollbackConciliation",
            "Rollback/conciliacao da janela",
            _validar_payload_carregado(
                payloads.get("rollbackConciliation"),
                loaders.get("rollbackConciliation"),
                "rollback-conciliacao-json",
                _validar_payload_rollback_conciliacao,
            ),
        ),
        _check(
            "operationalAcceptance",
            "Aceite operacional",
            _validar_referencia(references.get("operationalAcceptanceRef"), "aceite-operacional-ref"),
        ),
        _check(
            "consolidationItems",
            "Itens de consolidacao/compatibilidade/limpeza",
            _validar_flag(
                references.get("consolidationItemsResolved"),
                "itens-consolidacao-resolvidos",
            ),
        ),
        _check(
            "backupRollbackRecorded",
            "Backup, rollback e conciliacao registrados",
            _validar_flag(
                references.get("backupRollbackRecorded"),
                "backup-rollback-registrados",
            ),
        ),
        _check(
            "finalReviews",
            "Revisoes finais PM-06",
            _validar_revisoes_finais(references),
        ),
        _check(
            "updatedEvidence",
            "Evidencias e registro de execucao atualizados",
            _validar_flag(references.get("updatedEvidence"), "evidencias-atualizadas"),
        ),
        _check(
            "financeiroV3Policy",
            "Politica financeiro-v3 preservada",
            _validar_politica_financeiro_v3(financeiro_v3_policy),
        ),
        _check(
            "pm07Release",
            "Liberacao explicita da PM-07",
            _validar_flag(references.get("releasePm07"), "liberar-pm07"),
        ),
        _check(
            "outputEvidenceFiles",
            "Arquivos de evidencia do gate PM-06",
            _validar_arquivos_saida(
                output_files,
                exigir=requirements.get("outputEvidenceFiles"),
                input_files=evidence_files_from_references(references),
            ),
        ),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]
    generated_at = timezone.now().isoformat()
    closure_decision = _montar_decisao(ready, issues)

    return {
        "source": "pm06_closure_validation",
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
        "closureDecision": closure_decision,
        "closureNextAction": _montar_proxima_acao(closure_decision),
        "references": references,
        "financeiroV3Policy": financeiro_v3_policy,
        "frontendCanonicalValidationPolicy": frontend_validation_policy,
        "evidenceFiles": evidence_files_from_references(references),
        "generatedAt": generated_at,
        "recommendedCommands": {
            "pm06Preparation": (
                "python manage.py validar_preparacao_pm06 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--backend-ref=<tag-ou-commit-backend> "
                "--frontend-ref=<commit-ou-deploy-frontend> "
                "--backup-ref=<arquivo-backup-json> "
                "--rollback-plan-ref=<arquivo-rollback-md> "
                "--conciliation-plan-ref=<arquivo-conciliacao-md> "
                "--exigir-backend-ref-git --exigir-planos-arquivo "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "redirects": (
                "python manage.py validar_redirects_next_legado "
                "--diretorio-evidencias=<diretorio-evidencias-pm06-redirects> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "frontendValidation": (
                "npx --yes pnpm@10.33.4 run verify:publish "
                "# inclui check:financial-canonical"
            ),
            "legacyFreezeReadiness": (
                "python manage.py validar_prontidao_congelamento_pm06 "
                "--frontend-validacao-ref=<verify-publish-ou-check-financial-canonical-ref> "
                "--aceite-operacional-ref=<aceite-operacional> "
                "--backup-rollback-ref=<pm06-backup-rollback-ref> "
                "--janela-congelamento-ref=<janela-homologada> "
                "--revisao-semantica --revisao-tecnica --revisao-extra "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "rollbackConciliation": (
                "python manage.py validar_rollback_conciliacao_pm06 "
                "--backup-ref=<backup-ref> "
                "--codigo-janela-ref=<janela-pm06> "
                "--janela-inicio=<YYYY-MM-DD> "
                "--janela-fim=<YYYY-MM-DD> "
                "--rollback-plan-ref=<arquivo-rollback-md> "
                "--conciliation-script-ref=<arquivo-ou-script-conciliacao> "
                "--delta-data-policy-ref=<politica-dados-delta-md> "
                "--owner-ref=<responsavel> "
                "--homologacao-ref=<homologacao-sem-divergencias> "
                "--aceite-operacional-ref=<aceite-operacional> "
                "--revisao-semantica --revisao-tecnica --revisao-extra "
                "--exigir-arquivos-plano "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "manualReentryExport": (
                "python manage.py exportar_recadastro_manual_pm06 "
                "--diretorio-saida=<diretorio-evidencias-pm06>"
            ),
            "manualReentryValidation": (
                "python manage.py validar_recadastro_manual_pm06 "
                "--recadastro-json=<pm06-recadastro-manual.json> "
                "--comparar-base-atual "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "cleanupMigrationReadiness": (
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
            "rerunPm06Closure": (
                "python manage.py validar_fechamento_pm06 "
                "--pm06-preparacao-json=<pm06-validacao-backup-rollback.json> "
                "--redirects-json=<pm06-redirect-next-legado.json> "
                "--congelamento-legado-json=<pm06-prontidao-congelamento-legado.json> "
                "--rollback-conciliacao-json=<pm06-rollback-conciliacao-janela.json> "
                "--frontend-validacao-ref=<verify-publish-ref> "
                "--aceite-operacional-ref=<aceite-operacional> "
                "--itens-consolidacao-resolvidos "
                "--backup-rollback-registrados "
                "--revisao-semantica --revisao-tecnica --revisao-extra "
                "--evidencias-atualizadas --liberar-pm07 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        },
    }


def _normalizar_referencias(options):
    evidence_files = _normalizar_arquivos_evidencia(options)
    return {
        "pm06PreparationJson": evidence_files["pm06Preparation"],
        "redirectsJson": evidence_files["redirects"],
        "legacyFreezeJson": evidence_files["legacyFreeze"],
        "rollbackConciliationJson": evidence_files["rollbackConciliation"],
        "frontendValidationRef": options.get("frontend_validacao_ref") or "",
        "operationalAcceptanceRef": options.get("aceite_operacional_ref") or "",
        "consolidationItemsResolved": bool(options.get("itens_consolidacao_resolvidos")),
        "backupRollbackRecorded": bool(options.get("backup_rollback_registrados")),
        "semanticReview": bool(options.get("revisao_semantica")),
        "technicalReview": bool(options.get("revisao_tecnica")),
        "extraReview": bool(options.get("revisao_extra")),
        "updatedEvidence": bool(options.get("evidencias_atualizadas")),
        "releasePm07": bool(options.get("liberar_pm07")),
        "requirements": {
            "outputEvidenceFiles": bool(options.get("exigir_arquivos_evidencia")),
        },
    }


def evidence_files_from_references(references):
    return {
        "pm06Preparation": references.get("pm06PreparationJson") or "",
        "redirects": references.get("redirectsJson") or "",
        "legacyFreeze": references.get("legacyFreezeJson") or "",
        "rollbackConciliation": references.get("rollbackConciliationJson") or "",
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


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    base = Path(directory) if directory else None
    default_pm06_preparation = str(base / DEFAULT_PM06_PREPARATION_JSON) if base else ""
    default_redirects = str(base / DEFAULT_REDIRECTS_JSON) if base else ""
    default_legacy_freeze = str(base / DEFAULT_LEGACY_FREEZE_JSON) if base else ""
    default_rollback_conciliation = str(base / DEFAULT_ROLLBACK_CONCILIATION_JSON) if base else ""

    return {
        "pm06Preparation": options.get("pm06_preparacao_json") or default_pm06_preparation,
        "redirects": options.get("redirects_json") or default_redirects,
        "legacyFreeze": options.get("congelamento_legado_json") or default_legacy_freeze,
        "rollbackConciliation": (
            options.get("rollback_conciliacao_json") or default_rollback_conciliation
        ),
    }


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


def _carregar_payloads(evidence_files):
    payloads = {}
    checks = {"byKey": {}}
    labels = {
        "pm06Preparation": "pm06-preparacao-json",
        "redirects": "redirects-json",
        "legacyFreeze": "congelamento-legado-json",
        "rollbackConciliation": "rollback-conciliacao-json",
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


def _validar_payload_carregado(payload, loader, label, validar_identidade=None):
    load_issues = (loader or {}).get("issues") or []
    if load_issues:
        return load_issues
    issues = _validar_payload_ready(payload, label)
    if issues:
        return issues
    if validar_identidade:
        return validar_identidade(payload, label)
    return []


def _validar_payload_preparacao_pm06(payload, label):
    issues = []
    if payload.get("source") != "pm06_backup_rollback_preparation":
        issues.append(f"{label} nao e evidencia de preparacao PM-06.2")
    if payload.get("step") != "PM-06.2":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")
    return issues


def _validar_payload_redirects(payload, label):
    issues = []
    if payload.get("source") not in {"settings", "argument"}:
        issues.append(f"{label} origem invalida")
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        issues.append(f"{label} sem lista de superficies")
    elif not surfaces:
        issues.append(f"{label} sem superficies migradas")
    else:
        for surface in surfaces:
            if not isinstance(surface, dict):
                issues.append(f"{label} superficie de redirect invalida")
                continue
            if not str(surface.get("surface") or "").strip():
                issues.append(f"{label} superficie de redirect sem chave")
    activation = payload.get("activation")
    if not isinstance(activation, dict):
        issues.append(f"{label} sem plano de ativacao/rollback")
    else:
        if activation.get("readyToActivate") not in (None, True):
            issues.append(f"{label} ativacao nao esta pronta")
        recommended_surfaces = activation.get("recommendedSurfacesValue")
        if recommended_surfaces is not None and not str(recommended_surfaces).strip():
            issues.append(f"{label} sem allowlist recomendada")
        recommended_environment = activation.get("recommendedEnvironment")
        if recommended_environment is not None:
            if not isinstance(recommended_environment, dict):
                issues.append(f"{label} ambiente de ativacao recomendado invalido")
            else:
                if not str(
                    recommended_environment.get("NEXT_FRONTEND_URL") or ""
                ).strip():
                    issues.append(f"{label} sem URL frontend recomendada")
                if (
                    recommended_environment.get(
                        "NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED"
                    )
                    != "True"
                ):
                    issues.append(f"{label} ativacao recomendada nao liga redirects")
                if not str(
                    recommended_environment.get(
                        "NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES"
                    )
                    or ""
                ).strip():
                    issues.append(f"{label} sem allowlist de ativacao recomendada")
        rollback = activation.get("rollbackEnvironment")
        if not isinstance(rollback, dict):
            issues.append(f"{label} sem ambiente de rollback")
        elif rollback.get("NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED") != "False":
            issues.append(f"{label} rollback nao desativa redirects")
    return issues


def _validar_payload_congelamento_legado(payload, label):
    issues = []
    if payload.get("source") != "pm06_legacy_freeze_readiness":
        issues.append(f"{label} nao e evidencia de prontidao de congelamento PM-06")
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


def _validar_frontend_validacao_ref(value):
    issues = _validar_referencia(value, "frontend-validacao-ref")
    if issues:
        return issues
    normalized = str(value or "").strip().lower()
    if any(marker in normalized for marker in FRONTEND_CANONICAL_VALIDATION_MARKERS):
        return []
    return [
        "frontend-validacao-ref nao comprova guardrail canonico do frontend"
    ]


def _validar_referencias_congelamento_legado(payload, label):
    references = payload.get("references")
    if references is None:
        return []
    if not isinstance(references, dict):
        return [f"{label} referencias de congelamento invalidas"]
    return [
        f"{label} {issue}"
        for issue in _validar_frontend_validacao_ref(
            references.get("frontendValidationRef")
        )
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


def _resumir_politica_financeiro_v3(nomenclature):
    policy = nomenclature.get("aliasRemovalPolicy") or {}
    pending_physical_fields = nomenclature.get("physicalFieldsPendingMigration") or []
    planned_physical_renames = nomenclature.get("plannedPhysicalRenames") or {}
    return {
        "currentVersion": nomenclature.get("version") or "",
        "removeOnlyInVersion": policy.get("removeOnlyInVersion") or "",
        "rule": policy.get("rule") or "",
        "pendingPhysicalFieldCount": len(pending_physical_fields),
        "pendingPhysicalFields": list(pending_physical_fields),
        "plannedPhysicalRenameCount": len(planned_physical_renames),
        "plannedPhysicalRenames": sorted(planned_physical_renames),
    }


def _validar_politica_financeiro_v3(policy):
    issues = []
    if policy.get("removeOnlyInVersion") != VERSAO_REMOCAO_ALIASES_LEGADOS:
        issues.append("politica financeiro-v3 sem versao de corte esperada")
    if policy.get("currentVersion") == policy.get("removeOnlyInVersion"):
        issues.append("contrato atual ja esta na versao de remocao de aliases")
    if not policy.get("rule"):
        issues.append("politica financeiro-v3 sem regra documentada")
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


def _montar_decisao(ready, issues):
    return {
        "status": "approved" if ready else "blocked",
        "step": "PM-06",
        "mayMarkCurrentStepDone": bool(ready),
        "mayAdvanceSequence": bool(ready),
        "mayStartNextStep": bool(ready),
        "nextStep": "PM-07",
        "blockedBy": issues,
    }


def _montar_proxima_acao(decision):
    if decision["status"] == "approved":
        return {
            "key": "advanceToPm07",
            "status": "ready",
            "label": "Registrar fechamento da PM-06 e iniciar PM-07",
            "nextStep": "PM-07",
            "mayAdvanceSequence": True,
            "mayStartNextStep": True,
        }

    first_blocker = (decision.get("blockedBy") or [""])[0]
    return {
        "key": "resolvePm06Blockers",
        "status": "blocked",
        "label": "Resolver bloqueios finais da PM-06",
        "detail": first_blocker,
        "nextStep": "PM-07",
        "mayAdvanceSequence": False,
        "mayStartNextStep": False,
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
        path.write_text(json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    if _caminho_saida_salvavel(record_path, {".md", ".markdown"}):
        path = Path(record_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resultado["executionRecord"]["markdown"], encoding="utf-8")


def _arquivos_saida_validos(resultado):
    for check in resultado.get("checks") or []:
        if check.get("key") == "outputEvidenceFiles":
            return check.get("ok") is True
    return True


def _registro_fechamento_pm06(resultado):
    decision = resultado["closureDecision"]
    frontend_policy = resultado.get("frontendCanonicalValidationPolicy") or {}
    lines = [
        "### Registro PM-06 - validacao de fechamento",
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
            f"mayAdvanceSequence={decision['mayAdvanceSequence']}; "
            f"nextStep={decision['nextStep']}"
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
        return f"fechamento PM-06 nao aprovado: {resultado['issues'][0]}"
    return "fechamento PM-06 nao aprovado"
