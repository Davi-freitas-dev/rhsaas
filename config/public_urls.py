from django.urls import path

from tenancy.views_demo_public import api_demo_lease, api_health


urlpatterns = [
    path("api/health/", api_health, name="api_health"),
    path("api/demo/lease/", api_demo_lease, name="api_demo_lease"),
]
