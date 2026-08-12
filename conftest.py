import uuid

import pytest
from django.db import connection
from pytest_factoryboy import register

from caixa.factories import (
    ClienteFactory,
    DividaFinanceiraFactory,
    EventoCustoExtraFactory,
    EventoCustoServicoFactory,
    EventoFactory,
    InvestimentoFactory,
    PagamentoEventoCustoExtraFactory,
    PagamentoEventoCustoServicoFactory,
    PagamentoParcelaDividaFactory,
    ParcelaDividaFactory,
    ServicoFactory,
    UserFactory,
)
from tenancy.models import Domain, Tenant


register(UserFactory)
register(ClienteFactory)
register(ServicoFactory)
register(EventoFactory)
register(EventoCustoServicoFactory)
register(EventoCustoExtraFactory)
register(DividaFinanceiraFactory)
register(ParcelaDividaFactory)
register(PagamentoParcelaDividaFactory)
register(PagamentoEventoCustoServicoFactory)
register(PagamentoEventoCustoExtraFactory)
register(InvestimentoFactory)


@pytest.fixture(scope="session")
def tenant_pytest(django_db_setup, django_db_blocker):
    schema_name = f"pytest_{uuid.uuid4().hex[:12]}"
    domain_name = f"{schema_name}.testserver"

    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        tenant = Tenant(schema_name=schema_name, name=f"Pytest {schema_name}")
        tenant.save(verbosity=0)
        Domain.objects.create(
            tenant=tenant,
            domain=domain_name,
            is_primary=True,
        )

    yield tenant

    with django_db_blocker.unblock():
        connection.set_schema_to_public()
        if Tenant.objects.filter(pk=tenant.pk).exists():
            tenant.delete(force_drop=True)
        connection.set_schema_to_public()


@pytest.fixture
def tenant_db(db, tenant_pytest):
    connection.set_tenant(tenant_pytest)
    try:
        yield tenant_pytest
    finally:
        connection.set_schema_to_public()
