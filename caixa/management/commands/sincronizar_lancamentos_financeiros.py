import json

from django.core.management.base import BaseCommand

from caixa.models import DespesaOperacional, LancamentoFinanceiro, ReceitaOperacional
from caixa.models_custo_fixo import CustoFixo
from caixa.models_dividas import PagamentoParcelaDivida
from caixa.models_fcf import FinanciamentoMovimentacao
from caixa.models_fci import Investimento
from caixa.models_pagamentos import (
    PagamentoEventoCustoExtra,
    PagamentoEventoCustoServico,
)
from caixa.services_lancamentos import (
    sincronizar_lancamento_custo_fixo,
    sincronizar_lancamento_despesa_manual,
    sincronizar_lancamento_financiamento,
    sincronizar_lancamento_investimento,
    sincronizar_lancamento_pagamento_custo_extra,
    sincronizar_lancamento_pagamento_custo_servico,
    sincronizar_lancamento_pagamento_parcela,
    sincronizar_lancamento_receita,
)


ORIGENS_LEDGER = {
    "receita_operacional": {
        "model": ReceitaOperacional,
        "ledger_field": "receita_operacional",
        "sync": sincronizar_lancamento_receita,
    },
    "despesa_operacional": {
        "model": DespesaOperacional,
        "ledger_field": "despesa_operacional",
        "sync": sincronizar_lancamento_despesa_manual,
    },
    "custo_fixo": {
        "model": CustoFixo,
        "ledger_field": "custo_fixo",
        "sync": sincronizar_lancamento_custo_fixo,
    },
    "pagamento_custo_servico": {
        "model": PagamentoEventoCustoServico,
        "ledger_field": "pagamento_custo_servico",
        "sync": sincronizar_lancamento_pagamento_custo_servico,
    },
    "pagamento_custo_extra": {
        "model": PagamentoEventoCustoExtra,
        "ledger_field": "pagamento_custo_extra",
        "sync": sincronizar_lancamento_pagamento_custo_extra,
    },
    "pagamento_parcela_divida": {
        "model": PagamentoParcelaDivida,
        "ledger_field": "pagamento_parcela_divida",
        "sync": sincronizar_lancamento_pagamento_parcela,
    },
    "investimento": {
        "model": Investimento,
        "ledger_field": "investimento",
        "sync": sincronizar_lancamento_investimento,
    },
    "financiamento_movimentacao": {
        "model": FinanciamentoMovimentacao,
        "ledger_field": "financiamento_movimentacao",
        "sync": sincronizar_lancamento_financiamento,
    },
}


class Command(BaseCommand):
    help = (
        "Sincroniza LancamentoFinanceiro a partir das origens operacionais. "
        "Use apos restaurar fixture com loaddata, pois signals raw nao recriam ledger."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Grava/cria/atualiza/remove lancamentos. Sem esta flag, roda somente leitura.",
        )
        parser.add_argument(
            "--origem",
            "--source",
            action="append",
            choices=sorted(ORIGENS_LEDGER.keys()),
            default=[],
            help="Limita a sincronizacao a uma origem especifica.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON.",
        )

    def handle(self, *args, **options):
        resultado = sincronizar_lancamentos_financeiros(
            aplicar=options["aplicar"],
            origens=options["origem"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
            return

        modo = "aplicacao" if resultado["aplicar"] else "somente leitura"
        self.stdout.write("Sincronizacao de lancamentos financeiros concluida.")
        self.stdout.write(f"Modo: {modo}")
        for origem, resumo in resultado["origens"].items():
            self.stdout.write(
                f"- {origem}: verificados={resumo['verificados']}; "
                f"criados={resumo['criados']}; atualizados={resumo['atualizados']}; "
                f"removidos={resumo['removidos']}; ignorados={resumo['ignorados']}"
            )


def sincronizar_lancamentos_financeiros(aplicar=False, origens=None):
    origens_normalizadas = origens or sorted(ORIGENS_LEDGER.keys())
    resultado = {
        "aplicar": aplicar,
        "origens": {},
    }

    for origem in origens_normalizadas:
        config = ORIGENS_LEDGER[origem]
        resultado["origens"][origem] = _sincronizar_origem(config, aplicar)

    return resultado


def _sincronizar_origem(config, aplicar):
    resumo = {
        "verificados": 0,
        "criados": 0,
        "atualizados": 0,
        "removidos": 0,
        "ignorados": 0,
    }
    objetos = config["model"].objects.all().order_by("id")

    for origem in objetos:
        resumo["verificados"] += 1
        if not aplicar:
            continue

        filtro_ledger = {config["ledger_field"]: origem}
        existia = LancamentoFinanceiro.objects.filter(**filtro_ledger).exists()
        lancamento = config["sync"](origem)
        existe_agora = LancamentoFinanceiro.objects.filter(**filtro_ledger).exists()

        if lancamento is None:
            if existia and not existe_agora:
                resumo["removidos"] += 1
            else:
                resumo["ignorados"] += 1
            continue

        if lancamento[1]:
            resumo["criados"] += 1
        else:
            resumo["atualizados"] += 1

    return resumo
