from .models import Evento


def exclusao_originada_por_evento(origin):
    """Indica se um delete ORM foi iniciado por Evento ou por seu queryset."""
    if origin is None:
        return False

    origin_model = getattr(origin, "model", origin.__class__)
    return isinstance(origin_model, type) and issubclass(origin_model, Evento)
