import json

from django.core.management.base import BaseCommand

from caixa.services_modelagem_canonica import (
    sincronizar_modelagem_financeira_canonica,
)
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Sincroniza a modelagem financeira canonica a partir das origens "
        "legadas e do ledger. Por padrao roda em modo somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Grava obrigacoes, baixas e alocacoes canonicas.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema(
            "sincronizar_modelagem_financeira_canonica",
            action="sincronizar dados operacionais",
        )
        resultado = sincronizar_modelagem_financeira_canonica(
            aplicar=options["aplicar"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
            return

        modo = "aplicacao" if resultado["aplicar"] else "somente leitura"
        self.stdout.write("Sincronizacao da modelagem financeira canonica concluida.")
        self.stdout.write(f"Modo: {modo}")
        self.stdout.write(
            "Obrigacoes: "
            f"criadas={resultado['obrigacoes']['criadas']}; "
            f"atualizadas={resultado['obrigacoes']['atualizadas']}"
        )
        self.stdout.write(
            "Baixas: "
            f"criadas={resultado['baixas']['criadas']}; "
            f"atualizadas={resultado['baixas']['atualizadas']}"
        )
        self.stdout.write(
            "Alocacoes: "
            f"criadas={resultado['alocacoes']['criadas']}; "
            f"atualizadas={resultado['alocacoes']['atualizadas']}; "
            f"semObrigacao={resultado['alocacoes']['semObrigacao']}"
        )
