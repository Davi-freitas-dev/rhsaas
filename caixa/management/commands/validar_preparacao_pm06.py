import hashlib
import json
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils import timezone


PM06_STEP = "PM-06.2"
DEFAULT_EVIDENCE_FILENAMES = {
    "totalsAudit": "pm06-auditoria-totais-negocio.json",
    "deployPreflight": "pm06-preflight-deploy-financeiro.json",
}
DEFAULT_OUTPUT_JSON = "pm06-validacao-backup-rollback.json"
DEFAULT_OUTPUT_RECORD = "pm06-validacao-backup-rollback.md"


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, a preparacao PM-06.2 de backup, tag, "
        "rollback e conciliacao antes de qualquer consolidacao fisica."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help="Diretorio PM-06 usado para carregar validacoes e salvar o gate.",
        )
        parser.add_argument("--backend-ref", default="")
        parser.add_argument(
            "--exigir-backend-ref-git",
            action="store_true",
            help="Exige que backend-ref exista como commit/tag no repositorio local.",
        )
        parser.add_argument("--frontend-ref", default="")
        parser.add_argument("--backup-ref", default="")
        parser.add_argument("--rollback-plan-ref", default="")
        parser.add_argument("--conciliation-plan-ref", default="")
        parser.add_argument(
            "--exigir-planos-arquivo",
            action="store_true",
            help=(
                "Exige que rollback-plan-ref e conciliation-plan-ref apontem "
                "para arquivos locais existentes."
            ),
        )
        parser.add_argument(
            "--exigir-rollback-plan-arquivo",
            action="store_true",
            help="Exige que rollback-plan-ref aponte para arquivo local existente.",
        )
        parser.add_argument(
            "--exigir-conciliation-plan-arquivo",
            action="store_true",
            help="Exige que conciliation-plan-ref aponte para arquivo local existente.",
        )
        parser.add_argument("--auditoria-totais-json", default="")
        parser.add_argument("--preflight-json", default="")
        parser.add_argument("--salvar-json", "--save-json", default="")
        parser.add_argument("--salvar-registro", "--save-record", default="")
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            action="store_true",
            help=(
                "Exige caminhos para salvar o JSON e o registro markdown do "
                "gate PM-06.2."
            ),
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
            help="Retorna erro quando a preparacao PM-06.2 nao estiver aprovada.",
        )

    def handle(self, *args, **options):
        evidence_files = _normalizar_arquivos_evidencia(options)
        output_files = _normalizar_arquivos_saida(options)
        payloads, load_checks = _carregar_payloads_evidencia(evidence_files)
        references = _normalizar_referencias(options)
        resultado = validar_preparacao_pm06(
            references,
            evidence_files=evidence_files,
            output_files=output_files,
            payloads=payloads,
            load_checks=load_checks,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_preparacao_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao preparacao PM-06.2 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_preparacao_pm06(
    references,
    *,
    evidence_files=None,
    output_files=None,
    payloads=None,
    load_checks=None,
):
    evidence_files = evidence_files or {}
    output_files = output_files or {}
    payloads = payloads or {}
    load_checks = load_checks or {"byKey": {}}
    loaders = load_checks.get("byKey") or {}
    requirements = references.get("requirements") or {}
    backup_evidence = _inspecionar_backup(references.get("backupRef") or "")
    backend_git_evidence = _inspecionar_git_ref(
        references.get("backendRef") or "",
        required=requirements.get("backendGitRef"),
    )

    checks = [
        _check(
            "backendRef",
            "Referencia backend/tag",
            _validar_referencia_obrigatoria(references.get("backendRef"), "backend-ref")
            + _validar_git_ref_backend(backend_git_evidence),
        ),
        _check(
            "frontendRef",
            "Referencia frontend",
            _validar_referencia_obrigatoria(references.get("frontendRef"), "frontend-ref"),
        ),
        _check(
            "backup",
            "Backup real e metadados",
            _validar_backup(backup_evidence),
        ),
        _check(
            "rollbackPlan",
            "Plano de rollback",
            _validar_referencia_plano(
                references.get("rollbackPlanRef"),
                "rollback-plan-ref",
                exigir_arquivo=requirements.get("rollbackPlanFile"),
            ),
        ),
        _check(
            "conciliationPlan",
            "Plano de conciliacao",
            _validar_referencia_plano(
                references.get("conciliationPlanRef"),
                "conciliation-plan-ref",
                exigir_arquivo=requirements.get("conciliationPlanFile"),
            ),
        ),
        _check(
            "totalsAudit",
            "Auditoria de totais pos-backup",
            _validar_auditoria_totais(payloads.get("totalsAudit"))
            + ((loaders.get("totalsAudit") or {}).get("issues") or []),
        ),
        _check(
            "deployPreflight",
            "Pre-flight financeiro pos-backup",
            _validar_preflight(payloads.get("deployPreflight"))
            + ((loaders.get("deployPreflight") or {}).get("issues") or []),
        ),
        _check(
            "outputEvidenceFiles",
            "Arquivos de evidencia do gate PM-06.2",
            _validar_arquivos_saida(
                output_files,
                exigir=requirements.get("outputEvidenceFiles"),
            ),
        ),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]

    return {
        "source": "pm06_backup_rollback_preparation",
        "step": PM06_STEP,
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
        "references": references,
        "gitEvidence": {"backendRef": backend_git_evidence},
        "backupEvidence": backup_evidence,
        "evidenceFiles": evidence_files,
        "generatedAt": timezone.now().isoformat(),
        "recommendedCommands": {
            "createBackup": "python manage.py backup_banco_mensal --force --manter 12",
            "totalsAudit": (
                "python manage.py auditar_totais_negocio "
                "--validar-valores-editaveis --falhar-com-divergencia "
                "--falhar-com-valores-editaveis --json"
            ),
            "deployPreflight": (
                "python manage.py validar_preflight_deploy_financeiro --falhar --json"
            ),
            "rerunPm06Preparation": (
                "python manage.py validar_preparacao_pm06 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--backend-ref=<tag-ou-commit-backend> "
                "--frontend-ref=<commit-ou-deploy-frontend> "
                "--backup-ref=<arquivo-backup-json> "
                "--rollback-plan-ref=<registro-ou-arquivo> "
                "--conciliation-plan-ref=<registro-ou-arquivo> --json --falhar"
            ),
            "rerunPm06PreparationStrictFiles": (
                "python manage.py validar_preparacao_pm06 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--backend-ref=<tag-ou-commit-backend> "
                "--frontend-ref=<commit-ou-deploy-frontend> "
                "--backup-ref=<arquivo-backup-json> "
                "--rollback-plan-ref=<arquivo-rollback-md> "
                "--conciliation-plan-ref=<arquivo-conciliacao-md> "
                "--exigir-backend-ref-git "
                "--exigir-planos-arquivo "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        },
    }


def _normalizar_referencias(options):
    exigir_planos_arquivo = bool(options.get("exigir_planos_arquivo"))
    return {
        "backendRef": options.get("backend_ref") or "",
        "frontendRef": options.get("frontend_ref") or "",
        "backupRef": options.get("backup_ref") or "",
        "rollbackPlanRef": options.get("rollback_plan_ref") or "",
        "conciliationPlanRef": options.get("conciliation_plan_ref") or "",
        "requirements": {
            "backendGitRef": bool(options.get("exigir_backend_ref_git")),
            "rollbackPlanFile": exigir_planos_arquivo
            or bool(options.get("exigir_rollback_plan_arquivo")),
            "conciliationPlanFile": exigir_planos_arquivo
            or bool(options.get("exigir_conciliation_plan_arquivo")),
            "outputEvidenceFiles": bool(options.get("exigir_arquivos_evidencia")),
        },
    }


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    base_path = Path(directory).expanduser() if directory else None

    def default_path(key, option_name):
        value = options.get(option_name) or ""
        if value or not base_path:
            return value
        return str(base_path / DEFAULT_EVIDENCE_FILENAMES[key])

    return {
        "directory": directory,
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
    for key in DEFAULT_EVIDENCE_FILENAMES:
        path = evidence_files.get(key) or ""
        payload, issues = _carregar_json(path)
        payloads[key] = payload
        by_key[key] = {"path": path, "issues": issues}
    return payloads, {"byKey": by_key}


def _carregar_json(path):
    if not path:
        return None, ["caminho de evidencia nao informado"]
    target = Path(path).expanduser()
    if not target.exists():
        return None, [f"arquivo ausente: {path}"]
    try:
        payload = json.loads(target.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return None, [f"JSON invalido: {exc}"]
    if not isinstance(payload, dict):
        return None, ["JSON deve ser um objeto"]
    return payload, []


def _inspecionar_backup(backup_ref):
    evidence = {
        "path": backup_ref,
        "exists": False,
        "isFile": False,
        "sizeBytes": None,
        "sha256": "",
        "_fileError": "",
        "metadataPath": "",
        "metadataExists": False,
        "metadata": {},
    }
    if not backup_ref:
        return evidence

    backup_path = Path(backup_ref).expanduser()
    evidence["exists"] = backup_path.exists()
    evidence["isFile"] = backup_path.is_file()
    if evidence["isFile"]:
        try:
            evidence["sizeBytes"] = backup_path.stat().st_size
            evidence["sha256"] = _calcular_sha256(backup_path)
        except OSError as exc:
            evidence["_fileError"] = f"erro ao ler arquivo de backup: {exc}"
    metadata_path = backup_path.with_name(f"{backup_path.stem}.meta.json")
    evidence["metadataPath"] = str(metadata_path)
    evidence["metadataExists"] = metadata_path.exists()
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            metadata = {"_error": f"JSON invalido: {exc}"}
        if isinstance(metadata, dict):
            evidence["metadata"] = metadata
        else:
            evidence["metadata"] = {"_error": "metadata deve ser um objeto"}
    return evidence


def _inspecionar_git_ref(ref, *, required=False):
    evidence = {
        "ref": ref,
        "required": bool(required),
        "checked": False,
        "exists": False,
        "commit": "",
        "error": "",
    }
    if not required or not ref:
        return evidence

    evidence["checked"] = True
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        evidence["error"] = str(exc)
        return evidence

    if completed.returncode == 0:
        evidence["exists"] = True
        evidence["commit"] = (completed.stdout or "").strip()
    else:
        evidence["error"] = (completed.stderr or completed.stdout or "").strip()
    return evidence


def _validar_referencia_obrigatoria(value, label):
    if not value:
        return [f"{label} nao informado"]
    return []


def _validar_git_ref_backend(evidence):
    if not evidence.get("required"):
        return []
    if not evidence.get("ref"):
        return []
    if not evidence.get("exists"):
        return ["backend-ref nao encontrado como git ref"]
    return []


def _validar_referencia_plano(value, label, *, exigir_arquivo=False):
    issues = _validar_referencia_obrigatoria(value, label)
    if issues or not exigir_arquivo:
        return issues
    target = Path(value).expanduser()
    if not target.exists():
        issues.append(f"{label} nao encontrado como arquivo")
    elif not target.is_file():
        issues.append(f"{label} deve apontar para arquivo")
    return issues


def _validar_backup(backup_evidence):
    issues = []
    if not backup_evidence.get("path"):
        return ["backup-ref nao informado"]
    if not backup_evidence.get("exists"):
        issues.append("backup real nao encontrado no caminho informado")
    elif not backup_evidence.get("isFile"):
        issues.append("backup-ref deve apontar para arquivo")
    if not backup_evidence.get("metadataExists"):
        issues.append("metadata do backup ausente")
    if backup_evidence.get("_fileError"):
        issues.append(backup_evidence["_fileError"])
    metadata = backup_evidence.get("metadata") or {}
    if metadata.get("_error"):
        issues.append(metadata["_error"])
    for field in ("arquivo", "sha256", "tamanho_bytes", "criado_em", "mes_referencia"):
        if not metadata.get(field):
            issues.append(f"metadata do backup sem {field}")
    if metadata.get("criado_em") and parse_datetime(str(metadata["criado_em"])) is None:
        issues.append("metadata do backup com criado_em invalido")
    if metadata.get("arquivo") and backup_evidence.get("path"):
        backup_name = Path(backup_evidence["path"]).name
        if metadata.get("arquivo") != backup_name:
            issues.append("metadata do backup aponta para arquivo diferente")
    if metadata.get("mes_referencia") and not _mes_referencia_valido(
        metadata.get("mes_referencia")
    ):
        issues.append("metadata do backup com mes_referencia invalido")
    if metadata.get("tamanho_bytes") and backup_evidence.get("sizeBytes") is not None:
        if _as_int(metadata.get("tamanho_bytes")) != backup_evidence["sizeBytes"]:
            issues.append("metadata do backup com tamanho_bytes divergente")
    if metadata.get("sha256") and backup_evidence.get("sha256"):
        if metadata.get("sha256") != backup_evidence["sha256"]:
            issues.append("metadata do backup com sha256 divergente")
    return issues


def _validar_auditoria_totais(payload):
    if not isinstance(payload, dict):
        return ["payload de auditoria de totais ausente ou invalido"]
    issues = []
    if payload.get("issues"):
        issues.append("auditoria de totais contem issues")
    obligations = payload.get("obligations") or {}
    if _as_int(obligations.get("divergentCount")) != 0:
        issues.append("auditoria de totais contem obrigacoes divergentes")
    editable = payload.get("editableValuesIntegrity") or {}
    if editable and editable.get("consistent") is not True:
        issues.append("valores editaveis inconsistentes na auditoria")
    return issues


def _validar_preflight(payload):
    if not isinstance(payload, dict):
        return ["payload de pre-flight ausente ou invalido"]
    issues = []
    if payload.get("ready") is not True:
        issues.append("pre-flight financeiro deve retornar ready=True")
    if payload.get("issues"):
        issues.append("pre-flight financeiro contem issues")
    return issues


def _validar_arquivos_saida(output_files, *, exigir=False):
    if not exigir:
        return []
    issues = []
    if not (output_files.get("json") or ""):
        issues.append("arquivo JSON de evidencia PM-06.2 nao informado")
    if not (output_files.get("record") or ""):
        issues.append("registro markdown de evidencia PM-06.2 nao informado")
    return issues


def _check(key, label, issues):
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


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


def _registro_preparacao_pm06(resultado):
    summary = resultado["checksSummary"]
    checks = "; ".join(
        f"{check['key']}={'ok' if check['ok'] else 'pendente'}"
        for check in resultado["checks"]
    )
    references = resultado["references"]
    requirements = references.get("requirements") or {}
    backend_git = (resultado.get("gitEvidence") or {}).get("backendRef") or {}
    backup = resultado["backupEvidence"]
    return "\n".join(
        [
            "### Registro PM-06.2 - validacao de backup, tag, rollback e conciliacao",
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
                "Referencias: "
                f"backend={references.get('backendRef') or '-'}; "
                f"frontend={references.get('frontendRef') or '-'}; "
                f"backup={references.get('backupRef') or '-'}; "
                f"rollbackPlan={references.get('rollbackPlanRef') or '-'}; "
                f"conciliationPlan={references.get('conciliationPlanRef') or '-'}"
            ),
            (
                "Planos como arquivo: "
                f"rollback={requirements.get('rollbackPlanFile') is True}; "
                f"conciliation={requirements.get('conciliationPlanFile') is True}"
            ),
            (
                "Backend git ref: "
                f"exigido={requirements.get('backendGitRef') is True}; "
                f"existe={backend_git.get('exists') is True}; "
                f"commit={backend_git.get('commit') or '-'}"
            ),
            (
                "Arquivos de evidencia exigidos: "
                f"{requirements.get('outputEvidenceFiles') is True}"
            ),
            (
                "Backup: "
                f"arquivoExiste={backup.get('exists')}; "
                f"metadataExiste={backup.get('metadataExists')}; "
                f"sha256={(backup.get('metadata') or {}).get('sha256') or '-'}; "
                f"sha256Calculado={backup.get('sha256') or '-'}; "
                f"tamanhoBytes={backup.get('sizeBytes') if backup.get('sizeBytes') is not None else '-'}; "
                f"mesReferencia={(backup.get('metadata') or {}).get('mes_referencia') or '-'}"
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
        return "preparacao PM-06.2 nao aprovada"
    return f"preparacao PM-06.2 nao aprovada: {resultado['issues'][0]}"


def _calcular_sha256(path):
    hasher = hashlib.sha256()
    with path.open("rb") as backup_file:
        for chunk in iter(lambda: backup_file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _mes_referencia_valido(value):
    if not isinstance(value, str):
        return False
    year, separator, month = value.partition("-")
    if separator != "-":
        return False
    if not (year.isdigit() and month.isdigit()):
        return False
    return 1 <= int(month) <= 12


def _as_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return -1
