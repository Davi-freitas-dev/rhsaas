from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import connection
from django.utils import timezone
from django_tenants.utils import schema_context

from .models import Cliente, ConfiguracaoFinanceira, Orcamento, Servico


DEMO_SEED_SPEC = {
    "configuration": {
        "key": "demo.configuration.primary",
        "model": ConfiguracaoFinanceira,
        "visible": {
            "nome": "Configuracao Demo",
            "valor_alimentacao": Decimal("20.00"),
            "valor_transporte": Decimal("15.00"),
            "margem_lucro": Decimal("0.30"),
            "aliquota_imposto": Decimal("0.06"),
            "ativa": True,
            "observacao": "Dados ficticios da demonstracao publica.",
        },
    },
    "client": {
        "key": "demo.client.example",
        "model": Cliente,
        "visible": {
            "nome_razao_social": "Empresa Exemplo Demonstracao Ltda",
            "nome_fantasia": "Empresa Exemplo",
            "tipo_pessoa": "PJ",
            "cpf_cnpj": "00.000.000/0001-91",
            "telefone": "",
            "email": "contato@example.invalid",
            "responsavel": "Pessoa Ficticia",
            "endereco": "",
            "observacoes": "Registro exclusivamente demonstrativo.",
            "ativo": True,
        },
    },
    "daily_service": {
        "key": "demo.service.daily",
        "model": Servico,
        "visible": {
            "nome": "Recepcao para evento - diaria",
            "codigo": "recepcao-demo-diaria",
            "unidade_cobranca": Servico.UNIDADE_COBRANCA_DIARIA,
            "valor_unitario": Decimal("240.00"),
            "diaria_padrao": Decimal("240.00"),
            "horas_base_diaria": 8,
            "percentual_hora_extra": Decimal("1.50"),
            "usa_regra_especial": False,
            "ativo": True,
        },
    },
    "hourly_service": {
        "key": "demo.service.hourly",
        "model": Servico,
        "visible": {
            "nome": "Apoio operacional - hora",
            "codigo": "apoio-demo-hora",
            "unidade_cobranca": Servico.UNIDADE_COBRANCA_HORA,
            "valor_unitario": Decimal("100.00"),
            "diaria_padrao": Decimal("800.00"),
            "horas_base_diaria": 8,
            "percentual_hora_extra": Decimal("1.50"),
            "usa_regra_especial": False,
            "ativo": True,
        },
    },
    "budget": {
        "key": "demo.budget.example",
        "model": Orcamento,
        "visible": {
            "numero": "DEMO-EXEMPLO-001",
            "nome_evento": "Evento Corporativo Ficticio",
            "local": "Centro de Convencoes - ambiente ficticio",
            "observacoes": "Orcamento criado pelo seed da demo publica.",
        },
    },
}

DEMO_SEED_KEY_COUNT = len(DEMO_SEED_SPEC)
DEMO_SEED_KEYS = tuple(entry["key"] for entry in DEMO_SEED_SPEC.values())


class DemoSeedIntegrityError(ImproperlyConfigured):
    pass


@dataclass(frozen=True)
class DemoSeedReadiness:
    schema_name: str
    ready: bool
    errors: tuple[str, ...]
    objects: dict

    def require_ready(self):
        if not self.ready:
            details = "; ".join(self.errors) or "estado desconhecido"
            raise DemoSeedIntegrityError(
                f"Seed da demo inconsistente em {self.schema_name}: {details}."
            )
        return self


def demo_seed_entry(name):
    return DEMO_SEED_SPEC[name]


def demo_seed_create_defaults(name, *, today=None):
    today = today or timezone.localdate()
    defaults = dict(demo_seed_entry(name)["visible"])
    if name == "configuration":
        defaults["data_inicio_vigencia"] = today
    elif name == "budget":
        defaults.update(
            {
                "data_evento": today + timedelta(days=30),
                "validade": today + timedelta(days=7),
                "status": "rascunho",
            }
        )
    return defaults


def expected_demo_seed_keys_by_model():
    result = {}
    for entry in DEMO_SEED_SPEC.values():
        result.setdefault(entry["model"], set()).add(entry["key"])
    return {model: frozenset(keys) for model, keys in result.items()}


def inspect_demo_seed_readiness(*, schema_name=None):
    target_schema = schema_name or connection.schema_name
    if schema_name and connection.schema_name != schema_name:
        with schema_context(schema_name):
            return inspect_demo_seed_readiness()

    errors = []
    objects = {}
    for model, expected_keys in expected_demo_seed_keys_by_model().items():
        keyed_objects = list(model.objects.exclude(demo_seed_key__isnull=True))
        actual_keys = [obj.demo_seed_key for obj in keyed_objects]
        if len(actual_keys) != len(set(actual_keys)):
            errors.append(f"{model._meta.label_lower} possui chave duplicada")
        if set(actual_keys) != set(expected_keys):
            missing = sorted(set(expected_keys) - set(actual_keys))
            unknown = sorted(set(actual_keys) - set(expected_keys))
            if missing:
                errors.append(
                    f"{model._meta.label_lower} sem chaves: {', '.join(missing)}"
                )
            if unknown:
                errors.append(
                    f"{model._meta.label_lower} com chaves desconhecidas: "
                    f"{', '.join(unknown)}"
                )

        for obj in keyed_objects:
            objects[obj.demo_seed_key] = obj

    expected = set(DEMO_SEED_KEYS)
    if set(objects) != expected:
        missing = sorted(expected - set(objects))
        if missing:
            errors.append(f"conjunto seed incompleto: {', '.join(missing)}")

    if not errors:
        _validate_seed_relations(objects, errors)

    return DemoSeedReadiness(
        schema_name=target_schema,
        ready=not errors,
        errors=tuple(errors),
        objects=objects,
    )


def validate_demo_seed_readiness(*, schema_name=None):
    return inspect_demo_seed_readiness(schema_name=schema_name).require_ready()


def _validate_seed_relations(objects, errors):
    configuration = objects[demo_seed_entry("configuration")["key"]]
    client = objects[demo_seed_entry("client")["key"]]
    daily_service = objects[demo_seed_entry("daily_service")["key"]]
    hourly_service = objects[demo_seed_entry("hourly_service")["key"]]
    budget = objects[demo_seed_entry("budget")["key"]]

    if budget.cliente_id != client.pk:
        errors.append("orcamento seed nao referencia o cliente seed")
    if budget.configuracao_financeira_id != configuration.pk:
        errors.append("orcamento seed nao referencia a configuracao seed")
    if budget.status != "aprovado":
        errors.append("orcamento seed nao esta aprovado")

    items = list(budget.itens.select_related("servico").all())
    expected_service_ids = {daily_service.pk, hourly_service.pk}
    if len(items) != 2 or {item.servico_id for item in items} != expected_service_ids:
        errors.append("orcamento seed nao possui exatamente os dois servicos seed")

    try:
        event = budget.evento
    except ObjectDoesNotExist:
        errors.append("orcamento seed nao possui evento derivado")
        return

    if event.cliente_id != client.pk:
        errors.append("evento seed nao referencia o cliente seed")
    if not event.receitas.exists():
        errors.append("evento seed nao possui receita derivada")
    if not event.despesas.exists():
        errors.append("evento seed nao possui despesas derivadas")
    service_cost_ids = set(
        event.custos_servicos.values_list("servico_id", flat=True)
    )
    if service_cost_ids != expected_service_ids:
        errors.append("evento seed nao possui custos dos dois servicos seed")


def match_legacy_demo_seed():
    """Locate the legacy seed using the full canonical visual specification.

    This is a transition helper only. Runtime authorization must never call it.
    """

    matches = {}
    errors = []
    for name, entry in DEMO_SEED_SPEC.items():
        filters = dict(entry["visible"])
        if name == "budget":
            filters["status"] = "aprovado"
        candidates = list(entry["model"].objects.filter(**filters)[:2])
        if len(candidates) != 1:
            errors.append(
                f"{name}: esperado um candidato legado exato, encontrados "
                f"{len(candidates)}"
            )
        else:
            matches[name] = candidates[0]

    if errors:
        raise DemoSeedIntegrityError("; ".join(errors))

    budget = matches["budget"]
    if budget.cliente_id != matches["client"].pk:
        errors.append("orcamento legado nao referencia o cliente candidato")
    if budget.configuracao_financeira_id != matches["configuration"].pk:
        errors.append("orcamento legado nao referencia a configuracao candidata")

    items = list(budget.itens.all())
    expected_service_ids = {
        matches["daily_service"].pk,
        matches["hourly_service"].pk,
    }
    if len(items) != 2 or {item.servico_id for item in items} != expected_service_ids:
        errors.append("orcamento legado nao possui exatamente os dois servicos candidatos")

    try:
        event = budget.evento
    except ObjectDoesNotExist:
        errors.append("orcamento legado nao possui evento derivado")
    else:
        if not event.receitas.exists() or not event.despesas.exists():
            errors.append("evento legado nao possui derivados financeiros minimos")
        if set(event.custos_servicos.values_list("servico_id", flat=True)) != expected_service_ids:
            errors.append("evento legado nao possui custos dos servicos candidatos")

    if errors:
        raise DemoSeedIntegrityError("; ".join(errors))
    return matches
