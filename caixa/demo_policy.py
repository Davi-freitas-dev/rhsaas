from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import connection

from .demo_seed import inspect_demo_seed_readiness


DEMO_PUBLIC_GROUP_NAME = "Demo Publica"
DEMO_WRITE_DENIED_MESSAGE = "Dados de exemplo da demo sao somente leitura."
DEMO_SCHEMA_NOT_READY_MESSAGE = (
    "O ambiente demo ainda nao esta pronto para alteracoes."
)

# Relations are deliberately directed toward the budget/event root. A new
# budget that references a seed client or service must remain a common object.
DEMO_SEED_PARENT_FIELDS = {
    "orcamentoitem": ("orcamento",),
    "orcamentocustoextra": ("orcamento",),
    "evento": ("orcamento",),
    "receitaoperacional": ("evento",),
    "despesaoperacional": ("evento",),
    "eventocustoservico": ("evento",),
    "eventocustoextra": ("evento",),
    "participacaoservidorevento": ("evento",),
    "servidoreventodiatrabalhado": ("participacao",),
    "pagamentoeventocustoservico": ("custo_servico",),
    "pagamentoeventocustoextra": ("custo_extra",),
    "dividafinanceira": ("evento",),
    "parceladivida": ("divida",),
    "pagamentoparceladivida": ("parcela",),
    "investimento": ("evento",),
    "financiamentomovimentacao": ("evento", "divida_financeira"),
    "lancamentofinanceiro": (
        "evento",
        "receita_operacional",
        "despesa_operacional",
        "pagamento_custo_servico",
        "pagamento_custo_extra",
        "pagamento_parcela_divida",
        "investimento",
        "financiamento_movimentacao",
    ),
    "obrigacaofinanceira": (
        "evento",
        "receita_operacional",
        "despesa_operacional",
        "evento_custo_servico",
        "evento_custo_extra",
        "parcela_divida",
        "investimento",
        "financiamento_movimentacao",
    ),
    "baixafinanceira": (
        "evento",
        "receita_operacional",
        "despesa_operacional",
        "pagamento_custo_servico",
        "pagamento_custo_extra",
        "pagamento_parcela_divida",
        "investimento",
        "financiamento_movimentacao",
    ),
    "baixafinanceiraalocacao": ("baixa", "obrigacao"),
}


def is_demo_public_user(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.groups.filter(name=DEMO_PUBLIC_GROUP_NAME).exists()
    )


def is_applicable_demo_schema(schema_name=None):
    schema_name = schema_name or getattr(connection, "schema_name", "")
    if not schema_name.startswith("demo"):
        return False
    suffix = schema_name.removeprefix("demo")
    return suffix.isdigit() and 1 <= int(suffix) <= 10


def is_demo_seed_required_schema(schema_name=None):
    schema_name = schema_name or getattr(connection, "schema_name", "")
    return (
        is_applicable_demo_schema(schema_name)
        and schema_name != settings.DEMO_PERMANENT_TENANT_SCHEMA
    )


def is_demo_seed_object(obj, *, _visited=None, allow_lazy=True):
    if obj is None or not hasattr(obj, "_meta"):
        return False

    visited = _visited or set()
    identity = (obj._meta.label_lower, getattr(obj, "pk", None), id(obj))
    if identity in visited:
        return False
    visited.add(identity)

    if hasattr(obj, "demo_seed_key"):
        return bool(getattr(obj, "demo_seed_key", None))

    for field_name in DEMO_SEED_PARENT_FIELDS.get(obj._meta.model_name, ()):
        if allow_lazy:
            try:
                parent = getattr(obj, field_name, None)
            except ObjectDoesNotExist:
                parent = None
        else:
            state = getattr(obj, "_state", None)
            parent = (
                state.fields_cache.get(field_name)
                if state is not None
                else getattr(obj, field_name, None)
            )
        if parent is not None and is_demo_seed_object(
            parent,
            _visited=visited,
            allow_lazy=allow_lazy,
        ):
            return True
    return False


def assert_demo_write_allowed(user, obj=None, *, operation="write"):
    if not is_demo_public_user(user) or not is_applicable_demo_schema():
        return

    if not is_demo_seed_required_schema():
        return

    readiness = inspect_demo_seed_readiness()
    if not readiness.ready:
        raise PermissionDenied(DEMO_SCHEMA_NOT_READY_MESSAGE)
    if obj is not None and is_demo_seed_object(obj):
        raise PermissionDenied(DEMO_WRITE_DENIED_MESSAGE)


def demo_object_flags(obj, *, allow_lazy=True):
    schema_name = getattr(connection, "schema_name", "")
    is_seed = (
        schema_name != settings.DEMO_PERMANENT_TENANT_SCHEMA
        and is_demo_seed_object(obj, allow_lazy=allow_lazy)
    )
    return {
        "isSeed": is_seed,
        "isReadOnly": is_seed,
    }
