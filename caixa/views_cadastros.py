from django.views.decorators.http import require_safe

from .frontend_bridge import (
    legacy_frontend_redirect_required_response,
)
from .permissions import require_any_permission, require_permission


@require_permission("caixa.view_cliente")
def clientes_lista(request):
    return legacy_frontend_redirect_required_response(request, "clientes_lista")


@require_permission("caixa.view_orcamento")
def orcamentos_lista(request):
    return legacy_frontend_redirect_required_response(request, "orcamentos_lista")


@require_permission(["caixa.add_orcamento", "caixa.add_orcamentoitem"])
@require_safe
def orcamento_adicionar(request):
    return legacy_frontend_redirect_required_response(request, "orcamento_adicionar")


@require_permission("caixa.view_evento")
def eventos_lista(request):
    return legacy_frontend_redirect_required_response(request, "eventos_lista")


@require_any_permission("caixa.add_eventocustoextra", "caixa.view_eventocustoextra")
@require_safe
def custo_extra_adicionar(request):
    return legacy_frontend_redirect_required_response(request, "custo_extra_adicionar")


@require_permission("caixa.view_receitaoperacional")
def receitas_lista(request):
    return legacy_frontend_redirect_required_response(request, "receitas_lista")


@require_permission("caixa.view_despesaoperacional")
def despesas_lista(request):
    return legacy_frontend_redirect_required_response(request, "despesas_lista")
