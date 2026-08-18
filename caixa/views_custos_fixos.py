from .frontend_bridge import legacy_frontend_redirect_required_response


def custos_fixos_lista(request):
    return legacy_frontend_redirect_required_response(
        request,
        "custos_fixos_lista",
        required_permissions="caixa.view_custofixo",
    )
