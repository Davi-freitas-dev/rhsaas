from django.core.management.base import CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name


def current_schema_name():
    return getattr(connection, "schema_name", None) or get_public_schema_name()


def ensure_tenant_schema(command_name, *, action="manipular dados operacionais"):
    schema_name = current_schema_name()
    if not schema_name or schema_name == get_public_schema_name():
        raise CommandError(
            f"O comando '{command_name}' deve ser executado em um schema de tenant "
            f"para {action}. Use tenant_command com --schema=<schema_name>."
        )
    return schema_name
