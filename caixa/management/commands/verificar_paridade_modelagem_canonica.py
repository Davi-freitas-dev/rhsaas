import json

from django.core.management.base import BaseCommand, CommandError

from caixa.services_modelagem_canonica import (
    verificar_paridade_modelagem_financeira_canonica,
)
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Verifica a paridade entre origens legadas, ledger e a modelagem "
        "financeira canonica. O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando a paridade canonica nao estiver consistente.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de inconsistencias exibidas.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("verificar_paridade_modelagem_canonica", action="verificar dados operacionais")
        resultado = verificar_paridade_modelagem_financeira_canonica(
            limit=options["limit"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if not resultado["consistent"] and options["falhar"]:
            total = sum(
                grupo["missing"] + grupo["divergent"] + grupo["extra"]
                for grupo in (
                    resultado["obrigacoes"],
                    resultado["baixas"],
                    resultado["alocacoes"],
                )
            )
            primeira_issue = formatar_primeira_issue(resultado)
            raise CommandError(
                f"{total} inconsistencia(s) de paridade canonica encontrada(s): "
                f"{primeira_issue}"
            )

    def _imprimir_relatorio(self, resultado):
        if resultado["consistent"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "Paridade da modelagem financeira canonica consistente."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Paridade da modelagem financeira canonica com pontos de atencao."
                )
            )

        self._imprimir_resumo("Obrigacoes", resultado["obrigacoes"])
        self._imprimir_resumo("Baixas", resultado["baixas"])
        self._imprimir_resumo("Alocacoes", resultado["alocacoes"])

        if not resultado["issues"]:
            return

        self.stdout.write("Inconsistencias:")
        for issue in resultado["issues"]:
            diferencas = issue.get("diferencas") or []
            self.stdout.write(
                "- "
                f"{issue['tipo']} "
                f"{issue['chave']}: "
                f"{issue['mensagem']}"
            )
            for diferenca in diferencas[:5]:
                self.stdout.write(
                    "  * "
                    f"{diferenca['field']}: "
                    f"esperado={diferenca['expected']} "
                    f"atual={diferenca['actual']}"
                )

    def _imprimir_resumo(self, titulo, resumo):
        self.stdout.write(
            f"{titulo}: "
            f"esperado={resumo['expected']}; "
            f"existente={resumo['existing']}; "
            f"ausente={resumo['missing']}; "
            f"divergente={resumo['divergent']}; "
            f"extra={resumo['extra']}"
        )


def formatar_primeira_issue(resultado):
    issues = resultado.get("issues") or []
    if not issues:
        return "consulte o relatorio detalhado."
    issue = issues[0]
    return f"{issue['tipo']} {issue['chave']}: {issue['mensagem']}"
