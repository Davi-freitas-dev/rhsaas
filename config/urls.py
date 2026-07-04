"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
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
            staff_member_required(SpectacularAPIView.as_view()),
            name="api_schema",
        ),
        path(
            "api/docs/",
            staff_member_required(SpectacularSwaggerView.as_view(url_name="api_schema")),
            name="api_docs",
        ),
        path(
            "api/redoc/",
            staff_member_required(SpectacularRedocView.as_view(url_name="api_schema")),
            name="api_redoc",
        ),
    ]


urlpatterns = [
    *api_docs_urlpatterns,
    path("admin/", admin.site.urls),
    path("manifest.webmanifest", pwa_manifest, name="pwa_manifest"),
    path("sw.js", service_worker, name="service_worker"),
    path("", include(("caixa.urls", "caixa"), namespace="caixa")),
]

handler403 = "caixa.views_errors.permission_denied"
