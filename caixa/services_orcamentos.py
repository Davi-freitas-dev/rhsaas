from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .models_custos_extras import EventoCustoExtra
from .models_servico import EventoCustoServico
from .utils_eventos import gerar_numero_evento_orcamento
from .utils_financeiros import decimal_zero, quantizar_moeda


def sincronizar_custos_servicos_orcamento(orcamento, evento):
    itens = orcamento.itens.select_related("servico").all()

    totais_por_servico = {}
    servicos_processados = []

    for item in itens:
        if not item.servico_id:
            continue

        if item.servico_id not in totais_por_servico:
            totais_por_servico[item.servico_id] = {
                "servico": item.servico,
                "valor_diarias": Decimal("0.00"),
                "valor_alimentacao": Decimal("0.00"),
                "valor_transporte": Decimal("0.00"),
            }

        totais_por_servico[item.servico_id]["valor_diarias"] += item.custo_servico_total
        totais_por_servico[item.servico_id]["valor_alimentacao"] += item.gasto_alimentacao_total
        totais_por_servico[item.servico_id]["valor_transporte"] += item.gasto_transporte_total

    for servico_id, dados in totais_por_servico.items():
        custo_evento, _ = EventoCustoServico.objects.get_or_create(
            evento=evento,
            servico=dados["servico"],
            defaults={
                "valor_diarias": Decimal("0.00"),
                "valor_alimentacao": Decimal("0.00"),
                "valor_transporte": Decimal("0.00"),
            },
        )

        custo_evento.valor_diarias = quantizar_moeda(dados["valor_diarias"])
        custo_evento.valor_alimentacao = quantizar_moeda(dados["valor_alimentacao"])
        custo_evento.valor_transporte = quantizar_moeda(dados["valor_transporte"])
        custo_evento.save()

        servicos_processados.append(servico_id)

    custos_excedentes = EventoCustoServico.objects.filter(evento=evento).exclude(
        servico_id__in=servicos_processados,
    )
    for custo_excedente in custos_excedentes:
        if custo_servico_possui_movimento(custo_excedente):
            custo_excedente.valor_diarias = Decimal("0.00")
            custo_excedente.valor_alimentacao = Decimal("0.00")
            custo_excedente.valor_transporte = Decimal("0.00")
            custo_excedente.save(
                update_fields=[
                    "valor_diarias",
                    "valor_alimentacao",
                    "valor_transporte",
                    "atualizado_em",
                ]
            )
            continue

        custo_excedente.delete()


def sincronizar_custos_extras_orcamento(orcamento, evento):
    custos_extras = orcamento.custos_extras.all().order_by("id")

    for custo_orcamento in custos_extras:
        custo_evento = custo_orcamento.evento_custo_extra
        if not custo_evento or custo_evento.evento_id != evento.id:
            custo_evento = EventoCustoExtra(
                evento=evento,
                valor_pago=Decimal("0.00"),
            )

        custo_evento.evento = evento
        custo_evento.categoria = custo_orcamento.categoria
        custo_evento.descricao = custo_orcamento.descricao
        custo_evento.valor_previsto = quantizar_moeda(
            custo_orcamento.valor_previsto
        )
        custo_evento.data_vencimento = custo_orcamento.data_vencimento
        custo_evento.observacao = custo_orcamento.observacao
        custo_evento.save()

        if custo_orcamento.evento_custo_extra_id != custo_evento.id:
            custo_orcamento.evento_custo_extra = custo_evento
            custo_orcamento.save(update_fields=["evento_custo_extra", "atualizado_em"])


def sincronizar_imposto_orcamento(orcamento, evento):
    from .models import DespesaOperacional

    valor_imposto = quantizar_moeda(orcamento.total_impostos)
    despesas = list(
        DespesaOperacional.objects.filter(
            evento=evento,
            categoria="imposto",
            descricao="Imposto previsto",
        ).order_by("id")
    )

    if not despesas and valor_imposto <= Decimal("0.00"):
        return

    if despesas:
        despesa_principal = despesas[0]
        despesas_duplicadas = despesas[1:]
    else:
        despesa_principal = DespesaOperacional(
            evento=evento,
            descricao="Imposto previsto",
            categoria="imposto",
            valor_pago=Decimal("0.00"),
            data_vencimento=evento.data_inicio,
        )
        despesas_duplicadas = []

    valor_pago_total = quantizar_moeda(
        sum((decimal_zero(despesa.valor_pago) for despesa in despesas), Decimal("0.00"))
    )

    despesa_principal.descricao = "Imposto previsto"
    despesa_principal.categoria = "imposto"
    despesa_principal.valor_previsto = valor_imposto
    despesa_principal.valor_pago = valor_pago_total
    despesa_principal.data_vencimento = evento.data_inicio
    despesa_principal.origem = DespesaOperacional.ORIGEM_MANUAL
    despesa_principal.origem_custo_servico_tipo = ""
    despesa_principal.origem_custo_extra = None

    if valor_imposto == Decimal("0.00") and valor_pago_total == Decimal("0.00"):
        despesa_principal.status = "cancelado"
    elif valor_pago_total <= Decimal("0.00"):
        despesa_principal.status = "pendente"
    elif valor_pago_total < valor_imposto:
        despesa_principal.status = "parcial"
    else:
        despesa_principal.status = "pago"

    despesa_principal.save()

    if despesas_duplicadas:
        DespesaOperacional.objects.filter(
            id__in=[despesa.id for despesa in despesas_duplicadas]
        ).delete()


def custo_servico_possui_movimento(custo_servico):
    return (
        custo_servico.pagamentos.exists()
        or custo_servico.diarias_quitadas
        or custo_servico.alimentacao_quitada
        or custo_servico.transporte_quitado
    )


def criar_ou_atualizar_evento_do_orcamento(orcamento):
    from .models import Evento

    evento = Evento.objects.filter(orcamento=orcamento).first()
    criado = evento is None

    if criado:
        numero_evento = gerar_numero_evento_orcamento(orcamento.numero)
        _validar_numero_evento_disponivel(
            Evento,
            numero_evento,
            orcamento,
        )
        dados_evento = {
            "orcamento": orcamento,
            "cliente": orcamento.cliente,
            "numero": numero_evento,
            "nome_evento": orcamento.nome_evento,
            "data_inicio": orcamento.data_evento,
            "data_fim": orcamento.data_evento,
            "local": orcamento.local,
            "status": "planejado",
            "observacoes": orcamento.observacoes,
            "valor_total_previsto": orcamento.total_venda,
            "custo_total_previsto": quantizar_moeda(
                orcamento.subtotal_custos + orcamento.total_impostos
            ),
            "lucro_previsto": orcamento.total_lucro,
        }

        try:
            # O savepoint permite converter uma colisão concorrente sem deixar
            # a transação externa de aprovação inutilizável.
            with transaction.atomic():
                evento = Evento.objects.create(**dados_evento)
        except IntegrityError as error:
            evento_concorrente = Evento.objects.filter(orcamento=orcamento).first()
            if evento_concorrente is not None:
                evento = evento_concorrente
                criado = False
            else:
                _validar_numero_evento_disponivel(
                    Evento,
                    numero_evento,
                    orcamento,
                    causa=error,
                )
                raise

    if not criado:
        evento.cliente = orcamento.cliente
        evento.nome_evento = orcamento.nome_evento
        evento.data_inicio = orcamento.data_evento
        evento.data_fim = orcamento.data_evento
        evento.local = orcamento.local
        evento.observacoes = orcamento.observacoes
        evento.valor_total_previsto = orcamento.total_venda
        evento.custo_total_previsto = quantizar_moeda(
            orcamento.subtotal_custos + orcamento.total_impostos
        )
        evento.lucro_previsto = orcamento.total_lucro
        evento.full_clean()
        evento.save()

    return evento


def _validar_numero_evento_disponivel(
    evento_model,
    numero_evento,
    orcamento,
    *,
    causa=None,
):
    conflito = (
        evento_model.objects.filter(numero=numero_evento)
        .exclude(orcamento=orcamento)
        .only("id", "orcamento_id")
        .first()
    )
    if conflito is None:
        return

    erro = ValidationError(
        {
            "numero": (
                f"Já existe outro evento com o número {numero_evento} "
                "que não pertence a este orçamento."
            )
        }
    )
    if causa is not None:
        raise erro from causa
    raise erro


def sincronizar_evento_do_orcamento_aprovado(
    orcamento,
    sincronizar_receita_operacional=True,
    sincronizar_custos_servico=True,
    sincronizar_custos_extras=True,
):
    from .models import Evento

    if orcamento.status != "aprovado":
        return None

    try:
        evento_atual = orcamento.evento
    except Evento.DoesNotExist:
        return None

    contexto_anterior = {
        "nome_evento": evento_atual.nome_evento,
        "data_inicio": evento_atual.data_inicio,
        "valor_total_previsto": evento_atual.valor_total_previsto,
    }
    evento = criar_ou_atualizar_evento_do_orcamento(orcamento)
    if sincronizar_receita_operacional:
        sincronizar_receita_prevista_do_evento(evento, contexto_anterior)
    else:
        evento.recalcular_receita_prevista()
    if sincronizar_custos_servico:
        sincronizar_custos_servicos_orcamento(orcamento, evento)
        sincronizar_imposto_orcamento(orcamento, evento)
    if sincronizar_custos_extras:
        sincronizar_custos_extras_orcamento(orcamento, evento)
    evento.recalcular_custo_previsto()
    return evento


def sincronizar_receita_prevista_do_evento(evento, contexto_anterior):
    from .models import ReceitaOperacional

    descricao_atual = f"Receita prevista do evento {evento.nome_evento}"
    descricao_anterior = (
        f"Receita prevista do evento {contexto_anterior['nome_evento']}"
    )
    receitas = list(ReceitaOperacional.objects.filter(evento=evento).order_by("id"))

    if not receitas:
        ReceitaOperacional.objects.create(
            evento=evento,
            cliente=evento.cliente,
            descricao=descricao_atual,
            valor_previsto=evento.valor_total_previsto,
            valor_recebido=Decimal("0.00"),
            data_vencimento=evento.data_inicio,
            status="pendente",
        )
        return

    candidatas = [
        receita
        for receita in receitas
        if receita.descricao in {descricao_atual, descricao_anterior}
    ]
    if not candidatas and len(receitas) == 1:
        candidatas = [receitas[0]]

    if len(candidatas) != 1:
        return

    receita = candidatas[0]
    receita.cliente = evento.cliente
    receita.descricao = descricao_atual
    receita.valor_previsto = evento.valor_total_previsto
    receita.data_vencimento = evento.data_inicio
    receita.save()
