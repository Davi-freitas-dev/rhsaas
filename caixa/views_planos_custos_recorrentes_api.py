import logging
import json
import uuid
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import Http404
from django.db.models import Count
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models_custo_fixo import (
    AuditoriaCustoRecorrente,
    CustoFixo,
    PlanoCustoRecorrente,
)
from .permissions import (
    ADD_RECURRING_COST_PLAN_PERMISSION,
    CHANGE_RECURRING_COST_PLAN_PERMISSION,
    MATERIALIZE_RECURRING_COST_PLAN_PERMISSION,
    VIEW_RECURRING_COST_PLAN_PERMISSION,
    VIEW_SERVER_SALARY_PERMISSION,
)
from .security_salarios import filtrar_custos_fixos_por_salario
from .serializers_custos_recorrentes import (
    ApiErrorSerializer,
    RecurringMaterializationRequestSerializer,
    RecurringMaterializationResponseSerializer,
    RecurringPlanDetailResponseSerializer,
    RecurringPlanCreateSerializer,
    RecurringPlanListResponseSerializer,
    RecurringPlanMutationResponseSerializer,
    RecurringPlanUpdateSerializer,
    RecurringProjectionResponseSerializer,
)
from .services_idempotencia import (
    ChaveIdempotenciaInvalida,
    ConflitoChaveIdempotencia,
    executar_requisicao_idempotente,
    parsear_chave_idempotencia,
)
from .services_custos_recorrentes import (
    atualizar_plano_recorrente,
    criar_plano_recorrente,
    materializar_competencia,
    projetar_custos_recorrentes,
    recuperar_competencias_ausentes,
)
from .views_clientes_api import JsonBodySafeSessionAuthentication


logger = logging.getLogger(__name__)


IDEMPOTENCY_KEY_PARAMETER = OpenApiParameter(
    name="Idempotency-Key",
    location=OpenApiParameter.HEADER,
    required=True,
    type=str,
    description=(
        "UUID único da operação. A repetição do mesmo payload reproduz "
        "a resposta; payload diferente com a mesma chave é recusado."
    ),
)

IDEMPOTENCY_REPLAYED_RESPONSE_HEADER = OpenApiParameter(
    name="Idempotency-Replayed",
    location=OpenApiParameter.HEADER,
    response=[200, 201, 400, 401, 403, 409, 415, 500],
    type=str,
    description="`true` quando a resposta foi reproduzida; `false` na execução original ou rejeitada.",
)


def _unauthorized():
    return Response({"detail": "Authentication credentials were not provided."}, status=401)


def _denied():
    return Response({"detail": "Permission denied."}, status=403)


def _idempotent_response(body, *, status, replayed=False):
    response = Response(body, status=status)
    response["Idempotency-Replayed"] = "true" if replayed else "false"
    # Permite que clientes em outra origem leiam o resultado do replay.
    response["Access-Control-Expose-Headers"] = "Idempotency-Replayed"
    return response


def _json_mutation_payload(request):
    content_type = (request.content_type or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return _idempotent_response(
            {"detail": "Content-Type deve ser application/json."},
            status=415,
        )
    try:
        raw_body = request.body.decode("utf-8")
        payload = json.loads(raw_body) if raw_body.strip() else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    if not isinstance(payload, dict):
        return _idempotent_response(
            {"errors": {"detail": ["Informe um objeto JSON válido."]}},
            status=400,
        )
    return payload


def _errors(error):
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"detail": getattr(error, "messages", ["Dados inválidos."])}


def _safe_batch_response(result):
    counts = result["counts"]
    summary = {
        "requested": (
            len(result["results"]) + counts.get("notProcessed", 0)
        ),
        "created": counts["created"],
        "wouldCreate": counts["wouldCreate"],
        "alreadyMaterialized": counts["alreadyMaterialized"],
        "blocked": counts["blocked"] + counts["ignored"],
        "failed": counts["error"],
        "notProcessed": counts.get("notProcessed", 0),
    }
    data = {
        "status": result["status"],
        "correlationId": result["correlationId"],
        "summary": summary,
    }
    if result.get("failure"):
        data["failure"] = result["failure"]
    http_status = {
        "completed": 200,
        "completed_with_blocks": 200,
        "conflict": 409,
        "failed": 500,
    }[result["status"]]
    return {"data": data}, http_status


def _parse_date(payload, key, *, required=False):
    raw = payload.get(key)
    if raw in (None, ""):
        if required:
            raise ValidationError({key: "Informe uma data válida."})
        return None
    if hasattr(raw, "year") and hasattr(raw, "month"):
        return raw
    value = parse_date(str(raw))
    if value is None:
        raise ValidationError({key: "Informe uma data válida."})
    return value


def _parse_decimal(payload, key, *, required=False):
    raw = payload.get(key)
    if raw in (None, ""):
        if required:
            raise ValidationError({key: "Informe um valor válido."})
        return None
    try:
        return Decimal(str(raw).replace(",", "."))
    except (InvalidOperation, ValueError) as error:
        raise ValidationError({key: "Informe um valor válido."}) from error


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "nao", "não", "no"}
    return bool(value)


def _visible_plans(request):
    plans = PlanoCustoRecorrente.objects.select_related(
        "servidor",
        "plano_renovado",
        "custo_legado_referencia",
    ).annotate(materialized_count=Count("ocorrencias", distinct=True))
    if not request.user.has_perm(VIEW_SERVER_SALARY_PERMISSION):
        plans = plans.exclude(origem=PlanoCustoRecorrente.ORIGEM_SALARIO)
    return plans


def _serialize_plan(plan):
    materialized_count = getattr(plan, "materialized_count", None)
    if materialized_count is None:
        materialized_count = plan.ocorrencias.count()
    return {
        "id": plan.pk,
        "description": plan.descricao,
        "category": plan.categoria,
        "categoryLabel": plan.get_categoria_display(),
        "origin": plan.origem,
        "originLabel": plan.get_origem_display(),
        "frequency": plan.periodicidade,
        "plannedAmount": (
            f"{plan.valor_previsto:.2f}" if plan.valor_previsto is not None else None
        ),
        "startDate": plan.data_inicio.isoformat(),
        "endDate": plan.data_fim.isoformat() if plan.data_fim else None,
        "dueDay": plan.dia_vencimento,
        "authorizedMaterializationDate": (
            plan.data_autorizacao_materializacao.isoformat()
        ),
        "isActive": plan.ativo,
        "notes": plan.observacao,
        "serverId": plan.servidor_id,
        "legacyFixedCostId": plan.custo_legado_referencia_id,
        "renewedPlanId": plan.plano_renovado_id,
        "materializedCount": materialized_count,
        "createdAt": plan.criado_em.isoformat(),
        "updatedAt": plan.atualizado_em.isoformat(),
    }


def _plan_data(payload, *, plan=None, user=None):
    origin = plan.origem if plan else str(payload.get("origin") or "comum").strip().lower()
    if origin != PlanoCustoRecorrente.ORIGEM_COMUM:
        raise ValidationError(
            {"origin": "Planos salariais devem ser configurados no cadastro do servidor."}
        )

    category = str(payload.get("category") or (plan.categoria if plan else "outro")).strip()
    start_date = _parse_date(payload, "startDate", required=plan is None)
    authorization = _parse_date(
        payload,
        "authorizedMaterializationDate",
        required=plan is None,
    )
    due_day_raw = payload.get("dueDay", plan.dia_vencimento if plan else None)
    try:
        due_day = int(due_day_raw)
    except (TypeError, ValueError) as error:
        raise ValidationError({"dueDay": "Informe um dia entre 1 e 31."}) from error

    legacy_id = payload.get(
        "legacyFixedCostId",
        plan.custo_legado_referencia_id if plan else None,
    )
    renewed_id = payload.get("renewedPlanId", plan.plano_renovado_id if plan else None)
    legacy = None
    renewed = None
    if legacy_id:
        try:
            legacy = filtrar_custos_fixos_por_salario(
                CustoFixo.objects.all(),
                user,
            ).get(pk=legacy_id)
        except CustoFixo.DoesNotExist as error:
            raise ValidationError(
                {"legacyFixedCostId": "Custo legado não encontrado."}
            ) from error
    if renewed_id:
        try:
            renewed_queryset = PlanoCustoRecorrente.objects.all()
            if not user or not user.has_perm(VIEW_SERVER_SALARY_PERMISSION):
                renewed_queryset = renewed_queryset.exclude(
                    origem=PlanoCustoRecorrente.ORIGEM_SALARIO
                )
            renewed = renewed_queryset.get(pk=renewed_id)
        except PlanoCustoRecorrente.DoesNotExist as error:
            raise ValidationError({"renewedPlanId": "Plano anterior não encontrado."}) from error

    return {
        "descricao": str(
            payload.get("description", plan.descricao if plan else "")
        ).strip(),
        "categoria": category,
        "origem": origin,
        "periodicidade": PlanoCustoRecorrente.PERIODICIDADE_MENSAL,
        "valor_previsto": _parse_decimal(
            payload,
            "plannedAmount",
            required=plan is None,
        )
        if "plannedAmount" in payload or plan is None
        else plan.valor_previsto,
        "data_inicio": start_date or plan.data_inicio,
        "data_fim": (
            _parse_date(payload, "endDate")
            if "endDate" in payload
            else (plan.data_fim if plan else None)
        ),
        "dia_vencimento": due_day,
        "data_autorizacao_materializacao": (
            authorization or plan.data_autorizacao_materializacao
        ),
        "ativo": _parse_bool(
            payload.get("isActive"),
            plan.ativo if plan else True,
        ),
        "observacao": str(payload.get("notes", plan.observacao if plan else "")).strip(),
        "custo_legado_referencia": legacy,
        "plano_renovado": renewed,
        "servidor": None,
    }


@extend_schema(
    methods=["GET"],
    operation_id="recurring_cost_plans_list",
    parameters=[
        OpenApiParameter(
            name="active",
            type=bool,
            required=False,
            description="Filtra planos ativos ou inativos.",
        )
    ],
    responses={
        200: RecurringPlanListResponseSerializer,
        401: ApiErrorSerializer,
        403: ApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["POST"],
    operation_id="recurring_cost_plans_create",
    parameters=[IDEMPOTENCY_KEY_PARAMETER, IDEMPOTENCY_REPLAYED_RESPONSE_HEADER],
    request=RecurringPlanCreateSerializer,
    responses={
        201: RecurringPlanMutationResponseSerializer,
        400: ApiErrorSerializer,
        401: ApiErrorSerializer,
        403: ApiErrorSerializer,
        409: ApiErrorSerializer,
        415: ApiErrorSerializer,
        500: ApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_planos_custos_recorrentes(request):
    if not request.user.is_authenticated:
        if request.method == "POST":
            return _idempotent_response(_unauthorized().data, status=401)
        return _unauthorized()

    if request.method == "GET":
        if not request.user.has_perm(VIEW_RECURRING_COST_PLAN_PERMISSION):
            return _denied()
        plans = _visible_plans(request).order_by("data_inicio", "descricao", "id")
        active = (request.GET.get("active") or "").strip().lower()
        if active in {"true", "sim", "1"}:
            plans = plans.filter(ativo=True)
        elif active in {"false", "nao", "não", "0"}:
            plans = plans.filter(ativo=False)
        return Response(
            {
                "data": {
                    "recurringPlans": [_serialize_plan(plan) for plan in plans],
                    "total": plans.count(),
                    "permissions": {
                        "canCreate": request.user.has_perm(
                            ADD_RECURRING_COST_PLAN_PERMISSION
                        ),
                        "canUpdate": request.user.has_perm(
                            CHANGE_RECURRING_COST_PLAN_PERMISSION
                        ),
                        "canMaterialize": request.user.has_perm(
                            MATERIALIZE_RECURRING_COST_PLAN_PERMISSION
                        ),
                    },
                    "meta": {"source": "backend"},
                }
            }
        )

    if not request.user.has_perm(ADD_RECURRING_COST_PLAN_PERMISSION):
        return _idempotent_response(_denied().data, status=403)
    payload = _json_mutation_payload(request)
    if isinstance(payload, Response):
        return payload
    correlation_id = uuid.uuid4()
    try:
        idempotency_key = parsear_chave_idempotencia(
            request.headers.get("Idempotency-Key")
        )
        dados_plano = _plan_data(payload, user=request.user)

        def criar_plano():
            plan, materialization = criar_plano_recorrente(
                dados=dados_plano,
                usuario=request.user,
                materializar_atual=True,
            )
            return (
                {
                    "data": {
                        "recurringPlan": _serialize_plan(plan),
                        "materialization": materialization,
                        "message": "Plano recorrente criado com sucesso.",
                    }
                },
                201,
            )

        body, http_status, replayed = executar_requisicao_idempotente(
            escopo="criar-plano-custo-recorrente",
            chave=idempotency_key,
            payload=payload,
            ator=request.user,
            operacao=criar_plano,
        )
    except (ChaveIdempotenciaInvalida, ConflitoChaveIdempotencia) as error:
        return _idempotent_response(
            {"errors": {"Idempotency-Key": [str(error)]}},
            status=400,
        )
    except ValidationError as error:
        return _idempotent_response({"errors": _errors(error)}, status=400)
    except Exception as error:
        logger.error(
            "Falha inesperada ao criar plano recorrente",
            extra={
                "correlation_id": str(correlation_id),
                "exception_class": error.__class__.__name__,
            },
        )
        return _idempotent_response(
            {
                "errors": {
                    "detail": ["Não foi possível concluir a operação."],
                    "code": "UNEXPECTED_RECURRING_PLAN_FAILURE",
                    "correlationId": str(correlation_id),
                }
            },
            status=500,
        )
    return _idempotent_response(body, status=http_status, replayed=replayed)


@extend_schema(
    methods=["GET"],
    operation_id="recurring_cost_plans_retrieve",
    responses={
        200: RecurringPlanDetailResponseSerializer,
        401: ApiErrorSerializer,
        403: ApiErrorSerializer,
        404: ApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@extend_schema(
    methods=["PUT"],
    operation_id="recurring_cost_plans_update",
    parameters=[IDEMPOTENCY_KEY_PARAMETER, IDEMPOTENCY_REPLAYED_RESPONSE_HEADER],
    request=RecurringPlanUpdateSerializer,
    responses={
        200: RecurringPlanMutationResponseSerializer,
        400: ApiErrorSerializer,
        401: ApiErrorSerializer,
        403: ApiErrorSerializer,
        404: ApiErrorSerializer,
        409: ApiErrorSerializer,
        415: ApiErrorSerializer,
        500: ApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET", "PUT"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_plano_custo_recorrente_detalhe(request, pk):
    if not request.user.is_authenticated:
        if request.method == "PUT":
            return _idempotent_response(_unauthorized().data, status=401)
        return _unauthorized()
    permission = (
        VIEW_RECURRING_COST_PLAN_PERMISSION
        if request.method == "GET"
        else CHANGE_RECURRING_COST_PLAN_PERMISSION
    )
    if not request.user.has_perm(permission):
        if request.method == "PUT":
            return _idempotent_response(_denied().data, status=403)
        return _denied()
    try:
        plan = _visible_plans(request).get(pk=pk)
    except PlanoCustoRecorrente.DoesNotExist as error:
        if request.method == "PUT":
            return _idempotent_response(
                {"detail": "Not found."},
                status=404,
            )
        raise Http404 from error

    if request.method == "GET":
        return Response({"data": {"recurringPlan": _serialize_plan(plan)}})
    if plan.origem == PlanoCustoRecorrente.ORIGEM_SALARIO:
        return _idempotent_response(
            {
                "errors": {
                    "detail": "Plano salarial deve ser alterado no cadastro do servidor."
                }
            },
            status=400,
        )
    payload = _json_mutation_payload(request)
    if isinstance(payload, Response):
        return payload
    correlation_id = uuid.uuid4()
    try:
        idempotency_key = parsear_chave_idempotencia(
            request.headers.get("Idempotency-Key")
        )
        dados_plano = _plan_data(
            payload,
            plan=plan,
            user=request.user,
        )

        def atualizar_plano():
            plano_atualizado = atualizar_plano_recorrente(
                plan,
                dados=dados_plano,
                usuario=request.user,
            )
            return (
                {
                    "data": {
                        "recurringPlan": _serialize_plan(
                            plano_atualizado
                        ),
                        "message": "Plano recorrente atualizado com sucesso.",
                    }
                },
                200,
            )

        body, http_status, replayed = executar_requisicao_idempotente(
            escopo=f"atualizar-plano-recorrente:{plan.pk}",
            chave=idempotency_key,
            payload=payload,
            ator=request.user,
            operacao=atualizar_plano,
        )
    except (ChaveIdempotenciaInvalida, ConflitoChaveIdempotencia) as error:
        return _idempotent_response(
            {"errors": {"Idempotency-Key": [str(error)]}},
            status=400,
        )
    except ValidationError as error:
        return _idempotent_response({"errors": _errors(error)}, status=400)
    except Exception as error:
        logger.error(
            "Falha inesperada ao atualizar plano recorrente",
            extra={
                "correlation_id": str(correlation_id),
                "plan_id": plan.pk,
                "exception_class": error.__class__.__name__,
            },
        )
        return _idempotent_response(
            {
                "errors": {
                    "detail": ["Não foi possível concluir a operação."],
                    "code": "UNEXPECTED_RECURRING_PLAN_FAILURE",
                    "correlationId": str(correlation_id),
                }
            },
            status=500,
        )
    return _idempotent_response(body, status=http_status, replayed=replayed)


@extend_schema(
    methods=["GET"],
    operation_id="recurring_cost_projections_list",
    parameters=[
        OpenApiParameter(
            name="startDate",
            type=str,
            required=True,
            description="Data inicial inclusiva no formato AAAA-MM-DD.",
        ),
        OpenApiParameter(
            name="endDate",
            type=str,
            required=True,
            description="Data final inclusiva no formato AAAA-MM-DD.",
        ),
    ],
    responses={
        200: RecurringProjectionResponseSerializer,
        400: ApiErrorSerializer,
        401: ApiErrorSerializer,
        403: ApiErrorSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["GET"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_projecoes_custos_recorrentes(request):
    if not request.user.is_authenticated:
        return _unauthorized()
    if not request.user.has_perm(VIEW_RECURRING_COST_PLAN_PERMISSION):
        return _denied()
    try:
        start = parse_date(request.GET.get("startDate") or "")
        end = parse_date(request.GET.get("endDate") or "")
        if not start or not end:
            raise ValidationError(
                {"period": "Informe startDate e endDate no formato AAAA-MM-DD."}
            )
        projection = projetar_custos_recorrentes(
            inicio=start,
            fim=end,
            planos=_visible_plans(request).filter(ativo=True),
        )
    except ValidationError as error:
        return Response({"errors": _errors(error)}, status=400)
    return Response({"data": projection})


@extend_schema(
    methods=["POST"],
    operation_id="recurring_cost_materializations_create",
    parameters=[IDEMPOTENCY_KEY_PARAMETER, IDEMPOTENCY_REPLAYED_RESPONSE_HEADER],
    request=RecurringMaterializationRequestSerializer,
    responses={
        200: RecurringMaterializationResponseSerializer,
        400: ApiErrorSerializer,
        401: ApiErrorSerializer,
        403: ApiErrorSerializer,
        409: RecurringMaterializationResponseSerializer,
        415: ApiErrorSerializer,
        500: RecurringMaterializationResponseSerializer,
    },
    auth=[{"cookieAuth": []}],
)
@api_view(["POST"])
@authentication_classes([JsonBodySafeSessionAuthentication])
@permission_classes([AllowAny])
def api_materializar_custos_recorrentes(request):
    if not request.user.is_authenticated:
        return _idempotent_response(_unauthorized().data, status=401)
    if not request.user.has_perm(MATERIALIZE_RECURRING_COST_PLAN_PERMISSION):
        return _idempotent_response(_denied().data, status=403)
    payload = _json_mutation_payload(request)
    if isinstance(payload, Response):
        return payload
    correlation_id = uuid.uuid4()
    try:
        idempotency_key = parsear_chave_idempotencia(
            request.headers.get("Idempotency-Key")
        )

        def executar_materializacao():
            dry_run = _parse_bool(payload.get("dryRun"), False)
            recover_missing = _parse_bool(
                payload.get("recoverMissing"),
                False,
            )
            if recover_missing:
                if payload.get("competence") not in (None, ""):
                    raise ValidationError(
                        {
                            "mode": (
                                "Informe competence para uma execução única ou "
                                "recoverMissing, nunca ambos."
                            )
                        }
                    )
                through_competence = _parse_date(
                    payload,
                    "throughCompetence",
                    required=True,
                )
                result = recuperar_competencias_ausentes(
                    competencia_limite=through_competence,
                    usuario=request.user,
                    dry_run=dry_run,
                    planos=_visible_plans(request).filter(ativo=True),
                    origem=AuditoriaCustoRecorrente.ORIGEM_API,
                    correlation_id=correlation_id,
                )
            else:
                competence = _parse_date(
                    payload,
                    "competence",
                    required=True,
                )
                result = materializar_competencia(
                    competencia=competence,
                    usuario=request.user,
                    dry_run=dry_run,
                    planos=_visible_plans(request).filter(ativo=True),
                    origem=AuditoriaCustoRecorrente.ORIGEM_API,
                    correlation_id=correlation_id,
                )
            return _safe_batch_response(result)

        body, http_status, replayed = executar_requisicao_idempotente(
            escopo="materializar-custos-recorrentes",
            chave=idempotency_key,
            payload=payload,
            ator=request.user,
            operacao=executar_materializacao,
        )
    except (ChaveIdempotenciaInvalida, ConflitoChaveIdempotencia) as error:
        return _idempotent_response(
            {"errors": {"Idempotency-Key": [str(error)]}},
            status=400,
        )
    except ValidationError as error:
        return _idempotent_response({"errors": _errors(error)}, status=400)
    except Exception as error:
        logger.error(
            "Falha inesperada no endpoint de materialização recorrente",
            extra={
                "correlation_id": str(correlation_id),
                "exception_class": error.__class__.__name__,
            },
        )
        return _idempotent_response(
            {
                "data": {
                    "status": "failed",
                    "correlationId": str(correlation_id),
                    "summary": {
                        "requested": 0,
                        "created": 0,
                        "wouldCreate": 0,
                        "alreadyMaterialized": 0,
                        "blocked": 0,
                        "failed": 1,
                        "notProcessed": 0,
                    },
                    "failure": {
                        "code": "UNEXPECTED_MATERIALIZATION_FAILURE",
                        "planId": None,
                        "competence": None,
                    },
                }
            },
            status=500,
        )
    return _idempotent_response(body, status=http_status, replayed=replayed)
