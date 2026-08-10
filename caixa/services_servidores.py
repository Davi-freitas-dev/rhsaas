"""Escritas de servidores; exclusão respeita Evento -> Servidor -> Participação."""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Evento, Servico
from .models_servidores import (
    HistoricoJornadaMensalServidor,
    HistoricoSalarialServidor,
    ParticipacaoServidorEvento,
    Servidor,
    ServidorServico,
)
from .services_custos_recorrentes import sincronizar_plano_salarial


ZERO = Decimal("0.00")


def _atribuir_autoria(objeto, usuario, *, criado=False):
    if criado and hasattr(objeto, "criado_por"):
        objeto.criado_por = usuario
    if hasattr(objeto, "atualizado_por"):
        objeto.atualizado_por = usuario
    objeto._history_user = usuario


def _servicos_por_ids(servicos_ids):
    ids = list(dict.fromkeys(int(servico_id) for servico_id in servicos_ids))
    servicos = list(Servico.objects.filter(id__in=ids).order_by("nome", "id"))
    if len(servicos) != len(ids):
        raise ValidationError({"serviceIds": "Um ou mais serviços não foram encontrados."})
    return servicos


def _sincronizar_servicos(servidor, servicos_ids, usuario):
    servicos = _servicos_por_ids(servicos_ids)
    vinculos_atuais = {
        vinculo.servico_id: vinculo
        for vinculo in ServidorServico.objects.select_for_update().filter(
            servidor=servidor
        )
    }
    ids_desejados = {servico.id for servico in servicos}

    for servico in servicos:
        vinculo = vinculos_atuais.get(servico.id)
        if vinculo:
            if not vinculo.ativo:
                if not servico.ativo:
                    raise ValidationError(
                        {"serviceIds": f"O serviço inativo '{servico.nome}' não pode ser reativado."}
                    )
                vinculo.ativo = True
                _atribuir_autoria(vinculo, usuario)
                vinculo.full_clean()
                vinculo.save(update_fields=["ativo", "atualizado_por", "atualizado_em"])
            continue

        if not servico.ativo:
            raise ValidationError(
                {"serviceIds": f"O serviço inativo '{servico.nome}' não pode ser adicionado."}
            )
        vinculo = ServidorServico(
            servidor=servidor,
            servico=servico,
            ativo=True,
        )
        _atribuir_autoria(vinculo, usuario, criado=True)
        vinculo.full_clean()
        vinculo.save()

    for servico_id, vinculo in vinculos_atuais.items():
        if servico_id in ids_desejados:
            continue
        vinculo._history_user = usuario
        vinculo.delete()


def _fechar_vigencia_salarial(vigencia, data_fim, usuario):
    if data_fim < vigencia.data_inicio:
        vigencia._history_user = usuario
        vigencia.delete()
        return
    vigencia.data_fim = data_fim
    _atribuir_autoria(vigencia, usuario)
    vigencia.full_clean()
    vigencia.save(update_fields=["data_fim", "atualizado_por", "atualizado_em"])


def _sincronizar_historico_salarial(
    servidor,
    *,
    salario_anterior,
    vinculo_anterior,
    data_vigencia,
    usuario,
):
    mudou = (
        salario_anterior != servidor.salario_mensal
        or vinculo_anterior != servidor.tipo_vinculo
    )
    if not mudou:
        return

    atual = (
        HistoricoSalarialServidor.objects.select_for_update()
        .filter(servidor=servidor, data_fim__isnull=True)
        .order_by("-data_inicio", "-id")
        .first()
    )

    if servidor.tipo_vinculo != Servidor.VINCULO_MENSALISTA:
        if atual:
            _fechar_vigencia_salarial(atual, data_vigencia - timedelta(days=1), usuario)
        return

    if atual and data_vigencia < atual.data_inicio:
        raise ValidationError(
            {"salaryEffectiveDate": "A nova vigência não pode ser anterior à vigência salarial atual."}
        )

    if atual and atual.data_inicio == data_vigencia:
        atual.valor = servidor.salario_mensal
        atual.servidor_nome_snapshot = servidor.nome
        _atribuir_autoria(atual, usuario)
        atual.full_clean()
        atual.save(
            update_fields=[
                "valor",
                "servidor_nome_snapshot",
                "atualizado_por",
                "atualizado_em",
            ]
        )
        return

    if atual:
        _fechar_vigencia_salarial(atual, data_vigencia - timedelta(days=1), usuario)

    nova = HistoricoSalarialServidor(
        servidor=servidor,
        servidor_nome_snapshot=servidor.nome,
        servidor_id_snapshot=servidor.id,
        valor=servidor.salario_mensal,
        data_inicio=data_vigencia,
    )
    _atribuir_autoria(nova, usuario, criado=True)
    nova.full_clean()
    nova.save()


def _fechar_vigencia_jornada(vigencia, data_fim, usuario):
    if data_fim < vigencia.data_inicio:
        vigencia._history_user = usuario
        vigencia.delete()
        return
    vigencia.data_fim = data_fim
    _atribuir_autoria(vigencia, usuario)
    vigencia.full_clean()
    vigencia.save(update_fields=["data_fim", "atualizado_por", "atualizado_em"])


def _sincronizar_historico_jornada(
    servidor,
    *,
    jornada_anterior,
    vinculo_anterior,
    data_vigencia,
    usuario,
):
    mudou = (
        jornada_anterior != servidor.carga_horaria_mensal
        or vinculo_anterior != servidor.tipo_vinculo
    )
    if not mudou:
        return

    atual = (
        HistoricoJornadaMensalServidor.objects.select_for_update()
        .filter(servidor=servidor, data_fim__isnull=True)
        .order_by("-data_inicio", "-id")
        .first()
    )
    jornada = (
        servidor.carga_horaria_mensal
        if servidor.tipo_vinculo == Servidor.VINCULO_MENSALISTA
        else None
    )
    if jornada is None:
        if atual:
            _fechar_vigencia_jornada(
                atual,
                data_vigencia - timedelta(days=1),
                usuario,
            )
        return

    if atual and data_vigencia < atual.data_inicio:
        raise ValidationError(
            {
                "workloadEffectiveDate": (
                    "A nova vigência não pode ser anterior à vigência de jornada atual."
                )
            }
        )
    if atual and atual.data_inicio == data_vigencia:
        atual.horas_mensais = jornada
        atual.servidor_nome_snapshot = servidor.nome
        _atribuir_autoria(atual, usuario)
        atual.full_clean()
        atual.save(
            update_fields=[
                "horas_mensais",
                "servidor_nome_snapshot",
                "atualizado_por",
                "atualizado_em",
            ]
        )
        return
    if atual:
        _fechar_vigencia_jornada(
            atual,
            data_vigencia - timedelta(days=1),
            usuario,
        )

    nova = HistoricoJornadaMensalServidor(
        servidor=servidor,
        servidor_nome_snapshot=servidor.nome,
        servidor_id_snapshot=servidor.id,
        horas_mensais=jornada,
        data_inicio=data_vigencia,
    )
    _atribuir_autoria(nova, usuario, criado=True)
    nova.full_clean()
    nova.save()


@transaction.atomic
def criar_servidor(
    *,
    dados,
    servicos_ids,
    usuario,
    data_vigencia_salario=None,
    data_vigencia_jornada=None,
):
    servidor = Servidor(**dados)
    _atribuir_autoria(servidor, usuario, criado=True)
    servidor.full_clean()
    try:
        servidor.save()
    except IntegrityError as error:
        raise ValidationError({"document": "Já existe um servidor com este documento."}) from error

    _sincronizar_servicos(servidor, servicos_ids, usuario)
    _sincronizar_historico_salarial(
        servidor,
        salario_anterior=None,
        vinculo_anterior=None,
        data_vigencia=data_vigencia_salario or timezone.localdate(),
        usuario=usuario,
    )
    _sincronizar_historico_jornada(
        servidor,
        jornada_anterior=None,
        vinculo_anterior=None,
        data_vigencia=(
            data_vigencia_jornada
            or data_vigencia_salario
            or timezone.localdate()
        ),
        usuario=usuario,
    )
    sincronizar_plano_salarial(
        servidor,
        usuario=usuario,
        competencia_materializacao=data_vigencia_salario,
    )
    return servidor


@transaction.atomic
def atualizar_servidor(
    servidor,
    *,
    dados,
    servicos_ids,
    usuario,
    data_vigencia_salario=None,
    data_vigencia_jornada=None,
):
    servidor = Servidor.objects.select_for_update().get(pk=servidor.pk)
    salario_anterior = servidor.salario_mensal
    jornada_anterior = servidor.carga_horaria_mensal
    vinculo_anterior = servidor.tipo_vinculo
    for campo, valor in dados.items():
        setattr(servidor, campo, valor)
    _atribuir_autoria(servidor, usuario)
    servidor.full_clean()
    try:
        servidor.save()
    except IntegrityError as error:
        raise ValidationError({"document": "Já existe um servidor com este documento."}) from error

    _sincronizar_servicos(servidor, servicos_ids, usuario)
    _sincronizar_historico_salarial(
        servidor,
        salario_anterior=salario_anterior,
        vinculo_anterior=vinculo_anterior,
        data_vigencia=data_vigencia_salario or timezone.localdate(),
        usuario=usuario,
    )
    _sincronizar_historico_jornada(
        servidor,
        jornada_anterior=jornada_anterior,
        vinculo_anterior=vinculo_anterior,
        data_vigencia=(
            data_vigencia_jornada
            or data_vigencia_salario
            or timezone.localdate()
        ),
        usuario=usuario,
    )
    sincronizar_plano_salarial(
        servidor,
        usuario=usuario,
        competencia_materializacao=data_vigencia_salario,
    )
    return servidor


@transaction.atomic
def excluir_servidor(servidor, *, usuario):
    eventos_ids = list(
        ParticipacaoServidorEvento.objects.filter(servidor_id=servidor.pk)
        .order_by("evento_id")
        .values_list("evento_id", flat=True)
        .distinct()
    )
    list(
        Evento.objects.select_for_update()
        .filter(pk__in=eventos_ids)
        .order_by("pk")
    )
    servidor = Servidor.objects.select_for_update().get(pk=servidor.pk)
    agora = timezone.now()

    participacoes = list(
        ParticipacaoServidorEvento.objects.select_for_update()
        .filter(servidor=servidor)
        .order_by("pk")
    )
    for participacao in participacoes:
        participacao.servidor_nome_snapshot = servidor.nome
        participacao.servidor_identificador_snapshot = servidor.documento[-4:]
        participacao.servidor_excluido_por = usuario
        participacao.servidor_excluido_em = agora
        _atribuir_autoria(participacao, usuario)
        participacao.save(
            update_fields=[
                "servidor_nome_snapshot",
                "servidor_identificador_snapshot",
                "servidor_excluido_por",
                "servidor_excluido_em",
                "atualizado_por",
                "atualizado_em",
            ]
        )

    historicos_salariais = list(
        HistoricoSalarialServidor.objects.select_for_update().filter(servidor=servidor)
    )
    for historico in historicos_salariais:
        historico.servidor_nome_snapshot = servidor.nome
        _atribuir_autoria(historico, usuario)
        historico.save(
            update_fields=["servidor_nome_snapshot", "atualizado_por", "atualizado_em"]
        )

    historicos_jornada = list(
        HistoricoJornadaMensalServidor.objects.select_for_update().filter(
            servidor=servidor
        )
    )
    for historico in historicos_jornada:
        historico.servidor_nome_snapshot = servidor.nome
        _atribuir_autoria(historico, usuario)
        historico.save(
            update_fields=["servidor_nome_snapshot", "atualizado_por", "atualizado_em"]
        )

    for vinculo in list(
        ServidorServico.objects.select_for_update().filter(servidor=servidor)
    ):
        vinculo._history_user = usuario
        vinculo.delete()
    servidor._history_user = usuario
    servidor.delete()

    return len(participacoes)
