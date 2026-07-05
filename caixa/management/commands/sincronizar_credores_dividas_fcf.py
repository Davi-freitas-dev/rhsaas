import json

from django.core.management.base import BaseCommand, CommandError

from caixa.services_dividas import sincronizar_credores_dividas_fcf
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Sincroniza o cadastro mestre de credores com o alias textual legado "
        "das dividas FCF. Por padrao roda em modo somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Aplica as correcoes encontradas. Sem este parametro faz apenas dry-run.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON para automacoes.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de itens detalhados retornados no relatorio.",
        )
        parser.add_argument(
            "--falhar-com-pendencia",
            action="store_true",
            help="Retorna erro quando restarem pendencias apos a sincronizacao.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema(
            "sincronizar_credores_dividas_fcf",
            action="sincronizar dados operacionais",
        )
        if options["limit"] < 0:
            raise CommandError("--limit deve ser maior ou igual a 0.")

        resultado = sincronizar_credores_dividas_fcf(
            aplicar=options["aplicar"],
            limit=options["limit"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar_com_pendencia"] and not resultado["consistentAfter"]:
            raise CommandError(formatar_erro_sincronizacao_credores(resultado))

    def _imprimir_relatorio(self, resultado):
        modo = "aplicacao" if resultado["mode"] == "apply" else "somente leitura"
        self.stdout.write(f"Sincronizacao de credores de dividas FCF: modo {modo}.")
        self.stdout.write(
            "Pendencias encontradas: "
            f"{resultado['pendingCount']}; "
            f"corrigidas={resultado['fixed']}; "
            f"corrigiveis={resultado['wouldFix']}; "
            f"sem correcao automatica={resultado['unresolved']}."
        )

        if resultado["consistentAfter"]:
            self.stdout.write(self.style.SUCCESS("Credores de dividas FCF consistentes."))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Credores de dividas FCF ainda possuem pendencias."
                )
            )


def formatar_erro_sincronizacao_credores(resultado):
    itens = resultado.get("items") or []
    if not itens:
        return "Credores de dividas FCF ainda possuem pendencias."

    item = itens[0]
    return (
        "Credores de dividas FCF ainda possuem pendencias: "
        f"tipo={item['issueType']} "
        f"divida={item['debtId']} "
        f"credor_legado={item['legacyCreditor']}"
    )
