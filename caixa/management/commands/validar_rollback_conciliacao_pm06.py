import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_date


DEFAULT_OUTPUT_JSON = "pm06-rollback-conciliacao-janela.json"
DEFAULT_OUTPUT_RECORD = "pm06-rollback-conciliacao-janela.md"


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, o plano de rollback e conciliacao para "
        "dados criados entre backup e janela PM-06. Nao executa rollback, "
        "conciliacao, queries de alteracao, migrations ou limpeza."
    )

    def add_arguments(self, parser):
        parser.add_argument("--backup-ref", default="")
        parser.add_argument("--codigo-janela-ref", default="")
        parser.add_argument("--janela-inicio", default="")
        parser.add_argument("--janela-fim", default="")
        parser.add_argument("--rollback-plan-ref", default="")
        parser.add_argument("--conciliation-script-ref", default="")
        parser.add_argument("--delta-data-policy-ref", default="")
        parser.add_argument("--owner-ref", default="")
        parser.add_argument("--homologacao-ref", default="")
        parser.add_argument("--aceite-operacional-ref", default="")
        parser.add_argument("--revisao-semantica", action="store_true")
        parser.add_argument("--revisao-tecnica", action="store_true")
        parser.add_argument("--revisao-extra", action="store_true")
        parser.add_argument(
            "--exigir-arquivos-plano",
            action="store_true",
            help=(
                "Exige que rollback, conciliacao e politica de dados delta "
                "apontem para arquivos locais existentes."
            ),
        )
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
            help="Retorna erro quando rollback/conciliacao da janela nao estiverem aprovados.",
        )

    def handle(self, *args, **options):
        output_files = _normalizar_arquivos_saida(options)
        resultado = validar_rollback_conciliacao_pm06(
            _normalizar_referencias(options),
            output_files=output_files,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_rollback_conciliacao_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao rollback/conciliacao PM-06 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        decision = resultado["rollbackConciliationDecision"]
        self.stdout.write(
            "rollbackConciliationDecision="
            f"{decision['status']}; "
            f"mayUseForCleanupMigrationGate={decision['mayUseForCleanupMigrationGate']}; "
            f"mayExecuteRollback={decision['mayExecuteRollback']}; "
            f"mayExecuteConciliation={decision['mayExecuteConciliation']}"
        )
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")


def validar_rollback_conciliacao_pm06(references, *, output_files=None):
    references = references or {}
    output_files = output_files or {}
    requirements = references.get("requirements") or {}
    window = _montar_janela(references)

    checks = [
        _check("backup", "Backup da janela", _validar_referencia(references.get("backupRef"), "backup-ref")),
        _check(
            "windowRef",
            "Codigo/registro da janela",
            _validar_referencia(references.get("windowRef"), "codigo-janela-ref"),
        ),
        _check("windowInterval", "Intervalo da janela", _validar_janela(window)),
        _check(
            "rollbackPlan",
            "Plano de rollback",
            _validar_referencia_plano(
                references.get("rollbackPlanRef"),
                "rollback-plan-ref",
                exigir_arquivo=requirements.get("planFiles"),
            ),
        ),
        _check(
            "conciliationScript",
            "Script/plano de conciliacao",
            _validar_referencia_plano(
                references.get("conciliationScriptRef"),
                "conciliation-script-ref",
                exigir_arquivo=requirements.get("planFiles"),
            ),
        ),
        _check(
            "deltaDataPolicy",
            "Politica para dados criados entre backup e janela",
            _validar_referencia_plano(
                references.get("deltaDataPolicyRef"),
                "delta-data-policy-ref",
                exigir_arquivo=requirements.get("planFiles"),
            ),
        ),
        _check(
            "owner",
            "Responsavel operacional",
            _validar_referencia(references.get("ownerRef"), "owner-ref"),
        ),
        _check(
            "homologation",
            "Homologacao do rollback/conciliacao",
            _validar_referencia(references.get("homologationRef"), "homologacao-ref"),
        ),
        _check(
            "operationalAcceptance",
            "Aceite operacional",
            _validar_referencia(references.get("operationalAcceptanceRef"), "aceite-operacional-ref"),
        ),
        _check(
            "finalReviews",
            "Revisoes finais",
            _validar_revisoes_finais(references),
        ),
        _check(
            "outputEvidenceFiles",
            "Arquivos de evidencia",
            _validar_arquivos_saida(
                output_files,
                exigir=requirements.get("outputEvidenceFiles"),
                input_files=plan_files_from_references(references),
            ),
        ),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]
    decision = _montar_decisao_rollback_conciliacao(ready, issues)

    return {
        "source": "pm06_rollback_conciliation_window",
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
        "rollbackConciliationDecision": decision,
        "window": window,
        "references": references,
        "planFiles": plan_files_from_references(references),
        "generatedAt": timezone.now().isoformat(),
        "recommendedCommands": {
            "rerunRollbackConciliation": (
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
            )
        },
    }


def _normalizar_referencias(options):
    return {
        "backupRef": options.get("backup_ref") or "",
        "windowRef": options.get("codigo_janela_ref") or "",
        "windowStart": options.get("janela_inicio") or "",
        "windowEnd": options.get("janela_fim") or "",
        "rollbackPlanRef": options.get("rollback_plan_ref") or "",
        "conciliationScriptRef": options.get("conciliation_script_ref") or "",
        "deltaDataPolicyRef": options.get("delta_data_policy_ref") or "",
        "ownerRef": options.get("owner_ref") or "",
        "homologationRef": options.get("homologacao_ref") or "",
        "operationalAcceptanceRef": options.get("aceite_operacional_ref") or "",
        "semanticReview": bool(options.get("revisao_semantica")),
        "technicalReview": bool(options.get("revisao_tecnica")),
        "extraReview": bool(options.get("revisao_extra")),
        "requirements": {
            "planFiles": bool(options.get("exigir_arquivos_plano")),
            "outputEvidenceFiles": bool(options.get("exigir_arquivos_evidencia")),
        },
    }


def plan_files_from_references(references):
    return {
        "rollbackPlan": references.get("rollbackPlanRef") or "",
        "conciliationScript": references.get("conciliationScriptRef") or "",
        "deltaDataPolicy": references.get("deltaDataPolicyRef") or "",
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


def _montar_janela(references):
    start_value = references.get("windowStart") or ""
    end_value = references.get("windowEnd") or ""
    start = _parse_date_safe(start_value) if start_value else None
    end = _parse_date_safe(end_value) if end_value else None
    return {
        "ref": references.get("windowRef") or "",
        "start": start_value,
        "end": end_value,
        "startValid": bool(start),
        "endValid": bool(end),
        "ordered": bool(start and end and start <= end),
    }


def _parse_date_safe(value):
    try:
        return parse_date(value)
    except ValueError:
        return None


def _validar_janela(window):
    issues = []
    if not window.get("start"):
        issues.append("janela-inicio nao informado")
    elif not window.get("startValid"):
        issues.append("janela-inicio invalido")
    if not window.get("end"):
        issues.append("janela-fim nao informado")
    elif not window.get("endValid"):
        issues.append("janela-fim invalido")
    if window.get("startValid") and window.get("endValid") and not window.get("ordered"):
        issues.append("janela-inicio maior que janela-fim")
    return issues


def _validar_referencia(value, label):
    return [] if str(value or "").strip() else [f"{label} nao informado"]


def _validar_referencia_plano(value, label, *, exigir_arquivo=False):
    issues = _validar_referencia(value, label)
    if issues or not exigir_arquivo:
        return issues
    path = Path(str(value)).expanduser()
    if not path.exists() or not path.is_file():
        issues.append(f"{label} nao encontrado como arquivo")
    return issues


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
                f"arquivo JSON de evidencia PM-06 sobrescreve arquivo de plano: {key}"
            )
        if record_path and _mesmo_caminho_saida(record_path, input_path):
            issues.append(
                f"registro markdown de evidencia PM-06 sobrescreve arquivo de plano: {key}"
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


def _montar_decisao_rollback_conciliacao(ready, issues):
    return {
        "status": "approved" if ready else "blocked",
        "step": "PM-06",
        "mayUseForCleanupMigrationGate": bool(ready),
        "mayExecuteRollback": False,
        "mayExecuteConciliation": False,
        "executionPolicy": (
            "Este gate apenas valida planos. Executar rollback ou conciliacao "
            "exige janela operacional explicita e comando/procedimento proprio."
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


def _registro_rollback_conciliacao_pm06(resultado):
    decision = resultado["rollbackConciliationDecision"]
    window = resultado["window"]
    lines = [
        "### Registro PM-06 - rollback e conciliacao da janela",
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
            f"mayUseForCleanupMigrationGate={decision['mayUseForCleanupMigrationGate']}; "
            f"mayExecuteRollback={decision['mayExecuteRollback']}; "
            f"mayExecuteConciliation={decision['mayExecuteConciliation']}"
        ),
        (
            "Janela: "
            f"ref={window['ref'] or '-'}; "
            f"inicio={window['start'] or '-'}; "
            f"fim={window['end'] or '-'}"
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
        return f"rollback/conciliacao PM-06 nao aprovado: {resultado['issues'][0]}"
    return "rollback/conciliacao PM-06 nao aprovado"
