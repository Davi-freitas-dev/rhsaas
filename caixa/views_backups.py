import logging
import re
from datetime import datetime
from pathlib import Path

from django.http import FileResponse, Http404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST, require_safe
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .frontend_bridge import legacy_frontend_redirect_required_response
from .permissions import (
    current_schema_name,
    is_tenant_administrator,
    require_api_tenant_administrator,
    require_tenant_administrator,
)
from .selectors_backups import listar_backups_disponiveis, obter_caminho_backup
from .services_backups import criar_backup_banco
from .views_api_auth import IgnoreBodyParser, csrf_protect_drf_view


logger = logging.getLogger(__name__)
_SAFE_LOG_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.-]")


def _sanitize_log_filename(filename):
    filename = Path(str(filename or "")).name[:160]
    return _SAFE_LOG_FILENAME_RE.sub("_", filename)


def _audit_backup_event(request, action, outcome, *, filename=""):
    user = getattr(request, "user", None)
    logger.info(
        "backup_event action=%s outcome=%s schema=%s user_id=%s host=%s filename=%s",
        action,
        outcome,
        current_schema_name(),
        getattr(user, "pk", None),
        request.get_host(),
        _sanitize_log_filename(filename),
    )


@require_tenant_administrator
@require_safe
def backups_lista(request):
    return legacy_frontend_redirect_required_response(request, "backups_lista")


def serializar_backup(arquivo):
    nome = arquivo["nome"]
    criado_em = datetime.fromtimestamp(
        arquivo["criado_em"],
        tz=timezone.get_current_timezone(),
    )

    return {
        "name": nome,
        "nome": nome,
        "sizeMb": round(arquivo["tamanho_mb"], 4),
        "tamanho_mb": arquivo["tamanho_mb"],
        "createdAt": criado_em.isoformat(),
        "criado_em": arquivo["criado_em"],
        "downloadPath": reverse("caixa:backup_download", args=[nome]),
        "scope": arquivo["scope"],
        "schemaName": arquivo["schema_name"],
    }


@never_cache
@require_GET
@extend_schema(responses={200: OpenApiTypes.OBJECT}, auth=[{"cookieAuth": []}])
@api_view(["GET"])
@permission_classes([AllowAny])
def api_backups(request):
    if not request.user.is_authenticated:
        return Response(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )

    if not is_tenant_administrator(request.user):
        _audit_backup_event(request, "list", "denied")
        return Response({"detail": "Permission denied."}, status=403)

    backups = [serializar_backup(arquivo) for arquivo in listar_backups_disponiveis()]
    _audit_backup_event(request, "list", "allowed")
    return Response({"backups": backups})


@csrf_protect_drf_view
@require_api_tenant_administrator
@require_POST
@extend_schema(
    request=None,
    responses={200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT},
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@parser_classes([IgnoreBodyParser])
@permission_classes([AllowAny])
def api_backup_criar_manual(request):
    try:
        resultado = criar_backup_banco(force=True)
    except Exception:
        logger.exception("Falha ao criar backup manual pela API.")
        _audit_backup_event(request, "create", "error")
        return Response(
            {
                "detail": "Nao foi possivel criar o backup manual. Verifique os logs do servidor.",
            },
            status=500,
        )

    backup = None
    if resultado.get("arquivo"):
        backup = next(
            (
                serializar_backup(arquivo)
                for arquivo in listar_backups_disponiveis()
                if arquivo["nome"] == resultado["arquivo"]
            ),
            None,
        )

    _audit_backup_event(
        request,
        "create",
        "created" if resultado["criado"] else "unchanged",
        filename=resultado.get("arquivo") or "",
    )
    return Response(
        {
            "created": bool(resultado["criado"]),
            "criado": bool(resultado["criado"]),
            "message": resultado["mensagem"],
            "mensagem": resultado["mensagem"],
            "removedCount": resultado["removidos"],
            "removidos": resultado["removidos"],
            "backup": backup,
        },
        status=201 if resultado["criado"] else 200,
    )


@require_tenant_administrator
def backup_download(request, nome_arquivo):
    try:
        caminho = obter_caminho_backup(nome_arquivo)
    except Http404:
        _audit_backup_event(request, "download", "denied", filename=nome_arquivo)
        raise

    _audit_backup_event(request, "download", "allowed", filename=nome_arquivo)

    response = FileResponse(
        open(caminho, "rb"),
        as_attachment=True,
        filename=caminho.name,
        content_type="application/json",
    )
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    return response
