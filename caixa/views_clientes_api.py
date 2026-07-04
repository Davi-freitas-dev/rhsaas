import json

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.defaults import page_not_found
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.authentication import CSRFCheck, SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import ParseError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Cliente
from .permissions import (
    ADD_CLIENT_PERMISSION,
    CHANGE_CLIENT_PERMISSION,
    VIEW_CLIENT_PERMISSION,
    api_authentication_required_response,
    api_no_store_json_response,
    api_permission_denied_response,
)
from .selectors_cadastros import filtrar_clientes


class JsonBodySafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        def dummy_get_response(request):
            return None

        django_request = request._request
        check = CSRFCheck(dummy_get_response)
        check.process_request(django_request)
        reason = check.process_view(django_request, None, (), {})
        if reason:
            raise PermissionDenied(f"CSRF Failed: {reason}")


def _is_json_request(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip()
    return content_type == "application/json"


def _payload_json(request):
    if isinstance(request, Request):
        try:
            payload = request.data
        except ParseError:
            return None

        return payload if isinstance(payload, dict) else None

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    return payload if isinstance(payload, dict) else None


def _first_payload_value(payload, *keys, default=""):
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return default


def _string_payload_value(payload, *keys, default=""):
    value = _first_payload_value(payload, *keys, default=default)
    return str(value).strip() if value is not None else ""


def _boolean_payload_value(payload, *keys, default=True):
    value = _first_payload_value(payload, *keys, default=default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "nao", "não", "no"}

    return bool(value)


def _datetime_or_empty(value):
    return value.isoformat() if value else ""


def _errors_from_validation_error(error):
    if hasattr(error, "message_dict"):
        return error.message_dict

    return {"detail": error.messages}


def _serialize_cliente(cliente):
    return {
        "id": cliente.id,
        "name": cliente.nome_razao_social,
        "tradeName": cliente.nome_fantasia,
        "personType": cliente.tipo_pessoa,
        "personTypeLabel": cliente.get_tipo_pessoa_display(),
        "document": cliente.cpf_cnpj,
        "phone": cliente.telefone,
        "email": cliente.email,
        "responsible": cliente.responsavel,
        "address": cliente.endereco,
        "notes": cliente.observacoes,
        "isActive": cliente.ativo,
        "displayName": str(cliente),
        "createdAt": _datetime_or_empty(cliente.criado_em),
        "updatedAt": _datetime_or_empty(cliente.atualizado_em),
    }


def _cliente_data_from_payload(payload):
    return {
        "nome_razao_social": _string_payload_value(
            payload,
            "name",
            "nome_razao_social",
            "nomeRazaoSocial",
        ),
        "nome_fantasia": _string_payload_value(payload, "tradeName", "nome_fantasia"),
        "tipo_pessoa": _string_payload_value(payload, "personType", "tipo_pessoa") or "PJ",
        "cpf_cnpj": _string_payload_value(payload, "document", "cpf_cnpj", "cpfCnpj"),
        "telefone": _string_payload_value(payload, "phone", "telefone"),
        "email": _string_payload_value(payload, "email"),
        "responsavel": _string_payload_value(payload, "responsible", "responsavel"),
        "endereco": _string_payload_value(payload, "address", "endereco"),
        "observacoes": _string_payload_value(payload, "notes", "observacoes"),
        "ativo": _boolean_payload_value(payload, "isActive", "ativo", default=True),
    }


def _clientes_response(request):
    filtros = {
        "busca": (request.GET.get("search") or request.GET.get("busca", "")).strip(),
        "tipo_pessoa": (
            request.GET.get("personType") or request.GET.get("tipo_pessoa", "")
        ).strip(),
        "ativo": (request.GET.get("active") or request.GET.get("ativo", "")).strip(),
    }
    clientes = filtrar_clientes(**filtros)
    filters_payload = {
        **filtros,
        "search": filtros["busca"],
        "personType": filtros["tipo_pessoa"],
        "active": filtros["ativo"],
    }

    return api_no_store_json_response(
        {
            "data": {
                "clients": [_serialize_cliente(cliente) for cliente in clientes],
                "summary": {
                    "total": clientes.count(),
                    "active": clientes.filter(ativo=True).count(),
                    "inactive": clientes.filter(ativo=False).count(),
                    "legalPersons": clientes.filter(tipo_pessoa="PJ").count(),
                    "naturalPersons": clientes.filter(tipo_pessoa="PF").count(),
                },
                "filters": filters_payload,
                "filterOptions": {
                    "personTypes": [
                        {"value": value, "label": label}
                        for value, label in Cliente.TIPO_PESSOA_CHOICES
                    ],
                    "activeStatuses": [
                        {"value": "sim", "label": "Ativo"},
                        {"value": "nao", "label": "Inativo"},
                    ],
                },
                "permissions": {
                    "canCreate": request.user.has_perm(ADD_CLIENT_PERMISSION),
                    "canUpdate": request.user.has_perm(CHANGE_CLIENT_PERMISSION),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _criar_cliente_response(request):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    cliente = Cliente(**_cliente_data_from_payload(payload))

    try:
        cliente.full_clean()
        cliente.save()
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"cpf_cnpj": ["Ja existe um cliente com este CPF/CNPJ."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "client": _serialize_cliente(cliente),
                "message": "Cliente cadastrado com sucesso.",
            }
        },
        status=201,
        json_dumps_params={"ensure_ascii": False},
    )


def _cliente_detalhe_response(request, cliente):
    return api_no_store_json_response(
        {
            "data": {
                "client": _serialize_cliente(cliente),
                "permissions": {
                    "canUpdate": request.user.has_perm(CHANGE_CLIENT_PERMISSION),
                },
                "meta": {"source": "backend"},
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _atualizar_cliente_response(request, cliente):
    if not _is_json_request(request):
        return api_no_store_json_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )

    payload = _payload_json(request)
    if payload is None:
        return api_no_store_json_response({"detail": "JSON invalido."}, status=400)

    for field, value in _cliente_data_from_payload(payload).items():
        setattr(cliente, field, value)

    try:
        cliente.full_clean()
        cliente.save()
    except ValidationError as error:
        return api_no_store_json_response(
            {"errors": _errors_from_validation_error(error)},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )
    except IntegrityError:
        return api_no_store_json_response(
            {"errors": {"cpf_cnpj": ["Ja existe um cliente com este CPF/CNPJ."]}},
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    return api_no_store_json_response(
        {
            "data": {
                "client": _serialize_cliente(cliente),
                "message": "Cliente atualizado com sucesso.",
            }
        },
        json_dumps_params={"ensure_ascii": False},
    )


@never_cache
@extend_schema(methods=["GET"], responses=OpenApiTypes.OBJECT, auth=[{"cookieAuth": []}])
@extend_schema(
    methods=["POST"],
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_clientes(request):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        return Response(payload, status=response.status_code)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_CLIENT_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        return drf_response_from_json_response(_clientes_response(request))

    if not request.user.has_perm(ADD_CLIENT_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    return drf_response_from_json_response(_criar_cliente_response(request))


@extend_schema(
    methods=["GET"],
    operation_id="clientes_detalhe_retrieve",
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="clientes_detalhe_update",
    request=OpenApiTypes.OBJECT,
    responses=OpenApiTypes.OBJECT,
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_cliente_detalhe(request, pk):
    def drf_response_from_json_response(response):
        payload = json.loads(response.content.decode(response.charset or "utf-8"))
        drf_response = Response(payload, status=response.status_code)
        for header_name in ("Cache-Control", "Expires"):
            if header_name in response:
                drf_response[header_name] = response[header_name]
        return drf_response

    def django_not_found_response():
        django_request = request._request if isinstance(request, Request) else request
        exception = Http404("No Cliente matches the given query.")
        return page_not_found(django_request, exception)

    if not request.user.is_authenticated:
        return drf_response_from_json_response(api_authentication_required_response())

    if request.method == "GET":
        if not request.user.has_perm(VIEW_CLIENT_PERMISSION):
            return drf_response_from_json_response(api_permission_denied_response())

        try:
            cliente = get_object_or_404(Cliente, pk=pk)
        except Http404:
            return django_not_found_response()

        return drf_response_from_json_response(_cliente_detalhe_response(request, cliente))

    if not request.user.has_perm(CHANGE_CLIENT_PERMISSION):
        return drf_response_from_json_response(api_permission_denied_response())

    try:
        cliente = get_object_or_404(Cliente, pk=pk)
    except Http404:
        return django_not_found_response()

    return drf_response_from_json_response(_atualizar_cliente_response(request, cliente))
