from contextlib import contextmanager
from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context

from caixa.models import Cliente, Evento
from tenancy.models import Domain, Tenant


OPERATIONAL_GROUPS = ("Administrador", "Financeiro", "Operacional")


@contextmanager
def public_schema():
    connection.set_schema_to_public()
    try:
        yield
    finally:
        connection.set_schema_to_public()


@contextmanager
def tenant_schema(schema_name):
    with schema_context(schema_name):
        yield


def client_for_host(host):
    return Client(HTTP_HOST=host)


def host_kwargs(host):
    return {"HTTP_HOST": host}


class MultiTenantTestCase(TenantTestCase):
    primary_schema_name = "tenant_a"
    primary_tenant_name = "Tenant A"
    primary_domain = "tenant-a.localhost"
    _extra_allowed_hosts = []
    _extra_tenants = []
    _document_counter = 0

    @classmethod
    def get_test_schema_name(cls):
        return cls.primary_schema_name

    @classmethod
    def get_test_tenant_domain(cls):
        return cls.primary_domain

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = cls.primary_tenant_name

    @classmethod
    def setUpClass(cls):
        cls._extra_allowed_hosts = []
        cls._extra_tenants = []
        cls._document_counter = 0
        super().setUpClass()
        cls.primary_tenant = cls.tenant
        cls.primary_tenant_domain = cls.domain

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        for tenant in reversed(cls._extra_tenants):
            tenant.delete(force_drop=True)
        for host in cls._extra_allowed_hosts:
            cls.remove_allowed_host(host)
        super().tearDownClass()

    @classmethod
    def add_allowed_host(cls, host):
        from django.conf import settings

        if host not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS += [host]
            cls._extra_allowed_hosts.append(host)

    @classmethod
    def remove_allowed_host(cls, host):
        from django.conf import settings

        if host in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.remove(host)

    @classmethod
    def create_tenant(cls, schema_name, name, domain):
        with public_schema():
            tenant = Tenant(schema_name=schema_name, name=name)
            tenant.save(verbosity=0)
            domain_obj = Domain.objects.create(
                tenant=tenant,
                domain=domain,
                is_primary=True,
            )
        cls._extra_tenants.append(tenant)
        cls.add_allowed_host(domain)
        return tenant, domain_obj

    @classmethod
    def drop_tenant(cls, tenant):
        tenant_pk = tenant.pk
        with public_schema():
            tenant.delete(force_drop=True)
        cls._extra_tenants = [
            existing for existing in cls._extra_tenants if existing.pk != tenant_pk
        ]

    @classmethod
    def create_user(cls, schema_name, username, password="senha-segura", **extra):
        with tenant_schema(schema_name):
            return get_user_model().objects.create_user(
                username=username,
                password=password,
                **extra,
            )

    @classmethod
    def client_for_tenant(cls, tenant):
        with public_schema():
            domain = tenant.get_primary_domain().domain
        return client_for_host(domain)

    @classmethod
    def switch_to_public(cls):
        connection.set_schema_to_public()

    @classmethod
    def switch_to_tenant(cls, tenant):
        connection.set_tenant(tenant)

    @classmethod
    @contextmanager
    def in_schema(cls, schema_name):
        with tenant_schema(schema_name):
            yield

    @classmethod
    def table_names(cls, schema_name, prefix=None):
        with connection.cursor() as cursor:
            query = """
                select table_name
                  from information_schema.tables
                 where table_schema = %s
                   and table_type = 'BASE TABLE'
            """
            params = [schema_name]
            if prefix:
                query += " and table_name like %s"
                params.append(f"{prefix}%")
            query += " order by table_name"
            cursor.execute(query, params)
            return [row[0] for row in cursor.fetchall()]

    @classmethod
    def public_table_names(cls, prefix=None):
        return cls.table_names(get_public_schema_name(), prefix=prefix)

    @classmethod
    def create_basic_cliente(cls, schema_name, nome="Cliente Teste"):
        with tenant_schema(schema_name):
            cls._document_counter += 1
            return Cliente.objects.create(
                nome_razao_social=f"{nome} {cls._document_counter}",
                cpf_cnpj=f"00.000.000/0001-{cls._document_counter:02d}",
            )

    @classmethod
    def create_basic_evento(cls, schema_name, cliente=None, nome="Evento Teste"):
        with tenant_schema(schema_name):
            if cliente is None:
                cls._document_counter += 1
                cliente = Cliente.objects.create(
                    nome_razao_social=f"Cliente Teste {cls._document_counter}",
                    cpf_cnpj=f"00.000.000/0001-{cls._document_counter:02d}",
                )
            cls._document_counter += 1
            return Evento.objects.create(
                cliente=cliente,
                numero=f"EVT-{cls._document_counter:04d}",
                nome_evento=f"{nome} {cls._document_counter}",
                data_inicio=date(2026, 1, 1),
                data_fim=date(2026, 1, 1),
            )
