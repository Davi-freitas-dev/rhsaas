import calendar
from datetime import date

from django.utils import timezone

from .utils_datas import obter_periodo_mes_atual, obter_periodo_rapido
from .utils_request import normalizar_data_iso


PERIODOS_FRONTEND_PARA_RAPIDO = {
    "current-month": "mes_atual",
    "all": "todos",
}
PERIODOS_FRONTEND_INTERVALO = {"previous-month", "quarter", "semester", "year"}
PERIODOS_RAPIDOS_VALIDOS = {"hoje", "mes_atual", "30_dias", "todos", "vencidos"}


def normalizar_periodo_frontend(valor):
    valor = str(valor or "").strip()
    if valor in PERIODOS_FRONTEND_PARA_RAPIDO or valor in PERIODOS_FRONTEND_INTERVALO:
        return valor
    return ""


def normalizar_periodo_rapido(valor):
    valor = str(valor or "").strip()
    return valor if valor in PERIODOS_RAPIDOS_VALIDOS else ""


def normalizar_intervalo_datas(data_inicial, data_final):
    if data_inicial and data_final and data_inicial > data_final:
        return data_final, data_inicial
    return data_inicial, data_final


def resolver_intervalo_periodo_canonico(params):
    periodo = normalizar_periodo_frontend(params.get("period"))
    periodo_rapido = normalizar_periodo_rapido(params.get("quickPeriod"))
    data_inicial = normalizar_data_iso(params.get("startDate"))
    data_final = normalizar_data_iso(params.get("endDate"))
    data_inicial, data_final = normalizar_intervalo_datas(data_inicial, data_final)

    if not (data_inicial or data_final):
        if periodo_rapido:
            data_inicial, data_final = obter_periodo_rapido(periodo_rapido)
        elif periodo:
            data_inicial, data_final = intervalo_periodo_frontend(periodo)

    return {
        "period": periodo,
        "quickPeriod": periodo_rapido,
        "startDate": data_inicial or "",
        "endDate": data_final or "",
    }


def intervalo_periodo_frontend(periodo):
    hoje = timezone.localdate()

    if periodo == "current-month":
        return inicio_mes(hoje).isoformat(), fim_mes(hoje).isoformat()

    if periodo == "previous-month":
        referencia = somar_meses(hoje, -1)
        return inicio_mes(referencia).isoformat(), fim_mes(referencia).isoformat()

    if periodo == "quarter":
        return inicio_mes(somar_meses(hoje, -2)).isoformat(), fim_mes(hoje).isoformat()

    if periodo == "semester":
        return inicio_mes(somar_meses(hoje, -5)).isoformat(), fim_mes(hoje).isoformat()

    if periodo == "year":
        return date(hoje.year, 1, 1).isoformat(), date(hoje.year, 12, 31).isoformat()

    return "", ""


def somar_meses(data_base, meses):
    mes = data_base.month - 1 + meses
    ano = data_base.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data_base.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def inicio_mes(data_base):
    return data_base.replace(day=1)


def fim_mes(data_base):
    ultimo_dia = calendar.monthrange(data_base.year, data_base.month)[1]
    return data_base.replace(day=ultimo_dia)


def resolver_periodo_rapido_com_sessao(filtros, session, session_key):
    data_inicial_raw = normalizar_data_iso(filtros["data_inicial"])
    data_final_raw = normalizar_data_iso(filtros["data_final"])
    data_inicial = data_inicial_raw
    data_final = data_final_raw
    periodo_rapido = filtros["periodo_rapido"]
    tem_filtro_personalizado_sem_periodo = _tem_filtro_personalizado_sem_periodo(
        filtros,
        data_inicial_raw,
        data_final_raw,
        periodo_rapido,
    )

    if periodo_rapido:
        periodo_inicial, periodo_final = obter_periodo_rapido(periodo_rapido)

        if periodo_inicial is not None:
            if periodo_rapido == "vencidos" and (data_inicial_raw or data_final_raw):
                data_inicial = data_inicial_raw
                data_final = data_final_raw
            else:
                data_inicial = periodo_inicial
                data_final = periodo_final
            session[session_key] = periodo_rapido
        else:
            data_inicial, data_final = obter_periodo_mes_atual(data_inicial, data_final)

    elif not any(filtros.values()):
        periodo_salvo = session.get(session_key, "mes_atual")
        periodo_inicial, periodo_final = obter_periodo_rapido(periodo_salvo)

        if periodo_inicial is not None:
            data_inicial = periodo_inicial
            data_final = periodo_final
            periodo_rapido = periodo_salvo
        else:
            data_inicial, data_final = obter_periodo_mes_atual(data_inicial, data_final)

    elif tem_filtro_personalizado_sem_periodo:
        data_inicial = data_inicial_raw
        data_final = data_final_raw

    else:
        data_inicial, data_final = obter_periodo_mes_atual(data_inicial, data_final)

    hoje = timezone.localdate()
    deve_preencher_periodo_padrao = not tem_filtro_personalizado_sem_periodo

    if (
        deve_preencher_periodo_padrao
        and not data_inicial
        and periodo_rapido not in ["todos", "vencidos"]
    ):
        data_inicial = hoje.replace(day=1).isoformat()

    if not data_final and periodo_rapido == "vencidos":
        data_final = hoje.isoformat()
    elif deve_preencher_periodo_padrao and not data_final and periodo_rapido != "todos":
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        data_final = hoje.replace(day=ultimo_dia).isoformat()

    return {
        **filtros,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "periodo_rapido": periodo_rapido,
    }


def _tem_filtro_personalizado_sem_periodo(
    filtros,
    data_inicial,
    data_final,
    periodo_rapido,
):
    if data_inicial or data_final or periodo_rapido:
        return False

    campos_periodo = {"data_inicial", "data_final", "periodo_rapido"}
    return any(
        valor not in (None, "", [], (), {})
        for chave, valor in filtros.items()
        if chave not in campos_periodo
    )
