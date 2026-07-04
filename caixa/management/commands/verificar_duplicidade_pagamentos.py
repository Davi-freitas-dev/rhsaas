import json
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from caixa.models_dividas import PagamentoParcelaDivida
from caixa.models_pagamentos import (
    PagamentoEventoCustoExtra,
    PagamentoEventoCustoServico,
)


class Command(BaseCommand):
    help = (
        "Verifica possiveis pagamentos duplicados por origem, data, valor, "
        "tipo, descricao e observacao. O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--origem",
            "--source",
            action="append",
            choices=["custo_servico", "custo_extra", "parcela_divida"],
            default=[],
            help="Limita a verificacao a uma origem de pagamento.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Quantidade maxima de grupos duplicados exibidos.",
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
            help="Retorna erro quando houver duplicidade suspeita.",
        )

    def handle(self, *args, **options):
        resultado = verificar_duplicidade_pagamentos(
            origens=options["origem"],
            limit=options["limit"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir(resultado)

        if options["falhar"] and resultado["duplicateGroupCount"] > 0:
            raise CommandError(
                f"{resultado['duplicateGroupCount']} grupo(s) de pagamento "
                "duplicado encontrado(s)."
            )

    def _imprimir(self, resultado):
        if resultado["duplicateGroupCount"] == 0:
            self.stdout.write("Nenhuma duplicidade suspeita de pagamento encontrada.")
            return

        self.stdout.write(
            "Duplicidades suspeitas de pagamento encontradas: "
            f"{resultado['duplicateGroupCount']} grupo(s)."
        )
        for grupo in resultado["groups"]:
            ids = ", ".join(str(item) for item in grupo["paymentIds"])
            self.stdout.write(
                f"- {grupo['source']} {grupo['sourceLabel']} "
                f"tipo={grupo['type'] or '-'} data={grupo['paymentDate']} "
                f"valor={grupo['amount']} ids={ids}"
            )


def verificar_duplicidade_pagamentos(origens=None, limit=20):
    origens = origens or ["custo_servico", "custo_extra", "parcela_divida"]
    grupos = []

    if "custo_servico" in origens:
        grupos.extend(_duplicidades_custo_servico())
    if "custo_extra" in origens:
        grupos.extend(_duplicidades_custo_extra())
    if "parcela_divida" in origens:
        grupos.extend(_duplicidades_parcela_divida())

    grupos = sorted(
        grupos,
        key=lambda item: (
            item["source"],
            item["sourceLabel"],
            item["paymentDate"],
            item["amount"],
            item["paymentIds"],
        ),
    )

    return {
        "duplicateGroupCount": len(grupos),
        "groups": grupos[:limit],
        "truncated": len(grupos) > limit,
    }


def _duplicidades_custo_servico():
    pagamentos = (
        PagamentoEventoCustoServico.objects.select_related(
            "custo_servico",
            "custo_servico__evento",
            "custo_servico__servico",
        )
        .order_by("id")
    )
    return _agrupar(
        pagamentos,
        source="custo_servico",
        source_id=lambda pagamento: pagamento.custo_servico_id,
        source_label=lambda pagamento: str(pagamento.custo_servico),
        type_label=lambda pagamento: pagamento.tipo,
        payment_date=lambda pagamento: pagamento.data_pagamento,
        amount=lambda pagamento: pagamento.valor_pagamento,
        description=lambda pagamento: pagamento.descricao,
        notes=lambda pagamento: pagamento.observacao,
    )


def _duplicidades_custo_extra():
    pagamentos = (
        PagamentoEventoCustoExtra.objects.select_related(
            "custo_extra",
            "custo_extra__evento",
        )
        .order_by("id")
    )
    return _agrupar(
        pagamentos,
        source="custo_extra",
        source_id=lambda pagamento: pagamento.custo_extra_id,
        source_label=lambda pagamento: str(pagamento.custo_extra),
        type_label=lambda pagamento: "",
        payment_date=lambda pagamento: pagamento.data_pagamento,
        amount=lambda pagamento: pagamento.valor_pagamento,
        description=lambda pagamento: pagamento.descricao,
        notes=lambda pagamento: pagamento.observacao,
    )


def _duplicidades_parcela_divida():
    pagamentos = (
        PagamentoParcelaDivida.objects.select_related(
            "parcela",
            "parcela__divida",
        )
        .order_by("id")
    )
    return _agrupar(
        pagamentos,
        source="parcela_divida",
        source_id=lambda pagamento: pagamento.parcela_id,
        source_label=lambda pagamento: str(pagamento.parcela),
        type_label=lambda pagamento: pagamento.forma_pagamento,
        payment_date=lambda pagamento: pagamento.data_pagamento,
        amount=lambda pagamento: pagamento.valor_pagamento,
        description=lambda pagamento: "",
        notes=lambda pagamento: pagamento.observacao,
    )


def _agrupar(
    pagamentos,
    source,
    source_id,
    source_label,
    type_label,
    payment_date,
    amount,
    description,
    notes,
):
    grupos = defaultdict(list)
    metadados = {}

    for pagamento in pagamentos:
        chave = (
            source,
            source_id(pagamento),
            _normalizar_texto(type_label(pagamento)),
            payment_date(pagamento).isoformat(),
            f"{amount(pagamento):.2f}",
            _normalizar_texto(description(pagamento)),
            _normalizar_texto(notes(pagamento)),
        )
        grupos[chave].append(pagamento.id)
        metadados[chave] = {
            "source": source,
            "sourceId": source_id(pagamento),
            "sourceLabel": source_label(pagamento),
            "type": type_label(pagamento),
            "paymentDate": payment_date(pagamento).isoformat(),
            "amount": f"{amount(pagamento):.2f}",
            "description": description(pagamento) or "",
            "notes": notes(pagamento) or "",
        }

    duplicidades = []
    for chave, ids in grupos.items():
        if len(ids) <= 1:
            continue
        duplicidade = dict(metadados[chave])
        duplicidade["paymentIds"] = ids
        duplicidade["count"] = len(ids)
        duplicidades.append(duplicidade)

    return duplicidades


def _normalizar_texto(valor):
    return (valor or "").strip().casefold()
