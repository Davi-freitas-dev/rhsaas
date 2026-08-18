from django.views.decorators.http import require_safe

from .frontend_bridge import (
    legacy_frontend_redirect_required_response,
)
def clientes_lista(request):
    return legacy_frontend_redirect_required_response(
        request,
        "clientes_lista",
        required_permissions="caixa.view_cliente",
    )


def orcamentos_lista(request):
    return legacy_frontend_redirect_required_response(
        request,
        "orcamentos_lista",
        required_permissions="caixa.view_orcamento",
    )


@require_safe
def orcamento_adicionar(request):
    return legacy_frontend_redirect_required_response(
        request,
        "orcamento_adicionar",
        required_permissions=("caixa.add_orcamento", "caixa.add_orcamentoitem"),
    )


def eventos_lista(request):
    return legacy_frontend_redirect_required_response(
        request,
        "eventos_lista",
        required_permissions="caixa.view_evento",
    )


@require_safe
def custo_extra_adicionar(request):
    return legacy_frontend_redirect_required_response(
        request,
        "custo_extra_adicionar",
        required_permissions=(
            "caixa.add_eventocustoextra",
            "caixa.view_eventocustoextra",
        ),
        any_permission=True,
    )


def receitas_lista(request):
    return legacy_frontend_redirect_required_response(
        request,
        "receitas_lista",
        required_permissions="caixa.view_receitaoperacional",
    )


def despesas_lista(request):
    return legacy_frontend_redirect_required_response(
        request,
        "despesas_lista",
        required_permissions="caixa.view_despesaoperacional",
    )
