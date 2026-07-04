from .frontend_bridge import legacy_frontend_redirect_required_response
from .permissions import require_any_permission, require_permission


@require_any_permission(
    "caixa.add_pagamentoparceladivida",
    "caixa.add_pagamentoeventocustoservico",
    "caixa.add_pagamentoeventocustoextra",
)
def pagamentos(request):
    return legacy_frontend_redirect_required_response(request, "pagamentos")


@require_permission("caixa.add_pagamentoeventocustoservico")
def pagamentos_custos_servico(request):
    return legacy_frontend_redirect_required_response(
        request,
        "pagamentos_custos_servico",
    )


@require_permission("caixa.add_pagamentoeventocustoextra")
def pagamentos_custos_extras(request):
    return legacy_frontend_redirect_required_response(
        request,
        "pagamentos_custos_extras",
    )


@require_permission("caixa.add_pagamentoparceladivida")
def pagamentos_fcf(request):
    return legacy_frontend_redirect_required_response(request, "pagamentos_fcf")
