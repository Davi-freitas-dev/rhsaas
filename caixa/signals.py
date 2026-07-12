from django.db import connection, connections, transaction
from django.db.models.signals import post_migrate, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from .models import DespesaOperacional, Evento, Orcamento, OrcamentoItem, ReceitaOperacional
from .models_servico import EventoCustoServico
from .models_custo_fixo import CustoFixo
from .models_custos_extras import EventoCustoExtra
from .models_dividas import DividaFinanceira, PagamentoParcelaDivida, ParcelaDivida
from .models_fcf import FinanciamentoMovimentacao
from .models_fci import Investimento
from .models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from .permissions import sincronizar_grupos_permissoes
from .services_lancamentos import (
    sincronizar_lancamento_despesa_manual,
    sincronizar_lancamento_custo_fixo,
    sincronizar_lancamento_financiamento,
    sincronizar_lancamento_investimento,
    sincronizar_lancamento_pagamento_custo_extra,
    sincronizar_lancamento_pagamento_custo_servico,
    sincronizar_lancamento_pagamento_parcela,
    sincronizar_lancamento_receita,
)
from .services_modelagem_canonica import (
    sincronizar_baixa_canonica_por_origem,
    sincronizar_obrigacao_custo_extra_canonica,
    sincronizar_obrigacao_custo_fixo_canonica,
    sincronizar_obrigacao_despesa_manual_canonica,
    sincronizar_obrigacao_financiamento_canonica,
    sincronizar_obrigacao_investimento_canonica,
    sincronizar_obrigacao_parcela_divida_canonica,
    sincronizar_obrigacao_receita_canonica,
    sincronizar_obrigacoes_custo_servico_canonicas,
)
from .services_dividas_fcf import sincronizar_entrada_fcf_divida
from .services_pagamentos_servico import sincronizar_pagamento_servico_e_recalcular_evento
from .services_sincronizacao import sincronizar_evento_financeiro

@receiver(post_migrate)
def criar_grupos_permissoes(sender, using, **kwargs):
    if sender.name != "caixa":
        return

    schema_name = getattr(connections[using], "schema_name", None)
    if not schema_name or schema_name == get_public_schema_name():
        return

    sincronizar_grupos_permissoes()


@receiver(post_save, sender=EventoCustoServico)
def atualizar_despesas_apos_salvar_custo_servico(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_evento_financeiro(instance.evento)
    sincronizar_obrigacoes_custo_servico_canonicas(instance)


@receiver(post_delete, sender=EventoCustoServico)
def atualizar_despesas_apos_excluir_custo_servico(sender, instance, **kwargs):
    sincronizar_evento_financeiro(instance.evento)


@receiver(post_save, sender=EventoCustoExtra)
def atualizar_despesas_apos_salvar_custo_extra(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_evento_financeiro(instance.evento)
    sincronizar_obrigacao_custo_extra_canonica(instance)


@receiver(post_delete, sender=EventoCustoExtra)
def atualizar_despesas_apos_excluir_custo_extra(sender, instance, **kwargs):
    sincronizar_evento_financeiro(instance.evento)


@receiver(post_delete, sender=OrcamentoItem)
def recalcular_orcamento_apos_excluir_item(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    orcamento = Orcamento.objects.filter(pk=instance.orcamento_id).first()
    if not orcamento:
        return

    orcamento.recalcular_totais()
    orcamento.sincronizar_evento_aprovado()


@receiver(post_save, sender=PagamentoEventoCustoServico)
def atualizar_despesas_apos_salvar_pagamento_servico(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_pagamento_servico_e_recalcular_evento(instance.custo_servico.evento)
    sincronizar_obrigacoes_custo_servico_canonicas(instance.custo_servico)


@receiver(post_delete, sender=PagamentoEventoCustoServico)
def atualizar_despesas_apos_excluir_pagamento_servico(sender, instance, **kwargs):
    sincronizar_pagamento_servico_e_recalcular_evento(instance.custo_servico.evento)
    sincronizar_obrigacoes_custo_servico_canonicas(instance.custo_servico)


@receiver(post_delete, sender=ReceitaOperacional)
@receiver(post_delete, sender=DespesaOperacional)
def recalcular_evento_apos_excluir_movimento(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    recalcular_evento_realizado_apos_commit(instance.evento_id)
    if sender is ReceitaOperacional:
        recalcular_evento_receita_prevista_apos_commit(instance.evento_id)
    if sender is DespesaOperacional:
        recalcular_evento_custo_previsto_apos_commit(instance.evento_id)


@receiver(post_delete, sender=PagamentoParcelaDivida)
def recalcular_parcela_apos_excluir_pagamento(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    recalcular_parcela_divida_apos_commit(instance.parcela_id)


@receiver(post_delete, sender=ParcelaDivida)
def atualizar_divida_apos_excluir_parcela(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    atualizar_status_divida_apos_commit(instance.divida_id)


@receiver(post_save, sender=ParcelaDivida)
def sincronizar_obrigacao_apos_salvar_parcela(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_obrigacao_parcela_divida_canonica(instance)


@receiver(post_save, sender=DividaFinanceira)
def sincronizar_obrigacoes_apos_salvar_divida(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_entrada_fcf_divida(instance)
    for parcela in instance.parcelas.all():
        sincronizar_obrigacao_parcela_divida_canonica(parcela)


def recalcular_evento_realizado_apos_commit(evento_id):
    def recalcular():
        try:
            evento = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            return

        evento.recalcular_realizado()

    if connection.in_atomic_block:
        recalcular()
        return

    transaction.on_commit(recalcular)


def recalcular_evento_receita_prevista_apos_commit(evento_id):
    def recalcular():
        try:
            evento = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            return

        evento.recalcular_receita_prevista()

    # Na aprovação do orçamento, a receita é criada dentro de uma transação
    # abrangente. O recálculo precisa falhar dentro dela para permitir rollback.
    if connection.in_atomic_block:
        recalcular()
        return

    transaction.on_commit(recalcular)


def recalcular_evento_custo_previsto_apos_commit(evento_id):
    def recalcular():
        try:
            evento = Evento.objects.get(pk=evento_id)
        except Evento.DoesNotExist:
            return

        evento.recalcular_custo_previsto()

    if connection.in_atomic_block:
        recalcular()
        return

    transaction.on_commit(recalcular)


def recalcular_parcela_divida_apos_commit(parcela_id):
    def recalcular():
        try:
            parcela = ParcelaDivida.objects.get(pk=parcela_id)
        except ParcelaDivida.DoesNotExist:
            return

        parcela.recalcular_pagamento()
        sincronizar_obrigacao_parcela_divida_canonica(parcela)

    transaction.on_commit(recalcular)


def atualizar_status_divida_apos_commit(divida_id):
    def atualizar():
        try:
            divida = DividaFinanceira.objects.get(pk=divida_id)
        except DividaFinanceira.DoesNotExist:
            return

        divida.atualizar_status()
        DividaFinanceira.objects.filter(pk=divida_id).update(
            status=divida.status,
            atualizado_em=timezone.now(),
        )

    transaction.on_commit(atualizar)


@receiver(post_save, sender=ReceitaOperacional)
def sincronizar_lancamento_apos_salvar_receita(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_receita(instance)
    sincronizar_obrigacao_receita_canonica(instance)
    sincronizar_baixa_canonica_por_origem("receita_operacional", instance)
    recalcular_evento_receita_prevista_apos_commit(instance.evento_id)


@receiver(post_save, sender=DespesaOperacional)
def sincronizar_lancamento_apos_salvar_despesa(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_despesa_manual(instance)
    sincronizar_obrigacao_despesa_manual_canonica(instance)
    sincronizar_baixa_canonica_por_origem("despesa_operacional", instance)
    recalcular_evento_custo_previsto_apos_commit(instance.evento_id)


@receiver(post_save, sender=CustoFixo)
def sincronizar_lancamento_apos_salvar_custo_fixo(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_custo_fixo(instance)
    sincronizar_obrigacao_custo_fixo_canonica(instance)
    sincronizar_baixa_canonica_por_origem("custo_fixo", instance)


@receiver(post_save, sender=PagamentoEventoCustoServico)
def sincronizar_lancamento_apos_salvar_pagamento_servico(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_pagamento_custo_servico(instance)
    sincronizar_obrigacoes_custo_servico_canonicas(instance.custo_servico)
    sincronizar_baixa_canonica_por_origem("pagamento_custo_servico", instance)


@receiver(post_save, sender=PagamentoEventoCustoExtra)
def sincronizar_lancamento_apos_salvar_pagamento_extra(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_pagamento_custo_extra(instance)
    sincronizar_obrigacao_custo_extra_canonica(instance.custo_extra)
    sincronizar_baixa_canonica_por_origem("pagamento_custo_extra", instance)


@receiver(post_delete, sender=PagamentoEventoCustoExtra)
def sincronizar_obrigacao_apos_excluir_pagamento_extra(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_obrigacao_custo_extra_canonica(instance.custo_extra)


@receiver(post_save, sender=PagamentoParcelaDivida)
def sincronizar_lancamento_apos_salvar_pagamento_parcela(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_pagamento_parcela(instance)
    sincronizar_obrigacao_parcela_divida_canonica(instance.parcela)
    sincronizar_baixa_canonica_por_origem("pagamento_parcela_divida", instance)


@receiver(post_save, sender=Investimento)
def sincronizar_lancamento_apos_salvar_investimento(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_investimento(instance)
    sincronizar_obrigacao_investimento_canonica(instance)
    sincronizar_baixa_canonica_por_origem("investimento", instance)


@receiver(post_save, sender=FinanciamentoMovimentacao)
def sincronizar_lancamento_apos_salvar_financiamento(sender, instance, **kwargs):
    if kwargs.get("raw"):
        return

    sincronizar_lancamento_financiamento(instance)
    sincronizar_obrigacao_financiamento_canonica(instance)
    sincronizar_baixa_canonica_por_origem("financiamento_movimentacao", instance)
