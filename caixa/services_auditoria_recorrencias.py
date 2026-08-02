import hashlib
import json
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models_custo_fixo import (
    AuditoriaCustoRecorrente,
    EstadoAgregacaoAuditoriaRecorrente,
)


JANELA_AGREGACAO = timedelta(hours=1)
RETENCAO_AUDITORIA = timedelta(days=400)


def _chave_agregacao(
    *,
    tipo_evento,
    origem,
    plano_id,
    competencia,
    status,
    codigo_motivo,
    ator_id,
):
    payload = {
        "tipo": tipo_evento,
        "origem": origem,
        "plano": plano_id,
        "competencia": competencia.isoformat() if competencia else None,
        "status": status,
        "motivo": codigo_motivo,
        # `None` representa uma operação do sistema. Assim ela nunca é
        # agregada sob a identidade de uma pessoa, e pessoas distintas não
        # compartilham a mesma trilha de auditoria.
        "ator": ator_id,
    }
    serializado = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def _bloquear_ou_criar_estado(chave):
    try:
        return EstadoAgregacaoAuditoriaRecorrente.objects.select_for_update().get(
            pk=chave
        )
    except EstadoAgregacaoAuditoriaRecorrente.DoesNotExist:
        try:
            with transaction.atomic():
                EstadoAgregacaoAuditoriaRecorrente.objects.create(
                    chave_agregacao=chave
                )
        except IntegrityError:
            pass
        return EstadoAgregacaoAuditoriaRecorrente.objects.select_for_update().get(
            pk=chave
        )


@transaction.atomic
def registrar_evento_auditoria_recorrente(
    *,
    tipo_evento,
    origem,
    status,
    codigo_motivo,
    correlation_id,
    plano_id=None,
    competencia=None,
    ator=None,
    ocorrido_em=None,
):
    ocorrido_em = ocorrido_em or timezone.now()
    correlation_id = uuid.UUID(str(correlation_id))
    chave = _chave_agregacao(
        tipo_evento=tipo_evento,
        origem=origem,
        plano_id=plano_id,
        competencia=competencia,
        status=status,
        codigo_motivo=codigo_motivo,
        ator_id=getattr(ator, "pk", None),
    )
    estado = _bloquear_ou_criar_estado(chave)
    evento = None
    if estado.ultimo_evento_id:
        evento = AuditoriaCustoRecorrente.objects.select_for_update().get(
            pk=estado.ultimo_evento_id
        )
    if (
        evento is not None
        and abs(evento.last_occurred_at - ocorrido_em) <= JANELA_AGREGACAO
    ):
        primeiro_registro = min(evento.first_occurred_at, ocorrido_em)
        ultimo_registro = max(evento.last_occurred_at, ocorrido_em)
        AuditoriaCustoRecorrente.objects.filter(pk=evento.pk).update(
            first_occurred_at=primeiro_registro,
            last_occurred_at=ultimo_registro,
            occurrences_count=F("occurrences_count") + 1,
            correlation_id=correlation_id,
        )
        evento.refresh_from_db()
        return evento

    evento = AuditoriaCustoRecorrente.objects.create(
        tipo_evento=tipo_evento,
        origem=origem,
        plano_id=plano_id,
        competencia=competencia,
        status=status,
        codigo_motivo=codigo_motivo,
        ator=ator,
        correlation_id=correlation_id,
        chave_agregacao=chave,
        first_occurred_at=ocorrido_em,
        last_occurred_at=ocorrido_em,
        occurrences_count=1,
    )
    estado.ultimo_evento = evento
    estado.save(update_fields=["ultimo_evento", "atualizado_em"])
    return evento


@transaction.atomic
def expurgar_auditoria_recorrencias(*, agora=None):
    agora = agora or timezone.now()
    limite = agora - RETENCAO_AUDITORIA
    queryset = AuditoriaCustoRecorrente.objects.filter(
        last_occurred_at__lt=limite
    )
    quantidade = queryset.count()
    queryset.delete()
    EstadoAgregacaoAuditoriaRecorrente.objects.filter(
        ultimo_evento__isnull=True
    ).delete()
    return quantidade
