import json

from django.core.management.base import BaseCommand, CommandError

from caixa.management.commands.verificar_conciliacao_obrigacoes import (
    adicionar_argumentos_filtros_conciliacao,
    montar_filtros_conciliacao_obrigacoes,
    validar_conciliacao_obrigacoes,
)
from caixa.management.commands.verificar_contrato_baixa_obrigacoes import (
    validar_contrato_baixa_obrigacoes,
)
from caixa.management.commands.verificar_prontidao_escrita_canonica import (
    verificar_prontidao_escrita_canonica,
)
from caixa.serializers_obrigacoes import formatar_status_leitura_obrigacoes
from caixa.services_modelagem_canonica import (
    verificar_paridade_modelagem_financeira_canonica,
)
from caixa.services_valores_editaveis import (
    formatar_plano_correcao_valores_editaveis,
    resumir_integridade_valores_editaveis,
)


class Command(BaseCommand):
    help = (
        "Executa a validacao operacional completa das obrigacoes financeiras: "
        "contrato de baixa nativa e conciliacao com LancamentoFinanceiro. "
        "O comando e somente leitura."
    )

    def add_arguments(self, parser):
        adicionar_argumentos_filtros_conciliacao(parser)
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o relatorio consolidado em JSON para automacoes.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro se houver inconsistencia de contrato ou divergencia de conciliacao.",
        )
        parser.add_argument(
            "--falhar-com-inconsistencia",
            action="store_true",
            help="Retorna erro quando o contrato de baixa estiver inconsistente.",
        )
        parser.add_argument(
            "--falhar-com-divergencia",
            action="store_true",
            help="Retorna erro quando houver divergencia de conciliacao.",
        )
        parser.add_argument(
            "--validar-canonico",
            action="store_true",
            help="Inclui validacao da modelagem financeira canonica no pre-flight.",
        )
        parser.add_argument(
            "--falhar-com-paridade-canonica",
            action="store_true",
            help="Retorna erro quando a modelagem canonica nao estiver em paridade.",
        )
        parser.add_argument(
            "--validar-escrita-canonica",
            action="store_true",
            help="Inclui validacao da prontidao para escrita canonica.",
        )
        parser.add_argument(
            "--falhar-com-escrita-canonica",
            action="store_true",
            help="Retorna erro quando a prontidao de escrita canonica estiver inconsistente.",
        )
        parser.add_argument(
            "--canonical-limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias canonicas retornadas.",
        )
        parser.add_argument(
            "--validar-valores-editaveis",
            action="store_true",
            help=(
                "Inclui auditoria somente leitura da integridade de valores "
                "editaveis e seus efeitos derivados."
            ),
        )
        parser.add_argument(
            "--falhar-com-valores-editaveis",
            action="store_true",
            help=(
                "Retorna erro quando houver valores editaveis com efeitos "
                "derivados desatualizados."
            ),
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

    def handle(self, *args, **options):
        resultado = validar_operacao_obrigacoes(options)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        contrato_inconsistente = not resultado["contract"]["consistent"]
        conciliacao_divergente = resultado["reconciliation"]["hasDivergences"]
        canonico_inconsistente = (
            resultado["canonicalModeling"]["checked"]
            and not resultado["canonicalModeling"]["consistent"]
        )
        escrita_canonica_inconsistente = (
            resultado["canonicalWriteReadiness"]["checked"]
            and not resultado["canonicalWriteReadiness"]["ready"]
        )
        valores_editaveis_inconsistentes = (
            resultado["editableValuesIntegrity"]["checked"]
            and not resultado["editableValuesIntegrity"]["consistent"]
        )

        if contrato_inconsistente and (
            options["falhar"] or options["falhar_com_inconsistencia"]
        ):
            raise CommandError(
                f"{len(resultado['contract']['inconsistencies'])} "
                "inconsistencia(s) no contrato de baixa: "
                f"{formatar_primeira_inconsistencia_contrato(resultado['contract'])}"
            )

        if conciliacao_divergente and (
            options["falhar"] or options["falhar_com_divergencia"]
        ):
            raise CommandError(
                f"{resultado['reconciliation']['divergentCount']} "
                "divergencia(s) de conciliacao encontrada(s): "
                f"{formatar_primeira_divergencia_conciliacao(resultado['reconciliation'])}"
            )

        if canonico_inconsistente and (
            options["falhar"] or options["falhar_com_paridade_canonica"]
        ):
            total = resultado["canonicalModeling"]["totalIssues"]
            raise CommandError(
                f"{total} inconsistencia(s) de paridade canonica encontrada(s): "
                f"{formatar_primeira_issue_canonica(resultado['canonicalModeling'])}"
            )

        if escrita_canonica_inconsistente and (
            options["falhar"] or options["falhar_com_escrita_canonica"]
        ):
            total = resultado["canonicalWriteReadiness"]["totalIssues"]
            raise CommandError(
                f"{total} inconsistencia(s) de escrita canonica encontrada(s): "
                f"{formatar_primeira_issue_escrita_canonica(resultado['canonicalWriteReadiness'])}"
            )

        if valores_editaveis_inconsistentes and (
            options["falhar"] or options["falhar_com_valores_editaveis"]
        ):
            total = resultado["editableValuesIntegrity"]["totalIssues"]
            raise CommandError(
                f"{total} inconsistencia(s) de valores editaveis encontrada(s): "
                f"{formatar_primeira_issue_valores_editaveis(resultado['editableValuesIntegrity'])}"
            )

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "Validacao operacional de obrigacoes concluida: ambiente pronto."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Validacao operacional de obrigacoes concluida com pontos de atencao."
                )
            )

        contrato = resultado["contract"]
        conciliacao = resultado["reconciliation"]
        canonico = resultado["canonicalModeling"]
        escrita_canonica = resultado["canonicalWriteReadiness"]
        valores_editaveis = resultado["editableValuesIntegrity"]

        if contrato["consistent"]:
            self.stdout.write("Contrato: consistente.")
        else:
            self.stdout.write(
                f"Contrato: {len(contrato['inconsistencies'])} inconsistencia(s)."
            )
            for inconsistencia in contrato["inconsistencies"]:
                self.stdout.write(f"- {inconsistencia}")

        if not conciliacao["hasDivergences"]:
            self.stdout.write("Conciliacao: nenhuma divergencia encontrada.")
        else:
            self.stdout.write(
                f"Conciliacao: {conciliacao['divergentCount']} divergencia(s) encontrada(s)."
            )
            resumo = conciliacao["summary"]
            self.stdout.write(
                "Resumo: "
                f"origem={self._formatar_valor(resumo['realizedAmount'])}; "
                f"ledger={self._formatar_valor(resumo['ledgerRealizedAmount'])}; "
                f"diferenca={self._formatar_valor(resumo['realizedAmountDifference'])}"
            )
            self._imprimir_fila_divergencias(resumo.get("reconciliationWorklist", []))

            for item in conciliacao["items"]:
                orientacao = (item.get("reconciliationGuidance") or {}).get("title") or "-"
                self.stdout.write(
                    "- "
                    f"{item['source']}#{item['sourceId']} "
                    f"{item['description']} "
                    f"origem={self._formatar_valor(item['realizedAmount'])} "
                    f"ledger={self._formatar_valor(item['ledgerRealizedAmount'])} "
                    f"dif={self._formatar_valor(item['realizedAmountDifference'])} "
                    f"diagnostico={item.get('reconciliationDiagnosisLabel') or '-'} "
                    f"orientacao={orientacao}"
                )

        self._imprimir_status_leitura_obrigacoes(conciliacao["readModelStatus"])

        if not canonico["checked"]:
            self.stdout.write("Modelagem canonica: nao validada nesta execucao.")
        elif canonico["consistent"]:
            self.stdout.write("Modelagem canonica: paridade consistente.")
        else:
            resumo = canonico["summary"]
            self.stdout.write(
                "Modelagem canonica: "
                f"{canonico['totalIssues']} inconsistencia(s) de paridade."
            )
            self.stdout.write(
                "Resumo canonico: "
                f"esperado={resumo['expected']}; "
                f"existente={resumo['existing']}; "
                f"ausente={resumo['missing']}; "
                f"divergente={resumo['divergent']}; "
                f"extra={resumo['extra']}"
            )

            for issue in canonico["issues"]:
                self.stdout.write(
                    "- "
                    f"{issue['tipo']} "
                    f"{issue['chave']}: "
                    f"{issue['mensagem']}"
                )

        self._imprimir_prontidao_escrita_canonica(escrita_canonica)
        self._imprimir_integridade_valores_editaveis(valores_editaveis)

    def _imprimir_integridade_valores_editaveis(self, valores_editaveis):
        if not valores_editaveis["checked"]:
            self.stdout.write("Valores editaveis: nao validados nesta execucao.")
            return

        if valores_editaveis["consistent"]:
            self.stdout.write("Valores editaveis: efeitos derivados consistentes.")
            return

        self.stdout.write(
            "Valores editaveis: "
            f"{valores_editaveis['totalIssues']} inconsistencia(s)."
        )
        self._imprimir_filtros_valores_editaveis(valores_editaveis["filters"])
        resumo = valores_editaveis["summary"]
        self.stdout.write(
            "Resumo valores editaveis: "
            f"dividas={resumo['debts']}; "
            f"eventos={resumo['events']}; "
            f"orcamentosAprovados={resumo['approvedBudgets']}"
        )
        for issue in valores_editaveis["issues"]:
            self.stdout.write(
                "- "
                f"{issue['scope']}:{issue['objectId']} "
                f"{issue['code']}: "
                f"{issue['message']}"
            )
        for linha in formatar_plano_correcao_valores_editaveis(
            valores_editaveis["correctionPlan"]
        ):
            self.stdout.write(linha)

    def _imprimir_filtros_valores_editaveis(self, filtros):
        escopos = filtros.get("scopes") or []
        object_ids = filtros.get("objectIds") or []
        if escopos == ["divida", "evento", "orcamento"] and not object_ids:
            return

        self.stdout.write(
            "Filtros valores editaveis: "
            f"escopos={', '.join(escopos) or '-'}; "
            f"objectIds={', '.join(str(item) for item in object_ids) or '-'}"
        )

    def _imprimir_prontidao_escrita_canonica(self, escrita_canonica):
        if not escrita_canonica["checked"]:
            self.stdout.write("Escrita canonica: nao validada nesta execucao.")
            return

        if escrita_canonica["ready"]:
            self.stdout.write(
                "Escrita canonica: adapters transicionais consistentes."
            )
        else:
            self.stdout.write(
                "Escrita canonica: "
                f"{escrita_canonica['totalIssues']} inconsistencia(s)."
            )
            for issue in escrita_canonica["issues"]:
                self.stdout.write(f"- {issue}")

        self.stdout.write(
            "Escrita canonica: canonical-first "
            + self._status_canonical_first(escrita_canonica)
        )
        self.stdout.write(
            "Escrita canonica: feature flag "
            + ("ligada." if escrita_canonica["featureFlagEnabled"] else "desligada.")
        )
        self.stdout.write(
            "Escrita canonica: origens canonical-first habilitadas: "
            + ", ".join(escrita_canonica["enabledCanonicalFirstSources"] or ["-"])
        )

    def _status_canonical_first(self, escrita_canonica):
        if escrita_canonica["canonicalFirstReady"]:
            return "pronto."

        fontes_habilitadas = escrita_canonica.get("enabledCanonicalFirstSources") or []
        if escrita_canonica.get("featureFlagEnabled") and fontes_habilitadas:
            return "ativo para: " + ", ".join(fontes_habilitadas) + "."

        return "ainda nao ativo."

    def _imprimir_fila_divergencias(self, grupos):
        if not grupos:
            return

        self.stdout.write("Fila de divergencias:")
        for grupo in grupos:
            orientacao = (grupo.get("guidance") or {}).get("title") or "-"
            self.stdout.write(
                "* "
                f"diagnostico={grupo.get('reconciliationDiagnosisLabel') or '-'} "
                f"origem={grupo.get('sourceLabel') or grupo.get('source') or '-'} "
                f"contrato={grupo.get('contractCode') or 'sem contrato'} "
                f"cliente={grupo.get('clientName') or 'sem cliente'} "
                f"itens={grupo.get('divergentCount') or 0} "
                f"dif={self._formatar_valor(grupo.get('realizedAmountDifference'))} "
                f"orientacao={orientacao}"
            )

    def _formatar_valor(self, valor):
        return f"{float(valor or 0):.2f}"

    def _imprimir_status_leitura_obrigacoes(self, leitura):
        self.stdout.write(formatar_status_leitura_obrigacoes(leitura))


def validar_operacao_obrigacoes(options=None):
    options = options or {}
    contrato = validar_contrato_baixa_obrigacoes()
    filtros = montar_filtros_conciliacao_obrigacoes(options)
    conciliacao = validar_conciliacao_obrigacoes(filtros)
    conciliacao_publica = serializar_conciliacao_operacional(conciliacao)
    canonico = validar_modelagem_canonica_operacional(options)
    escrita_canonica = validar_prontidao_escrita_canonica_operacional(options)
    valores_editaveis = validar_integridade_valores_editaveis_operacional(options)

    return {
        "ready": (
            contrato["consistent"]
            and not conciliacao["hasDivergences"]
            and (not canonico["checked"] or canonico["consistent"])
            and (not escrita_canonica["checked"] or escrita_canonica["ready"])
            and (
                not valores_editaveis["checked"]
                or valores_editaveis["consistent"]
            )
        ),
        "contract": contrato,
        "reconciliation": conciliacao_publica,
        "canonicalModeling": canonico,
        "canonicalWriteReadiness": escrita_canonica,
        "editableValuesIntegrity": valores_editaveis,
        "filters": filtros,
    }


def serializar_conciliacao_operacional(conciliacao):
    return {
        chave: valor
        for chave, valor in conciliacao.items()
        if chave != "data"
    }


def validar_modelagem_canonica_operacional(options):
    deve_validar = bool(
        options.get("validar_canonico")
        or options.get("falhar_com_paridade_canonica")
    )
    if not deve_validar:
        return {
            "checked": False,
            "consistent": None,
            "summary": {},
            "issues": [],
            "totalIssues": 0,
        }

    resultado = verificar_paridade_modelagem_financeira_canonica(
        limit=options.get("canonical_limit") or 20,
    )
    resumo = _resumo_paridade_canonica(resultado)
    return {
        "checked": True,
        "consistent": resultado["consistent"],
        "summary": resumo,
        "issues": resultado["issues"],
        "totalIssues": resumo["missing"] + resumo["divergent"] + resumo["extra"],
        "groups": {
            "obrigacoes": resultado["obrigacoes"],
            "baixas": resultado["baixas"],
            "alocacoes": resultado["alocacoes"],
        },
    }


def validar_prontidao_escrita_canonica_operacional(options):
    deve_validar = bool(
        options.get("validar_escrita_canonica")
        or options.get("falhar_com_escrita_canonica")
    )
    if not deve_validar:
        return {
            "checked": False,
            "ready": None,
            "canonicalFirstReady": None,
            "featureFlagEnabled": False,
            "featureFlagSources": [],
            "enabledCanonicalFirstSources": [],
            "directCanonicalFirstSources": [],
            "invalidFeatureFlagSources": [],
            "issues": [],
            "totalIssues": 0,
            "adapters": {},
        }

    resultado = verificar_prontidao_escrita_canonica()
    return {
        "checked": True,
        "ready": resultado["ready"],
        "canonicalFirstReady": resultado["canonicalFirstReady"],
        "featureFlagEnabled": resultado["featureFlagEnabled"],
        "featureFlagSources": resultado["featureFlagSources"],
        "enabledCanonicalFirstSources": resultado["enabledCanonicalFirstSources"],
        "directCanonicalFirstSources": resultado["directCanonicalFirstSources"],
        "invalidFeatureFlagSources": resultado["invalidFeatureFlagSources"],
        "issues": resultado["inconsistencies"],
        "totalIssues": len(resultado["inconsistencies"]),
        "currentWriteMode": resultado["currentWriteMode"],
        "targetWriteMode": resultado["targetWriteMode"],
        "adapters": resultado["adapters"],
    }


def validar_integridade_valores_editaveis_operacional(options):
    deve_validar = bool(
        options.get("validar_valores_editaveis")
        or options.get("falhar_com_valores_editaveis")
    )
    return resumir_integridade_valores_editaveis(
        validar=deve_validar,
        limit=options.get("valores_editaveis_limit") or 20,
        escopos=options.get("valores_editaveis_escopo") or None,
        object_ids=options.get("valores_editaveis_object_ids") or None,
    )


def _resumo_paridade_canonica(resultado):
    grupos = (resultado["obrigacoes"], resultado["baixas"], resultado["alocacoes"])
    return {
        "expected": sum(grupo["expected"] for grupo in grupos),
        "existing": sum(grupo["existing"] for grupo in grupos),
        "missing": sum(grupo["missing"] for grupo in grupos),
        "divergent": sum(grupo["divergent"] for grupo in grupos),
        "extra": sum(grupo["extra"] for grupo in grupos),
    }


def formatar_primeira_inconsistencia_contrato(contrato):
    inconsistencias = contrato.get("inconsistencies") or []
    return inconsistencias[0] if inconsistencias else "consulte o relatorio detalhado."


def formatar_primeira_divergencia_conciliacao(conciliacao):
    itens = conciliacao.get("items") or []
    if not itens:
        return "consulte o relatorio detalhado."
    item = itens[0]
    return (
        f"{item.get('source')}#{item.get('sourceId')} "
        f"{item.get('description') or '-'} "
        f"dif={item.get('realizedAmountDifference')}"
    )


def formatar_primeira_issue_canonica(canonico):
    issues = canonico.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."
    issue = issues[0]
    return f"{issue['tipo']} {issue['chave']}: {issue['mensagem']}"


def formatar_primeira_issue_escrita_canonica(escrita_canonica):
    issues = escrita_canonica.get("issues") or []
    return issues[0] if issues else "consulte o relatorio detalhado."


def formatar_primeira_issue_valores_editaveis(valores_editaveis):
    issues = valores_editaveis.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."
    issue = issues[0]
    return (
        f"{issue['scope']}:{issue['objectId']} "
        f"{issue['code']}: {issue['message']}"
    )
