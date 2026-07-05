import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.auditar_totais_negocio import auditar_totais_negocio
from caixa.serializers_dashboard import montar_payload_dashboard_financial_overview_api
from caixa.serializers_lancamentos import montar_payload_lancamentos_financeiros_api
from caixa.serializers_mes_financeiro import montar_payload_mes_financeiro_api
from caixa.serializers_modelagem_canonica import (
    montar_payload_baixas_financeiras_canonicas_api,
)
from caixa.serializers_obrigacoes import montar_payload_obrigacoes_financeiras_api
from caixa.utils_periodos import (
    intervalo_periodo_frontend,
    normalizar_intervalo_datas,
    normalizar_periodo_frontend,
    normalizar_periodo_rapido,
)
from caixa.utils_request import normalizar_data_iso
from tenancy.command_guards import ensure_tenant_schema


PM05_STEP = "PM-05.2"
DEFAULT_BASELINE_JSON = "pm05-auditoria-totais-negocio.json"
DEFAULT_OUTPUT_JSON = "pm05-recortes-reais.json"
DEFAULT_OUTPUT_RECORD = "pm05-recortes-reais.md"
FLUXOS = ("fco", "fci", "fcf")


class Command(BaseCommand):
    help = (
        "Valida, de forma read-only, os recortes reais PM-05.2 apos baseline "
        "canonico aprovado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help="Diretorio PM-05 usado para carregar baseline e salvar recortes.",
        )
        parser.add_argument("--baseline-json", default="")
        parser.add_argument("--salvar-json", "--save-json", default="")
        parser.add_argument("--salvar-registro", "--save-record", default="")
        parser.add_argument("--period", default="")
        parser.add_argument("--periodo-rapido", default="")
        parser.add_argument("--data-inicial", "--start-date", default="")
        parser.add_argument("--data-final", "--end-date", default="")
        parser.add_argument("--event-id", "--evento-id", default="")
        parser.add_argument("--client-id", "--cliente-id", default="")
        parser.add_argument("--contract-code", "--contrato-codigo", default="")
        parser.add_argument("--cost-center-id", "--centro-custo-id", default="")
        parser.add_argument("--source", "--origem", default="")
        parser.add_argument(
            "--cash-flow-group",
            "--fluxo",
            dest="cash_flow_group",
            default="",
        )
        parser.add_argument("--obligation-type", "--tipo-obrigacao", default="")
        parser.add_argument("--nature", "--natureza", default="")
        parser.add_argument("--status", default="")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument(
            "--exigir-baseline",
            action="store_true",
            help="Reprova se a evidencia PM-05.1 de auditoria de totais faltar.",
        )
        parser.add_argument(
            "--exigir-canonico",
            action="store_true",
            default=False,
            help="Reprova quando recortes operacionais cairem para legado.",
        )
        parser.add_argument(
            "--falhar-com-diferenca-baseline",
            action="store_true",
            help="Reprova se o recorte global divergir da fotografia PM-05.1.",
        )
        parser.add_argument(
            "--exigir-itens",
            action="store_true",
            help="Reprova se o recorte principal nao retornar itens observaveis.",
        )
        parser.add_argument(
            "--exigir-amostra-filtrada",
            action="store_true",
            help="Reprova se o recorte global nao sugerir amostra filtrada real.",
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
            help="Retorna erro quando PM-05.2 nao estiver aprovada.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("validar_recortes_pm05", action="validar dados operacionais")
        evidence_files = _normalizar_arquivos_evidencia(options)
        filtros = _normalizar_filtros(options)
        baseline_payload, baseline_load_issues = _carregar_json(
            evidence_files["baselineAudit"]
        )
        resultado = validar_recortes_pm05(
            filtros,
            baseline_payload=baseline_payload,
            baseline_load_issues=baseline_load_issues,
            evidence_files=evidence_files,
            require_baseline=options["exigir_baseline"],
            require_canonical=options["exigir_canonico"],
            fail_on_baseline_difference=options["falhar_com_diferenca_baseline"],
            require_items=options["exigir_itens"],
            require_filtered_sample=options["exigir_amostra_filtrada"],
        )
        resultado["outputEvidenceFiles"] = _normalizar_arquivos_saida(options)
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_recortes_pm05(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Validacao de recortes PM-05.2 concluida.")
        self.stdout.write(f"ready={resultado['ready']}")
        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "pendente"
            self.stdout.write(f"- {check['label']}: {status}")
            for issue in check["issues"]:
                self.stdout.write(f"  - {issue}")
        filtered_sample = resultado.get("filteredSample") or {}
        if filtered_sample.get("available"):
            self.stdout.write("Amostra filtrada sugerida:")
            self.stdout.write(f"  {filtered_sample.get('command')}")


def validar_recortes_pm05(
    filtros,
    *,
    baseline_payload=None,
    baseline_load_issues=None,
    evidence_files=None,
    require_baseline=False,
    require_canonical=False,
    fail_on_baseline_difference=False,
    require_items=False,
    require_filtered_sample=False,
):
    evidence_files = evidence_files or {}
    baseline_load_issues = baseline_load_issues or []
    generated_at = timezone.now().isoformat()

    recortes = _montar_recortes(filtros)
    filtered_sample = _sugerir_recorte_filtrado(recortes["global"])
    checks = [
        _validar_baseline(
            baseline_payload,
            baseline_load_issues,
            require_baseline=require_baseline,
        ),
        _validar_recorte_global(
            recortes["global"],
            baseline_payload,
            filtros,
            fail_on_baseline_difference=fail_on_baseline_difference,
            require_canonical=require_canonical,
            require_items=require_items,
        ),
        _validar_amostra_filtrada(
            filtered_sample,
            require_filtered_sample=require_filtered_sample,
        ),
        _validar_recortes_fluxo(
            recortes["cashFlowGroups"],
            baseline_payload,
            filtros,
            fail_on_baseline_difference=fail_on_baseline_difference,
            require_canonical=require_canonical,
        ),
        _validar_opt_out_legado(recortes["legacyOptOut"]),
    ]
    issues = [issue for check in checks for issue in check["issues"]]
    ready = not issues
    pending = [check["key"] for check in checks if not check["ok"]]

    return {
        "source": "canonical_read_observation",
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
        "filters": filtros,
        "observationSummary": _resumir_observacao(recortes),
        "filteredSample": filtered_sample,
        "recortes": recortes,
        "baseline": {
            "required": require_baseline,
            "loaded": isinstance(baseline_payload, dict),
            "path": evidence_files.get("baselineAudit") or "",
            "issues": baseline_load_issues,
        },
        "evidenceFiles": evidence_files,
        "generatedAt": generated_at,
        "recommendedCommands": {
            "rerunObservation": (
                "python manage.py validar_recortes_pm05 "
                "--diretorio-evidencias=<diretorio-evidencias-pm05> "
                "--periodo-rapido=todos "
                "--exigir-baseline --exigir-canonico "
                "--falhar-com-diferenca-baseline "
                "--exigir-amostra-filtrada --json --falhar"
            ),
            "filteredObservation": (
                "python manage.py validar_recortes_pm05 "
                "--diretorio-evidencias=<diretorio-evidencias-pm05> "
                "--salvar-json=<diretorio-evidencias-pm05>/pm05-recortes-reais-filtrado.json "
                "--salvar-registro=<diretorio-evidencias-pm05>/pm05-recortes-reais-filtrado.md "
                "--event-id=<evento-id> --client-id=<cliente-id> "
                "--contract-code=<numero-contrato> --cost-center-id=<centro-custo-id> "
                "--source=<origem> --cash-flow-group=<fluxo> "
                "--obligation-type=<tipo-obrigacao> --nature=<natureza> "
                "--status=<status> --exigir-baseline --exigir-canonico "
                "--exigir-itens --json --falhar"
            ),
        },
    }


def _montar_recortes(filtros):
    global_params = _params_comuns(filtros)
    global_recorte = _montar_recorte("global", global_params, include_dashboard=True)
    cash_flow_groups = {
        fluxo: _montar_recorte(
            f"fluxo_{fluxo}",
            {
                **global_params,
                "cashFlowGroup": fluxo,
                "fluxo": fluxo,
            },
            include_dashboard=False,
        )
        for fluxo in FLUXOS
    }
    legacy_params = {
        **global_params,
        "dataSource": "legacy",
        "fonteDados": "legacy",
    }
    legacy_opt_out = {
        "key": "legacy_opt_out",
        "filters": legacy_params,
        "obligations": _payload_obrigacoes(legacy_params),
    }
    return {
        "global": global_recorte,
        "cashFlowGroups": cash_flow_groups,
        "legacyOptOut": legacy_opt_out,
    }


def _montar_recorte(key, params, *, include_dashboard):
    recorte = {
        "key": key,
        "filters": params,
        "obligations": _payload_obrigacoes(
            {
                **params,
                "dataSource": "canonical",
                "fonteDados": "canonical",
            }
        ),
        "ledger": montar_payload_lancamentos_financeiros_api(params)["data"],
        "canonicalSettlements": montar_payload_baixas_financeiras_canonicas_api(
            params
        )["data"],
    }
    if include_dashboard:
        recorte["dashboard"] = montar_payload_dashboard_financial_overview_api(
            _params_dashboard(params),
            {},
        )["data"]
        recorte["financialMonth"] = montar_payload_mes_financeiro_api(params)
        recorte["businessTotalsAudit"] = auditar_totais_negocio()
    return recorte


def _payload_obrigacoes(params):
    return montar_payload_obrigacoes_financeiras_api(params)["data"]


def _validar_baseline(payload, load_issues, *, require_baseline):
    if not isinstance(payload, dict):
        issues = list(load_issues) if require_baseline else []
        if require_baseline and not issues:
            issues.append("baseline PM-05.1 ausente")
        return _check("baselinePm051", "Baseline PM-05.1 verificado", issues)

    issues = []
    obligations = payload.get("obligations") or {}
    read_model = obligations.get("readModelStatus") or {}
    if read_model.get("dataSourceActual") != "canonical":
        issues.append("baseline.obligations.readModelStatus.dataSourceActual deve ser canonical")
    if read_model.get("canonicalReady") is not True:
        issues.append("baseline.obligations.readModelStatus.canonicalReady deve ser True")
    if _as_int(obligations.get("divergentCount")) != 0:
        issues.append("baseline.obligations.divergentCount deve ser 0")
    if not _is_zero_money(obligations.get("realizedAmountDifference")):
        issues.append("baseline.obligations.realizedAmountDifference deve ser 0.00")
    return _check("baselinePm051", "Baseline PM-05.1 verificado", issues)


def _validar_recorte_global(
    recorte,
    baseline,
    filtros,
    *,
    fail_on_baseline_difference,
    require_canonical,
    require_items,
):
    issues = []
    issues.extend(_issues_obrigacoes_canonicas(recorte["obligations"], "global"))
    issues.extend(
        _issues_ledger_vs_baixas(
            recorte["ledger"],
            recorte["canonicalSettlements"],
            "global",
        )
    )
    if _permite_comparar_dashboard_mes(filtros):
        issues.extend(_issues_dashboard(recorte.get("dashboard") or {}))
        issues.extend(
            _issues_mes_financeiro_vs_ledger(
                recorte.get("financialMonth") or {},
                recorte["ledger"],
            )
        )
    if fail_on_baseline_difference and _permite_comparar_baseline_global(filtros):
        issues.extend(_issues_baseline_vs_global(baseline, recorte))
    if require_canonical:
        issues.extend(_issues_fallback_legado(recorte["obligations"], "global"))
    if require_items:
        issues.extend(_issues_recorte_com_itens(recorte, "global"))
    return _check("globalObservation", "Recorte global observado", issues)


def _validar_amostra_filtrada(filtered_sample, *, require_filtered_sample):
    issues = []
    if require_filtered_sample and not filtered_sample.get("available"):
        issues.append(
            filtered_sample.get("reason")
            or "recorte global nao gerou amostra filtrada"
        )
    return _check("filteredSample", "Amostra filtrada sugerida", issues)


def _validar_recortes_fluxo(
    recortes,
    baseline,
    filtros,
    *,
    fail_on_baseline_difference,
    require_canonical,
):
    issues = []
    for fluxo, recorte in recortes.items():
        issues.extend(_issues_obrigacoes_canonicas(recorte["obligations"], fluxo))
        issues.extend(
            _issues_ledger_vs_baixas(
                recorte["ledger"],
                recorte["canonicalSettlements"],
                fluxo,
            )
        )
        if require_canonical:
            issues.extend(_issues_fallback_legado(recorte["obligations"], fluxo))
        if fail_on_baseline_difference and _permite_comparar_baseline_global(filtros):
            issues.extend(_issues_baseline_vs_fluxo(baseline, fluxo, recorte))
    return _check("cashFlowObservation", "Recortes FCO/FCI/FCF observados", issues)


def _validar_opt_out_legado(recorte):
    issues = []
    payload = recorte.get("obligations") or {}
    meta = payload.get("meta") or {}
    read_model = meta.get("readModelStatus") or {}
    if meta.get("dataSourceRequested") != "legacy":
        issues.append("legacyOptOut.dataSourceRequested deve ser legacy")
    if meta.get("dataSourceActual") != "legacy":
        issues.append("legacyOptOut.dataSourceActual deve ser legacy")
    if read_model and read_model.get("dataSourceActual") != "legacy":
        issues.append("legacyOptOut.readModelStatus.dataSourceActual deve ser legacy")
    return _check("legacyOptOut", "Opt-out legado continua explicito", issues)


def _issues_obrigacoes_canonicas(payload, label):
    issues = []
    meta = payload.get("meta") or {}
    summary = payload.get("summary") or {}
    read_model = meta.get("readModelStatus") or {}
    if meta.get("dataSourceRequested") != "canonical":
        issues.append(f"{label}: obrigacoes devem solicitar dataSource=canonical")
    if meta.get("dataSourceActual") != "canonical":
        issues.append(f"{label}: obrigacoes cairam para dataSource={meta.get('dataSourceActual')}")
    if read_model.get("canonicalReady") is not True:
        issues.append(f"{label}: readModelStatus.canonicalReady deve ser True")
    if _as_int(summary.get("divergentCount")) != 0:
        issues.append(f"{label}: summary.divergentCount deve ser 0")
    if not _is_zero_money(summary.get("realizedAmountDifference")):
        issues.append(f"{label}: summary.realizedAmountDifference deve ser 0.00")
    issues.extend(
        _issues_items_respeitam_filtros(
            payload,
            payload.get("filters") or meta.get("filters") or {},
            label,
            fields=(
                "eventId",
                "clientId",
                "contractCode",
                "source",
                "cashFlowGroup",
                "obligationType",
                "nature",
            ),
        )
    )
    return issues


def _issues_fallback_legado(payload, label):
    meta = payload.get("meta") or {}
    if meta.get("dataSourceActual") != "canonical":
        return [f"{label}: fallback legado bloqueia PM-05.2"]
    return []


def _issues_recorte_com_itens(recorte, label):
    total = 0
    for key in ("obligations", "ledger", "canonicalSettlements"):
        total += len((recorte.get(key) or {}).get("items") or [])
    if total <= 0:
        return [f"{label}: recorte sem itens observaveis"]
    return []


def _issues_ledger_vs_baixas(ledger_payload, baixas_payload, label):
    ledger_summary = ledger_payload.get("summary") or {}
    baixas_summary = baixas_payload.get("summary") or {}
    issues = []
    ledger_filters = ledger_payload.get("filters") or (
        ledger_payload.get("meta") or {}
    ).get("filters") or {}
    baixas_filters = baixas_payload.get("filters") or (
        baixas_payload.get("meta") or {}
    ).get("filters") or {}
    issues.extend(
        _issues_items_respeitam_filtros(
            ledger_payload,
            ledger_filters,
            f"{label}.ledger",
            fields=("eventId", "clientId", "contractCode", "source", "cashFlowGroup", "nature"),
        )
    )
    issues.extend(
        _issues_items_respeitam_filtros(
            baixas_payload,
            baixas_filters,
            f"{label}.baixas",
            fields=("eventId", "clientId", "contractCode", "source", "cashFlowGroup", "nature"),
        )
    )
    for field in ("inflowAmount", "outflowAmount", "financialResultAmount"):
        baixa_field = "financialResult" if field == "financialResultAmount" else field
        ledger_value = _money(ledger_summary.get(field))
        baixa_value = _money(baixas_summary.get(baixa_field))
        if ledger_value != baixa_value:
            issues.append(
                f"{label}: ledger.{field}={ledger_value} difere de "
                f"baixas.{baixa_field}={baixa_value}"
            )
    return issues


def _issues_items_respeitam_filtros(payload, filtros, label, *, fields):
    issues = []
    items = payload.get("items") or []
    for field in fields:
        esperado = str(filtros.get(field) or "").strip()
        if not esperado:
            continue
        for item in items:
            atual = item.get(field)
            if atual is None and field == "source":
                atual = item.get("origin") or item.get("origem")
            if atual is None and field == "nature":
                atual = item.get("natureza")
            if str(atual or "").strip() != esperado:
                issues.append(
                    f"{label}: item {item.get('id') or item.get('key') or '-'} "
                    f"tem {field}={atual or ''}, esperado {esperado}"
                )
                break
    return issues


def _issues_dashboard(payload):
    issues = []
    if not payload:
        return ["dashboard: payload ausente"]
    comparison = payload.get("realizedCashFlowComparison") or {}
    if comparison and comparison.get("equivalent") is not True:
        issues.append("dashboard: realizedCashFlowComparison.equivalent deve ser True")
    differences = comparison.get("differences") or {}
    issues.extend(_issues_diferencas_zero(differences, "dashboard"))
    return issues


def _issues_mes_financeiro_vs_ledger(month_payload, ledger_payload):
    if not month_payload:
        return ["mesFinanceiro: payload ausente"]
    issues = []
    month_flows = month_payload.get("cashFlows") or {}
    ledger_flows = ((ledger_payload.get("summary") or {}).get("cashFlows") or {})
    for fluxo in FLUXOS:
        month_flow = month_flows.get(fluxo) or {}
        ledger_flow = ledger_flows.get(fluxo) or {}
        pairs = (
            ("realizedInflowAmount", "inflowAmount"),
            ("realizedOutflowAmount", "outflowAmount"),
            ("realizedFinancialResultAmount", "financialResultAmount"),
        )
        for month_field, ledger_field in pairs:
            month_value = _money(month_flow.get(month_field))
            ledger_value = _money(ledger_flow.get(ledger_field))
            if month_value != ledger_value:
                issues.append(
                    f"mesFinanceiro.{fluxo}.{month_field}={month_value} difere "
                    f"de ledger.{fluxo}.{ledger_field}={ledger_value}"
                )
    return issues


def _issues_diferencas_zero(payload, prefix):
    issues = []
    for key, value in payload.items():
        if key == "cashFlows" and isinstance(value, dict):
            for fluxo, flow_values in value.items():
                issues.extend(_issues_diferencas_zero(flow_values, f"{prefix}.{fluxo}"))
        elif not _is_zero_money(value):
            issues.append(f"{prefix}: diferenca {key} deve ser 0")
    return issues


def _issues_baseline_vs_global(baseline, recorte):
    if not isinstance(baseline, dict):
        return ["baseline: fotografia PM-05.1 indisponivel para comparacao global"]
    issues = []
    baseline_ledger = baseline.get("ledger") or {}
    current_ledger = (recorte.get("ledger") or {}).get("summary") or {}
    pairs = (
        ("realizedInflowAmount", "inflowAmount"),
        ("realizedOutflowAmount", "outflowAmount"),
        ("realizedFinancialResult", "financialResultAmount"),
    )
    for baseline_field, current_field in pairs:
        baseline_value = _money(baseline_ledger.get(baseline_field))
        current_value = _money(current_ledger.get(current_field))
        if baseline_value != current_value:
            issues.append(
                f"baseline.global.{baseline_field}={baseline_value} difere de "
                f"recorte.global.{current_field}={current_value}"
            )
    return issues


def _issues_baseline_vs_fluxo(baseline, fluxo, recorte):
    if not isinstance(baseline, dict):
        return [f"baseline: fotografia PM-05.1 indisponivel para comparar {fluxo}"]
    baseline_flow = ((baseline.get("ledger") or {}).get("byCashFlowGroup") or {}).get(
        fluxo,
        {},
    )
    current_summary = (recorte.get("ledger") or {}).get("summary") or {}
    pairs = (
        ("inflowAmount", "inflowAmount"),
        ("outflowAmount", "outflowAmount"),
        ("financialResult", "financialResultAmount"),
    )
    issues = []
    for baseline_field, current_field in pairs:
        baseline_value = _money(baseline_flow.get(baseline_field))
        current_value = _money(current_summary.get(current_field))
        if baseline_value != current_value:
            issues.append(
                f"baseline.{fluxo}.{baseline_field}={baseline_value} difere de "
                f"recorte.{fluxo}.{current_field}={current_value}"
            )
    return issues


def _resumir_observacao(recortes):
    global_recorte = recortes["global"]
    obligations = global_recorte["obligations"]
    ledger = global_recorte["ledger"]
    settlements = global_recorte["canonicalSettlements"]
    return {
        "obligationsReadModel": (obligations.get("meta") or {}).get(
            "readModelStatus",
            {},
        ),
        "obligationsSummary": obligations.get("summary") or {},
        "ledgerSummary": ledger.get("summary") or {},
        "canonicalSettlementsSummary": settlements.get("summary") or {},
        "cashFlowGroups": {
            fluxo: {
                "ledger": recorte["ledger"].get("summary") or {},
                "canonicalSettlements": recorte["canonicalSettlements"].get("summary")
                or {},
                "obligations": recorte["obligations"].get("summary") or {},
            }
            for fluxo, recorte in recortes["cashFlowGroups"].items()
        },
    }


def _sugerir_recorte_filtrado(recorte):
    for payload_key in ("obligations", "canonicalSettlements", "ledger"):
        items = (recorte.get(payload_key) or {}).get("items") or []
        for item in items:
            filtros = _extrair_filtros_item(item)
            if filtros:
                return {
                    "available": True,
                    "sourcePayload": payload_key,
                    "filters": filtros,
                    "command": _comando_recorte_filtrado(filtros),
                }
    return {
        "available": False,
        "sourcePayload": "",
        "filters": {},
        "command": "",
        "reason": "recorte global nao retornou itens para sugerir amostra filtrada",
    }


def _extrair_filtros_item(item):
    filtros = {}
    for field in ("eventId", "clientId", "contractCode", "costCenterId"):
        value = item.get(field)
        if value:
            filtros[field] = str(value)
    source = item.get("source") or item.get("origin") or item.get("origem")
    if source:
        filtros["source"] = str(source)
    cash_flow_group = item.get("cashFlowGroup") or item.get("fluxo")
    if cash_flow_group:
        filtros["cashFlowGroup"] = str(cash_flow_group)
    obligation_type = item.get("obligationType") or item.get("tipoObrigacao")
    if obligation_type:
        filtros["obligationType"] = str(obligation_type)
    nature = item.get("nature") or item.get("natureza")
    if nature:
        filtros["nature"] = str(nature)
    return filtros


def _comando_recorte_filtrado(filtros):
    partes = [
        "python manage.py validar_recortes_pm05",
        "--diretorio-evidencias=\"$EVID_DIR\"",
        "--salvar-json=\"$EVID_DIR/pm05-recortes-reais-filtrado.json\"",
        "--salvar-registro=\"$EVID_DIR/pm05-recortes-reais-filtrado.md\"",
    ]
    mapa_cli = (
        ("eventId", "--event-id"),
        ("clientId", "--client-id"),
        ("contractCode", "--contract-code"),
        ("costCenterId", "--cost-center-id"),
        ("source", "--source"),
        ("cashFlowGroup", "--cash-flow-group"),
        ("obligationType", "--obligation-type"),
        ("nature", "--nature"),
    )
    for field, flag in mapa_cli:
        value = filtros.get(field)
        if value:
            partes.append(f"{flag}={value}")
    partes.extend(
        [
            "--exigir-baseline",
            "--exigir-canonico",
            "--exigir-itens",
            "--json",
            "--falhar",
        ]
    )
    return " ".join(partes)


def _normalizar_filtros(options):
    period = normalizar_periodo_frontend(options.get("period"))
    periodo_rapido = normalizar_periodo_rapido(options.get("periodo_rapido"))
    start_date = normalizar_data_iso(options.get("data_inicial"))
    end_date = normalizar_data_iso(options.get("data_final"))
    start_date, end_date = normalizar_intervalo_datas(start_date, end_date)
    if period and not (start_date or end_date):
        start_date, end_date = intervalo_periodo_frontend(period)
        periodo_rapido = ""
    elif start_date or end_date:
        periodo_rapido = "vencidos" if periodo_rapido == "vencidos" else ""
    else:
        periodo_rapido = periodo_rapido or "todos"

    limit = max(1, min(int(options.get("limit") or 20), 300))
    event_id = _normalizar_id(options.get("event_id"))
    cost_center_id = _normalizar_id(options.get("cost_center_id")) or event_id
    event_filter = event_id or cost_center_id
    source = str(options.get("source") or "").strip()
    cash_flow_group = str(options.get("cash_flow_group") or "").strip().lower()
    obligation_type = _normalizar_tipo_obrigacao(options.get("obligation_type"))
    nature = str(options.get("nature") or "").strip()
    return {
        "period": period,
        "periodo_rapido": periodo_rapido,
        "startDate": start_date,
        "data_inicial": start_date,
        "endDate": end_date,
        "data_final": end_date,
        "eventId": event_filter,
        "evento": event_filter,
        "evento_id": event_filter,
        "costCenterId": cost_center_id,
        "clientId": _normalizar_id(options.get("client_id")),
        "cliente": _normalizar_id(options.get("client_id")),
        "cliente_id": _normalizar_id(options.get("client_id")),
        "contractCode": str(options.get("contract_code") or "").strip(),
        "contrato_codigo": str(options.get("contract_code") or "").strip(),
        "source": source,
        "origin": source,
        "origem": source,
        "cashFlowGroup": cash_flow_group,
        "fluxo": cash_flow_group,
        "obligationType": obligation_type,
        "tipoObrigacao": obligation_type,
        "tipo_obrigacao": obligation_type,
        "nature": nature,
        "natureza": nature,
        "status": str(options.get("status") or "").strip(),
        "limit": str(limit),
    }


def _params_comuns(filtros):
    return {key: value for key, value in filtros.items() if value not in (None, "")}


def _params_dashboard(params):
    dashboard_params = dict(params)
    if params.get("eventId"):
        dashboard_params["evento"] = params["eventId"]
    if params.get("clientId"):
        dashboard_params["cliente"] = params["clientId"]
    if params.get("contractCode"):
        dashboard_params["contrato_codigo"] = params["contractCode"]
    return dashboard_params


def _permite_comparar_baseline_global(filtros):
    return not any(
        filtros.get(key)
        for key in (
            "period",
            "startDate",
            "endDate",
            "eventId",
            "costCenterId",
            "clientId",
            "contractCode",
            "source",
            "cashFlowGroup",
            "obligationType",
            "nature",
            "status",
        )
    ) and filtros.get("periodo_rapido") == "todos"


def _permite_comparar_dashboard_mes(filtros):
    return not any(
        filtros.get(key)
        for key in ("source", "cashFlowGroup", "obligationType", "nature", "status")
    )


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias") or ""
    base_path = Path(directory).expanduser() if directory else None
    baseline = options.get("baseline_json") or ""
    if not baseline and base_path:
        baseline = str(base_path / DEFAULT_BASELINE_JSON)
    return {
        "directory": directory,
        "baselineAudit": baseline,
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


def _carregar_json(path):
    if not path:
        return None, ["baseline-json nao informado"]
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


def _registro_recortes_pm05(resultado):
    summary = resultado["checksSummary"]
    checks = "; ".join(
        f"{check['key']}={'ok' if check['ok'] else 'pendente'}"
        for check in resultado["checks"]
    )
    read_model = resultado["observationSummary"]["obligationsReadModel"]
    filtered_sample = resultado.get("filteredSample") or {}
    sample_filters = _formatar_filtros_amostra(
        filtered_sample.get("filters") or {},
    )
    if filtered_sample.get("available"):
        sample_line = (
            "Amostra filtrada: "
            f"payload={filtered_sample.get('sourcePayload') or '-'}; "
            f"filtros={sample_filters or '-'}; "
            f"comando={filtered_sample.get('command') or '-'}"
        )
    else:
        sample_line = (
            "Amostra filtrada: indisponivel; "
            f"motivo={filtered_sample.get('reason') or '-'}"
        )
    return "\n".join(
        [
            "### Registro PM-05.2 - observacao de recortes reais",
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
                "Leitura de obrigacoes: "
                f"solicitada={read_model.get('dataSourceRequested') or '-'}; "
                f"efetiva={read_model.get('dataSourceActual') or '-'}; "
                f"canonicalReady={read_model.get('canonicalReady')}"
            ),
            sample_line,
            (
                "Arquivos salvos: "
                f"json={resultado['outputEvidenceFiles'].get('json') or '-'}; "
                f"registro={resultado['outputEvidenceFiles'].get('record') or '-'}"
            ),
        ]
    )


def _formatar_filtros_amostra(filtros):
    return "; ".join(f"{key}={value}" for key, value in filtros.items() if value)


def _check(key, label, issues):
    return {
        "key": key,
        "label": label,
        "ok": not issues,
        "issues": issues,
    }


def _formatar_primeira_issue(resultado):
    if not resultado.get("issues"):
        return "recortes PM-05.2 nao aprovados"
    return f"recortes PM-05.2 nao aprovados: {resultado['issues'][0]}"


def _normalizar_id(value):
    value = str(value or "").strip()
    return value if value.isdigit() else ""


def _normalizar_tipo_obrigacao(value):
    value = str(value or "").strip().lower()
    return value if value in {"pagar", "receber"} else ""


def _as_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return -1


def _is_zero_money(value):
    return _money(value) == Decimal("0.00")


def _money(value):
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.00"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("-999999999.99")
