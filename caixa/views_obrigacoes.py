import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, content_negotiation_class, permission_classes
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import (
    FINANCIAL_OBLIGATIONS_PERMISSION,
    FINANCIAL_DEBT_INSTALLMENTS_PERMISSION,
    FINANCIAL_INVESTMENTS_PERMISSION,
    VIEW_EXPENSE_PERMISSION,
    VIEW_FIXED_COST_PERMISSION,
    VIEW_REVENUE_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .contracts_obrigacoes import PERMISSOES_BAIXA_NATIVA
from .selectors_obrigacoes import (
    ORIGEM_CUSTO_EXTRA,
    ORIGEM_CUSTO_FIXO,
    ORIGEM_CUSTO_SERVICO,
    ORIGEM_DESPESA_OPERACIONAL,
    ORIGEM_FINANCIAMENTO,
    ORIGEM_INVESTIMENTO,
    ORIGEM_PARCELA_DIVIDA,
    ORIGEM_RECEITA_OPERACIONAL,
)
from .serializers_obrigacoes import (
    montar_exportacao_obrigacoes_financeiras_csv,
    montar_payload_obrigacoes_financeiras_api,
    normalizar_filtros_obrigacoes,
)
from .services_obrigacoes import liquidar_obrigacao_financeira_com_contexto_canonico


OBRIGACOES_SOURCE_VIEW_PERMISSIONS = {
    ORIGEM_RECEITA_OPERACIONAL: VIEW_REVENUE_PERMISSION,
    ORIGEM_DESPESA_OPERACIONAL: VIEW_EXPENSE_PERMISSION,
    ORIGEM_CUSTO_FIXO: VIEW_FIXED_COST_PERMISSION,
    ORIGEM_CUSTO_SERVICO: "caixa.view_eventocustoservico",
    ORIGEM_CUSTO_EXTRA: "caixa.view_eventocustoextra",
    ORIGEM_PARCELA_DIVIDA: FINANCIAL_DEBT_INSTALLMENTS_PERMISSION,
    ORIGEM_INVESTIMENTO: FINANCIAL_INVESTMENTS_PERMISSION,
    ORIGEM_FINANCIAMENTO: FINANCIAL_DEBT_INSTALLMENTS_PERMISSION,
}
PERMISSION_SCOPE_PAYMENTS = "payments"
EXPORT_SCOPES_OBRIGACOES = {
    "obligations",
    "revenues",
    "expenses",
    "payments",
}
EXPENSE_EXPORT_SOURCES = (
    ORIGEM_DESPESA_OPERACIONAL,
    ORIGEM_CUSTO_SERVICO,
    ORIGEM_CUSTO_EXTRA,
    ORIGEM_CUSTO_FIXO,
)
IGNORED_EXPORT_PAGINATION_PARAMS = (
    "limit",
    "offset",
    "queueLimit",
    "queueOffset",
)


def _payload_json(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    if content_type != "application/json":
        return None

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _erro_validacao_payload(erro):
    if hasattr(erro, "message_dict"):
        return erro.message_dict
    return {"detail": erro.messages}


class _ExportacaoObrigacoesContentNegotiation(DefaultContentNegotiation):
    class settings:
        URL_FORMAT_OVERRIDE = None


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_obrigacoes_financeiras(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    params = _params_obrigacoes_autorizados(request)
    if params is None:
        return drf_response_from_json_response(api_permission_denied_response())

    payload = montar_payload_obrigacoes_financeiras_api(params, request.user)
    return drf_response_from_json_response(
        api_no_store_json_response(
            payload,
            json_dumps_params={"ensure_ascii": False},
        )
    )


@require_GET
@extend_schema(responses=OpenApiTypes.BINARY, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@content_negotiation_class(_ExportacaoObrigacoesContentNegotiation)
@permission_classes([AllowAny])
def api_exportar_obrigacoes_financeiras(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    try:
        params = _params_exportacao_obrigacoes_autorizados(request)
    except ValidationError as erro:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _erro_validacao_payload(erro)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    if params is None:
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        exportacao = montar_exportacao_obrigacoes_financeiras_csv(
            params,
            request.user,
        )
    except ValidationError as erro:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _erro_validacao_payload(erro)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    response = HttpResponse(
        exportacao["content"],
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{exportacao["filename"]}"'
    response["Cache-Control"] = "no-store"
    return response


def _params_obrigacoes_autorizados(request):
    return _params_obrigacoes_autorizados_por_usuario(request.GET, request.user)


def _params_obrigacoes_autorizados_por_usuario(raw_params, user):
    if user.has_perm(FINANCIAL_OBLIGATIONS_PERMISSION):
        return raw_params

    params = raw_params.copy()
    filtros = normalizar_filtros_obrigacoes(params)
    source = _source_obrigacoes(filtros)
    permission_scope = _permission_scope_obrigacoes(filtros)

    if permission_scope == PERMISSION_SCOPE_PAYMENTS:
        return _params_obrigacoes_pagamentos_autorizados(
            params,
            user,
            source,
        )

    if source and _usuario_pode_ver_source_obrigacoes(user, source):
        return params

    return None


def _params_exportacao_obrigacoes_autorizados(request):
    params = request.GET.copy()
    for nome in IGNORED_EXPORT_PAGINATION_PARAMS:
        params.pop(nome, None)

    export_scope = str(params.get("exportScope") or "obligations").strip()
    if export_scope not in EXPORT_SCOPES_OBRIGACOES:
        raise ValidationError({"exportScope": "Escopo de exportacao invalido."})

    _aplicar_escopo_exportacao_obrigacoes(params, export_scope)
    if export_scope == "payments":
        filtros = normalizar_filtros_obrigacoes(params)
        return _params_obrigacoes_pagamentos_autorizados(
            params,
            request.user,
            _source_obrigacoes(filtros),
        )

    return _params_obrigacoes_autorizados_por_usuario(params, request.user)


def _aplicar_escopo_exportacao_obrigacoes(params, export_scope):
    if export_scope == "revenues":
        params["obligationType"] = "receber"
        params["source"] = ORIGEM_RECEITA_OPERACIONAL
        params.pop("sources", None)
        return

    if export_scope == "expenses":
        params["obligationType"] = "pagar"
        params["cashFlowGroup"] = "fco"
        source = str(params.get("source") or "").strip()
        if source:
            if source not in EXPENSE_EXPORT_SOURCES:
                raise ValidationError({"source": "Origem invalida para exportacao de despesas."})
            params.pop("sources", None)
            return

        sources = _normalizar_sources_exportacao(params.get("sources"))
        if sources:
            invalidas = sorted(set(sources) - set(EXPENSE_EXPORT_SOURCES))
            if invalidas:
                raise ValidationError({"sources": "Origem invalida para exportacao de despesas."})
            params["sources"] = ",".join(sources)
            return

        params["sources"] = ",".join(EXPENSE_EXPORT_SOURCES)
        return

    if export_scope == "payments":
        params["permissionScope"] = PERMISSION_SCOPE_PAYMENTS
        params["obligationType"] = "pagar"


def _normalizar_sources_exportacao(valor):
    if isinstance(valor, (list, tuple, set)):
        candidatos = valor
    else:
        candidatos = str(valor or "").replace(";", ",").split(",")

    sources = []
    for candidato in candidatos:
        source = str(candidato or "").strip()
        if source and source not in sources:
            sources.append(source)
    return sources


def _params_obrigacoes_pagamentos_autorizados(params, user, requested_source):
    allowed_sources = _payment_sources_permitidas(user)
    if not allowed_sources:
        return None

    if requested_source:
        if requested_source not in allowed_sources:
            return None

        params["source"] = requested_source
        return params

    params["sources"] = ",".join(allowed_sources)
    return params


def _source_obrigacoes(filtros):
    return filtros.get("source") or ""


def _permission_scope_obrigacoes(filtros):
    return str(filtros.get("permissionScope") or "").strip()


def _usuario_pode_ver_source_obrigacoes(user, source):
    permission = OBRIGACOES_SOURCE_VIEW_PERMISSIONS.get(source)
    return bool(permission and user.has_perm(permission))


def _payment_sources_permitidas(user):
    return [
        source
        for source, permission in PERMISSOES_BAIXA_NATIVA.items()
        if user.has_perm(permission)
    ]


@csrf_protect
@require_POST
@extend_schema(
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@permission_classes([AllowAny])
def api_liquidar_obrigacao_financeira(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    payload = _payload_json(request)
    if payload is None:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"detail": "JSON inválido ou Content-Type incorreto."},
                status=400,
            )
        )

    try:
        resultado = liquidar_obrigacao_financeira_com_contexto_canonico(
            payload.get("source"),
            payload.get("sourceId"),
            payload,
            request.user,
        )
    except PermissionDenied:
        return drf_response_from_json_response(api_permission_denied_response())
    except ValidationError as erro:
        return drf_response_from_json_response(
            api_no_store_json_response(
                {"errors": _erro_validacao_payload(erro)},
                status=400,
                json_dumps_params={"ensure_ascii": False},
            )
        )

    return drf_response_from_json_response(
        api_no_store_json_response(
            {
                "data": {
                    "item": resultado["item"],
                    "canonicalSettlement": resultado["canonicalSettlement"],
                    "settlement": resultado["settlement"],
                    "message": "Obrigação financeira atualizada com sucesso.",
                }
            },
            json_dumps_params={"ensure_ascii": False},
        )
    )


# DRF marca APIView como csrf_exempt; este endpoint preserva o bloqueio CSRF do Django.
api_liquidar_obrigacao_financeira.csrf_exempt = False
