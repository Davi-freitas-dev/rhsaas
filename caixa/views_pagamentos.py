from .frontend_bridge import legacy_frontend_redirect_required_response


def pagamentos(request):
    return legacy_frontend_redirect_required_response(
        request,
        "pagamentos",
        required_permissions=(
            "caixa.add_pagamentoparceladivida",
            "caixa.add_pagamentoeventocustoservico",
            "caixa.add_pagamentoeventocustoextra",
        ),
        any_permission=True,
    )


def pagamentos_custos_servico(request):
    return legacy_frontend_redirect_required_response(
        request,
        "pagamentos_custos_servico",
        required_permissions="caixa.add_pagamentoeventocustoservico",
    )


def pagamentos_custos_extras(request):
    return legacy_frontend_redirect_required_response(
        request,
        "pagamentos_custos_extras",
        required_permissions="caixa.add_pagamentoeventocustoextra",
    )


def pagamentos_fcf(request):
    return legacy_frontend_redirect_required_response(
        request,
        "pagamentos_fcf",
        required_permissions="caixa.add_pagamentoparceladivida",
    )
