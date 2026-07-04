import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.contracts_obrigacoes import NATIVE_SETTLEMENT_CAPABILITIES
from caixa.models import ObrigacaoFinanceira
from caixa.services_escrita_canonica import simular_baixa_canonica_primeiro


class Command(BaseCommand):
    help = (
        "Simula baixas canonical-first em lote usando obrigacoes pendentes reais. "
        "O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--payment-date", dest="payment_date")
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime a simulacao em JSON para automacoes.",
        )
        parser.add_argument(
            "--falhar-com-inconsistencia",
            action="store_true",
            help="Retorna erro quando alguma simulacao falhar.",
        )

    def handle(self, *args, **options):
        try:
            resultado = simular_baixas_canonicas_lote(
                source=options.get("source"),
                limit=options.get("limit") or 20,
                payment_date=options.get("payment_date") or timezone.localdate().isoformat(),
            )
        except ValidationError as exc:
            raise CommandError(_formatar_erro_validacao(exc)) from exc

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if resultado["failedCount"] and options["falhar_com_inconsistencia"]:
            raise CommandError(
                f"{resultado['failedCount']} simulacao(oes) canonical-first falharam: "
                f"{formatar_primeira_falha(resultado)}"
            )

    def _imprimir_relatorio(self, resultado):
        if resultado["failedCount"]:
            self.stdout.write(
                self.style.WARNING(
                    f"{resultado['failedCount']} simulacao(oes) com ponto de atencao."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Simulacoes canonical-first em lote consistentes.")
            )

        self.stdout.write("Modo: somente leitura")
        self.stdout.write(
            f"Avaliadas={resultado['evaluatedCount']}; "
            f"sucesso={resultado['successCount']}; "
            f"falhas={resultado['failedCount']}"
        )
        for item in resultado["items"]:
            if item["ok"]:
                self.stdout.write(
                    "- "
                    f"{item['source']}#{item['sourceId']} "
                    f"delta={item['deltaAmount']:.2f} "
                    f"obrigacao={item['obligationKey']}"
                )
            else:
                self.stdout.write(
                    "- "
                    f"{item['source']}#{item['sourceId']} "
                    f"erro={item['error']}"
                )


def simular_baixas_canonicas_lote(source=None, limit=20, payment_date=None):
    source = str(source or "").strip()
    if source and source not in NATIVE_SETTLEMENT_CAPABILITIES:
        raise ValidationError({"source": "Origem nao suporta baixa nativa."})

    limit = max(int(limit or 20), 1)
    query = ObrigacaoFinanceira.objects.filter(
        tipo=ObrigacaoFinanceira.TIPO_PAGAR,
        valor_pendente__gt=0,
        origem__in=NATIVE_SETTLEMENT_CAPABILITIES.keys(),
    ).order_by("origem", "id")
    if source:
        query = query.filter(origem=source)

    itens = []
    for obrigacao in query[:limit]:
        itens.append(simular_item_lote(obrigacao, payment_date))

    failed = [item for item in itens if not item["ok"]]
    return {
        "dryRun": True,
        "writesDatabase": False,
        "filters": {
            "source": source,
            "limit": limit,
            "paymentDate": payment_date,
        },
        "evaluatedCount": len(itens),
        "successCount": len(itens) - len(failed),
        "failedCount": len(failed),
        "items": itens,
    }


def simular_item_lote(obrigacao, payment_date):
    source_id = obter_source_id_obrigacao(obrigacao)
    realized_amount = obrigacao.valor_realizado + min(obrigacao.valor_pendente, 1)
    payload = {
        "sourceDetail": obrigacao.detalhe_origem,
        "realizedAmount": str(realized_amount),
        "paymentDate": payment_date,
    }

    try:
        simulacao = simular_baixa_canonica_primeiro(
            obrigacao.origem,
            source_id,
            payload,
        )
    except ValidationError as exc:
        return {
            "ok": False,
            "source": obrigacao.origem,
            "sourceId": source_id,
            "sourceDetail": obrigacao.detalhe_origem,
            "obligationKey": obrigacao.chave_origem,
            "error": _formatar_erro_validacao(exc),
        }

    return {
        "ok": True,
        "source": simulacao["source"],
        "sourceId": simulacao["sourceId"],
        "sourceDetail": simulacao["sourceDetail"],
        "obligationKey": simulacao["obligationKey"],
        "deltaAmount": simulacao["requested"]["deltaAmount"],
        "wouldCreateCanonicalSettlement": simulacao["effects"][
            "wouldCreateCanonicalSettlement"
        ],
    }


def obter_source_id_obrigacao(obrigacao):
    for field in (
        "despesa_operacional",
        "custo_fixo",
        "evento_custo_servico",
        "evento_custo_extra",
        "parcela_divida",
        "investimento",
        "financiamento_movimentacao",
    ):
        value = getattr(obrigacao, f"{field}_id", None)
        if value:
            return value
    return None


def formatar_primeira_falha(resultado):
    falhas = [item for item in resultado.get("items", []) if not item.get("ok")]
    if not falhas:
        return "consulte o relatorio detalhado."
    item = falhas[0]
    return (
        f"{item.get('source')}#{item.get('sourceId') or '-'} "
        f"obrigacao={item.get('obligationKey') or '-'} "
        f"erro={item.get('error') or '-'}"
    )


def _formatar_erro_validacao(exc):
    if hasattr(exc, "message_dict"):
        partes = []
        for campo, mensagens in exc.message_dict.items():
            partes.append(f"{campo}: {'; '.join(mensagens)}")
        return "; ".join(partes)
    return "; ".join(exc.messages)
