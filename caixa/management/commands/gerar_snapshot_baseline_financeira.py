import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


PM02_COMMANDS = [
    "python manage.py check",
    "python manage.py makemigrations --check --dry-run",
    "python manage.py validar_preflight_deploy_financeiro --falhar --json",
    (
        "python manage.py validar_operacao_obrigacoes --validar-canonico "
        "--validar-escrita-canonica --validar-valores-editaveis --falhar"
    ),
    (
        "python manage.py auditar_totais_negocio --validar-valores-editaveis "
        "--falhar-com-divergencia --falhar-com-valores-editaveis"
    ),
]
PM02_AGGREGATE_COMMAND = "python manage.py validar_baseline_pm02 --falhar --json"
PM02_STRICT_SERVER_COMMAND = (
    "python manage.py validar_baseline_pm02 --modo-servidor-estrito "
    "--frontend-ref=<commit-ou-deploy-vercel> "
    "--ambiente=<producao-ou-homologacao> "
    "--release-ref=<tag-ou-commit-backend> "
    "--backup-ref=<arquivo-ou-id-backup> "
    "--json"
)
PM02_STRICT_SERVER_COMMAND_WITH_DEPLOY_URL = (
    "python manage.py validar_baseline_pm02 --modo-servidor-estrito "
    "--frontend-deploy-url=<url-deploy-vercel> "
    "--ambiente=<producao-ou-homologacao> "
    "--release-ref=<tag-ou-commit-backend> "
    "--backup-ref=<arquivo-ou-id-backup> "
    "--json"
)
PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION = (
    "python manage.py validar_baseline_pm02 --modo-servidor-estrito "
    "--perfil-rhremoto-producao "
    "--frontend-ref=<commit-ou-deploy-vercel> "
    "--release-ref=<tag-ou-commit-backend> "
    "--backup-ref=<arquivo-ou-id-backup> "
    "--json"
)
PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION_WITH_DEPLOY_URL = (
    "python manage.py validar_baseline_pm02 --modo-servidor-estrito "
    "--perfil-rhremoto-producao "
    "--frontend-deploy-url=<url-deploy-vercel> "
    "--exigir-frontend-deploy-url-https "
    "--release-ref=<tag-ou-commit-backend> "
    "--backup-ref=<arquivo-ou-id-backup> "
    "--json"
)
PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION_WITH_EVIDENCE = (
    "python manage.py validar_baseline_pm02 --modo-servidor-estrito "
    "--perfil-rhremoto-producao "
    "--frontend-ref=<commit-ou-deploy-vercel> "
    "--release-ref=<tag-ou-commit-backend> "
    "--backup-ref=<arquivo-ou-id-backup> "
    "--diretorio-evidencias=<diretorio-evidencias-pm02> "
    "--exigir-arquivos-evidencia "
    "--json"
)
PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE = (
    "python manage.py validar_baseline_pm02 --modo-servidor-estrito "
    "--perfil-rhremoto-producao "
    "--frontend-deploy-url=<url-deploy-vercel> "
    "--exigir-frontend-deploy-url-https "
    "--release-ref=<tag-ou-commit-backend> "
    "--backup-ref=<arquivo-ou-id-backup> "
    "--diretorio-evidencias=<diretorio-evidencias-pm02> "
    "--exigir-arquivos-evidencia "
    "--json"
)
DEFAULT_FRONTEND_PATH = (
    settings.BASE_DIR.parent
    / "dashboardFinanceiro"
    / "v0-dashboard-financeiro-rhremoto"
)


class Command(BaseCommand):
    help = (
        "Gera um snapshot somente leitura da baseline PM-02: versao do codigo, "
        "canonical-first, cache, cookies e banco sem expor senhas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o snapshot em JSON para registrar na janela PM-02.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o snapshot JSON em um arquivo.",
        )
        parser.add_argument(
            "--falhar-se-dirty",
            action="store_true",
            help="Retorna erro se o git indicar worktree com alteracoes.",
        )
        parser.add_argument(
            "--falhar-se-debug",
            action="store_true",
            help="Retorna erro se DEBUG estiver ativo.",
        )
        parser.add_argument(
            "--frontend-path",
            default="",
            help=(
                "Caminho opcional do frontend Next.js. Se omitido, usa o "
                "caminho padrao do workspace."
            ),
        )
        parser.add_argument(
            "--frontend-ref",
            default="",
            help="Referencia manual do frontend publicado, por exemplo commit da Vercel.",
        )
        parser.add_argument(
            "--frontend-deploy-url",
            default="",
            help="URL opcional do deploy frontend usado na janela PM-02.",
        )

    def handle(self, *args, **options):
        snapshot = gerar_snapshot_baseline_financeira(
            frontend_path=options.get("frontend_path"),
            frontend_ref=options.get("frontend_ref"),
            frontend_deploy_url=options.get("frontend_deploy_url"),
        )
        snapshot["evidenceFiles"] = {"json": options.get("salvar_json", "")}
        json_text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)

        if options["json_output"]:
            self.stdout.write(json_text)
        else:
            self._imprimir_relatorio(snapshot)

        if options.get("salvar_json"):
            _salvar_arquivo_snapshot(options["salvar_json"], f"{json_text}\n")

        erros = []
        if options["falhar_se_dirty"] and snapshot["git"]["dirty"]:
            erros.append("worktree com alteracoes")
        if (
            options["falhar_se_dirty"]
            and snapshot["frontend"]["exists"]
            and snapshot["frontend"]["git"]["dirty"]
        ):
            erros.append("frontend com alteracoes")
        if options["falhar_se_debug"] and snapshot["environment"]["debug"]:
            erros.append("DEBUG ativo")

        if erros:
            raise CommandError("; ".join(erros))

    def _imprimir_relatorio(self, snapshot):
        self.stdout.write("Snapshot PM-02 de baseline financeira.")
        self.stdout.write(f"Gerado em: {snapshot['generatedAt']}")
        self.stdout.write(
            "Git: "
            f"commit={snapshot['git']['commitShort'] or '-'}; "
            f"dirty={'sim' if snapshot['git']['dirty'] else 'nao'}"
        )
        frontend = snapshot["frontend"]
        if frontend["exists"]:
            self.stdout.write(
                "Frontend: "
                f"commit={frontend['git']['commitShort'] or '-'}; "
                f"dirty={'sim' if frontend['git']['dirty'] else 'nao'}; "
                f"packageManager={frontend['packageManager'] or '-'}; "
                f"refDeclarada={frontend['declaredReference'] or '-'}"
            )
        else:
            self.stdout.write(
                f"Frontend: nao encontrado em {frontend['path']}; "
                f"refDeclarada={frontend['declaredReference'] or '-'}"
            )
        canonical = snapshot["canonicalFirst"]
        self.stdout.write(
            "Canonical-first: "
            f"{'ligado' if canonical['enabled'] else 'desligado'}; "
            f"origens={', '.join(canonical['sources']) or '-'}"
        )
        cache = snapshot["cache"]
        self.stdout.write(
            f"Cache: backend={cache['backend']}; location={cache['location']}"
        )
        api_throttling = snapshot["apiThrottling"]
        self.stdout.write(
            "API throttling: "
            f"classes={', '.join(api_throttling['classes']) or '-'}; "
            f"rates={_formatar_throttle_rates(api_throttling['rates'])}"
        )
        cookies = snapshot["cookies"]
        self.stdout.write(
            "Cookies: "
            f"sessionDomain={cookies['sessionCookieDomain'] or '-'}; "
            f"csrfDomain={cookies['csrfCookieDomain'] or '-'}; "
            f"sessionSecure={cookies['sessionCookieSecure']}; "
            f"csrfSecure={cookies['csrfCookieSecure']}"
        )
        database = snapshot["database"]
        self.stdout.write(
            "Banco: "
            f"engine={database['engine']}; "
            f"name={database['name']}; "
            f"host={database['host'] or '-'}; "
            f"port={database['port'] or '-'}"
        )
        self.stdout.write("Comandos PM-02 para repetir no servidor:")
        self.stdout.write(f"- {snapshot['pm02AggregateCommand']}")
        self.stdout.write(f"- {snapshot['pm02StrictServerCommand']}")
        self.stdout.write(f"- {snapshot['pm02StrictServerCommandWithDeployUrl']}")
        self.stdout.write(
            f"- {snapshot['pm02StrictServerCommandRhremotoProduction']}"
        )
        self.stdout.write(
            f"- {snapshot['pm02StrictServerCommandRhremotoProductionWithDeployUrl']}"
        )
        self.stdout.write(
            f"- {snapshot['pm02StrictServerCommandRhremotoProductionWithEvidence']}"
        )
        self.stdout.write(
            f"- {snapshot['pm02StrictServerCommandRhremotoProductionWithDeployUrlAndEvidence']}"
        )
        for command in snapshot["pm02Commands"]:
            self.stdout.write(f"- {command}")


def gerar_snapshot_baseline_financeira(
    frontend_path=None,
    frontend_ref="",
    frontend_deploy_url="",
):
    database = _database_snapshot(settings.DATABASES.get("default", {}))
    cache = _cache_snapshot(settings.CACHES.get("default", {}))
    git = _git_snapshot(settings.BASE_DIR)
    frontend = _frontend_snapshot(
        frontend_path,
        frontend_ref=frontend_ref,
        frontend_deploy_url=frontend_deploy_url,
    )

    return {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "project": {
            "backendRoot": str(settings.BASE_DIR),
            "djangoSettingsModule": os.environ.get("DJANGO_SETTINGS_MODULE", ""),
        },
        "git": git,
        "frontend": frontend,
        "environment": {
            "debug": bool(getattr(settings, "DEBUG", False)),
            "allowedHosts": list(getattr(settings, "ALLOWED_HOSTS", [])),
            "csrfTrustedOrigins": list(
                getattr(settings, "CSRF_TRUSTED_ORIGINS", [])
            ),
            "corsAllowedOrigins": list(
                getattr(settings, "CORS_ALLOWED_ORIGINS", [])
            ),
        },
        "canonicalFirst": {
            "enabled": bool(
                getattr(settings, "CANONICAL_FIRST_SETTLEMENT_ENABLED", False)
            ),
            "sources": list(
                getattr(settings, "CANONICAL_FIRST_SETTLEMENT_SOURCES", [])
            ),
        },
        "cache": cache,
        "apiThrottling": _api_throttling_snapshot(
            getattr(settings, "REST_FRAMEWORK", {})
        ),
        "cookies": {
            "sessionEngine": getattr(settings, "SESSION_ENGINE", ""),
            "sessionCookieDomain": getattr(settings, "SESSION_COOKIE_DOMAIN", None),
            "csrfCookieDomain": getattr(settings, "CSRF_COOKIE_DOMAIN", None),
            "sessionCookieSameSite": getattr(settings, "SESSION_COOKIE_SAMESITE", ""),
            "csrfCookieSameSite": getattr(settings, "CSRF_COOKIE_SAMESITE", ""),
            "sessionCookieSecure": bool(
                getattr(settings, "SESSION_COOKIE_SECURE", False)
            ),
            "csrfCookieSecure": bool(getattr(settings, "CSRF_COOKIE_SECURE", False)),
        },
        "database": database,
        "pm02AggregateCommand": PM02_AGGREGATE_COMMAND,
        "pm02StrictServerCommand": PM02_STRICT_SERVER_COMMAND,
        "pm02StrictServerCommandWithDeployUrl": (
            PM02_STRICT_SERVER_COMMAND_WITH_DEPLOY_URL
        ),
        "pm02StrictServerCommandRhremotoProduction": (
            PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION
        ),
        "pm02StrictServerCommandRhremotoProductionWithDeployUrl": (
            PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION_WITH_DEPLOY_URL
        ),
        "pm02StrictServerCommandRhremotoProductionWithEvidence": (
            PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION_WITH_EVIDENCE
        ),
        "pm02StrictServerCommandRhremotoProductionWithDeployUrlAndEvidence": (
            PM02_STRICT_SERVER_COMMAND_RHREMOTO_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE
        ),
        "pm02Commands": PM02_COMMANDS,
        "notes": [
            "Snapshot somente leitura; nao substitui backup real do banco.",
            "Senhas de cache e banco nao sao exibidas.",
            "Repetir comandos PM-02 no servidor antes de ampliar canonical-first.",
        ],
    }


def _salvar_arquivo_snapshot(path_value, content):
    path = Path(path_value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _cache_snapshot(cache_config):
    return {
        "backend": cache_config.get("BACKEND", ""),
        "location": _sanitize_url_or_value(cache_config.get("LOCATION", "")),
    }


def _api_throttling_snapshot(rest_framework_settings):
    classes = []
    for throttle_class in rest_framework_settings.get("DEFAULT_THROTTLE_CLASSES", []):
        if isinstance(throttle_class, str):
            classes.append(throttle_class)
        else:
            classes.append(
                f"{throttle_class.__module__}.{throttle_class.__name__}"
            )

    rates = {
        str(scope): None if rate is None else str(rate)
        for scope, rate in rest_framework_settings.get(
            "DEFAULT_THROTTLE_RATES",
            {},
        ).items()
    }
    return {"classes": classes, "rates": rates}


def _formatar_throttle_rates(rates):
    if not rates:
        return "-"

    return ", ".join(f"{scope}={rate or 'disabled'}" for scope, rate in rates.items())


def _database_snapshot(database_config):
    return {
        "engine": database_config.get("ENGINE", ""),
        "name": str(database_config.get("NAME", "")),
        "host": database_config.get("HOST", ""),
        "port": str(database_config.get("PORT", "")),
        "connMaxAge": database_config.get("CONN_MAX_AGE"),
        "connHealthChecks": bool(database_config.get("CONN_HEALTH_CHECKS", False)),
        "hasPassword": bool(database_config.get("PASSWORD")),
    }


def _frontend_snapshot(frontend_path=None, frontend_ref="", frontend_deploy_url=""):
    path = Path(frontend_path) if frontend_path else DEFAULT_FRONTEND_PATH
    path = path.expanduser()
    exists = path.exists()
    package_json = _read_package_json(path / "package.json") if exists else {}

    return {
        "path": str(path),
        "exists": exists,
        "git": _git_snapshot(path) if exists else _empty_git_snapshot(),
        "packageManager": package_json.get("packageManager", ""),
        "name": package_json.get("name", ""),
        "version": package_json.get("version", ""),
        "declaredReference": frontend_ref or "",
        "deployUrl": frontend_deploy_url or "",
    }


def _read_package_json(path):
    try:
        with path.open("r", encoding="utf-8") as package_file:
            return json.load(package_file)
    except (OSError, json.JSONDecodeError):
        return {}


def _git_snapshot(cwd):
    commit_full = _git_output(cwd, "rev-parse", "HEAD")
    commit_short = _git_output(cwd, "rev-parse", "--short", "HEAD")
    status = _git_output(cwd, "status", "--short")
    dirty = bool(status.strip()) if status is not None else False
    return {
        "available": commit_full is not None,
        "commit": commit_full or "",
        "commitShort": commit_short or "",
        "dirty": dirty,
        "statusLineCount": len([line for line in status.splitlines() if line])
        if status is not None
        else 0,
    }


def _empty_git_snapshot():
    return {
        "available": False,
        "commit": "",
        "commitShort": "",
        "dirty": False,
        "statusLineCount": 0,
    }


def _git_output(cwd, *args):
    try:
        resultado = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            check=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return resultado.stdout.strip()


def _sanitize_url_or_value(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_url_or_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_url_or_value(item) for item in value]
    if not isinstance(value, str):
        return value

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value

    auth = ""
    if parsed.username is not None:
        auth = parsed.username
        if parsed.password is not None:
            auth += ":***"
        auth += "@"
    elif parsed.password is not None:
        auth = ":***@"

    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""

    return urlunsplit(
        (
            parsed.scheme,
            f"{auth}{host}{port}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
