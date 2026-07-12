import json
import logging
from functools import wraps

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.cache import never_cache
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_GET, require_POST
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import (
    api_view,
    parser_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.parsers import BaseParser, JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .contracts_obrigacoes import PERMISSOES_BAIXA_NATIVA
from .permissions import (
    ADD_CLIENT_PERMISSION,
    ADD_BUDGET_ITEM_PERMISSION,
    ADD_BUDGET_PERMISSION,
    ADD_EVENT_EXTRA_COST_PERMISSION,
    ADD_FINANCIAL_CREDITOR_PERMISSION,
    ADD_FINANCIAL_CONFIGURATION_PERMISSION,
    ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION,
    ADD_FINANCIAL_INVESTMENT_PERMISSION,
    ADD_FIXED_COST_PERMISSION,
    ADD_SERVICE_PERMISSION,
    CHANGE_BUDGET_PERMISSION,
    CHANGE_CLIENT_PERMISSION,
    CHANGE_EVENT_PERMISSION,
    CHANGE_EVENT_EXTRA_COST_PERMISSION,
    CHANGE_EVENT_SERVICE_COST_PERMISSION,
    CHANGE_EXPENSE_PERMISSION,
    CHANGE_FINANCIAL_CONFIGURATION_PERMISSION,
    CHANGE_FIXED_COST_PERMISSION,
    CHANGE_REVENUE_PERMISSION,
    CHANGE_SERVICE_PERMISSION,
    DASHBOARD_PERMISSION,
    FINANCIAL_CREDITORS_PERMISSION,
    FINANCIAL_DEBT_INSTALLMENTS_PERMISSION,
    VIEW_FINANCIAL_CONFIGURATION_PERMISSION,
    FINANCIAL_INVESTMENTS_PERMISSION,
    FINANCIAL_LEDGER_PERMISSION,
    FINANCIAL_MONTH_PERMISSIONS,
    FINANCIAL_OBLIGATIONS_PERMISSION,
    PAY_DEBT_INSTALLMENT_PERMISSION,
    PAY_EVENT_EXTRA_COST_PERMISSION,
    PAY_EVENT_SERVICE_COST_PERMISSION,
    VIEW_CLIENT_PERMISSION,
    VIEW_BUDGET_PERMISSION,
    VIEW_EVENT_EXTRA_COST_PERMISSION,
    VIEW_EVENT_PERMISSION,
    VIEW_EVENT_SERVICE_COST_PERMISSION,
    VIEW_EXPENSE_PERMISSION,
    VIEW_FIXED_COST_PERMISSION,
    VIEW_REVENUE_PERMISSION,
    VIEW_SERVICE_PERMISSION,
    can_approve_budget,
    is_platform_operator,
    is_tenant_administrator,
    current_schema_name,
)
from .throttling import AuthLoginRateThrottle

GENERIC_LOGIN_ERROR = "Usuario ou senha invalidos."

logger = logging.getLogger(__name__)


class IgnoreBodyParser(BaseParser):
    media_type = "*/*"

    def parse(self, stream, media_type=None, parser_context=None):
        return {}


def _csrf_checked_callback(request, *args, **kwargs):
    return None


def csrf_protect_drf_view(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        def dummy_get_response(request):
            return None

        check = CsrfViewMiddleware(dummy_get_response)
        check.process_request(request)
        response = check.process_view(
            request,
            _csrf_checked_callback,
            args,
            kwargs,
        )
        if response is not None:
            return response

        return view_func(request, *args, **kwargs)

    return wrapped


def _user_payload(user):
    permissions = {
        "canViewDashboard": user.has_perm(DASHBOARD_PERMISSION),
        "canViewRevenues": user.has_perm(VIEW_REVENUE_PERMISSION),
        "canChangeRevenues": user.has_perm(CHANGE_REVENUE_PERMISSION),
        "canViewExpenses": user.has_perm(VIEW_EXPENSE_PERMISSION),
        "canChangeExpenses": user.has_perm(CHANGE_EXPENSE_PERMISSION),
        "canViewEvents": user.has_perm(VIEW_EVENT_PERMISSION),
        "canChangeEvents": user.has_perm(CHANGE_EVENT_PERMISSION),
        "canViewEventCosts": user.has_perm(VIEW_EVENT_PERMISSION),
        "canViewEventServiceCosts": user.has_perm(VIEW_EVENT_SERVICE_COST_PERMISSION),
        "canChangeEventServiceCosts": user.has_perm(
            CHANGE_EVENT_SERVICE_COST_PERMISSION
        ),
        "canViewEventExtraCosts": user.has_perm(VIEW_EVENT_EXTRA_COST_PERMISSION),
        "canChangeEventExtraCosts": user.has_perm(CHANGE_EVENT_EXTRA_COST_PERMISSION),
        "canViewClients": user.has_perm(VIEW_CLIENT_PERMISSION),
        "canAddClient": user.has_perm(ADD_CLIENT_PERMISSION),
        "canChangeClient": user.has_perm(CHANGE_CLIENT_PERMISSION),
        "canViewServices": user.has_perm(VIEW_SERVICE_PERMISSION),
        "canAddService": user.has_perm(ADD_SERVICE_PERMISSION),
        "canChangeService": user.has_perm(CHANGE_SERVICE_PERMISSION),
        "canViewFinancialConfigurations": user.has_perm(
            VIEW_FINANCIAL_CONFIGURATION_PERMISSION
        ),
        "canAddFinancialConfiguration": user.has_perm(
            ADD_FINANCIAL_CONFIGURATION_PERMISSION
        ),
        "canChangeFinancialConfiguration": user.has_perm(
            CHANGE_FINANCIAL_CONFIGURATION_PERMISSION
        ),
        "canViewBudgets": user.has_perm(VIEW_BUDGET_PERMISSION),
        "canAddBudget": all(
            user.has_perm(permission)
            for permission in [ADD_BUDGET_PERMISSION, ADD_BUDGET_ITEM_PERMISSION]
        ),
        "canChangeBudget": user.has_perm(CHANGE_BUDGET_PERMISSION),
        "canApproveBudget": can_approve_budget(user),
        "canViewFixedCosts": user.has_perm(VIEW_FIXED_COST_PERMISSION),
        "canAddFixedCost": user.has_perm(ADD_FIXED_COST_PERMISSION),
        "canChangeFixedCost": user.has_perm(CHANGE_FIXED_COST_PERMISSION),
        "canViewFinancialMonth": all(
            user.has_perm(permission)
            for permission in FINANCIAL_MONTH_PERMISSIONS
        ),
        "canViewFinancialDebtInstallments": user.has_perm(
            FINANCIAL_DEBT_INSTALLMENTS_PERMISSION
        ),
        "canViewFinancialCreditors": user.has_perm(FINANCIAL_CREDITORS_PERMISSION),
        "canAddFinancialCreditor": user.has_perm(
            ADD_FINANCIAL_CREDITOR_PERMISSION
        ),
        "canViewFinancialInvestments": user.has_perm(
            FINANCIAL_INVESTMENTS_PERMISSION
        ),
        "canAddFinancialInvestment": user.has_perm(
            ADD_FINANCIAL_INVESTMENT_PERMISSION
        ),
        "canAddFinancialFinancingMovement": user.has_perm(
            ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION
        ),
        "canViewFinancialLedger": user.has_perm(FINANCIAL_LEDGER_PERMISSION),
        "canViewFinancialObligations": user.has_perm(
            FINANCIAL_OBLIGATIONS_PERMISSION
        ),
        "canPayFinancialDebtInstallment": user.has_perm(
            PAY_DEBT_INSTALLMENT_PERMISSION
        ),
        "canAddEventExtraCost": user.has_perm(
            ADD_EVENT_EXTRA_COST_PERMISSION
        ),
        "canPayEventServiceCost": user.has_perm(PAY_EVENT_SERVICE_COST_PERMISSION),
        "canPayEventExtraCost": user.has_perm(PAY_EVENT_EXTRA_COST_PERMISSION),
        "canUsePayments": any(
            user.has_perm(permission)
            for permission in PERMISSOES_BAIXA_NATIVA.values()
        ),
        "canManageBackups": is_platform_operator(user) or is_tenant_administrator(user),
    }

    return {
        "id": user.pk,
        "username": user.get_username(),
        "displayName": user.get_full_name() or user.get_username(),
        "isStaff": user.is_staff,
        "isSuperuser": user.is_superuser,
        "isTenantAdmin": is_tenant_administrator(user),
        "isPlatformOperator": is_platform_operator(user),
        **permissions,
        "permissions": permissions,
    }


def _json_payload(request):
    if not request.body:
        return {}

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _is_json_request(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    return content_type == "application/json"


def _string_value(payload, key, *, strip=True):
    value = payload.get(key)
    if not isinstance(value, str):
        return ""
    return value.strip() if strip else value


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "")


def _audit_auth_event(request, action, outcome, *, user=None):
    logger.info(
        "auth_event action=%s outcome=%s schema=%s user_id=%s host=%s ip=%s",
        action,
        outcome,
        current_schema_name(),
        getattr(user, "pk", "") or "",
        request.get_host(),
        _client_ip(request),
    )


@ensure_csrf_cookie
@never_cache
@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_auth_csrf(request):
    return Response({"csrfToken": get_token(request)})


@never_cache
@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_auth_session(request):
    if not request.user.is_authenticated:
        return Response({"authenticated": False})

    return Response(
        {
            "authenticated": True,
            "user": _user_payload(request.user),
            "csrfToken": get_token(request),
        }
    )


@require_POST
@csrf_protect_drf_view
@sensitive_post_parameters("password")
@sensitive_variables("password")
@never_cache
@extend_schema(
    request=OpenApiTypes.OBJECT,
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["POST"])
@parser_classes([JSONParser])
@throttle_classes([AuthLoginRateThrottle])
@permission_classes([AllowAny])
def api_auth_login(request):
    django_request = getattr(request, "_request", request)

    if not _is_json_request(django_request):
        return Response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )
    payload = _json_payload(django_request)

    if payload is None:
        return Response({"detail": "JSON invalido."}, status=400)

    username = _string_value(payload, "username")
    password = _string_value(payload, "password", strip=False)

    if not username or not password:
        return Response({"detail": "Informe usuario e senha."}, status=400)

    form = AuthenticationForm(
        request=django_request,
        data={
            "username": username,
            "password": password,
        },
    )

    if not form.is_valid():
        _audit_auth_event(django_request, "login", "failed")
        return Response({"detail": GENERIC_LOGIN_ERROR}, status=401)

    user = form.get_user()
    login(django_request, user)
    _audit_auth_event(django_request, "login", "success", user=user)

    return Response(
        {
            "authenticated": True,
            "user": _user_payload(user),
            "csrfToken": get_token(django_request),
        }
    )


@require_POST
@csrf_protect_drf_view
@never_cache
@extend_schema(
    request=None,
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["POST"])
@parser_classes([IgnoreBodyParser])
@permission_classes([AllowAny])
def api_auth_logout(request):
    django_request = getattr(request, "_request", request)
    user = django_request.user if django_request.user.is_authenticated else None
    _audit_auth_event(django_request, "logout", "success", user=user)
    logout(django_request)
    return Response({"authenticated": False, "csrfToken": get_token(django_request)})
