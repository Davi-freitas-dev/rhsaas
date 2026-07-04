import json

from django.views.decorators.http import require_GET
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .frontend_bridge import legacy_frontend_redirect_required_response
from .permissions import (
    FINANCIAL_MONTH_PERMISSIONS,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
    require_permission,
)
from .serializers_mes_financeiro import montar_payload_mes_financeiro_api
from .utils_request import filtros_texto


FILTROS_MES_FINANCEIRO_CANONICOS = [
    "mes",
    "period",
    "startDate",
    "endDate",
    "quickPeriod",
    "eventId",
    "clientId",
    "contractCode",
    "status",
    "source",
]


@require_permission(FINANCIAL_MONTH_PERMISSIONS)
def mes_financeiro(request):
    return legacy_frontend_redirect_required_response(request, "mes_financeiro")


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_mes_financeiro(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not all(
        request.user.has_perm(permission)
        for permission in FINANCIAL_MONTH_PERMISSIONS
    ):
        return drf_response_from_json_response(api_permission_denied_response())

    payload = montar_payload_mes_financeiro_api(
        filtros_mes_financeiro_api(request)
    )
    return drf_response_from_json_response(
        api_no_store_json_response(
            payload,
            json_dumps_params={"ensure_ascii": False},
        )
    )


def filtros_mes_financeiro_api(request):
    filtros = filtros_texto(request, FILTROS_MES_FINANCEIRO_CANONICOS)
    if filtros.get("quickPeriod"):
        filtros["periodo_rapido"] = filtros["quickPeriod"]
    if filtros.get("source"):
        filtros["origem"] = filtros["source"]
    return filtros
