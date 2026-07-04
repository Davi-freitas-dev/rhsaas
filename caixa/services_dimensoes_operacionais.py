def validar_dimensao_operacional_por_evento(objeto, erros):
    return


def dados_dimensao_operacional(objeto):
    evento = getattr(objeto, "evento", None)
    cliente = None

    if evento:
        cliente = evento.cliente

    return {
        "cliente": cliente,
        "evento": evento,
    }


def codigo_contrato_visivel_evento(evento):
    if evento is None:
        return ""

    orcamento = relacao_carregada(evento, "orcamento")
    if orcamento is not None:
        return getattr(orcamento, "numero", "") or ""

    event_number = str(getattr(evento, "numero", "") or "").strip()
    if event_number.startswith("EVT-"):
        return event_number[4:].strip() or event_number

    return getattr(evento, "contrato_codigo", "") or event_number


def serializar_dimensao_operacional_financeira(objeto):
    if objeto is None:
        return _dimensao_operacional_vazia()

    evento = relacao_carregada(objeto, "evento")

    cliente = relacao_carregada(objeto, "cliente")
    if cliente is None and evento is not None:
        cliente = relacao_carregada(evento, "cliente")
    client_trade_name = getattr(cliente, "nome_fantasia", "") if cliente else ""
    client_display_name = str(cliente) if cliente else ""

    contract_code = ""
    if evento is not None:
        contract_code = codigo_contrato_visivel_evento(evento)

    return {
        "contractCode": contract_code,
        "contractName": "",
        "contractLabel": contract_code,
        "eventId": getattr(evento, "id", None) if evento is not None else None,
        "eventName": getattr(evento, "nome_evento", "") if evento is not None else "",
        "eventNumber": getattr(evento, "numero", "") if evento is not None else "",
        "eventLabel": str(evento) if evento is not None else "",
        "clientId": getattr(cliente, "id", None) if cliente is not None else None,
        "clientName": (
            getattr(cliente, "nome_razao_social", "") if cliente is not None else ""
        ),
        "clientTradeName": client_trade_name,
        "clientDisplayName": client_display_name,
    }


def relacao_carregada(objeto, nome):
    if objeto is None:
        return None
    state = getattr(objeto, "_state", None)
    if state is None:
        return getattr(objeto, nome, None)
    return state.fields_cache.get(nome)


def relacoes_multiplas_carregadas(objeto, nome):
    if objeto is None:
        return []
    state = getattr(objeto, "_state", None)
    if state is None:
        valor = getattr(objeto, nome, [])
        return list(valor or [])
    cache = getattr(objeto, "_prefetched_objects_cache", {})
    if nome not in cache:
        return []
    return list(cache[nome])


def dados_parcela_divida_sem_lazy(parcela):
    divida = relacao_carregada(parcela, "divida")
    rotulo_informado = ""
    if getattr(parcela, "_state", None) is None:
        rotulo_informado = getattr(parcela, "rotulo_parcela", "")
    numero_parcela = getattr(parcela, "numero_parcela", "") or rotulo_informado
    total_parcelas = (
        getattr(divida, "quantidade_parcelas", None) if divida is not None else None
    )
    rotulo_parcela = (
        rotulo_informado
        if rotulo_informado and not total_parcelas
        else f"{numero_parcela}/{total_parcelas or numero_parcela}"
    )
    credor = getattr(divida, "credor", "") if divida is not None else ""
    descricao = getattr(divida, "descricao", "") if divida is not None else ""

    return {
        "divida": divida,
        "descricao": descricao,
        "referencia": (
            f"{credor} / Parcela {rotulo_parcela}"
            if credor
            else f"Parcela {rotulo_parcela}"
        ),
        "rotuloParcela": rotulo_parcela,
    }


def _dimensao_operacional_vazia():
    return {
        "contractCode": "",
        "contractName": "",
        "contractLabel": "",
        "eventId": None,
        "eventName": "",
        "eventNumber": "",
        "eventLabel": "",
        "clientId": None,
        "clientName": "",
        "clientTradeName": "",
        "clientDisplayName": "",
    }
