import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from caixa.management.commands.auditar_totais_negocio import (
    auditar_totais_negocio,
    formatar_primeira_divergencia_obrigacoes,
    formatar_primeira_issue_valores_editaveis as formatar_primeira_issue_valores_editaveis_auditoria,
)
from caixa.management.commands.validar_operacao_obrigacoes import (
    formatar_primeira_divergencia_conciliacao,
    formatar_primeira_inconsistencia_contrato,
    formatar_primeira_issue_canonica,
    formatar_primeira_issue_escrita_canonica,
    formatar_primeira_issue_valores_editaveis,
    validar_operacao_obrigacoes,
)
from caixa.management.commands.verificar_integridade_lancamentos_financeiros import (
    formatar_primeira_issue_lancamentos,
    verificar_integridade_lancamentos_financeiros,
)
from caixa.management.commands.verificar_despesas_manuais_sobrepostas import (
    verificar_despesas_manuais_sobrepostas,
)
from caixa.serializers_obrigacoes import formatar_status_leitura_obrigacoes
from caixa.services_dividas import resumir_integridade_credores_dividas
from caixa.services_dividas_fcf import resumir_integridade_entradas_fcf_dividas
from tenancy.command_guards import ensure_tenant_schema


LIMIT_ARGUMENTS = (
    ("canonical_limit", "--canonical-limit"),
    ("valores_editaveis_limit", "--valores-editaveis-limit"),
    ("lancamentos_limit", "--lancamentos-limit"),
    ("credores_dividas_limit", "--credores-dividas-limit"),
    ("entradas_fcf_dividas_limit", "--entradas-fcf-dividas-limit"),
)


class Command(BaseCommand):
    help = (
        "Executa o pre-flight financeiro de deploy em modo somente leitura: "
        "check do Django, auditoria de totais e validacao operacional completa."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado consolidado em JSON para automacoes.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando qualquer validacao do pre-flight reprovar.",
        )
        parser.add_argument(
            "--validar-deploy-django",
            action="store_true",
            help="Inclui `python manage.py check --deploy` no pre-flight.",
        )
        parser.add_argument(
            "--canonical-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias canonicas retornadas.",
        )
        parser.add_argument(
            "--valores-editaveis-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias de valores editaveis retornadas.",
        )
        parser.add_argument(
            "--valores-editaveis-escopo",
            "--editable-values-scope",
            action="append",
            choices=["divida", "evento", "orcamento"],
            default=[],
            help="Limita a auditoria de valores editaveis a um escopo especifico.",
        )
        parser.add_argument(
            "--valores-editaveis-object-id",
            "--editable-values-object-id",
            dest="valores_editaveis_object_ids",
            action="append",
            type=int,
            default=[],
            help="Limita a auditoria de valores editaveis a um ID especifico.",
        )
        parser.add_argument(
            "--lancamentos-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias de lancamentos retornadas.",
        )
        parser.add_argument(
            "--credores-dividas-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias de credores FCF retornadas.",
        )
        parser.add_argument(
            "--entradas-fcf-dividas-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias de entradas FCF retornadas.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("validar_preflight_deploy_financeiro", action="validar dados operacionais")
        resultado = validar_preflight_deploy_financeiro(options)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_preflight_deploy(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Pre-flight de deploy financeiro aprovado.")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Pre-flight de deploy financeiro com pontos de atencao."
                )
            )

        self._imprimir_check("Django check", resultado["systemCheck"])
        self._imprimir_check("Django check --deploy", resultado["deployCheck"])

        auditoria = resultado["businessTotalsAudit"]
        obrigacoes = auditoria["obligations"]
        self.stdout.write(
            "Auditoria de totais: "
            f"divergencias={obrigacoes['divergentCount']}; "
            f"diferenca={obrigacoes['realizedAmountDifference']}"
        )
        self.stdout.write(formatar_status_leitura_obrigacoes(obrigacoes["readModelStatus"]))

        valores = auditoria["editableValuesIntegrity"]
        if valores["consistent"]:
            self.stdout.write("Valores editaveis: efeitos derivados consistentes.")
        else:
            self.stdout.write(
                "Valores editaveis: "
                f"{valores['totalIssues']} inconsistencia(s): "
                f"{formatar_primeira_issue_valores_editaveis_auditoria(valores)}"
            )

        lancamentos = resultado["financialLedgerIntegrity"]
        if lancamentos["consistent"]:
            self.stdout.write("Lancamentos financeiros: classificacao consistente.")
        else:
            self.stdout.write(
                "Lancamentos financeiros: "
                f"{lancamentos['totalIssues']} inconsistencia(s): "
                f"{formatar_primeira_issue_lancamentos(lancamentos)}"
            )

        sobreposicoes = resultado["manualExpenseOverlapIntegrity"]
        if sobreposicoes["consistent"]:
            self.stdout.write(
                "Despesas manuais sobrepostas: nenhuma reservada com efeito financeiro."
            )
        else:
            self.stdout.write(
                "Despesas manuais sobrepostas: "
                f"{sobreposicoes['reservedWithFinancialEffectCount']} reservada(s) "
                f"com efeito financeiro: {formatar_primeira_sobreposicao_manual(sobreposicoes)}"
            )

        credores_dividas = resultado["debtCreditorIntegrity"]
        if credores_dividas["consistent"]:
            self.stdout.write("Credores de dividas FCF: cadastro mestre consistente.")
        else:
            self.stdout.write(
                "Credores de dividas FCF: "
                f"{credores_dividas['totalIssues']} inconsistencia(s): "
                f"{formatar_primeira_issue_credor_divida(credores_dividas)}"
            )

        entradas_fcf_dividas = resultado["debtAutomaticFcfEntryIntegrity"]
        if entradas_fcf_dividas["consistent"]:
            self.stdout.write("Entradas FCF de dividas: sincronizadas.")
        else:
            self.stdout.write(
                "Entradas FCF de dividas: "
                f"{entradas_fcf_dividas['totalIssues']} pendencia(s): "
                f"{formatar_primeira_issue_entrada_fcf_divida(entradas_fcf_dividas)}"
            )

        operacao = resultado["operationalValidation"]
        self.stdout.write(
            "Validacao operacional: " + ("pronta." if operacao["ready"] else "pendente.")
        )
        for issue in resultado["issues"]:
            self.stdout.write(f"- {issue}")

        roteiro = resultado["remediationPlan"]
        if roteiro["steps"]:
            self.stdout.write("Roteiro sugerido:")
            for passo in roteiro["steps"]:
                self.stdout.write(f"- {passo['command']}")

    def _imprimir_check(self, titulo, check):
        if not check["checked"]:
            self.stdout.write(f"{titulo}: nao executado.")
            return
        if check["ok"]:
            self.stdout.write(f"{titulo}: ok.")
            return
        self.stdout.write(f"{titulo}: falhou: {check['error']}")


def validar_preflight_deploy_financeiro(options=None):
    options = options or {}
    validar_limites_preflight(options)
    valores_editaveis_escopos = options.get("valores_editaveis_escopo") or []
    valores_editaveis_object_ids = options.get("valores_editaveis_object_ids") or []

    system_check = executar_django_check(deploy=False)
    deploy_check = (
        executar_django_check(deploy=True)
        if options.get("validar_deploy_django")
        else {"checked": False, "ok": True, "output": "", "error": ""}
    )
    auditoria = auditar_totais_negocio(
        validar_valores_editaveis=True,
        valores_editaveis_limit=options.get("valores_editaveis_limit", 20),
        valores_editaveis_escopos=valores_editaveis_escopos,
        valores_editaveis_object_ids=valores_editaveis_object_ids,
    )
    operacao = validar_operacao_obrigacoes(
        {
            "validar_canonico": True,
            "validar_escrita_canonica": True,
            "validar_valores_editaveis": True,
            "canonical_limit": options.get("canonical_limit", 20),
            "valores_editaveis_limit": options.get("valores_editaveis_limit", 20),
            "valores_editaveis_escopo": valores_editaveis_escopos,
            "valores_editaveis_object_ids": valores_editaveis_object_ids,
        }
    )
    integridade_lancamentos = verificar_integridade_lancamentos_financeiros(
        limit=options.get("lancamentos_limit", 20),
    )
    sobreposicoes_manuais = validar_sobreposicoes_despesas_manuais()
    integridade_credores_dividas = resumir_integridade_credores_dividas(
        limit=options.get("credores_dividas_limit", 20),
    )
    integridade_entradas_fcf_dividas = resumir_integridade_entradas_fcf_dividas(
        limit=options.get("entradas_fcf_dividas_limit", 20),
    )

    issues = coletar_issues_preflight(
        system_check=system_check,
        deploy_check=deploy_check,
        auditoria=auditoria,
        operacao=operacao,
        integridade_lancamentos=integridade_lancamentos,
        sobreposicoes_manuais=sobreposicoes_manuais,
        integridade_credores_dividas=integridade_credores_dividas,
        integridade_entradas_fcf_dividas=integridade_entradas_fcf_dividas,
    )
    roteiro_correcao = montar_roteiro_correcao_preflight(
        auditoria=auditoria,
        operacao=operacao,
        integridade_lancamentos=integridade_lancamentos,
        sobreposicoes_manuais=sobreposicoes_manuais,
        integridade_credores_dividas=integridade_credores_dividas,
        integridade_entradas_fcf_dividas=integridade_entradas_fcf_dividas,
    )

    return {
        "ready": not issues,
        "readOnly": True,
        "systemCheck": system_check,
        "deployCheck": deploy_check,
        "businessTotalsAudit": auditoria,
        "financialLedgerIntegrity": integridade_lancamentos,
        "manualExpenseOverlapIntegrity": sobreposicoes_manuais,
        "debtCreditorIntegrity": integridade_credores_dividas,
        "debtAutomaticFcfEntryIntegrity": integridade_entradas_fcf_dividas,
        "operationalValidation": operacao,
        "issues": issues,
        "remediationPlan": roteiro_correcao,
    }


def validar_limites_preflight(options):
    for option_name, flag in LIMIT_ARGUMENTS:
        if options.get(option_name, 0) < 0:
            raise CommandError(f"{flag} deve ser maior ou igual a 0.")


def executar_django_check(deploy=False):
    stdout = StringIO()
    stderr = StringIO()
    try:
        args = ["check"]
        if deploy:
            args.append("--deploy")
        call_command(*args, stdout=stdout, stderr=stderr)
    except Exception as exc:  # pragma: no cover - coberto por integracao do Django
        return {
            "checked": True,
            "ok": False,
            "output": stdout.getvalue().strip(),
            "error": str(exc),
        }

    return {
        "checked": True,
        "ok": True,
        "output": stdout.getvalue().strip(),
        "error": stderr.getvalue().strip(),
    }


def coletar_issues_preflight(
    system_check,
    deploy_check,
    auditoria,
    operacao,
    integridade_lancamentos,
    sobreposicoes_manuais,
    integridade_credores_dividas,
    integridade_entradas_fcf_dividas,
):
    issues = []
    if not system_check["ok"]:
        issues.append(f"Django check falhou: {system_check['error']}")
    if deploy_check["checked"] and not deploy_check["ok"]:
        issues.append(f"Django check --deploy falhou: {deploy_check['error']}")

    obrigacoes = auditoria["obligations"]
    if obrigacoes["divergentCount"] > 0:
        issues.append(
            "Auditoria de totais encontrou divergencia origem/ledger: "
            f"{formatar_primeira_divergencia_obrigacoes(obrigacoes)}"
        )

    valores_auditoria = auditoria["editableValuesIntegrity"]
    if valores_auditoria["checked"] and not valores_auditoria["consistent"]:
        issues.append(
            "Auditoria de totais encontrou valores editaveis inconsistentes: "
            f"{formatar_primeira_issue_valores_editaveis_auditoria(valores_auditoria)}"
        )

    if not integridade_lancamentos["consistent"]:
        issues.append(
            "Auditoria de lancamentos financeiros encontrou inconsistencia: "
            f"{formatar_primeira_issue_lancamentos(integridade_lancamentos)}"
        )

    if not sobreposicoes_manuais["consistent"]:
        issues.append(
            "Auditoria de despesas manuais encontrou custo estruturado registrado como manual: "
            f"{formatar_primeira_sobreposicao_manual(sobreposicoes_manuais)}"
        )

    if not integridade_credores_dividas["consistent"]:
        issues.append(
            "Auditoria de credores de dividas FCF encontrou inconsistencia: "
            f"{formatar_primeira_issue_credor_divida(integridade_credores_dividas)}"
        )

    if not integridade_entradas_fcf_dividas["consistent"]:
        issues.append(
            "Auditoria de entradas FCF de dividas encontrou pendencia: "
            f"{formatar_primeira_issue_entrada_fcf_divida(integridade_entradas_fcf_dividas)}"
        )

    if not operacao["ready"]:
        issues.append(
            "Validacao operacional encontrou pendencia: "
            f"{formatar_primeira_issue_operacional(operacao)}"
        )
    return issues


def validar_sobreposicoes_despesas_manuais():
    resultado = verificar_despesas_manuais_sobrepostas()
    return {
        **resultado,
        "consistent": resultado["reservedWithFinancialEffectCount"] == 0,
    }


def formatar_primeira_sobreposicao_manual(resultado):
    itens = resultado.get("items") or []
    item = next(
        (
            item
            for item in itens
            if item.get("usesReservedDescription") and item.get("hasFinancialEffect")
        ),
        itens[0] if itens else None,
    )
    if not item:
        return "consulte o relatorio detalhado."

    return (
        f"origem={item['structuredSource']} "
        f"evento={item['eventLabel']} "
        f"categoria={item['category']} "
        f"despesa={item['expenseId']} "
        f"previsto={item['plannedAmount']} "
        f"pago={item['paidAmount']} "
        f"descricao={item['description']}"
    )


def formatar_primeira_issue_credor_divida(resultado):
    itens = resultado.get("items") or []
    if not itens:
        return "consulte o relatorio detalhado."

    item = itens[0]
    return (
        f"tipo={item['issueType']} "
        f"divida={item['debtId']} "
        f"credor_legado={item['legacyCreditor']} "
        f"credor_cadastro={item.get('creditorName') or '-'} "
        f"correcao_automatica={'sim' if item.get('canFix') else 'nao'}"
    )


def formatar_primeira_issue_entrada_fcf_divida(resultado):
    itens = resultado.get("items") or []
    if not itens:
        return "consulte o relatorio detalhado."

    item = itens[0]
    return (
        f"acao={item['action']} "
        f"divida={item['debtId']} "
        f"tipo={item['debtType']} "
        f"credor={item['debtCreditorName']}"
    )


def montar_roteiro_correcao_preflight(
    auditoria,
    operacao,
    integridade_lancamentos,
    sobreposicoes_manuais,
    integridade_credores_dividas,
    integridade_entradas_fcf_dividas,
):
    passos = []

    if _valores_editaveis_inconsistentes(auditoria, operacao):
        adicionar_passo(
            passos,
            "editableValues",
            "Corrigir efeitos derivados de valores editáveis",
            "python manage.py verificar_integridade_valores_editaveis --corrigir --falhar-com-inconsistencia",
            "Há valores editáveis com efeitos derivados desatualizados.",
        )

    if not sobreposicoes_manuais["consistent"]:
        adicionar_passo(
            passos,
            "structuredExpenses",
            "Recriar despesas derivadas dos custos estruturados",
            "python manage.py sincronizar_despesas_eventos",
            "Há despesa reservada de custo estruturado marcada como manual.",
        )
        adicionar_passo(
            passos,
            "structuredExpenses",
            "Validar se ainda há despesa reservada marcada como manual",
            "python manage.py verificar_despesas_manuais_sobrepostas --falhar-com-reservada",
            "Confirma que custos de serviço e custos extras não ficaram duplicados como despesas manuais.",
        )

    if not integridade_credores_dividas["consistent"]:
        adicionar_passo(
            passos,
            "debtCreditors",
            "Sincronizar credores cadastrados das dividas FCF",
            "python manage.py sincronizar_credores_dividas_fcf --aplicar --falhar-com-pendencia",
            "Garante que credor_cadastro seja a fonte principal e credor textual fique apenas como alias.",
        )

    if not integridade_entradas_fcf_dividas["consistent"]:
        adicionar_passo(
            passos,
            "debtAutomaticFcfEntries",
            "Sincronizar entradas FCF automaticas das dividas",
            "python manage.py sincronizar_entradas_fcf_dividas --aplicar --falhar-com-pendencia",
            "Garante que dividas emprestimo/financiamento tenham a entrada FCF/caixa automatica correta.",
        )

    if _origem_ledger_inconsistente(auditoria) or not integridade_lancamentos["consistent"]:
        adicionar_passo(
            passos,
            "financialLedger",
            "Sincronizar lançamentos financeiros a partir das origens",
            "python manage.py sincronizar_lancamentos_financeiros --aplicar",
            "Há divergência entre origem e ledger ou classificação de lançamento inconsistente.",
        )

    if _modelagem_canonica_pendente(operacao):
        adicionar_passo(
            passos,
            "canonicalModeling",
            "Sincronizar modelagem financeira canônica",
            "python manage.py sincronizar_modelagem_financeira_canonica --aplicar",
            "A modelagem canônica está ausente ou divergente em relação às origens.",
        )
        adicionar_passo(
            passos,
            "canonicalModeling",
            "Verificar paridade da modelagem canônica",
            "python manage.py verificar_paridade_modelagem_canonica --falhar",
            "Confirma que obrigações, baixas e alocações canônicas ficaram em paridade.",
        )

    if passos:
        adicionar_passo(
            passos,
            "preflight",
            "Reexecutar pre-flight financeiro",
            "python manage.py validar_preflight_deploy_financeiro --falhar",
            "Valida novamente a base depois das correções sugeridas.",
        )

    return {
        "version": "financial-preflight-remediation-v1",
        "steps": passos,
    }


def adicionar_passo(passos, category, label, command, reason):
    if any(passo["command"] == command for passo in passos):
        return
    passos.append({
        "order": len(passos) + 1,
        "category": category,
        "label": label,
        "command": command,
        "reason": reason,
    })


def _valores_editaveis_inconsistentes(auditoria, operacao):
    valores_auditoria = auditoria["editableValuesIntegrity"]
    valores_operacao = operacao["editableValuesIntegrity"]
    return (
        valores_auditoria["checked"] and not valores_auditoria["consistent"]
    ) or (
        valores_operacao["checked"] and not valores_operacao["consistent"]
    )


def _origem_ledger_inconsistente(auditoria):
    return auditoria["obligations"]["divergentCount"] > 0


def _modelagem_canonica_pendente(operacao):
    canonico = operacao["canonicalModeling"]
    return canonico["checked"] and not canonico["consistent"]


def formatar_primeira_issue_operacional(operacao):
    contrato = operacao["contract"]
    if not contrato["consistent"]:
        return formatar_primeira_inconsistencia_contrato(contrato)

    conciliacao = operacao["reconciliation"]
    if conciliacao["hasDivergences"]:
        return formatar_primeira_divergencia_conciliacao(conciliacao)

    canonico = operacao["canonicalModeling"]
    if canonico["checked"] and not canonico["consistent"]:
        return formatar_primeira_issue_canonica(canonico)

    escrita = operacao["canonicalWriteReadiness"]
    if escrita["checked"] and not escrita["ready"]:
        return formatar_primeira_issue_escrita_canonica(escrita)

    valores = operacao["editableValuesIntegrity"]
    if valores["checked"] and not valores["consistent"]:
        return formatar_primeira_issue_valores_editaveis(valores)

    return "consulte o relatorio detalhado."


def formatar_erro_preflight_deploy(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Pre-flight de deploy financeiro nao aprovado: {issues[0]}"
    return "Pre-flight de deploy financeiro nao aprovado."
