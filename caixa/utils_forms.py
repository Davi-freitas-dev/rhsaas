def adicionar_erros_validacao(form, erro):
    if hasattr(erro, "message_dict"):
        for campo, mensagens in erro.message_dict.items():
            form.add_error(campo if campo in form.fields else None, mensagens)
        return

    for mensagem in erro.messages:
        form.add_error(None, mensagem)
