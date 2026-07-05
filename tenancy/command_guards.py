from django.core.management.base import CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name


SCOPE_TENANT_ONLY = "tenant-only"
SCOPE_PLATFORM_ONLY = "platform-only"
SCOPE_READ_ONLY = "read-only"
SCOPE_LEGACY_READ_ONLY = "legacy/read-only"


TENANT_ONLY_COMMANDS = frozenset(
    {
        "auditar_fonte_escrita_baixas",
        "auditar_totais_negocio",
        "backup_banco_mensal",
        "diagnosticar_caixa_disponivel",
        "exportar_recadastro_manual_pm06",
        "limpar_base_operacional_pm06",
        "listar_candidatos_canario_pm03",
        "monitorar_janela_canonical_first",
        "simular_baixa_canonica",
        "simular_baixas_canonicas_lote",
        "sincronizar_credores_dividas_fcf",
        "sincronizar_despesas_eventos",
        "sincronizar_entradas_fcf_dividas",
        "sincronizar_lancamentos_financeiros",
        "sincronizar_modelagem_financeira_canonica",
        "testar_baixa_canonical_first",
        "validar_ativacao_canonical_first",
        "validar_baseline_pm02",
        "validar_janela_canonical_first",
        "validar_operacao_obrigacoes",
        "validar_preflight_deploy_financeiro",
        "validar_recortes_pm05",
        "validar_regressao_dividas_pm03",
        "verificar_conciliacao_obrigacoes",
        "verificar_consistencia_financeira",
        "verificar_despesas_manuais_sobrepostas",
        "verificar_duplicidade_custos_evento",
        "verificar_duplicidade_pagamentos",
        "verificar_integridade_lancamentos_financeiros",
        "verificar_integridade_valores_editaveis",
        "verificar_paridade_modelagem_canonica",
    }
)


READ_ONLY_COMMANDS = frozenset(
    {
        "inventariar_html_django_pm06",
        "validar_baseline_pm05",
        "validar_fechamento_pm03",
        "validar_fechamento_pm06",
        "validar_preparacao_pm06",
        "validar_prontidao_base_limpa_pm06",
        "validar_prontidao_congelamento_pm06",
        "validar_prontidao_migracao_limpeza_pm06",
        "validar_recadastro_manual_pm06",
        "validar_redirects_next_legado",
        "validar_rollback_conciliacao_pm06",
        "verificar_contrato_baixa_obrigacoes",
        "verificar_prontidao_escrita_canonica",
    }
)


LEGACY_READ_ONLY_COMMANDS = frozenset(
    {
        "gerar_snapshot_baseline_financeira",
    }
)


PLATFORM_ONLY_COMMANDS = frozenset()


COMMAND_SCOPES = {
    **{command: SCOPE_TENANT_ONLY for command in TENANT_ONLY_COMMANDS},
    **{command: SCOPE_PLATFORM_ONLY for command in PLATFORM_ONLY_COMMANDS},
    **{command: SCOPE_READ_ONLY for command in READ_ONLY_COMMANDS},
    **{command: SCOPE_LEGACY_READ_ONLY for command in LEGACY_READ_ONLY_COMMANDS},
}


def current_schema_name():
    return getattr(connection, "schema_name", None) or get_public_schema_name()


def ensure_tenant_schema(command_name, *, action="manipular dados operacionais"):
    schema_name = current_schema_name()
    if not schema_name or schema_name == get_public_schema_name():
        raise CommandError(
            f"O comando '{command_name}' deve ser executado em um schema de tenant "
            f"para {action}. Use tenant_command com --schema=<schema_name>."
        )
    return schema_name
