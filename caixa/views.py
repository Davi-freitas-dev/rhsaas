from .services_static import static_file_response


def pwa_manifest(request):
    return static_file_response(
        "caixa/manifest.webmanifest",
        "application/manifest+json",
        "Manifest não encontrado.",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


def service_worker(request):
    return static_file_response(
        "caixa/sw.js",
        "application/javascript",
        "Service worker não encontrado.",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache, max-age=0, must-revalidate",
        },
    )
