import resend
from django.conf import settings

resend.api_key = settings.RESEND_API_KEY


def enviar_email(destino, assunto, html):
    resend.Emails.send({
        "from": settings.DEFAULT_FROM_EMAIL,
        "to": destino,
        "subject": assunto,
        "html": html,
    })