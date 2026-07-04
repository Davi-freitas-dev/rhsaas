from django.conf import settings
from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.utils.crypto import salted_hmac


def password_reset_rate_limit_exceeded(request):
    attempts = settings.PASSWORD_RESET_RATE_LIMIT_ATTEMPTS
    window = settings.PASSWORD_RESET_RATE_LIMIT_WINDOW

    if attempts <= 0 or window <= 0:
        return False

    identifiers = [_client_ip(request)]
    email = request.POST.get("email", "").strip().lower()
    if email:
        identifiers.append(email)

    return any(_increment_attempts(identifier, attempts, window) for identifier in identifiers)


def _increment_attempts(identifier, attempts, window):
    cache_key = _cache_key(identifier)
    added = cache.add(cache_key, 1, window)
    if added:
        return False

    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, window)
        return False
    except InvalidCacheBackendError:
        return False

    return count > attempts


def _cache_key(identifier):
    digest = salted_hmac("password-reset-rate-limit", identifier).hexdigest()
    return f"password-reset:{digest}"


def _client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if settings.PASSWORD_RESET_TRUST_X_FORWARDED_FOR and forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR", "")
