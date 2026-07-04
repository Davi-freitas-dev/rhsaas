import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


PM05_STEP = "PM-05.1"
DEFAULT_EVIDENCE_FILENAMES = {
    "canonicalSync": "pm05-sync-canonica.json",
    "canonicalParity": "pm05-paridade-canonica.json",
    "operationalValidation": "pm05-validacao-operacao-obrigacoes.json",
    "writeReadiness": "pm05-prontidao-escrita-canonica.json",
    "totalsAudit": "pm05-auditoria-totais-negocio.json",
    "deployPreflight": "pm05-preflight-deploy-financeiro.json",
}
DEFAULT_OUTPUT_JSON = "pm05-validacao-baseline.json"
DEFAULT_OUTPUT_RECORD = "pm05-validacao-baseline.md"


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, o pacote de evidencias PM-05.1 para "
        "baseline de leitura canonica."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help="Diretorio com os JSONs padronizados de PM-05.1.",
        )
        parser.add_argument("--sync-json", default="")
        parser.add_argument("--paridade-json", default="")
        parser.add_argument("--validacao-operacao-json", default="")
        parser.add_argument("--prontidao-json", default="")
        parser.add_argument("--auditoria-totais-json", default="")
        parser.add_argument("--preflight-json", default="")
        parser.add_argument("--salvar-json", "--save-json", default="")
        parser.add_argument("--salvar-registro", "--save-record", default="")
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help="Reprova se algum arquivo obrigatorio de evidencia PM-05 faltar.",
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
            help="Retorna erro quando o baseline PM-05.1 nao estiver aprovado.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        payloads, load_checks = _carregar_payloads_evidencia(evidence_files)
        resultado = validar_baseline_pm05(payloads, evidence_files, load_checks)
        resultado["outputEvidenceFiles"] = _normalizar_arquivos_saida(options)
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_baseline_pm05(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["exigir_arquivos_evidencia"] and load_checks["missing"]:
            raise CommandError(
                "evidencias PM-05 obrigatorias ausentes: "
                + ", ".join(load_checks["missing"])
            )

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao baseline PM-05.1 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_baseline_pm05(payloads, evidence_files, load_checks=None):
    checks = []
    load_checks = load_checks or {"byKey": {}, "missing": []}
    loaders = load_checks.get("byKey") or {}

    checks.append(
        _montar_check(
            "canonicalSync",
            "Sincronizacao canonica",
            evidence_files,
            loaders,
            _validar_sync_canonica(payloads.get("canonicalSync")),
        )
    )
    checks.append(
        _montar_check(
            "canonicalParity",
            "Paridade canonica",
            evidence_files,
            loaders,
            _validar_paridade_canonica(payloads.get("canonicalParity")),
        )
    )
    checks.append(
        _montar_check(
            "operationalValidation",
            "Validacao operacional",
            evidence_files,
            loaders,
            _validar_operacao(payloads.get("operationalValidation")),
        )
    )
    checks.append(
        _montar_check(
            "writeReadiness",
            "Prontidao de escrita",
            evidence_files,
            loaders,
            _validar_prontidao(payloads.get("writeReadiness")),
        )
    )
    checks.append(
        _montar_check(
            "totalsAudit",
            "Auditoria de totais",
            evidence_files,
            loaders,
            _validar_auditoria_totais(payloads.get("totalsAudit")),
        )
    )
    checks.append(
        _montar_check(
            "deployPreflight",
            "Pre-flight financeiro",
            evidence_files,
            loaders,
            _validar_preflight(payloads.get("deployPreflight")),
        )
    )

    issues = [
        issue
        for check in checks
        for issue in check["issues"]
    ]
    ready = all(check["ok"] for check in checks)
    pending = [check["key"] for check in checks if not check["ok"]]
    return {
        "source": "canonical_read_baseline",
        "step": PM05_STEP,
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
        "evidenceFiles": evidence_files,
        "generatedAt": timezone.now().isoformat(),
        "recommendedCommands": {
            "rerunBaselineValidation": (
                "python manage.py validar_baseline_pm05 "
                "--diretorio-evidencias=<diretorio-evidencias-pm05> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        },
    }


def _montar_check(key, label, evidence_files, loaders, validation_issues):
    load_issues = (loaders.get(key) or {}).get("issues") or []
    issues = load_issues + validation_issues
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "path": evidence_files.get(key) or "",
        "issues": issues,
    }


def _validar_sync_canonica(payload):
    if not isinstance(payload, dict):
        return ["payload de sincronizacao canonica ausente ou invalido"]
    issues = []
    if payload.get("aplicar") is not True:
        issues.append("sincronizacao canonica deve ter aplicar=True")
    return issues


def _validar_paridade_canonica(payload):
    if not isinstance(payload, dict):
        return ["payload de paridade canonica ausente ou invalido"]
    issues = []
    if payload.get("consistent") is not True:
        issues.append("paridade canonica deve ter consistent=True")
    if payload.get("issues"):
        issues.append("paridade canonica contem issues")
    for group_key in ("obrigacoes", "baixas", "alocacoes"):
        group = payload.get(group_key) or {}
        for field in ("missing", "extra", "divergent"):
            if _as_int(group.get(field)) != 0:
                issues.append(f"{group_key}.{field} deve ser 0")
        if group_key == "alocacoes":
            for field in ("semBaixa", "semObrigacao"):
                if _as_int(group.get(field)) != 0:
                    issues.append(f"{group_key}.{field} deve ser 0")
    return issues


def _validar_operacao(payload):
    if not isinstance(payload, dict):
        return ["payload de validacao operacional ausente ou invalido"]
    issues = []
    if payload.get("ready") is not True:
        issues.append("validacao operacional deve ter ready=True")
    if payload.get("issues"):
        issues.append("validacao operacional contem issues")
    modeling = payload.get("canonicalModeling") or {}
    if modeling.get("consistent") is not True:
        issues.append("canonicalModeling.consistent deve ser True")
    write_readiness = payload.get("canonicalWriteReadiness") or {}
    if write_readiness.get("ready") is not True:
        issues.append("canonicalWriteReadiness.ready deve ser True")
    editable = payload.get("editableValuesIntegrity") or {}
    if editable.get("checked") and editable.get("consistent") is not True:
        issues.append("editableValuesIntegrity.consistent deve ser True")
    return issues


def _validar_prontidao(payload):
    if not isinstance(payload, dict):
        return ["payload de prontidao ausente ou invalido"]
    issues = []
    if payload.get("ready") is not True:
        issues.append("prontidao de escrita deve ter ready=True")
    if payload.get("inconsistencies"):
        issues.append("prontidao de escrita contem inconsistencias")
    if payload.get("invalidFeatureFlagSources"):
        issues.append("feature flag contem origens invalidas")
    return issues


def _validar_auditoria_totais(payload):
    if not isinstance(payload, dict):
        return ["payload de auditoria de totais ausente ou invalido"]
    issues = []
    if payload.get("issues"):
        issues.append("auditoria de totais contem issues")
    context = payload.get("evidenceContext") or {}
    if context.get("phase") != "PM-05":
        issues.append("evidenceContext.phase deve ser PM-05")
    if context.get("filePrefix") != "pm05":
        issues.append("evidenceContext.filePrefix deve ser pm05")
    obligations = payload.get("obligations") or {}
    read_model = obligations.get("readModelStatus") or {}
    if read_model.get("dataSourceActual") != "canonical":
        issues.append("obligations.readModelStatus.dataSourceActual deve ser canonical")
    if read_model.get("canonicalReady") is not True:
        issues.append("obligations.readModelStatus.canonicalReady deve ser True")
    if _as_int(obligations.get("divergentCount")) != 0:
        issues.append("obligations.divergentCount deve ser 0")
    if not _is_zero_money(obligations.get("realizedAmountDifference")):
        issues.append("obligations.realizedAmountDifference deve ser 0.00")
    editable = payload.get("editableValuesIntegrity") or {}
    if editable.get("checked") and editable.get("consistent") is not True:
        issues.append("editableValuesIntegrity.consistent deve ser True")
    record = ((payload.get("executionRecord") or {}).get("markdown") or "")
    if record and "Registro PM-05 - auditoria de totais de negocio" not in record:
        issues.append("executionRecord.markdown deve identificar Registro PM-05")
    return issues


def _validar_preflight(payload):
    if not isinstance(payload, dict):
        return ["payload de pre-flight financeiro ausente ou invalido"]
    issues = []
    if payload.get("ready") is not True:
        issues.append("pre-flight financeiro deve ter ready=True")
    if payload.get("issues"):
        issues.append("pre-flight financeiro contem issues")
    system_check = payload.get("systemCheck") or {}
    if system_check and system_check.get("ok") is not True:
        issues.append("systemCheck.ok deve ser True")
    ledger = payload.get("financialLedgerIntegrity") or {}
    if ledger and ledger.get("consistent") is not True:
        issues.append("financialLedgerIntegrity.consistent deve ser True")
    totals = payload.get("businessTotalsAudit") or {}
    obligations = totals.get("obligations") or {}
    read_model = obligations.get("readModelStatus") or {}
    if read_model and read_model.get("dataSourceActual") != "canonical":
        issues.append(
            "businessTotalsAudit.obligations.readModelStatus.dataSourceActual "
            "deve ser canonical"
        )
    return issues


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    base_path = Path(directory).expanduser() if directory else None

    def default_path(key, option_name):
        explicit = options.get(option_name) or ""
        if explicit or not base_path:
            return explicit
        return str(base_path / DEFAULT_EVIDENCE_FILENAMES[key])

    return {
        "directory": directory,
        "canonicalSync": default_path("canonicalSync", "sync_json"),
        "canonicalParity": default_path("canonicalParity", "paridade_json"),
        "operationalValidation": default_path(
            "operationalValidation",
            "validacao_operacao_json",
        ),
        "writeReadiness": default_path("writeReadiness", "prontidao_json"),
        "totalsAudit": default_path("totalsAudit", "auditoria_totais_json"),
        "deployPreflight": default_path("deployPreflight", "preflight_json"),
    }


def _normalizar_arquivos_saida(options):
    directory = options.get("diretorio_evidencias") or ""
    base_path = Path(directory).expanduser() if directory else None
    save_json = options.get("salvar_json") or ""
    save_record = options.get("salvar_registro") or ""
    if base_path:
        if not save_json:
            save_json = str(base_path / DEFAULT_OUTPUT_JSON)
        if not save_record:
            save_record = str(base_path / DEFAULT_OUTPUT_RECORD)
    return {
        "json": save_json,
        "record": save_record,
    }


def _carregar_payloads_evidencia(evidence_files):
    payloads = {}
    by_key = {}
    missing = []
    for key in DEFAULT_EVIDENCE_FILENAMES:
        path = evidence_files.get(key) or ""
        payload, issues = _carregar_json(path)
        payloads[key] = payload
        by_key[key] = {"path": path, "issues": issues}
        if not path or any(issue.startswith("arquivo ausente") for issue in issues):
            missing.append(key)
    return payloads, {"byKey": by_key, "missing": missing}


def _carregar_json(path):
    if not path:
        return None, ["caminho de evidencia nao informado"]
    target = Path(path).expanduser()
    if not target.exists():
        return None, [f"arquivo ausente: {path}"]
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"JSON invalido: {exc}"]
    if not isinstance(payload, dict):
        return None, ["JSON deve ser um objeto"]
    return payload, []


def _salvar_resultado(resultado):
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


def _registro_baseline_pm05(resultado):
    summary = resultado["checksSummary"]
    checks = "; ".join(
        f"{check['key']}={'ok' if check['ok'] else 'pendente'}"
        for check in resultado["checks"]
    )
    return "\n".join(
        [
            "### Registro PM-05.1 - validacao baseline de leitura canonica",
            "",
            f"Data/hora da validacao: {resultado['generatedAt']}",
            f"ready/issues: ready={resultado['ready']}; issues={len(resultado['issues'])}",
            (
                "Checks: "
                f"ok={summary['okCount']}; "
                f"pendentes={summary['pendingCount']}; "
                f"total={summary['total']}"
            ),
            f"Detalhe checks: {checks}",
            (
                "Evidencias: "
                + "; ".join(
                    f"{key}={value or '-'}"
                    for key, value in resultado["evidenceFiles"].items()
                    if key != "directory"
                )
            ),
            (
                "Arquivos salvos: "
                f"json={resultado['outputEvidenceFiles'].get('json') or '-'}; "
                f"registro={resultado['outputEvidenceFiles'].get('record') or '-'}"
            ),
        ]
    )


def _formatar_primeira_issue(resultado):
    if not resultado.get("issues"):
        return "baseline PM-05.1 nao aprovado"
    return f"baseline PM-05.1 nao aprovado: {resultado['issues'][0]}"


def _as_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return -1


def _is_zero_money(value):
    try:
        return float(value or 0) == 0.0
    except (TypeError, ValueError):
        return False
