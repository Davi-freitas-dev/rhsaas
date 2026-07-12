import json

from django.core.management.base import BaseCommand
from django.db.models import F

from caixa.models import OrcamentoItem, Servico


class Command(BaseCommand):
    help = (
        "Audita, sem alterar dados, itens diarios cujos snapshots historicos "
        "diferem dos parametros atuais do servico."
    )

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        limit = max(options["limit"], 0)
        queryset = (
            OrcamentoItem.objects
            .select_related("orcamento", "servico")
            .filter(unidade_cobranca_usada=Servico.UNIDADE_COBRANCA_DIARIA)
            .exclude(
                horas_base_diaria_usada=F("servico__horas_base_diaria"),
                percentual_hora_extra_usado=F("servico__percentual_hora_extra"),
            )
            .order_by("id")
        )
        total = queryset.count()
        items = [
            {
                "budgetId": item.orcamento_id,
                "budgetNumber": item.orcamento.numero,
                "itemId": item.id,
                "serviceId": item.servico_id,
                "serviceName": item.servico.nome,
                "baseHoursUsed": item.horas_base_diaria_usada,
                "currentBaseHours": item.servico.horas_base_diaria,
                "overtimePercentUsed": f"{item.percentual_hora_extra_usado:.2f}",
                "currentOvertimePercent": f"{item.servico.percentual_hora_extra:.2f}",
                "serviceCostAmount": f"{item.custo_servico_total:.2f}",
            }
            for item in queryset[:limit]
        ]

        if options["json"]:
            self.stdout.write(json.dumps({
                "totalPotentialDivergences": total,
                "returned": len(items),
                "items": items,
            }, ensure_ascii=False))
            return

        self.stdout.write(f"Itens diarios com snapshots divergentes: {total}")
        for item in items:
            self.stdout.write(
                "Item {itemId} / orçamento {budgetNumber}: "
                "base {baseHoursUsed}->{currentBaseHours}, "
                "extra {overtimePercentUsed}->{currentOvertimePercent}".format(**item)
            )
