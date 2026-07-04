import json

from django.views.decorators.http import require_GET
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .permissions import (
    FINANCIAL_LEDGER_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .serializers_modelagem_canonica import (
    montar_payload_baixas_financeiras_canonicas_api,
    montar_payload_modelagem_financeira_canonica_api,
)


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_modelagem_financeira_canonica(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(FINANCIAL_LEDGER_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    payload = montar_payload_modelagem_financeira_canonica_api(request.GET)
    return drf_response_from_json_response(
        api_no_store_json_response(
            payload,
            json_dumps_params={"ensure_ascii": False},
        )
    )


@require_GET
@extend_schema(responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_baixas_financeiras_canonicas(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if not request.user.has_perm(FINANCIAL_LEDGER_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    payload = montar_payload_baixas_financeiras_canonicas_api(request.GET)
    return drf_response_from_json_response(
        api_no_store_json_response(
            payload,
            json_dumps_params={"ensure_ascii": False},
        )
    )
