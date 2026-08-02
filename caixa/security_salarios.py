from django.db.models import Q

from .models_custo_fixo import CustoFixo
from .permissions import VIEW_SERVER_SALARY_PERMISSION


Q_CUSTO_SALARIAL = Q(origem_recorrencia="salario") | Q(categoria="salario")


def usuario_pode_ver_salarios(usuario):
    return bool(
        usuario
        and getattr(usuario, "is_authenticated", False)
        and usuario.has_perm(VIEW_SERVER_SALARY_PERMISSION)
    )


def usuario_pode_acessar_custos_salariais(usuario):
    """Política única para qualquer leitura que possa revelar custo salarial.

    Uma ocorrência salarial, seu histórico e totais derivados são o mesmo dado
    sensível. Chamadores devem aplicar esta decisão antes de montar consultas ou
    agregações, e não apenas antes de serializar a resposta.
    """
    return usuario_pode_ver_salarios(usuario)


def filtrar_ocorrencias_salariais_por_usuario(queryset, usuario):
    """Retorna um queryset vazio sem autorização, antes de qualquer agregação."""
    if not usuario_pode_acessar_custos_salariais(usuario):
        return queryset.none()
    return queryset.filter(Q_CUSTO_SALARIAL)


def filtrar_custos_fixos_por_salario(queryset, usuario=None, *, excluir=None):
    deve_excluir = (
        not usuario_pode_ver_salarios(usuario)
        if excluir is None
        else bool(excluir)
    )
    return queryset.exclude(Q_CUSTO_SALARIAL) if deve_excluir else queryset


def ids_custos_salariais():
    return CustoFixo.objects.filter(Q_CUSTO_SALARIAL).values_list("id", flat=True)


def filtrar_lancamentos_por_salario(queryset, usuario=None, *, excluir=None):
    deve_excluir = (
        not usuario_pode_ver_salarios(usuario)
        if excluir is None
        else bool(excluir)
    )
    if not deve_excluir:
        return queryset
    return queryset.exclude(
        Q(custo_fixo__origem_recorrencia="salario")
        | Q(custo_fixo__categoria="salario")
    )


def filtrar_obrigacoes_por_salario(queryset, usuario=None, *, excluir=None):
    deve_excluir = (
        not usuario_pode_ver_salarios(usuario)
        if excluir is None
        else bool(excluir)
    )
    if not deve_excluir:
        return queryset
    return queryset.exclude(
        Q(custo_fixo__origem_recorrencia="salario")
        | Q(custo_fixo__categoria="salario")
    )


def filtrar_baixas_por_salario(queryset, usuario=None, *, excluir=None):
    deve_excluir = (
        not usuario_pode_ver_salarios(usuario)
        if excluir is None
        else bool(excluir)
    )
    if not deve_excluir:
        return queryset
    return queryset.exclude(
        Q(custo_fixo__origem_recorrencia="salario")
        | Q(custo_fixo__categoria="salario")
        | Q(
            alocacoes__obrigacao__custo_fixo__origem_recorrencia="salario"
        )
        | Q(alocacoes__obrigacao__custo_fixo__categoria="salario")
    ).distinct()


def filtrar_alocacoes_baixa_por_salario(
    queryset,
    usuario=None,
    *,
    excluir=None,
):
    deve_excluir = (
        not usuario_pode_ver_salarios(usuario)
        if excluir is None
        else bool(excluir)
    )
    if not deve_excluir:
        return queryset
    return queryset.exclude(
        Q(obrigacao__custo_fixo__origem_recorrencia="salario")
        | Q(obrigacao__custo_fixo__categoria="salario")
        | Q(baixa__custo_fixo__origem_recorrencia="salario")
        | Q(baixa__custo_fixo__categoria="salario")
    )


def filtrar_itens_obrigacoes_salariais(itens, *, excluir):
    if not excluir:
        return itens
    ids_relevantes = {
        item.get("source_id")
        for item in itens
        if item.get("source") == "custo_fixo"
        and item.get("source_id") is not None
    }
    ids = set(
        CustoFixo.objects.filter(
            Q_CUSTO_SALARIAL,
            id__in=ids_relevantes,
        ).values_list("id", flat=True)
    )
    return [
        item
        for item in itens
        if not (
            item.get("source") == "custo_fixo"
            and item.get("source_id") in ids
        )
    ]
