import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.exportar_recadastro_manual_pm06 import (
    montar_pacote_recadastro_manual_pm06,
)


DEFAULT_OUTPUT_JSON = "pm06-validacao-recadastro-manual.json"
DEFAULT_OUTPUT_RECORD = "pm06-validacao-recadastro-manual.md"


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, um pacote de recadastro manual PM-06. "
        "O comando nao limpa dados, nao restaura backup e nao altera models."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--recadastro-json",
            default="",
            help="Caminho do pm06-recadastro-manual.json ja exportado.",
        )
        parser.add_argument(
            "--usar-base-atual",
            action="store_true",
            help="Monta e valida o pacote em memoria a partir da base atual.",
        )
        parser.add_argument(
            "--comparar-base-atual",
            action="store_true",
            help="Compara o JSON informado com um pacote montado da base atual.",
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
            help="Retorna erro quando o pacote ainda nao estiver pronto para recadastro manual.",
        )

    def handle(self, *args, **options):
        output_files = _normalizar_arquivos_saida(options)
        pacote, package_ref, load_issues = _carregar_pacote(options)
        current_package = (
            montar_pacote_recadastro_manual_pm06({"json": "", "markdown": ""})
            if options["comparar_base_atual"]
            else None
        )
        resultado = validar_recadastro_manual_pm06(
            pacote,
            package_ref=package_ref,
            load_issues=load_issues,
            output_files=output_files,
            require_output_files=options["exigir_arquivos_evidencia"],
            compare_current_database=options["comparar_base_atual"],
            current_package=current_package,
        )
        resultado["outputEvidenceFiles"] = output_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_recadastro_manual_pm06(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao de recadastro manual PM-06 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        decision = resultado["manualReentryDecision"]
        self.stdout.write(
            "manualReentryDecision="
            f"{decision['status']}; "
            f"mayUseForManualReentry={decision['mayUseForManualReentry']}; "
            f"mayCleanData={decision['mayCleanData']}; "
            f"mayRestoreAutomatically={decision['mayRestoreAutomatically']}"
        )
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")
        for warning in resultado["manualRiskWarnings"]:
            self.stdout.write(f"- aviso: {warning}")


def validar_recadastro_manual_pm06(
    pacote,
    *,
    package_ref="",
    load_issues=None,
    output_files=None,
    require_output_files=False,
    compare_current_database=False,
    current_package=None,
):
    pacote = pacote if isinstance(pacote, dict) else {}
    load_issues = load_issues or []
    output_files = output_files or {}
    current_database_comparison = _montar_comparacao_base_atual(
        pacote,
        current_package,
        compare_current_database,
    )

    checks = [
        _check("packageLoad", "Pacote carregado", load_issues),
        _check("identity", "Identidade do pacote", _validar_identidade(pacote)),
        _check("policy", "Politica de recadastro", _validar_politica(pacote)),
        _check("sections", "Secoes obrigatorias", _validar_secoes(pacote)),
        _check("summary", "Resumo consistente", _validar_resumo(pacote)),
        _check("budgets", "Orcamentos exportados", _validar_orcamentos(pacote)),
        _check("events", "Eventos exportados", _validar_eventos(pacote)),
        _check("fcf", "FCF exportado", _validar_fcf(pacote)),
        _check("outOfManualScope", "Fora do pacote declarado", _validar_fora_do_escopo(pacote)),
        _check(
            "currentDatabaseComparison",
            "Comparacao com base atual",
            current_database_comparison["issues"],
        ),
        _check(
            "outputEvidenceFiles",
            "Arquivos de evidencia de saida",
            _validar_arquivos_saida(output_files, require_output_files),
        ),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]
    warnings = _montar_warnings_manuais(pacote)
    decision = {
        "status": "approved" if ready else "blocked",
        "mayUseForManualReentry": ready,
        "mayCleanData": False,
        "mayRestoreAutomatically": False,
        "nextStep": (
            "Usar o pacote como guia de recadastro manual em base limpa, mantendo backup bruto separado."
            if ready
            else "Corrigir pendencias do pacote antes de qualquer limpeza ou recadastro."
        ),
    }
    return {
        "source": "pm06_manual_reentry_readiness",
        "step": "PM-06",
        "readOnly": True,
        "generatedAt": timezone.localtime().isoformat(),
        "packageRef": package_ref,
        "ready": ready,
        "issues": issues,
        "manualReentryDecision": decision,
        "checks": checks,
        "checksSummary": {
            "ready": ready,
            "total": len(checks),
            "okCount": sum(1 for check in checks if check["ok"]),
            "pending": pending,
            "pendingCount": len(pending),
            "issueCount": len(issues),
        },
        "manualRiskWarnings": warnings,
        "packageSummary": pacote.get("summary") if isinstance(pacote.get("summary"), dict) else {},
        "currentDatabaseComparison": current_database_comparison,
    }


def _carregar_pacote(options):
    package_path = str(options.get("recadastro_json") or "").strip()
    if package_path:
        path = Path(package_path)
        if not path.exists():
            return {}, package_path, [f"recadastro-json nao encontrado: {package_path}"]
        try:
            return json.loads(path.read_text(encoding="utf-8")), str(path), []
        except json.JSONDecodeError as exc:
            return {}, str(path), [f"recadastro-json invalido: {exc}"]

    if options.get("usar_base_atual"):
        return (
            montar_pacote_recadastro_manual_pm06({"json": "", "markdown": ""}),
            "current_database_snapshot",
            [],
        )

    return {}, "", ["informe --recadastro-json ou --usar-base-atual"]


def _normalizar_arquivos_saida(options):
    output_dir = str(options.get("diretorio_evidencias") or "").strip()
    json_path = str(options.get("salvar_json") or "").strip()
    record_path = str(options.get("salvar_registro") or "").strip()
    if output_dir:
        base = Path(output_dir)
        json_path = json_path or str(base / DEFAULT_OUTPUT_JSON)
        record_path = record_path or str(base / DEFAULT_OUTPUT_RECORD)
    return {
        "json": json_path,
        "markdown": record_path,
    }


def _validar_identidade(pacote):
    issues = []
    if pacote.get("source") != "pm06_manual_reentry_export":
        issues.append("source do pacote invalido")
    if pacote.get("step") != "PM-06":
        issues.append("step do pacote invalido")
    if pacote.get("readOnly") is not True:
        issues.append("pacote sem readOnly=True")
    if not str(pacote.get("generatedAt") or "").strip():
        issues.append("pacote sem generatedAt")
    return issues


def _validar_politica(pacote):
    policy = pacote.get("policy")
    if not isinstance(policy, dict):
        return ["policy ausente ou invalida"]

    issues = []
    if policy.get("rawFullBackupRequired") is not True:
        issues.append("policy sem rawFullBackupRequired=True")
    if policy.get("restoreMode") != "manual_reentry_through_new_system":
        issues.append("policy com restoreMode invalido")
    if policy.get("canonicalDataOnly") is not True:
        issues.append("policy sem canonicalDataOnly=True")
    if policy.get("reuseExistingCodeWork") is not True:
        issues.append("policy sem reuseExistingCodeWork=True")
    excluded = policy.get("excludedDerivedModels")
    if not isinstance(excluded, list) or "ObrigacaoFinanceira" not in excluded:
        issues.append("policy sem derivados excluidos documentados")
    return issues


def _validar_secoes(pacote):
    issues = []
    for key in (
        "clients",
        "services",
        "budgets",
        "events",
        "fixedCosts",
        "manualChecklist",
    ):
        if not isinstance(pacote.get(key), list):
            issues.append(f"secao {key} ausente ou invalida")

    fcf = pacote.get("fcf")
    if not isinstance(fcf, dict):
        issues.append("secao fcf ausente ou invalida")
    else:
        for key in ("creditors", "debts", "financingMovements"):
            if not isinstance(fcf.get(key), list):
                issues.append(f"secao fcf.{key} ausente ou invalida")

    if not isinstance(pacote.get("outOfManualScope"), dict):
        issues.append("secao outOfManualScope ausente ou invalida")
    return issues


def _validar_resumo(pacote):
    summary = pacote.get("summary")
    if not isinstance(summary, dict):
        return ["summary ausente ou invalido"]

    fcf = pacote.get("fcf") if isinstance(pacote.get("fcf"), dict) else {}
    budgets = _as_list(pacote.get("budgets"))
    events = _as_list(pacote.get("events"))
    expected_counts = {
        "clientsCount": len(_as_list(pacote.get("clients"))),
        "visibleContractCodesCount": len(
            {
                str(code or "").strip()
                for code in (
                    *(
                        budget.get("contractCode") or budget.get("number")
                        for budget in budgets
                    ),
                    *(
                        event.get("contractCode") or event.get("number")
                        for event in events
                    ),
                )
                if str(code or "").strip()
            }
        ),
        "budgetsCount": len(budgets),
        "approvedBudgetsCount": sum(1 for budget in budgets if budget.get("status") == "aprovado"),
        "budgetLinkedEventsCount": sum(1 for budget in budgets if budget.get("approvedEventLegacyId")),
        "budgetItemsCount": sum(len(_as_list(budget.get("items"))) for budget in budgets),
        "budgetExtraCostsCount": sum(len(_as_list(budget.get("extraCosts"))) for budget in budgets),
        "eventsCount": len(events),
        "eventServiceCostsCount": sum(len(_as_list(event.get("serviceCosts"))) for event in events),
        "eventExtraCostsCount": sum(len(_as_list(event.get("extraCosts"))) for event in events),
        "fixedCostsCount": len(_as_list(pacote.get("fixedCosts"))),
        "fcfDebtsCount": len(_as_list(fcf.get("debts"))),
        "fcfInstallmentsCount": sum(len(_as_list(debt.get("installments"))) for debt in _as_list(fcf.get("debts"))),
        "fcfFinancingMovementsCount": len(_as_list(fcf.get("financingMovements"))),
    }
    issues = []
    for key, expected in expected_counts.items():
        if summary.get(key) != expected:
            issues.append(f"{key} esperado {expected}, recebido {summary.get(key)}")

    for key in (
        "budgetSubtotalCostsAmount",
        "budgetTaxAmount",
        "budgetProfitAmount",
        "budgetSaleAmount",
        "plannedEventRevenueAmount",
        "plannedEventCostAmount",
        "fixedCostsPlannedAmount",
        "fcfDebtContractedAmount",
    ):
        if not _is_money(summary.get(key)):
            issues.append(f"{key} ausente ou invalido")
    return issues


def _validar_orcamentos(pacote):
    issues = []
    for index, budget in enumerate(_as_list(pacote.get("budgets")), start=1):
        label = f"orcamento #{index}"
        for key in ("legacyId", "number", "name", "clientLegacyId", "clientName", "eventDate", "status"):
            if budget.get(key) in (None, ""):
                issues.append(f"{label} sem {key}")
        for key in ("subtotalCostAmount", "taxAmount", "profitAmount", "saleAmount"):
            if not _is_money(budget.get(key)):
                issues.append(f"{label} com {key} invalido")
        if not isinstance(budget.get("items"), list):
            issues.append(f"{label} sem items em lista")
        if not isinstance(budget.get("extraCosts"), list):
            issues.append(f"{label} sem extraCosts em lista")
        for item_index, item in enumerate(_as_list(budget.get("items")), start=1):
            item_label = f"{label} item #{item_index}"
            for key in ("serviceLegacyId", "serviceName", "hoursPerDay", "daysCount", "peopleCount"):
                if item.get(key) in (None, ""):
                    issues.append(f"{item_label} sem {key}")
            for key in ("usedDailyAmount", "totalCostAmount", "taxAmount", "profitAmount", "saleAmount"):
                if not _is_money(item.get(key)):
                    issues.append(f"{item_label} com {key} invalido")
        for extra_index, extra in enumerate(_as_list(budget.get("extraCosts")), start=1):
            extra_label = f"{label} custo extra #{extra_index}"
            for key in ("category", "description", "dueDate"):
                if extra.get(key) in (None, ""):
                    issues.append(f"{extra_label} sem {key}")
            if not _is_money(extra.get("plannedAmount")):
                issues.append(f"{extra_label} com plannedAmount invalido")
    return issues


def _validar_eventos(pacote):
    issues = []
    for index, event in enumerate(_as_list(pacote.get("events")), start=1):
        label = f"evento #{index}"
        for key in ("legacyId", "number", "name", "clientLegacyId", "clientName", "startDate", "endDate"):
            if event.get(key) in (None, ""):
                issues.append(f"{label} sem {key}")
        for key in ("plannedRevenueAmount", "plannedCostAmount", "realizedCostAmount"):
            if not _is_money(event.get(key)):
                issues.append(f"{label} com {key} invalido")
        if not isinstance(event.get("serviceCosts"), list):
            issues.append(f"{label} sem serviceCosts em lista")
        if not isinstance(event.get("extraCosts"), list):
            issues.append(f"{label} sem extraCosts em lista")
    return issues


def _validar_fcf(pacote):
    fcf = pacote.get("fcf")
    if not isinstance(fcf, dict):
        return ["fcf ausente ou invalido"]

    issues = []
    for index, debt in enumerate(_as_list(fcf.get("debts")), start=1):
        label = f"divida FCF #{index}"
        for key in ("legacyId", "description", "creditorName", "contractDate", "contractedAmount"):
            if debt.get(key) in (None, ""):
                issues.append(f"{label} sem {key}")
        if not isinstance(debt.get("installments"), list):
            issues.append(f"{label} sem installments em lista")
    return issues


def _validar_fora_do_escopo(pacote):
    out = pacote.get("outOfManualScope")
    if not isinstance(out, dict):
        return ["outOfManualScope ausente ou invalido"]
    issues = []
    for key in (
        "receitasOperacionaisCount",
        "despesasOperacionaisCount",
        "despesasManuaisCount",
        "obrigacoesFinanceirasCount",
        "lancamentosFinanceirosCount",
        "fciInvestmentsCount",
    ):
        if not isinstance(out.get(key), int):
            issues.append(f"outOfManualScope.{key} ausente ou invalido")
    if not str(out.get("warning") or "").strip():
        issues.append("outOfManualScope sem warning")
    return issues


def _montar_comparacao_base_atual(pacote, current_package, compare_current_database):
    comparison = {
        "enabled": bool(compare_current_database),
        "compared": False,
        "issues": [],
        "differences": [],
        "packageSummary": pacote.get("summary") if isinstance(pacote.get("summary"), dict) else {},
        "currentSummary": {},
    }
    if not compare_current_database:
        return comparison
    if not isinstance(current_package, dict):
        comparison["issues"].append("base atual nao disponivel para comparacao")
        return comparison

    comparison["compared"] = True
    comparison["currentSummary"] = (
        current_package.get("summary")
        if isinstance(current_package.get("summary"), dict)
        else {}
    )
    differences = []
    differences.extend(
        _comparar_dicionario(
            "summary",
            pacote.get("summary"),
            current_package.get("summary"),
        )
    )
    differences.extend(
        _comparar_dicionario(
            "outOfManualScope",
            pacote.get("outOfManualScope"),
            current_package.get("outOfManualScope"),
            ignored_keys={"warning"},
        )
    )
    comparison["differences"] = differences
    comparison["issues"] = [
        (
            f"{difference['path']} divergente: "
            f"pacote={difference['packageValue']}; "
            f"baseAtual={difference['currentValue']}"
        )
        for difference in differences
    ]
    return comparison


def _comparar_dicionario(section, package_value, current_value, ignored_keys=None):
    ignored_keys = ignored_keys or set()
    if not isinstance(package_value, dict) or not isinstance(current_value, dict):
        return [
            {
                "path": section,
                "packageValue": _tipo_valor(package_value),
                "currentValue": _tipo_valor(current_value),
            }
        ]

    differences = []
    keys = sorted((set(package_value.keys()) | set(current_value.keys())) - ignored_keys)
    for key in keys:
        package_item = package_value.get(key)
        current_item = current_value.get(key)
        if package_item != current_item:
            differences.append(
                {
                    "path": f"{section}.{key}",
                    "packageValue": package_item,
                    "currentValue": current_item,
                }
            )
    return differences


def _tipo_valor(value):
    return type(value).__name__


def _validar_arquivos_saida(output_files, require_output_files):
    if not require_output_files:
        return []
    issues = []
    if not str(output_files.get("json") or "").strip():
        issues.append("salvar-json obrigatorio quando exigir-arquivos-evidencia")
    if not str(output_files.get("markdown") or "").strip():
        issues.append("salvar-registro obrigatorio quando exigir-arquivos-evidencia")
    if output_files.get("json") and output_files.get("markdown"):
        if Path(output_files["json"]) == Path(output_files["markdown"]):
            issues.append("json e markdown de saida nao podem usar o mesmo caminho")
    return issues


def _montar_warnings_manuais(pacote):
    warnings = []
    summary = pacote.get("summary") if isinstance(pacote.get("summary"), dict) else {}
    out = pacote.get("outOfManualScope") if isinstance(pacote.get("outOfManualScope"), dict) else {}
    if summary.get("budgetLinkedEventsCount", 0) > 0 and summary.get("eventsCount", 0) > 0:
        warnings.append(
            "ha orcamentos vinculados a eventos; no recadastro manual, aprove orcamentos somente se o evento ainda nao foi recriado."
        )
    if out.get("despesasManuaisCount", 0) > 0:
        warnings.append("ha despesas manuais fora do pacote; confira se devem ser recadastradas manualmente.")
    if out.get("fciInvestmentsCount", 0) > 0:
        warnings.append("ha investimentos FCI fora do pacote; confira se devem permanecer fora da base limpa.")
    return warnings


def _registro_recadastro_manual_pm06(resultado):
    linhas = [
        "# PM-06 - Validacao do recadastro manual",
        "",
        f"- Gerado em: {resultado['generatedAt']}",
        f"- Pacote: {resultado['packageRef'] or '-'}",
        f"- Ready: {resultado['ready']}",
        f"- Decisao: {resultado['manualReentryDecision']['status']}",
        f"- Pode usar para recadastro manual: {resultado['manualReentryDecision']['mayUseForManualReentry']}",
        f"- Pode limpar dados: {resultado['manualReentryDecision']['mayCleanData']}",
        f"- Pode restaurar automaticamente: {resultado['manualReentryDecision']['mayRestoreAutomatically']}",
        (
            "- Comparacao com base atual: "
            f"{'sim' if resultado['currentDatabaseComparison']['compared'] else 'nao'}"
        ),
        "",
        "## Checks",
    ]
    for check in resultado["checks"]:
        status = "ok" if check["ok"] else "pendente"
        linhas.append(f"- {check['label']}: {status}")
        for issue in check["issues"]:
            linhas.append(f"  - {issue}")

    if resultado["manualRiskWarnings"]:
        linhas.append("")
        linhas.append("## Avisos manuais")
        for warning in resultado["manualRiskWarnings"]:
            linhas.append(f"- {warning}")

    differences = resultado["currentDatabaseComparison"].get("differences") or []
    if differences:
        linhas.append("")
        linhas.append("## Divergencias com base atual")
        for difference in differences:
            linhas.append(
                "- "
                f"{difference['path']}: pacote={difference['packageValue']}; "
                f"baseAtual={difference['currentValue']}"
            )

    linhas.append("")
    return "\n".join(linhas)


def _salvar_resultado(resultado):
    output_files = resultado.get("outputEvidenceFiles") or {}
    json_path = output_files.get("json") or ""
    markdown_path = output_files.get("markdown") or ""
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if markdown_path:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resultado["executionRecord"]["markdown"], encoding="utf-8")


def _check(key, label, issues):
    issues = [issue for issue in issues if issue]
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


def _formatar_primeira_issue(resultado):
    for check in resultado["checks"]:
        if check["issues"]:
            return f"{check['label']}: {check['issues'][0]}"
    return "Validacao de recadastro manual PM-06 bloqueada."


def _as_list(value):
    return value if isinstance(value, list) else []


def _is_money(value):
    try:
        Decimal(str(value))
        return True
    except (InvalidOperation, TypeError, ValueError):
        return False
