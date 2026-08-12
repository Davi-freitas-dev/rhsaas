from datetime import date
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from .models import Cliente, Evento, Servico
from .models_custos_extras import EventoCustoExtra
from .models_dividas import DividaFinanceira, PagamentoParcelaDivida, ParcelaDivida
from .models_fci import Investimento
from .models_pagamentos import PagamentoEventoCustoExtra, PagamentoEventoCustoServico
from .models_servico import EventoCustoServico


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.django.Password("senha-segura")


class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cliente

    nome_razao_social = factory.Sequence(lambda n: f"Cliente Teste {n}")
    nome_fantasia = factory.Sequence(lambda n: f"Cliente {n}")
    tipo_pessoa = "PJ"
    cpf_cnpj = factory.Sequence(lambda n: f"{n:014d}")
    email = factory.Sequence(lambda n: f"cliente-{n}@example.com")


class ServicoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Servico

    nome = factory.Sequence(lambda n: f"Servico Teste {n}")
    codigo = factory.Sequence(lambda n: f"servico-teste-{n}")
    diaria_padrao = Decimal("100.00")


class EventoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Evento

    cliente = factory.SubFactory(ClienteFactory)
    numero = factory.Sequence(lambda n: f"EVT-PY-{n}")
    nome_evento = factory.Sequence(lambda n: f"Evento Pytest {n}")
    data_inicio = date(2026, 5, 1)
    data_fim = date(2026, 5, 1)


class EventoCustoServicoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventoCustoServico

    evento = factory.SubFactory(EventoFactory)
    servico = factory.SubFactory(ServicoFactory)
    valor_diarias = Decimal("100.00")
    valor_alimentacao = Decimal("20.00")
    valor_transporte = Decimal("10.00")


class EventoCustoExtraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventoCustoExtra

    evento = factory.SubFactory(EventoFactory)
    categoria = "material"
    descricao = factory.Sequence(lambda n: f"Custo extra pytest {n}")
    valor_previsto = Decimal("100.00")
    data_vencimento = date(2026, 5, 10)


class DividaFinanceiraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DividaFinanceira

    descricao = factory.Sequence(lambda n: f"Divida pytest {n}")
    credor = factory.Sequence(lambda n: f"Banco Pytest {n}")
    tipo = "financiamento"
    data_contratacao = date(2026, 5, 1)
    valor_contratado = Decimal("100.00")
    quantidade_parcelas = 1


class ParcelaDividaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ParcelaDivida

    divida = factory.SubFactory(DividaFinanceiraFactory)
    numero_parcela = factory.Sequence(lambda n: n + 1)
    data_vencimento_original = date(2026, 5, 10)
    data_vencimento_atual = date(2026, 5, 10)
    valor_principal = Decimal("100.00")


class InvestimentoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Investimento

    descricao = factory.Sequence(lambda n: f"Entrada caixa pytest {n}")
    categoria = "outros"
    tipo_fluxo = "entrada"
    valor_previsto = Decimal("10000.00")
    valor_realizado = Decimal("10000.00")
    data_prevista = date(2026, 5, 1)
    data_realizacao = date(2026, 5, 1)


class PagamentoParcelaDividaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PagamentoParcelaDivida

    parcela = factory.SubFactory(ParcelaDividaFactory)
    data_pagamento = date(2026, 5, 10)
    valor_pagamento = Decimal("40.00")
    forma_pagamento = "pix"


class PagamentoEventoCustoServicoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PagamentoEventoCustoServico

    custo_servico = factory.SubFactory(EventoCustoServicoFactory)
    tipo = "diarias"
    valor_pagamento = Decimal("40.00")
    data_pagamento = date(2026, 5, 10)


class PagamentoEventoCustoExtraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PagamentoEventoCustoExtra

    custo_extra = factory.SubFactory(EventoCustoExtraFactory)
    valor_pagamento = Decimal("40.00")
    data_pagamento = date(2026, 5, 10)
