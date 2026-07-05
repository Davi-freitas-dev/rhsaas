from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from caixa.views import pwa_manifest, service_worker

api_docs_urlpatterns = []
if settings.ENABLE_API_DOCS:
    api_docs_urlpatterns = [
        path(
            "api/schema/",
            staff_member_required(
                SpectacularAPIView.as_view(),
                login_url="caixa:login",
            ),
            name="api_schema",
        ),
        path(
            "api/docs/",
            staff_member_required(
                SpectacularSwaggerView.as_view(url_name="api_schema"),
                login_url="caixa:login",
            ),
            name="api_docs",
        ),
        path(
            "api/redoc/",
            staff_member_required(
                SpectacularRedocView.as_view(url_name="api_schema"),
                login_url="caixa:login",
            ),
            name="api_redoc",
        ),
    ]


urlpatterns = [
    *api_docs_urlpatterns,
    path("manifest.webmanifest", pwa_manifest, name="pwa_manifest"),
    path("sw.js", service_worker, name="service_worker"),
    path("", include(("caixa.urls", "caixa"), namespace="caixa")),
]

handler403 = "caixa.views_errors.permission_denied"
