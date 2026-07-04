from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, Sum

from caixa.constants_financeiros import TIPO_FLUXO_ENTRADA, TIPO_FLUXO_SAIDA
from caixa.models import DespesaOperacional, ReceitaOperacional
from caixa.models_custo_fixo import CustoFixo
from caixa.models_dividas import PagamentoParcelaDivida, ParcelaDivida
from caixa.models_fcf import FinanciamentoMovimentacao
from caixa.models_fci import Investimento
from caixa.models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from caixa.selectors_mes_financeiro import montar_contexto_mes_financeiro
from caixa.services_validacao_pagamentos import (
    pagamentos_custos_servico_legado,
    saldo_caixa_disponivel,
)
from caixa.utils_financeiros import ZERO_DECIMAL, decimal_zero, quantizar_moeda


class Command(BaseCommand):
    help = (
        "Lista as entradas e saídas que compõem o caixa disponível até uma data, "
        "usando a mesma base da validação de pagamentos."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            required=True,
            help="Data limite em formato YYYY-MM-DD.",
        )
        parser.add_argument(
            "--data-inicial",
            default=None,
            help=(
                "Data inicial do período do Mês Financeiro para comparar "
                "resultado realizado do período com caixa disponível acumulado."
            ),
        )
        parser.add_argument(
            "--valor-pagamento",
            type=Decimal,
            default=None,
            help="Valor opcional para simular se há caixa suficiente.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Quantidade máxima de itens detalhados por tipo.",
        )
        parser.add_argument(
            "--sem-detalhes",
            action="store_true",
            help="Mostra apenas os totais por origem.",
        )
        parser.add_argument(
            "--detalhar-mes-financeiro",
            action="store_true",
            help=(
                "Quando --data-inicial for informado, lista as contas pagas "
                "que compoem o total Pago do Mes Financeiro."
            ),
        )

    def handle(self, *args, **options):
        data_limite = parse_data(options["data"])
        data_inicial = parse_data(options["data_inicial"]) if options["data_inicial"] else None
        valor_pagamento = options["valor_pagamento"]
        limit = max(options["limit"], 0)

        entradas = listar_entradas_caixa(data_limite)
        saidas = listar_saidas_caixa(data_limite)
        total_entradas = somar_itens(entradas)
        total_saidas = somar_itens(saidas)
        saldo = saldo_caixa_disponivel(data_limite)

        self.stdout.write("Diagnóstico de caixa disponível.")
        self.stdout.write(f"Data limite: {data_limite:%Y-%m-%d}")
        self.stdout.write(f"Entradas: {total_entradas:.2f}")
        self.stdout.write(f"Saídas: {total_saidas:.2f}")
        self.stdout.write(f"Caixa disponível: {saldo:.2f}")

        if data_inicial:
            imprimir_comparacao_mes_financeiro_detalhada(
                self,
                data_inicial,
                data_limite,
                saldo,
                entradas,
                saidas,
                limit,
                options["detalhar_mes_financeiro"],
            )

        if valor_pagamento is not None:
            valor_pagamento = quantizar_moeda(valor_pagamento)
            deficit = quantizar_moeda(valor_pagamento - saldo)
            self.stdout.write(f"Valor pagamento simulado: {valor_pagamento:.2f}")
            if deficit > ZERO_DECIMAL:
                self.stdout.write(f"Déficit de caixa: {deficit:.2f}")
            else:
                self.stdout.write("Caixa suficiente para o valor simulado.")

        self.stdout.write("")
        imprimir_grupos(self, "Entradas por origem", entradas)
        imprimir_grupos(self, "Saídas por origem", saidas)

        if not options["sem_detalhes"]:
            self.stdout.write("")
            imprimir_itens(self, "Entradas detalhadas", entradas, limit)
            imprimir_itens(self, "Saídas detalhadas", saidas, limit)


def parse_data(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError) as exc:
        raise CommandError("Informe --data no formato YYYY-MM-DD.") from exc


def imprimir_comparacao_mes_financeiro(command, data_inicial, data_final, saldo_caixa):
    contexto = montar_contexto_mes_financeiro(
        {
            "data_inicial": data_inicial.isoformat(),
            "data_final": data_final.isoformat(),
            "mes": "",
            "periodo_rapido": "",
            "origem": "",
            "status": "",
            "evento": "",
            "cliente": "",
            "contrato_codigo": "",
        }
    )
    recebido_periodo = quantizar_moeda(contexto["receita_recebida"])
    pago_periodo = quantizar_moeda(contexto["divida_paga"])
    resultado_realizado_periodo = quantizar_moeda(
        contexto["resultado_financeiro_realizado"]
    )
    diferenca = quantizar_moeda(resultado_realizado_periodo - saldo_caixa)

    command.stdout.write("")
    command.stdout.write("Comparação com Mês Financeiro:")
    command.stdout.write(f"Período: {data_inicial:%Y-%m-%d} a {data_final:%Y-%m-%d}")
    command.stdout.write(
        "Resultado realizado do período = "
        f"{recebido_periodo:.2f} - {pago_periodo:.2f} = "
        f"{resultado_realizado_periodo:.2f}"
    )
    command.stdout.write(
        "Caixa disponível acumulado = "
        f"{saldo_caixa:.2f}"
    )
    command.stdout.write(
        "Diferença entre resultado do período e caixa disponível = "
        f"{diferenca:.2f}"
    )

    if diferenca > ZERO_DECIMAL:
        command.stdout.write(
            "Leitura: há saídas acumuladas fora do recorte do Mês Financeiro, "
            "ou saldo anterior negativo, reduzindo o caixa disponível."
        )
    elif diferenca < ZERO_DECIMAL:
        command.stdout.write(
            "Leitura: há entradas acumuladas fora do recorte do Mês Financeiro, "
            "ou saldo anterior positivo, aumentando o caixa disponível."
        )
    else:
        command.stdout.write(
            "Leitura: resultado realizado do período e caixa disponível acumulado "
            "batem nesta janela."
        )


def imprimir_comparacao_mes_financeiro_detalhada(
    command,
    data_inicial,
    data_final,
    saldo_caixa,
    entradas_caixa,
    saidas_caixa,
    limit,
    detalhar_mes_financeiro,
):
    imprimir_comparacao_mes_financeiro(
        command,
        data_inicial,
        data_final,
        saldo_caixa,
    )
    contexto = montar_contexto_mes_financeiro(
        {
            "data_inicial": data_inicial.isoformat(),
            "data_final": data_final.isoformat(),
            "mes": "",
            "periodo_rapido": "",
            "origem": "",
            "status": "",
            "evento": "",
            "cliente": "",
            "contrato_codigo": "",
        }
    )
    recebido_periodo = quantizar_moeda(contexto["receita_recebida"])
    pago_periodo = quantizar_moeda(contexto["divida_paga"])
    resultado_realizado_periodo = quantizar_moeda(
        contexto["resultado_financeiro_realizado"]
    )
    diferenca = quantizar_moeda(resultado_realizado_periodo - saldo_caixa)
    entradas_caixa_periodo = filtrar_itens_periodo(
        entradas_caixa,
        data_inicial,
        data_final,
    )
    saidas_caixa_periodo = filtrar_itens_periodo(
        saidas_caixa,
        data_inicial,
        data_final,
    )
    total_entradas_caixa_periodo = somar_itens(entradas_caixa_periodo)
    total_saidas_caixa_periodo = somar_itens(saidas_caixa_periodo)
    resultado_caixa_periodo = quantizar_moeda(
        total_entradas_caixa_periodo - total_saidas_caixa_periodo
    )
    diferenca_pago_saida_caixa = quantizar_moeda(
        pago_periodo - total_saidas_caixa_periodo
    )

    command.stdout.write("")
    command.stdout.write("Detalhe de caixa por data efetiva:")
    command.stdout.write(f"Periodo: {data_inicial:%Y-%m-%d} a {data_final:%Y-%m-%d}")
    command.stdout.write(
        "Resultado realizado do periodo = "
        f"{recebido_periodo:.2f} - {pago_periodo:.2f} = "
        f"{resultado_realizado_periodo:.2f}"
    )
    command.stdout.write(f"Caixa disponivel acumulado = {saldo_caixa:.2f}")
    command.stdout.write(
        f"Entradas de caixa no periodo = {total_entradas_caixa_periodo:.2f}"
    )
    command.stdout.write(
        f"Saidas de caixa no periodo = {total_saidas_caixa_periodo:.2f}"
    )
    command.stdout.write(
        f"Resultado de caixa no periodo = {resultado_caixa_periodo:.2f}"
    )
    command.stdout.write(
        "Diferenca entre Pago do Mes Financeiro e saidas de caixa no periodo = "
        f"{diferenca_pago_saida_caixa:.2f}"
    )
    command.stdout.write(
        "Diferenca entre resultado do periodo e caixa disponivel = "
        f"{diferenca:.2f}"
    )

    if diferenca_pago_saida_caixa > ZERO_DECIMAL:
        command.stdout.write(
            "Leitura adicional: o total Pago do Mes Financeiro esta maior que "
            "as saidas de caixa efetivas no periodo. Revise itens pagos pela "
            "data de vencimento do recorte ou registros sincronizados que usam "
            "valor_pago, enquanto o caixa usa data de pagamento/baixa."
        )
    elif diferenca_pago_saida_caixa < ZERO_DECIMAL:
        command.stdout.write(
            "Leitura adicional: as saidas de caixa efetivas no periodo estao "
            "maiores que o total Pago do Mes Financeiro. Revise pagamentos com "
            "data de baixa dentro do periodo e vencimento fora do recorte."
        )
    else:
        command.stdout.write(
            "Leitura adicional: Pago do Mes Financeiro e saidas de caixa do "
            "periodo batem nesta janela."
        )

    if diferenca > ZERO_DECIMAL:
        command.stdout.write(
            "Leitura: ha saidas acumuladas fora do recorte do Mes Financeiro, "
            "ou saldo anterior negativo, reduzindo o caixa disponivel."
        )
    elif diferenca < ZERO_DECIMAL:
        command.stdout.write(
            "Leitura: ha entradas acumuladas fora do recorte do Mes Financeiro, "
            "ou saldo anterior positivo, aumentando o caixa disponivel."
        )
    else:
        command.stdout.write(
            "Leitura: resultado realizado do periodo e caixa disponivel acumulado "
            "batem nesta janela."
        )

    if detalhar_mes_financeiro:
        command.stdout.write("")
        imprimir_contas_pagas_mes_financeiro(
            command,
            "Contas pagas no Mes Financeiro",
            contexto["contas_a_pagar"],
            limit,
        )
        command.stdout.write("")
        imprimir_itens(
            command,
            "Saidas de caixa detalhadas no periodo",
            saidas_caixa_periodo,
            limit,
        )


def listar_entradas_caixa(data_limite):
    itens = []
    itens.extend(listar_receitas_recebidas(data_limite))
    itens.extend(listar_investimentos_realizados(data_limite, TIPO_FLUXO_ENTRADA))
    itens.extend(listar_financiamentos_realizados(data_limite, TIPO_FLUXO_ENTRADA))
    return ordenar_itens(itens)


def listar_saidas_caixa(data_limite):
    itens = []
    itens.extend(listar_despesas_manuais_pagas(data_limite))
    itens.extend(listar_custos_fixos_pagos(data_limite))
    itens.extend(listar_investimentos_realizados(data_limite, TIPO_FLUXO_SAIDA))
    itens.extend(listar_financiamentos_realizados(data_limite, TIPO_FLUXO_SAIDA))
    itens.extend(listar_pagamentos_parcelas(data_limite))
    itens.extend(listar_pagamentos_custos_servico(data_limite))
    itens.extend(listar_pagamentos_custos_servico_legado(data_limite))
    itens.extend(listar_pagamentos_custos_extras(data_limite))
    itens.extend(listar_pagamentos_parcelas_legado(data_limite))
    return ordenar_itens(itens)


def filtrar_itens_periodo(itens, data_inicial, data_final):
    return [
        item
        for item in itens
        if data_inicial <= item["data"] <= data_final
    ]


def listar_receitas_recebidas(data_limite):
    receitas = ReceitaOperacional.objects.filter(valor_recebido__gt=ZERO_DECIMAL).filter(
        filtro_data_efetiva("data_recebimento", "data_vencimento", data_limite)
    )
    return [
        item_caixa(
            "entrada",
            "receita_operacional",
            data_efetiva(receita, "data_recebimento", "data_vencimento"),
            receita.descricao,
            receita.valor_recebido,
        )
        for receita in receitas
    ]


def listar_despesas_manuais_pagas(data_limite):
    despesas = (
        DespesaOperacional.objects.filter(valor_pago__gt=ZERO_DECIMAL)
        .exclude(descricao__startswith="Custo extra: ")
        .exclude(
            Q(categoria__in=["mao_obra", "alimentacao", "transporte"])
            & (Q(descricao__endswith="prevista") | Q(descricao__endswith="previsto"))
        )
        .filter(filtro_data_efetiva("data_pagamento", "data_vencimento", data_limite))
    )
    return [
        item_caixa(
            "saida",
            "despesa_operacional_manual",
            data_efetiva(despesa, "data_pagamento", "data_vencimento"),
            despesa.descricao,
            despesa.valor_pago,
        )
        for despesa in despesas
    ]


def listar_custos_fixos_pagos(data_limite):
    custos = CustoFixo.objects.filter(valor_pago__gt=ZERO_DECIMAL).filter(
        filtro_data_efetiva("data_pagamento", "data_vencimento", data_limite)
    )
    return [
        item_caixa(
            "saida",
            "custo_fixo",
            data_efetiva(custo, "data_pagamento", "data_vencimento"),
            custo.descricao,
            custo.valor_pago,
        )
        for custo in custos
    ]


def listar_investimentos_realizados(data_limite, tipo_fluxo):
    investimentos = Investimento.objects.filter(
        ativo=True,
        tipo_fluxo=tipo_fluxo,
        valor_realizado__gt=ZERO_DECIMAL,
    ).filter(filtro_data_efetiva("data_realizacao", "data_prevista", data_limite))
    tipo = "entrada" if tipo_fluxo == TIPO_FLUXO_ENTRADA else "saida"
    return [
        item_caixa(
            tipo,
            f"investimento_{tipo_fluxo}",
            data_efetiva(investimento, "data_realizacao", "data_prevista"),
            investimento.descricao,
            investimento.valor_realizado,
        )
        for investimento in investimentos
    ]


def listar_financiamentos_realizados(data_limite, tipo_fluxo):
    financiamentos = FinanciamentoMovimentacao.objects.filter(
        ativo=True,
        tipo_fluxo=tipo_fluxo,
        valor_realizado__gt=ZERO_DECIMAL,
    ).filter(filtro_data_efetiva("data_realizacao", "data_prevista", data_limite))
    tipo = "entrada" if tipo_fluxo == TIPO_FLUXO_ENTRADA else "saida"
    return [
        item_caixa(
            tipo,
            f"financiamento_{tipo_fluxo}",
            data_efetiva(financiamento, "data_realizacao", "data_prevista"),
            financiamento.descricao,
            financiamento.valor_realizado,
        )
        for financiamento in financiamentos
    ]


def listar_pagamentos_parcelas(data_limite):
    pagamentos = PagamentoParcelaDivida.objects.select_related("parcela", "parcela__divida").filter(
        valor_pagamento__gt=ZERO_DECIMAL,
        data_pagamento__lte=data_limite,
    )
    return [
        item_caixa(
            "saida",
            "pagamento_parcela_divida",
            pagamento.data_pagamento,
            (
                f"{pagamento.parcela.divida.descricao} / "
                f"Parcela {pagamento.parcela.rotulo_parcela}"
            ),
            pagamento.valor_pagamento,
        )
        for pagamento in pagamentos
    ]


def listar_pagamentos_custos_servico(data_limite):
    pagamentos = PagamentoEventoCustoServico.objects.select_related(
        "custo_servico",
        "custo_servico__evento",
        "custo_servico__servico",
    ).filter(
        valor_pagamento__gt=ZERO_DECIMAL,
        data_pagamento__lte=data_limite,
    )
    return [
        item_caixa(
            "saida",
            "pagamento_custo_servico",
            pagamento.data_pagamento,
            (
                f"{pagamento.custo_servico.evento} / "
                f"{pagamento.custo_servico.servico} / "
                f"{pagamento.get_tipo_display()} / {pagamento.descricao}"
            ).strip(" /"),
            pagamento.valor_pagamento,
        )
        for pagamento in pagamentos
    ]


def listar_pagamentos_custos_servico_legado(data_limite):
    return [
        item_caixa(
            "saida",
            "pagamento_custo_servico_legado",
            item["data"],
            item["descricao"],
            item["valor"],
        )
        for item in pagamentos_custos_servico_legado(data_limite)
    ]


def listar_pagamentos_custos_extras(data_limite):
    pagamentos = PagamentoEventoCustoExtra.objects.select_related(
        "custo_extra",
        "custo_extra__evento",
    ).filter(
        valor_pagamento__gt=ZERO_DECIMAL,
        data_pagamento__lte=data_limite,
    )
    return [
        item_caixa(
            "saida",
            "pagamento_custo_extra",
            pagamento.data_pagamento,
            f"{pagamento.custo_extra.evento} / {pagamento.custo_extra.descricao}",
            pagamento.valor_pagamento,
        )
        for pagamento in pagamentos
    ]


def listar_pagamentos_parcelas_legado(data_limite):
    parcelas = (
        ParcelaDivida.objects.select_related("divida")
        .filter(valor_pago__gt=ZERO_DECIMAL, data_vencimento_atual__lte=data_limite)
        .annotate(total_registrado=Sum("pagamentos__valor_pagamento"))
    )
    itens = []
    for parcela in parcelas:
        valor_legado = quantizar_moeda(
            decimal_zero(parcela.valor_pago) - decimal_zero(parcela.total_registrado)
        )
        if valor_legado > ZERO_DECIMAL:
            itens.append(
                item_caixa(
                    "saida",
                    "pagamento_parcela_divida_legado",
                    parcela.data_vencimento_atual,
                    f"{parcela.divida.descricao} / Parcela {parcela.rotulo_parcela}",
                    valor_legado,
                )
            )
    return itens


def filtro_data_efetiva(campo_realizado, campo_previsto, data_limite):
    return (
        Q(**{f"{campo_realizado}__lte": data_limite})
        | (
            Q(**{f"{campo_realizado}__isnull": True})
            & Q(**{f"{campo_previsto}__lte": data_limite})
        )
    )


def data_efetiva(objeto, campo_realizado, campo_previsto):
    return getattr(objeto, campo_realizado) or getattr(objeto, campo_previsto)


def item_caixa(tipo, origem, data_movimento, descricao, valor):
    return {
        "tipo": tipo,
        "origem": origem,
        "data": data_movimento,
        "descricao": descricao or "-",
        "valor": quantizar_moeda(valor),
    }


def ordenar_itens(itens):
    return sorted(
        itens,
        key=lambda item: (
            item["data"],
            item["origem"],
            item["descricao"],
            item["valor"],
        ),
    )


def somar_itens(itens):
    return quantizar_moeda(
        sum((decimal_zero(item["valor"]) for item in itens), Decimal("0.00"))
    )


def imprimir_grupos(command, titulo, itens):
    command.stdout.write(titulo + ":")
    grupos = {}
    for item in itens:
        grupos.setdefault(item["origem"], {"count": 0, "total": Decimal("0.00")})
        grupos[item["origem"]]["count"] += 1
        grupos[item["origem"]]["total"] += decimal_zero(item["valor"])

    if not grupos:
        command.stdout.write("- nenhum")
        return

    for origem, resumo in sorted(grupos.items()):
        command.stdout.write(
            f"- {origem}: count={resumo['count']}; valor={resumo['total']:.2f}"
        )


def imprimir_itens(command, titulo, itens, limit):
    command.stdout.write(titulo + ":")
    if not itens:
        command.stdout.write("- nenhum")
        return

    for item in itens[:limit]:
        command.stdout.write(
            f"- {item['data']:%Y-%m-%d}; {item['origem']}; "
            f"{item['valor']:.2f}; {item['descricao']}"
        )

    if len(itens) > limit:
        command.stdout.write(f"- ... {len(itens) - limit} item(ns) omitido(s)")


def imprimir_contas_pagas_mes_financeiro(command, titulo, contas, limit):
    contas_pagas = [
        conta
        for conta in contas
        if decimal_zero(conta.get("pago")) > ZERO_DECIMAL
    ]
    command.stdout.write(titulo + ":")
    if not contas_pagas:
        command.stdout.write("- nenhum")
        return

    for conta in contas_pagas[:limit]:
        objeto = conta.get("objeto")
        origem_objeto = "-"
        if objeto is not None:
            origem_objeto = (
                f"{objeto.__class__.__name__}#{getattr(objeto, 'pk', '-')}"
            )
        command.stdout.write(
            f"- {conta['data']:%Y-%m-%d}; {conta['tipo']}; "
            f"pago={decimal_zero(conta.get('pago')):.2f}; "
            f"aberto={decimal_zero(conta.get('aberto')):.2f}; "
            f"status={conta.get('status', '-')}; "
            f"{conta.get('descricao', '-')}; {conta.get('referencia', '-')}; "
            f"objeto={origem_objeto}"
        )

    if len(contas_pagas) > limit:
        command.stdout.write(f"- ... {len(contas_pagas) - limit} item(ns) omitido(s)")
