import json
import hashlib
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, override_settings
from django_tenants.utils import get_public_schema_name
from rest_framework.throttling import SimpleRateThrottle

from caixa.models import ReceitaOperacional
from caixa.permissions import is_platform_operator, is_tenant_administrator
from caixa.tenant_files import backup_dir_for_schema
from caixa.throttling import (
    AuthLoginRateThrottle,
    BackupCreateRateThrottle,
    BackupDownloadRateThrottle,
    ExportCsvRateThrottle,
    TenantUserRateThrottle,
)
from tenancy.command_guards import (
    COMMAND_SCOPES,
    SCOPE_TENANT_ONLY,
)
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


class TenantAdminDisabledTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.add_allowed_host("admin-public.localhost")

    def _route_strings(self, urlpatterns, prefix=""):
        routes = []
        for url_pattern in urlpatterns:
            route = f"{prefix}{url_pattern.pattern}"
            routes.append(route)
            nested_patterns = getattr(url_pattern, "url_patterns", None)
            if nested_patterns:
                routes.extend(self._route_strings(nested_patterns, route))
        return routes

    def _admin_resolvers(self, urlpatterns, prefix=""):
        resolvers = []
        for url_pattern in urlpatterns:
            route = f"{prefix}{url_pattern.pattern}"
            app_name = getattr(url_pattern, "app_name", None)
            namespace = getattr(url_pattern, "namespace", None)
            if app_name == "admin" or namespace == "admin":
                resolvers.append(route)
            nested_patterns = getattr(url_pattern, "url_patterns", None)
            if nested_patterns:
                resolvers.extend(self._admin_resolvers(nested_patterns, route))
        return resolvers

    def test_urlconfs_nao_publicam_django_admin(self):
        from config import public_urls, tenant_urls

        routes = self._route_strings(public_urls.urlpatterns)
        routes.extend(self._route_strings(tenant_urls.urlpatterns))
        admin_resolvers = self._admin_resolvers(public_urls.urlpatterns)
        admin_resolvers.extend(self._admin_resolvers(tenant_urls.urlpatterns))

        self.assertEqual(
            [route for route in routes if route.startswith("admin/")],
            [],
        )
        self.assertEqual(admin_resolvers, [])

    def test_admin_no_public_sem_tenant_retorna_404(self):
        response = self.client.get("/admin/", HTTP_HOST="admin-public.localhost")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(connection.schema_name, get_public_schema_name())

    def test_admin_no_tenant_retorna_404(self):
        response = self.client_for_tenant(self.primary_tenant).get("/admin/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.wsgi_request.tenant.schema_name,
            self.primary_tenant.schema_name,
        )


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

    def _csrf_client_for_schema(self, schema_name):
        domain = (
            "tenant-a.localhost"
            if schema_name == "tenant_a"
            else "tenant-b.localhost"
        )
        return Client(enforce_csrf_checks=True, HTTP_HOST=domain)

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

    def test_login_e_logout_registram_auditoria_minima_por_tenant(self):
        user = self.create_user("tenant_a", "usuario-log-auth", "senha-log-auth")
        client = self._client_for_schema("tenant_a")

        with self.assertLogs("caixa.views_api_auth", level="INFO") as logs:
            login_response = self._login_json(
                client,
                "usuario-log-auth",
                "senha-log-auth",
            )
            logout_response = self._logout_json(client)

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(logout_response.status_code, 200)
        audit_output = "\n".join(logs.output)
        self.assertIn("auth_event action=login outcome=success", audit_output)
        self.assertIn("auth_event action=logout outcome=success", audit_output)
        self.assertIn("schema=tenant_a", audit_output)
        self.assertIn("host=tenant-a.localhost", audit_output)
        self.assertIn(f"user_id={user.pk}", audit_output)
        self.assertIn("ip=", audit_output)
        self.assertNotIn("senha-log-auth", audit_output)
        self.assertNotIn("password", audit_output)

    def test_falha_de_login_registra_auditoria_minima_sem_payload(self):
        self.create_user("tenant_a", "usuario-log-falha", "senha-correta")
        client = self._client_for_schema("tenant_a")

        with self.assertLogs("caixa.views_api_auth", level="INFO") as logs:
            response = self._login_json(
                client,
                "usuario-log-falha",
                "senha-incorreta",
            )

        self.assertEqual(response.status_code, 401)
        audit_output = "\n".join(logs.output)
        self.assertIn("auth_event action=login outcome=failed", audit_output)
        self.assertIn("schema=tenant_a", audit_output)
        self.assertIn("host=tenant-a.localhost", audit_output)
        self.assertIn("user_id=", audit_output)
        self.assertIn("ip=", audit_output)
        self.assertNotIn("usuario-log-falha", audit_output)
        self.assertNotIn("senha-incorreta", audit_output)
        self.assertNotIn("password", audit_output)

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

    def test_login_rotaciona_session_key_preexistente(self):
        self.create_user("tenant_a", "usuario-fixation", "senha-fixation")
        client = self._client_for_schema("tenant_a")
        session = client.session
        session["pre_login_marker"] = "fixation-check"
        session.save()
        session_key_antes_login = session.session_key

        response = self._login_json(client, "usuario-fixation", "senha-fixation")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.tenant.schema_name, "tenant_a")
        self.assertIn(settings.SESSION_COOKIE_NAME, client.cookies)
        self.assertNotEqual(
            client.cookies[settings.SESSION_COOKIE_NAME].value,
            session_key_antes_login,
        )

    def test_csrf_obtido_em_um_tenant_nao_valida_post_em_outro_host(self):
        self.create_user("tenant_b", "usuario-csrf-b", "senha-csrf-b")
        client_a = self._csrf_client_for_schema("tenant_a")
        csrf_response_a = client_a.get("/api/auth/csrf/")
        csrf_token_a = csrf_response_a.json()["csrfToken"]
        self.assertIn(settings.CSRF_COOKIE_NAME, client_a.cookies)

        client_b = self._csrf_client_for_schema("tenant_b")
        self.assertNotIn(settings.CSRF_COOKIE_NAME, client_b.cookies)
        cross_host_response = client_b.post(
            "/api/auth/login/",
            data=json.dumps(
                {
                    "username": "usuario-csrf-b",
                    "password": "senha-csrf-b",
                }
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token_a,
        )

        self.assertEqual(cross_host_response.status_code, 403)
        self.assertEqual(
            cross_host_response.wsgi_request.tenant.schema_name,
            "tenant_b",
        )

        csrf_token_b = client_b.get("/api/auth/csrf/").json()["csrfToken"]
        login_b = client_b.post(
            "/api/auth/login/",
            data=json.dumps(
                {
                    "username": "usuario-csrf-b",
                    "password": "senha-csrf-b",
                }
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token_b,
        )

        self.assertEqual(login_b.status_code, 200)
        self.assertEqual(login_b.wsgi_request.tenant.schema_name, "tenant_b")

    def test_falhas_do_django_axes_em_um_tenant_nao_bloqueiam_outro(self):
        username = "usuario-axes-compartilhado"
        self.create_user("tenant_a", username, "senha-axes-a")
        self.create_user("tenant_b", username, "senha-axes-b")
        client_a = self._client_for_schema("tenant_a")

        for _ in range(settings.AXES_FAILURE_LIMIT):
            response = self._login_json(client_a, username, "senha-incorreta")
            self.assertNotEqual(response.status_code, 200)
            self.assertEqual(response.wsgi_request.tenant.schema_name, "tenant_a")

        response_b = self._login_json(
            self._client_for_schema("tenant_b"),
            username,
            "senha-axes-b",
        )

        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")


class TenantPlatformRoleSeparationTests(MultiTenantTestCase):
    def _login_json(self, client, username, password):
        return client.post(
            "/api/auth/login/",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )

    def test_superuser_de_tenant_nao_e_operador_da_plataforma(self):
        self.create_user(
            "tenant_a",
            "admin-tenant",
            "senha-admin-tenant",
            is_staff=True,
            is_superuser=True,
        )

        with self.in_schema("tenant_a"):
            tenant_user = get_user_model().objects.get(username="admin-tenant")
            self.assertTrue(is_tenant_administrator(tenant_user))
            self.assertFalse(is_platform_operator(tenant_user))

        self.switch_to_public()
        platform_user = get_user_model().objects.create_superuser(
            username="operador-plataforma",
            email="operador-plataforma@example.com",
            password="senha-operador-plataforma",
        )

        self.assertTrue(is_platform_operator(platform_user))
        self.assertFalse(is_tenant_administrator(platform_user))

    def test_payload_de_sessao_separa_admin_tenant_de_operador_plataforma(self):
        self.create_user(
            "tenant_a",
            "admin-payload",
            "senha-admin-payload",
            is_staff=True,
            is_superuser=True,
        )
        client = self.client_for_tenant(self.primary_tenant)

        response = self._login_json(client, "admin-payload", "senha-admin-payload")
        payload = response.json()["user"]

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["isSuperuser"])
        self.assertTrue(payload["isTenantAdmin"])
        self.assertFalse(payload["isPlatformOperator"])
        self.assertTrue(payload["canManageBackups"])

    def test_admin_do_tenant_nao_recebe_permissao_de_backup_global(self):
        self.create_user(
            "tenant_a",
            "admin-backup-global",
            "senha-admin-backup-global",
            is_staff=True,
            is_superuser=True,
        )
        client = self.client_for_tenant(self.primary_tenant)
        login_response = self._login_json(
            client,
            "admin-backup-global",
            "senha-admin-backup-global",
        )
        self.assertEqual(login_response.status_code, 200)

        list_response = client.get("/api/backups/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), {"backups": []})


class TenantBackupIsolationTests(MultiTenantTestCase):
    backup_filename = "backup_banco_2026-07_20260705_010203_000001.json"

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

    def _authenticated_admin(self, schema_name):
        username = f"admin-backup-{schema_name}-{self._testMethodName}"
        password = "senha-backup-tenant"
        self.create_user(
            schema_name,
            username,
            password,
            is_staff=True,
            is_superuser=True,
        )
        client = self._client_for_schema(schema_name)
        response = self._login_json(client, username, password)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.tenant.schema_name, schema_name)
        return client

    def _write_backup(self, schema_name, filename=None, content=None, sha256=None):
        filename = filename or self.backup_filename
        if content is None:
            content = f"conteudo-{schema_name}".encode("utf-8")
        metadata_sha256 = sha256 or hashlib.sha256(content).hexdigest()
        with self.in_schema(schema_name):
            backup_dir = backup_dir_for_schema()
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / filename
            backup_path.write_bytes(content)
            backup_path.with_name(f"{backup_path.stem}.meta.json").write_text(
                json.dumps(
                    {
                        "arquivo": backup_path.name,
                        "criado_em": "2026-07-05T00:00:00-03:00",
                        "mes_referencia": "2026-07",
                        "scope": "tenant",
                        "schema_name": schema_name,
                        "sha256": metadata_sha256,
                        "tamanho_bytes": backup_path.stat().st_size,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return backup_path

    def test_listagem_de_backups_mostra_apenas_arquivos_do_schema_atual(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                self._write_backup("tenant_a", content=b"backup tenant a")
                self._write_backup("tenant_b", content=b"backup tenant b")
                client_a = self._authenticated_admin("tenant_a")
                client_b = self._authenticated_admin("tenant_b")

                response_a = client_a.get("/api/backups/")
                response_b = client_b.get("/api/backups/")

            self.assertEqual(response_a.status_code, 200)
            self.assertEqual(response_b.status_code, 200)
            self.assertEqual(response_a.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")
            self.assertEqual(len(response_a.json()["backups"]), 1)
            self.assertEqual(len(response_b.json()["backups"]), 1)
            self.assertEqual(response_a.json()["backups"][0]["schemaName"], "tenant_a")
            self.assertEqual(response_b.json()["backups"][0]["schemaName"], "tenant_b")

    def test_backup_com_sha256_invalido_nao_lista_nem_baixa(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                self._write_backup("tenant_a", sha256="sha256-invalido")
                client_a = self._authenticated_admin("tenant_a")

                list_response = client_a.get("/api/backups/")
                download_response = client_a.get(
                    f"/backups/{self.backup_filename}/download/"
                )

            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(list_response.json(), {"backups": []})
            self.assertEqual(download_response.status_code, 404)
            self.assertEqual(list_response.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(download_response.wsgi_request.tenant.schema_name, "tenant_a")

    def test_backup_com_sha256_valido_continua_listando_e_baixando(self):
        content = b"backup tenant a valido"
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                self._write_backup("tenant_a", content=content)
                client_a = self._authenticated_admin("tenant_a")

                list_response = client_a.get("/api/backups/")
                download_response = client_a.get(
                    f"/backups/{self.backup_filename}/download/"
                )

                downloaded = b"".join(download_response.streaming_content)
                download_response.close()

            self.assertEqual(list_response.status_code, 200)
            self.assertEqual(download_response.status_code, 200)
            self.assertEqual(len(list_response.json()["backups"]), 1)
            self.assertEqual(
                list_response.json()["backups"][0]["name"],
                self.backup_filename,
            )
            self.assertEqual(downloaded, content)
            self.assertEqual(list_response.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(download_response.wsgi_request.tenant.schema_name, "tenant_a")

    def test_download_de_backup_nao_acessa_arquivo_de_outro_tenant(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                self._write_backup("tenant_b")
                client_a = self._authenticated_admin("tenant_a")
                client_b = self._authenticated_admin("tenant_b")

                response_a = client_a.get(f"/backups/{self.backup_filename}/download/")
                response_b = client_b.get(f"/backups/{self.backup_filename}/download/")

                if hasattr(response_b, "close"):
                    response_b.close()

            self.assertEqual(response_a.status_code, 404)
            self.assertEqual(response_b.status_code, 200)
            self.assertEqual(response_a.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")

    def test_download_de_backup_envia_headers_seguros(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                self._write_backup("tenant_a")
                client = self._authenticated_admin("tenant_a")

                response = client.get(f"/backups/{self.backup_filename}/download/")

                if hasattr(response, "close"):
                    response.close()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertEqual(response["Pragma"], "no-cache")
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_download_de_backup_invalido_registra_tentativa_negada(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                client = self._authenticated_admin("tenant_a")

                with self.assertLogs("caixa.views_backups", level="INFO") as logs:
                    response = client.get(
                        "/backups/backup_banco_inexistente.json/download/"
                    )

            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.wsgi_request.tenant.schema_name, "tenant_a")
            audit_output = "\n".join(logs.output)
            self.assertIn("backup_event action=download outcome=denied", audit_output)
            self.assertIn("schema=tenant_a", audit_output)
            self.assertIn("host=tenant-a.localhost", audit_output)
            self.assertIn("user_id=", audit_output)
            self.assertIn("filename=backup_banco_inexistente.json", audit_output)
            self.assertNotIn("encontrado", audit_output.lower())
            self.assertNotIn("exists", audit_output.lower())

    def test_criacao_manual_de_backup_grava_no_diretorio_do_tenant(self):
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with override_settings(BASE_DIR=base_dir):
                client_a = self._authenticated_admin("tenant_a")
                with patch("caixa.services_backups.call_command"):
                    response = client_a.post(
                        "/api/backups/criar/",
                        data="",
                        content_type="application/octet-stream",
                    )

                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.wsgi_request.tenant.schema_name, "tenant_a")
                payload = response.json()
                self.assertEqual(payload["backup"]["schemaName"], "tenant_a")

                with self.in_schema("tenant_a"):
                    tenant_a_files = [
                        path
                        for path in backup_dir_for_schema().glob("backup_banco_*.json")
                        if not path.name.endswith(".meta.json")
                    ]
                with self.in_schema("tenant_b"):
                    tenant_b_files = [
                        path
                        for path in backup_dir_for_schema().glob("backup_banco_*.json")
                        if not path.name.endswith(".meta.json")
                    ]

            self.assertEqual(len(tenant_a_files), 1)
            self.assertEqual(tenant_b_files, [])
            self.assertFalse((base_dir / "backups" / "db").exists())
            self.assertIn(
                base_dir / "backups" / "tenants" / "tenant_a" / "db",
                [tenant_a_files[0].parent],
            )

    def test_criacao_manual_de_backup_tem_rate_limit_por_tenant(self):
        rates = dict(SimpleRateThrottle.THROTTLE_RATES)
        rates["backup_create"] = "1/minute"
        cache.clear()
        try:
            with TemporaryDirectory() as temp_dir:
                base_dir = Path(temp_dir)
                with override_settings(BASE_DIR=base_dir):
                    client_a = self._authenticated_admin("tenant_a")
                    client_b = self._authenticated_admin("tenant_b")

                    with patch.object(SimpleRateThrottle, "THROTTLE_RATES", rates):
                        with patch("caixa.services_backups.call_command"):
                            primeira_a = client_a.post(
                                "/api/backups/criar/",
                                data="",
                                content_type="application/octet-stream",
                            )
                            segunda_a = client_a.post(
                                "/api/backups/criar/",
                                data="",
                                content_type="application/octet-stream",
                            )
                            primeira_b = client_b.post(
                                "/api/backups/criar/",
                                data="",
                                content_type="application/octet-stream",
                            )

                self.assertEqual(primeira_a.status_code, 201)
                self.assertEqual(segunda_a.status_code, 429)
                self.assertIn("Retry-After", segunda_a.headers)
                self.assertEqual(primeira_b.status_code, 201)
                self.assertEqual(primeira_a.wsgi_request.tenant.schema_name, "tenant_a")
                self.assertEqual(segunda_a.wsgi_request.tenant.schema_name, "tenant_a")
                self.assertEqual(primeira_b.wsgi_request.tenant.schema_name, "tenant_b")
        finally:
            cache.clear()

    def test_download_de_backup_tem_rate_limit_por_tenant(self):
        rates = dict(SimpleRateThrottle.THROTTLE_RATES)
        rates["backup_download"] = "1/minute"
        cache.clear()
        try:
            with TemporaryDirectory() as temp_dir:
                base_dir = Path(temp_dir)
                with override_settings(BASE_DIR=base_dir):
                    self._write_backup("tenant_a")
                    self._write_backup("tenant_b")
                    client_a = self._authenticated_admin("tenant_a")
                    client_b = self._authenticated_admin("tenant_b")

                    with patch.object(SimpleRateThrottle, "THROTTLE_RATES", rates):
                        primeira_a = client_a.get(
                            f"/backups/{self.backup_filename}/download/"
                        )
                        segunda_a = client_a.get(
                            f"/backups/{self.backup_filename}/download/"
                        )
                        primeira_b = client_b.get(
                            f"/backups/{self.backup_filename}/download/"
                        )

                    for response in (primeira_a, primeira_b):
                        if hasattr(response, "close"):
                            response.close()

                self.assertEqual(primeira_a.status_code, 200)
                self.assertEqual(segunda_a.status_code, 429)
                self.assertIn("Retry-After", segunda_a.headers)
                self.assertEqual(segunda_a["Cache-Control"], "no-store")
                self.assertEqual(primeira_b.status_code, 200)
                self.assertEqual(primeira_a.wsgi_request.tenant.schema_name, "tenant_a")
                self.assertEqual(segunda_a.wsgi_request.tenant.schema_name, "tenant_a")
                self.assertEqual(primeira_b.wsgi_request.tenant.schema_name, "tenant_b")
        finally:
            cache.clear()


class TenantExportDownloadIsolationTests(MultiTenantTestCase):
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
        cls.password = "senha-export-tenant"
        cls.create_user(
            "tenant_a",
            "admin-export-a",
            cls.password,
            is_staff=True,
            is_superuser=True,
        )
        cls.create_user(
            "tenant_b",
            "admin-export-b",
            cls.password,
            is_staff=True,
            is_superuser=True,
        )
        cls.create_user(
            "tenant_a",
            "usuario-export-sem-permissao",
            cls.password,
        )
        cliente_a = cls.create_basic_cliente("tenant_a", nome="Cliente Export A")
        cliente_b = cls.create_basic_cliente("tenant_b", nome="Cliente Export B")
        evento_a = cls.create_basic_evento(
            "tenant_a",
            cliente=cliente_a,
            nome="Evento Export A",
        )
        evento_b = cls.create_basic_evento(
            "tenant_b",
            cliente=cliente_b,
            nome="Evento Export B",
        )
        cls._create_receita(
            "tenant_a",
            evento_a.id,
            cliente_a.id,
            "Receita Export Tenant A",
            Decimal("111.00"),
        )
        cls._create_receita(
            "tenant_b",
            evento_b.id,
            cliente_b.id,
            "Receita Export Tenant B",
            Decimal("222.00"),
        )

    @classmethod
    def _create_receita(cls, schema_name, evento_id, cliente_id, descricao, valor):
        with cls.in_schema(schema_name):
            ReceitaOperacional.objects.create(
                evento_id=evento_id,
                cliente_id=cliente_id,
                descricao=descricao,
                valor_previsto=valor,
                valor_recebido=Decimal("0.00"),
                data_vencimento=date(2026, 7, 5),
            )

    def _client_for_schema(self, schema_name):
        return self.client_for_tenant(self.tenants[schema_name])

    def _login_json(self, client, username):
        return client.post(
            "/api/auth/login/",
            data=json.dumps({"username": username, "password": self.password}),
            content_type="application/json",
        )

    def _authenticated_client(self, schema_name):
        username = "admin-export-a" if schema_name == "tenant_a" else "admin-export-b"
        client = self._client_for_schema(schema_name)
        response = self._login_json(client, username)
        self.assertEqual(response.status_code, 200)
        return client

    def test_exportacao_csv_retorna_apenas_dados_do_schema_do_host(self):
        with self.assertLogs("caixa.views_obrigacoes", level="INFO") as logs:
            response_a = self._authenticated_client("tenant_a").get(
                "/api/obrigacoes-financeiras/exportar/",
                {
                    "exportScope": "revenues",
                    "startDate": "2026-07-01",
                    "endDate": "2026-07-31",
                },
            )
        response_b = self._authenticated_client("tenant_b").get(
            "/api/obrigacoes-financeiras/exportar/",
            {
                "exportScope": "revenues",
                "startDate": "2026-07-01",
                "endDate": "2026-07-31",
            },
        )

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        content_a = response_a.content.decode("utf-8-sig")
        content_b = response_b.content.decode("utf-8-sig")
        self.assertIn("Receita Export Tenant A", content_a)
        self.assertNotIn("Receita Export Tenant B", content_a)
        self.assertIn("Receita Export Tenant B", content_b)
        self.assertNotIn("Receita Export Tenant A", content_b)
        self.assertIn("no-store", response_a["Cache-Control"])
        self.assertEqual(response_a["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment;", response_a["Content-Disposition"])
        audit_output = "\n".join(logs.output)
        self.assertIn("export_event action=obligations_csv outcome=allowed", audit_output)
        self.assertIn("schema=tenant_a", audit_output)
        self.assertIn("scope=revenues", audit_output)

    def test_exportacao_csv_exige_permissao_no_tenant(self):
        client = self._client_for_schema("tenant_a")
        response_login = self._login_json(client, "usuario-export-sem-permissao")
        self.assertEqual(response_login.status_code, 200)

        with self.assertLogs("caixa.views_obrigacoes", level="INFO") as logs:
            response = client.get(
                "/api/obrigacoes-financeiras/exportar/",
                {
                    "exportScope": "revenues",
                    "startDate": "2026-07-01",
                    "endDate": "2026-07-31",
                },
            )

        self.assertEqual(response.status_code, 403)
        audit_output = "\n".join(logs.output)
        self.assertIn("export_event action=obligations_csv outcome=denied_permission", audit_output)
        self.assertIn("schema=tenant_a", audit_output)

    def test_exportacao_csv_tem_rate_limit_por_tenant(self):
        rates = dict(SimpleRateThrottle.THROTTLE_RATES)
        rates["export_csv"] = "1/minute"
        cache.clear()
        try:
            client_a = self._authenticated_client("tenant_a")
            client_b = self._authenticated_client("tenant_b")
            params = {
                "exportScope": "revenues",
                "startDate": "2026-07-01",
                "endDate": "2026-07-31",
            }

            with patch.object(SimpleRateThrottle, "THROTTLE_RATES", rates):
                primeira_a = client_a.get(
                    "/api/obrigacoes-financeiras/exportar/",
                    params,
                )
                segunda_a = client_a.get(
                    "/api/obrigacoes-financeiras/exportar/",
                    params,
                )
                primeira_b = client_b.get(
                    "/api/obrigacoes-financeiras/exportar/",
                    params,
                )

            self.assertEqual(primeira_a.status_code, 200)
            self.assertEqual(segunda_a.status_code, 429)
            self.assertIn("Retry-After", segunda_a.headers)
            self.assertEqual(primeira_b.status_code, 200)
            self.assertEqual(primeira_a.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(segunda_a.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(primeira_b.wsgi_request.tenant.schema_name, "tenant_b")
        finally:
            cache.clear()


class TenantApiIdorIsolationTests(MultiTenantTestCase):
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
        cls.password = "senha-api-isolada"
        cls.user_a = cls.create_user(
            "tenant_a",
            "usuario-api-a",
            cls.password,
            is_superuser=True,
        )
        cls.user_b = cls.create_user(
            "tenant_b",
            "usuario-api-b",
            cls.password,
            is_superuser=True,
        )
        cls.cliente_a_shared_id = cls.create_basic_cliente(
            "tenant_a",
            nome="Cliente API Tenant A",
        ).id
        cls.cliente_b_shared_id = cls.create_basic_cliente(
            "tenant_b",
            nome="Cliente API Tenant B",
        ).id
        cls.cliente_apenas_a_id = cls.create_basic_cliente(
            "tenant_a",
            nome="Cliente Apenas Tenant A",
        ).id

        cls.evento_a_id = cls.create_basic_evento(
            "tenant_a",
            cliente=cls._cliente("tenant_a", cls.cliente_a_shared_id),
            nome="Evento Financeiro Tenant A",
        ).id
        cls.evento_b_id = cls.create_basic_evento(
            "tenant_b",
            cliente=cls._cliente("tenant_b", cls.cliente_b_shared_id),
            nome="Evento Financeiro Tenant B",
        ).id
        cls._create_receita(
            "tenant_a",
            cls.evento_a_id,
            cls.cliente_a_shared_id,
            "Receita Tenant A",
            Decimal("1000.00"),
        )
        cls._create_receita(
            "tenant_b",
            cls.evento_b_id,
            cls.cliente_b_shared_id,
            "Receita Tenant B",
            Decimal("2000.00"),
        )

    @classmethod
    def _cliente(cls, schema_name, cliente_id):
        with cls.in_schema(schema_name):
            from caixa.models import Cliente

            return Cliente.objects.get(pk=cliente_id)

    @classmethod
    def _create_receita(cls, schema_name, evento_id, cliente_id, descricao, valor):
        with cls.in_schema(schema_name):
            ReceitaOperacional.objects.create(
                evento_id=evento_id,
                cliente_id=cliente_id,
                descricao=descricao,
                valor_previsto=valor,
                valor_recebido=Decimal("0.00"),
                data_vencimento=date(2026, 1, 15),
            )

    def _client_for_schema(self, schema_name):
        return self.client_for_tenant(self.tenants[schema_name])

    def _login_json(self, client, username, password):
        return client.post(
            "/api/auth/login/",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )

    def _authenticated_client(self, schema_name):
        username = "usuario-api-a" if schema_name == "tenant_a" else "usuario-api-b"
        client = self._client_for_schema(schema_name)
        response = self._login_json(client, username, self.password)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.tenant.schema_name, schema_name)
        return client

    def _client_names(self, schema_name):
        response = self._authenticated_client(schema_name).get("/api/clientes/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.tenant.schema_name, schema_name)
        return {
            item["name"]
            for item in response.json()["data"]["clients"]
        }

    def _client_detail(self, schema_name, cliente_id):
        response = self._authenticated_client(schema_name).get(
            f"/api/clientes/{cliente_id}/"
        )
        self.assertEqual(response.wsgi_request.tenant.schema_name, schema_name)
        return response

    def test_dados_do_tenant_a_nao_aparecem_na_listagem_do_tenant_b(self):
        nomes_tenant_b = self._client_names("tenant_b")

        self.assertIn("Cliente API Tenant B 2", nomes_tenant_b)
        self.assertNotIn("Cliente API Tenant A 1", nomes_tenant_b)
        self.assertNotIn("Cliente Apenas Tenant A 3", nomes_tenant_b)

    def test_dados_do_tenant_b_nao_aparecem_na_listagem_do_tenant_a(self):
        nomes_tenant_a = self._client_names("tenant_a")

        self.assertIn("Cliente API Tenant A 1", nomes_tenant_a)
        self.assertIn("Cliente Apenas Tenant A 3", nomes_tenant_a)
        self.assertNotIn("Cliente API Tenant B 2", nomes_tenant_a)

    def test_mesmo_id_em_tenants_diferentes_retorna_dado_do_schema_do_host(self):
        self.assertEqual(self.cliente_a_shared_id, self.cliente_b_shared_id)

        response_a = self._client_detail("tenant_a", self.cliente_a_shared_id)
        response_b = self._client_detail("tenant_b", self.cliente_b_shared_id)

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(
            response_a.json()["data"]["client"]["name"],
            "Cliente API Tenant A 1",
        )
        self.assertEqual(
            response_b.json()["data"]["client"]["name"],
            "Cliente API Tenant B 2",
        )

    def test_acessar_id_existente_apenas_no_outro_tenant_retorna_404(self):
        response = self._client_detail("tenant_b", self.cliente_apenas_a_id)

        self.assertEqual(response.status_code, 404)

    def test_dashboard_financeiro_nao_soma_dados_de_outro_tenant(self):
        response_a = self._authenticated_client("tenant_a").get(
            "/api/dashboard/financial-overview/?period=all"
        )
        response_b = self._authenticated_client("tenant_b").get(
            "/api/dashboard/financial-overview/?period=all"
        )

        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_a.wsgi_request.tenant.schema_name, "tenant_a")
        self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")
        self.assertEqual(
            response_a.json()["data"]["kpis"]["receitaTotal"]["value"],
            1000.0,
        )
        self.assertEqual(
            response_b.json()["data"]["kpis"]["receitaTotal"]["value"],
            2000.0,
        )


class TenantCacheIsolationTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, cls.secondary_domain = cls.create_tenant(
            schema_name="tenant_b",
            name="Tenant B",
            domain="tenant-b.localhost",
        )

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_cache_key_isolada_por_schema(self):
        with self.in_schema("tenant_a"):
            cache.set("shared-cache-key", "valor-tenant-a", timeout=60)

        with self.in_schema("tenant_b"):
            self.assertIsNone(cache.get("shared-cache-key"))
            cache.set("shared-cache-key", "valor-tenant-b", timeout=60)

        self.switch_to_public()
        self.assertIsNone(cache.get("shared-cache-key"))
        cache.set("shared-cache-key", "valor-public", timeout=60)

        with self.in_schema("tenant_a"):
            self.assertEqual(cache.get("shared-cache-key"), "valor-tenant-a")

        with self.in_schema("tenant_b"):
            self.assertEqual(cache.get("shared-cache-key"), "valor-tenant-b")

        self.switch_to_public()
        self.assertEqual(cache.get("shared-cache-key"), "valor-public")


class TenantCachedDbSessionIsolationTests(MultiTenantTestCase):
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

    @override_settings(SESSION_ENGINE="django.contrib.sessions.backends.cached_db")
    def test_sessao_cached_db_nao_autentica_em_outro_tenant(self):
        self.create_user("tenant_a", "usuario-cache-session-a", "senha-cache-session")
        client_a = self._client_for_schema("tenant_a")
        login_a = self._login_json(
            client_a,
            "usuario-cache-session-a",
            "senha-cache-session",
        )
        self.assertEqual(login_a.status_code, 200)

        session_cookie = client_a.cookies[settings.SESSION_COOKIE_NAME].value
        client_b = self._client_for_schema("tenant_b")
        client_b.cookies[settings.SESSION_COOKIE_NAME] = session_cookie

        response_b = client_b.get("/api/auth/session/")

        self.assertEqual(response_b.status_code, 200)
        self.assertEqual(response_b.wsgi_request.tenant.schema_name, "tenant_b")
        self.assertEqual(response_b.json(), {"authenticated": False})


class TenantThrottleIsolationTests(MultiTenantTestCase):
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
        cls.password = "senha-throttle-isolado"
        cls.create_user("tenant_a", "usuario-throttle-a", cls.password)
        cls.create_user("tenant_b", "usuario-throttle-b", cls.password)

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _client_for_schema(self, schema_name):
        return self.client_for_tenant(self.tenants[schema_name])

    def _login_json(self, client, username, password):
        return client.post(
            "/api/auth/login/",
            data=json.dumps({"username": username, "password": password}),
            content_type="application/json",
        )

    def test_throttle_de_usuario_inclui_schema_usuario_e_ip(self):
        client_a = self._client_for_schema("tenant_a")
        client_b = self._client_for_schema("tenant_b")
        self.assertEqual(
            self._login_json(client_a, "usuario-throttle-a", self.password).status_code,
            200,
        )
        self.assertEqual(
            self._login_json(client_b, "usuario-throttle-b", self.password).status_code,
            200,
        )

        request_a = client_a.get("/api/auth/session/").wsgi_request
        request_b = client_b.get("/api/auth/session/").wsgi_request
        key_a = TenantUserRateThrottle().get_cache_key(request_a, None)
        key_b = TenantUserRateThrottle().get_cache_key(request_b, None)

        self.assertIn("tenant_a", key_a)
        self.assertIn("tenant_b", key_b)
        self.assertIn("user:", key_a)
        self.assertIn("ip:", key_a)
        self.assertNotEqual(key_a, key_b)

    def test_throttles_de_operacoes_sensiveis_incluem_schema_usuario_e_ip(self):
        client_a = self._client_for_schema("tenant_a")
        client_b = self._client_for_schema("tenant_b")
        self.assertEqual(
            self._login_json(client_a, "usuario-throttle-a", self.password).status_code,
            200,
        )
        self.assertEqual(
            self._login_json(client_b, "usuario-throttle-b", self.password).status_code,
            200,
        )

        request_a = client_a.get("/api/auth/session/").wsgi_request
        request_b = client_b.get("/api/auth/session/").wsgi_request

        for throttle_class, scope in (
            (BackupCreateRateThrottle, "backup_create"),
            (BackupDownloadRateThrottle, "backup_download"),
            (ExportCsvRateThrottle, "export_csv"),
        ):
            with self.subTest(scope=scope):
                key_a = throttle_class().get_cache_key(request_a, None)
                key_b = throttle_class().get_cache_key(request_b, None)

                self.assertIn(scope, key_a)
                self.assertIn("tenant_a", key_a)
                self.assertIn("tenant_b", key_b)
                self.assertIn("user:", key_a)
                self.assertIn("ip:", key_a)
                self.assertNotEqual(key_a, key_b)

    def test_throttle_de_login_anonimo_inclui_schema_e_ip(self):
        request_a = self._client_for_schema("tenant_a").get(
            "/api/auth/csrf/"
        ).wsgi_request
        request_b = self._client_for_schema("tenant_b").get(
            "/api/auth/csrf/"
        ).wsgi_request

        key_a = AuthLoginRateThrottle().get_cache_key(request_a, None)
        key_b = AuthLoginRateThrottle().get_cache_key(request_b, None)

        self.assertIn("tenant_a", key_a)
        self.assertIn("tenant_b", key_b)
        self.assertIn("anon:ip:", key_a)
        self.assertNotEqual(key_a, key_b)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PASSWORD_RESET_RATE_LIMIT_ATTEMPTS=1,
        PASSWORD_RESET_RATE_LIMIT_WINDOW=3600,
    )
    def test_rate_limit_de_reset_de_senha_e_isolado_por_schema(self):
        email = "reset-compartilhado@example.com"
        self.create_user("tenant_a", "reset-tenant-a", self.password, email=email)
        self.create_user("tenant_b", "reset-tenant-b", self.password, email=email)
        cache.clear()
        mail.outbox = []
        try:
            client_a = self._client_for_schema("tenant_a")
            client_b = self._client_for_schema("tenant_b")

            primeira_a = client_a.post("/password-reset/", {"email": email})
            segunda_a = client_a.post("/password-reset/", {"email": email})
            primeira_b = client_b.post("/password-reset/", {"email": email})

            self.assertEqual(primeira_a.status_code, 302)
            self.assertEqual(segunda_a.status_code, 302)
            self.assertEqual(primeira_b.status_code, 302)
            self.assertEqual(primeira_a.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(segunda_a.wsgi_request.tenant.schema_name, "tenant_a")
            self.assertEqual(primeira_b.wsgi_request.tenant.schema_name, "tenant_b")
            self.assertEqual(len(mail.outbox), 2)
        finally:
            cache.clear()


class TenantCommandGuardTests(MultiTenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.secondary_tenant, cls.secondary_domain = cls.create_tenant(
            schema_name="tenant_b",
            name="Tenant B",
            domain="tenant-b.localhost",
        )

    def test_todos_commands_customizados_estao_classificados(self):
        commands_dir = Path(settings.BASE_DIR) / "caixa" / "management" / "commands"
        command_names = {
            path.stem
            for path in commands_dir.glob("*.py")
            if path.name != "__init__.py"
        }

        self.assertEqual(command_names, set(COMMAND_SCOPES))

    def test_commands_tenant_only_possuem_guarda_de_schema(self):
        commands_dir = Path(settings.BASE_DIR) / "caixa" / "management" / "commands"
        missing = []

        for command_name, scope in sorted(COMMAND_SCOPES.items()):
            if scope != SCOPE_TENANT_ONLY:
                continue

            command_path = commands_dir / f"{command_name}.py"
            command_source = command_path.read_text(encoding="utf-8")
            if "ensure_tenant_schema(" not in command_source:
                missing.append(command_name)

        self.assertEqual(missing, [])

    def test_comando_operacional_recusa_schema_public(self):
        self.switch_to_public()

        with self.assertRaisesMessage(CommandError, "schema de tenant"):
            call_command("backup_banco_mensal", stdout=StringIO())

    def test_commands_tenant_only_criticos_recusam_schema_public(self):
        self.switch_to_public()

        for command_name in (
            "auditar_totais_negocio",
            "validar_preflight_deploy_financeiro",
            "verificar_integridade_valores_editaveis",
        ):
            with self.subTest(command_name=command_name):
                with self.assertRaisesMessage(CommandError, "schema de tenant"):
                    call_command(command_name, stdout=StringIO())

    def test_comando_operacional_permite_schema_de_tenant(self):
        resultado = {"criado": False, "mensagem": "Sem alteracao.", "removidos": 0}

        with self.in_schema("tenant_a"):
            with patch(
                "caixa.management.commands.backup_banco_mensal.criar_backup_banco",
                return_value=resultado,
            ) as criar_backup:
                call_command("backup_banco_mensal", stdout=StringIO())

        criar_backup.assert_called_once_with(force=False, manter=3)

    def test_limpeza_operacional_rejeita_backup_de_outro_schema(self):
        backup_dir = backup_dir_for_schema("tenant_b")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / "backup_banco_2026-01_20260101_000000_000000.json"
        backup_content = b"[]"
        backup_path.write_bytes(backup_content)
        backup_path.with_suffix(".meta.json").write_text(
            json.dumps(
                {
                    "arquivo": backup_path.name,
                    "scope": "tenant",
                    "schema_name": "tenant_b",
                    "sha256": hashlib.sha256(backup_content).hexdigest(),
                }
            ),
            encoding="utf-8",
        )

        with self.in_schema("tenant_a"):
            with self.assertRaisesMessage(CommandError, "outro schema"):
                call_command(
                    "limpar_base_operacional_pm06",
                    "--backup-ref",
                    str(backup_path),
                    "--falhar",
                    stdout=StringIO(),
                )

    def test_perfil_legado_esta_desativado(self):
        with self.assertRaisesMessage(CommandError, "perfil legado"):
            call_command(
                "validar_baseline_pm02",
                "--perfil-legado-producao",
                stdout=StringIO(),
            )

    def test_snapshot_financeiro_usa_frontend_rhsaas_por_padrao(self):
        from caixa.management.commands.gerar_snapshot_baseline_financeira import (
            DEFAULT_FRONTEND_PATH,
        )

        self.assertEqual(DEFAULT_FRONTEND_PATH.name, "rhsaasfront")
