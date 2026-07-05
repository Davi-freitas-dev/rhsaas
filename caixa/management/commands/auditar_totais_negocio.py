import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.utils import timezone

from caixa.constants_financeiros import (
    STATUS_REALIZADO,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from caixa.models import (
    Cliente,
    BaixaFinanceira,
    BaixaFinanceiraAlocacao,
    DespesaOperacional,
    Evento,
    LancamentoFinanceiro,
    ObrigacaoFinanceira,
    Orcamento,
    ReceitaOperacional,
)
from caixa.models_custo_fixo import CustoFixo
from caixa.models_custos_extras import EventoCustoExtra
from caixa.models_dividas import DividaFinanceira, ParcelaDivida, PagamentoParcelaDivida
from caixa.models_fcf import FinanciamentoMovimentacao
from caixa.models_fci import Investimento
from caixa.models_pagamentos import (
    PagamentoEventoCustoExtra,
    PagamentoEventoCustoServico,
)
from caixa.models_servico import EventoCustoServico
from caixa.serializers_obrigacoes import (
    formatar_status_leitura_obrigacoes,
    montar_payload_obrigacoes_financeiras_api,
    resumir_status_leitura_obrigacoes_meta,
)
from caixa.utils_financeiros import decimal_zero, quantizar_moeda
from caixa.services_valores_editaveis import (
    formatar_plano_correcao_valores_editaveis,
    resumir_integridade_valores_editaveis,
)
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Audita contagens e totais de negocio para comparacao com backup. "
        "O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime a fotografia em JSON para comparacao automatizada.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON da auditoria em um arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown da auditoria em um arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help=(
                "Diretorio opcional para gerar arquivos padronizados de "
                "evidencia da auditoria de totais."
            ),
        )
        parser.add_argument(
            "--fase-evidencia",
            "--evidence-phase",
            default="PM-03",
            help=(
                "Fase usada nos nomes padronizados de evidencia e no registro "
                "markdown. Padrao: PM-03."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os caminhos de evidencia PM-03 nao forem "
                "informados por --diretorio-evidencias ou caminhos explicitos."
            ),
        )
        parser.add_argument(
            "--falhar-com-divergencia",
            action="store_true",
            help="Retorna erro se houver divergencia entre origem e ledger nas obrigacoes.",
        )
        parser.add_argument(
            "--validar-valores-editaveis",
            action="store_true",
            help="Inclui auditoria read-only de valores editaveis na fotografia.",
        )
        parser.add_argument(
            "--falhar-com-valores-editaveis",
            action="store_true",
            help=(
                "Retorna erro quando houver valores editaveis com efeitos "
                "derivados desatualizados."
            ),
        )
        parser.add_argument(
            "--valores-editaveis-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias de valores editaveis retornadas.",
        )
        parser.add_argument(
            "--valores-editaveis-escopo",
            "--editable-values-scope",
            action="append",
            choices=["divida", "evento", "orcamento"],
            default=[],
            help="Limita a auditoria de valores editaveis a um escopo especifico.",
        )
        parser.add_argument(
            "--valores-editaveis-object-id",
            "--editable-values-object-id",
            dest="valores_editaveis_object_ids",
            action="append",
            type=int,
            default=[],
            help="Limita a auditoria de valores editaveis a um ID especifico.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("auditar_totais_negocio", action="auditar dados operacionais")
        evidence_context = _normalizar_contexto_evidencia(options.get("fase_evidencia"))
        evidence_files = _normalizar_arquivos_evidencia(options, evidence_context)
        if options["exigir_arquivos_evidencia"]:
            _exigir_arquivos_evidencia(evidence_files, evidence_context)
        fotografia = auditar_totais_negocio(
            validar_valores_editaveis=(
                options["validar_valores_editaveis"]
                or options["falhar_com_valores_editaveis"]
            ),
            valores_editaveis_limit=options["valores_editaveis_limit"],
            valores_editaveis_escopos=options["valores_editaveis_escopo"],
            valores_editaveis_object_ids=options["valores_editaveis_object_ids"],
        )
        fotografia["evidenceContext"] = evidence_context
        fotografia["evidenceFiles"] = evidence_files
        fotografia["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_auditoria_totais(fotografia),
        }
        _salvar_evidencias_auditoria(fotografia)

        if options["json_output"]:
            self.stdout.write(json.dumps(fotografia, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(fotografia)

        if (
            options["falhar_com_divergencia"]
            and fotografia["obligations"]["divergentCount"] > 0
        ):
            raise CommandError(
                f"{fotografia['obligations']['divergentCount']} divergencia(s) "
                "entre origem e ledger encontrada(s): "
                f"{formatar_primeira_divergencia_obrigacoes(fotografia['obligations'])}"
            )

        valores_editaveis = fotografia["editableValuesIntegrity"]
        if (
            options["falhar_com_valores_editaveis"]
            and valores_editaveis["checked"]
            and not valores_editaveis["consistent"]
        ):
            raise CommandError(
                f"{valores_editaveis['totalIssues']} inconsistencia(s) "
                "de valores editaveis encontrada(s): "
                f"{formatar_primeira_issue_valores_editaveis(valores_editaveis)}"
            )

    def _imprimir_relatorio(self, fotografia):
        self.stdout.write("Auditoria de totais de negocio concluida.")
        self.stdout.write(f"Gerado em: {fotografia['generatedAt']}")
        self.stdout.write("Modo: somente leitura")

        self.stdout.write("Cadastros:")
        for nome, dados in fotografia["businessTables"].items():
            self.stdout.write(f"- {nome}: {dados['count']}")

        self.stdout.write("Totais financeiros:")
        for nome, dados in fotografia["financialTotals"].items():
            valores = [
                f"{chave}={valor}"
                for chave, valor in dados.items()
                if chave != "count"
            ]
            self.stdout.write(f"- {nome}: count={dados['count']}; {'; '.join(valores)}")

        ledger = fotografia["ledger"]
        self.stdout.write(
            "Ledger: "
            f"count={ledger['count']}; "
            f"entradas={ledger['realizedInflowAmount']}; "
            f"saidas={ledger['realizedOutflowAmount']}; "
            f"resultado={ledger['realizedFinancialResult']}"
        )

        obrigacoes = fotografia["obligations"]
        self.stdout.write(
            "Obrigacoes: "
            f"count={obrigacoes['count']}; "
            f"divergencias={obrigacoes['divergentCount']}; "
            f"diferenca={obrigacoes['realizedAmountDifference']}"
        )
        leitura = obrigacoes["readModelStatus"]
        self.stdout.write(formatar_status_leitura_obrigacoes(leitura))
        self._imprimir_valores_editaveis(fotografia["editableValuesIntegrity"])

    def _imprimir_valores_editaveis(self, valores_editaveis):
        if not valores_editaveis["checked"]:
            return

        if valores_editaveis["consistent"]:
            self.stdout.write("Valores editaveis: efeitos derivados consistentes.")
            return

        self.stdout.write(
            "Valores editaveis: "
            f"{valores_editaveis['totalIssues']} inconsistencia(s)."
        )
        self._imprimir_filtros_valores_editaveis(valores_editaveis["filters"])
        resumo = valores_editaveis["summary"]
        self.stdout.write(
            "Resumo valores editaveis: "
            f"dividas={resumo['debts']}; "
            f"eventos={resumo['events']}; "
            f"orcamentosAprovados={resumo['approvedBudgets']}"
        )
        for linha in formatar_plano_correcao_valores_editaveis(
            valores_editaveis["correctionPlan"]
        ):
            self.stdout.write(linha)

    def _imprimir_filtros_valores_editaveis(self, filtros):
        escopos = filtros.get("scopes") or []
        object_ids = filtros.get("objectIds") or []
        if escopos == ["divida", "evento", "orcamento"] and not object_ids:
            return

        self.stdout.write(
            "Filtros valores editaveis: "
            f"escopos={', '.join(escopos) or '-'}; "
            f"objectIds={', '.join(str(item) for item in object_ids) or '-'}"
        )


def auditar_totais_negocio(
    validar_valores_editaveis=False,
    valores_editaveis_limit=20,
    valores_editaveis_escopos=None,
    valores_editaveis_object_ids=None,
):
    obrigacoes = montar_payload_obrigacoes_financeiras_api({"limit": "1"})["data"]
    resumo_obrigacoes = obrigacoes["summary"]
    meta_obrigacoes = obrigacoes["meta"]

    return {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "businessTables": _auditar_tabelas_negocio(),
        "financialTotals": _auditar_totais_financeiros(),
        "ledger": _auditar_ledger(),
        "obligations": {
            "count": obrigacoes["pagination"]["total"],
            "plannedAmount": _moeda(resumo_obrigacoes["plannedAmount"]),
            "originRealizedAmount": _moeda(resumo_obrigacoes["originRealizedAmount"]),
            "ledgerRealizedAmount": _moeda(resumo_obrigacoes["ledgerRealizedAmount"]),
            "pendingAmount": _moeda(resumo_obrigacoes["pendingAmount"]),
            "realizedAmountDifference": _moeda(
                resumo_obrigacoes["realizedAmountDifference"]
            ),
            "divergentCount": resumo_obrigacoes["divergentCount"],
            "reconciledCount": resumo_obrigacoes["reconciledCount"],
            "reconciliationWorklistCount": len(
                resumo_obrigacoes.get("reconciliationWorklist", [])
            ),
            "reconciliationWorklist": resumo_obrigacoes.get(
                "reconciliationWorklist",
                [],
            ),
            "readModelStatus": resumir_status_leitura_obrigacoes_meta(meta_obrigacoes),
        },
        "editableValuesIntegrity": _auditar_valores_editaveis(
            validar_valores_editaveis,
            valores_editaveis_limit,
            valores_editaveis_escopos,
            valores_editaveis_object_ids,
        ),
    }


def _auditar_valores_editaveis(validar, limit, escopos=None, object_ids=None):
    return resumir_integridade_valores_editaveis(
        validar=validar,
        limit=limit,
        escopos=escopos,
        object_ids=object_ids,
    )


def formatar_primeira_divergencia_obrigacoes(obrigacoes):
    fila = obrigacoes.get("reconciliationWorklist") or []
    if not fila:
        return "consulte o relatorio detalhado."
    item = fila[0]
    orientacao = (item.get("guidance") or {}).get("title") or "-"
    return (
        f"diagnostico={item.get('reconciliationDiagnosisLabel') or '-'} "
        f"origem={item.get('sourceLabel') or item.get('source') or '-'} "
        f"contrato={item.get('contractCode') or 'sem contrato'} "
        f"cliente={item.get('clientName') or 'sem cliente'} "
        f"itens={item.get('divergentCount') or 0} "
        f"dif={item.get('realizedAmountDifference')} "
        f"orientacao={orientacao}"
    )


def formatar_primeira_issue_valores_editaveis(valores_editaveis):
    issues = valores_editaveis.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."
    issue = issues[0]
    return (
        f"{issue['scope']}:{issue['objectId']} "
        f"{issue['code']}: {issue['message']}"
    )


def _normalizar_contexto_evidencia(raw_phase):
    phase = (raw_phase or "PM-03").strip().upper()
    if not phase:
        phase = "PM-03"
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    invalid = [char for char in phase if char not in allowed]
    if invalid:
        raise CommandError(
            "--fase-evidencia deve conter apenas letras, numeros, ponto, "
            "hifen ou sublinhado"
        )
    return {
        "phase": phase,
        "filePrefix": phase.lower().replace("-", ""),
    }


def _normalizar_arquivos_evidencia(options, evidence_context=None):
    directory = options.get("diretorio_evidencias", "")
    save_json = options.get("salvar_json", "")
    save_record = options.get("salvar_registro", "")
    file_prefix = (evidence_context or {}).get("filePrefix") or "pm03"

    if directory:
        base_path = Path(directory).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError(
                "--diretorio-evidencias deve apontar para um diretorio"
            )
        if not save_json:
            save_json = str(base_path / f"{file_prefix}-auditoria-totais-negocio.json")
        if not save_record:
            save_record = str(base_path / f"{file_prefix}-auditoria-totais-negocio.md")

    return {
        "directory": directory,
        "json": save_json,
        "record": save_record,
    }


def _exigir_arquivos_evidencia(evidence_files, evidence_context=None):
    phase = (evidence_context or {}).get("phase") or "PM-03"
    missing = [
        label
        for label, path in (
            ("json", evidence_files.get("json")),
            ("record", evidence_files.get("record")),
        )
        if not path
    ]
    if missing:
        raise CommandError(
            f"arquivos de evidencia {phase} incompletos: " + ", ".join(missing)
        )


def _salvar_evidencias_auditoria(fotografia):
    evidence_files = fotografia.get("evidenceFiles") or {}
    json_path = evidence_files.get("json")
    record_path = evidence_files.get("record")

    if json_path:
        _salvar_texto(
            json_path,
            json.dumps(fotografia, ensure_ascii=False, sort_keys=True, indent=2),
        )
    if record_path:
        _salvar_texto(record_path, fotografia["executionRecord"]["markdown"])


def _salvar_texto(path, content):
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _registro_auditoria_totais_pm03(fotografia):
    return _registro_auditoria_totais(fotografia)


def _registro_auditoria_totais(fotografia):
    ledger = fotografia["ledger"]
    obrigacoes = fotografia["obligations"]
    valores_editaveis = fotografia["editableValuesIntegrity"]
    evidence_files = fotografia.get("evidenceFiles") or {}
    evidence_context = fotografia.get("evidenceContext") or {}
    phase = evidence_context.get("phase") or "PM-03"
    evidence_summary = (
        f"diretorio={evidence_files.get('directory') or '-'}; "
        f"json={evidence_files.get('json') or '-'}; "
        f"registro={evidence_files.get('record') or '-'}"
    )

    return "\n".join(
        [
            f"### Registro {phase} - auditoria de totais de negocio",
            "",
            f"Data/hora da auditoria: {fotografia['generatedAt']}",
            f"Ledger: count={ledger['count']}; realizados={ledger['realizedCount']}",
            (
                "Ledger realizado: "
                f"entradas={ledger['realizedInflowAmount']}; "
                f"saidas={ledger['realizedOutflowAmount']}; "
                f"resultado={ledger['realizedFinancialResult']}"
            ),
            (
                "Obrigacoes: "
                f"count={obrigacoes['count']}; "
                f"divergencias={obrigacoes['divergentCount']}; "
                f"diferenca={obrigacoes['realizedAmountDifference']}"
            ),
            (
                "Leitura de obrigacoes: "
                f"{obrigacoes['readModelStatus']['label']}"
            ),
            (
                "Valores editaveis: "
                f"checked={valores_editaveis['checked']}; "
                f"consistent={valores_editaveis['consistent']}; "
                f"issues={valores_editaveis['totalIssues']}"
            ),
            f"Arquivos salvos: {evidence_summary}",
        ]
    )


def _auditar_tabelas_negocio():
    return {
        "clientes": _contagem(Cliente),
        "orcamentos": _contagem(Orcamento),
        "eventos": _contagem(Evento),
        "receitasOperacionais": _contagem(ReceitaOperacional),
        "despesasOperacionais": _contagem(DespesaOperacional),
        "custosServico": _contagem(EventoCustoServico),
        "pagamentosCustosServico": _contagem(PagamentoEventoCustoServico),
        "custosExtras": _contagem(EventoCustoExtra),
        "pagamentosCustosExtras": _contagem(PagamentoEventoCustoExtra),
        "custosFixos": _contagem(CustoFixo),
        "dividas": _contagem(DividaFinanceira),
        "parcelasDivida": _contagem(ParcelaDivida),
        "pagamentosParcelas": _contagem(PagamentoParcelaDivida),
        "investimentos": _contagem(Investimento),
        "financiamentos": _contagem(FinanciamentoMovimentacao),
        "lancamentosFinanceiros": _contagem(LancamentoFinanceiro),
        "obrigacoesFinanceirasCanonicas": _contagem(ObrigacaoFinanceira),
        "baixasFinanceirasCanonicas": _contagem(BaixaFinanceira),
        "alocacoesBaixasCanonicas": _contagem(BaixaFinanceiraAlocacao),
    }


def _auditar_totais_financeiros():
    return {
        "orcamentos": _totais_basicos(
            Orcamento,
            planned_field="total_venda",
            realized_field=None,
            extra_fields={
                "costAmount": "subtotal_custos",
                "taxAmount": "total_impostos",
                "profitAmount": "total_lucro",
            },
        ),
        "eventos": _totais_basicos(
            Evento,
            planned_field="valor_total_previsto",
            realized_field="valor_total_realizado",
            extra_fields={
                "plannedCostAmount": "custo_total_previsto",
                "realizedCostAmount": "custo_total_realizado",
                "plannedResultAmount": "lucro_previsto",
                "realizedResultAmount": "lucro_realizado",
            },
        ),
        "receitasOperacionais": _totais_basicos(
            ReceitaOperacional,
            planned_field="valor_previsto",
            realized_field="valor_recebido",
        ),
        "despesasOperacionais": _totais_basicos(
            DespesaOperacional,
            planned_field="valor_previsto",
            realized_field="valor_pago",
        ),
        "custosServico": _totais_custos_servico(),
        "pagamentosCustosServico": _totais_pagamentos(PagamentoEventoCustoServico),
        "custosExtras": _totais_basicos(
            EventoCustoExtra,
            planned_field="valor_previsto",
            realized_field="valor_pago",
        ),
        "pagamentosCustosExtras": _totais_pagamentos(PagamentoEventoCustoExtra),
        "custosFixos": _totais_basicos(
            CustoFixo,
            planned_field="valor_previsto",
            realized_field="valor_pago",
        ),
        "parcelasDivida": _totais_parcelas_divida(),
        "pagamentosParcelas": _totais_pagamentos(PagamentoParcelaDivida),
        "investimentos": _totais_basicos(
            Investimento,
            planned_field="valor_previsto",
            realized_field="valor_realizado",
        ),
        "financiamentos": _totais_basicos(
            FinanciamentoMovimentacao,
            planned_field="valor_previsto",
            realized_field="valor_realizado",
        ),
        "obrigacoesFinanceirasCanonicas": _totais_obrigacoes_canonicas(),
        "baixasFinanceirasCanonicas": _totais_baixas_canonicas(),
        "alocacoesBaixasCanonicas": _totais_alocacoes_canonicas(),
    }


def _auditar_ledger():
    realizados = LancamentoFinanceiro.objects.filter(status=STATUS_REALIZADO)
    entradas = _somar(realizados.filter(tipo=TIPO_FLUXO_ENTRADA), "valor")
    saidas = _somar(realizados.filter(tipo=TIPO_FLUXO_SAIDA), "valor")

    return {
        "count": LancamentoFinanceiro.objects.count(),
        "realizedCount": realizados.count(),
        "realizedInflowAmount": _moeda(entradas),
        "realizedOutflowAmount": _moeda(saidas),
        "realizedFinancialResult": _moeda(entradas - saidas),
        "byCashFlowGroup": {
            fluxo: _auditar_ledger_fluxo(realizados, fluxo)
            for fluxo in ("fco", "fci", "fcf")
        },
    }


def _auditar_ledger_fluxo(queryset, fluxo):
    filtrado = queryset.filter(fluxo=fluxo)
    entradas = _somar(filtrado.filter(tipo=TIPO_FLUXO_ENTRADA), "valor")
    saidas = _somar(filtrado.filter(tipo=TIPO_FLUXO_SAIDA), "valor")
    return {
        "count": filtrado.count(),
        "inflowAmount": _moeda(entradas),
        "outflowAmount": _moeda(saidas),
        "financialResult": _moeda(entradas - saidas),
    }


def _totais_basicos(modelo, planned_field, realized_field, extra_fields=None):
    planned = _somar(modelo.objects.all(), planned_field)
    realized = _somar(modelo.objects.all(), realized_field) if realized_field else None
    dados = {
        "count": modelo.objects.count(),
        "plannedAmount": _moeda(planned),
    }
    if realized is not None:
        dados["realizedAmount"] = _moeda(realized)
        dados["pendingGrossAmount"] = _moeda(planned - realized)

    for chave, campo in (extra_fields or {}).items():
        dados[chave] = _moeda(_somar(modelo.objects.all(), campo))

    return dados


def _totais_custos_servico():
    queryset = EventoCustoServico.objects.all()
    diarias = _somar(queryset, "valor_diarias")
    alimentacao = _somar(queryset, "valor_alimentacao")
    transporte = _somar(queryset, "valor_transporte")
    planned = diarias + alimentacao + transporte
    paid = _somar(PagamentoEventoCustoServico.objects.all(), "valor_pagamento")
    return {
        "count": queryset.count(),
        "plannedAmount": _moeda(planned),
        "realizedAmount": _moeda(paid),
        "pendingGrossAmount": _moeda(planned - paid),
        "dailyAmount": _moeda(diarias),
        "foodAmount": _moeda(alimentacao),
        "transportAmount": _moeda(transporte),
    }


def _totais_parcelas_divida():
    queryset = ParcelaDivida.objects.all()
    principal = _somar(queryset, "valor_principal")
    juros = _somar(queryset, "valor_juros")
    multa = _somar(queryset, "valor_multa")
    desconto = _somar(queryset, "valor_desconto")
    planned = principal + juros + multa - desconto
    realized = _somar(queryset, "valor_pago")
    return {
        "count": queryset.count(),
        "plannedAmount": _moeda(planned),
        "realizedAmount": _moeda(realized),
        "pendingGrossAmount": _moeda(planned - realized),
        "principalAmount": _moeda(principal),
        "interestAmount": _moeda(juros),
        "fineAmount": _moeda(multa),
        "discountAmount": _moeda(desconto),
    }


def _totais_pagamentos(modelo):
    return {
        "count": modelo.objects.count(),
        "realizedAmount": _moeda(_somar(modelo.objects.all(), "valor_pagamento")),
    }


def _totais_obrigacoes_canonicas():
    queryset = ObrigacaoFinanceira.objects.all()
    return {
        "count": queryset.count(),
        "plannedAmount": _moeda(_somar(queryset, "valor_previsto")),
        "realizedAmount": _moeda(_somar(queryset, "valor_realizado")),
        "pendingAmount": _moeda(_somar(queryset, "valor_pendente")),
        "overRealizedAmount": _moeda(_somar(queryset, "valor_excedente_realizado")),
    }


def _totais_baixas_canonicas():
    queryset = BaixaFinanceira.objects.all()
    entradas = _somar(queryset.filter(tipo=TIPO_FLUXO_ENTRADA), "valor_total")
    saidas = _somar(queryset.filter(tipo=TIPO_FLUXO_SAIDA), "valor_total")
    return {
        "count": queryset.count(),
        "inflowAmount": _moeda(entradas),
        "outflowAmount": _moeda(saidas),
        "financialResult": _moeda(entradas - saidas),
    }


def _totais_alocacoes_canonicas():
    queryset = BaixaFinanceiraAlocacao.objects.all()
    return {
        "count": queryset.count(),
        "allocatedAmount": _moeda(_somar(queryset, "valor_alocado")),
        "interestAmount": _moeda(_somar(queryset, "valor_juros")),
        "fineAmount": _moeda(_somar(queryset, "valor_multa")),
        "discountAmount": _moeda(_somar(queryset, "valor_desconto")),
    }


def _contagem(modelo):
    return {"count": modelo.objects.count()}


def _somar(queryset, campo):
    if not campo:
        return quantizar_moeda(decimal_zero(None))

    total = queryset.aggregate(total=Sum(campo))["total"]
    return quantizar_moeda(decimal_zero(total))


def _moeda(valor):
    if isinstance(valor, Decimal):
        decimal = valor
    elif valor in (None, ""):
        decimal = Decimal("0.00")
    else:
        decimal = Decimal(str(valor))

    return str(quantizar_moeda(decimal))
