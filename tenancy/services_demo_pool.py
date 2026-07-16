import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from caixa.models import (
    Cliente,
    ConfiguracaoFinanceira,
    Orcamento,
    OrcamentoItem,
    Servico,
)
from caixa.permissions import PERMISSION_PROFILES, sincronizar_grupos_permissoes
from tenancy.command_guards import (
    demo_public_pool_schema_names,
    ensure_demo_permanent_tenant_schema,
    ensure_demo_pool_schema,
    ensure_demo_public_pool_schema,
)
from tenancy.models import DemoTenantSlot, Domain


DEMO_API_DOMAIN_SUFFIX = "api-demo-rh.taquiondev.com.br"
DEMO_PUBLIC_GROUP_NAME = "Demo Publica"
DEMO_PUBLIC_USERNAME = "demo"


class DemoPoolUnavailable(Exception):
    pass


class DemoPoolFull(Exception):
    pass


class DemoNetworkLimitExceeded(Exception):
    pass


class DemoLeaseResumeUnavailable(Exception):
    pass


class DemoAccessTokenInvalid(Exception):
    pass


@dataclass(frozen=True)
class DemoLeaseGrant:
    slot_code: str
    api_base_url: str
    expires_at: object
    exchange_token: str
    reused: bool


@dataclass(frozen=True)
class DemoPublicStatus:
    total: int
    available: int
    active_slot_code: str | None
    active_expires_at: object | None


@dataclass(frozen=True)
class DemoExpirationResult:
    slot_code: str
    sessions_removed: int
    axes_rows_removed: int
    cache_keys_removed: int
    user_deactivated: bool


def hash_demo_identifier(purpose, value):
    normalized_value = str(value or "").strip()
    if not normalized_value:
        raise ValueError("Identificador anonimo da demo nao pode ficar vazio.")

    message = f"rhsaas-demo:{purpose}:{normalized_value}".encode("utf-8")
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def has_active_demo_lease(*, visitor_identifier, now=None):
    if not settings.DEMO_PUBLIC_LEASE_ENABLED:
        return False

    now = now or timezone.now()
    visitor_hash = hash_demo_identifier("visitor", visitor_identifier)
    with schema_context(get_public_schema_name()):
        return DemoTenantSlot.objects.filter(
            visitor_key_hash=visitor_hash,
            slot_code__in=demo_public_pool_schema_names(),
            status=DemoTenantSlot.Status.OCUPADO,
            lease_expires_at__gt=now,
        ).exists()


def get_demo_public_status(*, visitor_identifier=None, now=None):
    pool_slots = demo_public_pool_schema_names()
    total = len(pool_slots)
    if not settings.DEMO_PUBLIC_LEASE_ENABLED:
        return DemoPublicStatus(
            total=total,
            available=0,
            active_slot_code=None,
            active_expires_at=None,
        )

    now = now or timezone.now()
    visitor_hash = (
        hash_demo_identifier("visitor", visitor_identifier)
        if visitor_identifier
        else None
    )
    with schema_context(get_public_schema_name()):
        slots = DemoTenantSlot.objects.filter(slot_code__in=pool_slots)
        available = slots.filter(status=DemoTenantSlot.Status.LIVRE).count()
        active_slot = None
        if visitor_hash:
            active_slot = (
                slots.filter(
                    visitor_key_hash=visitor_hash,
                    status=DemoTenantSlot.Status.OCUPADO,
                    lease_expires_at__gt=now,
                )
                .order_by("slot_code")
                .values("slot_code", "lease_expires_at")
                .first()
            )

    return DemoPublicStatus(
        total=total,
        available=available,
        active_slot_code=active_slot["slot_code"] if active_slot else None,
        active_expires_at=(
            active_slot["lease_expires_at"] if active_slot else None
        ),
    )


def demo_api_base_url(slot_code):
    slot_code = ensure_demo_pool_schema(
        slot_code,
        command_name="servico_demo_publica",
        action="montar URL do tenant demo",
    )
    return f"https://{slot_code}.{DEMO_API_DOMAIN_SUFFIX}/api"


def sync_demo_public_user(
    schema_name,
    *,
    username=DEMO_PUBLIC_USERNAME,
    password=None,
    display_name="Visitante Demo",
    email="",
):
    schema_name = ensure_demo_pool_schema(
        schema_name,
        command_name="servico_demo_publica",
        action="sincronizar usuario demo",
    )

    with schema_context(schema_name):
        sincronizar_grupos_permissoes()
        group = Group.objects.get(name=DEMO_PUBLIC_GROUP_NAME)
        User = get_user_model()
        user, _created = User.objects.get_or_create(username=username)

        user.email = email
        user.first_name = display_name[:150]
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        user.groups.set([group])
        user.user_permissions.clear()
        return user


def sync_demo_permanent_user(
    schema_name,
    *,
    username=DEMO_PUBLIC_USERNAME,
    password=None,
    display_name="Visitante Demo",
):
    schema_name = ensure_demo_permanent_tenant_schema(schema_name)

    with schema_context(schema_name), transaction.atomic():
        sincronizar_grupos_permissoes()
        group = Group.objects.get(name=DEMO_PUBLIC_GROUP_NAME)
        User = get_user_model()
        user = User.objects.filter(username=username).first()

        if user is None and not password:
            raise ImproperlyConfigured(
                "O usuario permanente ainda nao existe; informe a senha por "
                "variavel de ambiente."
            )
        if user is not None and not user.has_usable_password() and not password:
            raise ImproperlyConfigured(
                "O usuario permanente nao possui senha utilizavel; informe uma "
                "senha por variavel de ambiente."
            )
        if user is None:
            user = User(username=username)

        user.first_name = display_name[:150]
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        if password:
            user.set_password(password)
        user.save()
        user.groups.set([group])
        user.user_permissions.clear()
        return user


def seed_demo_tenant(schema_name):
    schema_name = ensure_demo_pool_schema(
        schema_name,
        command_name="seed_demo_tenant",
        action="recriar dados ficticios da demo",
    )

    with schema_context(schema_name):
        sincronizar_grupos_permissoes()
        missing_groups = set(PERMISSION_PROFILES) - set(
            Group.objects.filter(name__in=PERMISSION_PROFILES).values_list(
                "name",
                flat=True,
            )
        )
        if missing_groups:
            raise ImproperlyConfigured(
                f"Grupos obrigatorios ausentes no seed de {schema_name}."
            )

        configuration = ConfiguracaoFinanceira.objects.filter(ativa=True).first()
        if configuration is None:
            configuration = ConfiguracaoFinanceira.objects.create(
                nome="Configuracao Demo",
                valor_alimentacao=Decimal("20.00"),
                valor_transporte=Decimal("15.00"),
                margem_lucro=Decimal("0.30"),
                aliquota_imposto=Decimal("0.06"),
                ativa=True,
                data_inicio_vigencia=timezone.localdate(),
                observacao="Dados ficticios da demonstracao publica.",
            )

        client, _created = Cliente.objects.update_or_create(
            cpf_cnpj="00.000.000/0001-91",
            defaults={
                "nome_razao_social": "Empresa Exemplo Demonstracao Ltda",
                "nome_fantasia": "Empresa Exemplo",
                "tipo_pessoa": "PJ",
                "email": "contato@example.invalid",
                "responsavel": "Pessoa Ficticia",
                "observacoes": "Registro exclusivamente demonstrativo.",
                "ativo": True,
            },
        )

        daily_service, _created = Servico.objects.update_or_create(
            codigo="recepcao-demo-diaria",
            defaults={
                "nome": "Recepcao para evento - diaria",
                "unidade_cobranca": Servico.UNIDADE_COBRANCA_DIARIA,
                "valor_unitario": Decimal("240.00"),
                "diaria_padrao": Decimal("240.00"),
                "horas_base_diaria": 8,
                "percentual_hora_extra": Decimal("1.50"),
                "usa_regra_especial": False,
                "ativo": True,
            },
        )
        hourly_service, _created = Servico.objects.update_or_create(
            codigo="apoio-demo-hora",
            defaults={
                "nome": "Apoio operacional - hora",
                "unidade_cobranca": Servico.UNIDADE_COBRANCA_HORA,
                "valor_unitario": Decimal("100.00"),
                "diaria_padrao": Decimal("800.00"),
                "horas_base_diaria": 8,
                "percentual_hora_extra": Decimal("1.50"),
                "usa_regra_especial": False,
                "ativo": True,
            },
        )

        budget, budget_created = Orcamento.objects.get_or_create(
            numero="DEMO-EXEMPLO-001",
            defaults={
                "cliente": client,
                "configuracao_financeira": configuration,
                "nome_evento": "Evento Corporativo Ficticio",
                "data_evento": timezone.localdate() + timedelta(days=30),
                "local": "Centro de Convencoes - ambiente ficticio",
                "validade": timezone.localdate() + timedelta(days=7),
                "status": "rascunho",
                "observacoes": "Orcamento criado pelo seed da demo publica.",
            },
        )
        if budget_created:
            OrcamentoItem.objects.create(
                orcamento=budget,
                servico=daily_service,
                horas_por_dia=Decimal("8.00"),
                quantidade_dias=1,
                quantidade_pessoas=2,
            )
            OrcamentoItem.objects.create(
                orcamento=budget,
                servico=hourly_service,
                horas_por_dia=Decimal("2.00"),
                quantidade_dias=2,
                quantidade_pessoas=2,
            )
            budget.aprovar_e_gerar_evento()

        return {
            "configuration_id": configuration.pk,
            "client_id": client.pk,
            "daily_service_id": daily_service.pk,
            "hourly_service_id": hourly_service.pk,
            "budget_id": budget.pk,
        }


def allocate_demo_lease(
    *,
    visitor_identifier,
    network_identifier,
    now=None,
    resume_only=False,
):
    if not settings.DEMO_PUBLIC_LEASE_ENABLED:
        raise DemoPoolUnavailable("Entrada publica da demo desativada.")

    now = now or timezone.now()
    visitor_hash = hash_demo_identifier("visitor", visitor_identifier)
    network_hash = hash_demo_identifier("network", network_identifier)

    connection.set_schema_to_public()
    with transaction.atomic():
        _lock_demo_identifiers(visitor_hash, network_hash)
        slot = (
            DemoTenantSlot.objects.select_for_update()
            .select_related("tenant")
            .filter(
                visitor_key_hash=visitor_hash,
                slot_code__in=demo_public_pool_schema_names(),
                status=DemoTenantSlot.Status.OCUPADO,
                lease_expires_at__gt=now,
            )
            .order_by("slot_code")
            .first()
        )
        reused = slot is not None

        if slot is None:
            if resume_only:
                raise DemoLeaseResumeUnavailable(
                    "O lease ativo nao esta mais disponivel para retomada."
                )

            active_network_leases = DemoTenantSlot.objects.filter(
                network_key_hash=network_hash,
                slot_code__in=demo_public_pool_schema_names(),
                status=DemoTenantSlot.Status.OCUPADO,
                lease_expires_at__gt=now,
            ).count()
            if active_network_leases >= settings.DEMO_MAX_ACTIVE_LEASES_PER_NETWORK:
                raise DemoNetworkLimitExceeded(
                    "Limite de leases ativos para a rede atingido."
                )

            slot = (
                DemoTenantSlot.objects.select_for_update(skip_locked=True)
                .select_related("tenant")
                .filter(
                    slot_code__in=demo_public_pool_schema_names(),
                    status=DemoTenantSlot.Status.LIVRE,
                )
                .order_by("slot_code")
                .first()
            )
            if slot is None:
                raise DemoPoolFull("Pool demo temporariamente cheia.")

        schema_name = _validate_public_demo_slot(slot)
        seed_demo_tenant(schema_name)
        sync_demo_public_user(schema_name)

        if not reused:
            slot.assigned_name = ""
            slot.assigned_email = ""
            slot.assigned_phone = ""
            slot.visitor_key_hash = visitor_hash
            slot.network_key_hash = network_hash
            slot.lease_started_at = now
            slot.lease_expires_at = now + timedelta(
                minutes=settings.DEMO_LEASE_DURATION_MINUTES
            )
            slot.last_assigned_at = now
            slot.status = DemoTenantSlot.Status.OCUPADO

        raw_token = secrets.token_urlsafe(32)
        slot.exchange_token_digest = hash_demo_identifier("exchange", raw_token)
        slot.exchange_token_expires_at = min(
            slot.lease_expires_at,
            now + timedelta(seconds=settings.DEMO_EXCHANGE_TOKEN_TTL_SECONDS),
        )
        slot.exchange_token_consumed_at = None
        slot.full_clean()
        slot.save()

        return DemoLeaseGrant(
            slot_code=slot.slot_code,
            api_base_url=demo_api_base_url(slot.slot_code),
            expires_at=slot.lease_expires_at,
            exchange_token=raw_token,
            reused=reused,
        )


def consume_demo_exchange_token(*, schema_name, raw_token, now=None):
    schema_name = ensure_demo_pool_schema(
        schema_name,
        command_name="troca_acesso_demo",
        action="autenticar acesso temporario",
    )
    if not isinstance(raw_token, str) or not 20 <= len(raw_token) <= 256:
        raise DemoAccessTokenInvalid("Token de acesso invalido.")

    now = now or timezone.now()
    token_digest = hash_demo_identifier("exchange", raw_token)

    with transaction.atomic():
        with schema_context(get_public_schema_name()):
            slot = (
                DemoTenantSlot.objects.select_for_update()
                .select_related("tenant")
                .filter(exchange_token_digest=token_digest)
                .first()
            )
            if slot is None:
                raise DemoAccessTokenInvalid("Token de acesso invalido.")
            try:
                _validate_public_demo_slot(slot)
            except DemoPoolUnavailable as exc:
                raise DemoAccessTokenInvalid("Token de acesso invalido.") from exc
            if slot.slot_code != schema_name:
                raise DemoAccessTokenInvalid("Token de acesso invalido.")
            if slot.status != DemoTenantSlot.Status.OCUPADO:
                raise DemoAccessTokenInvalid("Token de acesso invalido.")
            if not slot.lease_expires_at or slot.lease_expires_at <= now:
                raise DemoAccessTokenInvalid("Acesso demo expirado.")
            if (
                slot.exchange_token_consumed_at is not None
                or not slot.exchange_token_expires_at
                or slot.exchange_token_expires_at <= now
            ):
                raise DemoAccessTokenInvalid("Token de acesso invalido.")

        with schema_context(schema_name):
            User = get_user_model()
            user = User.objects.filter(
                username=DEMO_PUBLIC_USERNAME,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            ).first()
            if user is None:
                raise DemoAccessTokenInvalid("Acesso demo indisponivel.")

        with schema_context(get_public_schema_name()):
            slot.exchange_token_digest = None
            slot.exchange_token_consumed_at = now
            slot.save(
                update_fields=[
                    "exchange_token_digest",
                    "exchange_token_consumed_at",
                    "updated_at",
                ]
            )

    return user, slot.lease_expires_at


def _lock_demo_identifiers(*identifier_hashes):
    """Serialize competing leases for the same anonymous visitor or network."""

    if connection.vendor != "postgresql":
        raise ImproperlyConfigured(
            "A alocacao da demo publica exige advisory locks do PostgreSQL."
        )

    lock_keys = set()
    for identifier_hash in identifier_hashes:
        unsigned_key = int(identifier_hash[:16], 16)
        signed_key = (
            unsigned_key - (1 << 64)
            if unsigned_key >= (1 << 63)
            else unsigned_key
        )
        lock_keys.add(signed_key)

    with connection.cursor() as cursor:
        for lock_key in sorted(lock_keys):
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_key])


def expire_due_demo_leases(
    *,
    slot_code=None,
    username=DEMO_PUBLIC_USERNAME,
    now=None,
    dry_run=False,
):
    now = now or timezone.now()
    connection.set_schema_to_public()
    queryset = DemoTenantSlot.objects.select_related("tenant").filter(
        slot_code__in=demo_public_pool_schema_names(),
        status=DemoTenantSlot.Status.OCUPADO,
        lease_expires_at__lt=now,
    )
    if slot_code:
        slot_code = ensure_demo_public_pool_schema(
            slot_code,
            command_name="expirar_leases_demo",
            action="expirar lease demo",
        )
        queryset = queryset.filter(slot_code=slot_code)

    if dry_run:
        return [slot.slot_code for slot in queryset.order_by("slot_code")]

    results = []
    with transaction.atomic():
        for slot in queryset.select_for_update().order_by("slot_code"):
            schema_name = _validate_public_demo_slot(slot)
            cleanup = cleanup_demo_tenant_access(schema_name, username=username)
            slot.status = DemoTenantSlot.Status.EXPIRADO
            slot.exchange_token_digest = None
            slot.exchange_token_expires_at = None
            slot.exchange_token_consumed_at = None
            slot.full_clean()
            slot.save(
                update_fields=[
                    "status",
                    "exchange_token_digest",
                    "exchange_token_expires_at",
                    "exchange_token_consumed_at",
                    "updated_at",
                ]
            )
            results.append(
                DemoExpirationResult(
                    slot_code=slot.slot_code,
                    sessions_removed=cleanup["sessions_removed"],
                    axes_rows_removed=cleanup["axes_rows_removed"],
                    cache_keys_removed=cleanup["cache_keys_removed"],
                    user_deactivated=cleanup["user_deactivated"],
                )
            )
    return results


def cleanup_demo_tenant_access(schema_name, *, username=DEMO_PUBLIC_USERNAME):
    schema_name = ensure_demo_pool_schema(
        schema_name,
        command_name="limpeza_acesso_demo",
        action="limpar acesso expirado",
    )
    with schema_context(schema_name):
        User = get_user_model()
        deactivated = bool(
            User.objects.filter(username=username, is_active=True).update(
                is_active=False
            )
        )
        sessions_removed, _details = Session.objects.all().delete()
        axes_rows_removed = 0
        for model in (AccessAttempt, AccessFailureLog, AccessLog):
            removed, _details = model.objects.all().delete()
            axes_rows_removed += removed

    cache_keys_removed = clear_demo_tenant_cache(schema_name)
    return {
        "user_deactivated": deactivated,
        "sessions_removed": sessions_removed,
        "axes_rows_removed": axes_rows_removed,
        "cache_keys_removed": cache_keys_removed,
    }


def clear_demo_tenant_cache(schema_name):
    schema_name = ensure_demo_pool_schema(
        schema_name,
        command_name="limpeza_cache_demo",
        action="limpar cache tenant-scoped",
    )
    key_prefix = getattr(cache, "key_prefix", "")
    tenant_prefix = f"{key_prefix}:{schema_name}:" if key_prefix else f"{schema_name}:"
    backend_cache = getattr(cache, "_cache", None)

    if hasattr(backend_cache, "get_client"):
        client = backend_cache.get_client(None, write=True)
        keys = list(client.scan_iter(match=f"{tenant_prefix}*", count=100))
        if keys:
            client.delete(*keys)
        return len(keys)

    if isinstance(backend_cache, dict) and hasattr(cache, "_lock"):
        with cache._lock:
            keys = [key for key in backend_cache if str(key).startswith(tenant_prefix)]
            for key in keys:
                backend_cache.pop(key, None)
                cache._expire_info.pop(key, None)
        return len(keys)

    raise ImproperlyConfigured(
        "Backend de cache nao suporta limpeza tenant-scoped segura."
    )


def _validate_demo_slot(slot):
    schema_name = ensure_demo_pool_schema(
        slot.tenant.schema_name,
        command_name="servico_demo_publica",
        action="validar slot demo",
    )
    if slot.slot_code != schema_name:
        raise DemoPoolUnavailable("Slot demo inconsistente.")

    expected_domain = f"{slot.slot_code}.{DEMO_API_DOMAIN_SUFFIX}"
    domain = Domain.objects.select_related("tenant").filter(domain=expected_domain).first()
    if domain is None or domain.tenant_id != slot.tenant_id:
        raise DemoPoolUnavailable("Domain tecnico do slot demo inconsistente.")
    return schema_name


def _validate_public_demo_slot(slot):
    schema_name = _validate_demo_slot(slot)
    try:
        return ensure_demo_public_pool_schema(
            schema_name,
            command_name="servico_demo_publica",
            action="validar vaga temporaria",
        )
    except CommandError as exc:
        raise DemoPoolUnavailable("Slot fora da pool publica.") from exc
