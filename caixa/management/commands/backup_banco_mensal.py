from django.core.management import BaseCommand

from caixa.services_backups import criar_backup_banco


class Command(BaseCommand):
    help = "Cria backup JSON mensal do banco somente quando houver alteracao nos dados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Cria um backup mesmo se os dados forem iguais ao ultimo backup.",
        )
        parser.add_argument(
            "--manter",
            type=int,
            default=3,
            help="Quantidade de backups mais recentes a manter. Padrao: 3.",
        )

    def handle(self, *args, **options):
        resultado = criar_backup_banco(
            force=options["force"],
            manter=options["manter"],
        )

        if not resultado["criado"]:
            self.stdout.write(self.style.WARNING(resultado["mensagem"]))
            return

        self.stdout.write(self.style.SUCCESS(resultado["mensagem"]))
        if resultado["removidos"]:
            self.stdout.write(f"Backups antigos removidos: {resultado['removidos']}")
