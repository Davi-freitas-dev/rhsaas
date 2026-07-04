import calendar
from datetime import timedelta
from django.utils import timezone


def obter_periodo_mes_atual(data_inicial="", data_final=""):
    hoje = timezone.localdate()

    if not data_inicial:
        data_inicial = hoje.replace(day=1).isoformat()

    if not data_final:
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        data_final = hoje.replace(day=ultimo_dia).isoformat()

    return data_inicial, data_final


def obter_periodo_rapido(periodo):
    hoje = timezone.localdate()

    if periodo == "hoje":
        return hoje.isoformat(), hoje.isoformat()

    if periodo == "mes_atual":
        primeiro = hoje.replace(day=1)
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        ultimo = hoje.replace(day=ultimo_dia)
        return primeiro.isoformat(), ultimo.isoformat()

    if periodo == "30_dias":
        inicial = hoje - timedelta(days=29)
        return inicial.isoformat(), hoje.isoformat()

    if periodo == "todos":
        return "", ""

    if periodo == "vencidos":
        return "", hoje.isoformat()

    return None, None