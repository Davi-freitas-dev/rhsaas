from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from caixa.constants_dividas import (
    STATUS_PARCELA_CANCELADA,
    STATUS_PARCELA_PAGA,
    STATUS_PARCELA_RENEGOCIADA,
)
from caixa.models import Evento, Orcamento
from caixa.models_dividas import DividaFinanceira
from caixa.services_orcamentos import custo_servico_possui_movimento
from caixa.utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")
STATUS_PARCELA_NAO_REPROGRAMA_VENCIMENTO = {
    STATUS_PARCELA_PAGA,
    STATUS_PARCELA_RENEGOCIADA,
    STATUS_PARCELA_CANCELADA,
}


def verificar_integridade_valores_editaveis(
    corrigir=False,
    limit=20,
    escopos=None,
    object_ids=None,
):
    filtros = _normalizar_filtros(escopos=escopos, object_ids=object_ids)
    inicial = auditar_integridade_valores_editaveis(limit=limit, **filtros)
    correcoes = []

    if corrigir and inicial["totalIssues"]:
        correcoes.extend(_corrigir_dividas(inicial))
        correcoes.extend(_corrigir_orcamentos(inicial))
        correcoes.extend(_corrigir_eventos(inicial))

    restante = auditar_integridade_valores_editaveis(limit=limit, **filtros)
    correcoes_aplicadas = [
        correcao for correcao in correcoes if correcao.get("status") == "applied"
    ]
    correcoes_bloqueadas = [
        correcao for correcao in correcoes if correcao.get("status") == "blocked"
    ]

    return {
        "apply": corrigir,
        "filters": _serializar_filtros(filtros),
        "consistent": restante["totalIssues"] == 0,
        "initial": inicial,
        "remaining": restante,
        "correctionPlan": _montar_plano_correcao(restante, limit),
        "correctionsApplied": len(correcoes_aplicadas),
        "correctionsBlocked": len(correcoes_bloqueadas),
        "corrections": correcoes[:limit],
    }


def auditar_integridade_valores_editaveis(limit=20, escopos=None, object_ids=None):
    filtros = _normalizar_filtros(escopos=escopos, object_ids=object_ids)
    resultado = {
        "consistent": True,
        "totalIssues": 0,
        "filters": _serializar_filtros(filtros),
        "checked": {
            "debts": 0,
            "approvedBudgets": 0,
            "events": 0,
        },
        "targets": {
            "divida": [],
            "orcamento": [],
            "evento": [],
        },
        "issues": [],
    }

    if "divida" in filtros["escopos"]:
        dividas = DividaFinanceira.objects.prefetch_related(
            "parcelas__pagamentos"
        ).order_by("id")
        if filtros["object_ids"] is not None:
            dividas = dividas.filter(id__in=filtros["object_ids"])

        for divida in dividas:
            resultado["checked"]["debts"] += 1
            _auditar_divida(divida, resultado, limit)

    if "orcamento" in filtros["escopos"]:
        orcamentos = Orcamento.objects.filter(status="aprovado").prefetch_related(
            "itens__servico",
            "evento__custos_servicos__pagamentos",
            "evento__receitas",
        ).order_by("id")
        if filtros["object_ids"] is not None:
            orcamentos = orcamentos.filter(id__in=filtros["object_ids"])

        for orcamento in orcamentos:
            resultado["checked"]["approvedBudgets"] += 1
            _auditar_orcamento_aprovado(orcamento, resultado, limit)

    if "evento" in filtros["escopos"]:
        eventos = Evento.objects.prefetch_related(
            "receitas",
            "despesas",
            "custos_servicos",
        ).order_by("id")
        if filtros["object_ids"] is not None:
            eventos = eventos.filter(id__in=filtros["object_ids"])

        for evento in eventos:
            resultado["checked"]["events"] += 1
            _auditar_evento(evento, resultado, limit)

    resultado["consistent"] = resultado["totalIssues"] == 0
    return resultado


def resumir_integridade_valores_editaveis(
    validar=False,
    limit=20,
    escopos=None,
    object_ids=None,
):
    if not validar:
        return {
            "checked": False,
            "consistent": None,
            "filters": _serializar_filtros(_normalizar_filtros()),
            "summary": {},
            "issues": [],
            "totalIssues": 0,
            "targets": {},
            "correctionPlan": {"totalTargets": 0, "items": []},
        }

    resultado = auditar_integridade_valores_editaveis(
        limit=limit,
        escopos=escopos,
        object_ids=object_ids,
    )
    return {
        "checked": True,
        "consistent": resultado["consistent"],
        "filters": resultado["filters"],
        "summary": resultado["checked"],
        "issues": resultado["issues"],
        "totalIssues": resultado["totalIssues"],
        "targets": resultado["targets"],
        "correctionPlan": _montar_plano_correcao(resultado, limit),
    }


def formatar_plano_correcao_valores_editaveis(plano):
    linhas = []
    itens = plano.get("items") or []
    if not itens:
        return linhas

    linhas.append("Plano de correcao sugerido:")
    for item in itens:
        linhas.extend([
            f"- {item['scope']}:{item['objectId']}",
            f"  auditar: {item['auditCommand']}",
            f"  corrigir: {item['applyCommand']}",
            f"  validar: {item['validationCommand']}",
        ])

    return linhas


def _normalizar_filtros(escopos=None, object_ids=None):
    return {
        "escopos": _normalizar_escopos(escopos),
        "object_ids": _normalizar_object_ids(object_ids),
    }


def _normalizar_escopos(escopos=None):
    aliases = {
        "divida": "divida",
        "dividas": "divida",
        "orcamento": "orcamento",
        "orcamentos": "orcamento",
        "evento": "evento",
        "eventos": "evento",
    }
    if not escopos:
        return {"divida", "evento", "orcamento"}

    normalizados = set()
    for escopo in escopos:
        chave = str(escopo or "").strip().lower()
        if chave not in aliases:
            raise ValueError(f"Escopo de valores editaveis invalido: {escopo}.")
        normalizados.add(aliases[chave])
    return normalizados


def _normalizar_object_ids(object_ids=None):
    if not object_ids:
        return None

    return {int(object_id) for object_id in object_ids}


def _serializar_filtros(filtros):
    return {
        "scopes": sorted(filtros["escopos"]),
        "objectIds": sorted(filtros["object_ids"] or []),
    }


def _corrigir_dividas(resultado):
    correcoes = []
    dividas_ids = _ids_por_escopo(resultado, "divida")

    for divida in DividaFinanceira.objects.filter(id__in=dividas_ids).order_by("id"):
        try:
            with transaction.atomic():
                resumo = divida.sincronizar_parcelas_contratadas()
        except ValidationError as erro:
            correcoes.append({
                "scope": "divida",
                "objectId": divida.id,
                "status": "blocked",
                "message": str(erro),
            })
            continue

        correcoes.append({
            "scope": "divida",
            "objectId": divida.id,
            "status": "applied",
            "summary": resumo,
        })

    return correcoes


def _corrigir_orcamentos(resultado):
    from caixa.services_sincronizacao import sincronizar_evento_financeiro

    correcoes = []
    orcamentos_ids = _ids_por_escopo(resultado, "orcamento")

    for orcamento in Orcamento.objects.filter(id__in=orcamentos_ids).order_by("id"):
        try:
            with transaction.atomic():
                orcamento.recalcular_totais()
                orcamento.refresh_from_db()
                evento = orcamento.sincronizar_evento_aprovado(
                    sincronizar_receita_operacional=_possui_issue(
                        resultado,
                        "orcamento",
                        orcamento.id,
                        "receita_operacional_ausente",
                    ),
                    sincronizar_custos_servico=False,
                )
                if evento:
                    sincronizar_evento_financeiro(evento)
        except ValidationError as erro:
            correcoes.append({
                "scope": "orcamento",
                "objectId": orcamento.id,
                "status": "blocked",
                "message": str(erro),
            })
            continue

        correcoes.append({
            "scope": "orcamento",
            "objectId": orcamento.id,
            "status": "applied" if evento else "not_applicable",
        })

    return correcoes


def _corrigir_eventos(resultado):
    from caixa.services_sincronizacao import sincronizar_evento_financeiro

    correcoes = []
    eventos_ids = _ids_por_escopo(resultado, "evento")

    for evento in Evento.objects.filter(id__in=eventos_ids).order_by("id"):
        try:
            with transaction.atomic():
                sincronizar_evento_financeiro(evento)
                evento.refresh_from_db()
                evento.recalcular_receita_prevista()
        except ValidationError as erro:
            correcoes.append({
                "scope": "evento",
                "objectId": evento.id,
                "status": "blocked",
                "message": str(erro),
            })
            continue

        correcoes.append({
            "scope": "evento",
            "objectId": evento.id,
            "status": "applied",
        })

    return correcoes


def _ids_por_escopo(resultado, escopo):
    return resultado["targets"].get(escopo, [])


def _possui_issue(resultado, escopo, objeto_id, codigo):
    return any(
        issue.get("scope") == escopo
        and issue.get("objectId") == objeto_id
        and issue.get("code") == codigo
        for issue in resultado.get("issues", [])
    )


def _montar_plano_correcao(resultado, limit):
    itens = []

    for escopo in ("divida", "evento", "orcamento"):
        for object_id in sorted(resultado["targets"].get(escopo, [])):
            itens.append({
                "scope": escopo,
                "objectId": object_id,
                "auditCommand": (
                    "python manage.py verificar_integridade_valores_editaveis "
                    f"--escopo={escopo} --object-id={object_id}"
                ),
                "applyCommand": (
                    "python manage.py verificar_integridade_valores_editaveis "
                    f"--escopo={escopo} --object-id={object_id} "
                    "--corrigir --falhar-com-inconsistencia"
                ),
                "validationCommand": (
                    "python manage.py validar_operacao_obrigacoes "
                    "--validar-valores-editaveis "
                    f"--valores-editaveis-escopo={escopo} "
                    f"--valores-editaveis-object-id={object_id} "
                    "--falhar-com-valores-editaveis"
                ),
            })

    return {
        "totalTargets": len(itens),
        "items": itens[:limit],
    }


def _auditar_divida(divida, resultado, limit):
    if divida.quantidade_parcelas < 1:
        _adicionar_issue(
            resultado,
            limit,
            "divida",
            divida.id,
            "quantidade_parcelas_invalida",
            "Quantidade de parcelas menor que 1.",
        )
        return

    parcelas = list(divida.parcelas.all())
    parcelas_por_numero = {parcela.numero_parcela: parcela for parcela in parcelas}
    valores = divida.valores_principais_parcelas(divida.quantidade_parcelas)

    for numero, valor_esperado in enumerate(valores, start=1):
        parcela = parcelas_por_numero.get(numero)
        vencimento_esperado = divida.data_vencimento_parcela(numero)

        if parcela is None:
            _adicionar_issue(
                resultado,
                limit,
                "divida",
                divida.id,
                "parcela_ausente",
                f"Parcela {numero} ausente.",
            )
            continue

        if parcela.valor_principal != valor_esperado:
            _adicionar_issue(
                resultado,
                limit,
                "divida",
                divida.id,
                "valor_parcela_desatualizado",
                (
                    f"Parcela {numero} usa {parcela.valor_principal}, "
                    f"esperado {valor_esperado}."
                ),
            )

        if parcela.data_vencimento_original != vencimento_esperado:
            _adicionar_issue(
                resultado,
                limit,
                "divida",
                divida.id,
                "vencimento_original_desatualizado",
                (
                    f"Parcela {numero} vence originalmente em "
                    f"{parcela.data_vencimento_original}, esperado "
                    f"{vencimento_esperado}."
                ),
            )

        if (
            parcela.status not in STATUS_PARCELA_NAO_REPROGRAMA_VENCIMENTO
            and parcela.data_vencimento_atual != vencimento_esperado
        ):
            _adicionar_issue(
                resultado,
                limit,
                "divida",
                divida.id,
                "vencimento_atual_desatualizado",
                (
                    f"Parcela {numero} vence em {parcela.data_vencimento_atual}, "
                    f"esperado {vencimento_esperado}."
                ),
            )

    for parcela in parcelas:
        if parcela.numero_parcela > divida.quantidade_parcelas:
            _adicionar_issue(
                resultado,
                limit,
                "divida",
                divida.id,
                "parcela_excedente",
                (
                    f"Parcela {parcela.numero_parcela} excede a quantidade "
                    f"contratada {divida.quantidade_parcelas}."
                ),
            )


def _auditar_orcamento_aprovado(orcamento, resultado, limit):
    esperado = _totais_orcamento_por_itens(orcamento)

    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "subtotal_custos_desatualizado",
        orcamento.subtotal_custos,
        esperado["subtotal_custos"],
    )
    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "total_impostos_desatualizado",
        orcamento.total_impostos,
        esperado["total_impostos"],
    )
    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "total_lucro_desatualizado",
        orcamento.total_lucro,
        esperado["total_lucro"],
    )
    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "total_venda_desatualizado",
        orcamento.total_venda,
        esperado["total_venda"],
    )

    try:
        evento = orcamento.evento
    except Exception:
        _adicionar_issue(
            resultado,
            limit,
            "orcamento",
            orcamento.id,
            "evento_aprovado_ausente",
            "Orçamento aprovado não possui evento gerado.",
        )
        return

    receita_prevista_evento = _receita_prevista_operacional_evento(evento)
    custo_previsto_evento = _custo_previsto_operacional_evento(evento)
    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "evento_valor_previsto_desatualizado",
        evento.valor_total_previsto,
        receita_prevista_evento,
    )
    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "evento_custo_previsto_desatualizado",
        evento.custo_total_previsto,
        custo_previsto_evento,
    )
    _comparar_valor(
        resultado,
        limit,
        "orcamento",
        orcamento.id,
        "evento_lucro_previsto_desatualizado",
        evento.lucro_previsto,
        quantizar_moeda(receita_prevista_evento - custo_previsto_evento),
    )

    _auditar_receita_prevista_orcamento(orcamento, evento, resultado, limit)
    _auditar_custos_operacionais_evento(orcamento, evento, resultado, limit)


def _auditar_evento(evento, resultado, limit):
    receita_prevista = _receita_prevista_operacional_evento(evento)
    custo_previsto = _custo_previsto_operacional_evento(evento)
    receita_realizada = _receita_realizada_operacional_evento(evento)
    custo_realizado = _custo_realizado_operacional_evento(evento)

    _comparar_valor(
        resultado,
        limit,
        "evento",
        evento.id,
        "receita_prevista_desatualizada",
        evento.valor_total_previsto,
        receita_prevista,
    )
    _comparar_valor(
        resultado,
        limit,
        "evento",
        evento.id,
        "custo_previsto_desatualizado",
        evento.custo_total_previsto,
        custo_previsto,
    )
    _comparar_valor(
        resultado,
        limit,
        "evento",
        evento.id,
        "resultado_previsto_desatualizado",
        evento.lucro_previsto,
        quantizar_moeda(receita_prevista - custo_previsto),
    )
    _comparar_valor(
        resultado,
        limit,
        "evento",
        evento.id,
        "receita_realizada_desatualizada",
        evento.valor_total_realizado,
        receita_realizada,
    )
    _comparar_valor(
        resultado,
        limit,
        "evento",
        evento.id,
        "custo_realizado_desatualizado",
        evento.custo_total_realizado,
        custo_realizado,
    )
    _comparar_valor(
        resultado,
        limit,
        "evento",
        evento.id,
        "resultado_realizado_desatualizado",
        evento.lucro_realizado,
        quantizar_moeda(receita_realizada - custo_realizado),
    )

    if not evento.despesas.exists() and evento.custos_servicos.exists():
        _adicionar_issue(
            resultado,
            limit,
            "evento",
            evento.id,
            "despesas_operacionais_ausentes",
            "Evento possui custos de servico, mas nao possui despesas operacionais sincronizadas.",
        )


def _auditar_receita_prevista_orcamento(orcamento, evento, resultado, limit):
    receitas = list(evento.receitas.all())
    if not receitas:
        _adicionar_issue(
            resultado,
            limit,
            "orcamento",
            orcamento.id,
            "receita_operacional_ausente",
            "Evento aprovado nao possui receita operacional prevista.",
        )


def _receita_prevista_operacional_evento(evento):
    return quantizar_moeda(
        sum((receita.valor_previsto for receita in evento.receitas.all()), ZERO)
    )


def _custo_previsto_operacional_evento(evento):
    return quantizar_moeda(
        sum((despesa.valor_previsto for despesa in evento.despesas.all()), ZERO)
    )


def _receita_realizada_operacional_evento(evento):
    return quantizar_moeda(
        sum((receita.valor_recebido for receita in evento.receitas.all()), ZERO)
    )


def _custo_realizado_operacional_evento(evento):
    return quantizar_moeda(
        sum((despesa.valor_pago for despesa in evento.despesas.all()), ZERO)
    )


def _auditar_custos_operacionais_evento(orcamento, evento, resultado, limit):
    if not evento.despesas.exists() and evento.custos_servicos.exists():
        _adicionar_issue(
            resultado,
            limit,
            "orcamento",
            orcamento.id,
            "despesas_operacionais_ausentes",
            "Evento possui custos de servico, mas nao possui despesas operacionais sincronizadas.",
        )


def _auditar_custos_servico_orcamento(orcamento, evento, resultado, limit):
    esperados = _custos_servico_esperados(orcamento)
    custos = list(evento.custos_servicos.all())
    custos_por_servico = {custo.servico_id: custo for custo in custos}

    for servico_id, esperado in esperados.items():
        custo = custos_por_servico.get(servico_id)
        if custo is None:
            _adicionar_issue(
                resultado,
                limit,
                "orcamento",
                orcamento.id,
                "custo_servico_ausente",
                f"Custo de serviço {servico_id} ausente no evento.",
            )
            continue

        for campo in ("valor_diarias", "valor_alimentacao", "valor_transporte"):
            _comparar_valor(
                resultado,
                limit,
                "orcamento",
                orcamento.id,
                f"custo_servico_{campo}_desatualizado",
                getattr(custo, campo),
                esperado[campo],
            )

    for custo in custos:
        if custo.servico_id in esperados:
            continue

        possui_movimento = custo_servico_possui_movimento(custo)
        total_previsto = quantizar_moeda(
            custo.valor_diarias + custo.valor_alimentacao + custo.valor_transporte
        )
        if possui_movimento and total_previsto > ZERO:
            _adicionar_issue(
                resultado,
                limit,
                "orcamento",
                orcamento.id,
                "custo_servico_excedente_com_movimento",
                (
                    f"Custo de serviço {custo.servico_id} removido do orçamento "
                    "mantém valor previsto apesar de possuir movimento."
                ),
            )
        elif not possui_movimento:
            _adicionar_issue(
                resultado,
                limit,
                "orcamento",
                orcamento.id,
                "custo_servico_excedente",
                f"Custo de serviço {custo.servico_id} não existe mais no orçamento.",
            )


def _totais_orcamento_por_itens(orcamento):
    itens = list(orcamento.itens.all())
    return {
        "subtotal_custos": quantizar_moeda(
            sum((item.custo_total for item in itens), ZERO)
        ),
        "total_impostos": quantizar_moeda(
            sum((item.valor_imposto for item in itens), ZERO)
        ),
        "total_lucro": quantizar_moeda(sum((item.lucro for item in itens), ZERO)),
        "total_venda": quantizar_moeda(
            sum((item.preco_venda for item in itens), ZERO)
        ),
    }


def _custos_servico_esperados(orcamento):
    totais = {}
    for item in orcamento.itens.all():
        totais.setdefault(
            item.servico_id,
            {
                "valor_diarias": ZERO,
                "valor_alimentacao": ZERO,
                "valor_transporte": ZERO,
            },
        )
        totais[item.servico_id]["valor_diarias"] += item.custo_servico_total
        totais[item.servico_id]["valor_alimentacao"] += item.gasto_alimentacao_total
        totais[item.servico_id]["valor_transporte"] += item.gasto_transporte_total

    return {
        servico_id: {
            campo: quantizar_moeda(valor)
            for campo, valor in valores.items()
        }
        for servico_id, valores in totais.items()
    }


def _comparar_valor(resultado, limit, escopo, objeto_id, codigo, atual, esperado):
    atual = quantizar_moeda(atual)
    esperado = quantizar_moeda(esperado)
    if atual == esperado:
        return

    _adicionar_issue(
        resultado,
        limit,
        escopo,
        objeto_id,
        codigo,
        f"Valor atual {atual}, esperado {esperado}.",
    )


def _adicionar_issue(resultado, limit, escopo, objeto_id, codigo, mensagem):
    resultado["totalIssues"] += 1
    if objeto_id not in resultado["targets"][escopo]:
        resultado["targets"][escopo].append(objeto_id)
    if len(resultado["issues"]) >= limit:
        return

    resultado["issues"].append({
        "scope": escopo,
        "objectId": objeto_id,
        "code": codigo,
        "message": mensagem,
    })
