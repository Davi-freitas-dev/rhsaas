from rest_framework.throttling import UserRateThrottle


class AuthLoginRateThrottle(UserRateThrottle):
    scope = "auth_login"
