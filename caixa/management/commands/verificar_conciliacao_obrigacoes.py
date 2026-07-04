import json

from django.core.management.base import BaseCommand, CommandError

from caixa.serializers_obrigacoes import (
    formatar_status_leitura_obrigacoes,
    montar_payload_obrigacoes_financeiras_api,
    resumir_status_leitura_obrigacoes_meta,
)


CONCILIACAO_FILTER_ALIASES = (
    ("data_inicial", "startDate"),
    ("data_final", "endDate"),
    ("contract_code", "contractCode"),
    ("contrato_codigo", "contrato_codigo"),
    ("event_id", "eventId"),
    ("evento", "eventId"),
    ("evento_id", "eventId"),
    ("client_id", "clientId"),
    ("cliente", "clientId"),
    ("cliente_id", "clientId"),
    ("source", "source"),
    ("origem", "source"),
    ("cash_flow_group", "cashFlowGroup"),
    ("fluxo", "cashFlowGroup"),
    ("settlement_status", "settlementStatus"),
    ("situacao", "settlementStatus"),
    ("reconciliation_diagnosis", "reconciliationDiagnosis"),
    ("diagnostico_conciliacao", "reconciliationDiagnosis"),
    ("diagnostico", "reconciliationDiagnosis"),
    ("search", "search"),
    ("busca", "search"),
)


class Command(BaseCommand):
    help = (
        "Verifica divergencias de conciliacao entre obrigacoes financeiras "
        "e LancamentoFinanceiro. O comando e somente leitura."
    )

    def add_arguments(self, parser):
        adicionar_argumentos_filtros_conciliacao(parser)
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o payload serializado para automacoes.",
        )
        parser.add_argument(
            "--falhar-com-divergencia",
            action="store_true",
            help="Retorna erro quando houver divergencia, util para CI/rotinas.",
        )

    def handle(self, *args, **options):
        filtros = montar_filtros_conciliacao_obrigacoes(options)
        resultado = validar_conciliacao_obrigacoes(filtros)
        dados = resultado["data"]
        total_divergencias = resultado["divergentCount"]

        if options["json_output"]:
            self.stdout.write(json.dumps(dados, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(dados)

        if total_divergencias and options["falhar_com_divergencia"]:
            raise CommandError(
                f"{total_divergencias} divergencia(s) de conciliacao encontrada(s): "
                f"{formatar_primeira_divergencia(dados)}"
            )

    def _imprimir_relatorio(self, dados):
        resumo = dados["summary"]
        paginacao = dados["pagination"]
        total = paginacao["total"]
        self._imprimir_status_leitura(dados["meta"])

        if not total:
            self.stdout.write(
                self.style.SUCCESS("Nenhuma divergencia de conciliacao encontrada.")
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"{total} divergencia(s) de conciliacao encontrada(s)."
            )
        )
        self.stdout.write(
            "Resumo: "
            f"origem={self._formatar_valor(resumo['realizedAmount'])}; "
            f"ledger={self._formatar_valor(resumo['ledgerRealizedAmount'])}; "
            f"diferenca={self._formatar_valor(resumo['realizedAmountDifference'])}"
        )
        self._imprimir_fila_divergencias(resumo.get("reconciliationWorklist", []))

        for item in dados["items"]:
            contexto = self._formatar_contexto(item)
            orientacao = (item.get("reconciliationGuidance") or {}).get("title") or "-"
            self.stdout.write(
                "- "
                f"{item['source']}#{item['sourceId']} "
                f"{item['description']} "
                f"venc={item['dueDate'] or '-'} "
                f"origem={self._formatar_valor(item['realizedAmount'])} "
                f"ledger={self._formatar_valor(item['ledgerRealizedAmount'])} "
                f"dif={self._formatar_valor(item['realizedAmountDifference'])} "
                f"diagnostico={item.get('reconciliationDiagnosisLabel') or '-'} "
                f"orientacao={orientacao}"
                f"{contexto}"
            )

        if paginacao["hasMore"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Exibindo {len(dados['items'])} de {total}. Use --limit para ampliar."
                )
            )

    def _formatar_contexto(self, item):
        partes = []
        if item.get("contractCode"):
            partes.append(f"contrato={item['contractCode']}")
        if item.get("eventName"):
            partes.append(f"evento={item['eventName']}")
        if item.get("sourceDetailLabel"):
            partes.append(f"detalhe={item['sourceDetailLabel']}")

        return f" ({'; '.join(partes)})" if partes else ""

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

    def _imprimir_status_leitura(self, meta):
        leitura = resumir_status_leitura_obrigacoes_meta(meta)
        self.stdout.write(formatar_status_leitura_obrigacoes(leitura))


def adicionar_argumentos_filtros_conciliacao(parser):
    parser.add_argument("--data-inicial", dest="data_inicial")
    parser.add_argument("--data-final", dest="data_final")
    parser.add_argument("--contract-code", dest="contract_code")
    parser.add_argument("--contrato-codigo", dest="contrato_codigo")
    parser.add_argument("--event-id", dest="event_id")
    parser.add_argument("--evento", dest="evento")
    parser.add_argument("--evento-id", dest="evento_id")
    parser.add_argument("--client-id", dest="client_id")
    parser.add_argument("--cliente", dest="cliente")
    parser.add_argument("--cliente-id", dest="cliente_id")
    parser.add_argument("--source", dest="source")
    parser.add_argument("--origem", dest="origem")
    parser.add_argument("--cash-flow-group", dest="cash_flow_group")
    parser.add_argument("--fluxo", dest="fluxo")
    parser.add_argument("--settlement-status", dest="settlement_status")
    parser.add_argument("--situacao", dest="situacao")
    parser.add_argument("--reconciliation-diagnosis", dest="reconciliation_diagnosis")
    parser.add_argument("--diagnostico-conciliacao", dest="diagnostico_conciliacao")
    parser.add_argument("--diagnostico", dest="diagnostico")
    parser.add_argument("--search", dest="search")
    parser.add_argument("--busca", dest="busca")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Quantidade maxima de divergencias exibidas no relatorio.",
    )


def montar_filtros_conciliacao_obrigacoes(options):
    filtros = {
        "reconciliationStatus": "divergente",
        "dataSource": "legacy",
        "limit": max(int(options.get("limit") or 20), 1),
    }

    for option_name, filter_name in CONCILIACAO_FILTER_ALIASES:
        valor = options.get(option_name)
        if valor not in (None, ""):
            filtros[filter_name] = str(valor)

    return filtros


def validar_conciliacao_obrigacoes(filtros=None):
    filtros_normalizados = {"reconciliationStatus": "divergente", "limit": 20}
    if filtros:
        filtros_normalizados.update(filtros)

    payload = montar_payload_obrigacoes_financeiras_api(filtros_normalizados)
    dados = payload["data"]
    total_divergencias = dados["pagination"]["total"]

    return {
        "hasDivergences": bool(total_divergencias),
        "divergentCount": total_divergencias,
        "readModelStatus": resumir_status_leitura_obrigacoes_meta(dados["meta"]),
        "summary": dados["summary"],
        "items": dados["items"],
        "pagination": dados["pagination"],
        "filters": filtros_normalizados,
        "data": dados,
    }


def formatar_primeira_divergencia(dados):
    itens = dados.get("items") or []
    if not itens:
        return "consulte o relatorio detalhado."
    item = itens[0]
    return (
        f"{item.get('source')}#{item.get('sourceId')} "
        f"{item.get('description') or '-'} "
        f"dif={item.get('realizedAmountDifference')}"
    )
