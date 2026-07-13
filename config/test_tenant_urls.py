from django.contrib import admin
from django.urls import path

from .tenant_urls import handler403, urlpatterns as tenant_urlpatterns


urlpatterns = [
    path("admin/", admin.site.urls),
    *tenant_urlpatterns,
]
