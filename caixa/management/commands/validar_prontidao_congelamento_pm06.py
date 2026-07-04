import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.constants_nomenclatura import (
    VERSAO_REMOCAO_ALIASES_LEGADOS,
    montar_metadados_nomenclatura_financeira,
)
from caixa.management.commands.verificar_prontidao_escrita_canonica import (
    verificar_prontidao_escrita_canonica,
)


DEFAULT_OUTPUT_JSON = "pm06-prontidao-congelamento-legado.json"
DEFAULT_OUTPUT_RECORD = "pm06-prontidao-congelamento-legado.md"
FRONTEND_CANONICAL_VALIDATION_MARKERS = (
    "verify:publish",
    "verify-publish",
    "check:financial-canonical",
    "check-financial-canonical",
    "financial-canonical",
)


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, se a PM-06 pode iniciar congelamento "
        "de escrita em modelos legados. O comando nao altera dados, flags, "
        "models, migrations, aliases ou templates."
    )

    def add_arguments(self, parser):
        parser.add_argument("--frontend-validacao-ref", default="")
        parser.add_argument("--aceite-operacional-ref", default="")
        parser.add_argument("--backup-rollback-ref", default="")
        parser.add_argument("--janela-congelamento-ref", default="")
        parser.add_argument("--revisao-semantica", action="store_true")
        parser.add_argument("--revisao-tecnica", action="store_true")
        parser.add_argument("--revisao-extra", action="store_true")
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
            help="Retorna erro quando o congelamento legado ainda estiver bloqueado.",
        )

    def handle(self, *args, **options):
        output_files = _normalizar_arquivos_saida(options)
        resultado = validar_prontidao_congelamento_pm06(
            _normalizar_referencias(options),
            output_files=output_files,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_prontidao_congelamento_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao de prontidao de congelamento PM-06 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        decision = resultado["freezeDecision"]
        self.stdout.write(
            "freezeDecision="
            f"{decision['status']}; "
            f"mayFreezeLegacyWrites={decision['mayFreezeLegacyWrites']}; "
            f"mayCreateCleanupMigrations={decision['mayCreateCleanupMigrations']}"
        )
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_prontidao_congelamento_pm06(
    references,
    *,
    output_files=None,
    write_readiness=None,
    nomenclature=None,
):
    output_files = output_files or {}
    references = references or {}
    requirements = references.get("requirements") or {}
    write_readiness = write_readiness or verificar_prontidao_escrita_canonica()
    nomenclature = nomenclature or montar_metadados_nomenclatura_financeira()
    freeze_scope = _montar_escopo_congelamento(write_readiness, nomenclature)

    checks = [
        _check(
            "canonicalWriteReadiness",
            "Cobertura de escrita canonical-first",
            _validar_cobertura_canonical_first(write_readiness),
        ),
        _check(
            "adapterOnlySources",
            "Origens ainda adapter-only",
            _validar_origens_adapter_only(write_readiness),
        ),
        _check(
            "physicalFields",
            "Campos fisicos pendentes",
            _validar_campos_fisicos_pendentes(freeze_scope),
        ),
        _check(
            "financeiroV3Policy",
            "Politica financeiro-v3",
            _validar_politica_financeiro_v3(freeze_scope),
        ),
        _check(
            "frontendValidation",
            "Validacao frontend publicada",
            _validar_frontend_validacao_ref(
                references.get("frontendValidationRef")
            ),
        ),
        _check(
            "operationalAcceptance",
            "Aceite operacional",
            _validar_referencia(references.get("operationalAcceptanceRef"), "aceite-operacional-ref"),
        ),
        _check(
            "backupRollback",
            "Backup/rollback da janela",
            _validar_referencia(references.get("backupRollbackRef"), "backup-rollback-ref"),
        ),
        _check(
            "freezeWindow",
            "Janela de congelamento",
            _validar_referencia(
                references.get("freezeWindowRef"),
                "janela-congelamento-ref",
            ),
        ),
        _check(
            "finalReviews",
            "Revisoes finais antes do congelamento",
            _validar_revisoes_finais(references),
        ),
        _check(
            "outputEvidenceFiles",
            "Arquivos de evidencia",
            _validar_arquivos_saida(
                output_files,
                exigir=requirements.get("outputEvidenceFiles"),
            ),
        ),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]
    decision = _montar_decisao_congelamento(ready, issues)

    return {
        "source": "pm06_legacy_freeze_readiness",
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
        "freezeDecision": decision,
        "freezeScope": freeze_scope,
        "frontendCanonicalValidationPolicy": _resumir_politica_validacao_frontend(),
        "references": references,
        "generatedAt": timezone.now().isoformat(),
        "recommendedCommands": {
            "canonicalWriteReadiness": (
                "python manage.py verificar_prontidao_escrita_canonica "
                "--json --falhar-com-inconsistencia"
            ),
            "pm06ClosureGate": (
                "python manage.py validar_fechamento_pm06 "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
            "rerunFreezeReadiness": (
                "python manage.py validar_prontidao_congelamento_pm06 "
                "--frontend-validacao-ref=<verify-publish-ou-check-financial-canonical-ref> "
                "--aceite-operacional-ref=<aceite-operacional> "
                "--backup-rollback-ref=<pm06-backup-rollback-ref> "
                "--janela-congelamento-ref=<janela-homologada> "
                "--revisao-semantica --revisao-tecnica --revisao-extra "
                "--diretorio-evidencias=<diretorio-evidencias-pm06> "
                "--exigir-arquivos-evidencia --json --falhar"
            ),
        },
    }


def _normalizar_referencias(options):
    return {
        "frontendValidationRef": options.get("frontend_validacao_ref") or "",
        "operationalAcceptanceRef": options.get("aceite_operacional_ref") or "",
        "backupRollbackRef": options.get("backup_rollback_ref") or "",
        "freezeWindowRef": options.get("janela_congelamento_ref") or "",
        "semanticReview": bool(options.get("revisao_semantica")),
        "technicalReview": bool(options.get("revisao_tecnica")),
        "extraReview": bool(options.get("revisao_extra")),
        "requirements": {
            "outputEvidenceFiles": bool(options.get("exigir_arquivos_evidencia")),
        },
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


def _montar_escopo_congelamento(write_readiness, nomenclature):
    alias_policy = nomenclature.get("aliasRemovalPolicy") or {}
    pending_physical_fields = nomenclature.get("physicalFieldsPendingMigration") or []
    planned_physical_renames = nomenclature.get("plannedPhysicalRenames") or {}
    return {
        "currentContractVersion": nomenclature.get("version") or "",
        "removeOnlyInVersion": alias_policy.get("removeOnlyInVersion") or "",
        "aliasRemovalRule": alias_policy.get("rule") or "",
        "currentWriteMode": write_readiness.get("currentWriteMode") or "",
        "targetWriteMode": write_readiness.get("targetWriteMode") or "",
        "canonicalFirstReady": write_readiness.get("canonicalFirstReady") is True,
        "featureFlagEnabled": write_readiness.get("featureFlagEnabled") is True,
        "enabledCanonicalFirstSources": list(
            write_readiness.get("enabledCanonicalFirstSources") or []
        ),
        "invalidFeatureFlagSources": list(
            write_readiness.get("invalidFeatureFlagSources") or []
        ),
        "directCanonicalFirstSources": list(
            write_readiness.get("directCanonicalFirstSources") or []
        ),
        "adapterOnlySources": list(write_readiness.get("adapterOnlySources") or []),
        "writeReadinessInconsistencies": list(
            write_readiness.get("inconsistencies") or []
        ),
        "pendingPhysicalFields": list(pending_physical_fields),
        "pendingPhysicalFieldCount": len(pending_physical_fields),
        "plannedPhysicalRenames": sorted(planned_physical_renames),
        "plannedPhysicalRenameCount": len(planned_physical_renames),
    }


def _validar_cobertura_canonical_first(write_readiness):
    issues = []
    inconsistencies = write_readiness.get("inconsistencies") or []
    for inconsistency in inconsistencies:
        issues.append(f"prontidao de escrita canonica inconsistente: {inconsistency}")
    if write_readiness.get("currentWriteMode") != write_readiness.get("targetWriteMode"):
        issues.append("modo de escrita atual ainda nao e canonical-first")
    if write_readiness.get("canonicalFirstReady") is not True:
        issues.append("canonical-first ainda nao esta pronto para todas as origens")
    if write_readiness.get("featureFlagEnabled") is not True:
        issues.append("feature flag canonical-first nao esta ativa")
    if not write_readiness.get("enabledCanonicalFirstSources"):
        issues.append("nenhuma origem canonical-first esta habilitada")
    invalid_sources = write_readiness.get("invalidFeatureFlagSources") or []
    if invalid_sources:
        issues.append(
            "feature flag canonical-first contem origens invalidas: "
            + ", ".join(invalid_sources)
        )
    return issues


def _validar_origens_adapter_only(write_readiness):
    sources = write_readiness.get("adapterOnlySources") or []
    if not sources:
        return []
    return [
        "origens adapter-only ainda dependem de escrita legada sincronizada: "
        + ", ".join(sources)
    ]


def _validar_campos_fisicos_pendentes(freeze_scope):
    fields = freeze_scope.get("pendingPhysicalFields") or []
    if not fields:
        return []
    return ["campos fisicos pendentes de migracao: " + ", ".join(fields)]


def _validar_politica_financeiro_v3(freeze_scope):
    issues = []
    if freeze_scope.get("removeOnlyInVersion") != VERSAO_REMOCAO_ALIASES_LEGADOS:
        issues.append("politica financeiro-v3 sem versao de remocao esperada")
    if freeze_scope.get("currentContractVersion") == freeze_scope.get("removeOnlyInVersion"):
        issues.append("contrato atual ja esta na versao de remocao de aliases")
    if not freeze_scope.get("aliasRemovalRule"):
        issues.append("politica financeiro-v3 sem regra documentada")
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


def _validar_revisoes_finais(references):
    issues = []
    if not references.get("semanticReview"):
        issues.append("revisao-semantica nao confirmada")
    if not references.get("technicalReview"):
        issues.append("revisao-tecnica nao confirmada")
    if not references.get("extraReview"):
        issues.append("revisao-extra nao confirmada")
    return issues


def _validar_arquivos_saida(output_files, *, exigir=False):
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


def _montar_decisao_congelamento(ready, issues):
    return {
        "status": "approved" if ready else "blocked",
        "step": "PM-06",
        "mayFreezeLegacyWrites": bool(ready),
        "mayCreateCleanupMigrations": False,
        "cleanupMigrationPolicy": (
            "Migrations de limpeza continuam bloqueadas e exigem gate proprio "
            "de backup, homologacao, auditoria sem divergencias e aceite operacional."
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


def _registro_prontidao_congelamento_pm06(resultado):
    decision = resultado["freezeDecision"]
    scope = resultado["freezeScope"]
    frontend_policy = resultado.get("frontendCanonicalValidationPolicy") or {}
    lines = [
        "### Registro PM-06 - prontidao de congelamento legado",
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
            f"mayFreezeLegacyWrites={decision['mayFreezeLegacyWrites']}; "
            f"mayCreateCleanupMigrations={decision['mayCreateCleanupMigrations']}"
        ),
        (
            "Escopo: "
            f"currentWriteMode={scope['currentWriteMode'] or '-'}; "
            f"targetWriteMode={scope['targetWriteMode'] or '-'}; "
            f"adapterOnlySources={','.join(scope['adapterOnlySources']) or '-'}; "
            f"pendingPhysicalFields={','.join(scope['pendingPhysicalFields']) or '-'}"
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
        return f"congelamento legado PM-06 nao aprovado: {resultado['issues'][0]}"
    return "congelamento legado PM-06 nao aprovado"
