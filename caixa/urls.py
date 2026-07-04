from django.urls import path

from .views_api_auth import (
    api_auth_csrf,
    api_auth_login,
    api_auth_logout,
    api_auth_session,
)
from .views_auth import (
    LoginSeguroView,
    LogoutSeguroView,
    RecuperarSenhaView,
    RecuperarSenhaDoneView,
    RecuperarSenhaConfirmView,
    RecuperarSenhaCompleteView,
)
from .views_backups import (
    api_backup_criar_manual,
    api_backups,
    backup_download,
    backups_lista,
)
from .views_custos_fixos import custos_fixos_lista
from .views_dashboard import (
    api_custos_por_evento,
    api_dashboard_financial_overview,
    custos_por_evento,
    dashboard_financeiro,
)
from .views_financiamentos import (
    api_criar_divida_financeira,
    api_credores_financiamentos,
    api_financiamentos,
    lista_financiamentos,
    pagar_parcela,
)
from .views_lancamentos import api_lancamentos_financeiros
from .views_modelagem_canonica import (
    api_baixas_financeiras_canonicas,
    api_modelagem_financeira_canonica,
)
from .views_obrigacoes import (
    api_exportar_obrigacoes_financeiras,
    api_liquidar_obrigacao_financeira,
    api_obrigacoes_financeiras,
)
from .views_investimentos import api_investimentos, lista_investimentos
from .views_custos_extras_api import api_criar_custo_extra_evento
from .views_clientes_api import api_cliente_detalhe, api_clientes
from .views_custos_fixos_api import api_custo_fixo_detalhe, api_custos_fixos
from .views_despesas_api import api_despesa_detalhe
from .views_eventos_api import api_evento_detalhe, api_eventos
from .views_orcamentos_api import (
    api_aprovar_orcamento,
    api_orcamento_detalhe,
    api_orcamentos,
)
from .views_receitas_api import api_receita_detalhe
from .views_servicos_api import api_servico_detalhe, api_servicos
from .views_mes_financeiro import api_mes_financeiro, mes_financeiro
from .views_pagamentos import (
    pagamentos,
    pagamentos_custos_extras,
    pagamentos_custos_servico,
    pagamentos_fcf,
)
from .views_cadastros import (
    clientes_lista,
    custo_extra_adicionar,
    despesas_lista,
    eventos_lista,
    orcamento_adicionar,
    orcamentos_lista,
    receitas_lista,
)


app_name = "caixa"

urlpatterns = [
    # Autenticacao
    path("login/", LoginSeguroView.as_view(), name="login"),
    path("logout/", LogoutSeguroView.as_view(), name="logout"),
    path("api/auth/csrf/", api_auth_csrf, name="api_auth_csrf"),
    path("api/auth/login/", api_auth_login, name="api_auth_login"),
    path("api/auth/logout/", api_auth_logout, name="api_auth_logout"),
    path("api/auth/session/", api_auth_session, name="api_auth_session"),
    path("password-reset/", RecuperarSenhaView.as_view(), name="password_reset"),
    path("password-reset/done/", RecuperarSenhaDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", RecuperarSenhaConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", RecuperarSenhaCompleteView.as_view(), name="password_reset_complete"),
    path("backups/", backups_lista, name="backups_lista"),
    path("backups/<str:nome_arquivo>/download/", backup_download, name="backup_download"),
    path("api/backups/", api_backups, name="api_backups"),
    path("api/backups/criar/", api_backup_criar_manual, name="api_backup_criar_manual"),

    # Telas principais
    path("", dashboard_financeiro, name="dashboard_financeiro"),
    path(
        "api/dashboard/financial-overview/",
        api_dashboard_financial_overview,
        name="api_dashboard_financial_overview",
    ),
    path(
        "api/custos-por-evento/",
        api_custos_por_evento,
        name="api_custos_por_evento",
    ),
    path(
        "api/lancamentos-financeiros/",
        api_lancamentos_financeiros,
        name="api_lancamentos_financeiros",
    ),
    path(
        "api/modelagem-financeira-canonica/",
        api_modelagem_financeira_canonica,
        name="api_modelagem_financeira_canonica",
    ),
    path(
        "api/canonical-financial-model/",
        api_modelagem_financeira_canonica,
        name="api_canonical_financial_model",
    ),
    path(
        "api/baixas-financeiras-canonicas/",
        api_baixas_financeiras_canonicas,
        name="api_baixas_financeiras_canonicas",
    ),
    path(
        "api/canonical-settlements/",
        api_baixas_financeiras_canonicas,
        name="api_canonical_settlements",
    ),
    path(
        "api/obrigacoes-financeiras/",
        api_obrigacoes_financeiras,
        name="api_obrigacoes_financeiras",
    ),
    path(
        "api/obrigacoes-financeiras/exportar/",
        api_exportar_obrigacoes_financeiras,
        name="api_exportar_obrigacoes_financeiras",
    ),
    path(
        "api/payment-obligations/",
        api_obrigacoes_financeiras,
        name="api_payment_obligations",
    ),
    path(
        "api/obrigacoes-financeiras/liquidar/",
        api_liquidar_obrigacao_financeira,
        name="api_liquidar_obrigacao_financeira",
    ),
    path(
        "api/payment-obligations/settle/",
        api_liquidar_obrigacao_financeira,
        name="api_settle_payment_obligation",
    ),
    path("custos-por-evento/", custos_por_evento, name="custos_por_evento"),
    path("custos-fixos/", custos_fixos_lista, name="custos_fixos_lista"),
    path("fci/", lista_investimentos, name="lista_investimentos"),
    path("api/fci/", api_investimentos, name="api_investimentos"),
    path("pagamentos/", pagamentos, name="pagamentos"),
    path("fcf/", lista_financiamentos, name="lista_financiamentos"),
    path("api/fcf/", api_financiamentos, name="api_financiamentos"),
    path(
        "api/fcf/debts/",
        api_criar_divida_financeira,
        name="api_criar_divida_financeira",
    ),
    path(
        "api/fcf/creditors/",
        api_credores_financiamentos,
        name="api_credores_financiamentos",
    ),
    path(
        "api/eventos/custos-extras/",
        api_criar_custo_extra_evento,
        name="api_criar_custo_extra_evento",
    ),
    path("api/eventos/", api_eventos, name="api_eventos"),
    path("api/eventos/<int:pk>/", api_evento_detalhe, name="api_evento_detalhe"),
    path("api/clientes/", api_clientes, name="api_clientes"),
    path("api/clientes/<int:pk>/", api_cliente_detalhe, name="api_cliente_detalhe"),
    path("api/servicos/", api_servicos, name="api_servicos"),
    path("api/servicos/<int:pk>/", api_servico_detalhe, name="api_servico_detalhe"),
    path("api/orcamentos/", api_orcamentos, name="api_orcamentos"),
    path(
        "api/orcamentos/<int:pk>/",
        api_orcamento_detalhe,
        name="api_orcamento_detalhe",
    ),
    path(
        "api/orcamentos/<int:pk>/aprovar/",
        api_aprovar_orcamento,
        name="api_aprovar_orcamento",
    ),
    path("api/custos-fixos/", api_custos_fixos, name="api_custos_fixos"),
    path(
        "api/custos-fixos/<int:pk>/",
        api_custo_fixo_detalhe,
        name="api_custo_fixo_detalhe",
    ),
    path("api/receitas/<int:pk>/", api_receita_detalhe, name="api_receita_detalhe"),
    path("api/despesas/<int:pk>/", api_despesa_detalhe, name="api_despesa_detalhe"),
    path("fcf/pagamentos/", pagamentos_fcf, name="pagamentos_fcf"),
    path("fcf/parcelas/<int:pk>/pagar/", pagar_parcela, name="pagar_parcela"),
    path("mes-financeiro/", mes_financeiro, name="mes_financeiro"),
    path("api/mes-financeiro/", api_mes_financeiro, name="api_mes_financeiro"),
    path("clientes/", clientes_lista, name="clientes_lista"),
    path("orcamentos/", orcamentos_lista, name="orcamentos_lista"),
    path("orcamentos/adicionar/", orcamento_adicionar, name="orcamento_adicionar"),
    path("eventos/", eventos_lista, name="eventos_lista"),
    path(
        "eventos/custos-servico/pagamentos/",
        pagamentos_custos_servico,
        name="pagamentos_custos_servico",
    ),
    path(
        "eventos/custos-extras/pagamentos/",
        pagamentos_custos_extras,
        name="pagamentos_custos_extras",
    ),
    path("eventos/custos-extras/adicionar/", custo_extra_adicionar, name="custo_extra_adicionar"),
    path("receitas/", receitas_lista, name="receitas_lista"),
    path("despesas/", despesas_lista, name="despesas_lista"),
]
