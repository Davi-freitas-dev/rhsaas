import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from caixa.frontend_bridge import (
    LEGACY_FRONTEND_SURFACES,
    build_next_frontend_url_for_surface,
)


DEFAULT_OUTPUT_JSON = "pm06-inventario-html-django.json"
DEFAULT_OUTPUT_RECORD = "pm06-inventario-html-django.md"


OPERATIONAL_HTML_SURFACES = []


REMOVED_OPERATIONAL_HTML_SURFACES = [
    {
        "surface": "dashboard_financeiro",
        "djangoUrl": "/",
        "template": "caixa/dashboard.html",
        "nextPath": "/",
        "removalRisk": "medium",
        "removedIn": "PM-06.1325",
        "reason": "Template HTML removido; dashboard operacional fica no Next.js/API, com filtros, totais, alertas e agregacoes preservados em selectors/serializers.",
    },
    {
        "surface": "mes_financeiro",
        "djangoUrl": "/mes-financeiro/",
        "template": "caixa/mes_financeiro.html",
        "nextPath": "/obrigacoes-financeiras",
        "removalRisk": "high",
        "removedIn": "PM-06.1326",
        "reason": "Template HTML removido; mes financeiro operacional fica no Next.js/Obrigacoes, enquanto api_mes_financeiro e selectors preservam filtros, totais, fluxo e caixa disponivel.",
    },
    {
        "surface": "clientes_lista",
        "djangoUrl": "/clientes/",
        "template": "caixa/clientes.html",
        "nextPath": "/clientes",
        "removalRisk": "low",
        "removedIn": "PM-06.1316",
        "reason": "Template HTML removido; rota legada redireciona obrigatoriamente para Next.js.",
    },
    {
        "surface": "orcamentos_lista",
        "djangoUrl": "/orcamentos/",
        "template": "caixa/orcamentos.html",
        "nextPath": "/orcamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1316",
        "reason": "Template HTML removido; listagem/edicao/aprovacao ficam no Next.js e APIs JSON.",
    },
    {
        "surface": "orcamento_adicionar",
        "djangoUrl": "/orcamentos/adicionar/",
        "template": "caixa/orcamento_adicionar.html",
        "nextPath": "/orcamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1316",
        "reason": "Template HTML removido; cadastro de orcamento fica no Next.js e API de orcamentos.",
    },
    {
        "surface": "eventos_lista",
        "djangoUrl": "/eventos/",
        "template": "caixa/eventos.html",
        "nextPath": "/eventos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1316",
        "reason": "Template HTML removido; listagem operacional de eventos fica no Next.js e API de eventos.",
    },
    {
        "surface": "backups_lista",
        "djangoUrl": "/backups/",
        "template": "caixa/backups.html",
        "nextPath": "/backups",
        "removalRisk": "low",
        "removedIn": "PM-06.1317",
        "reason": "Template HTML removido; listagem e geracao manual ficam no Next.js/API, download tecnico permanece.",
    },
    {
        "surface": "receitas_lista",
        "djangoUrl": "/receitas/",
        "template": "caixa/receitas.html",
        "nextPath": "/receitas",
        "removalRisk": "medium",
        "removedIn": "PM-06.1318",
        "reason": "Template HTML removido; leitura operacional fica no Next.js/API canonica de obrigacoes e edicao em API dedicada.",
    },
    {
        "surface": "despesas_lista",
        "djangoUrl": "/despesas/",
        "template": "caixa/despesas.html",
        "nextPath": "/despesas",
        "removalRisk": "medium",
        "removedIn": "PM-06.1318",
        "reason": "Template HTML removido; leitura operacional fica no Next.js/API canonica de obrigacoes e edicao em API dedicada.",
    },
    {
        "surface": "custo_extra_adicionar",
        "djangoUrl": "/eventos/custos-extras/adicionar/",
        "template": "caixa/custo_extra_adicionar.html",
        "nextPath": "/custos-extras",
        "removalRisk": "medium",
        "removedIn": "PM-06.1319",
        "reason": "Template HTML removido; cadastro/listagem operacional fica no Next.js/API de custos extras, com filtros preservados em selector.",
    },
    {
        "surface": "custos_fixos_lista",
        "djangoUrl": "/custos-fixos/",
        "template": "caixa/custos_fixos.html",
        "nextPath": "/custos-fixos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1320",
        "reason": "Template HTML removido; leitura e escrita operacional ficam no Next.js/API de custos fixos, com filtros/totais preservados em selector.",
    },
    {
        "surface": "custos_por_evento",
        "djangoUrl": "/custos-por-evento/",
        "template": "caixa/custos_por_evento.html",
        "nextPath": "/custos-por-evento",
        "removalRisk": "medium",
        "removedIn": "PM-06.1321",
        "reason": "Template HTML removido; leitura operacional fica no Next.js/API de custos por evento, com agrupamentos, filtros e totais preservados em selector.",
    },
    {
        "surface": "lista_investimentos",
        "djangoUrl": "/fci/",
        "template": "caixa/fci.html",
        "nextPath": "/fci",
        "removalRisk": "medium",
        "removedIn": "PM-06.1322",
        "reason": "Template HTML removido; leitura operacional FCI fica no Next.js/API de investimentos, com filtros, grupos, totais e performance preservados em selector.",
    },
    {
        "surface": "lista_financiamentos",
        "djangoUrl": "/fcf/",
        "template": "caixa/fcf.html",
        "nextPath": "/fcf",
        "removalRisk": "medium",
        "removedIn": "PM-06.1323",
        "reason": "Template HTML removido; leitura operacional FCF fica no Next.js/API de financiamentos, com parcelas, movimentacoes, filtros, grupos e totais preservados em selector.",
    },
    {
        "surface": "pagamentos",
        "djangoUrl": "/pagamentos/",
        "template": "caixa/pagamentos.html",
        "nextPath": "/pagamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1324",
        "reason": "Template HTML removido; fila e baixa operacional ficam no Next.js/API canonica de obrigacoes, com filtros, permissoes e regras de liquidacao preservados em selectors/services.",
    },
    {
        "surface": "pagamentos_custos_servico",
        "djangoUrl": "/eventos/custos-servico/pagamentos/",
        "template": "caixa/pagamentos_custos_servico.html",
        "nextPath": "/pagamentos?source=custo_servico",
        "removalRisk": "medium",
        "removedIn": "PM-06.1324",
        "reason": "Template HTML removido; baixa de custos de servico fica na fila de pagamentos Next.js e na API canonica de liquidacao, preservando regra em selectors/services.",
    },
    {
        "surface": "pagamentos_custos_extras",
        "djangoUrl": "/eventos/custos-extras/pagamentos/",
        "template": "caixa/pagamentos_custos_extras.html",
        "nextPath": "/pagamentos?source=custo_extra",
        "removalRisk": "medium",
        "removedIn": "PM-06.1324",
        "reason": "Template HTML removido; baixa de custos extras fica na fila de pagamentos Next.js e na API canonica de liquidacao, preservando regra em selectors/services.",
    },
    {
        "surface": "pagamentos_fcf",
        "djangoUrl": "/fcf/pagamentos/",
        "template": "caixa/pagamentos_fcf.html",
        "nextPath": "/pagamentos?source=parcela_divida",
        "removalRisk": "medium",
        "removedIn": "PM-06.1324",
        "reason": "Template HTML removido; baixa de parcelas FCF fica na fila de pagamentos Next.js e na API canonica de liquidacao, preservando regras FCF nos services.",
    },
    {
        "surface": "pagar_parcela",
        "djangoUrl": "/fcf/parcelas/<id>/pagar/",
        "template": "caixa/pagar_parcela.html",
        "nextPath": "/pagamentos?source=parcela_divida",
        "removalRisk": "medium",
        "removedIn": "PM-06.1324",
        "reason": "Template HTML removido; rota preserva sourceId e redireciona para a fila Next.js, enquanto a baixa ocorre somente pela API canonica.",
    },
]


LEGACY_POST_ROUTES = []


REMOVED_LEGACY_POST_ROUTES = [
    {
        "routeName": "aprovar_orcamento",
        "djangoUrl": "/orcamentos/<id>/aprovar/",
        "nextApi": "api_aprovar_orcamento",
        "nextPath": "/orcamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1314",
        "reason": "Aprovacao operacional usa apenas POST /api/orcamentos/<id>/aprovar/ no Next.js.",
    },
    {
        "routeName": "backup_criar_manual",
        "djangoUrl": "/backups/criar/",
        "nextApi": "api_backup_criar_manual",
        "nextPath": "/backups",
        "removalRisk": "low",
        "removedIn": "PM-06.1314",
        "reason": "Geracao manual de backup usa apenas POST /api/backups/criar/ no Next.js.",
    },
]


INLINE_LEGACY_POST_SURFACES = []


REMOVED_INLINE_LEGACY_POST_SURFACES = [
    {
        "surface": "orcamento_adicionar",
        "djangoUrl": "/orcamentos/adicionar/",
        "nextApi": "api_orcamentos",
        "nextPath": "/orcamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1315",
        "reason": "Cadastro HTML de orcamento deixou de aceitar POST; Next.js usa API de orcamentos.",
    },
    {
        "surface": "custo_extra_adicionar",
        "djangoUrl": "/eventos/custos-extras/adicionar/",
        "nextApi": "api_criar_custo_extra_evento",
        "nextPath": "/custos-extras",
        "removalRisk": "medium",
        "removedIn": "PM-06.1315",
        "reason": "Cadastro HTML de custo extra deixou de aceitar POST; Next.js usa API dedicada.",
    },
    {
        "surface": "pagamentos_custos_servico",
        "djangoUrl": "/eventos/custos-servico/pagamentos/",
        "nextApi": "api_liquidar_obrigacao_financeira",
        "nextPath": "/pagamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1315",
        "reason": "Baixa HTML de custo de servico deixou de aceitar POST; Next.js usa liquidacao canonica.",
    },
    {
        "surface": "pagamentos_custos_extras",
        "djangoUrl": "/eventos/custos-extras/pagamentos/",
        "nextApi": "api_liquidar_obrigacao_financeira",
        "nextPath": "/pagamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1315",
        "reason": "Baixa HTML de custo extra deixou de aceitar POST; Next.js usa liquidacao canonica.",
    },
    {
        "surface": "pagar_parcela",
        "djangoUrl": "/fcf/parcelas/<id>/pagar/",
        "nextApi": "api_liquidar_obrigacao_financeira",
        "nextPath": "/pagamentos",
        "removalRisk": "medium",
        "removedIn": "PM-06.1315",
        "reason": "Baixa HTML de parcela FCF deixou de aceitar POST; Next.js usa liquidacao canonica.",
    },
]


PRESERVED_HTML_SUPPORT = [
    {
        "routeName": "login",
        "template": "caixa/login.html",
        "classification": "auth_support",
        "decision": "preserve",
    },
    {
        "routeName": "password_reset",
        "template": "caixa/password_reset_form.html",
        "classification": "auth_support",
        "decision": "preserve",
    },
    {
        "routeName": "password_reset_done",
        "template": "caixa/password_reset_done.html",
        "classification": "auth_support",
        "decision": "preserve",
    },
    {
        "routeName": "password_reset_confirm",
        "template": "caixa/password_reset_confirm.html",
        "classification": "auth_support",
        "decision": "preserve",
    },
    {
        "routeName": "password_reset_complete",
        "template": "caixa/password_reset_complete.html",
        "classification": "auth_support",
        "decision": "preserve",
    },
    {
        "routeName": "permission_denied",
        "template": "caixa/403.html",
        "classification": "auth_error_support",
        "decision": "preserve",
    },
    {
        "routeName": "backup_download",
        "template": "",
        "classification": "technical_download",
        "decision": "preserve",
    },
]


REMOVED_OPERATIONAL_SHELL_TEMPLATES = [
    {
        "template": "caixa/base.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Shell base usado apenas por telas operacionais Django removidas; auth usa layouts/auth.html.",
    },
    {
        "template": "caixa/shared/_app_header.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Cabecalho operacional Django removido junto com o shell base legado.",
    },
    {
        "template": "caixa/shared/_app_nav.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Navegacao operacional Django removida; Next.js e a unica interface operacional.",
    },
    {
        "template": "caixa/shared/_frontend_migration_notice.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Aviso de migracao perdeu funcao depois que nao restou HTML operacional.",
    },
    {
        "template": "caixa/shared/_empty_table_row.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Parcial de tabela usado apenas por listagens HTML operacionais removidas.",
    },
    {
        "template": "caixa/shared/_page_title.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Parcial visual usado apenas por paginas operacionais Django removidas.",
    },
    {
        "template": "caixa/shared/_messages.html",
        "classification": "legacy_operational_shell",
        "removedIn": "PM-06.1327",
        "reason": "Mensagens do shell operacional antigo removidas; auth preserva layout proprio.",
    },
]


REMOVED_FORMS_INVENTORY = [
    {
        "module": "forms_orcamentos.py",
        "classification": "legacy_operational_html",
        "decision": "removed",
        "removedIn": "PM-06.1328",
        "reason": "Form usado apenas pela tela HTML antiga de orcamentos; API de orcamentos usa parser/serializer proprio.",
    },
]


REMOVED_OPERATIONAL_ASSETS = [
    {
        "asset": "caixa/css/base.css",
        "classification": "legacy_operational_shell_asset",
        "removedIn": "PM-06.1329",
        "reason": "CSS do shell base operacional Django removido em PM-06.1327.",
    },
    {
        "asset": "caixa/css/dashboard.css",
        "classification": "legacy_operational_template_asset",
        "removedIn": "PM-06.1329",
        "reason": "CSS das telas operacionais Django removidas; Next.js assume a UI operacional.",
    },
    {
        "asset": "caixa/js/menu.js",
        "classification": "legacy_operational_shell_asset",
        "removedIn": "PM-06.1329",
        "reason": "Script do menu operacional Django removido junto com o shell visual antigo.",
    },
]


FORMS_INVENTORY = [
    {
        "module": "forms_custos_extras.py",
        "classification": "api_shared_form",
        "decision": "preserve_until_api_serializer_replaces_form",
        "reason": "API de custos extras ainda reutiliza EventoCustoExtraForm para validacao.",
    },
    {
        "module": "forms_pagamentos.py",
        "classification": "admin_and_service_form",
        "decision": "preserve",
        "reason": "Usado por Admin, services e testes de baixa de pagamentos.",
    },
    {
        "module": "forms_dividas.py",
        "classification": "admin_and_service_form",
        "decision": "preserve",
        "reason": "Usado por Admin, services e testes de FCF/dividas.",
    },
    {
        "module": "utils_forms.py",
        "classification": "service_helper",
        "decision": "preserve",
        "reason": "Usado por services de pagamentos/dividas para erros de validacao.",
    },
]


def inventariar_html_django_pm06(options=None):
    options = options or {}
    operational = [_serializar_surface(surface) for surface in OPERATIONAL_HTML_SURFACES]
    removed_operational = [
        _serializar_removed_operational_surface(surface)
        for surface in REMOVED_OPERATIONAL_HTML_SURFACES
    ]
    post_routes = [_serializar_post_route(route) for route in LEGACY_POST_ROUTES]
    removed_post_routes = [
        _serializar_removed_post_route(route)
        for route in REMOVED_LEGACY_POST_ROUTES
    ]
    inline_post_surfaces = [
        _serializar_inline_post_surface(surface)
        for surface in INLINE_LEGACY_POST_SURFACES
    ]
    removed_inline_post_surfaces = [
        _serializar_removed_inline_post_surface(surface)
        for surface in REMOVED_INLINE_LEGACY_POST_SURFACES
    ]
    support = [_serializar_support_route(route) for route in PRESERVED_HTML_SUPPORT]
    removed_shell_templates = list(REMOVED_OPERATIONAL_SHELL_TEMPLATES)
    issues = _issues_inventario(operational)
    risks = _riscos_inventario(operational, post_routes, inline_post_surfaces)
    removal_candidates = [
        surface for surface in operational if surface["removalCandidate"]
    ]
    removal_blocked = [
        surface for surface in operational if not surface["removalCandidate"]
    ]

    resultado = {
        "source": "pm06_django_html_inventory",
        "step": "PM-06.1329",
        "readOnly": True,
        "ready": not issues,
        "generatedAt": timezone.now().isoformat(),
        "architectureDecision": {
            "djangoOperationalHtml": "remove_after_surface_validation",
            "djangoOperationalShell": "removed_when_unused_by_auth_or_admin",
            "djangoAdmin": "preserve",
            "djangoApis": "preserve",
            "nextOperationalUi": "single_operational_interface",
            "databasePremise": "clean_database_manual_reentry",
        },
        "summary": {
            "operationalHtmlCount": len(operational),
            "removedOperationalHtmlCount": len(removed_operational),
            "coveredByNextCount": sum(
                1 for surface in operational if surface["nextCoverage"] == "covered"
            ),
            "partialCoverageCount": sum(
                1 for surface in operational if surface["nextCoverage"] == "partial"
            ),
            "removalCandidateCount": len(removal_candidates),
            "removalBlockedCount": len(removal_blocked),
            "legacyPostRouteCount": len(post_routes),
            "removedLegacyPostRouteCount": len(removed_post_routes),
            "inlineLegacyPostSurfaceCount": len(inline_post_surfaces),
            "removedInlineLegacyPostSurfaceCount": len(removed_inline_post_surfaces),
            "preservedSupportHtmlCount": len(support),
            "removedOperationalShellTemplateCount": len(removed_shell_templates),
            "removedLegacyFormCount": len(REMOVED_FORMS_INVENTORY),
            "removedOperationalAssetCount": len(REMOVED_OPERATIONAL_ASSETS),
        },
        "operationalHtml": operational,
        "removedOperationalHtml": removed_operational,
        "legacyPostRoutes": post_routes,
        "removedLegacyPostRoutes": removed_post_routes,
        "inlineLegacyPostSurfaces": inline_post_surfaces,
        "removedInlineLegacyPostSurfaces": removed_inline_post_surfaces,
        "preservedHtmlSupport": support,
        "removedOperationalShellTemplates": removed_shell_templates,
        "formsInventory": FORMS_INVENTORY,
        "removedFormsInventory": REMOVED_FORMS_INVENTORY,
        "removedOperationalAssets": REMOVED_OPERATIONAL_ASSETS,
        "risks": risks,
        "issues": issues,
        "recommendedNextSteps": [
            "Validar redirects por superficie com validar_redirects_next_legado.",
            "Preservar Admin, APIs, auth, permissao, services, comandos e auditoria.",
            "Manter escritas operacionais em API JSON; nao recriar POST HTML Django.",
            "Mover validacao compartilhada de forms para serializers/services antes de remover forms usados por API.",
            "Manter API/selector de mes financeiro como read-model backend enquanto houver consumidor ou auditoria.",
            "Revisar forms remanescentes e remover apenas quando serializers/services equivalentes estiverem confirmados.",
        ],
    }
    resultado["executionRecord"] = {
        "format": "markdown",
        "markdown": _registro_inventario(resultado),
    }
    return resultado


def _serializar_surface(surface):
    surface_key = surface["surface"]
    bridge = LEGACY_FRONTEND_SURFACES.get(surface_key) or {}
    django_url = _reverse_surface(surface_key, bridge.get("routeArgs", []))
    next_url = build_next_frontend_url_for_surface(surface_key) if bridge else ""
    next_path = bridge.get("path") or ""
    status = bridge.get("status") or "missing"
    next_coverage = surface["nextCoverage"]

    return {
        "surface": surface_key,
        "djangoUrl": django_url,
        "template": surface["template"],
        "bridgeRegistered": bool(bridge),
        "bridgeStatus": status,
        "nextPath": next_path,
        "nextUrl": next_url,
        "nextCoverage": next_coverage,
        "redirectEligible": status == "migrated" and bool(bridge),
        "removalCandidate": next_coverage == "covered" and status == "migrated",
        "removalRisk": surface["removalRisk"],
        "reason": surface["reason"],
    }


def _serializar_removed_operational_surface(surface):
    surface_key = surface["surface"]
    bridge = LEGACY_FRONTEND_SURFACES.get(surface_key) or {}
    return {
        **surface,
        "classification": "legacy_operational_html",
        "decision": "redirect_only_no_html",
        "bridgeRegistered": bool(bridge),
        "bridgeStatus": bridge.get("status") or "missing",
        "redirectEligible": bool(bridge) and bridge.get("status") == "migrated",
        "removalCandidate": False,
    }


def _serializar_post_route(route):
    return {
        **route,
        "classification": "legacy_operational_post",
        "removalCandidate": True,
        "decision": "remove_after_next_api_smoke",
    }


def _serializar_removed_post_route(route):
    return {
        **route,
        "classification": "legacy_operational_post",
        "removalCandidate": False,
        "decision": "removed_api_only",
    }


def _serializar_inline_post_surface(surface):
    return {
        **surface,
        "classification": "legacy_operational_inline_post",
        "removalCandidate": True,
        "decision": "remove_or_405_after_api_smoke",
    }


def _serializar_removed_inline_post_surface(surface):
    return {
        **surface,
        "classification": "legacy_operational_inline_post",
        "removalCandidate": False,
        "decision": "blocked_api_only",
    }


def _serializar_support_route(route):
    route_name = route["routeName"]
    return {
        **route,
        "djangoUrl": _reverse_route(route_name),
        "removalCandidate": False,
    }


def _reverse_surface(surface_key, args=None):
    return _reverse_route(surface_key, args=args)


def _reverse_route(route_name, args=None):
    try:
        return reverse(f"caixa:{route_name}", args=args or [])
    except NoReverseMatch:
        return ""


def _issues_inventario(operational):
    issues = []
    for surface in operational:
        if not surface["djangoUrl"]:
            issues.append(
                {
                    "code": "missingDjangoRoute",
                    "surface": surface["surface"],
                    "detail": "Rota Django operacional nao resolvida.",
                }
            )
        if surface["nextCoverage"] == "covered" and not surface["bridgeRegistered"]:
            issues.append(
                {
                    "code": "missingFrontendBridge",
                    "surface": surface["surface"],
                    "detail": "Superficie coberta pelo Next sem ponte LEGACY_FRONTEND_SURFACES.",
                }
            )
        if surface["nextCoverage"] == "covered" and surface["bridgeStatus"] != "migrated":
            issues.append(
                {
                    "code": "coveredSurfaceNotMigrated",
                    "surface": surface["surface"],
                    "detail": "Superficie coberta pelo Next nao esta marcada como migrated.",
                }
            )
    return issues


def _riscos_inventario(operational, post_routes, inline_post_surfaces):
    risks = []
    partial = [
        surface["surface"] for surface in operational if surface["nextCoverage"] == "partial"
    ]
    if partial:
        risks.append(
            {
                "code": "partialNextCoverage",
                "surfaces": partial,
                "detail": "Nao remover fisicamente superficies com cobertura parcial sem aceite operacional.",
            }
        )
    if post_routes:
        risks.append(
            {
                "code": "legacyPostRoutes",
                "routes": [route["routeName"] for route in post_routes],
                "detail": "Rotas POST HTML antigas devem sair somente depois de smoke API/Next equivalente.",
            }
        )
    if inline_post_surfaces:
        risks.append(
            {
                "code": "legacyInlinePostSurfaces",
                "surfaces": [surface["surface"] for surface in inline_post_surfaces],
                "detail": "Views HTML migradas ainda aceitam POST embutido; remover ou retornar 405 apos smoke API equivalente.",
            }
        )
    risks.append(
        {
            "code": "sharedForms",
            "modules": [
                item["module"]
                for item in FORMS_INVENTORY
                if item["decision"] != "candidate_after_html_routes_removed"
            ],
            "detail": "Forms compartilhados com API/Admin/services nao devem ser removidos junto com templates.",
        }
    )
    return risks


def _registro_inventario(resultado):
    summary = resultado["summary"]
    lines = [
        "### Registro PM-06.1329 - inventario HTML Django operacional",
        "",
        f"- generatedAt: {resultado['generatedAt']}",
        f"- ready: {resultado['ready']}",
        f"- operationalHtmlCount: {summary['operationalHtmlCount']}",
        f"- removedOperationalHtmlCount: {summary['removedOperationalHtmlCount']}",
        f"- coveredByNextCount: {summary['coveredByNextCount']}",
        f"- partialCoverageCount: {summary['partialCoverageCount']}",
        f"- removalCandidateCount: {summary['removalCandidateCount']}",
        f"- removalBlockedCount: {summary['removalBlockedCount']}",
        f"- legacyPostRouteCount: {summary['legacyPostRouteCount']}",
        f"- removedLegacyPostRouteCount: {summary['removedLegacyPostRouteCount']}",
        f"- inlineLegacyPostSurfaceCount: {summary['inlineLegacyPostSurfaceCount']}",
        f"- removedInlineLegacyPostSurfaceCount: {summary['removedInlineLegacyPostSurfaceCount']}",
        f"- removedOperationalShellTemplateCount: {summary['removedOperationalShellTemplateCount']}",
        f"- removedLegacyFormCount: {summary['removedLegacyFormCount']}",
        f"- removedOperationalAssetCount: {summary['removedOperationalAssetCount']}",
        "",
        "#### Decisao arquitetural",
        "- Django fica como backend/API/Admin.",
        "- Next.js fica como unica interface operacional.",
        "- HTML Django operacional foi removido; auth, erro e suporte tecnico permanecem preservados.",
        "",
        "#### Superficies operacionais",
    ]
    for surface in resultado["operationalHtml"]:
        lines.append(
            "- "
            f"{surface['surface']}: coverage={surface['nextCoverage']}; "
            f"bridge={surface['bridgeStatus']}; "
            f"next={surface['nextPath'] or '-'}; "
            f"removeCandidate={surface['removalCandidate']}"
        )

    lines.extend(["", "#### Superficies HTML operacionais removidas"])
    for surface in resultado["removedOperationalHtml"]:
        lines.append(
            "- "
            f"{surface['surface']}: removedIn={surface['removedIn']}; "
            f"next={surface['nextPath'] or '-'}; "
            f"decision={surface['decision']}"
        )

    lines.extend(["", "#### Shell operacional removido"])
    for item in resultado["removedOperationalShellTemplates"]:
        lines.append(
            "- "
            f"{item['template']}: removedIn={item['removedIn']}; "
            f"classification={item['classification']}"
        )

    lines.extend(["", "#### Rotas POST legadas"])
    if resultado["legacyPostRoutes"]:
        for route in resultado["legacyPostRoutes"]:
            lines.append(
                "- "
                f"{route['routeName']}: nextApi={route['nextApi']}; "
                f"removeCandidate={route['removalCandidate']}"
            )
    else:
        lines.append("- nenhuma pendente")

    lines.extend(["", "#### Rotas POST legadas removidas"])
    for route in resultado["removedLegacyPostRoutes"]:
        lines.append(
            "- "
            f"{route['routeName']}: removedIn={route['removedIn']}; "
            f"nextApi={route['nextApi']}; "
            f"decision={route['decision']}"
        )

    lines.extend(["", "#### POST HTML embutido ainda pendente"])
    if resultado["inlineLegacyPostSurfaces"]:
        for surface in resultado["inlineLegacyPostSurfaces"]:
            lines.append(
                "- "
                f"{surface['surface']}: nextApi={surface['nextApi']}; "
                f"decision={surface['decision']}"
            )
    else:
        lines.append("- nenhum pendente")

    lines.extend(["", "#### POST HTML embutido bloqueado"])
    for surface in resultado["removedInlineLegacyPostSurfaces"]:
        lines.append(
            "- "
            f"{surface['surface']}: nextApi={surface['nextApi']}; "
            f"removedIn={surface['removedIn']}; "
            f"decision={surface['decision']}"
        )

    lines.extend(["", "#### Suporte preservado"])
    for route in resultado["preservedHtmlSupport"]:
        lines.append(
            "- "
            f"{route['routeName']}: classification={route['classification']}; "
            f"decision={route['decision']}"
        )

    lines.extend(["", "#### Forms"])
    for item in resultado["formsInventory"]:
        lines.append(
            "- "
            f"{item['module']}: classification={item['classification']}; "
            f"decision={item['decision']}"
        )

    lines.extend(["", "#### Forms removidos"])
    for item in resultado["removedFormsInventory"]:
        lines.append(
            "- "
            f"{item['module']}: removedIn={item['removedIn']}; "
            f"classification={item['classification']}; "
            f"decision={item['decision']}"
        )

    lines.extend(["", "#### Assets operacionais removidos"])
    for item in resultado["removedOperationalAssets"]:
        lines.append(
            "- "
            f"{item['asset']}: removedIn={item['removedIn']}; "
            f"classification={item['classification']}"
        )

    lines.extend(["", "#### Riscos"])
    if resultado["risks"]:
        for risk in resultado["risks"]:
            lines.append(f"- {risk['code']}: {risk['detail']}")
    else:
        lines.append("- nenhum")

    lines.extend(["", "#### Pendencias"])
    if resultado["issues"]:
        for issue in resultado["issues"]:
            lines.append(f"- {issue['surface']}: {issue['detail']}")
    else:
        lines.append("- nenhuma")

    output_files = resultado.get("outputEvidenceFiles") or {}
    lines.extend(
        [
            "",
            "#### Arquivos salvos",
            f"- json: {output_files.get('json') or '-'}",
            f"- registro: {output_files.get('record') or '-'}",
        ]
    )
    return "\n".join(lines)


def _normalizar_arquivos_saida(options):
    evidence_dir = options.get("diretorio_evidencias") or ""
    save_json = options.get("salvar_json") or ""
    save_record = options.get("salvar_registro") or ""
    if evidence_dir:
        base_path = Path(evidence_dir).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError("--diretorio-evidencias deve apontar para um diretorio")
        if not save_json:
            save_json = str(base_path / DEFAULT_OUTPUT_JSON)
        if not save_record:
            save_record = str(base_path / DEFAULT_OUTPUT_RECORD)
    return {
        "directory": evidence_dir,
        "json": save_json,
        "record": save_record,
    }


def _validar_arquivos_saida(output_files, *, exigir=False):
    if not exigir:
        return []
    issues = []
    if not (output_files.get("json") or ""):
        issues.append("arquivo JSON de evidencia PM-06.1313 nao informado")
    if not (output_files.get("record") or ""):
        issues.append("registro markdown de evidencia PM-06.1313 nao informado")
    return issues


def _aplicar_issues_saida(resultado, issues):
    if not issues:
        return
    resultado["ready"] = False
    for issue in issues:
        resultado["issues"].append(
            {
                "code": "missingEvidenceOutput",
                "surface": "output",
                "detail": issue,
            }
        )


def _salvar_resultado(resultado):
    output_files = resultado.get("outputEvidenceFiles") or {}
    json_path = output_files.get("json")
    record_path = output_files.get("record")
    if json_path:
        _salvar_texto(
            json_path,
            json.dumps(resultado, ensure_ascii=False, sort_keys=True, indent=2),
        )
    if record_path:
        _salvar_texto(record_path, resultado["executionRecord"]["markdown"])


def _salvar_texto(path, content):
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _formatar_primeira_issue(resultado):
    if resultado["issues"]:
        issue = resultado["issues"][0]
        return f"inventario HTML Django PM-06 reprovado: {issue['surface']}: {issue['detail']}"
    return "inventario HTML Django PM-06 reprovado"


class Command(BaseCommand):
    help = (
        "Inventaria telas HTML Django operacionais legadas, cobertura Next.js "
        "e riscos antes da remocao fisica na PM-06."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado consolidado em JSON.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando o inventario tiver pendencias.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON da validacao em arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o executionRecord.markdown em arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help="Diretorio usado para salvar JSON e Markdown com nomes padronizados.",
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            action="store_true",
            help="Reprova se os caminhos de JSON e registro nao forem informados.",
        )

    def handle(self, *args, **options):
        output_files = _normalizar_arquivos_saida(options)
        resultado = inventariar_html_django_pm06(options)
        resultado["outputEvidenceFiles"] = output_files
        _aplicar_issues_saida(
            resultado,
            _validar_arquivos_saida(
                output_files,
                exigir=options["exigir_arquivos_evidencia"],
            ),
        )
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_inventario(resultado),
        }
        _salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(_formatar_primeira_issue(resultado))

    def _imprimir_relatorio(self, resultado):
        status = "aprovado" if resultado["ready"] else "com pendencias"
        self.stdout.write(f"Inventario HTML Django PM-06 {status}.")
        summary = resultado["summary"]
        self.stdout.write(
            "Operacionais: "
            f"{summary['operationalHtmlCount']}; "
            f"cobertas no Next: {summary['coveredByNextCount']}; "
            f"parciais: {summary['partialCoverageCount']}; "
            f"candidatas remocao: {summary['removalCandidateCount']}"
        )
        self.stdout.write("Riscos:")
        for risk in resultado["risks"]:
            self.stdout.write(f"- {risk['code']}: {risk['detail']}")
        self.stdout.write("Registro markdown:")
        self.stdout.write(resultado["executionRecord"]["markdown"])
