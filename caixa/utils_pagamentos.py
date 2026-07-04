from decimal import Decimal


def mensagem_sucesso_pagamento(form, mensagem_padrao):
    valor_pagamento = form.cleaned_data.get("valor_pagamento") or Decimal("0.00")

    if form.cleaned_data.get("baixar_saldo") and valor_pagamento <= Decimal("0.00"):
        return "Pendência restante baixada com sucesso."

    if form.cleaned_data.get("baixar_saldo"):
        return "Pagamento registrado e pendência restante baixada com sucesso."

    return mensagem_padrao
