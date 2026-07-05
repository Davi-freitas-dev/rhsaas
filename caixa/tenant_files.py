import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import connection
from django_tenants.utils import get_public_schema_name


_SAFE_SCHEMA_RE = re.compile(r"^[A-Za-z0-9_]+$")


def current_schema_name():
    return getattr(connection, "schema_name", get_public_schema_name())


def validate_schema_name(schema_name):
    schema_name = str(schema_name or "").strip()
    if not schema_name or not _SAFE_SCHEMA_RE.match(schema_name):
        raise SuspiciousOperation("Schema invalido para caminho de arquivo.")
    return schema_name


def artifact_scope_for_schema(schema_name=None):
    schema_name = validate_schema_name(schema_name or current_schema_name())
    if schema_name == get_public_schema_name():
        return "platform", schema_name
    return "tenant", schema_name


def artifacts_root_for_schema(schema_name=None):
    scope, schema_name = artifact_scope_for_schema(schema_name)
    base = Path(settings.BASE_DIR) / "backups"
    if scope == "platform":
        return base / "platform"
    return base / "tenants" / schema_name


def backup_dir_for_schema(schema_name=None):
    return artifacts_root_for_schema(schema_name) / "db"


def recadastro_dir_for_schema(schema_name=None):
    return artifacts_root_for_schema(schema_name) / "recadastro"
