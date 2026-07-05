import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from caixa.contracts_obrigacoes import CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
from caixa.models import ObrigacaoFinanceira
from caixa.services_obrigacoes import liquidar_obrigacao_financeira_com_contexto_canonico
from caixa.utils_financeiros import quantizar_moeda
from tenancy.command_guards import ensure_tenant_schema


class Command(BaseCommand):
    help = (
        "Executa um canario rollback-only da baixa canonical-first. "
        "A operacao usa a escrita real dentro de transacao e desfaz no final."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--source", default="despesa_operacional")
        parser.add_argument("--source-id", dest="source_id")
        parser.add_argument("--payment-date", dest="payment_date")
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado em JSON para automacoes.",
        )
        parser.add_argument(
            "--falhar-com-inconsistencia",
            action="store_true",
            help="Retorna erro quando o canario nao ficar sincronizado.",
        )

    def handle(self, *args, **options):
        ensure_tenant_schema(
            "testar_baixa_canonical_first",
            action="testar baixa com dados operacionais",
        )
        try:
            resultado = testar_baixa_canonical_first(
                username=options["username"],
                source=options.get("source"),
                source_id=options.get("source_id"),
                payment_date=(
                    options.get("payment_date") or timezone.localdate().isoformat()
                ),
            )
        except (ValidationError, PermissionDenied) as exc:
            raise CommandError(_formatar_erro(exc)) from exc

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if (
            options["falhar_com_inconsistencia"]
            and not resultado["canonicalSettlement"]["synced"]
        ):
            raise CommandError(
                "Canario canonical-first nao ficou sincronizado: "
                f"{formatar_canario_nao_sincronizado(resultado)}"
            )

    def _imprimir_relatorio(self, resultado):
        self.stdout.write(
            self.style.SUCCESS("Canario canonical-first executado com rollback.")
        )
        self.stdout.write(
            f"Origem: {resultado['source']}#{resultado['sourceId']} "
            f"delta={resultado['deltaAmount']:.2f}"
        )
        self.stdout.write(
            "Sincronizacao canonica: "
            + ("ok" if resultado["canonicalSettlement"]["synced"] else "pendente")
        )
        self.stdout.write("Escritas persistidas: nao")


def testar_baixa_canonical_first(username, source, source_id=None, payment_date=None):
    source = str(source or "").strip()
    if source not in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES:
        raise ValidationError(
            {"source": "Canario canonical-first suporta apenas origens diretas."}
        )

    usuario = obter_usuario(username)
    obrigacao = obter_obrigacao_canario(source, source_id)
    source_id = getattr(obrigacao, f"{source}_id")
    delta = min(quantizar_moeda(obrigacao.valor_pendente), Decimal("1.00"))
    valor_realizado = quantizar_moeda(obrigacao.valor_realizado + delta)
    payload = {
        "source": source,
        "sourceId": source_id,
        "realizedAmount": str(valor_realizado),
        "paymentDate": payment_date,
        "notes": "Canario rollback-only da escrita canonical-first",
    }

    with override_settings(
        CANONICAL_FIRST_SETTLEMENT_ENABLED=True,
        CANONICAL_FIRST_SETTLEMENT_SOURCES=[source],
    ):
        with transaction.atomic():
            resultado = liquidar_obrigacao_financeira_com_contexto_canonico(
                source,
                source_id,
                payload,
                usuario,
            )
            transaction.set_rollback(True)

    return {
        "canary": True,
        "rollbackOnly": True,
        "writesPersisted": False,
        "source": source,
        "sourceId": source_id,
        "paymentDate": str(payment_date or ""),
        "obligationId": obrigacao.id,
        "obligationKey": obrigacao.chave_origem,
        "requestedRealizedAmount": float(valor_realizado),
        "deltaAmount": float(delta),
        "item": resultado["item"],
        "canonicalSettlement": resultado["canonicalSettlement"],
    }


def obter_usuario(username):
    usuario = get_user_model().objects.filter(username=username).first()
    if not usuario:
        raise ValidationError({"username": "Usuario nao encontrado."})
    return usuario


def obter_obrigacao_canario(source, source_id):
    query = ObrigacaoFinanceira.objects.filter(
        origem=source,
        tipo=ObrigacaoFinanceira.TIPO_PAGAR,
        valor_pendente__gt=0,
    ).order_by("data_vencimento", "id")
    if source_id:
        query = query.filter(**{f"{source}_id": source_id})

    obrigacao = query.first()
    if not obrigacao:
        raise ValidationError(
            {"sourceId": "Nenhuma obrigacao pendente encontrada para o canario."}
        )
    return obrigacao


def formatar_canario_nao_sincronizado(resultado):
    canonical_settlement = resultado.get("canonicalSettlement") or {}
    return (
        f"{resultado.get('source')}#{resultado.get('sourceId')} "
        f"obrigacao={resultado.get('obligationKey') or '-'} "
        f"delta={resultado.get('deltaAmount')} "
        f"writeModelSource={canonical_settlement.get('writeModelSource') or '-'}"
    )


def _formatar_erro(exc):
    if hasattr(exc, "message_dict"):
        partes = []
        for campo, mensagens in exc.message_dict.items():
            partes.append(f"{campo}: {'; '.join(mensagens)}")
        return "; ".join(partes)
    if hasattr(exc, "messages"):
        return "; ".join(exc.messages)
    return str(exc)
