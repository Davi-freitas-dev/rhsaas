from urllib.parse import parse_qsl, urlencode

from django.conf import settings
from django.http import HttpResponseGone, HttpResponseNotAllowed
from django.shortcuts import redirect


DEFAULT_NEXT_FRONTEND_URL = "http://localhost:3000"


LEGACY_FRONTEND_SURFACES = {
    "dashboard_financeiro": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "O dashboard operacional oficial fica no Next.js. A rota Django "
            "foi mantida apenas como redirect tecnico para a interface nova."
        ),
        "path": "/",
        "status": "migrated",
    },
    "clientes_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "O cadastro operacional de clientes ja esta disponivel no "
            "frontend novo. Esta tela Django permanece apenas como legado "
            "transitorio."
        ),
        "path": "/clientes",
        "status": "migrated",
    },
    "orcamentos_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A listagem e operacao de orcamentos ja estao disponiveis no "
            "frontend novo. Esta tela Django permanece apenas como legado "
            "transitorio."
        ),
        "path": "/orcamentos",
        "status": "migrated",
    },
    "orcamento_adicionar": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "O cadastro de orcamentos ja esta disponivel no frontend novo. "
            "Esta tela Django permanece apenas como legado transitorio."
        ),
        "path": "/orcamentos",
        "status": "migrated",
    },
    "eventos_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A listagem operacional de eventos ja esta disponivel no "
            "frontend novo. Esta tela Django permanece apenas como legado "
            "transitorio."
        ),
        "path": "/eventos",
        "status": "migrated",
    },
    "custos_por_evento": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A experiencia principal de custos por evento ja esta disponivel "
            "no frontend novo. A interface operacional Django desta rota foi "
            "removida."
        ),
        "path": "/custos-por-evento",
        "status": "migrated",
    },
    "receitas_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A experiencia principal de receitas ja esta disponivel no "
            "frontend novo. Esta tela Django permanece como fallback legado."
        ),
        "path": "/receitas",
        "status": "migrated",
    },
    "despesas_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A experiencia principal de despesas ja esta disponivel no "
            "frontend novo. Esta tela Django permanece como fallback legado."
        ),
        "path": "/despesas",
        "status": "migrated",
    },
    "custos_fixos_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A experiencia principal de custos fixos ja esta disponivel no "
            "frontend novo. Esta tela Django permanece como fallback legado."
        ),
        "path": "/custos-fixos",
        "status": "migrated",
    },
    "custo_extra_adicionar": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "O cadastro operacional de custos extras ja esta disponivel no "
            "frontend novo. Esta tela Django permanece como fallback legado."
        ),
        "path": "/custos-extras",
        "status": "migrated",
    },
    "pagamentos": {
        "title": "Central migrada para o Next.js",
        "description": (
            "A fila principal de pagamentos ja esta disponivel no frontend "
            "novo. A interface operacional Django desta rota foi removida."
        ),
        "path": "/pagamentos",
        "status": "migrated",
    },
    "pagamentos_custos_servico": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A liquidacao de custos de servico ja esta disponivel na fila "
            "principal do frontend novo. A interface operacional Django "
            "desta rota foi removida."
        ),
        "path": "/pagamentos",
        "query": {"source": "custo_servico"},
        "status": "migrated",
    },
    "pagamentos_custos_extras": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A liquidacao de custos extras ja esta disponivel na fila "
            "principal do frontend novo. A interface operacional Django "
            "desta rota foi removida."
        ),
        "path": "/pagamentos",
        "query": {"source": "custo_extra"},
        "status": "migrated",
    },
    "pagamentos_fcf": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A liquidacao de parcelas FCF ja esta disponivel na fila "
            "principal do frontend novo. A interface operacional Django "
            "desta rota foi removida."
        ),
        "path": "/pagamentos",
        "query": {"source": "parcela_divida"},
        "status": "migrated",
    },
    "pagar_parcela": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "O pagamento de parcelas FCF ja esta disponivel na fila principal "
            "do frontend novo. A interface operacional Django desta rota foi "
            "removida."
        ),
        "path": "/pagamentos",
        "query": {"source": "parcela_divida"},
        "routeArgs": [1],
        "status": "migrated",
    },
    "lista_investimentos": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A experiencia principal de FCI ja esta disponivel no frontend "
            "novo. A interface operacional Django desta rota foi removida."
        ),
        "path": "/fci",
        "status": "migrated",
    },
    "lista_financiamentos": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A experiencia principal de FCF ja esta disponivel no frontend "
            "novo. A interface operacional Django desta rota foi removida."
        ),
        "path": "/fcf",
        "status": "migrated",
    },
    "backups_lista": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "A gestao de backups ja esta disponivel no frontend novo. Esta "
            "tela Django permanece como fallback legado restrito ao admin."
        ),
        "path": "/backups",
        "status": "migrated",
    },
    "mes_financeiro": {
        "title": "Tela migrada para o Next.js",
        "description": (
            "O mes financeiro operacional foi retirado do HTML Django. "
            "O fluxo visual fica no Next.js e a API de mes permanece "
            "disponivel como read-model backend."
        ),
        "path": "/obrigacoes-financeiras",
        "status": "migrated",
    },
}


SAFE_REDIRECT_METHODS = {"GET", "HEAD"}


def next_frontend_base_url():
    configured_url = getattr(settings, "NEXT_FRONTEND_URL", "")
    if configured_url:
        return configured_url.rstrip("/")
    if getattr(settings, "DEBUG", False):
        return DEFAULT_NEXT_FRONTEND_URL
    return ""


def build_next_frontend_url(path):
    base_url = next_frontend_base_url()
    if not base_url:
        return ""
    path = "/" + str(path or "").lstrip("/")
    return f"{base_url}{path}"


def surface_query_string(surface, query_string="", extra_query=None):
    query = {
        chave: valor
        for chave, valor in (surface.get("query") or {}).items()
        if valor not in (None, "")
    }
    query.update(
        {
            chave: valor
            for chave, valor in (extra_query or {}).items()
            if valor not in (None, "")
        }
    )
    if query_string:
        for chave, valor in parse_qsl(query_string, keep_blank_values=True):
            if valor != "" and chave not in query:
                query[chave] = valor
    return urlencode(query)


def build_next_frontend_url_for_surface(surface_key, query_string="", extra_query=None):
    surface = LEGACY_FRONTEND_SURFACES[surface_key]
    url = build_next_frontend_url(surface["path"])
    query = surface_query_string(surface, query_string, extra_query)
    if query and url:
        return f"{url}?{query}"
    return url


def frontend_migration_context(surface_key, extra_query=None):
    surface = LEGACY_FRONTEND_SURFACES[surface_key]
    return {
        "frontend_migration": {
            "title": surface["title"],
            "description": surface["description"],
            "status": surface["status"],
            "url": build_next_frontend_url_for_surface(
                surface_key,
                extra_query=extra_query,
            ),
        }
    }


def legacy_frontend_redirect_response(request, surface_key, extra_query=None):
    if request.method not in SAFE_REDIRECT_METHODS:
        return None
    if not getattr(settings, "NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED", False):
        return None

    allowed_surfaces = set(
        getattr(settings, "NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES", [])
    )
    if surface_key not in allowed_surfaces:
        return None

    surface = LEGACY_FRONTEND_SURFACES[surface_key]
    if surface.get("status") != "migrated":
        return None

    url = build_next_frontend_url_for_surface(
        surface_key,
        request.META.get("QUERY_STRING", ""),
        extra_query=extra_query,
    )
    if not url:
        return None

    return redirect(url)


def legacy_frontend_redirect_required_response(request, surface_key, extra_query=None):
    if request.method not in SAFE_REDIRECT_METHODS:
        return HttpResponseNotAllowed(sorted(SAFE_REDIRECT_METHODS))

    url = build_next_frontend_url_for_surface(
        surface_key,
        request.META.get("QUERY_STRING", ""),
        extra_query=extra_query,
    )
    if url:
        return redirect(url)

    surface = LEGACY_FRONTEND_SURFACES[surface_key]
    return HttpResponseGone(
        (
            f"{surface['title']}. A interface operacional Django desta rota "
            "foi removida; use o frontend Next.js."
        ),
        content_type="text/plain; charset=utf-8",
    )
