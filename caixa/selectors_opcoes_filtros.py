from types import SimpleNamespace

from .models import Cliente, Evento
from .models_dividas import Credor, DividaFinanceira, ParcelaDivida
from .services_dimensoes_operacionais import codigo_contrato_visivel_evento


EVENTO_FILTRO_CAMPOS = (
    "id",
    "numero",
    "nome_evento",
    "data_inicio",
    "status",
    "cliente_id",
    "cliente__nome_razao_social",
    "orcamento__numero",
)
CLIENTE_FILTRO_CAMPOS = ("id", "nome_razao_social")


def _eventos_filtro_base():
    return Evento.objects.select_related("cliente", "orcamento").only(
        *EVENTO_FILTRO_CAMPOS
    )


def _ordenar_eventos_recentes(queryset):
    return queryset.order_by(
        "-data_inicio",
        "-id",
    )


def listar_eventos_filtro():
    return _eventos_filtro_base().order_by(
        "-data_inicio",
        "nome_evento",
    )


def listar_eventos_filtro_recentes():
    return _ordenar_eventos_recentes(_eventos_filtro_base())


def _listar_eventos_filtro_por_relacao(nome_relacao):
    return _ordenar_eventos_recentes(
        _eventos_filtro_base()
        .filter(**{f"{nome_relacao}__isnull": False})
        .distinct()
    )


def listar_eventos_filtro_com_custos_servico():
    return _listar_eventos_filtro_por_relacao("custos_servicos")


def listar_eventos_filtro_com_custos_extras():
    return _listar_eventos_filtro_por_relacao("custos_extras")


def listar_clientes_filtro():
    return Cliente.objects.only(*CLIENTE_FILTRO_CAMPOS).order_by(
        "nome_razao_social",
    )


def listar_contratos_visuais_filtro():
    contratos = {}
    for evento in listar_eventos_filtro_recentes():
        codigo = codigo_contrato_visivel_evento(evento)
        if not codigo or codigo in contratos:
            continue
        contratos[codigo] = SimpleNamespace(
            id=codigo,
            codigo=codigo,
            nome=evento.nome_evento,
            status=evento.status,
            cliente_id=evento.cliente_id,
            cliente=evento.cliente,
        )
    return list(contratos.values())


def listar_credores_fcf_filtro():
    return (
        Credor.objects.filter(ativo=True)
        .order_by("nome", "id")
        .values_list("nome", flat=True)
    )


def listar_credores_cadastrados_fcf_filtro():
    return Credor.objects.filter(ativo=True).order_by("nome", "id")


def listar_tipos_divida_fcf_filtro():
    return DividaFinanceira.TIPO_CHOICES


def listar_status_parcelas_fcf_filtro():
    return ParcelaDivida.STATUS_CHOICES


def montar_opcoes_eventos_clientes_filtro():
    return {
        "eventos_filtro": listar_eventos_filtro(),
        "clientes_filtro": listar_clientes_filtro(),
        "contratos_filtro": listar_contratos_visuais_filtro(),
    }
