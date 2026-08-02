"""Escritas com lock global Evento -> Servidor(es) -> Participação -> Custo."""

from decimal import Decimal, InvalidOperation, ROUND_FLOOR

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .demo_policy import assert_demo_write_allowed
from .models import Evento, Servico
from .models_servidores import (
    ParticipacaoServidorEvento,
    Servidor,
    ServidorEventoDiaTrabalhado,
    ServidorServico,
)
from .models_servico import EventoCustoServico
from .utils_financeiros import quantizar_moeda


ZERO = Decimal("0.00")
CENTAVO = Decimal("0.01")
EVENTOS_BLOQUEADOS = {"concluido", "cancelado"}


def _atribuir_autoria(objeto, usuario, *, criado=False):
    if criado:
        objeto.criado_por = usuario
    objeto.atualizado_por = usuario
    objeto._history_user = usuario


def _validar_evento_editavel(evento):
    if evento.status in EVENTOS_BLOQUEADOS:
        raise ValidationError(
            {"event": f"Participações não podem ser alteradas em evento {evento.get_status_display().lower()}."}
        )


def _ratear_centavos(total, participacoes, peso):
    total = quantizar_moeda(total)
    if not participacoes:
        return {}
    pesos = {item.id: Decimal(peso(item)) for item in participacoes}
    peso_total = sum(pesos.values(), ZERO)
    if peso_total <= ZERO:
        raise ValidationError({"workUnits": "As unidades de trabalho do rateio devem ser positivas."})

    total_centavos = int((total / CENTAVO).to_integral_value())
    bases = {}
    restos = []
    usados = 0
    for item in participacoes:
        exato = Decimal(total_centavos) * pesos[item.id] / peso_total
        base = int(exato.to_integral_value(rounding=ROUND_FLOOR))
        bases[item.id] = base
        usados += base
        restos.append((exato - Decimal(base), item.id))

    residuos = total_centavos - usados
    restos.sort(key=lambda entrada: (-entrada[0], entrada[1]))
    for _resto, item_id in restos[:residuos]:
        bases[item_id] += 1
    return {item_id: Decimal(centavos) * CENTAVO for item_id, centavos in bases.items()}


def _custo_servico_bloqueado(evento, servico):
    try:
        return EventoCustoServico.objects.select_for_update().get(
            evento=evento,
            servico=servico,
        )
    except EventoCustoServico.DoesNotExist as error:
        raise ValidationError(
            {"service": "O evento não possui custo estruturado para este serviço."}
        ) from error


def _recalcular_grupo_bloqueado(evento, servico, usuario):
    # O evento já está bloqueado por todos os chamadores públicos. Travar os
    # servidores em ordem crescente antes das participações completa a ordem
    # global e também serializa exclusão de servidor com o rateio.
    servidores_ids = list(
        ParticipacaoServidorEvento.objects.filter(
            evento=evento,
            servico=servico,
            servidor_id__isnull=False,
        )
        .order_by("servidor_id")
        .values_list("servidor_id", flat=True)
        .distinct()
    )
    if servidores_ids:
        list(
            Servidor.objects.select_for_update()
            .filter(pk__in=servidores_ids)
            .order_by("pk")
        )
    participacoes = list(
        ParticipacaoServidorEvento.objects.select_for_update()
        .filter(evento=evento, servico=servico)
        .order_by("id")
    )
    custo = _custo_servico_bloqueado(evento, servico)
    total = quantizar_moeda(custo.valor_diarias)
    diaristas = [
        item for item in participacoes if item.tipo_vinculo == Servidor.VINCULO_DIARISTA
    ]
    mensalistas = [
        item for item in participacoes if item.tipo_vinculo == Servidor.VINCULO_MENSALISTA
    ]

    for mensalista in mensalistas:
        mensalista.valor_calculado = ZERO
        mensalista.valor_final = ZERO
        mensalista.valor_total_servico_snapshot = ZERO
        mensalista.quantidade_servidores_rateio_snapshot = max(len(diaristas), 1)
        _atribuir_autoria(mensalista, usuario)
        mensalista.save(
            update_fields=[
                "valor_calculado",
                "valor_final",
                "valor_total_servico_snapshot",
                "quantidade_servidores_rateio_snapshot",
                "atualizado_por",
                "atualizado_em",
            ]
        )

    if not diaristas:
        return

    excluidos = [item for item in diaristas if item.servidor_id is None]
    editaveis = [item for item in diaristas if item.servidor_id is not None]
    valor_excluidos = quantizar_moeda(sum((item.valor_final for item in excluidos), ZERO))
    total_editavel = quantizar_moeda(total - valor_excluidos)
    if total_editavel < ZERO:
        raise ValidationError(
            {"distribution": "Valores preservados de servidores excluídos ultrapassam o custo do serviço."}
        )

    rateio_calculado = _ratear_centavos(
        total_editavel,
        editaveis,
        lambda item: item.unidades_rateio,
    )
    manuais = [item for item in editaveis if item.valor_editado_manualmente]
    automaticos = [item for item in editaveis if not item.valor_editado_manualmente]
    total_manual = quantizar_moeda(sum((item.valor_final for item in manuais), ZERO))
    restante = quantizar_moeda(total_editavel - total_manual)
    if restante < ZERO:
        raise ValidationError(
            {"finalAmount": "Os valores manuais ultrapassam o total distribuível do serviço."}
        )
    if restante > ZERO and not automaticos:
        raise ValidationError(
            {"finalAmount": "O valor manual deve completar exatamente o total quando não há rateios automáticos."}
        )
    rateio_final = _ratear_centavos(
        restante,
        automaticos,
        lambda item: item.unidades_rateio,
    )

    for item in editaveis:
        item.valor_calculado = rateio_calculado.get(item.id, ZERO)
        if not item.valor_editado_manualmente:
            item.valor_final = rateio_final.get(item.id, ZERO)
        item.valor_total_servico_snapshot = total
        item.quantidade_servidores_rateio_snapshot = len(diaristas)
        _atribuir_autoria(item, usuario)
        item.full_clean()
        item.save(
            update_fields=[
                "valor_calculado",
                "valor_final",
                "valor_total_servico_snapshot",
                "quantidade_servidores_rateio_snapshot",
                "atualizado_por",
                "atualizado_em",
            ]
        )

    soma_final = quantizar_moeda(sum((item.valor_final for item in diaristas), ZERO))
    if soma_final != total:
        raise ValidationError(
            {"distribution": "A soma distribuída não coincide com o custo do serviço."}
        )


@transaction.atomic
def recalcular_participacoes_por_custo_servico(custo_servico, *, usuario=None):
    """Recalcula o único grupo afetado por uma mutação de custo estruturado.

    É chamado pelo próprio model depois de bloquear Evento e persistir o custo;
    por isso orçamento, Admin e qualquer escrita ORM normal compartilham a
    mesma invariante financeira, sem depender de signal para o rateio.
    """
    evento = Evento.objects.select_for_update().get(pk=custo_servico.evento_id)
    custo = EventoCustoServico.objects.select_for_update().get(pk=custo_servico.pk)
    _recalcular_grupo_bloqueado(evento, custo.servico, usuario)


@transaction.atomic
def atualizar_evento_com_periodo(evento, *, valores, usuario=None):
    """Atualiza um evento sob o primeiro lock da ordem global.

    A atualização do período deve competir pelo mesmo lock de ``Evento`` que
    criação, edição de escala e recálculo de participação.  A validação é
    feita *depois* do lock: assim, uma escala que acabou de ser persistida não
    pode ser ignorada por uma leitura anterior do período, e uma escala que
    começa depois da alteração sempre enxerga o intervalo novo.

    ``valores`` é deliberadamente explícito para que o chamador não replique a
    regra de persistência nem faça ``save`` direto para alterar o período.
    """
    evento_bloqueado = Evento.objects.select_for_update().get(pk=evento.pk)
    campos = []
    for campo, valor in valores.items():
        if campo not in evento_bloqueado._meta._forward_fields_map:
            raise ValueError(f"Campo de evento não permitido: {campo}.")
        setattr(evento_bloqueado, campo, valor)
        campos.append(campo)

    evento_bloqueado._history_user = usuario
    evento_bloqueado.full_clean()
    evento_bloqueado.save(update_fields=[*campos, "atualizado_em"])
    return evento_bloqueado


def _validar_vinculo_servidor_servico(servidor, servico):
    if not servidor.ativo:
        raise ValidationError({"server": "Servidor inativo não pode ser adicionado ao evento."})
    if not servico.__class__.objects.filter(pk=servico.pk, ativo=True).exists():
        raise ValidationError(
            {"service": "Serviço inativo não pode receber uma nova participação."}
        )
    if not ServidorServico.objects.filter(
        servidor=servidor,
        servico=servico,
        ativo=True,
    ).exists():
        raise ValidationError(
            {"service": "O serviço executado não está vinculado ao servidor."}
        )


def _bloquear_participacao_na_ordem(participacao):
    """Bloqueia Evento -> Servidor -> Participação, sempre por chave crescente."""
    referencia = ParticipacaoServidorEvento.objects.only("evento_id").get(
        pk=participacao.pk
    )
    evento = Evento.objects.select_for_update().get(pk=referencia.evento_id)
    referencia = ParticipacaoServidorEvento.objects.only("servidor_id").get(
        pk=participacao.pk
    )
    servidor = None
    if referencia.servidor_id is not None:
        servidor = Servidor.objects.select_for_update().get(
            pk=referencia.servidor_id
        )
    participacao = (
        ParticipacaoServidorEvento.objects.select_for_update(of=("self",))
        .select_related("evento", "servidor", "servico")
        .get(pk=participacao.pk)
    )
    return participacao, evento, servidor


def _preencher_snapshots_criacao(participacao, servidor, servico):
    """Captura atributos de identidade no nascimento da participação.

    Nome, vínculo, identificador e salário de referência descrevem o fato
    histórico. Eles não acompanham edições cadastrais posteriores.
    """
    participacao.tipo_vinculo = servidor.tipo_vinculo
    participacao.servidor_nome_snapshot = servidor.nome
    participacao.servidor_id_snapshot = servidor.id
    participacao.servidor_identificador_snapshot = servidor.documento[-4:]
    participacao.servico_nome_snapshot = servico.nome
    participacao.servico_codigo_snapshot = servico.codigo
    participacao.salario_mensal_referencia = servidor.salario_mensal
    _atualizar_snapshot_servico(participacao, servico)


def _atualizar_snapshot_servico(participacao, servico):
    """Atualiza somente a identidade do serviço numa troca explícita dele."""
    participacao.servico_nome_snapshot = servico.nome
    participacao.servico_codigo_snapshot = servico.codigo
    participacao.unidade_cobranca_snapshot = servico.unidade_cobranca
    participacao.horas_base_diaria_snapshot = servico.horas_base_diaria


def _preparar_escala(evento, datas_trabalhadas):
    if datas_trabalhadas is None:
        return None
    if not datas_trabalhadas:
        raise ValidationError(
            {"workedDays": "Informe ao menos uma data trabalhada."}
        )

    escala = []
    datas_vistas = set()
    for indice, item in enumerate(datas_trabalhadas):
        data_trabalhada = item.get("data", item.get("date"))
        horas = item.get("quantidade_horas", item.get("hours"))
        if data_trabalhada is None:
            raise ValidationError(
                {"workedDays": f"Informe a data trabalhada no item {indice + 1}."}
            )
        if data_trabalhada in datas_vistas:
            raise ValidationError(
                {"workedDays": "Não é permitido informar a mesma data mais de uma vez."}
            )
        datas_vistas.add(data_trabalhada)
        if data_trabalhada < evento.data_inicio or data_trabalhada > evento.data_fim:
            raise ValidationError(
                {
                    "workedDays": (
                        f"A data {data_trabalhada:%d/%m/%Y} não pertence ao "
                        "período do evento."
                    )
                }
            )
        if horas is not None:
            try:
                horas = Decimal(str(horas))
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ValidationError(
                    {
                        "workedDays": (
                            f"Informe uma quantidade de horas válida no item "
                            f"{indice + 1}."
                        )
                    }
                ) from error
            if horas <= ZERO:
                raise ValidationError(
                    {
                        "workedDays": (
                            "A quantidade de horas deve ser maior que zero "
                            "quando informada."
                        )
                    }
                )
        escala.append({"data": data_trabalhada, "quantidade_horas": horas})
    return sorted(escala, key=lambda item: item["data"])


def _totais_escala(escala):
    return (
        len(escala),
        sum(
            (
                item["quantidade_horas"]
                for item in escala
                if item["quantidade_horas"] is not None
            ),
            ZERO,
        ),
    )


def _substituir_escala(participacao, escala):
    atuais = {
        item.data: item
        for item in (
            ServidorEventoDiaTrabalhado.objects.select_for_update()
            .filter(participacao=participacao)
            .order_by("data", "id")
        )
    }
    desejadas = {item["data"]: item for item in escala}
    ids_remover = [
        item.pk for data, item in atuais.items() if data not in desejadas
    ]
    if ids_remover:
        ServidorEventoDiaTrabalhado.objects.filter(pk__in=ids_remover).delete()

    try:
        for data_trabalhada, dados in desejadas.items():
            existente = atuais.get(data_trabalhada)
            if existente is not None:
                if existente.quantidade_horas != dados["quantidade_horas"]:
                    existente.quantidade_horas = dados["quantidade_horas"]
                    existente.full_clean()
                    existente.save(
                        update_fields=["quantidade_horas", "atualizado_em"]
                    )
                continue
            novo = ServidorEventoDiaTrabalhado(
                participacao=participacao,
                data=data_trabalhada,
                quantidade_horas=dados["quantidade_horas"],
            )
            novo.full_clean()
            novo.save()
    except IntegrityError as error:
        raise ValidationError(
            {"workedDays": "A mesma data não pode ser cadastrada duas vezes."}
        ) from error


def _totais_escala_persistida(participacao):
    escala = list(
        ServidorEventoDiaTrabalhado.objects.select_for_update()
        .filter(participacao=participacao)
        .values("data", "quantidade_horas")
        .order_by("data", "id")
    )
    return _totais_escala(escala) if escala else None


@transaction.atomic
def criar_participacao(
    *,
    evento,
    servidor,
    servico,
    quantidade_dias,
    quantidade_horas,
    usuario,
    datas_trabalhadas=None,
):
    evento = Evento.objects.select_for_update().get(pk=evento.pk)
    servidor = Servidor.objects.select_for_update().get(pk=servidor.pk)
    assert_demo_write_allowed(usuario, evento, operation="create participation")
    _validar_evento_editavel(evento)
    _validar_vinculo_servidor_servico(servidor, servico)
    escala = _preparar_escala(evento, datas_trabalhadas)
    if escala is not None:
        quantidade_dias, quantidade_horas = _totais_escala(escala)

    participacao = ParticipacaoServidorEvento(
        servidor=servidor,
        evento=evento,
        servico=servico,
        quantidade_dias=quantidade_dias,
        quantidade_horas=quantidade_horas,
    )
    _preencher_snapshots_criacao(participacao, servidor, servico)
    _atribuir_autoria(participacao, usuario, criado=True)
    participacao.full_clean()
    try:
        participacao.save()
    except IntegrityError as error:
        raise ValidationError(
            {"server": "Este servidor já participa do evento neste serviço."}
        ) from error

    if escala is not None:
        _substituir_escala(participacao, escala)
    _recalcular_grupo_bloqueado(evento, servico, usuario)
    participacao.refresh_from_db()
    return participacao


@transaction.atomic
def atualizar_participacao(
    participacao,
    *,
    servico,
    quantidade_dias,
    quantidade_horas,
    valor_final=None,
    motivo_edicao="",
    usuario,
    datas_trabalhadas=None,
):
    participacao, evento, servidor = _bloquear_participacao_na_ordem(participacao)
    assert_demo_write_allowed(usuario, participacao, operation="update participation")
    _validar_evento_editavel(evento)
    if participacao.servidor_id is None:
        raise ValidationError(
            {"server": "Participação de servidor excluído é histórica e não pode ser editada."}
        )
    _validar_vinculo_servidor_servico(servidor, servico)

    servico_anterior = participacao.servico
    escala = _preparar_escala(evento, datas_trabalhadas)
    if escala is not None:
        quantidade_dias, quantidade_horas = _totais_escala(escala)
    else:
        totais_persistidos = _totais_escala_persistida(participacao)
        if totais_persistidos is not None:
            quantidade_dias, quantidade_horas = totais_persistidos
    servico_alterado = participacao.servico_id != servico.id
    participacao.servico = servico
    participacao.quantidade_dias = quantidade_dias
    participacao.quantidade_horas = quantidade_horas
    if servico_alterado:
        _atualizar_snapshot_servico(participacao, servico)
    if valor_final is not None:
        if participacao.tipo_vinculo == Servidor.VINCULO_MENSALISTA:
            raise ValidationError(
                {"finalAmount": "Mensalista não admite valor final distribuído manualmente."}
            )
        valor_final = quantizar_moeda(valor_final)
        if valor_final < ZERO:
            raise ValidationError({"finalAmount": "O valor final não pode ser negativo."})
        motivo_edicao = (motivo_edicao or "").strip()
        if not motivo_edicao:
            raise ValidationError({"editReason": "Informe o motivo da edição manual."})
        participacao.valor_anterior_edicao = participacao.valor_final
        participacao.valor_novo_edicao = valor_final
        participacao.valor_final = valor_final
        participacao.valor_editado_manualmente = True
        participacao.motivo_edicao = motivo_edicao
        participacao.editado_por = usuario
        participacao.editado_em = timezone.now()
    _atribuir_autoria(participacao, usuario)
    participacao.full_clean()
    try:
        participacao.save()
    except IntegrityError as error:
        raise ValidationError(
            {"server": "Este servidor já participa do evento neste serviço."}
        ) from error

    if escala is not None:
        _substituir_escala(participacao, escala)
    if servico_anterior.id != servico.id:
        _recalcular_grupo_bloqueado(evento, servico_anterior, usuario)
    _recalcular_grupo_bloqueado(evento, servico, usuario)
    participacao.refresh_from_db()
    return participacao


@transaction.atomic
def excluir_participacao(participacao, *, usuario):
    participacao, evento, _servidor = _bloquear_participacao_na_ordem(participacao)
    assert_demo_write_allowed(usuario, participacao, operation="delete participation")
    _validar_evento_editavel(evento)
    if participacao.servidor_id is None:
        raise ValidationError(
            {"server": "Participação histórica de servidor excluído não pode ser removida."}
        )
    servico = participacao.servico
    participacao._history_user = usuario
    participacao.delete()
    _recalcular_grupo_bloqueado(evento, servico, usuario)


@transaction.atomic
def restaurar_calculo_participacao(participacao, *, usuario):
    participacao, evento, _servidor = _bloquear_participacao_na_ordem(participacao)
    assert_demo_write_allowed(usuario, participacao, operation="restore participation")
    _validar_evento_editavel(evento)
    if participacao.servidor_id is None:
        raise ValidationError(
            {"server": "Participação histórica de servidor excluído não pode ser restaurada."}
        )
    participacao.valor_editado_manualmente = False
    participacao.motivo_edicao = ""
    participacao.valor_anterior_edicao = participacao.valor_final
    participacao.valor_novo_edicao = None
    participacao.editado_por = usuario
    participacao.editado_em = timezone.now()
    _atribuir_autoria(participacao, usuario)
    participacao.save(
        update_fields=[
            "valor_editado_manualmente",
            "motivo_edicao",
            "valor_anterior_edicao",
            "valor_novo_edicao",
            "editado_por",
            "editado_em",
            "atualizado_por",
            "atualizado_em",
        ]
    )
    _recalcular_grupo_bloqueado(evento, participacao.servico, usuario)
    participacao.refresh_from_db()
    return participacao


@transaction.atomic
def recalcular_evento(evento, *, usuario):
    evento = Evento.objects.select_for_update().get(pk=evento.pk)
    assert_demo_write_allowed(usuario, evento, operation="recalculate participation")
    _validar_evento_editavel(evento)
    servicos = list(
        evento.participacoes_servidores.order_by("servico_id")
        .values_list("servico_id", flat=True)
        .distinct()
    )

    for servico in Servico.objects.filter(id__in=servicos).order_by("id"):
        _recalcular_grupo_bloqueado(evento, servico, usuario)
    return len(servicos)
