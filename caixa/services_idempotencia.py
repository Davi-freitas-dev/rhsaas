import hashlib
import json
import uuid
from datetime import timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models_custo_fixo import RequisicaoIdempotenteRecorrencia


RETENCAO_IDEMPOTENCIA_PADRAO_DIAS = 7


class ChaveIdempotenciaInvalida(ValueError):
    pass


class ConflitoChaveIdempotencia(ValueError):
    pass


def parsear_chave_idempotencia(valor):
    if not valor:
        raise ChaveIdempotenciaInvalida(
            "Informe o cabeçalho Idempotency-Key como UUID."
        )
    try:
        return uuid.UUID(str(valor))
    except (TypeError, ValueError, AttributeError) as error:
        raise ChaveIdempotenciaInvalida(
            "Informe o cabeçalho Idempotency-Key como UUID."
        ) from error


def hash_payload_idempotente(payload):
    serializado = json.dumps(
        payload,
        cls=DjangoJSONEncoder,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _obter_ou_criar_registro(*, escopo, chave, payload_hash, ator):
    try:
        return (
            RequisicaoIdempotenteRecorrencia.objects.select_for_update().get(
                escopo=escopo,
                chave=chave,
            ),
            False,
        )
    except RequisicaoIdempotenteRecorrencia.DoesNotExist:
        try:
            with transaction.atomic():
                registro = RequisicaoIdempotenteRecorrencia.objects.create(
                    escopo=escopo,
                    chave=chave,
                    payload_hash=payload_hash,
                    ator=ator,
                    http_status=500,
                    resposta_segura={},
                )
            return registro, True
        except IntegrityError:
            return (
                RequisicaoIdempotenteRecorrencia.objects.select_for_update().get(
                    escopo=escopo,
                    chave=chave,
                ),
                False,
            )


@transaction.atomic
def executar_requisicao_idempotente(
    *,
    escopo,
    chave,
    payload,
    ator,
    operacao,
):
    payload_hash = hash_payload_idempotente(payload)
    registro, criado = _obter_ou_criar_registro(
        escopo=escopo,
        chave=chave,
        payload_hash=payload_hash,
        ator=ator,
    )
    if not criado:
        if (
            registro.payload_hash != payload_hash
            or registro.ator_id != getattr(ator, "pk", None)
        ):
            raise ConflitoChaveIdempotencia(
                "A Idempotency-Key já foi usada com outra requisição."
            )
        return registro.resposta_segura, registro.http_status, True

    resposta, http_status = operacao()
    if http_status >= 500:
        registro.delete()
        return resposta, http_status, False
    registro.http_status = http_status
    registro.resposta_segura = resposta
    registro.save(
        update_fields=[
            "http_status",
            "resposta_segura",
            "status",
            "atualizado_em",
        ]
    )
    return resposta, http_status, False


@transaction.atomic
def expurgar_requisicoes_idempotentes_recorrencia(
    *,
    agora=None,
    retencao_dias=RETENCAO_IDEMPOTENCIA_PADRAO_DIAS,
    dry_run=False,
):
    """Remove chaves idempotentes concluídas após a janela de retry.

    A retenção é tenant-local porque a tabela está em ``TENANT_APPS`` e o
    command correspondente exige schema de tenant.  A janela de sete dias
    preserva retries operacionais tardios sem manter chaves indefinidamente.
    """
    if retencao_dias < 1:
        raise ValueError("A retenção de idempotência deve ser de pelo menos um dia.")
    agora = agora or timezone.now()
    limite = agora - timedelta(days=retencao_dias)
    queryset = RequisicaoIdempotenteRecorrencia.objects.filter(
        atualizado_em__lt=limite,
    )
    quantidade = queryset.count()
    if not dry_run:
        queryset.delete()
    return quantidade
