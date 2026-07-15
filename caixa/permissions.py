from functools import wraps

from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import JsonResponse
from django.utils.cache import add_never_cache_headers
from django_tenants.utils import get_public_schema_name


API_AUTHENTICATION_REQUIRED_PAYLOAD = {
    "detail": "Authentication credentials were not provided.",
}
API_PERMISSION_DENIED_PAYLOAD = {"detail": "Permission denied."}


VIEW_EVENT_PERMISSION = "caixa.view_evento"
CHANGE_EVENT_PERMISSION = "caixa.change_evento"
DASHBOARD_PERMISSION = VIEW_EVENT_PERMISSION
VIEW_REVENUE_PERMISSION = "caixa.view_receitaoperacional"
CHANGE_REVENUE_PERMISSION = "caixa.change_receitaoperacional"
VIEW_EXPENSE_PERMISSION = "caixa.view_despesaoperacional"
CHANGE_EXPENSE_PERMISSION = "caixa.change_despesaoperacional"
VIEW_CLIENT_PERMISSION = "caixa.view_cliente"
ADD_CLIENT_PERMISSION = "caixa.add_cliente"
CHANGE_CLIENT_PERMISSION = "caixa.change_cliente"
VIEW_SERVICE_PERMISSION = "caixa.view_servico"
ADD_SERVICE_PERMISSION = "caixa.add_servico"
CHANGE_SERVICE_PERMISSION = "caixa.change_servico"
VIEW_FINANCIAL_CONFIGURATION_PERMISSION = "caixa.view_configuracaofinanceira"
ADD_FINANCIAL_CONFIGURATION_PERMISSION = "caixa.add_configuracaofinanceira"
CHANGE_FINANCIAL_CONFIGURATION_PERMISSION = "caixa.change_configuracaofinanceira"
VIEW_FIXED_COST_PERMISSION = "caixa.view_custofixo"
ADD_FIXED_COST_PERMISSION = "caixa.add_custofixo"
CHANGE_FIXED_COST_PERMISSION = "caixa.change_custofixo"
VIEW_EVENT_SERVICE_COST_PERMISSION = "caixa.view_eventocustoservico"
CHANGE_EVENT_SERVICE_COST_PERMISSION = "caixa.change_eventocustoservico"
VIEW_EVENT_EXTRA_COST_PERMISSION = "caixa.view_eventocustoextra"
CHANGE_EVENT_EXTRA_COST_PERMISSION = "caixa.change_eventocustoextra"
VIEW_BUDGET_PERMISSION = "caixa.view_orcamento"
ADD_BUDGET_PERMISSION = "caixa.add_orcamento"
ADD_BUDGET_ITEM_PERMISSION = "caixa.add_orcamentoitem"
CHANGE_BUDGET_PERMISSION = "caixa.change_orcamento"
APPROVE_BUDGET_PERMISSION = "caixa.approve_orcamento"
FINANCIAL_MONTH_PERMISSIONS = (
    "caixa.view_parceladivida",
    "caixa.view_receitaoperacional",
)
FINANCIAL_DEBT_INSTALLMENTS_PERMISSION = "caixa.view_parceladivida"
FINANCIAL_CREDITORS_PERMISSION = "caixa.view_credor"
FINANCIAL_INVESTMENTS_PERMISSION = "caixa.view_investimento"
FINANCIAL_LEDGER_PERMISSION = "caixa.view_lancamentofinanceiro"
FINANCIAL_OBLIGATIONS_PERMISSION = FINANCIAL_LEDGER_PERMISSION
ADD_FINANCIAL_CREDITOR_PERMISSION = "caixa.add_credor"
ADD_FINANCIAL_INVESTMENT_PERMISSION = "caixa.add_investimento"
ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION = "caixa.add_financiamentomovimentacao"
ADD_FINANCIAL_DEBT_PERMISSION = "caixa.add_dividafinanceira"
PAY_DEBT_INSTALLMENT_PERMISSION = "caixa.add_pagamentoparceladivida"
ADD_EVENT_EXTRA_COST_PERMISSION = "caixa.add_eventocustoextra"
PAY_EVENT_SERVICE_COST_PERMISSION = "caixa.add_pagamentoeventocustoservico"
PAY_EVENT_EXTRA_COST_PERMISSION = "caixa.add_pagamentoeventocustoextra"


PERMISSION_PROFILES = {
    "Administrador": "__all__",
    "Financeiro": [
        "view_cliente",
        "add_cliente",
        "change_cliente",
        "view_servico",
        "add_servico",
        "change_servico",
        "view_configuracaofinanceira",
        "add_configuracaofinanceira",
        "change_configuracaofinanceira",
        "view_evento",
        "view_receitaoperacional",
        "add_receitaoperacional",
        "change_receitaoperacional",
        "view_despesaoperacional",
        "add_despesaoperacional",
        "change_despesaoperacional",
        "view_custofixo",
        "add_custofixo",
        "change_custofixo",
        "view_investimento",
        "add_investimento",
        "change_investimento",
        "view_financiamentomovimentacao",
        "add_financiamentomovimentacao",
        "change_financiamentomovimentacao",
        "view_credor",
        "add_credor",
        "change_credor",
        "view_dividafinanceira",
        "add_dividafinanceira",
        "change_dividafinanceira",
        "view_obrigacaofinanceira",
        "view_baixafinanceira",
        "view_baixafinanceiraalocacao",
        "view_parceladivida",
        "add_parceladivida",
        "change_parceladivida",
        "view_pagamentoparceladivida",
        "add_pagamentoparceladivida",
        "change_pagamentoparceladivida",
        "view_eventocustoservico",
        "add_eventocustoservico",
        "change_eventocustoservico",
        "view_eventocustoextra",
        "add_eventocustoextra",
        "change_eventocustoextra",
        "view_pagamentoeventocustoservico",
        "add_pagamentoeventocustoservico",
        "change_pagamentoeventocustoservico",
        "view_pagamentoeventocustoextra",
        "add_pagamentoeventocustoextra",
        "change_pagamentoeventocustoextra",
        "view_lancamentofinanceiro",
    ],
    "Operacional": [
        "view_cliente",
        "view_servico",
        "view_configuracaofinanceira",
        "view_orcamento",
        "view_orcamentoitem",
        "view_evento",
        "add_evento",
        "change_evento",
        "view_eventocustoservico",
        "add_eventocustoservico",
        "change_eventocustoservico",
        "view_eventocustoextra",
        "add_eventocustoextra",
        "change_eventocustoextra",
        "view_pagamentoeventocustoservico",
        "add_pagamentoeventocustoservico",
        "change_pagamentoeventocustoservico",
        "view_pagamentoeventocustoextra",
        "add_pagamentoeventocustoextra",
        "change_pagamentoeventocustoextra",
    ],
    "Demo Publica": [
        "view_cliente",
        "add_cliente",
        "change_cliente",
        "view_servico",
        "add_servico",
        "change_servico",
        "view_configuracaofinanceira",
        "view_orcamento",
        "add_orcamento",
        "change_orcamento",
        "view_orcamentoitem",
        "add_orcamentoitem",
        "change_orcamentoitem",
        "approve_orcamento",
        "view_evento",
        "add_evento",
        "change_evento",
        "view_receitaoperacional",
        "view_despesaoperacional",
        "view_custofixo",
        "view_eventocustoservico",
        "view_eventocustoextra",
    ],
}


def sincronizar_grupos_permissoes():
    permissoes_caixa = Permission.objects.filter(content_type__app_label="caixa")

    for nome_grupo, codenames in PERMISSION_PROFILES.items():
        grupo, _ = Group.objects.get_or_create(name=nome_grupo)

        if codenames == "__all__":
            grupo.permissions.set(permissoes_caixa)
            continue

        grupo.permissions.set(permissoes_caixa.filter(codename__in=codenames))


def require_permission(permissions):
    def decorator(view_func):
        return login_required(
            permission_required(permissions, raise_exception=True)(view_func)
        )

    return decorator


def require_any_permission(*permissions):
    def decorator(view_func):
        @wraps(view_func)
        def guarded_view(request, *args, **kwargs):
            if not any(request.user.has_perm(permission) for permission in permissions):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return login_required(guarded_view)

    return decorator


def current_schema_name():
    return getattr(connection, "schema_name", get_public_schema_name())


def is_public_schema():
    return current_schema_name() == get_public_schema_name()


def is_tenant_schema():
    return not is_public_schema()


def can_approve_budget(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and is_tenant_schema()
        and user.has_perm(APPROVE_BUDGET_PERMISSION)
    )


def is_tenant_administrator(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_superuser
        and is_tenant_schema()
    )


def is_platform_operator(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.is_superuser
        and is_public_schema()
    )


def require_tenant_administrator(view_func):
    return user_passes_test(
        is_tenant_administrator,
        login_url="caixa:login",
    )(view_func)


def require_platform_operator(view_func):
    return user_passes_test(
        is_platform_operator,
        login_url="caixa:login",
    )(view_func)


def require_superuser(view_func):
    return require_tenant_administrator(view_func)


def normalizar_lista_permissoes(permissions):
    if isinstance(permissions, str):
        return [permissions]

    return list(permissions)


def api_no_store_json_response(payload, *, status=200, json_dumps_params=None):
    response_options = {"status": status}
    if json_dumps_params is not None:
        response_options["json_dumps_params"] = json_dumps_params
    response = JsonResponse(payload, **response_options)
    add_never_cache_headers(response)
    return response


def api_auth_control_response(payload, *, status):
    return api_no_store_json_response(payload, status=status)


def api_authentication_required_response():
    return api_auth_control_response(API_AUTHENTICATION_REQUIRED_PAYLOAD, status=401)


def api_permission_denied_response():
    return api_auth_control_response(API_PERMISSION_DENIED_PAYLOAD, status=403)


def require_api_permission(permissions):
    required_permissions = normalizar_lista_permissoes(permissions)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return api_authentication_required_response()

            if not all(
                request.user.has_perm(permission)
                for permission in required_permissions
            ):
                return api_permission_denied_response()

            response = view_func(request, *args, **kwargs)
            add_never_cache_headers(response)
            return response

        return wrapper

    return decorator


def require_api_tenant_administrator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return api_authentication_required_response()

        if not is_tenant_administrator(request.user):
            return api_permission_denied_response()

        response = view_func(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response

    return wrapper


def require_api_superuser(view_func):
    return require_api_tenant_administrator(view_func)


def require_api_platform_operator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return api_authentication_required_response()

        if not is_platform_operator(request.user):
            return api_permission_denied_response()

        response = view_func(request, *args, **kwargs)
        add_never_cache_headers(response)
        return response

    return wrapper
