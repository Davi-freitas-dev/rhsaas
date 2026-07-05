import json
from decimal import Decimal
from pathlib import Path

from django.core.management import BaseCommand
from django.utils import timezone

from caixa.models import (
    Cliente,
    DespesaOperacional,
    Evento,
    LancamentoFinanceiro,
    ObrigacaoFinanceira,
    Orcamento,
    ReceitaOperacional,
    Servico,
)
from caixa.models_custo_fixo import CustoFixo
from caixa.models_custos_extras import EventoCustoExtra
from caixa.models_dividas import Credor, DividaFinanceira
from caixa.models_fcf import FinanciamentoMovimentacao
from caixa.models_fci import Investimento
from caixa.models_servico import EventoCustoServico
from caixa.tenant_files import recadastro_dir_for_schema
from caixa.utils_financeiros import decimal_zero
from tenancy.command_guards import ensure_tenant_schema


DEFAULT_OUTPUT_JSON = "pm06-recadastro-manual.json"
DEFAULT_OUTPUT_MD = "pm06-recadastro-manual.md"


class Command(BaseCommand):
    help = (
        "Exporta um pacote read-only para recadastro manual PM-06 em base limpa. "
        "Nao restaura dados e nao inclui modelos derivados como fonte primaria."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--diretorio-saida",
            "--output-dir",
            default="",
            help="Diretorio para salvar JSON e Markdown do pacote.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Caminho do JSON de recadastro manual.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Caminho do Markdown de recadastro manual.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o payload JSON no stdout.",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Salva os arquivos e imprime apenas um resumo curto.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema(
            "exportar_recadastro_manual_pm06",
            action="exportar dados operacionais",
        )
        output_files = resolver_arquivos_saida(options)
        payload = montar_pacote_recadastro_manual_pm06(output_files)
        registro = montar_registro_markdown(payload)

        salvar_pacote(payload, registro, output_files)

        if options["json_output"]:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            return

        if options["quiet"]:
            self.stdout.write(
                "Pacote de recadastro manual PM-06 gerado: "
                f"json={output_files.get('json') or '-'}; "
                f"markdown={output_files.get('markdown') or '-'}"
            )
            return

        self.stdout.write(registro)


def resolver_arquivos_saida(options):
    output_dir = options.get("diretorio_saida") or ""
    json_path = options.get("salvar_json") or ""
    record_path = options.get("salvar_registro") or ""

    if output_dir:
        base = Path(output_dir)
    elif json_path or record_path:
        base = None
    else:
        base = recadastro_dir_for_schema()

    if base is not None:
        json_path = json_path or str(base / DEFAULT_OUTPUT_JSON)
        record_path = record_path or str(base / DEFAULT_OUTPUT_MD)

    return {
        "json": json_path,
        "markdown": record_path,
    }


def montar_pacote_recadastro_manual_pm06(output_files=None):
    output_files = output_files or {"json": "", "markdown": ""}
    eventos = list(
        Evento.objects.select_related("cliente", "orcamento")
        .prefetch_related(
            "custos_servicos__servico",
            "custos_servicos__pagamentos",
            "custos_extras__pagamentos",
            "dividas_financeiras__parcelas__pagamentos",
        )
        .order_by("data_inicio", "id")
    )
    custos_fixos = list(CustoFixo.objects.order_by("data_vencimento", "id"))
    dividas = list(
        DividaFinanceira.objects.select_related(
            "credor_cadastro",
            "evento",
            "evento__orcamento",
        )
        .prefetch_related("parcelas__pagamentos")
        .order_by("data_contratacao", "id")
    )
    financiamentos = list(
        FinanciamentoMovimentacao.objects.select_related(
            "evento",
            "evento__orcamento",
            "divida_financeira",
        ).order_by("data_prevista", "id")
    )
    orcamentos = list(
        Orcamento.objects.select_related(
            "cliente",
            "configuracao_financeira",
            "evento",
        )
        .prefetch_related(
            "itens__servico",
            "custos_extras__evento_custo_extra",
        )
        .order_by("data_evento", "id")
    )

    payload = {
        "source": "pm06_manual_reentry_export",
        "step": "PM-06",
        "readOnly": True,
        "generatedAt": timezone.localtime().isoformat(),
        "outputFiles": output_files,
        "policy": {
            "rawFullBackupRequired": True,
            "restoreMode": "manual_reentry_through_new_system",
            "canonicalDataOnly": True,
            "reuseExistingCodeWork": True,
            "excludedDerivedModels": [
                "ObrigacaoFinanceira",
                "LancamentoFinanceiro",
                "BaixaFinanceira",
                "BaixaFinanceiraAlocacao",
                "DespesaOperacional derivada de custo",
                "ReceitaOperacional derivada de evento",
                "totais salvos recalculaveis",
            ],
        },
        "summary": montar_resumo(eventos, custos_fixos, dividas, financiamentos, orcamentos),
        "clients": [serializar_cliente(cliente) for cliente in Cliente.objects.order_by("nome_razao_social", "id")],
        "services": [serializar_servico(servico) for servico in Servico.objects.order_by("nome", "id")],
        "budgets": [serializar_orcamento(orcamento) for orcamento in orcamentos],
        "events": [serializar_evento(evento) for evento in eventos],
        "fixedCosts": [serializar_custo_fixo(custo) for custo in custos_fixos],
        "fcf": {
            "creditors": [serializar_credor(credor) for credor in Credor.objects.order_by("nome", "id")],
            "debts": [serializar_divida(divida) for divida in dividas],
            "financingMovements": [
                serializar_financiamento(movimento)
                for movimento in financiamentos
            ],
        },
        "outOfManualScope": montar_fora_do_escopo(),
        "manualChecklist": [
            "Criar backup bruto completo antes de limpar qualquer dado.",
            "Guardar este JSON e o Markdown junto com o relatorio financeiro atual.",
            "Rodar validar_recadastro_manual_pm06 contra este JSON antes de limpar ou recadastrar dados.",
            "Recriar clientes, servicos, orcamentos e eventos primeiro.",
            "Recriar orcamentos e aprovar apenas quando o evento correspondente ainda nao existir na base limpa.",
            "Recriar custos por evento, custos extras, custos fixos e FCF pelo sistema novo.",
            "Recriar pagamentos/baixas somente quando existirem no pacote.",
            "Rodar sincronizacao/recalculo canonico apos o recadastro.",
            "Comparar totais do relatorio antigo com os totais da base limpa.",
        ],
    }
    return payload


def montar_resumo(eventos, custos_fixos, dividas, financiamentos, orcamentos):
    custos_servico = EventoCustoServico.objects.all()
    custos_extras = EventoCustoExtra.objects.all()
    return {
        "clientsCount": Cliente.objects.count(),
        "visibleContractCodesCount": len(
            {
                codigo
                for codigo in (
                    *(orcamento.numero for orcamento in orcamentos),
                    *(evento.contrato_codigo for evento in eventos),
                )
                if codigo
            }
        ),
        "budgetsCount": len(orcamentos),
        "approvedBudgetsCount": sum(1 for orcamento in orcamentos if orcamento.status == "aprovado"),
        "budgetLinkedEventsCount": sum(1 for orcamento in orcamentos if obter_evento_do_orcamento(orcamento)),
        "budgetItemsCount": sum(orcamento.itens.count() for orcamento in orcamentos),
        "budgetExtraCostsCount": sum(orcamento.custos_extras.count() for orcamento in orcamentos),
        "eventsCount": len(eventos),
        "eventServiceCostsCount": custos_servico.count(),
        "eventExtraCostsCount": custos_extras.count(),
        "fixedCostsCount": len(custos_fixos),
        "fcfDebtsCount": len(dividas),
        "fcfInstallmentsCount": sum(divida.parcelas.count() for divida in dividas),
        "fcfFinancingMovementsCount": len(financiamentos),
        "budgetSubtotalCostsAmount": money(sum((orcamento.subtotal_custos for orcamento in orcamentos), Decimal("0.00"))),
        "budgetTaxAmount": money(sum((orcamento.total_impostos for orcamento in orcamentos), Decimal("0.00"))),
        "budgetProfitAmount": money(sum((orcamento.total_lucro for orcamento in orcamentos), Decimal("0.00"))),
        "budgetSaleAmount": money(sum((orcamento.total_venda for orcamento in orcamentos), Decimal("0.00"))),
        "plannedEventRevenueAmount": money(sum((evento.valor_total_previsto for evento in eventos), Decimal("0.00"))),
        "plannedEventCostAmount": money(sum((evento.custo_total_previsto for evento in eventos), Decimal("0.00"))),
        "realizedEventCostAmount": money(sum((evento.custo_total_realizado for evento in eventos), Decimal("0.00"))),
        "fixedCostsPlannedAmount": money(sum((custo.valor_previsto for custo in custos_fixos), Decimal("0.00"))),
        "fixedCostsPaidAmount": money(sum((custo.valor_pago for custo in custos_fixos), Decimal("0.00"))),
        "fcfDebtContractedAmount": money(sum((divida.valor_contratado for divida in dividas), Decimal("0.00"))),
        "fcfFinancingPlannedAmount": money(sum((mov.valor_previsto for mov in financiamentos), Decimal("0.00"))),
        "fcfFinancingRealizedAmount": money(sum((mov.valor_realizado for mov in financiamentos), Decimal("0.00"))),
    }


def montar_fora_do_escopo():
    return {
        "receitasOperacionaisCount": ReceitaOperacional.objects.count(),
        "despesasOperacionaisCount": DespesaOperacional.objects.count(),
        "despesasManuaisCount": DespesaOperacional.objects.filter(
            origem=DespesaOperacional.ORIGEM_MANUAL
        ).count(),
        "obrigacoesFinanceirasCount": ObrigacaoFinanceira.objects.count(),
        "lancamentosFinanceirosCount": LancamentoFinanceiro.objects.count(),
        "fciInvestmentsCount": Investimento.objects.count(),
        "warning": (
            "Itens fora do pacote nao sao restaurados como fonte primaria. "
            "Revise contagens antes de limpar producao."
        ),
    }


def serializar_cliente(cliente):
    return {
        "legacyId": cliente.id,
        "name": cliente.nome_razao_social,
        "tradeName": cliente.nome_fantasia,
        "personType": cliente.tipo_pessoa,
        "document": cliente.cpf_cnpj,
        "phone": cliente.telefone,
        "email": cliente.email,
        "contactPerson": cliente.responsavel,
        "address": cliente.endereco,
        "notes": cliente.observacoes,
        "isActive": cliente.ativo,
    }


def serializar_servico(servico):
    return {
        "legacyId": servico.id,
        "name": servico.nome,
        "code": servico.codigo,
        "dailyRate": money(servico.diaria_padrao),
        "baseHours": servico.horas_base_diaria,
        "specialRuleEnabled": servico.usa_regra_especial,
        "isActive": servico.ativo,
    }


def serializar_orcamento(orcamento):
    evento = obter_evento_do_orcamento(orcamento)
    return {
        "legacyId": orcamento.id,
        "number": orcamento.numero,
        "contractCode": orcamento.numero,
        "name": orcamento.nome_evento,
        "clientLegacyId": orcamento.cliente_id,
        "clientName": orcamento.cliente.nome_razao_social,
        "configurationLegacyId": orcamento.configuracao_financeira_id,
        "configurationName": orcamento.configuracao_financeira.nome,
        "eventDate": date_value(orcamento.data_evento),
        "location": orcamento.local,
        "validUntil": date_value(orcamento.validade),
        "status": orcamento.status,
        "notes": orcamento.observacoes,
        "subtotalCostAmount": money(orcamento.subtotal_custos),
        "taxAmount": money(orcamento.total_impostos),
        "profitAmount": money(orcamento.total_lucro),
        "saleAmount": money(orcamento.total_venda),
        "approvedEventLegacyId": evento.id if evento else None,
        "approvedEventNumber": evento.numero if evento else "",
        "items": [
            serializar_item_orcamento(item)
            for item in orcamento.itens.all()
        ],
        "extraCosts": [
            serializar_custo_extra_orcamento(custo)
            for custo in orcamento.custos_extras.all()
        ],
    }


def serializar_item_orcamento(item):
    return {
        "legacyId": item.id,
        "serviceLegacyId": item.servico_id,
        "serviceName": item.servico.nome,
        "serviceCode": item.servico.codigo,
        "hoursPerDay": item.horas_por_dia,
        "daysCount": item.quantidade_dias,
        "peopleCount": item.quantidade_pessoas,
        "usedDailyAmount": money(item.valor_diaria_usada),
        "usedMealAmount": money(item.valor_alimentacao_usado),
        "usedTransportAmount": money(item.valor_transporte_usado),
        "usedProfitMargin": money(item.margem_lucro_usada),
        "usedTaxRate": money(item.aliquota_imposto_usada),
        "specialRuleEnabled": item.usa_regra_especial,
        "dayAmountPerPerson": money(item.valor_dia_por_pessoa),
        "mealsPerDayCount": item.quantidade_alimentacao_por_dia,
        "transportPerDayCount": item.quantidade_transporte_por_dia,
        "serviceCostAmount": money(item.custo_servico_total),
        "mealCostAmount": money(item.gasto_alimentacao_total),
        "transportCostAmount": money(item.gasto_transporte_total),
        "overtimeAmount": money(item.valor_horas_extras_total),
        "totalCostAmount": money(item.custo_total),
        "amountWithMargin": money(item.valor_com_margem),
        "taxAmount": money(item.valor_imposto),
        "profitAmount": money(item.lucro),
        "saleAmount": money(item.preco_venda),
    }


def serializar_custo_extra_orcamento(custo):
    custo_evento = custo.evento_custo_extra
    return {
        "legacyId": custo.id,
        "category": custo.categoria,
        "categoryLabel": custo.get_categoria_display(),
        "description": custo.descricao,
        "plannedAmount": money(custo.valor_previsto),
        "dueDate": date_value(custo.data_vencimento),
        "eventExtraCostLegacyId": custo_evento.id if custo_evento else None,
        "eventLegacyId": custo_evento.evento_id if custo_evento else None,
        "notes": custo.observacao,
    }


def serializar_evento(evento):
    return {
        "legacyId": evento.id,
        "number": evento.numero,
        "contractCode": evento.contrato_codigo,
        "name": evento.nome_evento,
        "clientLegacyId": evento.cliente_id,
        "clientName": evento.cliente.nome_razao_social,
        "startDate": date_value(evento.data_inicio),
        "endDate": date_value(evento.data_fim),
        "location": evento.local,
        "status": evento.status,
        "notes": evento.observacoes,
        "plannedRevenueAmount": money(evento.valor_total_previsto),
        "plannedCostAmount": money(evento.custo_total_previsto),
        "plannedProfitAmount": money(evento.lucro_previsto),
        "realizedRevenueAmount": money(evento.valor_total_realizado),
        "realizedCostAmount": money(evento.custo_total_realizado),
        "realizedProfitAmount": money(evento.lucro_realizado),
        "serviceCosts": [
            serializar_custo_servico(custo)
            for custo in evento.custos_servicos.all()
        ],
        "extraCosts": [
            serializar_custo_extra(custo)
            for custo in evento.custos_extras.all()
        ],
    }


def serializar_custo_servico(custo):
    return {
        "legacyId": custo.id,
        "serviceLegacyId": custo.servico_id,
        "serviceName": custo.servico.nome,
        "dailyAmount": money(custo.valor_diarias),
        "mealAmount": money(custo.valor_alimentacao),
        "transportAmount": money(custo.valor_transporte),
        "totalAmount": money(custo.total),
        "paidDailyAmount": money(custo.total_pago_diarias),
        "paidMealAmount": money(custo.total_pago_alimentacao),
        "paidTransportAmount": money(custo.total_pago_transporte),
        "pendingAmount": money(custo.valor_pendente_pagamento),
        "dailyClosed": custo.diarias_quitadas,
        "mealClosed": custo.alimentacao_quitada,
        "transportClosed": custo.transporte_quitado,
        "writeOffReason": custo.motivo_baixa,
        "notes": custo.observacao,
        "payments": [
            {
                "legacyId": pagamento.id,
                "type": pagamento.tipo,
                "description": pagamento.descricao,
                "paidAmount": money(pagamento.valor_pagamento),
                "paymentDate": date_value(pagamento.data_pagamento),
                "notes": pagamento.observacao,
            }
            for pagamento in custo.pagamentos.all()
        ],
    }


def serializar_custo_extra(custo):
    return {
        "legacyId": custo.id,
        "category": custo.categoria,
        "categoryLabel": custo.get_categoria_display(),
        "description": custo.descricao,
        "plannedAmount": money(custo.valor_previsto),
        "paidAmount": money(custo.valor_pago),
        "totalPaidAmount": money(custo.total_pago),
        "pendingAmount": money(custo.valor_pendente_pagamento),
        "dueDate": date_value(custo.data_vencimento),
        "closed": custo.quitado,
        "writeOffReason": custo.motivo_baixa,
        "notes": custo.observacao,
        "payments": [
            {
                "legacyId": pagamento.id,
                "description": pagamento.descricao,
                "paidAmount": money(pagamento.valor_pagamento),
                "paymentDate": date_value(pagamento.data_pagamento),
                "notes": pagamento.observacao,
            }
            for pagamento in custo.pagamentos.all()
        ],
    }


def serializar_custo_fixo(custo):
    return {
        "legacyId": custo.id,
        "description": custo.descricao,
        "category": custo.categoria,
        "categoryLabel": custo.get_categoria_display(),
        "plannedAmount": money(custo.valor_previsto),
        "paidAmount": money(custo.valor_pago),
        "pendingAmount": money(custo.valor_pendente_pagamento),
        "dueDate": date_value(custo.data_vencimento),
        "paymentDate": date_value(custo.data_pagamento),
        "status": custo.status,
        "closedManually": custo.baixado_manualmente,
        "writeOffReason": custo.motivo_baixa,
        "notes": custo.observacao,
        "isActive": custo.ativo,
        "isRecurring": custo.recorrente,
        "monthsCount": custo.quantidade_meses,
        "parentLegacyId": custo.custo_pai_id,
        "generatedAutomatically": custo.gerado_automaticamente,
    }


def serializar_credor(credor):
    return {
        "legacyId": credor.id,
        "name": credor.nome,
        "document": credor.documento,
        "isActive": credor.ativo,
        "notes": credor.observacao,
    }


def serializar_divida(divida):
    return {
        "legacyId": divida.id,
        "description": divida.descricao,
        "creditorLegacyId": divida.credor_cadastro_id,
        "creditorName": divida.credor,
        "type": divida.tipo,
        "contractDate": date_value(divida.data_contratacao),
        "contractedAmount": money(divida.valor_contratado),
        "monthlyInterestRate": money(divida.taxa_juros_mensal, places=4),
        "installmentsCount": divida.quantidade_parcelas,
        "dueDay": divida.dia_vencimento,
        "eventLegacyId": divida.evento_id,
        "status": divida.status,
        "notes": divida.observacao,
        "pendingAmount": money(divida.saldo_devedor),
        "installments": [
            {
                "legacyId": parcela.id,
                "number": parcela.numero_parcela,
                "label": parcela.rotulo_parcela,
                "originalDueDate": date_value(parcela.data_vencimento_original),
                "currentDueDate": date_value(parcela.data_vencimento_atual),
                "principalAmount": money(parcela.valor_principal),
                "interestAmount": money(parcela.valor_juros),
                "fineAmount": money(parcela.valor_multa),
                "discountAmount": money(parcela.valor_desconto),
                "totalDueAmount": money(parcela.valor_total_devido),
                "paidAmount": money(parcela.valor_pago),
                "pendingAmount": money(parcela.valor_pendente_pagamento),
                "status": parcela.status,
                "closedManually": parcela.baixado_manualmente,
                "writeOffReason": parcela.motivo_baixa,
                "notes": parcela.observacao,
                "payments": [
                    {
                        "legacyId": pagamento.id,
                        "paidAmount": money(pagamento.valor_pagamento),
                        "paymentDate": date_value(pagamento.data_pagamento),
                        "paymentMethod": pagamento.forma_pagamento,
                        "notes": pagamento.observacao,
                    }
                    for pagamento in parcela.pagamentos.all()
                ],
            }
            for parcela in divida.parcelas.all()
        ],
    }


def serializar_financiamento(movimento):
    return {
        "legacyId": movimento.id,
        "description": movimento.descricao,
        "category": movimento.categoria,
        "categoryLabel": movimento.get_categoria_display(),
        "cashFlowType": movimento.tipo_fluxo,
        "plannedAmount": money(movimento.valor_previsto),
        "realizedAmount": money(movimento.valor_realizado),
        "pendingAmount": money(movimento.valor_pendente_realizacao),
        "plannedDate": date_value(movimento.data_prevista),
        "realizedDate": date_value(movimento.data_realizacao),
        "eventLegacyId": movimento.evento_id,
        "debtLegacyId": movimento.divida_financeira_id,
        "status": movimento.status,
        "notes": movimento.observacao,
        "isActive": movimento.ativo,
    }


def obter_evento_do_orcamento(orcamento):
    try:
        return orcamento.evento
    except Evento.DoesNotExist:
        return None


def montar_registro_markdown(payload):
    summary = payload["summary"]
    out = payload["outOfManualScope"]
    linhas = [
        "# PM-06 - Recadastro manual em base limpa",
        "",
        f"- Gerado em: {payload['generatedAt']}",
        f"- Fonte: {payload['source']}",
        "- Modo: recadastrar manualmente pelo sistema novo, mantendo backup bruto separado.",
        "- Derivados nao entram como fonte primaria: obrigacoes, lancamentos, baixas e totais recalculaveis.",
        "",
        "## Resumo",
        f"- Clientes: {summary['clientsCount']}",
        f"- Numeros de contrato visiveis: {summary['visibleContractCodesCount']}",
        f"- Orcamentos: {summary['budgetsCount']}",
        f"- Itens de orcamento: {summary['budgetItemsCount']}",
        f"- Custos extras de orcamento: {summary['budgetExtraCostsCount']}",
        f"- Eventos: {summary['eventsCount']}",
        f"- Custos por evento: {summary['eventServiceCostsCount']}",
        f"- Custos extras: {summary['eventExtraCostsCount']}",
        f"- Custos fixos: {summary['fixedCostsCount']}",
        f"- Dividas FCF: {summary['fcfDebtsCount']}",
        f"- Movimentacoes FCF: {summary['fcfFinancingMovementsCount']}",
        "",
        "## Totais Para Conferencia",
        f"- Orcamentos venda prevista: {summary['budgetSaleAmount']}",
        f"- Orcamentos custos previstos: {summary['budgetSubtotalCostsAmount']}",
        f"- Orcamentos impostos previstos: {summary['budgetTaxAmount']}",
        f"- Eventos receita prevista: {summary['plannedEventRevenueAmount']}",
        f"- Eventos custo previsto: {summary['plannedEventCostAmount']}",
        f"- Eventos custo realizado: {summary['realizedEventCostAmount']}",
        f"- Custos fixos previsto: {summary['fixedCostsPlannedAmount']}",
        f"- Custos fixos pago: {summary['fixedCostsPaidAmount']}",
        f"- FCF dividas contratadas: {summary['fcfDebtContractedAmount']}",
        "",
        "## Fora Do Pacote Manual",
        f"- Receitas operacionais: {out['receitasOperacionaisCount']}",
        f"- Despesas operacionais: {out['despesasOperacionaisCount']}",
        f"- Despesas manuais: {out['despesasManuaisCount']}",
        f"- Obrigacoes financeiras: {out['obrigacoesFinanceirasCount']}",
        f"- Lancamentos financeiros: {out['lancamentosFinanceirosCount']}",
        f"- FCI investimentos: {out['fciInvestmentsCount']}",
        "",
        "## Orcamentos",
    ]
    for orcamento in payload["budgets"]:
        evento = orcamento["approvedEventNumber"] or "-"
        linhas.extend(
            [
                f"- {orcamento['number']} | {orcamento['name']} | cliente: {orcamento['clientName']} | data: {orcamento['eventDate']} | status: {orcamento['status']}",
                f"  - Itens: {len(orcamento['items'])}; custos extras: {len(orcamento['extraCosts'])}; evento aprovado: {evento}",
            ]
        )

    linhas.extend([
        "",
        "## Eventos",
    ])
    for evento in payload["events"]:
        linhas.extend(
            [
                f"- {evento['number']} | {evento['name']} | cliente: {evento['clientName']} | data: {evento['startDate']}",
                f"  - Custos por evento: {len(evento['serviceCosts'])}; custos extras: {len(evento['extraCosts'])}",
            ]
        )

    linhas.append("")
    linhas.append("## Custos Fixos")
    for custo in payload["fixedCosts"]:
        linhas.append(
            f"- {custo['dueDate']} | {custo['description']} | previsto {custo['plannedAmount']} | pago {custo['paidAmount']} | status {custo['status']}"
        )

    linhas.append("")
    linhas.append("## FCF")
    for divida in payload["fcf"]["debts"]:
        linhas.append(
            f"- {divida['creditorName']} | {divida['description']} | contratado {divida['contractedAmount']} | parcelas {divida['installmentsCount']} | status {divida['status']}"
        )

    linhas.append("")
    linhas.append("## Checklist")
    for item in payload["manualChecklist"]:
        linhas.append(f"- [ ] {item}")

    linhas.append("")
    return "\n".join(linhas)


def salvar_pacote(payload, registro, output_files):
    json_path = output_files.get("json") or ""
    markdown_path = output_files.get("markdown") or ""

    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    if markdown_path:
        path = Path(markdown_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(registro, encoding="utf-8")


def money(value, places=2):
    quant = Decimal("1").scaleb(-places)
    return f"{decimal_zero(value).quantize(quant):.{places}f}"


def date_value(value):
    return value.isoformat() if value else ""
