from django.conf import settings
from django.http import HttpResponse


def _setdefault_header(response, header, value):
    if header not in response:
        response[header] = value


def _append_vary_origin(response):
    vary = response.get("Vary", "")
    valores = [item.strip() for item in vary.split(",") if item.strip()]
    if "Origin" not in valores:
        valores.append("Origin")
    response["Vary"] = ", ".join(valores)


class ConfiguredCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        origin_allowed = origin in getattr(settings, "CORS_ALLOWED_ORIGINS", [])

        if request.method == "OPTIONS" and origin_allowed:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin_allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = (
                "true" if getattr(settings, "CORS_ALLOW_CREDENTIALS", False) else "false"
            )
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
            _append_vary_origin(response)

        return response


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        excluded_prefixes = getattr(settings, "CSP_EXCLUDED_PATH_PREFIXES", ())
        if not any(request.path_info.startswith(prefix) for prefix in excluded_prefixes):
            _setdefault_header(
                response,
                "Content-Security-Policy",
                getattr(settings, "CONTENT_SECURITY_POLICY", ""),
            )

        _setdefault_header(
            response,
            "Permissions-Policy",
            getattr(settings, "PERMISSIONS_POLICY", ""),
        )
        _setdefault_header(
            response,
            "Cross-Origin-Opener-Policy",
            getattr(settings, "CROSS_ORIGIN_OPENER_POLICY", "same-origin"),
        )
        _setdefault_header(
            response,
            "Cross-Origin-Resource-Policy",
            getattr(settings, "CROSS_ORIGIN_RESOURCE_POLICY", "same-origin"),
        )
        _setdefault_header(
            response,
            "X-Permitted-Cross-Domain-Policies",
            getattr(settings, "X_PERMITTED_CROSS_DOMAIN_POLICIES", "none"),
        )
        return response
