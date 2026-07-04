import json

from django.core.management.base import BaseCommand, CommandError

from caixa.models_dividas import DividaFinanceira
from caixa.models_fcf import FinanciamentoMovimentacao
from caixa.services_dividas_fcf import (
    dados_entrada_fcf_divida,
    movimento_entrada_fcf_desatualizado,
    resumir_integridade_entradas_fcf_dividas,
    sincronizar_entrada_fcf_divida,
)


class Command(BaseCommand):
    help = (
        "Sincroniza entradas FCF automaticas para dividas do tipo emprestimo "
        "ou financiamento."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Aplica criacoes, atualizacoes e remocoes.",
        )
        parser.add_argument(
            "--falhar-com-pendencia",
            action="store_true",
            help="Retorna erro se houver pendencias sem --aplicar.",
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
            help="Quantidade maxima de pendencias detalhadas retornadas.",
        )

    def handle(self, *args, **options):
        aplicar = options["aplicar"]
        limit = options["limit"]
        if limit < 0:
            raise CommandError("--limit deve ser maior ou igual a 0.")

        criadas = atualizadas = removidas = inalteradas = 0
        pendencias = []

        dividas = list(DividaFinanceira.objects.select_related(
            "evento",
            "evento__orcamento",
            "criado_por",
            "atualizado_por",
        ).order_by("id"))
        movimentos_por_divida = FinanciamentoMovimentacao.objects.filter(
            divida_financeira_id__in=[divida.id for divida in dividas],
        ).in_bulk(field_name="divida_financeira_id")

        for divida in dividas:
            dados = dados_entrada_fcf_divida(divida)
            movimento = movimentos_por_divida.get(divida.id)

            if dados is None:
                if movimento is None:
                    inalteradas += 1
                    continue

                removidas += 1
                pendencias.append(f"remover divida:{divida.id}")
                if aplicar:
                    sincronizar_entrada_fcf_divida(divida)
                continue

            if movimento is None:
                criadas += 1
                pendencias.append(f"criar divida:{divida.id}")
                if aplicar:
                    sincronizar_entrada_fcf_divida(divida)
                continue

            if movimento_entrada_fcf_desatualizado(movimento, dados):
                atualizadas += 1
                pendencias.append(f"atualizar divida:{divida.id}")
                if aplicar:
                    sincronizar_entrada_fcf_divida(divida)
                continue

            inalteradas += 1

        modo = "aplicacao" if aplicar else "somente leitura"
        restante = (
            resumir_integridade_entradas_fcf_dividas(limit=limit)
            if aplicar
            else None
        )
        remaining_issues = (
            restante["totalIssues"]
            if restante is not None
            else len(pendencias)
        )

        resultado = {
            "mode": "apply" if aplicar else "dry-run",
            "readOnly": not aplicar,
            "checked": len(dividas),
            "created": criadas,
            "updated": atualizadas,
            "removed": removidas,
            "unchanged": inalteradas,
            "pendingCount": len(pendencias),
            "pending": pendencias[:limit],
            "limit": limit,
            "remainingIssues": remaining_issues,
            "consistentAfter": remaining_issues == 0,
        }

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write("Sincronizacao de entradas FCF por dividas concluida.")
            self.stdout.write(f"Modo: {modo}")
            self.stdout.write(
                "Entradas FCF: "
                f"criadas={criadas}; atualizadas={atualizadas}; "
                f"removidas={removidas}; inalteradas={inalteradas}"
            )

            if pendencias and not aplicar:
                self.stdout.write("Pendencias:")
                for pendencia in pendencias[:limit]:
                    self.stdout.write(f"- {pendencia}")

        if options["falhar_com_pendencia"] and not resultado["consistentAfter"]:
            raise CommandError(
                f"{resultado['remainingIssues']} pendencia(s) de entrada FCF por divida."
            )
