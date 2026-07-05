import json

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_public_schema_name

from tenancy.models import Domain, Tenant
from tenancy.test_helpers import MultiTenantTestCase, OPERATIONAL_GROUPS


class TenantIsolationInfrastructureTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, cls.secondary_domain = cls.create_tenant(
            schema_name="tenant_b",
            name="Tenant B",
            domain="tenant-b.localhost",
        )
        cls.add_allowed_host("tenant-inexistente.localhost")
        cls.tenants = {
            cls.primary_tenant.schema_name: cls.primary_tenant,
            cls.secondary_tenant.schema_name: cls.secondary_tenant,
        }

    def test_cria_dois_tenants_e_dominios(self):
        self.switch_to_public()

        self.assertEqual(
            set(Tenant.objects.values_list("schema_name", flat=True)),
            {"tenant_a", "tenant_b"},
        )
        self.assertEqual(
            set(Domain.objects.values_list("domain", flat=True)),
            {"tenant-a.localhost", "tenant-b.localhost"},
        )

    def test_resolve_schema_correto_por_host(self):
        for schema_name, host in (
            ("tenant_a", "tenant-a.localhost"),
            ("tenant_b", "tenant-b.localhost"),
        ):
            with self.subTest(host=host):
                response = self.client_for_tenant(self.tenants[schema_name]).get(
                    "/manifest.webmanifest"
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.wsgi_request.tenant.schema_name, schema_name)
                self.assertEqual(connection.schema_name, schema_name)

    def test_host_inexistente_retorna_404(self):
        response = self.client.get(
            "/manifest.webmanifest",
            HTTP_HOST="tenant-inexistente.localhost",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(connection.schema_name, get_public_schema_name())

    def test_public_continua_sem_tabelas_caixa(self):
        self.switch_to_public()

        self.assertEqual(self.public_table_names(prefix="caixa_"), [])

    def test_grupos_operacionais_existem_apenas_nos_tenants(self):
        self.switch_to_public()
        public_groups = set(
            Group.objects.filter(name__in=OPERATIONAL_GROUPS).values_list(
                "name",
                flat=True,
            )
        )
        self.assertEqual(public_groups, set())

        for schema_name in self.tenants:
            with self.subTest(schema_name=schema_name):
                with self.in_schema(schema_name):
                    tenant_groups = set(
                        Group.objects.filter(
                            name__in=OPERATIONAL_GROUPS
                        ).values_list("name", flat=True)
                    )

                self.assertEqual(tenant_groups, set(OPERATIONAL_GROUPS))


class TenantAuthSessionIsolationTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, cls.secondary_domain = cls.create_tenant(
            schema_name="tenant_b",
            name="Tenant B",
            domain="tenant-b.localhost",
        )
        cls.tenants = {
            cls.primary_tenant.schema_name: cls.primary_tenant,
            cls.secondary_tenant.schema_name: cls.secondary_tenant,
        }

    def _client_for_schema(self, schema_name):
        return self.client_for_tenant(self.tenants[schema_name])

    def _login_json(self, client, username, password):
        return client.post(
            "/api/auth/login/",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )

    def _logout_json(self, client):
        return client.post(
            "/api/auth/logout/",
            data="",
            content_type="application/json",
        )

    def _auth_session(self, client):
        return client.get("/api/auth/session/")

    def test_usuario_criado_no_tenant_a_nao_autentica_no_tenant_b(self):
        self.create_user("tenant_a", "usuario-apenas-a", "senha-tenant-a")

        response_a = self._login_json(
            self._client_for_schema("tenant_a"),
            "usuario-apenas-a",
            "senha-tenant-a",
        )
        response_b = self._login_json(
            self._client_for_schema("tenant_b"),
            "usuario-apenas-a",
            "senha-tenant-a",
        )

        self.assertEqual(response_a.status_code, 200)
        self.assertTrue(response_a.json()["authenticated"])
        self.assertEqual(response_a.wsgi_request.tenant.schema_name, "tenant_a")
        self.assertEqual(response_b.status_code, 401)
        self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")

    def test_mesmo_username_pode_existir_em_tenants_diferentes(self):
        username = "usuario-compartilhado"
        self.create_user("tenant_a", username, "senha-tenant-a")
        self.create_user("tenant_b", username, "senha-tenant-b")

        with self.in_schema("tenant_a"):
            user_a = get_user_model().objects.get(username=username)
            self.assertTrue(user_a.check_password("senha-tenant-a"))
            self.assertFalse(user_a.check_password("senha-tenant-b"))

        with self.in_schema("tenant_b"):
            user_b = get_user_model().objects.get(username=username)
            self.assertTrue(user_b.check_password("senha-tenant-b"))
            self.assertFalse(user_b.check_password("senha-tenant-a"))

    def test_cookie_de_sessao_do_tenant_a_nao_autentica_no_tenant_b(self):
        self.create_user("tenant_a", "usuario-cookie-a", "senha-cookie-a")
        client_a = self._client_for_schema("tenant_a")
        login_a = self._login_json(client_a, "usuario-cookie-a", "senha-cookie-a")
        self.assertEqual(login_a.status_code, 200)

        session_cookie = client_a.cookies[settings.SESSION_COOKIE_NAME].value
        client_b = self._client_for_schema("tenant_b")
        client_b.cookies[settings.SESSION_COOKIE_NAME] = session_cookie

        response_b = self._auth_session(client_b)

        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")
        self.assertEqual(response_b.json(), {"authenticated": False})

    def test_logout_em_um_tenant_nao_derruba_sessao_de_outro_tenant(self):
        self.create_user("tenant_a", "usuario-logout-a", "senha-logout-a")
        self.create_user("tenant_b", "usuario-logout-b", "senha-logout-b")
        client_a = self._client_for_schema("tenant_a")
        client_b = self._client_for_schema("tenant_b")

        self.assertEqual(
            self._login_json(client_a, "usuario-logout-a", "senha-logout-a").status_code,
            200,
        )
        self.assertEqual(
            self._login_json(client_b, "usuario-logout-b", "senha-logout-b").status_code,
            200,
        )

        logout_a = self._logout_json(client_a)
        session_a = self._auth_session(client_a)
        session_b = self._auth_session(client_b)

        self.assertEqual(logout_a.status_code, 200)
        self.assertEqual(logout_a.wsgi_request.tenant.schema_name, "tenant_a")
        self.assertFalse(session_a.json()["authenticated"])
        self.assertTrue(session_b.json()["authenticated"])
        self.assertEqual(session_b.json()["user"]["username"], "usuario-logout-b")
        self.assertEqual(session_b.wsgi_request.tenant.schema_name, "tenant_b")

    def test_login_usa_sempre_o_schema_do_host_atual(self):
        username = "usuario-schema-host"
        self.create_user("tenant_a", username, "senha-schema-a")
        self.create_user("tenant_b", username, "senha-schema-b")

        response_a = self._login_json(
            self._client_for_schema("tenant_a"),
            username,
            "senha-schema-a",
        )
        response_b_wrong_password = self._login_json(
            self._client_for_schema("tenant_b"),
            username,
            "senha-schema-a",
        )
        response_b = self._login_json(
            self._client_for_schema("tenant_b"),
            username,
            "senha-schema-b",
        )

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_a.wsgi_request.tenant.schema_name, "tenant_a")
        self.assertEqual(response_a.json()["user"]["username"], username)
        self.assertEqual(response_b_wrong_password.status_code, 401)
        self.assertEqual(
            response_b_wrong_password.wsgi_request.tenant.schema_name,
            "tenant_b",
        )
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")
        self.assertEqual(response_b.json()["user"]["username"], username)
