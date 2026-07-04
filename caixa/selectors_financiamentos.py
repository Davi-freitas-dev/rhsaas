from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from .constants_financeiros import (
    STATUS_CANCELADO,
    STATUS_REALIZADO,
    TIPO_FLUXO_ENTRADA,
    TIPO_FLUXO_SAIDA,
)
from .models_dividas import DividaFinanceira, ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .selectors_dividas import (
    filtrar_por_credor_divida,
    filtro_credor_usa_id_canonico,
    valor_filtro_credor,
)
from .selectors_opcoes_filtros import (
    listar_clientes_filtro,
    listar_contratos_visuais_filtro,
    listar_credores_cadastrados_fcf_filtro,
    listar_credores_fcf_filtro,
    listar_eventos_filtro_recentes,
    listar_status_parcelas_fcf_filtro,
    listar_tipos_divida_fcf_filtro,
)
from .selectors_pagamentos import filtrar_parcelas_disponiveis_para_pagamento
from .services_dimensoes_operacionais import relacao_carregada
from .utils_contratos import (
    montar_filtro_evento_ou_orcamento_por_contrato_visual,
    resolver_codigo_contrato_visual_parametros,
)
from .utils_financeiros import quantizar_moeda
from .utils_periodos import (
    PERIODOS_FRONTEND_PARA_RAPIDO,
    intervalo_periodo_frontend,
    normalizar_intervalo_datas,
    normalizar_periodo_frontend,
    normalizar_periodo_rapido,
    resolver_periodo_rapido_com_sessao,
)
from .utils_request import normalizar_data_iso


TIPOS_ORIGEM_MOVIMENTACAO_FINANCIAMENTO = (
    ("manual", "Movimentacao FCF manual"),
    ("divida_automatica", "Entrada automatica da divida"),
)
ORIGENS_MOVIMENTACAO_FINANCIAMENTO = {
    valor for valor, _rotulo in TIPOS_ORIGEM_MOVIMENTACAO_FINANCIAMENTO
}
TIPOS_DIVIDA_FCF = {valor for valor, _rotulo in DividaFinanceira.TIPO_CHOICES}
STATUS_FILTRO_FINANCIAMENTO = {
    valor for valor, _rotulo in ParcelaDivida.STATUS_CHOICES
} | {valor for valor, _rotulo in FinanciamentoMovimentacao.STATUS_CHOICES}
FILTROS_PERIODO_FINANCIAMENTOS = {
    "data_inicial",
    "data_final",
    "startDate",
    "endDate",
    "period",
    "quickPeriod",
    "periodo_rapido",
}


def valor_filtro_tipo_divida(filtros):
    tipo = str(filtros.get("type") or filtros.get("tipo") or "").strip()
    return tipo if tipo in TIPOS_DIVIDA_FCF else ""


def valor_filtro_status_financiamento(filtros):
    status = str(filtros.get("status") or "").strip()
    return status if status in STATUS_FILTRO_FINANCIAMENTO else ""


def filtros_financiamentos_tem_periodo_explicito(filtros):
    return any(str(filtros.get(nome) or "").strip() for nome in FILTROS_PERIODO_FINANCIAMENTOS)


def filtros_financiamentos_tem_filtro_sem_periodo(filtros):
    return any(
        str(valor or "").strip()
        for nome, valor in filtros.items()
        if nome not in FILTROS_PERIODO_FINANCIAMENTOS
    )


def resolver_periodo_financiamentos(filtros, session):
    periodo_explicito = filtros_financiamentos_tem_periodo_explicito(filtros)
    filtro_sem_periodo = filtros_financiamentos_tem_filtro_sem_periodo(filtros)
    contrato_codigo = valor_filtro_codigo_contrato(filtros)
    data_inicial = normalizar_data_iso(
        filtros.get("data_inicial") or filtros.get("startDate") or ""
    )
    data_final = normalizar_data_iso(
        filtros.get("data_final") or filtros.get("endDate") or ""
    )
    data_inicial, data_final = normalizar_intervalo_datas(data_inicial, data_final)
    periodo = normalizar_periodo_frontend(filtros.get("period"))
    periodo_rapido = normalizar_periodo_rapido(
        filtros.get("quickPeriod") or filtros.get("periodo_rapido")
    )

    if data_inicial or data_final:
        periodo_rapido = "vencidos" if periodo_rapido == "vencidos" else ""
    elif periodo in PERIODOS_FRONTEND_PARA_RAPIDO:
        periodo_rapido = PERIODOS_FRONTEND_PARA_RAPIDO[periodo]
    elif periodo:
        data_inicial, data_final = intervalo_periodo_frontend(periodo)
        periodo_rapido = ""

    filtros = {
        **filtros,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "period": periodo,
        "periodo_rapido": periodo_rapido,
        "tipo": valor_filtro_tipo_divida(filtros),
        "status": valor_filtro_status_financiamento(filtros),
        "contractCode": contrato_codigo,
        "contrato_codigo": contrato_codigo,
    }
    if not periodo_explicito and filtro_sem_periodo:
        filtros["periodo_rapido"] = "todos"
        return filtros

    return resolver_periodo_rapido_com_sessao(
        filtros,
        session,
        "fcf_periodo_rapido",
    )


def valor_filtro_origem_movimentacao(filtros):
    origem = (
        filtros.get("sourceType")
        or filtros.get("movementSourceType")
        or filtros.get("origem_movimentacao")
        or ""
    )
    if origem:
        return origem if origem in ORIGENS_MOVIMENTACAO_FINANCIAMENTO else ""

    automatico = str(filtros.get("automaticFromDebt") or "").strip().lower()
    if automatico in {"1", "true", "sim", "yes"}:
        return "divida_automatica"
    if automatico in {"0", "false", "nao", "no"}:
        return "manual"

    return ""


def valor_filtro_operacional(filtros, *nomes):
    for nome in nomes:
        valor = filtros.get(nome)
        if valor not in (None, ""):
            return str(valor).strip()

    return ""


def filtro_id_operacional_invalido(valor):
    valor_id = str(valor or "").strip()
    return bool(valor_id and not valor_id.isdigit())


def valor_filtro_cliente(filtros):
    return valor_filtro_operacional(filtros, "clientId", "cliente_id", "cliente")


def filtro_cliente_id_invalido(filtros):
    return filtro_id_operacional_invalido(valor_filtro_cliente(filtros))


def valor_filtro_evento(filtros):
    return valor_filtro_operacional(
        filtros,
        "eventId",
        "costCenterId",
        "evento_id",
        "evento",
    )


def valor_filtro_codigo_contrato(filtros):
    return resolver_codigo_contrato_visual_parametros(filtros)


def filtrar_por_origem_movimentacao(queryset, origem):
    origem_normalizada = str(origem or "").strip()
    if origem_normalizada == "divida_automatica":
        return queryset.filter(divida_financeira__isnull=False)
    if origem_normalizada == "manual":
        return queryset.filter(divida_financeira__isnull=True)

    return queryset


def filtrar_parcelas_divida(filtros):
    parcelas = ParcelaDivida.objects.select_related(
        "divida",
        "divida__credor_cadastro",
        "divida__evento",
        "divida__evento__cliente",
        "divida__evento__orcamento",
    ).all()
    hoje = timezone.localdate()

    if filtros["periodo_rapido"] == "vencidos":
        parcelas = filtrar_parcelas_disponiveis_para_pagamento(
            parcelas.filter(data_vencimento_atual__lt=hoje)
        )

    if filtros["data_inicial"]:
        parcelas = parcelas.filter(data_vencimento_atual__gte=filtros["data_inicial"])

    if filtros["data_final"]:
        parcelas = parcelas.filter(data_vencimento_atual__lte=filtros["data_final"])

    if filtros["tipo"]:
        parcelas = parcelas.filter(divida__tipo=filtros["tipo"])

    if filtros["status"]:
        parcelas = parcelas.filter(status=filtros["status"])

    credor = valor_filtro_credor(filtros)
    if credor:
        parcelas = filtrar_por_credor_divida(
            parcelas,
            credor,
            id_estrito=filtro_credor_usa_id_canonico(filtros),
        )

    evento_id = valor_filtro_evento(filtros)
    if evento_id:
        if filtro_id_operacional_invalido(evento_id):
            return parcelas.none()

        parcelas = parcelas.filter(divida__evento_id=evento_id)

    contrato_codigo = valor_filtro_codigo_contrato(filtros)
    if contrato_codigo:
        parcelas = parcelas.filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "divida__evento__",
                contrato_codigo,
            )
        )

    cliente_id = valor_filtro_cliente(filtros)
    if cliente_id:
        if filtro_cliente_id_invalido(filtros):
            return parcelas.none()

        parcelas = parcelas.filter(divida__evento__cliente_id=cliente_id)

    return parcelas


def filtrar_movimentacoes_financiamento(filtros):
    movimentacoes = FinanciamentoMovimentacao.objects.select_related(
        "evento",
        "evento__cliente",
        "evento__orcamento",
        "divida_financeira",
        "divida_financeira__credor_cadastro",
        "divida_financeira__evento",
        "divida_financeira__evento__cliente",
        "divida_financeira__evento__orcamento",
    ).filter(ativo=True)
    hoje = timezone.localdate()

    if filtros["periodo_rapido"] == "vencidos":
        movimentacoes = movimentacoes.filter(
            data_prevista__lt=hoje,
            tipo_fluxo=TIPO_FLUXO_SAIDA,
        ).exclude(status__in=[STATUS_REALIZADO, STATUS_CANCELADO])

    if filtros["data_inicial"]:
        movimentacoes = movimentacoes.filter(data_prevista__gte=filtros["data_inicial"])

    if filtros["data_final"]:
        movimentacoes = movimentacoes.filter(data_prevista__lte=filtros["data_final"])

    if filtros["status"]:
        movimentacoes = movimentacoes.filter(status=filtros["status"])

    evento_id = valor_filtro_evento(filtros)
    if evento_id:
        if filtro_id_operacional_invalido(evento_id):
            return movimentacoes.none()

        movimentacoes = movimentacoes.filter(
            Q(evento_id=evento_id)
            | Q(divida_financeira__evento_id=evento_id)
        )

    contrato_codigo = valor_filtro_codigo_contrato(filtros)
    if contrato_codigo:
        movimentacoes = movimentacoes.filter(
            montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "evento__",
                contrato_codigo,
            )
            | montar_filtro_evento_ou_orcamento_por_contrato_visual(
                "divida_financeira__evento__",
                contrato_codigo,
            )
        )

    cliente_id = valor_filtro_cliente(filtros)
    if cliente_id:
        if filtro_cliente_id_invalido(filtros):
            return movimentacoes.none()

        movimentacoes = movimentacoes.filter(
            Q(evento__cliente_id=cliente_id)
            | Q(divida_financeira__evento__cliente_id=cliente_id)
        )

    if filtros["tipo"]:
        movimentacoes = movimentacoes.filter(divida_financeira__tipo=filtros["tipo"])

    origem_movimentacao = valor_filtro_origem_movimentacao(filtros)
    if origem_movimentacao:
        movimentacoes = filtrar_por_origem_movimentacao(
            movimentacoes,
            origem_movimentacao,
        )

    credor = valor_filtro_credor(filtros)
    if credor:
        movimentacoes = filtrar_por_credor_divida(
            movimentacoes,
            credor,
            prefixo="divida_financeira__",
            id_estrito=filtro_credor_usa_id_canonico(filtros),
        )

    return movimentacoes


def listar_parcelas_ordenadas(parcelas):
    return list(
        parcelas.order_by(
            "divida__credor",
            "divida__credor_cadastro__nome",
            "divida__descricao",
            "data_vencimento_atual",
            "numero_parcela",
            "id",
        )
    )


def listar_movimentacoes_financiamento_ordenadas(movimentacoes):
    return list(
        movimentacoes.order_by(
            "data_prevista",
            "descricao",
            "id",
        )
    )


def totais_financiamentos(lista_parcelas, lista_movimentacoes_financiamento=None):
    hoje = timezone.localdate()
    total_previsto_saida = Decimal("0.00")
    total_realizado_saida = Decimal("0.00")
    total_previsto_entrada = Decimal("0.00")
    total_realizado_entrada = Decimal("0.00")
    total_contas_pendentes = Decimal("0.00")
    total_contas_vencidas = Decimal("0.00")
    total_parcelas_previsto_saida = Decimal("0.00")
    total_parcelas_realizado_saida = Decimal("0.00")
    total_parcelas_contas_pendentes = Decimal("0.00")
    total_movimentacoes_previsto_entrada = Decimal("0.00")
    total_movimentacoes_previsto_saida = Decimal("0.00")
    total_movimentacoes_realizado_entrada = Decimal("0.00")
    total_movimentacoes_realizado_saida = Decimal("0.00")
    total_movimentacoes_contas_pendentes = Decimal("0.00")
    lista_movimentacoes_financiamento = lista_movimentacoes_financiamento or []

    for movimentacao in lista_movimentacoes_financiamento:
        valor_pendente = movimentacao.valor_pendente_realizacao
        movimentacao.dias_atraso = 0

        if movimentacao.tipo_fluxo == TIPO_FLUXO_ENTRADA:
            total_previsto_entrada += movimentacao.valor_previsto
            total_realizado_entrada += movimentacao.valor_realizado
            total_movimentacoes_previsto_entrada += movimentacao.valor_previsto
            total_movimentacoes_realizado_entrada += movimentacao.valor_realizado
            continue

        total_previsto_saida += movimentacao.valor_previsto
        total_realizado_saida += movimentacao.valor_realizado
        total_contas_pendentes += valor_pendente
        total_movimentacoes_previsto_saida += movimentacao.valor_previsto
        total_movimentacoes_realizado_saida += movimentacao.valor_realizado
        total_movimentacoes_contas_pendentes += valor_pendente

        if movimentacao.data_prevista < hoje and valor_pendente > Decimal("0.00"):
            total_contas_vencidas += valor_pendente
            movimentacao.dias_atraso = (hoje - movimentacao.data_prevista).days

    for parcela in lista_parcelas:
        valor_pendente = parcela.valor_pendente_pagamento
        total_previsto_saida += parcela.valor_total_devido
        total_realizado_saida += parcela.valor_pago
        total_contas_pendentes += valor_pendente
        total_parcelas_previsto_saida += parcela.valor_total_devido
        total_parcelas_realizado_saida += parcela.valor_pago
        total_parcelas_contas_pendentes += valor_pendente

        if parcela.data_vencimento_atual < hoje and valor_pendente > Decimal("0.00"):
            total_contas_vencidas += valor_pendente
            parcela.dias_atraso = (hoje - parcela.data_vencimento_atual).days
        else:
            parcela.dias_atraso = 0

    resultado_financeiro_projetado = quantizar_moeda(
        total_previsto_entrada - total_previsto_saida
    )
    resultado_financeiro_realizado = quantizar_moeda(
        total_realizado_entrada - total_realizado_saida
    )
    contas_pendentes = quantizar_moeda(total_contas_pendentes)
    contas_vencidas = quantizar_moeda(total_contas_vencidas)

    return {
        "total_previsto_entrada": quantizar_moeda(total_previsto_entrada),
        "total_previsto_saida": quantizar_moeda(total_previsto_saida),
        "total_realizado_entrada": quantizar_moeda(total_realizado_entrada),
        "total_realizado_saida": quantizar_moeda(total_realizado_saida),
        "plannedInflowAmount": quantizar_moeda(total_previsto_entrada),
        "plannedOutflowAmount": quantizar_moeda(total_previsto_saida),
        "realizedInflowAmount": quantizar_moeda(total_realizado_entrada),
        "realizedOutflowAmount": quantizar_moeda(total_realizado_saida),
        "saldo_previsto_fcf": resultado_financeiro_projetado,
        "saldo_realizado_fcf": resultado_financeiro_realizado,
        "resultado_financeiro_fcf_projetado": resultado_financeiro_projetado,
        "resultado_financeiro_fcf_realizado": resultado_financeiro_realizado,
        "projectedFinancialResultAmount": resultado_financeiro_projetado,
        "realizedFinancialResultAmount": resultado_financeiro_realizado,
        "total_contas_pendentes": contas_pendentes,
        "total_em_aberto": contas_pendentes,
        "total_contas_vencidas": contas_vencidas,
        "total_vencido": contas_vencidas,
        "contas_pendentes": contas_pendentes,
        "contas_vencidas": contas_vencidas,
        "pendingAccountsAmount": contas_pendentes,
        "pendingPaymentAmount": contas_pendentes,
        "total_parcelas_previsto_saida": quantizar_moeda(total_parcelas_previsto_saida),
        "total_parcelas_realizado_saida": quantizar_moeda(total_parcelas_realizado_saida),
        "total_parcelas_contas_pendentes": quantizar_moeda(total_parcelas_contas_pendentes),
        "total_movimentacoes_financiamento_previsto_entrada": quantizar_moeda(total_movimentacoes_previsto_entrada),
        "total_movimentacoes_financiamento_previsto_saida": quantizar_moeda(total_movimentacoes_previsto_saida),
        "total_movimentacoes_financiamento_realizado_entrada": quantizar_moeda(total_movimentacoes_realizado_entrada),
        "total_movimentacoes_financiamento_realizado_saida": quantizar_moeda(total_movimentacoes_realizado_saida),
        "total_movimentacoes_financiamento_contas_pendentes": quantizar_moeda(total_movimentacoes_contas_pendentes),
    }


def agrupar_parcelas_por_credor(lista_parcelas):
    hoje = timezone.localdate()
    grupos_credor = []
    credor_atual = None
    grupo_credor_atual = None
    divida_atual_id = None
    grupo_divida_atual = None

    for parcela in lista_parcelas:
        divida = _divida_carregada_da_parcela(parcela)
        credor_nome = getattr(divida, "credor", "") if divida else ""
        credor_id = getattr(divida, "credor_cadastro_id", None) if divida else None
        credor_chave = credor_id or credor_nome or parcela.divida_id

        if credor_atual != credor_chave:
            credor_atual = credor_chave
            grupo_credor_atual = {
                "credor_id": credor_id,
                "creditorId": credor_id,
                "credor_nome": credor_nome,
                "creditorName": credor_nome,
                "credor": credor_nome,
                "dividas": [],
                "subtotal_devido": Decimal("0.00"),
                "subtotal_pago": Decimal("0.00"),
                "subtotal_contas_pendentes": Decimal("0.00"),
                "subtotal_em_aberto": Decimal("0.00"),
                "quantidade_parcelas_pendentes": 0,
                "quantidade_parcelas_abertas": 0,
                "quantidade_parcelas_vencidas": 0,
            }
            grupos_credor.append(grupo_credor_atual)
            divida_atual_id = None

        if divida_atual_id != parcela.divida_id:
            divida_atual_id = parcela.divida_id
            grupo_divida_atual = {
                "divida_id": parcela.divida_id,
                "divida": divida,
                "credor_id": credor_id,
                "creditorId": credor_id,
                "credor_nome": credor_nome,
                "creditorName": credor_nome,
                "descricao": getattr(divida, "descricao", "") if divida else "",
                "parcelas": [],
                "subtotal_devido": Decimal("0.00"),
                "subtotal_pago": Decimal("0.00"),
                "subtotal_contas_pendentes": Decimal("0.00"),
                "subtotal_em_aberto": Decimal("0.00"),
                "quantidade_parcelas": 0,
                "quantidade_parcelas_pendentes": 0,
                "quantidade_parcelas_abertas": 0,
                "quantidade_parcelas_vencidas": 0,
            }
            grupo_credor_atual["dividas"].append(grupo_divida_atual)

        _adicionar_parcela_ao_grupo(parcela, grupo_divida_atual, grupo_credor_atual, hoje)

    for grupo_credor in grupos_credor:
        _quantizar_grupo_credor(grupo_credor)

    return grupos_credor


def estatisticas_financiamentos(lista_parcelas, lista_movimentacoes_financiamento=None):
    lista_movimentacoes_financiamento = lista_movimentacoes_financiamento or []
    hoje = timezone.localdate()
    dividas_listadas = {parcela.divida_id for parcela in lista_parcelas}
    dividas_pendentes = {
        parcela.divida_id
        for parcela in lista_parcelas
        if parcela.disponivel_para_pagamento
    }

    quantidade_parcelas_vencidas = sum(
        1
        for parcela in lista_parcelas
        if parcela.data_vencimento_atual < hoje
        and parcela.disponivel_para_pagamento
    )
    quantidade_movimentacoes_vencidas = sum(
        1
        for movimentacao in lista_movimentacoes_financiamento
        if movimentacao.tipo_fluxo == TIPO_FLUXO_SAIDA
        and movimentacao.data_prevista < hoje
        and movimentacao.valor_pendente_realizacao > Decimal("0.00")
    )
    quantidade_movimentacoes_automaticas = sum(
        1
        for movimentacao in lista_movimentacoes_financiamento
        if movimentacao.divida_financeira_id
    )
    quantidade_movimentacoes_manuais = (
        len(lista_movimentacoes_financiamento) - quantidade_movimentacoes_automaticas
    )

    return {
        "quantidade_dividas": len(dividas_pendentes),
        "quantidade_dividas_pendentes": len(dividas_pendentes),
        "quantidade_dividas_listadas": len(dividas_listadas),
        "quantidade_parcelas": len(lista_parcelas),
        "quantidade_parcelas_vencidas": quantidade_parcelas_vencidas,
        "quantidade_movimentacoes_financiamento": len(lista_movimentacoes_financiamento),
        "quantidade_movimentacoes_financiamento_vencidas": quantidade_movimentacoes_vencidas,
        "quantidade_movimentacoes_financiamento_automaticas": quantidade_movimentacoes_automaticas,
        "quantidade_movimentacoes_financiamento_manuais": quantidade_movimentacoes_manuais,
    }


def credores_para_filtro():
    return listar_credores_fcf_filtro()


def credores_cadastrados_para_filtro():
    return listar_credores_cadastrados_fcf_filtro()


def tipos_divida_para_filtro():
    return listar_tipos_divida_fcf_filtro()


def status_parcelas_para_filtro():
    return listar_status_parcelas_fcf_filtro()


def tipos_origem_movimentacao_financiamento_para_filtro():
    return TIPOS_ORIGEM_MOVIMENTACAO_FINANCIAMENTO


def dividas_das_parcelas(lista_parcelas):
    dividas_por_id = {}

    for parcela in lista_parcelas:
        divida = _divida_carregada_da_parcela(parcela)
        if divida is not None:
            dividas_por_id.setdefault(parcela.divida_id, divida)

    return sorted(
        dividas_por_id.values(),
        key=lambda divida: (divida.data_contratacao, divida.id),
        reverse=True,
    )


def _adicionar_parcela_ao_grupo(parcela, grupo_divida, grupo_credor, hoje):
    grupo_divida["parcelas"].append(parcela)
    valor_pendente = parcela.valor_pendente_pagamento
    grupo_divida["subtotal_devido"] += parcela.valor_total_devido
    grupo_divida["subtotal_pago"] += parcela.valor_pago
    grupo_divida["subtotal_contas_pendentes"] += valor_pendente
    grupo_divida["subtotal_em_aberto"] += valor_pendente
    grupo_divida["quantidade_parcelas"] += 1

    grupo_credor["subtotal_devido"] += parcela.valor_total_devido
    grupo_credor["subtotal_pago"] += parcela.valor_pago
    grupo_credor["subtotal_contas_pendentes"] += valor_pendente
    grupo_credor["subtotal_em_aberto"] += valor_pendente
    parcela_pendente = parcela.disponivel_para_pagamento
    grupo_credor["quantidade_parcelas_pendentes"] += int(parcela_pendente)
    grupo_credor["quantidade_parcelas_abertas"] += int(parcela_pendente)

    if parcela_pendente:
        grupo_divida["quantidade_parcelas_pendentes"] += 1
        grupo_divida["quantidade_parcelas_abertas"] += 1

    if parcela.data_vencimento_atual < hoje and parcela_pendente:
        grupo_divida["quantidade_parcelas_vencidas"] += 1
        grupo_credor["quantidade_parcelas_vencidas"] += 1


def _divida_carregada_da_parcela(parcela):
    return relacao_carregada(parcela, "divida")


def _quantizar_grupo_credor(grupo_credor):
    grupo_credor["subtotal_devido"] = quantizar_moeda(grupo_credor["subtotal_devido"])
    grupo_credor["subtotal_pago"] = quantizar_moeda(grupo_credor["subtotal_pago"])
    grupo_credor["subtotal_contas_pendentes"] = quantizar_moeda(
        grupo_credor["subtotal_contas_pendentes"]
    )
    grupo_credor["subtotal_em_aberto"] = quantizar_moeda(grupo_credor["subtotal_em_aberto"])
    grupo_credor["subtotalPendingAccountsAmount"] = grupo_credor[
        "subtotal_contas_pendentes"
    ]
    grupo_credor["subtotalPendingPaymentAmount"] = grupo_credor[
        "subtotal_contas_pendentes"
    ]

    for grupo_divida in grupo_credor["dividas"]:
        grupo_divida["subtotal_devido"] = quantizar_moeda(grupo_divida["subtotal_devido"])
        grupo_divida["subtotal_pago"] = quantizar_moeda(grupo_divida["subtotal_pago"])
        grupo_divida["subtotal_contas_pendentes"] = quantizar_moeda(
            grupo_divida["subtotal_contas_pendentes"]
        )
        grupo_divida["subtotal_em_aberto"] = quantizar_moeda(grupo_divida["subtotal_em_aberto"])
        grupo_divida["subtotalPendingAccountsAmount"] = grupo_divida[
            "subtotal_contas_pendentes"
        ]
        grupo_divida["subtotalPendingPaymentAmount"] = grupo_divida[
            "subtotal_contas_pendentes"
        ]


def montar_contexto_financiamentos(filtros_raw, session):
    filtros = resolver_periodo_financiamentos(filtros_raw, session)
    parcelas = filtrar_parcelas_divida(filtros)
    movimentacoes_financiamento = filtrar_movimentacoes_financiamento(filtros)
    lista_parcelas = listar_parcelas_ordenadas(parcelas)
    lista_movimentacoes_financiamento = listar_movimentacoes_financiamento_ordenadas(
        movimentacoes_financiamento
    )
    totais = totais_financiamentos(lista_parcelas, lista_movimentacoes_financiamento)
    estatisticas = estatisticas_financiamentos(lista_parcelas, lista_movimentacoes_financiamento)
    credor = valor_filtro_credor(filtros)
    credor_id_canonico = credor if filtro_credor_usa_id_canonico(filtros) else ""
    origem_movimentacao = valor_filtro_origem_movimentacao(filtros)
    automatico_divida = ""
    if origem_movimentacao == "divida_automatica":
        automatico_divida = "true"
    elif origem_movimentacao == "manual":
        automatico_divida = "false"

    return {
        "dividas": dividas_das_parcelas(lista_parcelas),
        "parcelas": lista_parcelas,
        "movimentacoes_financiamento": lista_movimentacoes_financiamento,
        "grupos_credor": agrupar_parcelas_por_credor(lista_parcelas),
        **totais,
        **estatisticas,
        "credores_filtro": credores_para_filtro(),
        "credores_cadastrados_filtro": credores_cadastrados_para_filtro(),
        "tipos_divida": tipos_divida_para_filtro(),
        "status_parcelas": status_parcelas_para_filtro(),
        "categorias_financiamento": FinanciamentoMovimentacao.CATEGORIA_CHOICES,
        "tipos_fluxo_financiamento": FinanciamentoMovimentacao.TIPO_FLUXO_CHOICES,
        "status_financiamento": FinanciamentoMovimentacao.STATUS_CHOICES,
        "tipos_origem_movimentacao_financiamento": (
            tipos_origem_movimentacao_financiamento_para_filtro()
        ),
        "contratos_filtro": listar_contratos_visuais_filtro(),
        "eventos_filtro": listar_eventos_filtro_recentes(),
        "clientes_filtro": listar_clientes_filtro(),
        "periodo_rapido": filtros["periodo_rapido"],
        "filtros": {
            "data_inicial": filtros["data_inicial"],
            "data_final": filtros["data_final"],
            "startDate": filtros["data_inicial"],
            "endDate": filtros["data_final"],
            "period": filtros.get("period", ""),
            "quickPeriod": filtros["periodo_rapido"],
            "tipo": filtros["tipo"],
            "type": filtros["tipo"],
            "status": filtros["status"],
            "credor": credor,
            "creditor": credor,
            "creditorId": credor_id_canonico,
            "credor_id": credor_id_canonico,
            "sourceType": origem_movimentacao,
            "movementSourceType": origem_movimentacao,
            "origem_movimentacao": origem_movimentacao,
            "automaticFromDebt": automatico_divida,
            "contractCode": filtros["contractCode"],
            "contrato_codigo": filtros["contrato_codigo"],
            "evento": valor_filtro_evento(filtros),
            "costCenterId": valor_filtro_evento(filtros),
            "eventId": valor_filtro_evento(filtros),
            "evento_id": valor_filtro_evento(filtros),
            "cliente": valor_filtro_cliente(filtros) or "",
            "clientId": valor_filtro_cliente(filtros) or "",
            "cliente_id": valor_filtro_cliente(filtros) or "",
        },
    }
