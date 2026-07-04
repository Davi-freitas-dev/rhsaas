import json

from django.core.management.base import BaseCommand, CommandError

from caixa.services_valores_editaveis import (
    formatar_plano_correcao_valores_editaveis,
    verificar_integridade_valores_editaveis,
)


class Command(BaseCommand):
    help = (
        "Verifica se valores editaveis substituem os valores antigos em "
        "parcelas, eventos, receitas e custos derivados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--corrigir",
            action="store_true",
            help="Aplica sincronizacoes seguras para corrigir divergencias.",
        )
        parser.add_argument(
            "--falhar-com-inconsistencia",
            action="store_true",
            help="Retorna erro quando houver inconsistencia restante.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Exibe o resultado em JSON.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias exibidas.",
        )
        parser.add_argument(
            "--escopo",
            "--scope",
            action="append",
            choices=["divida", "evento", "orcamento"],
            default=[],
            help="Limita a auditoria a um escopo especifico.",
        )
        parser.add_argument(
            "--object-id",
            "--objeto-id",
            dest="object_ids",
            action="append",
            type=int,
            default=[],
            help="Limita a auditoria/correcao a um ID especifico do escopo.",
        )

    def handle(self, *args, **options):
        limit = max(options["limit"], 1)
        resultado = verificar_integridade_valores_editaveis(
            corrigir=options["corrigir"],
            limit=limit,
            escopos=options["escopo"],
            object_ids=options["object_ids"],
        )

        if options["json"]:
            self.stdout.write(json.dumps(resultado, indent=2, default=str))
        else:
            self._imprimir_resultado(resultado)

        if (
            options["falhar_com_inconsistencia"]
            and resultado["remaining"]["totalIssues"]
        ):
            primeira_inconsistencia = formatar_primeira_inconsistencia(
                resultado["remaining"]
            )
            raise CommandError(
                f"{resultado['remaining']['totalIssues']} inconsistencia(s) "
                "de valores editaveis encontrada(s): "
                f"{primeira_inconsistencia}"
            )

    def _imprimir_resultado(self, resultado):
        modo = "aplicacao" if resultado["apply"] else "somente leitura"
        restantes = resultado["remaining"]
        inicial = resultado["initial"]

        self.stdout.write("Auditoria de valores editaveis concluida.")
        self.stdout.write(f"Modo: {modo}")
        self._imprimir_filtros(resultado["filters"])
        self.stdout.write(
            "Verificados: "
            f"dividas={restantes['checked']['debts']}; "
            f"eventos={restantes['checked']['events']}; "
            f"orcamentosAprovados={restantes['checked']['approvedBudgets']}"
        )
        self.stdout.write(
            "Inconsistencias: "
            f"iniciais={inicial['totalIssues']}; "
            f"restantes={restantes['totalIssues']}; "
            f"correcoesAplicadas={resultado['correctionsApplied']}; "
            f"correcoesBloqueadas={resultado['correctionsBlocked']}"
        )

        if not restantes["issues"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "Nenhuma inconsistencia de valores editaveis encontrada."
                )
            )
            return

        self.stdout.write("Inconsistencias restantes:")
        for issue in restantes["issues"]:
            self.stdout.write(
                f"- {issue['scope']}:{issue['objectId']} "
                f"{issue['code']}: {issue['message']}"
            )
        self._imprimir_plano_correcao(resultado["correctionPlan"])

    def _imprimir_filtros(self, filtros):
        escopos = filtros.get("scopes") or []
        object_ids = filtros.get("objectIds") or []
        if escopos == ["divida", "evento", "orcamento"] and not object_ids:
            return

        self.stdout.write(
            "Filtros: "
            f"escopos={', '.join(escopos) or '-'}; "
            f"objectIds={', '.join(str(item) for item in object_ids) or '-'}"
        )

    def _imprimir_plano_correcao(self, plano):
        for linha in formatar_plano_correcao_valores_editaveis(plano):
            self.stdout.write(linha)


def formatar_primeira_inconsistencia(restantes):
    issues = restantes.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."
    issue = issues[0]
    return (
        f"{issue['scope']}:{issue['objectId']} "
        f"{issue['code']}: {issue['message']}"
    )
