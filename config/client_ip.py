from ipaddress import ip_address, ip_network

from django.conf import settings


_CLOUDFLARE_PROXY_NETWORKS = tuple(
    ip_network(cidr)
    for cidr in (
        "173.245.48.0/20",
        "103.21.244.0/22",
        "103.22.200.0/22",
        "103.31.4.0/22",
        "141.101.64.0/18",
        "108.162.192.0/18",
        "190.93.240.0/20",
        "188.114.96.0/20",
        "197.234.240.0/22",
        "198.41.128.0/17",
        "162.158.0.0/15",
        "104.16.0.0/13",
        "104.24.0.0/14",
        "172.64.0.0/13",
        "131.0.72.0/22",
        "2400:cb00::/32",
        "2606:4700::/32",
        "2803:f800::/32",
        "2405:b500::/32",
        "2405:8100::/32",
        "2a06:98c0::/29",
        "2c0f:f248::/32",
    )
)


def get_axes_client_ip(request):
    """Return the real client IP for Axes when Django is behind a trusted proxy."""

    meta = getattr(request, "META", {}) or {}
    remote_addr = _valid_ip(meta.get("REMOTE_ADDR"))
    if not _is_trusted_proxy(remote_addr):
        return remote_addr

    cloudflare_connecting_ip = _valid_ip(meta.get("HTTP_CF_CONNECTING_IP"))
    real_ip = _valid_ip(meta.get("HTTP_X_REAL_IP"))
    if real_ip:
        if cloudflare_connecting_ip and _is_cloudflare_proxy(real_ip):
            return cloudflare_connecting_ip
        return real_ip

    forwarded_for = meta.get("HTTP_X_FORWARDED_FOR", "")
    for candidate in reversed([part.strip() for part in forwarded_for.split(",")]):
        forwarded_ip = _valid_ip(candidate)
        if forwarded_ip:
            if cloudflare_connecting_ip and _is_cloudflare_proxy(forwarded_ip):
                return cloudflare_connecting_ip
            return forwarded_ip

    return remote_addr


def get_client_network_identifier(request):
    """Return a stable public network identifier for demo lease quotas."""

    client_ip = get_axes_client_ip(request)
    if not client_ip:
        return None

    address = ip_address(client_ip)
    if address.version == 4:
        return str(address)

    if address.ipv4_mapped:
        return str(address.ipv4_mapped)

    return str(ip_network(f"{address}/64", strict=False))


def _is_trusted_proxy(remote_addr):
    trusted_proxies = getattr(
        settings,
        "AXES_TRUSTED_PROXY_REMOTE_ADDRS",
        ["127.0.0.1", "::1"],
    )
    return remote_addr in trusted_proxies


def _is_cloudflare_proxy(value):
    address = ip_address(value)
    return any(address in network for network in _CLOUDFLARE_PROXY_NETWORKS)


def _valid_ip(value):
    if not value:
        return None

    candidate = str(value).strip()
    try:
        return str(ip_address(candidate))
    except ValueError:
        return None
