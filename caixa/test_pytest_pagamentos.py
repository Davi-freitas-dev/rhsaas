from decimal import Decimal

import pytest

from .forms_pagamentos import PagamentoEventoCustoExtraForm
from .selectors_pagamentos import listar_custos_extras, listar_custos_servico
from .services_pagamentos_custos_extras import registrar_pagamento_custo_extra_com_lock


@pytest.mark.django_db
def test_selector_custos_servico_prefetch_evita_n_plus_one(
    django_assert_num_queries,
    evento_custo_servico_factory,
    investimento_factory,
    pagamento_evento_custo_servico_factory,
):
    investimento_factory()
    custo_a = evento_custo_servico_factory(valor_diarias=Decimal("100.00"))
    custo_b = evento_custo_servico_factory(valor_diarias=Decimal("200.00"))
    pagamento_evento_custo_servico_factory(
        custo_servico=custo_a,
        tipo="diarias",
        valor_pagamento=Decimal("40.00"),
    )
    pagamento_evento_custo_servico_factory(
        custo_servico=custo_b,
        tipo="diarias",
        valor_pagamento=Decimal("50.00"),
    )

    filtros = {"busca": "", "evento": "", "tipo": "", "situacao": "todos"}

    with django_assert_num_queries(2):
        custos = listar_custos_servico(filtros)
        saldos = [custo.saldo_diarias for custo in custos]

    assert saldos == [Decimal("60.00"), Decimal("150.00")]


@pytest.mark.django_db
def test_selector_custos_extras_prefetch_evita_n_plus_one(
    django_assert_num_queries,
    evento_custo_extra_factory,
    investimento_factory,
    pagamento_evento_custo_extra_factory,
):
    investimento_factory()
    custo_a = evento_custo_extra_factory(valor_previsto=Decimal("100.00"))
    custo_b = evento_custo_extra_factory(valor_previsto=Decimal("200.00"))
    pagamento_evento_custo_extra_factory(
        custo_extra=custo_a,
        valor_pagamento=Decimal("40.00"),
    )
    pagamento_evento_custo_extra_factory(
        custo_extra=custo_b,
        valor_pagamento=Decimal("50.00"),
    )

    filtros = {"busca": "", "evento": "", "categoria": "", "situacao": "todos"}

    with django_assert_num_queries(2):
        custos = listar_custos_extras(filtros)
        saldos = [custo.saldo_a_pagar for custo in custos]

    assert saldos == [Decimal("60.00"), Decimal("150.00")]


@pytest.mark.django_db
def test_service_custo_extra_revalida_saldo_stale_form_com_factory(
    evento_custo_extra_factory,
    investimento_factory,
    pagamento_evento_custo_extra_factory,
    user_factory,
):
    investimento_factory()
    usuario = user_factory()
    custo_extra = evento_custo_extra_factory(valor_previsto=Decimal("100.00"))
    form = PagamentoEventoCustoExtraForm(
        {
            "custo_extra": str(custo_extra.id),
            "descricao": "",
            "valor_pagamento": "100.00",
            "data_pagamento": "2026-05-10",
            "observacao": "",
        },
    )
    assert form.is_valid(), form.errors

    pagamento_evento_custo_extra_factory(
        custo_extra=custo_extra,
        valor_pagamento=Decimal("80.00"),
    )

    form = registrar_pagamento_custo_extra_com_lock(form, usuario)

    assert form.pagamento_registrado is False
    assert "valor_pagamento" in form.errors
    assert custo_extra.pagamentos.count() == 1
