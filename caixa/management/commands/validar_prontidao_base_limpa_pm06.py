import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


DEFAULT_OUTPUT_JSON = "pm06-prontidao-base-limpa-manual.json"
DEFAULT_OUTPUT_RECORD = "pm06-prontidao-base-limpa-manual.md"
DEFAULT_PM06_PREPARATION_JSON = "pm06-validacao-backup-rollback.json"
DEFAULT_MANUAL_REENTRY_JSON = "pm06-validacao-recadastro-manual.json"
DEFAULT_ROLLBACK_CONCILIATION_JSON = "pm06-rollback-conciliacao-janela.json"


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, a prontidao PM-06 para base limpa com "
        "recadastro manual. Nao limpa dados, nao restaura backup e nao cria "
        "migrations."
    )

    def add_arguments(self, parser):
        parser.add_argument("--pm06-preparacao-json", default="")
        parser.add_argument("--recadastro-manual-json", default="")
        parser.add_argument("--rollback-conciliacao-json", default="")
        parser.add_argument("--relatorio-atual-ref", default="")
        parser.add_argument("--aceite-operacional-ref", default="")
        parser.add_argument("--revisao-semantica", action="store_true")
        parser.add_argument("--revisao-tecnica", action="store_true")
        parser.add_argument("--revisao-extra", action="store_true")
        parser.add_argument("--liberar-base-limpa-manual", action="store_true")
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
            help="Retorna erro quando a base limpa manual ainda estiver bloqueada.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        output_files = _normalizar_arquivos_saida(options)
        payloads, load_checks = _carregar_payloads(evidence_files)
        resultado = validar_prontidao_base_limpa_pm06(
            _normalizar_referencias(options),
            payloads=payloads,
            load_checks=load_checks,
            evidence_files=evidence_files,
            output_files=output_files,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_base_limpa_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao de base limpa manual PM-06 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        decision = resultado["cleanDatabaseManualDecision"]
        self.stdout.write(
            "cleanDatabaseManualDecision="
            f"{decision['status']}; "
            f"mayUseCleanDatabaseManualReentry={decision['mayUseCleanDatabaseManualReentry']}; "
            f"mayCleanProductionData={decision['mayCleanProductionData']}; "
            f"mayCreateCleanupMigrations={decision['mayCreateCleanupMigrations']}"
        )
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_prontidao_base_limpa_pm06(
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
            "pm06Preparation",
            "Preparacao PM-06 com backup/preflight",
            _validar_payload_carregado(
                payloads.get("pm06Preparation"),
                loaders.get("pm06Preparation"),
                "pm06-preparacao-json",
                _validar_payload_preparacao,
            ),
        ),
        _check(
            "manualReentry",
            "Recadastro manual comparado",
            _validar_payload_carregado(
                payloads.get("manualReentry"),
                loaders.get("manualReentry"),
                "recadastro-manual-json",
                _validar_payload_recadastro_manual,
            ),
        ),
        _check(
            "rollbackConciliation",
            "Rollback/conciliacao aprovado",
            _validar_payload_carregado(
                payloads.get("rollbackConciliation"),
                loaders.get("rollbackConciliation"),
                "rollback-conciliacao-json",
                _validar_payload_rollback_conciliacao,
            ),
        ),
        _check(
            "currentReport",
            "Relatorio atual preservado",
            _validar_referencia(references.get("currentReportRef"), "relatorio-atual-ref"),
        ),
        _check(
            "operationalAcceptance",
            "Aceite operacional",
            _validar_referencia(references.get("operationalAcceptanceRef"), "aceite-operacional-ref"),
        ),
        _check("finalReviews", "Revisoes finais", _validar_revisoes_finais(references)),
        _check(
            "explicitRelease",
            "Liberacao explicita de base limpa manual",
            _validar_flag(
                references.get("releaseCleanDatabaseManual"),
                "liberar-base-limpa-manual",
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
    decision = _montar_decisao_base_limpa(ready, issues)

    return {
        "source": "pm06_clean_database_manual_reentry_readiness",
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
        "cleanDatabaseManualDecision": decision,
        "references": references,
        "evidenceFiles": evidence_files,
        "generatedAt": timezone.now().isoformat(),
        "recommendedCommands": {
            "manualReentryExport": (
                "python manage.py exportar_recadastro_manual_pm06 "
                "--diretorio-saida=<diretorio-evidencias-pm06>"
            ),
            "manualReentryValidation": (
                "python manage.py validar_recadastro_manual_pm06 "
                "--recadastro-json=<pm06-recadastro-manual.json> "
                "--comparar-base-atual --diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "rerunCleanDatabaseReadiness": (
                "python manage.py validar_prontidao_base_limpa_pm06 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--relatorio-atual-ref=<relatorio-atual> "
                "--aceite-operacional-ref=<aceite-operacional> "
                "--revisao-semantica --revisao-tecnica --revisao-extra "
                "--liberar-base-limpa-manual "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        },
    }


def _normalizar_referencias(options):
    return {
        "currentReportRef": options.get("relatorio_atual_ref") or "",
        "operationalAcceptanceRef": options.get("aceite_operacional_ref") or "",
        "semanticReview": bool(options.get("revisao_semantica")),
        "technicalReview": bool(options.get("revisao_tecnica")),
        "extraReview": bool(options.get("revisao_extra")),
        "releaseCleanDatabaseManual": bool(options.get("liberar_base_limpa_manual")),
        "requirements": {
            "outputEvidenceFiles": bool(options.get("exigir_arquivos_evidencia")),
        },
    }


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    base = Path(directory) if directory else None
    return {
        "pm06Preparation": options.get("pm06_preparacao_json")
        or (str(base / DEFAULT_PM06_PREPARATION_JSON) if base else ""),
        "manualReentry": options.get("recadastro_manual_json")
        or (str(base / DEFAULT_MANUAL_REENTRY_JSON) if base else ""),
        "rollbackConciliation": options.get("rollback_conciliacao_json")
        or (str(base / DEFAULT_ROLLBACK_CONCILIATION_JSON) if base else ""),
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
        "manualReentry": "recadastro-manual-json",
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


def _validar_payload_carregado(payload, loader, label, validar_identidade):
    load_issues = (loader or {}).get("issues") or []
    if load_issues:
        return load_issues
    issues = _validar_payload_ready(payload, label)
    if issues:
        return issues
    return validar_identidade(payload, label)


def _validar_payload_ready(payload, label):
    if not isinstance(payload, dict):
        return [f"payload {label} ausente ou invalido"]
    issues = payload.get("issues")
    if not isinstance(issues, list):
        return [f"{label} sem lista de issues"]
    if issues:
        return [f"{label} contem pendencia: {issue}" for issue in issues]
    if payload.get("ready") is not True:
        return [f"{label} nao aprovado"]
    checks = payload.get("checks")
    if isinstance(checks, list):
        check_issues = []
        for check in checks:
            if not isinstance(check, dict):
                check_issues.append(f"{label} contem check invalido")
                continue
            check_key = check.get("key") or "sem-chave"
            if check.get("ok") is not True:
                check_issues.append(f"{label} contem check nao aprovado: {check_key}")
            if check.get("issues"):
                check_issues.extend(
                    f"{label} contem pendencia em check {check_key}: {issue}"
                    for issue in check.get("issues")
                )
        if check_issues:
            return check_issues
    return []


def _validar_payload_preparacao(payload, label):
    issues = []
    if payload.get("source") != "pm06_backup_rollback_preparation":
        issues.append(f"{label} nao e evidencia de preparacao PM-06")
    if payload.get("step") != "PM-06.2":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")
    backup = payload.get("backupEvidence")
    if not isinstance(backup, dict):
        issues.append(f"{label} sem backupEvidence")
    else:
        if backup.get("exists") is not True or backup.get("isFile") is not True:
            issues.append(f"{label} backup real nao confirmado")
        if backup.get("metadataExists") is not True:
            issues.append(f"{label} metadata do backup nao confirmada")
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
        issues.append(f"{label} recadastro manual nao aprovado")
    if decision.get("mayUseForManualReentry") is not True:
        issues.append(f"{label} nao libera recadastro manual")
    if decision.get("mayCleanData") is not False:
        issues.append(f"{label} nao preserva bloqueio de limpeza")
    if decision.get("mayRestoreAutomatically") is not False:
        issues.append(f"{label} nao preserva bloqueio de restauracao automatica")
    comparison = payload.get("currentDatabaseComparison")
    if not isinstance(comparison, dict):
        issues.append(f"{label} sem comparacao com base atual")
    elif comparison.get("compared") is not True:
        issues.append(f"{label} nao comparou pacote com base atual")
    elif comparison.get("differences"):
        issues.append(f"{label} possui divergencias com base atual")
    return issues


def _validar_payload_rollback_conciliacao(payload, label):
    issues = []
    if payload.get("source") != "pm06_rollback_conciliation_window":
        issues.append(f"{label} nao e evidencia de rollback/conciliacao PM-06")
    if payload.get("step") != "PM-06":
        issues.append(f"{label} step invalido")
    if payload.get("readOnly") is not True:
        issues.append(f"{label} sem readOnly=True")
    decision = payload.get("rollbackConciliationDecision")
    if not isinstance(decision, dict):
        issues.append(f"{label} decisao de rollback/conciliacao invalida")
        decision = {}
    if decision.get("status") != "approved":
        issues.append(f"{label} rollback/conciliacao nao aprovado")
    if decision.get("mayExecuteRollback") is not False:
        issues.append(f"{label} nao preserva bloqueio de rollback")
    if decision.get("mayExecuteConciliation") is not False:
        issues.append(f"{label} nao preserva bloqueio de conciliacao")
    return issues


def _validar_referencia(value, option_name):
    if not str(value or "").strip():
        return [f"{option_name} nao informado"]
    return []


def _validar_revisoes_finais(references):
    issues = []
    if references.get("semanticReview") is not True:
        issues.append("revisao-semantica nao confirmada")
    if references.get("technicalReview") is not True:
        issues.append("revisao-tecnica nao confirmada")
    if references.get("extraReview") is not True:
        issues.append("revisao-extra nao confirmada")
    return issues


def _validar_flag(value, option_name):
    return [] if value is True else [f"{option_name} nao informado"]


def _validar_evidencias_entrada_distintas(evidence_files):
    issues = []
    by_path = {}
    for key, value in (evidence_files or {}).items():
        if not value:
            continue
        if Path(str(value)).suffix.lower() != ".json":
            issues.append(f"evidencia de entrada PM-06 deve usar extensao .json: {key}")
        normalized = str(Path(value).resolve())
        previous_key = by_path.get(normalized)
        if previous_key:
            issues.append(
                "evidencias de entrada PM-06 usam o mesmo caminho: "
                f"{previous_key} e {key}"
            )
        else:
            by_path[normalized] = key
    return issues


def _validar_arquivos_saida(output_files, exigir=False, input_files=None):
    if not exigir:
        return []
    issues = []
    json_path = output_files.get("json") or ""
    record_path = output_files.get("record") or ""
    if not json_path:
        issues.append("salvar-json obrigatorio quando exigir-arquivos-evidencia")
    if not record_path:
        issues.append("salvar-registro obrigatorio quando exigir-arquivos-evidencia")
    if json_path and Path(json_path).suffix.lower() != ".json":
        issues.append("arquivo JSON de evidencia PM-06 deve usar extensao .json")
    if record_path and Path(record_path).suffix.lower() not in {".md", ".markdown"}:
        issues.append("registro de evidencia PM-06 deve usar extensao .md")
    if json_path and record_path and Path(json_path).resolve() == Path(record_path).resolve():
        issues.append("json e markdown de evidencia PM-06 nao podem usar o mesmo caminho")
    for key, input_path in (input_files or {}).items():
        if json_path and input_path and Path(json_path).resolve() == Path(input_path).resolve():
            issues.append(f"arquivo JSON de evidencia PM-06 sobrescreve evidencia de entrada: {key}")
        if record_path and input_path and Path(record_path).resolve() == Path(input_path).resolve():
            issues.append(f"registro de evidencia PM-06 sobrescreve evidencia de entrada: {key}")
    return issues


def _montar_decisao_base_limpa(ready, issues):
    return {
        "status": "approved" if ready else "blocked",
        "step": "PM-06",
        "mayUseCleanDatabaseManualReentry": bool(ready),
        "mayCleanProductionData": False,
        "mayRestoreAutomatically": False,
        "mayCreateCleanupMigrations": False,
        "serverActionRequired": bool(ready),
        "executionPolicy": (
            "Aprovado apenas como prontidao operacional. Limpeza real de dados "
            "em servidor exige confirmacao humana, backup vigente e recadastro "
            "manual conferido por relatorio antes/depois."
        ),
        "blockedBy": issues,
    }


def _salvar_resultado(resultado):
    if not _saida_aprovada(resultado):
        return
    output_files = resultado.get("outputEvidenceFiles") or {}
    json_path = output_files.get("json")
    record_path = output_files.get("record")
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if record_path:
        path = Path(record_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resultado["executionRecord"]["markdown"], encoding="utf-8")


def _saida_aprovada(resultado):
    for check in resultado.get("checks") or []:
        if check.get("key") == "outputEvidenceFiles":
            return check.get("ok") is True
    return True


def _registro_base_limpa_pm06(resultado):
    decision = resultado["cleanDatabaseManualDecision"]
    lines = [
        "### Registro PM-06 - prontidao para base limpa manual",
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
            f"mayUseCleanDatabaseManualReentry={decision['mayUseCleanDatabaseManualReentry']}; "
            f"mayCleanProductionData={decision['mayCleanProductionData']}; "
            f"mayCreateCleanupMigrations={decision['mayCreateCleanupMigrations']}"
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


def _check(key, label, issues):
    issues = [issue for issue in issues if issue]
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


def _formatar_primeira_issue(resultado):
    if resultado.get("issues"):
        return f"base limpa manual PM-06 nao aprovada: {resultado['issues'][0]}"
    return "base limpa manual PM-06 nao aprovada"
