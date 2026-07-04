from decimal import Decimal
from datetime import date
import calendar

from django.utils import timezone

from .constants_dividas import (
    STATUS_DIVIDAS,
    STATUS_DIVIDA_ATIVA,
    STATUS_DIVIDA_QUITADA,
    STATUS_PARCELA_ABERTA,
    STATUS_PARCELA_CANCELADA,
    STATUS_PARCELA_PAGA,
    STATUS_PARCELA_PARCIAL,
    STATUS_PARCELA_VENCIDA,
    STATUS_PARCELAS,
)
from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_PAGO,
    STATUS_PENDENTE,
    STATUS_REALIZADO,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from .models import DespesaOperacional, ReceitaOperacional
from .models_custo_fixo import CustoFixo
from .models_dividas import ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .selectors_opcoes_filtros import montar_opcoes_eventos_clientes_filtro
from .utils_contratos import (
    montar_filtro_evento_por_contrato_visual,
    resolver_codigo_contrato_visual_parametros,
)
from .services_dimensoes_operacionais import (
    dados_parcela_divida_sem_lazy,
    serializar_dimensao_operacional_financeira,
)
from .services_validacao_pagamentos import saldo_caixa_disponivel
from .utils_datas import obter_periodo_rapido
from .utils_financeiros import quantizar_moeda
from .utils_fluxos_caixa import (
    calcular_saldo_inicial_fluxo_caixa,
    calcular_totais_fluxos_caixa,
)
from .utils_periodos import (
    PERIODOS_FRONTEND_PARA_RAPIDO,
    intervalo_periodo_frontend,
    normalizar_intervalo_datas,
    normalizar_periodo_frontend,
    normalizar_periodo_rapido,
)
from .utils_request import normalizar_data_iso, normalizar_mes_iso


def montar_contexto_mes_financeiro(filtros):
    filtros = resolver_filtros_mes_financeiro(filtros)
    hoje = timezone.localdate()

    (
        receitas,
        parcelas,
        despesas,
        custos_fixos,
        investimentos,
        financiamentos,
    ) = buscar_movimentos_mes(filtros)
    investimentos_saida = [
        investimento
        for investimento in investimentos
        if investimento.tipo_fluxo == TIPO_FLUXO_SAIDA
    ]
    investimentos_entrada = [
        investimento
        for investimento in investimentos
        if investimento.tipo_fluxo == TIPO_FLUXO_ENTRADA
    ]
    financiamentos_saida = [
        financiamento
        for financiamento in financiamentos
        if financiamento.tipo_fluxo == TIPO_FLUXO_SAIDA
    ]
    financiamentos_entrada = [
        financiamento
        for financiamento in financiamentos
        if financiamento.tipo_fluxo == TIPO_FLUXO_ENTRADA
    ]
    contas_a_pagar = montar_contas_a_pagar(
        parcelas,
        despesas,
        custos_fixos,
        investimentos_saida,
        financiamentos_saida,
    )
    marcar_atrasos(contas_a_pagar, hoje)
    entradas_fluxos = montar_entradas_fluxos_caixa_mes(
        investimentos_entrada,
        financiamentos_entrada,
    )
    saldo_inicial = calcular_saldo_inicial_fluxo_caixa(filtros.get("data_inicial"))
    movimentacoes = montar_movimentacoes_mes(
        receitas,
        contas_a_pagar,
        entradas_fluxos,
        saldo_inicial=saldo_inicial,
    )
    totais_fluxos_caixa = calcular_totais_fluxos_caixa(
        movimentacoes,
        saldo_inicial=saldo_inicial,
    )
    totais = calcular_totais_mes_financeiro(
        receitas,
        contas_a_pagar,
        totais_fluxos_caixa,
    )
    caixa_disponivel = calcular_caixa_disponivel_mes(filtros, totais_fluxos_caixa)

    return {
        "receitas": receitas,
        "parcelas": parcelas,
        "despesas": despesas,
        "custos_fixos": custos_fixos,
        "investimentos": investimentos,
        "investimentos_saida": investimentos_saida,
        "investimentos_entrada": investimentos_entrada,
        "financiamentos": financiamentos,
        "financiamentos_saida": financiamentos_saida,
        "financiamentos_entrada": financiamentos_entrada,
        "contas_a_pagar": contas_a_pagar,
        "entradas_fluxos": entradas_fluxos,
        "movimentacoes": movimentacoes,
        **totais_fluxos_caixa,
        **totais,
        **caixa_disponivel,
        **montar_opcoes_filtros_mes_financeiro(),
        "filtros": filtros,
    }


def calcular_caixa_disponivel_mes(filtros, totais_fluxos_caixa=None):
    data_referencia = normalizar_data_referencia_caixa(filtros.get("data_final"))
    saldo_acumulado = saldo_caixa_disponivel(data_referencia)
    saldo = (
        totais_fluxos_caixa["caixa_final_mes"]
        if totais_fluxos_caixa is not None
        else saldo_acumulado
    )

    return {
        "caixa_disponivel": saldo,
        "saldo_caixa_disponivel": saldo,
        "caixa_disponivel_acumulado": saldo_acumulado,
        "saldo_caixa_disponivel_acumulado": saldo_acumulado,
        "caixa_disponivel_data_referencia": data_referencia,
        "availableCashAmount": saldo,
        "cashAvailableAmount": saldo,
        "accumulatedAvailableCashAmount": saldo_acumulado,
        "cashAvailableUntilDate": data_referencia,
    }


def normalizar_data_referencia_caixa(valor):
    if isinstance(valor, date):
        return valor

    try:
        return date.fromisoformat(str(valor or ""))
    except ValueError:
        return None


def resolver_filtros_mes_financeiro(filtros):
    hoje = timezone.localdate()
    mes = normalizar_mes_iso(filtros.get("mes", ""))
    data_inicial = normalizar_data_iso(
        filtros.get("data_inicial") or filtros.get("startDate") or ""
    )
    data_final = normalizar_data_iso(
        filtros.get("data_final") or filtros.get("endDate") or ""
    )
    data_inicial, data_final = normalizar_intervalo_datas(data_inicial, data_final)
    periodo_frontend = normalizar_periodo_frontend(filtros.get("period"))
    periodo_rapido = normalizar_periodo_rapido(filtros.get("periodo_rapido"))

    if data_inicial or data_final:
        periodo_rapido = "vencidos" if periodo_rapido == "vencidos" else ""
    elif periodo_frontend in PERIODOS_FRONTEND_PARA_RAPIDO:
        periodo_rapido = PERIODOS_FRONTEND_PARA_RAPIDO[periodo_frontend]
    elif periodo_frontend:
        data_inicial, data_final = intervalo_periodo_frontend(periodo_frontend)
        periodo_rapido = ""
        mes = ""

    periodo_resolvido = resolver_periodo_filtros_mes_financeiro(
        mes,
        data_inicial,
        data_final,
        periodo_rapido,
        hoje,
    )
    evento = normalizar_id_filtro(
        valor_filtro_operacional(
            filtros,
            "eventId",
            "costCenterId",
            "evento_id",
            "evento",
        )
    )
    cliente = normalizar_id_filtro(
        valor_filtro_operacional(filtros, "clientId", "cliente_id", "cliente")
    )
    contrato_codigo = resolver_codigo_contrato_visual_parametros(filtros)

    return {
        **filtros,
        **periodo_resolvido,
        "period": periodo_frontend,
        "startDate": periodo_resolvido["data_inicial"],
        "endDate": periodo_resolvido["data_final"],
        "evento": evento,
        "costCenterId": evento,
        "eventId": evento,
        "evento_id": evento,
        "cliente": cliente,
        "clientId": cliente,
        "cliente_id": cliente,
        "contractCode": contrato_codigo,
        "contrato_codigo": contrato_codigo,
        "status": (filtros.get("status") or "").strip(),
        "origem": (filtros.get("origem") or "").strip(),
    }


def valor_filtro_operacional(filtros, *nomes):
    for nome in nomes:
        valor = filtros.get(nome)
        if valor not in (None, ""):
            return str(valor).strip()

    return ""


def normalizar_id_filtro(valor):
    valor = str(valor or "").strip()
    return valor if valor.isdigit() else ""


def resolver_periodo_filtros_mes_financeiro(
    mes,
    data_inicial,
    data_final,
    periodo_rapido,
    hoje=None,
):
    hoje = hoje or timezone.localdate()

    if periodo_rapido:
        periodo_inicial, periodo_final = obter_periodo_rapido(periodo_rapido)
        if periodo_inicial is not None:
            if periodo_rapido == "vencidos" and (data_inicial or data_final):
                pass
            else:
                data_inicial = periodo_inicial
                data_final = periodo_final
            if periodo_rapido == "todos":
                mes = ""
        elif data_inicial or data_final:
            periodo_rapido = ""
        else:
            periodo_rapido = ""

    if not periodo_rapido and (data_inicial or data_final):
        if not data_inicial:
            data_inicial = hoje.replace(day=1).isoformat()
        if not data_final:
            data_final = hoje.replace(
                day=calendar.monthrange(hoje.year, hoje.month)[1]
            ).isoformat()
    elif not periodo_rapido:
        if not mes:
            mes = hoje.strftime("%Y-%m")
        data_inicial, data_final = periodo_do_mes(mes)

    return {
        "mes": mes,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "periodo_rapido": periodo_rapido,
    }


def periodo_do_mes(valor_mes):
    ano, mes = [int(parte) for parte in valor_mes.split("-", 1)]
    primeiro = timezone.datetime(ano, mes, 1).date()
    ultimo = primeiro.replace(day=calendar.monthrange(ano, mes)[1])
    return primeiro.isoformat(), ultimo.isoformat()


CAMPOS_DATA_MOVIMENTOS_MES = {
    "receitas": "data_vencimento",
    "parcelas": "data_vencimento_atual",
    "despesas": "data_vencimento",
    "custos_fixos": "data_vencimento",
    "investimentos": "data_prevista",
    "financiamentos": "data_prevista",
}

STATUS_FECHADOS_VENCIDOS_MES = {
    "receitas": ["recebido", STATUS_CANCELADO],
    "parcelas": [STATUS_PARCELA_PAGA, STATUS_PARCELA_CANCELADA],
    "despesas": [STATUS_PAGO, STATUS_CANCELADO],
    "custos_fixos": [STATUS_PAGO, STATUS_CANCELADO],
    "investimentos": [STATUS_REALIZADO, STATUS_CANCELADO],
    "financiamentos": [STATUS_REALIZADO, STATUS_CANCELADO],
}

ORDENACOES_MOVIMENTOS_MES = {
    "receitas": ("data_vencimento", "evento__nome_evento", "id"),
    "parcelas": ("data_vencimento_atual", "divida__credor", "numero_parcela", "id"),
    "despesas": ("data_vencimento", "evento__nome_evento", "id"),
    "custos_fixos": ("data_vencimento", "descricao", "id"),
    "investimentos": ("data_prevista", "descricao", "id"),
    "financiamentos": ("data_prevista", "descricao", "id"),
}

ORIGEM_MES_FINANCEIRO_RECEITAS = "receitas"
ORIGEM_MES_FINANCEIRO_DIVIDAS = "dividas"

ORIGENS_MES_FINANCEIRO_FILTRO = (
    (ORIGEM_MES_FINANCEIRO_RECEITAS, "Somente receitas"),
    (ORIGEM_MES_FINANCEIRO_DIVIDAS, "Somente contas"),
)

STATUS_MES_FINANCEIRO_FILTRO = (
    (STATUS_PENDENTE, "Receita pendente"),
    ("recebido", "Receita recebida"),
    (STATUS_PARCELA_ABERTA, "Parcela aberta"),
    (STATUS_PARCELA_PARCIAL, "Parcela parcial"),
    (STATUS_PARCELA_PAGA, "Parcela paga"),
    (STATUS_PARCELA_VENCIDA, "Parcela vencida"),
    (STATUS_DIVIDA_ATIVA, "Dívida ativa"),
    (STATUS_DIVIDA_QUITADA, "Dívida quitada"),
)


def origens_mes_financeiro_para_filtro():
    return ORIGENS_MES_FINANCEIRO_FILTRO


def status_mes_financeiro_para_filtro():
    return STATUS_MES_FINANCEIRO_FILTRO


def montar_opcoes_filtros_mes_financeiro():
    return {
        **montar_opcoes_eventos_clientes_filtro(),
        "origens_mes_financeiro": origens_mes_financeiro_para_filtro(),
        "status_mes_financeiro": status_mes_financeiro_para_filtro(),
    }


def buscar_movimentos_mes(filtros):
    querysets = criar_querysets_movimentos_mes()
    querysets = aplicar_filtros_periodo_movimentos_mes(querysets, filtros)
    querysets = aplicar_filtros_relacionais_movimentos_mes(querysets, filtros)
    querysets = aplicar_filtros_status_movimentos_mes(querysets, filtros)
    querysets = aplicar_filtros_origem_movimentos_mes(querysets, filtros)

    return materializar_movimentos_mes(querysets)


def criar_querysets_movimentos_mes():
    return {
        "receitas": ReceitaOperacional.objects.select_related(
            "cliente",
            "evento",
            "evento__orcamento",
        ),
        "parcelas": ParcelaDivida.objects.select_related(
            "divida",
            "divida__evento",
            "divida__evento__cliente",
            "divida__evento__orcamento",
        ),
        "despesas": DespesaOperacional.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
        ),
        "custos_fixos": CustoFixo.objects.filter(ativo=True),
        "investimentos": Investimento.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
        ).filter(ativo=True),
        "financiamentos": FinanciamentoMovimentacao.objects.select_related(
            "evento",
            "evento__cliente",
            "evento__orcamento",
        ).filter(ativo=True),
    }


def aplicar_filtros_periodo_movimentos_mes(querysets, filtros):
    if filtros["periodo_rapido"] == "vencidos":
        hoje = timezone.localdate()
        for chave, campo_data in CAMPOS_DATA_MOVIMENTOS_MES.items():
            querysets[chave] = aplicar_filtro_vencidos_mes(
                querysets[chave],
                campo_data,
                STATUS_FECHADOS_VENCIDOS_MES[chave],
                hoje,
            )

    for chave, campo_data in CAMPOS_DATA_MOVIMENTOS_MES.items():
        querysets[chave] = aplicar_filtro_intervalo_data_mes(
            querysets[chave],
            campo_data,
            filtros["data_inicial"],
            filtros["data_final"],
        )

    return querysets


def aplicar_filtro_vencidos_mes(queryset, campo_data, status_fechados, hoje=None):
    hoje = hoje or timezone.localdate()
    return queryset.filter(**{f"{campo_data}__lt": hoje}).exclude(
        status__in=status_fechados
    )


def aplicar_filtro_intervalo_data_mes(queryset, campo_data, data_inicial, data_final):
    if data_inicial:
        queryset = queryset.filter(**{f"{campo_data}__gte": data_inicial})
    if data_final:
        queryset = queryset.filter(**{f"{campo_data}__lte": data_final})
    return queryset


def aplicar_filtros_relacionais_movimentos_mes(querysets, filtros):
    if filtros["evento"]:
        querysets["receitas"] = querysets["receitas"].filter(evento_id=filtros["evento"])
        querysets["despesas"] = querysets["despesas"].filter(
            evento_id=filtros["evento"]
        )

    if filtros["cliente"]:
        querysets["receitas"] = querysets["receitas"].filter(
            cliente_id=filtros["cliente"]
        )
        querysets["despesas"] = querysets["despesas"].filter(
            evento__cliente_id=filtros["cliente"]
        )

    if filtros["contrato_codigo"]:
        filtro_contrato = montar_filtro_evento_por_contrato_visual(
            "evento__",
            filtros["contrato_codigo"],
        )
        querysets["receitas"] = querysets["receitas"].filter(filtro_contrato)
        querysets["despesas"] = querysets["despesas"].filter(filtro_contrato)

    return querysets


def aplicar_filtros_status_movimentos_mes(querysets, filtros):
    if filtros["status"]:
        querysets["receitas"] = querysets["receitas"].filter(status=filtros["status"])
        querysets["despesas"] = querysets["despesas"].filter(status=filtros["status"])
        querysets["custos_fixos"] = querysets["custos_fixos"].filter(
            status=filtros["status"]
        )
        querysets["investimentos"] = querysets["investimentos"].filter(
            status=filtros["status"]
        )
        querysets["financiamentos"] = querysets["financiamentos"].filter(
            status=filtros["status"]
        )

        if filtros["status"] in STATUS_PARCELAS:
            querysets["parcelas"] = querysets["parcelas"].filter(
                status=filtros["status"]
            )
        elif filtros["status"] in STATUS_DIVIDAS:
            querysets["parcelas"] = querysets["parcelas"].filter(
                divida__status=filtros["status"]
            )
        else:
            querysets["parcelas"] = querysets["parcelas"].none()

    return querysets


def aplicar_filtros_origem_movimentos_mes(querysets, filtros):
    if filtros["origem"] == ORIGEM_MES_FINANCEIRO_RECEITAS:
        querysets["parcelas"] = querysets["parcelas"].none()
        querysets["despesas"] = querysets["despesas"].none()
        querysets["custos_fixos"] = querysets["custos_fixos"].none()
        querysets["investimentos"] = querysets["investimentos"].none()
        querysets["financiamentos"] = querysets["financiamentos"].none()
    elif filtros["origem"] == ORIGEM_MES_FINANCEIRO_DIVIDAS:
        querysets["receitas"] = querysets["receitas"].none()
        querysets["investimentos"] = querysets["investimentos"].filter(
            tipo_fluxo=TIPO_FLUXO_SAIDA
        )
        querysets["financiamentos"] = querysets["financiamentos"].filter(
            tipo_fluxo=TIPO_FLUXO_SAIDA
        )

    return querysets


def materializar_movimentos_mes(querysets):
    return (
        list(querysets["receitas"].order_by(*ORDENACOES_MOVIMENTOS_MES["receitas"])),
        list(querysets["parcelas"].order_by(*ORDENACOES_MOVIMENTOS_MES["parcelas"])),
        list(querysets["despesas"].order_by(*ORDENACOES_MOVIMENTOS_MES["despesas"])),
        list(
            querysets["custos_fixos"].order_by(
                *ORDENACOES_MOVIMENTOS_MES["custos_fixos"]
            )
        ),
        list(
            querysets["investimentos"].order_by(
                *ORDENACOES_MOVIMENTOS_MES["investimentos"]
            )
        ),
        list(
            querysets["financiamentos"].order_by(
                *ORDENACOES_MOVIMENTOS_MES["financiamentos"]
            )
        ),
    )


def montar_contas_a_pagar(
    parcelas,
    despesas,
    custos_fixos,
    investimentos_saida,
    financiamentos_saida=None,
):
    contas = []
    financiamentos_saida = financiamentos_saida or []

    for parcela in parcelas:
        contas.append(montar_conta_parcela_mes(parcela))

    for despesa in despesas:
        contas.append(montar_conta_despesa_mes(despesa))

    for custo_fixo in custos_fixos:
        contas.append(montar_conta_custo_fixo_mes(custo_fixo))

    for investimento in investimentos_saida:
        contas.append(montar_conta_investimento_mes(investimento))

    for financiamento in financiamentos_saida:
        contas.append(montar_conta_financiamento_mes(financiamento))

    contas.sort(key=lambda item: (item["data"], item["tipo"], item["descricao"]))

    for conta in contas:
        aplicar_aliases_conta_pendente_mes(conta)

    return contas


def aplicar_aliases_conta_pendente_mes(conta):
    conta["valor_previsto"] = conta["previsto"]
    conta["valor_pago"] = conta["pago"]
    conta["contas_pendentes"] = conta["aberto"]
    conta["valor_pendente_pagamento"] = conta["aberto"]
    return conta


def referencia_receita_mes_sem_lazy(receita):
    dimensao = serializar_dimensao_operacional_financeira(receita)
    cliente_label = dimensao["clientDisplayName"] or dimensao["clientName"]
    evento_nome = dimensao["eventName"]
    if cliente_label and evento_nome:
        return f"{cliente_label} / {evento_nome}"
    return cliente_label or evento_nome


def nome_evento_mes_sem_lazy(objeto):
    return serializar_dimensao_operacional_financeira(objeto)["eventName"]


def montar_conta_parcela_mes(parcela):
    valor_pendente = getattr(parcela, "valor_pendente_pagamento", None)
    if valor_pendente is None:
        valor_pendente = parcela.saldo_em_aberto
    dados_divida = dados_parcela_divida_sem_lazy(parcela)

    return {
        "data": parcela.data_vencimento_atual,
        "tipo": "FCF",
        "fluxo_caixa": "FCF",
        "origem": "FCF",
        "descricao": dados_divida["descricao"],
        "referencia": dados_divida["referencia"],
        "previsto": parcela.valor_total_devido,
        "pago": parcela.valor_pago,
        "aberto": valor_pendente,
        "status": parcela.status,
        "status_display": parcela.get_status_display(),
        "objeto": parcela,
        **serializar_dimensao_operacional_financeira(dados_divida["divida"]),
    }


def montar_conta_despesa_mes(despesa):
    return {
        "data": despesa.data_vencimento,
        "tipo": "Despesa",
        "fluxo_caixa": "FCO",
        "origem": "FCO",
        "descricao": despesa.descricao,
        "referencia": nome_evento_mes_sem_lazy(despesa),
        "previsto": despesa.valor_previsto,
        "pago": despesa.valor_pago,
        "aberto": despesa.saldo_a_pagar,
        "status": despesa.status,
        "status_display": despesa.get_status_display(),
        "objeto": despesa,
        **serializar_dimensao_operacional_financeira(despesa),
    }


def montar_conta_custo_fixo_mes(custo_fixo):
    valor_pendente = getattr(
        custo_fixo,
        "valor_pendente_pagamento",
        custo_fixo.saldo_em_aberto,
    )

    return {
        "data": custo_fixo.data_vencimento,
        "tipo": "Custo fixo",
        "fluxo_caixa": "FCO",
        "origem": "FCO",
        "descricao": custo_fixo.descricao,
        "referencia": custo_fixo.get_categoria_display(),
        "previsto": custo_fixo.valor_previsto,
        "pago": custo_fixo.valor_pago,
        "aberto": valor_pendente,
        "status": custo_fixo.status,
        "status_display": custo_fixo.get_status_display(),
        "objeto": custo_fixo,
        **serializar_dimensao_operacional_financeira(None),
    }


def montar_conta_investimento_mes(investimento):
    return {
        "data": investimento.data_prevista,
        "tipo": "FCI",
        "fluxo_caixa": "FCI",
        "origem": "FCI",
        "descricao": investimento.descricao,
        "referencia": investimento.get_categoria_display(),
        "previsto": investimento.valor_previsto,
        "pago": investimento.valor_realizado,
        "aberto": investimento.saldo_restante,
        "status": investimento.status,
        "status_display": investimento.get_status_display(),
        "objeto": investimento,
        **serializar_dimensao_operacional_financeira(investimento),
    }


def montar_conta_financiamento_mes(financiamento):
    return {
        "data": financiamento.data_prevista,
        "tipo": "FCF",
        "fluxo_caixa": "FCF",
        "origem": "FCF",
        "descricao": financiamento.descricao,
        "referencia": financiamento.get_categoria_display(),
        "previsto": financiamento.valor_previsto,
        "pago": financiamento.valor_realizado,
        "aberto": financiamento.saldo_restante,
        "status": financiamento.status,
        "status_display": financiamento.get_status_display(),
        "objeto": financiamento,
        **serializar_dimensao_operacional_financeira(financiamento),
    }


def marcar_atrasos(contas_a_pagar, hoje):
    for conta in contas_a_pagar:
        if conta["data"] < hoje and conta["contas_pendentes"] > Decimal("0.00"):
            conta["dias_atraso"] = (hoje - conta["data"]).days
        else:
            conta["dias_atraso"] = 0


def montar_entradas_fluxos_caixa_mes(investimentos_entrada=None, financiamentos_entrada=None):
    entradas = []
    investimentos_entrada = investimentos_entrada or []
    financiamentos_entrada = financiamentos_entrada or []

    for investimento in investimentos_entrada:
        entradas.append(montar_entrada_investimento_mes(investimento))

    for financiamento in financiamentos_entrada:
        entradas.append(montar_entrada_financiamento_mes(financiamento))

    return entradas


def montar_entrada_investimento_mes(investimento):
    return {
        "data": investimento.data_prevista,
        "tipo": "FCI",
        "fluxo_caixa": "FCI",
        "origem": "FCI",
        "descricao": investimento.descricao,
        "referencia": investimento.get_categoria_display(),
        "entrada": investimento.valor_previsto,
        "saida": Decimal("0.00"),
        "recebido": investimento.valor_realizado,
        "pago": Decimal("0.00"),
        "aberto": Decimal("0.00"),
        "status": investimento.status,
        **serializar_dimensao_operacional_financeira(investimento),
    }


def montar_entrada_financiamento_mes(financiamento):
    return {
        "data": financiamento.data_prevista,
        "tipo": financiamento.get_categoria_display(),
        "fluxo_caixa": "FCF",
        "origem": "FCF",
        "descricao": financiamento.descricao,
        "referencia": financiamento.get_categoria_display(),
        "entrada": financiamento.valor_previsto,
        "saida": Decimal("0.00"),
        "recebido": financiamento.valor_realizado,
        "pago": Decimal("0.00"),
        "aberto": Decimal("0.00"),
        "status": financiamento.status,
        **serializar_dimensao_operacional_financeira(financiamento),
    }


def montar_movimentacoes_mes(
    receitas,
    contas_a_pagar,
    entradas_fluxos=None,
    saldo_inicial=Decimal("0.00"),
):
    movimentacoes = []
    entradas_fluxos = entradas_fluxos or []

    for receita in receitas:
        movimentacoes.append(montar_movimento_receita_mes(receita))

    movimentacoes.extend(entradas_fluxos)

    for conta in contas_a_pagar:
        movimentacoes.append(montar_movimento_conta_mes(conta))

    movimentacoes.sort(key=lambda item: (item["data"], item["tipo"], item["descricao"]))

    aplicar_acumulados_movimentacoes_mes(
        movimentacoes,
        saldo_inicial=saldo_inicial,
    )
    return movimentacoes


def montar_movimento_receita_mes(receita):
    return {
        "data": receita.data_vencimento,
        "tipo": "Receita",
        "fluxo_caixa": "FCO",
        "origem": "FCO",
        "descricao": receita.descricao,
        "referencia": referencia_receita_mes_sem_lazy(receita),
        "entrada": receita.valor_previsto,
        "saida": Decimal("0.00"),
        "recebido": receita.valor_recebido,
        "pago": Decimal("0.00"),
        "aberto": Decimal("0.00"),
        "status": receita.status,
        **serializar_dimensao_operacional_financeira(receita),
    }


def montar_movimento_conta_mes(conta):
    return {
        "data": conta["data"],
        "tipo": conta["tipo"],
        "fluxo_caixa": conta.get("fluxo_caixa", conta.get("origem", "FCO")),
        "origem": conta.get("origem", conta.get("fluxo_caixa", "FCO")),
        "descricao": conta["descricao"],
        "referencia": conta["referencia"],
        "entrada": Decimal("0.00"),
        "saida": conta["previsto"],
        "recebido": Decimal("0.00"),
        "pago": conta["pago"],
        "aberto": conta["aberto"],
        "status": conta["status"],
        "contractCode": conta.get("contractCode", ""),
        "contractName": conta.get("contractName", ""),
        "contractLabel": conta.get("contractLabel", ""),
        "eventId": conta.get("eventId"),
        "eventName": conta.get("eventName", ""),
        "eventNumber": conta.get("eventNumber", ""),
        "eventLabel": conta.get("eventLabel", ""),
        "clientId": conta.get("clientId"),
        "clientName": conta.get("clientName", ""),
    }


def aplicar_acumulados_movimentacoes_mes(
    movimentacoes,
    saldo_inicial=Decimal("0.00"),
):
    saldo_inicial = quantizar_moeda(saldo_inicial)
    resultado_financeiro_previsto_acumulado = saldo_inicial
    resultado_financeiro_realizado_acumulado = saldo_inicial
    contas_pendentes_acumuladas = Decimal("0.00")

    for item in movimentacoes:
        resultado_financeiro_previsto_acumulado += item["entrada"]
        resultado_financeiro_previsto_acumulado -= item["saida"]
        resultado_financeiro_realizado_acumulado += item["recebido"]
        resultado_financeiro_realizado_acumulado -= item["pago"]
        contas_pendentes_acumuladas += item["aberto"]
        caixa_realizado_disponivel = (
            resultado_financeiro_realizado_acumulado
            if resultado_financeiro_realizado_acumulado > Decimal("0.00")
            else Decimal("0.00")
        )
        deficit_caixa_base = contas_pendentes_acumuladas - caixa_realizado_disponivel
        resultado_financeiro_acumulado = quantizar_moeda(
            resultado_financeiro_previsto_acumulado
        )
        resultado_financeiro_realizado = quantizar_moeda(
            resultado_financeiro_realizado_acumulado
        )
        deficit_caixa_acumulado = quantizar_moeda(
            deficit_caixa_base
            if deficit_caixa_base > Decimal("0.00")
            else Decimal("0.00")
        )
        item["entrada_prevista"] = item["entrada"]
        item["saida_prevista"] = item["saida"]
        item["valor_recebido"] = item["recebido"]
        item["valor_pago"] = item["pago"]
        item["contas_pendentes"] = item["aberto"]
        item["saldo_previsto_acumulado"] = resultado_financeiro_acumulado
        item["saldo_realizado_acumulado"] = resultado_financeiro_realizado
        item["falta_cobrir_acumulada"] = deficit_caixa_acumulado
        item["saldo_acumulado"] = resultado_financeiro_acumulado
        item["resultado_financeiro_acumulado"] = resultado_financeiro_acumulado
        item["resultado_financeiro_previsto_acumulado"] = resultado_financeiro_acumulado
        item["resultado_financeiro_realizado_acumulado"] = resultado_financeiro_realizado
        item["deficit_caixa_acumulado"] = deficit_caixa_acumulado

    return movimentacoes


def calcular_totais_receitas(receitas):
    receita_prevista = sum(
        (receita.valor_previsto for receita in receitas),
        Decimal("0.00"),
    )
    receita_recebida = sum(
        (receita.valor_recebido for receita in receitas),
        Decimal("0.00"),
    )
    receita_pendente = sum(
        (receita.saldo_a_receber for receita in receitas),
        Decimal("0.00"),
    )

    return {
        "receita_prevista": quantizar_moeda(receita_prevista),
        "receita_recebida": quantizar_moeda(receita_recebida),
        "receita_aberta": quantizar_moeda(receita_pendente),
        "receita_pendente_recebimento": quantizar_moeda(receita_pendente),
    }


def calcular_totais_dividas(contas_a_pagar):
    divida_prevista = sum(
        (conta["previsto"] for conta in contas_a_pagar),
        Decimal("0.00"),
    )
    divida_paga = sum(
        (conta["pago"] for conta in contas_a_pagar),
        Decimal("0.00"),
    )
    contas_pendentes = sum(
        (conta.get("contas_pendentes", conta["aberto"]) for conta in contas_a_pagar),
        Decimal("0.00"),
    )
    contas_vencidas = sum(
        (
            conta.get("contas_pendentes", conta["aberto"])
            for conta in contas_a_pagar
            if conta.get("dias_atraso", 0) > 0
        ),
        Decimal("0.00"),
    )

    return {
        "divida_prevista": quantizar_moeda(divida_prevista),
        "divida_paga": quantizar_moeda(divida_paga),
        "divida_pendente_pagamento": quantizar_moeda(contas_pendentes),
        "divida_aberta": quantizar_moeda(contas_pendentes),
        "divida_vencida": quantizar_moeda(contas_vencidas),
        "contas_previstas": quantizar_moeda(divida_prevista),
        "contas_pagas": quantizar_moeda(divida_paga),
        "contas_pendentes": quantizar_moeda(contas_pendentes),
        "contas_vencidas": quantizar_moeda(contas_vencidas),
    }


def calcular_totais_mes_financeiro(receitas, contas_a_pagar, totais_fluxos_caixa=None):
    totais_receitas = calcular_totais_receitas(receitas)
    totais_dividas = calcular_totais_dividas(contas_a_pagar)
    indicadores_fco = calcular_indicadores_fco_previstos(
        totais_receitas,
        contas_a_pagar,
    )
    resumo = calcular_resumo_financeiro_mes(
        totais_receitas,
        totais_dividas,
        totais_fluxos_caixa,
    )

    return {
        **totais_receitas,
        **totais_dividas,
        **indicadores_fco,
        **(totais_fluxos_caixa or {}),
        **resumo,
        **montar_aliases_canonicos_totais_mes_financeiro(
            totais_receitas,
            totais_dividas,
            resumo,
            indicadores_fco,
        ),
    }


def calcular_indicadores_fco_previstos(totais_receitas, contas_a_pagar):
    receita_bruta = totais_receitas["receita_prevista"]
    custo_variavel = sum(
        (
            conta["previsto"]
            for conta in contas_a_pagar
            if conta.get("origem") == "FCO" and conta.get("tipo") == "Despesa"
        ),
        Decimal("0.00"),
    )
    custo_fixo = sum(
        (
            conta["previsto"]
            for conta in contas_a_pagar
            if conta.get("origem") == "FCO" and conta.get("tipo") == "Custo fixo"
        ),
        Decimal("0.00"),
    )
    margem_contribuicao = quantizar_moeda(receita_bruta - custo_variavel)
    margem_contribuicao_percentual = (
        ((margem_contribuicao / receita_bruta) * Decimal("100")).quantize(
            Decimal("0.01")
        )
        if receita_bruta > Decimal("0.00")
        else Decimal("0.00")
    )
    lucro_operacional_ebit = quantizar_moeda(margem_contribuicao - custo_fixo)

    return {
        "custo_variavel": quantizar_moeda(custo_variavel),
        "margem_contribuicao": margem_contribuicao,
        "margem_contribuicao_percentual": margem_contribuicao_percentual,
        "lucro_operacional_ebit": lucro_operacional_ebit,
    }


def montar_aliases_canonicos_totais_mes_financeiro(
    totais_receitas,
    totais_dividas,
    resumo,
    indicadores_fco,
):
    return {
        "plannedRevenueAmount": totais_receitas["receita_prevista"],
        "receivedRevenueAmount": totais_receitas["receita_recebida"],
        "pendingReceivableAmount": totais_receitas[
            "receita_pendente_recebimento"
        ],
        "plannedPayablesAmount": totais_dividas["contas_previstas"],
        "paidPayablesAmount": totais_dividas["contas_pagas"],
        "pendingAccountsAmount": totais_dividas["contas_pendentes"],
        "overdueAccountsAmount": totais_dividas["contas_vencidas"],
        "financialResultAmount": resumo["resultado_financeiro"],
        "plannedFinancialResultAmount": resumo[
            "resultado_financeiro_previsto"
        ],
        "projectedFinancialResultAmount": resumo[
            "resultado_financeiro_projetado"
        ],
        "realizedFinancialResultAmount": resumo[
            "resultado_financeiro_realizado"
        ],
        "pendingFinancialResultAmount": resumo[
            "resultado_financeiro_pendente"
        ],
        "cashDeficitAmount": resumo["deficit_caixa"],
        "variableCostAmount": indicadores_fco["custo_variavel"],
        "contributionMarginAmount": indicadores_fco["margem_contribuicao"],
        "contributionMarginPercent": indicadores_fco[
            "margem_contribuicao_percentual"
        ],
        "operatingProfitEbitAmount": indicadores_fco[
            "lucro_operacional_ebit"
        ],
        "plannedVariableCostAmount": indicadores_fco["custo_variavel"],
        "plannedContributionMarginAmount": indicadores_fco[
            "margem_contribuicao"
        ],
        "plannedContributionMarginPercent": indicadores_fco[
            "margem_contribuicao_percentual"
        ],
        "plannedOperatingProfitEbitAmount": indicadores_fco[
            "lucro_operacional_ebit"
        ],
    }


def calcular_resumo_financeiro_mes(totais_receitas, totais_dividas, totais_fluxos_caixa=None):
    resultado_financeiro_realizado = (
        totais_fluxos_caixa["resultado_realizado_periodo"]
        if totais_fluxos_caixa is not None
        else quantizar_moeda(
            totais_receitas["receita_recebida"] - totais_dividas["divida_paga"]
        )
    )
    caixa_final_realizado = (
        totais_fluxos_caixa["caixa_final_realizado"]
        if totais_fluxos_caixa is not None
        else resultado_financeiro_realizado
    )
    caixa_realizado_disponivel = (
        caixa_final_realizado
        if caixa_final_realizado > Decimal("0.00")
        else Decimal("0.00")
    )
    contas_pendentes = totais_dividas.get(
        "contas_pendentes",
        totais_dividas.get(
            "divida_pendente_pagamento",
            totais_dividas["divida_aberta"],
        ),
    )
    deficit_caixa_base = contas_pendentes - caixa_realizado_disponivel
    resultado_financeiro = (
        totais_fluxos_caixa["resultado_previsto_periodo"]
        if totais_fluxos_caixa is not None
        else quantizar_moeda(
            totais_receitas["receita_prevista"] - totais_dividas["divida_prevista"]
        )
    )
    resultado_financeiro_pendente = quantizar_moeda(
        totais_receitas.get(
            "receita_pendente_recebimento",
            totais_receitas["receita_aberta"],
        )
        - contas_pendentes
    )
    deficit_caixa = quantizar_moeda(
        deficit_caixa_base if deficit_caixa_base > Decimal("0.00") else Decimal("0.00")
    )

    return {
        "saldo_previsto": resultado_financeiro,
        "saldo_realizado": resultado_financeiro_realizado,
        "saldo_aberto": resultado_financeiro_pendente,
        "falta_cobrir": deficit_caixa,
        "resultado_financeiro": resultado_financeiro,
        "resultado_financeiro_previsto": resultado_financeiro,
        "resultado_financeiro_projetado": resultado_financeiro,
        "resultado_financeiro_realizado": resultado_financeiro_realizado,
        "resultado_financeiro_pendente": resultado_financeiro_pendente,
        "deficit_caixa": deficit_caixa,
    }
