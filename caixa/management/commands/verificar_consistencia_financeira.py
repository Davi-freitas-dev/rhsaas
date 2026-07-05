from decimal import Decimal

from django.core.management.base import BaseCommand

from caixa.models import Evento
from caixa.services_sincronizacao import sincronizar_evento_financeiro
from caixa.utils_financeiros import quantizar_moeda
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = "Verifica divergencias entre eventos, receitas e despesas. Use --corrigir para sincronizar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--corrigir",
            action="store_true",
            help="Sincroniza despesas derivadas e recalcula eventos inconsistentes.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("verificar_consistencia_financeira", action="verificar dados operacionais")
        corrigir = options["corrigir"]
        inconsistentes = []

        for evento in Evento.objects.prefetch_related("receitas", "despesas").order_by("id"):
            receita_real = sum(
                (receita.valor_recebido for receita in evento.receitas.all()),
                Decimal("0.00"),
            )
            custo_real = sum(
                (despesa.valor_pago for despesa in evento.despesas.all()),
                Decimal("0.00"),
            )
            receita_real = quantizar_moeda(receita_real)
            custo_real = quantizar_moeda(custo_real)
            lucro_real = quantizar_moeda(receita_real - custo_real)
            tem_agregado_extra_antigo = any(
                despesa.descricao == "Custos extras previstos"
                for despesa in evento.despesas.all()
            )

            divergente = (
                evento.valor_total_realizado != receita_real
                or evento.custo_total_realizado != custo_real
                or evento.lucro_realizado != lucro_real
                or tem_agregado_extra_antigo
            )

            if not divergente:
                continue

            inconsistentes.append(evento)
            self.stdout.write(
                self.style.WARNING(
                    f"Inconsistencia: {evento.numero} - {evento.nome_evento}"
                )
            )

            if corrigir:
                sincronizar_evento_financeiro(evento)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Corrigido: {evento.numero} - {evento.nome_evento}"
                    )
                )

        if inconsistentes:
            acao = "corrigida(s)" if corrigir else "encontrada(s)"
            self.stdout.write(
                self.style.WARNING(
                    f"{len(inconsistentes)} inconsistencia(s) {acao}."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("Nenhuma inconsistencia financeira encontrada."))
