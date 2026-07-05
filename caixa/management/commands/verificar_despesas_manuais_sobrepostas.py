import json

from django.core.management.base import BaseCommand, CommandError

from caixa.models import DespesaOperacional
from caixa.models_custos_extras import EventoCustoExtra
from caixa.models_servico import EventoCustoServico
from tenancy.command_guards import ensure_tenant_schema


CATEGORIAS_CUSTO_SERVICO = {
    "mao_obra": {
        "tipo": "diarias",
        "campo": "valor_diarias",
    },
    "alimentacao": {
        "tipo": "alimentacao",
        "campo": "valor_alimentacao",
    },
    "transporte": {
        "tipo": "transporte",
        "campo": "valor_transporte",
    },
}


class Command(BaseCommand):
    help = (
        "Lista despesas operacionais manuais sobrepostas a custos estruturados "
        "de servico ou custos extras no mesmo evento. O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--evento-id",
            "--event-id",
            type=int,
            help="Limita a auditoria a um evento especifico.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON.",
        )
        parser.add_argument(
            "--falhar-com-reservada",
            action="store_true",
            help=(
                "Retorna erro quando houver despesa manual com efeito financeiro "
                "usando descricao reservada de custo estruturado."
            ),
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("verificar_despesas_manuais_sobrepostas", action="verificar dados operacionais")
        resultado = verificar_despesas_manuais_sobrepostas(
            evento_id=options["evento_id"],
        )

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir(resultado)

        if (
            options["falhar_com_reservada"]
            and resultado["reservedWithFinancialEffectCount"] > 0
        ):
            raise CommandError(
                f"{resultado['reservedWithFinancialEffectCount']} despesa(s) manual(is) "
                "com efeito financeiro usando descricao reservada de custo estruturado."
            )

    def _imprimir(self, resultado):
        if resultado["manualOverlapCount"] == 0:
            self.stdout.write(
                "Nenhuma despesa manual sobreposta a custo estruturado encontrada."
            )
            return

        self.stdout.write(
            "Despesas manuais sobrepostas a custos estruturados: "
            f"{resultado['manualOverlapCount']} item(ns)."
        )
        self.stdout.write(
            "Descricoes reservadas: "
            f"{resultado['reservedDescriptionCount']}; "
            f"reservadas com efeito financeiro: "
            f"{resultado['reservedWithFinancialEffectCount']}; "
            f"adicionais manuais: {resultado['additionalManualCount']}"
        )
        for item in resultado["items"]:
            marcador = "reservada" if item["usesReservedDescription"] else "manual-adicional"
            impacto = "com-impacto" if item["hasFinancialEffect"] else "sem-impacto"
            self.stdout.write(
                f"- {marcador}/{impacto}: origem={item['structuredSource']} "
                f"evento={item['eventLabel']} "
                f"categoria={item['category']} previsto={item['plannedAmount']} "
                f"pago={item['paidAmount']} descricao={item['description']}"
            )


def verificar_despesas_manuais_sobrepostas(evento_id=None):
    despesas = DespesaOperacional.objects.select_related("evento").filter(
        origem=DespesaOperacional.ORIGEM_MANUAL,
        categoria__in=CATEGORIAS_CUSTO_SERVICO.keys(),
    )
    if evento_id:
        despesas = despesas.filter(evento_id=evento_id)

    items = []
    for despesa in despesas.order_by("evento_id", "categoria", "id"):
        config = CATEGORIAS_CUSTO_SERVICO[despesa.categoria]
        if not _evento_tem_custo_servico(despesa.evento_id, config["campo"]):
            continue

        descricao_reservada = (
            despesa.descricao
            == DespesaOperacional.CUSTOS_SERVICO_DERIVADOS[despesa.categoria][0]
        )
        has_financial_effect = (
            despesa.valor_previsto > 0
            or despesa.valor_pago > 0
        )
        items.append({
            "structuredSource": "custo_servico",
            "expenseId": despesa.id,
            "eventId": despesa.evento_id,
            "eventLabel": str(despesa.evento),
            "category": despesa.categoria,
            "serviceCostType": config["tipo"],
            "description": despesa.descricao,
            "plannedAmount": f"{despesa.valor_previsto:.2f}",
            "paidAmount": f"{despesa.valor_pago:.2f}",
            "usesReservedDescription": descricao_reservada,
            "hasFinancialEffect": has_financial_effect,
        })

    items.extend(_despesas_manuais_sobrepostas_custos_extras(evento_id))

    reserved_count = sum(1 for item in items if item["usesReservedDescription"])
    reserved_with_effect = sum(
        1
        for item in items
        if item["usesReservedDescription"] and item["hasFinancialEffect"]
    )
    return {
        "manualOverlapCount": len(items),
        "reservedDescriptionCount": reserved_count,
        "reservedWithFinancialEffectCount": reserved_with_effect,
        "additionalManualCount": len(items) - reserved_count,
        "items": items,
    }


def _evento_tem_custo_servico(evento_id, campo):
    return EventoCustoServico.objects.filter(
        evento_id=evento_id,
        **{f"{campo}__gt": 0},
    ).exists()


def _despesas_manuais_sobrepostas_custos_extras(evento_id=None):
    despesas = DespesaOperacional.objects.select_related("evento").filter(
        origem=DespesaOperacional.ORIGEM_MANUAL,
        descricao__startswith="Custo extra: ",
    )
    if evento_id:
        despesas = despesas.filter(evento_id=evento_id)

    items = []
    for despesa in despesas.order_by("evento_id", "categoria", "id"):
        descricao_custo = despesa.descricao.removeprefix("Custo extra: ")
        if not EventoCustoExtra.objects.filter(
            evento_id=despesa.evento_id,
            descricao=descricao_custo,
        ).exists():
            continue

        has_financial_effect = (
            despesa.valor_previsto > 0
            or despesa.valor_pago > 0
        )
        items.append({
            "structuredSource": "custo_extra",
            "expenseId": despesa.id,
            "eventId": despesa.evento_id,
            "eventLabel": str(despesa.evento),
            "category": despesa.categoria,
            "serviceCostType": "",
            "description": despesa.descricao,
            "plannedAmount": f"{despesa.valor_previsto:.2f}",
            "paidAmount": f"{despesa.valor_pago:.2f}",
            "usesReservedDescription": True,
            "hasFinancialEffect": has_financial_effect,
        })

    return items
