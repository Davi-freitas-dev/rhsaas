from django.core.management.base import BaseCommand

from caixa.models import Evento
from caixa.services_sincronizacao import sincronizar_evento_financeiro
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = "Sincroniza as despesas operacionais dos eventos com os custos por servico e extras."

    def handle(self, *args, **options):
        ensure_tenant_schema(
            "sincronizar_despesas_eventos",
            action="sincronizar dados operacionais",
        )
        eventos = Evento.objects.all().order_by("id")
        total = eventos.count()
        processados = 0

        if total == 0:
            self.stdout.write(self.style.WARNING("Nenhum evento encontrado."))
            return

        self.stdout.write(f"Iniciando sincronizacao de {total} evento(s)...")

        for evento in eventos:
            sincronizar_evento_financeiro(evento)

            processados += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{processados}/{total}] Evento sincronizado: {evento.numero} - {evento.nome_evento}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Sincronizacao concluida com sucesso."))
