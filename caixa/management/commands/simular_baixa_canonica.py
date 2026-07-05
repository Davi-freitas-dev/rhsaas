import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from caixa.services_escrita_canonica import simular_baixa_canonica_primeiro
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Simula uma baixa canonical-first sem gravar dados. "
        "Use para preparar a inversao futura da escrita para BaixaFinanceira."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--source-id", required=True, dest="source_id")
        parser.add_argument("--source-detail", dest="source_detail")
        parser.add_argument("--realized-amount", required=True, dest="realized_amount")
        parser.add_argument("--payment-date", dest="payment_date")
        parser.add_argument(
            "--settle-remaining-balance",
            action="store_true",
            dest="settle_remaining_balance",
        )
        parser.add_argument("--write-off-reason", dest="write_off_reason")
        parser.add_argument("--notes")
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime a simulacao em JSON para automacoes.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema(
            "simular_baixa_canonica",
            action="simular baixa com dados operacionais",
        )
        payload = {
            "sourceDetail": options.get("source_detail"),
            "realizedAmount": options.get("realized_amount"),
            "paymentDate": options.get("payment_date"),
            "settleRemainingBalance": options.get("settle_remaining_balance"),
            "writeOffReason": options.get("write_off_reason"),
            "notes": options.get("notes"),
        }

        try:
            resultado = simular_baixa_canonica_primeiro(
                options["source"],
                options["source_id"],
                payload,
            )
        except ValidationError as exc:
            raise CommandError(_formatar_erro_validacao(exc)) from exc

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
            return

        self._imprimir_relatorio(resultado)

    def _imprimir_relatorio(self, resultado):
        self.stdout.write(
            self.style.SUCCESS("Simulacao de baixa canonical-first concluida.")
        )
        self.stdout.write("Modo: somente leitura")
        self.stdout.write(f"Origem: {resultado['source']}#{resultado['sourceId']}")
        if resultado["sourceDetail"]:
            self.stdout.write(f"Detalhe: {resultado['sourceDetail']}")
        self.stdout.write(f"Obrigacao canonica: {resultado['obligationKey']}")
        self.stdout.write(
            "Baixa simulada: "
            f"valor={resultado['canonicalSettlementDraft']['amount']:.2f}; "
            f"data={resultado['canonicalSettlementDraft']['date'] or '-'}; "
            f"fluxo={resultado['canonicalSettlementDraft']['cashFlowGroup']}"
        )
        self.stdout.write(
            "Adapter legado posterior: "
            f"{resultado['legacyAdapter']['name']} "
            f"({resultado['legacyAdapter']['mode']})"
        )
        self.stdout.write(
            "Escritas no banco: "
            + ("sim" if resultado["effects"]["writesDatabase"] else "nao")
        )


def _formatar_erro_validacao(exc):
    if hasattr(exc, "message_dict"):
        partes = []
        for campo, mensagens in exc.message_dict.items():
            partes.append(f"{campo}: {'; '.join(mensagens)}")
        return "; ".join(partes)

    return "; ".join(exc.messages)
