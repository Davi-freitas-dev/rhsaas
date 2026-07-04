from .frontend_bridge import legacy_frontend_redirect_required_response
from .permissions import require_permission


@require_permission("caixa.view_custofixo")
def custos_fixos_lista(request):
    return legacy_frontend_redirect_required_response(request, "custos_fixos_lista")
