import json

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, transaction
from django.db.models import Q
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from django_tenants.utils import (
    get_public_schema_name,
    schema_context,
    schema_exists,
)

from caixa.demo_policy import DEMO_SEED_PARENT_FIELDS
from caixa.demo_seed import (
    DEMO_SEED_KEYS,
    DEMO_SEED_SPEC,
    DemoSeedIntegrityError,
    demo_seed_entry,
    inspect_demo_seed_readiness,
    match_legacy_demo_seed,
)
from caixa.models import Cliente, ConfiguracaoFinanceira, Evento, Orcamento, OrcamentoItem, Servico
from caixa.models_custos_extras import OrcamentoCustoExtra
from tenancy.command_guards import ensure_demo_permanent_tenant_schema
from tenancy.services_demo_pool import clear_demo_tenant_cache


CONFIRMATION_PREFIX = "REMOVER-DADOS-FICTICIOS"
SEED_ENTRY_NAMES = (
    "configuration",
    "client",
    "daily_service",
    "hourly_service",
    "budget",
)
SEED_ROOT_MODELS = (ConfiguracaoFinanceira, Cliente, Servico, Orcamento)
LEGACY_IDENTITY_FIELDS = {
    "client": ("cpf_cnpj",),
    "daily_service": ("codigo",),
    "hourly_service": ("codigo",),
    "budget": ("numero",),
}


class Command(BaseCommand):
    help = (
        "Remove exclusivamente o seed ficticio canonico da demo1, preservando "
        "usuarios, grupos, permissoes, dominio e demais dados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida e mostra as contagens sem alterar o tenant.",
        )
        parser.add_argument(
            "--diagnostico",
            action="store_true",
            help=(
                "Inspeciona seed keys, candidatos legados e referencias em uma "
                "transacao PostgreSQL estritamente somente leitura."
            ),
        )
        parser.add_argument(
            "--confirm",
            help=(
                "Confirmacao forte para executar: "
                '"REMOVER-DADOS-FICTICIOS demo1".'
            ),
        )

    def handle(self, *args, **options):
        connection.set_schema_to_public()
        if connection.schema_name != get_public_schema_name():
            raise CommandError(
                "remover_dados_ficticios_demo1 deve executar no schema public."
            )

        schema_name = ensure_demo_permanent_tenant_schema(
            settings.DEMO_PERMANENT_TENANT_SCHEMA,
            command_name="remover_dados_ficticios_demo1",
        )
        if not schema_exists(schema_name):
            raise CommandError(f"O schema permanente {schema_name} nao existe.")

        expected_confirmation = f"{CONFIRMATION_PREFIX} {schema_name}"
        dry_run = bool(options["dry_run"])
        diagnostic = bool(options["diagnostico"])
        if diagnostic and (dry_run or options.get("confirm")):
            raise CommandError(
                "--diagnostico nao pode ser combinado com --dry-run ou --confirm."
            )
        if diagnostic:
            if connection.in_atomic_block:
                raise CommandError(
                    "--diagnostico exige execucao fora de uma transacao externa "
                    "para impor READ ONLY no PostgreSQL."
                )
            with schema_context(schema_name), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                    )
                self._write_diagnostic(schema_name)
            return

        if not dry_run and options.get("confirm") != expected_confirmation:
            raise CommandError(
                "Execucao exige confirmacao forte: "
                f'--confirm "{expected_confirmation}".'
            )

        summary = None
        deleted = None
        with schema_context(schema_name):
            try:
                with transaction.atomic():
                    self._lock_cleanup_tables()
                    resolved_seed = self._resolve_existing_seed()
                    if resolved_seed is not None:
                        seed_objects, identification = resolved_seed
                        summary = self._build_summary(seed_objects, identification)
                        deleted = self._remove_seed(seed_objects, identification)
                        connection.check_constraints()
                        if self._remaining_seed_root_count(seed_objects) != 0:
                            raise CommandError(
                                "A limpeza terminou com dados ficticios residuais; "
                                "a transacao foi revertida."
                            )
                        if dry_run:
                            transaction.set_rollback(True)
            except (IntegrityError, ProtectedError) as exc:
                raise CommandError(
                    "Os dados ficticios possuem referencias fora do seed canonico; "
                    "a limpeza foi revertida para preservar os demais dados."
                ) from exc

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY-RUN: nenhum dado foi alterado.")
            )
            if summary is None:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Schema {schema_name} ja esta sem dados ficticios canonicos."
                    )
                )
            else:
                self._write_summary(schema_name, summary)
            return

        cache_keys_removed = self._clear_cache_with_warning(schema_name)
        cache_status = (
            "cache_pendente=sim"
            if cache_keys_removed is None
            else f"chaves_cache={cache_keys_removed}"
        )
        if deleted is None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Schema {schema_name} ja esta sem dados ficticios canonicos; "
                    f"{cache_status}."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Dados ficticios removidos de {schema_name}. "
                f"registros_vivos={deleted['live']}; "
                f"historicos={deleted['history']}; "
                f"{cache_status}; "
                "usuarios_e_permissoes=preservados."
            )
        )

    def _clear_cache_with_warning(self, schema_name):
        try:
            return clear_demo_tenant_cache(schema_name)
        except Exception:
            self.stderr.write(
                self.style.WARNING(
                    f"ATENCAO: o banco de {schema_name} esta sem os dados "
                    "ficticios, mas o cache nao foi invalidado. A limpeza do "
                    "banco foi concluida; repita o mesmo comando para tentar "
                    "a invalidacao do cache novamente."
                )
            )
            return None

    def _write_diagnostic(self, schema_name):
        self.stdout.write("DIAGNOSTICO SOMENTE LEITURA")
        self.stdout.write(f"schema={schema_name}")
        self.stdout.write("transaction_read_only=sim")

        expected_keys = sorted(DEMO_SEED_KEYS)
        keyed_rows = []
        for model in SEED_ROOT_MODELS:
            for pk, seed_key in model._base_manager.exclude(
                demo_seed_key__isnull=True
            ).order_by("pk").values_list("pk", "demo_seed_key"):
                keyed_rows.append(
                    {
                        "model": model._meta.label_lower,
                        "id": pk,
                        "seed_key": seed_key,
                    }
                )
        actual_keys = sorted(
            {row["seed_key"] for row in keyed_rows}, key=lambda value: str(value)
        )
        self._write_json("expected_seed_keys", expected_keys)
        self._write_json("actual_seed_keys", actual_keys)
        self._write_json(
            "missing_seed_keys", sorted(set(expected_keys) - set(actual_keys))
        )
        self._write_json(
            "unexpected_seed_keys", sorted(set(actual_keys) - set(expected_keys))
        )
        self.stdout.write(f"keyed_object_count={len(keyed_rows)}")
        for row in keyed_rows:
            self._write_json("keyed_object", row)

        readiness = inspect_demo_seed_readiness()
        self.stdout.write(
            f"keyed_seed_validation={'valid' if readiness.ready else 'invalid'}"
        )
        for error in readiness.errors:
            self.stdout.write(f"keyed_seed_error={error}")

        exact_candidates = {}
        exact_candidate_total = 0
        for name, entry in DEMO_SEED_SPEC.items():
            filters = self._legacy_filters(name, entry)
            ids = list(
                entry["model"]._base_manager.filter(**filters)
                .order_by("pk")
                .values_list("pk", flat=True)
            )
            exact_candidates[name] = ids
            exact_candidate_total += len(ids)
            status = (
                "missing"
                if not ids
                else "unique"
                if len(ids) == 1
                else "ambiguous"
            )
            self._write_json(
                "legacy_exact_candidate",
                {
                    "entry": name,
                    "model": entry["model"]._meta.label_lower,
                    "expected_seed_key": entry["key"],
                    "status": status,
                    "count": len(ids),
                    "ids": ids,
                    "classifies_as_seed": False,
                },
            )
        self.stdout.write(f"legacy_exact_candidate_total={exact_candidate_total}")

        self._write_identity_probes()
        for name, ids in exact_candidates.items():
            model = DEMO_SEED_SPEC[name]["model"]
            for obj in model._base_manager.filter(pk__in=ids).order_by("pk"):
                for reference in self._related_references(obj):
                    self._write_json(
                        "legacy_exact_candidate_reference",
                        {
                            "entry": name,
                            "candidate_model": model._meta.label_lower,
                            "candidate_id": obj.pk,
                            **reference,
                        },
                    )

        proven_seed = None
        proven_by = "none"
        if keyed_rows:
            if readiness.ready:
                proven_seed = readiness.objects
                proven_by = "canonical_seed_keys"
            else:
                self.stdout.write("legacy_validation=not_used_seed_keys_exist")
        elif exact_candidate_total == 0:
            self.stdout.write("legacy_validation=no_exact_candidates")
        else:
            try:
                legacy_matches = match_legacy_demo_seed()
            except DemoSeedIntegrityError as exc:
                self.stdout.write("legacy_validation=partial_or_ambiguous")
                self.stdout.write(f"legacy_validation_error={exc}")
            else:
                proven_seed = {
                    DEMO_SEED_SPEC[name]["key"]: obj
                    for name, obj in legacy_matches.items()
                }
                proven_by = "exact_legacy_spec_and_relations"
                self.stdout.write("legacy_validation=valid")

        self.stdout.write(f"proven_seed_set={proven_by}")
        if proven_seed is None:
            self.stdout.write(
                "blocking_reference_analysis=not_evaluated_unproven_seed_set"
            )
            return

        blockers = self._blocking_references(proven_seed)
        self.stdout.write(f"blocking_reference_count={len(blockers)}")
        for blocker in blockers:
            self._write_json("blocking_reference", blocker)

    def _write_json(self, key, value):
        print_value = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            default=str,
        )
        self.stdout.write(f"{key}={print_value}")

    def _write_identity_probes(self):
        for name, entry in DEMO_SEED_SPEC.items():
            identity_fields = LEGACY_IDENTITY_FIELDS.get(name)
            if not identity_fields:
                self._write_json_line(
                    "legacy_identity_probe",
                    {
                        "entry": name,
                        "status": "unavailable_no_stable_legacy_identifier",
                        "classifies_as_seed": False,
                    },
                )
                continue

            identity = {
                field_name: entry["visible"][field_name]
                for field_name in identity_fields
            }
            objects = list(
                entry["model"]._base_manager.filter(**identity).order_by("pk")
            )
            self._write_json_line(
                "legacy_identity_probe",
                {
                    "entry": name,
                    "model": entry["model"]._meta.label_lower,
                    "identity_fields": identity,
                    "count": len(objects),
                    "ids": [obj.pk for obj in objects],
                    "status": "found" if objects else "missing",
                    "classifies_as_seed": False,
                },
            )
            expected = self._legacy_filters(name, entry)
            for obj in objects:
                mismatched_fields = [
                    field_name
                    for field_name, expected_value in expected.items()
                    if getattr(obj, field_name) != expected_value
                ]
                self._write_json_line(
                    "legacy_identity_object",
                    {
                        "entry": name,
                        "model": obj._meta.label_lower,
                        "id": obj.pk,
                        "mismatched_exact_spec_fields": mismatched_fields,
                    },
                )

    def _write_json_line(self, key, value):
        self._write_json(key, value)

    @staticmethod
    def _legacy_filters(name, entry):
        filters = dict(entry["visible"])
        if name == "budget":
            filters["status"] = "aprovado"
        return filters

    @staticmethod
    def _related_references(obj):
        references = []
        for relation in obj._meta.related_objects:
            field = relation.field
            if getattr(field, "many_to_many", False) or not hasattr(field, "attname"):
                continue
            ids = list(
                relation.related_model._base_manager.filter(
                    **{field.attname: obj.pk}
                )
                .order_by("pk")
                .values_list("pk", flat=True)
            )
            if not ids:
                continue
            references.append(
                {
                    "referencing_model": relation.related_model._meta.label_lower,
                    "field": field.name,
                    "on_delete": getattr(
                        field.remote_field.on_delete,
                        "__name__",
                        str(field.remote_field.on_delete),
                    ),
                    "db_constraint": field.db_constraint,
                    "count": len(ids),
                    "ids": ids,
                }
            )
        return references

    @classmethod
    def _blocking_references(cls, seed_objects):
        budget = seed_objects[demo_seed_entry("budget")["key"]]
        event = Evento.objects.filter(orcamento=budget).first()
        planned = {
            (obj._meta.label_lower, obj.pk) for obj in seed_objects.values()
        }
        blockers = []

        if event is not None:
            collector = Collector(using=connection.alias)
            try:
                collector.collect([event])
            except (ProtectedError, RestrictedError) as exc:
                protected_objects = getattr(
                    exc,
                    "protected_objects",
                    getattr(exc, "restricted_objects", ()),
                )
                grouped = {}
                for obj in protected_objects:
                    grouped.setdefault(obj._meta.label_lower, []).append(obj.pk)
                for model_label, ids in sorted(grouped.items()):
                    blockers.append(
                        {
                            "kind": "event_delete_protected",
                            "model": model_label,
                            "ids": sorted(ids),
                        }
                    )
                return blockers

            for model, objects in collector.data.items():
                planned.update(
                    (model._meta.label_lower, obj.pk) for obj in objects
                )
            for queryset in collector.fast_deletes:
                planned.update(
                    (queryset.model._meta.label_lower, pk)
                    for pk in queryset.values_list("pk", flat=True)
                )

        planned.update(
            (OrcamentoItem._meta.label_lower, pk)
            for pk in OrcamentoItem.objects.filter(orcamento=budget).values_list(
                "pk", flat=True
            )
        )
        planned.update(
            (OrcamentoCustoExtra._meta.label_lower, pk)
            for pk in OrcamentoCustoExtra.objects.filter(orcamento=budget).values_list(
                "pk", flat=True
            )
        )

        raw_targets = [
            ("budget", budget),
            (
                "daily_service",
                seed_objects[demo_seed_entry("daily_service")["key"]],
            ),
            (
                "hourly_service",
                seed_objects[demo_seed_entry("hourly_service")["key"]],
            ),
            ("client", seed_objects[demo_seed_entry("client")["key"]]),
            (
                "configuration",
                seed_objects[demo_seed_entry("configuration")["key"]],
            ),
        ]
        for entry_name, target in raw_targets:
            for reference in cls._related_references(target):
                model_label = reference["referencing_model"]
                external_ids = [
                    pk
                    for pk in reference["ids"]
                    if (model_label, pk) not in planned
                ]
                if not reference["db_constraint"] or not external_ids:
                    continue
                blockers.append(
                    {
                        "kind": "raw_delete_external_fk",
                        "target_entry": entry_name,
                        "target_model": target._meta.label_lower,
                        "target_id": target.pk,
                        "referencing_model": model_label,
                        "field": reference["field"],
                        "on_delete": reference["on_delete"],
                        "ids": external_ids,
                    }
                )
        return blockers

    @staticmethod
    def _lock_cleanup_tables():
        table_names = sorted(
            {
                model._meta.db_table
                for model in apps.get_app_config("caixa").get_models()
                if model._meta.managed and not model._meta.proxy
            }
        )
        if not table_names:
            raise CommandError(
                "Nenhuma tabela operacional foi encontrada para bloquear; "
                "a limpeza foi abortada."
            )

        quoted_tables = ", ".join(
            connection.ops.quote_name(table_name) for table_name in table_names
        )
        with connection.cursor() as cursor:
            cursor.execute(
                f"LOCK TABLE {quoted_tables} IN SHARE ROW EXCLUSIVE MODE"
            )

    @staticmethod
    def _keyed_root_count():
        return sum(
            model.objects.exclude(demo_seed_key__isnull=True).count()
            for model in SEED_ROOT_MODELS
        )

    def _resolve_existing_seed(self):
        keyed_count = self._keyed_root_count()
        if keyed_count:
            readiness = inspect_demo_seed_readiness()
            if not readiness.ready:
                details = "; ".join(readiness.errors) or "estado desconhecido"
                raise CommandError(
                    "O seed existente esta parcial ou inconsistente; nenhuma "
                    f"exclusao foi executada. Detalhes: {details}."
                )
            return readiness.objects, "chaves_canonicas"

        legacy_candidate_count = self._legacy_candidate_count()
        if legacy_candidate_count == 0:
            return None

        try:
            legacy_matches = match_legacy_demo_seed()
        except DemoSeedIntegrityError as exc:
            raise CommandError(
                "Foram encontrados candidatos a dados ficticios legados, mas o "
                "conjunto esta parcial ou ambiguo; nenhuma exclusao foi executada."
            ) from exc

        return {
            DEMO_SEED_SPEC[name]["key"]: obj
            for name, obj in legacy_matches.items()
        }, "especificacao_legada_exata"

    @staticmethod
    def _legacy_candidate_count():
        count = 0
        for name, entry in DEMO_SEED_SPEC.items():
            filters = dict(entry["visible"])
            if name == "budget":
                filters["status"] = "aprovado"
            count += entry["model"].objects.filter(**filters).count()
        return count

    @staticmethod
    def _remaining_seed_root_count(seed_objects):
        return sum(
            entry["model"].objects.filter(pk=seed_objects[entry["key"]].pk).count()
            for entry in (demo_seed_entry(name) for name in SEED_ENTRY_NAMES)
        )

    @staticmethod
    def _build_summary(seed_objects, identification):
        budget = seed_objects[demo_seed_entry("budget")["key"]]
        event = Evento.objects.filter(orcamento=budget).first()
        root_identities = frozenset(
            (obj._meta.label_lower, obj.pk) for obj in seed_objects.values()
        )
        history_targets, _seed_ids_by_model = Command._collect_history_targets(
            root_identities
        )
        return {
            "identification": identification,
            "roots": len(DEMO_SEED_KEYS),
            "budget_items": OrcamentoItem.objects.filter(orcamento=budget).count(),
            "budget_extra_costs": OrcamentoCustoExtra.objects.filter(
                orcamento=budget
            ).count(),
            "event": int(event is not None),
            "proven_history_records": sum(
                len(history_ids) for _history_model, history_ids in history_targets
            ),
        }

    def _write_summary(self, schema_name, summary):
        self.stdout.write(f"schema={schema_name}")
        for key, value in summary.items():
            self.stdout.write(f"{key}={value}")
        self.stdout.write("usuarios_e_permissoes=preservados")

    def _remove_seed(self, seed_objects, identification):
        try:
            roots = {
                key: entry["model"].objects.select_for_update().get(
                    pk=seed_objects[key].pk
                )
                for entry in (demo_seed_entry(name) for name in SEED_ENTRY_NAMES)
                for key in (entry["key"],)
            }
        except ObjectDoesNotExist as exc:
            raise CommandError(
                "O conjunto ficticio mudou durante a validacao; a limpeza foi "
                "revertida sem excluir dados."
            ) from exc

        self._validate_seed_unchanged(roots, identification)
        budget = roots[demo_seed_entry("budget")["key"]]
        root_identities = frozenset(
            (obj._meta.label_lower, obj.pk) for obj in roots.values()
        )
        history_targets, seed_ids_by_model = self._collect_history_targets(
            root_identities
        )
        before_live = sum(
            1
            for model in apps.get_app_config("caixa").get_models()
            if model._meta.model_name in DEMO_SEED_PARENT_FIELDS
            for obj in model._base_manager.all().iterator()
            if self._is_resolved_seed_object(obj, root_identities)
        ) + len(DEMO_SEED_KEYS)

        event = Evento.objects.select_for_update().filter(orcamento=budget).first()
        if event is not None:
            event.delete()

        self._raw_delete(OrcamentoCustoExtra.objects.filter(orcamento=budget))
        self._raw_delete(OrcamentoItem.objects.filter(orcamento=budget))
        self._raw_delete(Orcamento.objects.filter(pk=budget.pk))

        service_ids = [
            roots[demo_seed_entry("daily_service")["key"]].pk,
            roots[demo_seed_entry("hourly_service")["key"]].pk,
        ]
        self._raw_delete(Servico.objects.filter(pk__in=service_ids))
        self._raw_delete(
            Cliente.objects.filter(pk=roots[demo_seed_entry("client")["key"]].pk)
        )
        self._raw_delete(
            ConfiguracaoFinanceira.objects.filter(
                pk=roots[demo_seed_entry("configuration")["key"]].pk
            )
        )

        deletion_history_targets, _seed_ids_by_model = (
            self._collect_history_targets(
                root_identities,
                known_seed_ids=seed_ids_by_model,
            )
        )
        history_ids_by_model = {}
        for history_model, history_ids in (
            history_targets + deletion_history_targets
        ):
            history_ids_by_model.setdefault(history_model, set()).update(history_ids)

        history_deleted = 0
        for history_model, history_ids in history_ids_by_model.items():
            deleted, _details = history_model._base_manager.filter(
                history_id__in=history_ids
            ).delete()
            history_deleted += deleted

        return {"live": before_live, "history": history_deleted}

    @staticmethod
    def _raw_delete(queryset):
        return queryset._raw_delete(queryset.db)

    def _validate_seed_unchanged(self, locked_roots, identification):
        try:
            resolved_seed = self._resolve_existing_seed()
        except CommandError as exc:
            raise CommandError(
                "O conjunto ficticio mudou durante a validacao; a limpeza foi "
                "revertida sem excluir dados."
            ) from exc

        if resolved_seed is None:
            raise CommandError(
                "O conjunto ficticio mudou durante a validacao; a limpeza foi "
                "revertida sem excluir dados."
            )

        current_objects, current_identification = resolved_seed
        locked_identities = {
            key: (obj._meta.label_lower, obj.pk) for key, obj in locked_roots.items()
        }
        current_identities = {
            key: (obj._meta.label_lower, obj.pk)
            for key, obj in current_objects.items()
        }
        if (
            current_identification != identification
            or current_identities != locked_identities
        ):
            raise CommandError(
                "O conjunto ficticio mudou durante a validacao; a limpeza foi "
                "revertida sem excluir dados."
            )

    @classmethod
    def _collect_history_targets(
        cls,
        root_identities,
        *,
        known_seed_ids=None,
    ):
        seed_ids_by_model = {
            model_label: set(object_ids)
            for model_label, object_ids in (known_seed_ids or {}).items()
        }
        for model_label, object_id in root_identities:
            seed_ids_by_model.setdefault(model_label, set()).add(object_id)

        related_models = [
            model
            for model in apps.get_app_config("caixa").get_models()
            if model._meta.model_name in DEMO_SEED_PARENT_FIELDS
        ]
        history_ids_by_model = {}
        changed = True
        while changed:
            changed = False
            for model in related_models:
                parent_query = cls._seed_parent_query(model, seed_ids_by_model)
                if parent_query is None:
                    continue

                related_ids = set(
                    model._base_manager.filter(parent_query).values_list(
                        "pk", flat=True
                    )
                )
                history = getattr(model, "history", None)
                history_model = getattr(history, "model", None)
                if history_model is not None:
                    related_history = list(
                        history_model._base_manager.filter(parent_query).values_list(
                            "id", "history_id"
                        )
                    )
                    related_ids.update(object_id for object_id, _ in related_history)
                    history_ids_by_model.setdefault(history_model, set()).update(
                        history_id for _, history_id in related_history
                    )

                model_ids = seed_ids_by_model.setdefault(
                    model._meta.label_lower, set()
                )
                new_ids = related_ids - model_ids
                if new_ids:
                    model_ids.update(new_ids)
                    changed = True

        targets = [
            (history_model, frozenset(history_ids))
            for history_model, history_ids in history_ids_by_model.items()
            if history_ids
        ]
        return targets, seed_ids_by_model

    @staticmethod
    def _seed_parent_query(model, seed_ids_by_model):
        query = None
        for field_name in DEMO_SEED_PARENT_FIELDS.get(
            model._meta.model_name, ()
        ):
            field = model._meta.get_field(field_name)
            parent_ids = seed_ids_by_model.get(
                field.related_model._meta.label_lower, set()
            )
            if not parent_ids:
                continue
            condition = Q(**{f"{field.attname}__in": parent_ids})
            query = condition if query is None else query | condition
        return query

    @classmethod
    def _is_resolved_seed_object(
        cls,
        obj,
        root_identities,
        *,
        visited=None,
    ):
        if obj is None or not hasattr(obj, "_meta"):
            return False

        identity = (obj._meta.label_lower, getattr(obj, "pk", None))
        if identity in root_identities:
            return True

        visited = visited or set()
        traversal_identity = (*identity, id(obj))
        if traversal_identity in visited:
            return False
        visited.add(traversal_identity)

        for field_name in DEMO_SEED_PARENT_FIELDS.get(obj._meta.model_name, ()):
            try:
                parent = getattr(obj, field_name, None)
            except ObjectDoesNotExist:
                parent = None
            if parent is not None and cls._is_resolved_seed_object(
                parent,
                root_identities,
                visited=visited,
            ):
                return True
        return False
