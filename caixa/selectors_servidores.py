from django.db.models import Count, Prefetch, Q

from .models_servidores import Servidor, ServidorServico


def queryset_servidores():
    return (
        Servidor.objects.all()
        .prefetch_related(
            Prefetch(
                "vinculos_servicos",
                queryset=ServidorServico.objects.select_related("servico").order_by(
                    "servico__nome", "id"
                ),
            )
        )
        .annotate(
            quantidade_eventos=Count(
                "participacoes_eventos__evento_id",
                distinct=True,
            )
        )
        .order_by("nome", "id")
    )


def filtrar_servidores(
    *,
    busca="",
    ativo="",
    tipo_vinculo="",
    servico_id="",
    pode_pesquisar_sensiveis=False,
):
    servidores = queryset_servidores()
    if busca:
        criterio_busca = Q(nome__icontains=busca)
        if pode_pesquisar_sensiveis:
            criterio_busca |= (
                Q(documento__icontains=Servidor.normalizar_documento(busca))
                | Q(email__icontains=busca)
                | Q(telefone__icontains=busca)
            )
        servidores = servidores.filter(criterio_busca)
    if ativo in {"true", "1", "ativo"}:
        servidores = servidores.filter(ativo=True)
    elif ativo in {"false", "0", "inativo"}:
        servidores = servidores.filter(ativo=False)
    if tipo_vinculo in {Servidor.VINCULO_DIARISTA, Servidor.VINCULO_MENSALISTA}:
        servidores = servidores.filter(tipo_vinculo=tipo_vinculo)
    if str(servico_id).isdigit():
        servidores = servidores.filter(
            vinculos_servicos__servico_id=int(servico_id),
            vinculos_servicos__ativo=True,
        )
    return servidores.distinct()


def obter_servidor(pk):
    return queryset_servidores().get(pk=pk)


def resumo_servidores(servidores):
    ids = servidores.values("id")
    base = Servidor.objects.filter(id__in=ids)
    return {
        "total": base.count(),
        "ativos": base.filter(ativo=True).count(),
        "inativos": base.filter(ativo=False).count(),
        "diaristas": base.filter(tipo_vinculo=Servidor.VINCULO_DIARISTA).count(),
        "mensalistas": base.filter(tipo_vinculo=Servidor.VINCULO_MENSALISTA).count(),
    }
