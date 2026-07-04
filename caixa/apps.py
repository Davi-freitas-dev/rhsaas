from django.apps import AppConfig

class CaixaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "caixa"

    def ready(self):
        import caixa.signals
        import caixa.signals_pagamentos