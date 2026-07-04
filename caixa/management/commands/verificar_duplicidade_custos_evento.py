import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from caixa.models_servico import EventoCustoServico


class Command(BaseCommand):
    help = (
        "Verifica se existem custos de servico duplicados para o mesmo evento "
        "e servico. O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando houver duplicidade.",
        )

    def handle(self, *args, **options):
        resultado = verificar_duplicidade_custos_evento()

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir(resultado)

        if options["falhar"] and resultado["duplicateGroupCount"] > 0:
            raise CommandError(
                f"{resultado['duplicateGroupCount']} grupo(s) de custo de evento "
                "duplicado encontrado(s)."
            )

    def _imprimir(self, resultado):
        if resultado["duplicateGroupCount"] == 0:
            self.stdout.write("Nenhuma duplicidade de custo de servico por evento encontrada.")
            return

        self.stdout.write(
            "Duplicidades de custo de servico por evento encontradas: "
            f"{resultado['duplicateGroupCount']} grupo(s)."
        )
        for grupo in resultado["groups"]:
            ids = ", ".join(str(item) for item in grupo["costIds"])
            self.stdout.write(
                f"- evento={grupo['eventLabel']} servico={grupo['serviceName']} "
                f"qtd={grupo['count']} ids={ids}"
            )


def verificar_duplicidade_custos_evento():
    duplicados = (
        EventoCustoServico.objects.values("evento_id", "servico_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
        .order_by("evento_id", "servico_id")
    )

    grupos = []
    for grupo in duplicados:
        custos = list(
            EventoCustoServico.objects.select_related("evento", "servico")
            .filter(
                evento_id=grupo["evento_id"],
                servico_id=grupo["servico_id"],
            )
            .order_by("id")
        )
        if not custos:
            continue

        primeiro = custos[0]
        grupos.append({
            "eventId": primeiro.evento_id,
            "eventLabel": str(primeiro.evento),
            "serviceId": primeiro.servico_id,
            "serviceName": primeiro.servico.nome,
            "count": grupo["count"],
            "costIds": [custo.id for custo in custos],
        })

    return {
        "duplicateGroupCount": len(grupos),
        "groups": grupos,
    }
