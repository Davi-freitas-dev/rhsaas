from ipaddress import ip_address

from django.conf import settings


def get_axes_client_ip(request):
    """Return the real client IP for Axes when Django is behind a trusted proxy."""

    meta = getattr(request, "META", {}) or {}
    remote_addr = _valid_ip(meta.get("REMOTE_ADDR"))
    if not _is_trusted_proxy(remote_addr):
        return remote_addr

    real_ip = _valid_ip(meta.get("HTTP_X_REAL_IP"))
    if real_ip:
        return real_ip

    forwarded_for = meta.get("HTTP_X_FORWARDED_FOR", "")
    for candidate in reversed([part.strip() for part in forwarded_for.split(",")]):
        forwarded_ip = _valid_ip(candidate)
        if forwarded_ip:
            return forwarded_ip

    return remote_addr


def _is_trusted_proxy(remote_addr):
    trusted_proxies = getattr(
        settings,
        "AXES_TRUSTED_PROXY_REMOTE_ADDRS",
        ["127.0.0.1", "::1"],
    )
    return remote_addr in trusted_proxies


def _valid_ip(value):
    if not value:
        return None

    candidate = str(value).strip()
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None
