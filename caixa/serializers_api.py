"""Estruturas reutilizáveis dos contratos HTTP públicos."""

from rest_framework import serializers


class HttpApiErrorSerializer(serializers.Serializer):
    """Erro JSON canônico retornado pelas APIs SaaS.

    Alguns endpoints usam ``detail`` e outros retornam erros por campo em
    ``errors``; ambos fazem parte do contrato e permanecem documentados.
    """

    detail = serializers.CharField(required=False)
    errors = serializers.JSONField(required=False)
