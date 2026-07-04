from .services_dimensoes_operacionais import (
    codigo_contrato_visivel_evento,
    relacao_carregada,
)


def obter_dimensao_operacional(objeto):
    if _objeto_e_evento(objeto):
        evento = objeto
        return None, evento

    evento = relacao_carregada(objeto, "evento")

    if not evento:
        divida = relacao_carregada(objeto, "divida_financeira")
        if divida:
            evento = relacao_carregada(divida, "evento")

    return None, evento


def _objeto_e_evento(objeto):
    meta = getattr(objeto, "_meta", None)
    return getattr(meta, "model_name", "") == "evento"


def serializar_dimensao_operacional(objeto):
    contrato, evento = obter_dimensao_operacional(objeto)
    contract_code_proprio = _codigo_contrato_proprio(objeto)
    contract_code = (
        codigo_contrato_visivel_evento(evento) if evento else ""
    ) or contract_code_proprio
    contract_label = contract_code
    cliente = relacao_carregada(objeto, "cliente")
    if cliente is None and evento:
        cliente = relacao_carregada(evento, "cliente")
    client_trade_name = cliente.nome_fantasia if cliente else ""
    client_display_name = str(cliente) if cliente else ""

    return {
        "contractCode": contract_code,
        "contractName": "",
        "contractLabel": contract_label,
        "contract": contract_code,
        "contrato_codigo": contract_code,
        "eventId": evento.id if evento else None,
        "eventName": evento.nome_evento if evento else "",
        "eventNumber": evento.numero if evento else "",
        "eventLabel": str(evento) if evento else "",
        "evento_id": evento.id if evento else None,
        "evento_nome": evento.nome_evento if evento else "",
        "evento_numero": evento.numero if evento else "",
        "evento_label": str(evento) if evento else "",
        "clientId": cliente.id if cliente else None,
        "clientName": cliente.nome_razao_social if cliente else "",
        "clientTradeName": client_trade_name,
        "clientDisplayName": client_display_name,
        "cliente_id": cliente.id if cliente else None,
        "cliente_nome": cliente.nome_razao_social if cliente else "",
        "cliente_nome_fantasia": client_trade_name,
        "cliente_label": client_display_name,
    }


def _codigo_contrato_proprio(objeto):
    meta = getattr(objeto, "_meta", None)
    if getattr(meta, "model_name", "") != "orcamento":
        return ""

    return str(getattr(objeto, "numero", "") or "").strip()


def serializar_contrato_visual_opcao(contrato):
    label = f"{contrato.codigo} - {contrato.nome}" if contrato.nome else contrato.codigo
    cliente = relacao_carregada(contrato, "cliente")
    client_name = cliente.nome_razao_social if cliente else ""
    return {
        "id": str(contrato.codigo),
        "value": str(contrato.codigo),
        "label": label,
        "contractCode": contrato.codigo,
        "contractName": contrato.nome,
        "contract": contrato.codigo,
        "name": contrato.nome,
        "clientId": contrato.cliente_id,
        "clientName": client_name,
        "description": client_name,
        "contractDescription": client_name,
    }


def serializar_evento_operacional_opcao(evento, event_description_format="label"):
    cliente = relacao_carregada(evento, "cliente")
    contrato_codigo = codigo_contrato_visivel_evento(evento)
    contract_name = ""
    label = f"{contrato_codigo} - {evento.nome_evento}"
    client_name = cliente.nome_razao_social if cliente else ""
    start_date = evento.data_inicio.isoformat() if evento.data_inicio else ""
    event_date_label = formatar_data_br(evento.data_inicio)
    description = start_date if event_description_format == "iso" else event_date_label
    return {
        "id": str(evento.id),
        "value": str(evento.id),
        "label": label,
        "name": evento.nome_evento,
        "eventId": evento.id,
        "eventName": evento.nome_evento,
        "eventNumber": evento.numero,
        "startDate": start_date,
        "dataInicio": start_date,
        "contractCode": contrato_codigo,
        "contractName": contract_name,
        "contract": contrato_codigo,
        "clientId": evento.cliente_id,
        "clientName": client_name,
        "description": description,
        "eventDateLabel": event_date_label,
        "numero": evento.numero,
    }


def serializar_cliente_operacional_opcao(cliente):
    return {
        "id": str(cliente.id),
        "value": str(cliente.id),
        "label": cliente.nome_razao_social,
        "name": cliente.nome_razao_social,
        "clientId": cliente.id,
        "clientName": cliente.nome_razao_social,
    }


def limitar_opcoes(itens, limite):
    return itens[:limite] if limite else itens


def serializar_opcoes_entidades_operacionais(
    contexto,
    *,
    incluir_clientes=False,
    limite_contratos=None,
    limite_eventos=None,
    limite_clientes=None,
    event_description_format="label",
):
    contratos = [
        serializar_contrato_visual_opcao(contrato)
        for contrato in limitar_opcoes(
            contexto["contratos_filtro"],
            limite_contratos,
        )
    ]
    eventos = [
        serializar_evento_operacional_opcao(evento, event_description_format)
        for evento in limitar_opcoes(contexto["eventos_filtro"], limite_eventos)
    ]
    opcoes = {
        "contracts": contratos,
        "events": eventos,
    }

    if incluir_clientes:
        opcoes["clients"] = [
            serializar_cliente_operacional_opcao(cliente)
            for cliente in limitar_opcoes(contexto["clientes_filtro"], limite_clientes)
        ]

    return opcoes


def serializar_opcoes_dimensoes_operacionais(contexto):
    opcoes = serializar_opcoes_entidades_operacionais(contexto)
    contratos = opcoes["contracts"]
    eventos = opcoes["events"]

    return {
        "contratos": contratos,
        "contracts": contratos,
        "eventos": eventos,
        "events": eventos,
    }


def formatar_data_br(valor):
    return valor.strftime("%d/%m/%Y") if valor else ""
