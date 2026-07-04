TIPO_FLUXO_ENTRADA = "entrada"
TIPO_FLUXO_SAIDA = "saida"

TIPO_CUSTO_DIARIAS = "diarias"
TIPO_CUSTO_ALIMENTACAO = "alimentacao"
TIPO_CUSTO_TRANSPORTE = "transporte"

STATUS_PLANEJADO = "planejado"
STATUS_PARCIAL = "parcial"
STATUS_REALIZADO = "realizado"
STATUS_CANCELADO = "cancelado"

STATUS_PENDENTE = "pendente"
STATUS_PAGO = "pago"
STATUS_VENCIDO = "vencido"

TIPO_FLUXO_CHOICES = [
    (TIPO_FLUXO_ENTRADA, "Entrada"),
    (TIPO_FLUXO_SAIDA, "Saída"),
]

STATUS_PREVISTO_REALIZADO_CHOICES = [
    (STATUS_PLANEJADO, "Planejado"),
    (STATUS_PARCIAL, "Parcial"),
    (STATUS_REALIZADO, "Realizado"),
    (STATUS_CANCELADO, "Cancelado"),
]

STATUS_PAGAMENTO_CHOICES = [
    (STATUS_PENDENTE, "Pendente"),
    (STATUS_PARCIAL, "Parcial"),
    (STATUS_PAGO, "Pago"),
    (STATUS_VENCIDO, "Vencido"),
    (STATUS_CANCELADO, "Cancelado"),
]

TIPOS_CUSTO_SERVICO = {
    TIPO_CUSTO_DIARIAS: {
        "rotulo": "Diarias",
        "saldo": "saldo_diarias",
        "previsto": "valor_diarias",
        "pago": "total_pago_diarias",
        "quitado": "diarias_quitadas",
    },
    TIPO_CUSTO_ALIMENTACAO: {
        "rotulo": "Alimentacao",
        "saldo": "saldo_alimentacao",
        "previsto": "valor_alimentacao",
        "pago": "total_pago_alimentacao",
        "quitado": "alimentacao_quitada",
    },
    TIPO_CUSTO_TRANSPORTE: {
        "rotulo": "Transporte",
        "saldo": "saldo_transporte",
        "previsto": "valor_transporte",
        "pago": "total_pago_transporte",
        "quitado": "transporte_quitado",
    },
}
