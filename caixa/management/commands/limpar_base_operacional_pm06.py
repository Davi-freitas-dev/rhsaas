import hashlib
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import router, transaction
from django.utils import timezone

from caixa.management.commands.auditar_totais_negocio import auditar_totais_negocio
from caixa.models import (
    BaixaFinanceira,
    BaixaFinanceiraAlocacao,
    Cliente,
    DespesaOperacional,
    Evento,
    LancamentoFinanceiro,
    ObrigacaoFinanceira,
    Orcamento,
    OrcamentoItem,
    ReceitaOperacional,
)
from caixa.models_custo_fixo import CustoFixo
from caixa.models_custos_extras import EventoCustoExtra, OrcamentoCustoExtra
from caixa.models_dividas import Credor, DividaFinanceira, PagamentoParcelaDivida, ParcelaDivida
from caixa.models_fcf import FinanciamentoMovimentacao
from caixa.models_fci import Investimento
from caixa.models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from caixa.models_servico import EventoCustoServico


CONFIRMATION_TOKEN = "LIMPAR_BASE_PM06_COM_BACKUP_E_RECADASTRO_MANUAL"
DEFAULT_READINESS_JSON = "pm06-prontidao-base-limpa-manual.json"
DEFAULT_REENTRY_JSON = "pm06-validacao-recadastro-manual.json"
DEFAULT_DRY_RUN_JSON = "pm06-limpeza-base-operacional-dry-run.json"
DEFAULT_DRY_RUN_MD = "pm06-limpeza-base-operacional-dry-run.md"
DEFAULT_EXECUTION_JSON = "pm06-limpeza-base-operacional-execucao.json"
DEFAULT_EXECUTION_MD = "pm06-limpeza-base-operacional-execucao.md"


CURRENT_MODELS = [
    BaixaFinanceiraAlocacao,
    BaixaFinanceira,
    ObrigacaoFinanceira,
    LancamentoFinanceiro,
    PagamentoEventoCustoServico,
    PagamentoEventoCustoExtra,
    PagamentoParcelaDivida,
    ReceitaOperacional,
    DespesaOperacional,
    Investimento,
    FinanciamentoMovimentacao,
    CustoFixo,
    ParcelaDivida,
    DividaFinanceira,
    OrcamentoCustoExtra,
    EventoCustoServico,
    EventoCustoExtra,
    Evento,
    OrcamentoItem,
    Orcamento,
    Credor,
    Cliente,
]

PRESERVED_MODELS = [
    "auth.User",
    "auth.Group",
    "auth.Permission",
    "sessions.Session",
    "caixa.Servico",
    "caixa.ConfiguracaoFinanceira",
]


class Command(BaseCommand):
    help = (
        "Limpa dados operacionais PM-06 para recadastro manual em base limpa. "
        "Exige backup, evidencias aprovadas e confirmacao explicita."
    )

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--executar", action="store_true")
        parser.add_argument("--diretorio-evidencias", default="")
        parser.add_argument("--prontidao-json", default="")
        parser.add_argument("--recadastro-validacao-json", default="")
        parser.add_argument("--backup-ref", default="")
        parser.add_argument("--confirmacao", default="")
        parser.add_argument("--limpar-historico", action="store_true")
        parser.add_argument("--salvar-json", default="")
        parser.add_argument("--salvar-registro", default="")
        parser.add_argument("--exigir-arquivos-evidencia", action="store_true")
        parser.add_argument("--json", action="store_true", dest="json_output")
        parser.add_argument("--falhar", action="store_true")

    def handle(self, *args, **options):
        mode = "execute" if options["executar"] else "dry-run"
        refs = _normalizar_referencias(options, mode)
        output_files = _normalizar_arquivos_saida(options, mode)
        payload = executar_limpeza_pm06(
            mode=mode,
            refs=refs,
            output_files=output_files,
            clean_history=bool(options["limpar_historico"]),
            confirmation=options.get("confirmacao") or "",
            require_output_files=bool(options["exigir_arquivos_evidencia"]),
        )
        _salvar_payload(payload)

        if options["json_output"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(payload["executionRecord"]["markdown"])

        if (options["falhar"] or mode == "execute") and not payload["ready"]:
            raise CommandError(_primeira_issue(payload))


def executar_limpeza_pm06(
    *,
    mode,
    refs,
    output_files,
    clean_history,
    confirmation,
    require_output_files,
):
    checks = []
    issues = []

    backup_check = _validar_backup(refs["backupRef"])
    readiness_payload, readiness_check = _carregar_e_validar_prontidao(refs["readinessJson"])
    reentry_payload, reentry_check = _carregar_e_validar_recadastro(refs["reentryValidationJson"])
    consistency_check = _validar_consistencia_evidencias(
        refs,
        readiness_payload=readiness_payload,
        reentry_payload=reentry_payload,
    )
    output_check = _validar_arquivos_saida(output_files, require_output_files)
    confirmation_check = _validar_confirmacao(mode, confirmation)

    checks.extend([
        backup_check,
        readiness_check,
        reentry_check,
        consistency_check,
        output_check,
        confirmation_check,
    ])
    issues.extend(issue for check in checks for issue in check["issues"])

    before_counts = _contagens_modelos(CURRENT_MODELS)
    before_history_counts = _contagens_modelos(_historical_models()) if clean_history else {}
    preserved_counts = _contagens_preservados()
    audit_before = auditar_totais_negocio(validar_valores_editaveis=True)

    deleted_counts = {}
    history_deleted_counts = {}
    nullified_counts = {}
    executed = False

    if not issues and mode == "execute":
        with transaction.atomic():
            nullified_counts = _preparar_fks_auto_referenciadas()
            deleted_counts = _limpar_modelos(CURRENT_MODELS)
            if clean_history:
                history_deleted_counts = _limpar_modelos(_historical_models())
            executed = True
    elif mode == "dry-run":
        deleted_counts = dict(before_counts)
        history_deleted_counts = dict(before_history_counts)

    after_counts = _contagens_modelos(CURRENT_MODELS)
    after_history_counts = _contagens_modelos(_historical_models()) if clean_history else {}
    audit_after = auditar_totais_negocio(validar_valores_editaveis=True) if executed else None

    if executed:
        residue = {
            label: count
            for label, count in after_counts.items()
            if count != 0
        }
        if residue:
            issues.append(f"limpeza executada deixou residuos: {residue}")

    ready = not issues
    decision = _montar_decisao(mode, ready, executed, clean_history)
    payload = {
        "source": "pm06_operational_clean_database_execution",
        "step": "PM-06",
        "mode": mode,
        "readOnly": mode != "execute",
        "ready": ready,
        "executed": executed,
        "cleanHistory": clean_history,
        "issues": issues,
        "checks": checks,
        "checksSummary": {
            "ready": ready,
            "total": len(checks),
            "okCount": sum(1 for check in checks if check["ok"]),
            "pending": [check["key"] for check in checks if not check["ok"]],
            "pendingCount": sum(1 for check in checks if not check["ok"]),
            "issueCount": len(issues),
        },
        "decision": decision,
        "references": refs,
        "counts": {
            "before": before_counts,
            "after": after_counts,
            "deleted": deleted_counts,
            "historyBefore": before_history_counts,
            "historyAfter": after_history_counts,
            "historyDeleted": history_deleted_counts,
            "nullified": nullified_counts,
            "preserved": preserved_counts,
        },
        "auditBefore": audit_before,
        "auditAfter": audit_after,
        "inputEvidence": {
            "readiness": _resumir_payload(readiness_payload),
            "manualReentry": _resumir_payload(reentry_payload),
        },
        "outputEvidenceFiles": output_files,
        "generatedAt": timezone.now().isoformat(),
    }
    payload["executionRecord"] = {
        "format": "markdown",
        "markdown": _registro_markdown(payload),
    }
    return payload


def _normalizar_referencias(options, mode):
    directory = options.get("diretorio_evidencias") or ""
    base = Path(directory) if directory else None
    return {
        "evidenceDirectory": directory,
        "backupRef": options.get("backup_ref") or "",
        "readinessJson": (
            options.get("prontidao_json")
            or (str(base / DEFAULT_READINESS_JSON) if base else "")
        ),
        "reentryValidationJson": (
            options.get("recadastro_validacao_json")
            or (str(base / DEFAULT_REENTRY_JSON) if base else "")
        ),
        "confirmationToken": CONFIRMATION_TOKEN if mode == "execute" else "",
    }


def _normalizar_arquivos_saida(options, mode):
    directory = options.get("diretorio_evidencias") or ""
    output_json = options.get("salvar_json") or ""
    output_record = options.get("salvar_registro") or ""
    if directory:
        base = Path(directory)
        if mode == "execute":
            output_json = output_json or str(base / DEFAULT_EXECUTION_JSON)
            output_record = output_record or str(base / DEFAULT_EXECUTION_MD)
        else:
            output_json = output_json or str(base / DEFAULT_DRY_RUN_JSON)
            output_record = output_record or str(base / DEFAULT_DRY_RUN_MD)
    return {
        "json": output_json,
        "record": output_record,
    }


def _check(key, label, issues):
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


def _validar_backup(backup_ref):
    issues = []
    if not backup_ref:
        issues.append("backup-ref nao informado")
        return _check("backup", "Backup bruto vigente", issues)

    backup_path = Path(backup_ref)
    if not backup_path.exists() or not backup_path.is_file():
        issues.append(f"backup-ref nao encontrado: {backup_ref}")
        return _check("backup", "Backup bruto vigente", issues)

    metadata_path = backup_path.with_suffix(".meta.json")
    if not metadata_path.exists():
        issues.append(f"metadata do backup nao encontrada: {metadata_path}")
        return _check("backup", "Backup bruto vigente", issues)

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        issues.append(f"metadata do backup invalida: {exc}")
        return _check("backup", "Backup bruto vigente", issues)

    expected_sha = metadata.get("sha256")
    if not expected_sha:
        issues.append("metadata do backup nao contem sha256")
    else:
        actual_sha = _sha256(backup_path)
        if actual_sha != expected_sha:
            issues.append("sha256 do backup diverge da metadata")

    return _check("backup", "Backup bruto vigente", issues)


def _carregar_e_validar_prontidao(path):
    payload, issues = _carregar_json(path, "prontidao-json")
    if payload:
        if payload.get("source") != "pm06_clean_database_manual_reentry_readiness":
            issues.append("prontidao-json nao e evidencia de base limpa PM-06")
        if not payload.get("ready"):
            issues.append("prontidao-json nao esta ready=true")
        decision = payload.get("cleanDatabaseManualDecision") or {}
        if decision.get("status") != "approved":
            issues.append("prontidao-json nao esta approved")
        if not decision.get("mayUseCleanDatabaseManualReentry"):
            issues.append("prontidao-json nao libera uso de recadastro manual")
    return payload, _check("readiness", "Prontidao PM-06 aprovada", issues)


def _carregar_e_validar_recadastro(path):
    payload, issues = _carregar_json(path, "recadastro-validacao-json")
    if payload:
        if payload.get("source") != "pm06_manual_reentry_readiness":
            issues.append("recadastro-validacao-json nao e evidencia de recadastro PM-06")
        if not payload.get("ready"):
            issues.append("recadastro-validacao-json nao esta ready=true")
        decision = payload.get("manualReentryDecision") or {}
        if decision.get("status") != "approved":
            issues.append("recadastro manual nao esta approved")
        if not decision.get("mayUseForManualReentry"):
            issues.append("recadastro manual nao libera uso para recadastro")
        comparison = payload.get("currentDatabaseComparison") or {}
        if not comparison.get("compared"):
            issues.append("recadastro manual nao comparou pacote com base atual")
        if comparison.get("differences"):
            issues.append("recadastro manual possui divergencias contra base atual")
    return payload, _check("manualReentry", "Recadastro manual validado", issues)


def _validar_consistencia_evidencias(refs, *, readiness_payload, reentry_payload):
    issues = []
    backup_ref = _normalizar_ref(refs.get("backupRef"))
    if readiness_payload:
        readiness_refs = readiness_payload.get("references") or {}
        readiness_backup = _normalizar_ref(readiness_refs.get("backupRef"))
        if readiness_backup and backup_ref and readiness_backup != backup_ref:
            issues.append(
                "backup-ref diverge do backup registrado na prontidao PM-06: "
                f"{readiness_backup}"
            )

    if reentry_payload:
        comparison = reentry_payload.get("currentDatabaseComparison") or {}
        if comparison.get("enabled") is False:
            issues.append("comparacao do recadastro com a base atual estava desativada")

    return _check("evidenceConsistency", "Consistencia entre evidencias", issues)


def _carregar_json(path, label):
    issues = []
    if not path:
        return None, [f"{label} nao informado"]
    json_path = Path(path)
    if not json_path.exists() or not json_path.is_file():
        return None, [f"{label} nao encontrado: {path}"]
    try:
        return json.loads(json_path.read_text(encoding="utf-8-sig")), issues
    except Exception as exc:
        return None, [f"{label} invalido: {exc}"]


def _validar_arquivos_saida(output_files, require_output_files):
    issues = []
    if require_output_files:
        for key in ("json", "record"):
            if not output_files.get(key):
                issues.append(f"arquivo de saida nao informado: {key}")
    for key, value in output_files.items():
        if not value:
            continue
        path = Path(value)
        if path.exists() and path.is_dir():
            issues.append(f"arquivo de saida aponta para diretorio: {value}")
        if key == "json" and path.suffix.lower() != ".json":
            issues.append("arquivo JSON de evidencia deve usar extensao .json")
        if key == "record" and path.suffix.lower() not in {".md", ".markdown"}:
            issues.append("registro de evidencia deve usar extensao .md ou .markdown")
        if path.parent and not path.parent.exists():
            issues.append(f"diretorio de saida nao existe: {path.parent}")
    return _check("outputEvidenceFiles", "Arquivos de evidencia de saida", issues)


def _validar_confirmacao(mode, confirmation):
    issues = []
    if mode == "execute" and confirmation != CONFIRMATION_TOKEN:
        issues.append(
            "confirmacao invalida; use "
            f"--confirmacao={CONFIRMATION_TOKEN}"
        )
    return _check("confirmation", "Confirmacao explicita", issues)


def _contagens_modelos(models):
    return {
        _model_label(model): model._base_manager.count()
        for model in models
    }


def _contagens_preservados():
    return {label: "preservado" for label in PRESERVED_MODELS}


def _preparar_fks_auto_referenciadas():
    return {
        "caixa.CustoFixo.custo_pai": CustoFixo.objects.exclude(custo_pai=None).update(custo_pai=None),
        "caixa.ParcelaDivida.parcela_origem": ParcelaDivida.objects.exclude(parcela_origem=None).update(parcela_origem=None),
    }


def _limpar_modelos(models):
    deleted = {}
    for model in models:
        label = _model_label(model)
        using = router.db_for_write(model)
        deleted[label] = model._base_manager.all()._raw_delete(using)
    return deleted


def _historical_models():
    historical = []
    seen = set()
    for model in CURRENT_MODELS:
        history = getattr(model, "history", None)
        history_model = getattr(history, "model", None)
        if history_model is None:
            continue
        label = _model_label(history_model)
        if label in seen:
            continue
        historical.append(history_model)
        seen.add(label)
    return historical


def _model_label(model):
    return f"{model._meta.app_label}.{model.__name__}"


def _normalizar_ref(value):
    return str(value or "").strip().replace("\\", "/")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resumir_payload(payload):
    if not payload:
        return {}
    return {
        "source": payload.get("source"),
        "step": payload.get("step"),
        "ready": payload.get("ready"),
        "generatedAt": payload.get("generatedAt"),
    }


def _montar_decisao(mode, ready, executed, clean_history):
    return {
        "status": "approved" if ready else "blocked",
        "mode": mode,
        "executed": executed,
        "mayUseForManualReentry": ready,
        "cleanHistory": clean_history,
        "nextStep": (
            "Recadastrar manualmente pelo sistema novo e comparar auditoria antes/depois."
            if executed
            else "Revisar dry-run; executar somente com token explicito."
        ),
    }


def _registro_markdown(payload):
    counts = payload["counts"]
    lines = [
        "### Registro PM-06 - limpeza operacional para base limpa manual",
        "",
        f"Data/hora: {payload['generatedAt']}",
        f"Modo: {payload['mode']}",
        f"Ready: {payload['ready']}",
        f"Executado: {payload['executed']}",
        f"Limpar historico: {payload['cleanHistory']}",
        f"Issues: {len(payload['issues'])}",
        "",
        "#### Checks",
    ]
    for check in payload["checks"]:
        status = "ok" if check["ok"] else "pendente"
        lines.append(f"- {check['label']}: {status}")
        for issue in check["issues"]:
            lines.append(f"  - {issue}")

    lines.extend(["", "#### Contagens alvo"])
    for label, count in counts["before"].items():
        after = counts["after"].get(label, "-")
        deleted = counts["deleted"].get(label, "-")
        lines.append(f"- {label}: antes={count}; removidos={deleted}; depois={after}")

    if payload["cleanHistory"]:
        lines.extend(["", "#### Historico"])
        for label, count in counts["historyBefore"].items():
            after = counts["historyAfter"].get(label, "-")
            deleted = counts["historyDeleted"].get(label, "-")
            lines.append(f"- {label}: antes={count}; removidos={deleted}; depois={after}")

    lines.extend([
        "",
        "#### Preservado",
        *[f"- {label}" for label in PRESERVED_MODELS],
        "",
        "#### Arquivos",
        f"- json: {payload['outputEvidenceFiles'].get('json') or '-'}",
        f"- registro: {payload['outputEvidenceFiles'].get('record') or '-'}",
    ])
    return "\n".join(lines)


def _salvar_payload(payload):
    files = payload.get("outputEvidenceFiles") or {}
    json_path = files.get("json") or ""
    record_path = files.get("record") or ""
    if json_path:
        Path(json_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if record_path:
        Path(record_path).write_text(
            payload["executionRecord"]["markdown"],
            encoding="utf-8",
        )


def _primeira_issue(payload):
    return payload["issues"][0] if payload.get("issues") else "limpeza PM-06 bloqueada"
