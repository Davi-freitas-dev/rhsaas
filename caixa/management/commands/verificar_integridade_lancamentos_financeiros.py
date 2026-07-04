import json

from django.core.management.base import BaseCommand, CommandError

from caixa.models import LancamentoFinanceiro, DespesaOperacional


class Command(BaseCommand):
    help = (
        "Audita a integridade semantica dos LancamentoFinanceiro existentes. "
        "O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias detalhadas.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando houver inconsistencia.",
        )

    def handle(self, *args, **options):
        resultado = verificar_integridade_lancamentos_financeiros(
            limit=options["limit"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir(resultado)

        if options["falhar"] and not resultado["consistent"]:
            raise CommandError(
                f"{resultado['totalIssues']} inconsistencia(s) em lancamentos "
                f"financeiros: {formatar_primeira_issue_lancamentos(resultado)}"
            )

    def _imprimir(self, resultado):
        if resultado["consistent"]:
            self.stdout.write("Integridade de lancamentos financeiros consistente.")
        else:
            self.stdout.write(
                "Integridade de lancamentos financeiros com pontos de atencao."
            )

        self.stdout.write(
            f"Verificados: {resultado['checked']}; "
            f"inconsistencias={resultado['totalIssues']}"
        )

        for issue in resultado["issues"]:
            self.stdout.write(
                "- "
                f"lancamento:{issue['ledgerEntryId']} "
                f"{issue['code']}: origem={issue['origin'] or '-'} "
                f"tipo={issue['type']}; fluxo={issue['cashFlowGroup']}; "
                f"natureza={issue['nature']}; {issue['message']}"
            )

        if resultado["hasMore"]:
            self.stdout.write(
                f"Exibindo {len(resultado['issues'])} de "
                f"{resultado['totalIssues']} inconsistencia(s). Use --limit para ampliar."
            )


def verificar_integridade_lancamentos_financeiros(limit=20):
    issues = []
    checked = 0
    query = LancamentoFinanceiro.objects.select_related(
        "despesa_operacional",
        "investimento",
        "financiamento_movimentacao",
    ).order_by("id")

    for lancamento in query:
        checked += 1
        issues.extend(_issues_lancamento(lancamento))

    issues_limitadas = issues[:limit]
    return {
        "checked": checked,
        "consistent": len(issues) == 0,
        "totalIssues": len(issues),
        "hasMore": len(issues) > len(issues_limitadas),
        "issues": issues_limitadas,
    }


def _issues_lancamento(lancamento):
    issues = []
    origens = lancamento.campos_origem_preenchidos()

    if len(origens) != 1:
        issues.append(
            _issue(
                lancamento,
                "origem_invalida",
                ",".join(origens),
                "Lancamento financeiro deve possuir exatamente uma origem.",
            )
        )
        return issues

    origem = origens[0]
    regra = LancamentoFinanceiro.REGRAS_ORIGEM[origem]
    tipo_esperado = regra.get("tipo")

    if tipo_esperado and lancamento.tipo != tipo_esperado:
        issues.append(
            _issue(
                lancamento,
                "tipo_incoerente",
                origem,
                f"Tipo esperado para a origem: {tipo_esperado}.",
            )
        )

    if lancamento.fluxo != regra["fluxo"]:
        issues.append(
            _issue(
                lancamento,
                "fluxo_incoerente",
                origem,
                f"Fluxo esperado para a origem: {regra['fluxo']}.",
            )
        )

    if lancamento.natureza != regra["natureza"]:
        issues.append(
            _issue(
                lancamento,
                "natureza_incoerente",
                origem,
                f"Natureza esperada para a origem: {regra['natureza']}.",
            )
        )

    if origem == "despesa_operacional":
        despesa = lancamento.despesa_operacional
        if despesa and despesa.origem != DespesaOperacional.ORIGEM_MANUAL:
            issues.append(
                _issue(
                    lancamento,
                    "despesa_operacional_nao_manual",
                    origem,
                    "Lancamento de despesa operacional aponta para despesa sincronizada.",
                )
            )

    if origem == "investimento" and lancamento.investimento_id:
        _validar_tipo_fluxo_origem(lancamento, lancamento.investimento, origem, issues)

    if (
        origem == "financiamento_movimentacao"
        and lancamento.financiamento_movimentacao_id
    ):
        _validar_tipo_fluxo_origem(
            lancamento,
            lancamento.financiamento_movimentacao,
            origem,
            issues,
        )

    return issues


def _validar_tipo_fluxo_origem(lancamento, origem_objeto, origem, issues):
    if origem_objeto.tipo_fluxo != lancamento.tipo:
        issues.append(
            _issue(
                lancamento,
                "tipo_fluxo_origem_incoerente",
                origem,
                f"Tipo deve acompanhar o tipo_fluxo da origem: {origem_objeto.tipo_fluxo}.",
            )
        )


def _issue(lancamento, code, origin, message):
    return {
        "ledgerEntryId": lancamento.id,
        "code": code,
        "origin": origin,
        "type": lancamento.tipo,
        "cashFlowGroup": lancamento.fluxo,
        "nature": lancamento.natureza,
        "message": message,
    }


def formatar_primeira_issue_lancamentos(resultado):
    issues = resultado.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."

    issue = issues[0]
    return (
        f"lancamento:{issue['ledgerEntryId']} {issue['code']} "
        f"origem={issue['origin'] or '-'} {issue['message']}"
    )
