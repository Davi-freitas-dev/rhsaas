import secrets

from django.conf import settings
from django.core.signing import BadSignature


DEMO_VISITOR_COOKIE_NAME = "rhsaas_demo_visitor"
DEMO_VISITOR_COOKIE_SALT = "rhsaas.demo.public.visitor.v1"
DEMO_LEASE_RESUME_ONLY_REQUEST_ATTR = "_rhsaas_demo_lease_resume_only"


def read_demo_visitor_identifier(request):
    try:
        return request.get_signed_cookie(
            DEMO_VISITOR_COOKIE_NAME,
            salt=DEMO_VISITOR_COOKIE_SALT,
            max_age=settings.DEMO_VISITOR_COOKIE_MAX_AGE,
        )
    except (BadSignature, KeyError):
        return None


def get_or_create_demo_visitor_identifier(request):
    return read_demo_visitor_identifier(request) or secrets.token_urlsafe(24)


def mark_demo_lease_resume_only(request):
    django_request = getattr(request, "_request", request)
    setattr(django_request, DEMO_LEASE_RESUME_ONLY_REQUEST_ATTR, True)


def is_demo_lease_resume_only(request):
    django_request = getattr(request, "_request", request)
    return bool(
        getattr(django_request, DEMO_LEASE_RESUME_ONLY_REQUEST_ATTR, False)
    )
