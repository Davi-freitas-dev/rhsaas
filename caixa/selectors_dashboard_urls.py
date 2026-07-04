from urllib.parse import urlencode

from django.urls import reverse


def limpar_classe_css(valor):
    if not valor:
        return ""

    return (
        str(valor)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def montar_url_com_params(nome_rota, params=None):
    url = reverse(nome_rota)
    params_limpos = {
        chave: valor
        for chave, valor in (params or {}).items()
        if valor not in ("", None)
    }

    if not params_limpos:
        return url

    return f"{url}?{urlencode(params_limpos)}"


def params_periodo_dashboard(filtros_dashboard):
    return {
        "data_inicial": filtros_dashboard.get("data_inicial", ""),
        "data_final": filtros_dashboard.get("data_final", ""),
    }


def params_periodo_com_sessao(filtros_dashboard):
    params = params_periodo_dashboard(filtros_dashboard)

    if filtros_dashboard.get("periodo_rapido") == "todos":
        params["periodo_rapido"] = "todos"

    return params


def params_vencidos_dashboard(filtros_dashboard):
    return {
        "periodo_rapido": "vencidos",
        **params_periodo_dashboard(filtros_dashboard),
    }


def params_mes_financeiro_dashboard(filtros_dashboard):
    params = {
        "periodo_rapido": filtros_dashboard.get("periodo_rapido", ""),
        **params_periodo_dashboard(filtros_dashboard),
        "evento": filtros_dashboard.get("evento_id", ""),
        "cliente": filtros_dashboard.get("cliente_id", ""),
        "contrato_codigo": filtros_dashboard.get("contrato_codigo", ""),
        "status": filtros_dashboard.get("status", ""),
    }
    return params


def params_receitas_dashboard(filtros_dashboard):
    params = {
        "periodo_rapido": filtros_dashboard.get("periodo_rapido", ""),
        **params_periodo_dashboard(filtros_dashboard),
        "evento": filtros_dashboard.get("evento_id", ""),
        "cliente": filtros_dashboard.get("cliente_id", ""),
        "contrato_codigo": filtros_dashboard.get("contrato_codigo", ""),
        "status": filtros_dashboard.get("status", ""),
    }
    return params


def params_despesas_pessoal_dashboard(filtros_dashboard):
    return {
        **params_receitas_dashboard(filtros_dashboard),
        "categoria": "mao_obra",
    }
