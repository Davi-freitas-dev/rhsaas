from decimal import Decimal

from .constants_dividas import STATUS_DIVIDA_CANCELADA
from .constants_financeiros import STATUS_REALIZADO, TIPO_FLUXO_ENTRADA
from .models_fcf import FinanciamentoMovimentacao


class EntradaFCFDividaStrategy:
    tipos = frozenset()

    def suporta(self, divida):
        return divida.tipo in self.tipos

    def deve_gerar_entrada(self, divida):
        return (
            divida.status != STATUS_DIVIDA_CANCELADA
            and divida.valor_contratado > Decimal("0.00")
        )

    def descricao(self, divida):
        return f"{divida.get_tipo_display()} - {divida.credor}"

    def observacao(self, divida):
        observacao = (
            f"Entrada automatica gerada pela divida financeira #{divida.pk}: "
            f"{divida.descricao}"
        )

        if divida.observacao:
            return f"{observacao}\n\nObservacao da divida: {divida.observacao}"

        return observacao

    def dados(self, divida):
        if not self.deve_gerar_entrada(divida):
            return None

        return {
            "descricao": self.descricao(divida),
            "categoria": divida.tipo,
            "tipo_fluxo": TIPO_FLUXO_ENTRADA,
            "valor_previsto": divida.valor_contratado,
            "valor_realizado": divida.valor_contratado,
            "data_prevista": divida.data_contratacao,
            "data_realizacao": divida.data_contratacao,
            "evento": divida.evento,
            "status": STATUS_REALIZADO,
            "ativo": True,
            "observacao": self.observacao(divida),
            "criado_por": divida.criado_por,
            "atualizado_por": divida.atualizado_por,
        }


class EntradaFCFContratacaoDividaStrategy(EntradaFCFDividaStrategy):
    tipos = frozenset({"emprestimo", "financiamento"})


DEFAULT_ENTRADA_FCF_DIVIDA_STRATEGY = EntradaFCFDividaStrategy()
ENTRADA_FCF_DIVIDA_STRATEGIES = (
    EntradaFCFContratacaoDividaStrategy(),
)
TIPOS_DIVIDA_COM_ENTRADA_CAIXA = frozenset(
    tipo
    for strategy in ENTRADA_FCF_DIVIDA_STRATEGIES
    for tipo in strategy.tipos
)


def estrategia_entrada_fcf_divida(divida):
    for strategy in ENTRADA_FCF_DIVIDA_STRATEGIES:
        if strategy.suporta(divida):
            return strategy

    return None


def divida_deve_gerar_entrada_fcf(divida):
    strategy = estrategia_entrada_fcf_divida(divida)
    return bool(strategy and strategy.deve_gerar_entrada(divida))


def descricao_entrada_fcf_divida(divida):
    strategy = (
        estrategia_entrada_fcf_divida(divida)
        or DEFAULT_ENTRADA_FCF_DIVIDA_STRATEGY
    )
    return strategy.descricao(divida)


def observacao_entrada_fcf_divida(divida):
    strategy = (
        estrategia_entrada_fcf_divida(divida)
        or DEFAULT_ENTRADA_FCF_DIVIDA_STRATEGY
    )
    return strategy.observacao(divida)


def dados_entrada_fcf_divida(divida):
    strategy = estrategia_entrada_fcf_divida(divida)
    if strategy is None:
        return None

    return strategy.dados(divida)


def sincronizar_entrada_fcf_divida(divida):
    dados = dados_entrada_fcf_divida(divida)

    if dados is None:
        remover_entrada_fcf_divida(divida)
        return None

    movimento, _criado = FinanciamentoMovimentacao.objects.update_or_create(
        divida_financeira=divida,
        defaults=dados,
    )
    return movimento


def remover_entrada_fcf_divida(divida):
    FinanciamentoMovimentacao.objects.filter(divida_financeira=divida).delete()


def resumir_integridade_entradas_fcf_dividas(limit=20):
    from .models_dividas import DividaFinanceira

    _validar_limit_relatorio(limit)
    resultado = {
        "checked": 0,
        "consistent": True,
        "totalIssues": 0,
        "pendingCount": 0,
        "returnedIssues": 0,
        "limit": limit,
        "created": 0,
        "updated": 0,
        "removed": 0,
        "items": [],
    }
    dividas = list(DividaFinanceira.objects.select_related(
        "credor_cadastro",
        "evento",
        "criado_por",
        "atualizado_por",
    ).order_by("id"))
    movimentos_por_divida = FinanciamentoMovimentacao.objects.filter(
        divida_financeira_id__in=[divida.id for divida in dividas],
    ).in_bulk(field_name="divida_financeira_id")

    for divida in dividas:
        resultado["checked"] += 1
        dados = dados_entrada_fcf_divida(divida)
        movimento = movimentos_por_divida.get(divida.id)
        acao = None

        if dados is None and movimento is not None:
            acao = "remover"
            resultado["removed"] += 1
        elif dados is not None and movimento is None:
            acao = "criar"
            resultado["created"] += 1
        elif dados is not None and movimento_entrada_fcf_desatualizado(
            movimento,
            dados,
        ):
            acao = "atualizar"
            resultado["updated"] += 1

        if acao is None:
            continue

        resultado["totalIssues"] += 1
        resultado["pendingCount"] += 1
        resultado["consistent"] = False
        if len(resultado["items"]) < limit:
            resultado["items"].append(_item_integridade_entrada_fcf(
                divida,
                movimento,
                acao,
            ))

    resultado["returnedIssues"] = len(resultado["items"])
    return resultado


def _validar_limit_relatorio(limit):
    if limit < 0:
        raise ValueError("limit deve ser maior ou igual a 0.")


def _item_integridade_entrada_fcf(divida, movimento, acao):
    return {
        "action": acao,
        "debtId": divida.id,
        "debtType": divida.tipo,
        "debtCreditorId": divida.credor_cadastro_id,
        "debtCreditorName": divida.credor,
        "movementId": getattr(movimento, "id", None),
        "movementDescription": getattr(movimento, "descricao", ""),
    }


def movimento_entrada_fcf_desatualizado(movimento, dados):
    if dados is None:
        return movimento is not None

    if movimento is None:
        return True

    campos_relacionais = {"evento", "criado_por", "atualizado_por"}
    for campo, valor_esperado in dados.items():
        if campo in campos_relacionais:
            valor_atual = getattr(movimento, f"{campo}_id")
            valor_esperado_id = getattr(valor_esperado, "id", None)
            if valor_atual != valor_esperado_id:
                return True
            continue

        if getattr(movimento, campo) != valor_esperado:
            return True

    return False
