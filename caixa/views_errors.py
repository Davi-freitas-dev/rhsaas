from .permissions import api_permission_denied_response


def permission_denied(request, exception=None):
    return api_permission_denied_response()
