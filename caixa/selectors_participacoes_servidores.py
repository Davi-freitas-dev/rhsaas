from .models_servidores import ParticipacaoServidorEvento


def queryset_participacoes():
    return ParticipacaoServidorEvento.objects.select_related(
        "servidor",
        "evento",
        "evento__cliente",
        "servico",
        "criado_por",
        "atualizado_por",
        "editado_por",
        "servidor_excluido_por",
    ).prefetch_related("dias_trabalhados").order_by(
        "servico_nome_snapshot",
        "servidor_nome_snapshot",
        "id",
    )


def listar_participacoes_evento(evento):
    return queryset_participacoes().filter(evento=evento)


def obter_participacao(pk):
    return queryset_participacoes().get(pk=pk)
