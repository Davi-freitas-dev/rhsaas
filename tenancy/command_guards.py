from django.core.management.base import CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name

from tenancy.models import DEMO_SLOT_CODES


SCOPE_TENANT_ONLY = "tenant-only"
SCOPE_PLATFORM_ONLY = "platform-only"
SCOPE_READ_ONLY = "read-only"
SCOPE_LEGACY_READ_ONLY = "legacy/read-only"

DEMO_POOL_SCHEMA_NAMES = frozenset(DEMO_SLOT_CODES)
FIXED_DEMO_SCHEMA_NAME = "rh_teste"


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


def is_demo_pool_schema(schema_name):
    return schema_name in DEMO_POOL_SCHEMA_NAMES


def ensure_demo_pool_schema(
    schema_name=None,
    *,
    command_name="comando demo",
    action="manipular tenant demo",
):
    schema_name = (
        current_schema_name() if schema_name is None else str(schema_name).strip()
    )

    if not schema_name:
        raise CommandError(
            f"O comando '{command_name}' exige um schema do pool demo "
            f"para {action}. Informe um valor entre demo1 e demo10."
        )

    public_schema_name = get_public_schema_name()
    if schema_name == public_schema_name:
        raise CommandError(
            f"O comando '{command_name}' recusou o schema public. "
            "Operacoes do pool demo nunca devem atingir o schema publico."
        )

    if schema_name == FIXED_DEMO_SCHEMA_NAME:
        raise CommandError(
            f"O comando '{command_name}' recusou o schema rh_teste. "
            "A demo fixa nao faz parte do pool demo1...demo10."
        )

    if not is_demo_pool_schema(schema_name):
        raise CommandError(
            f"O comando '{command_name}' aceita somente schemas do pool "
            "demo1...demo10. "
            f"Recebido: {schema_name!r}."
        )

    return schema_name


def ensure_demo_pool_confirmation(
    schema_name,
    confirmation,
    *,
    command_name="comando demo",
    option_name="--confirm",
    action="executar operacao destrutiva",
):
    schema_name = ensure_demo_pool_schema(
        schema_name,
        command_name=command_name,
        action=action,
    )
    confirmation = "" if confirmation is None else str(confirmation).strip()

    if confirmation != schema_name:
        raise CommandError(
            f"Confirmacao textual invalida para '{command_name}'. "
            f"Para {action}, informe {option_name} {schema_name}."
        )

    return schema_name
