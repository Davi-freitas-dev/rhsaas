import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import NoReverseMatch, reverse

from caixa.frontend_bridge import (
    LEGACY_FRONTEND_SURFACES,
    build_next_frontend_url_for_surface,
    next_frontend_base_url,
)


DEFAULT_OUTPUT_JSON = "pm06-redirect-next-legado.json"
DEFAULT_OUTPUT_RECORD = "pm06-redirect-next-legado.md"


def normalizar_surfaces(surfaces):
    normalizadas = []
    vistas = set()
    for surface in surfaces or []:
        surface = str(surface or "").strip()
        if not surface or surface in vistas:
            continue
        normalizadas.append(surface)
        vistas.add(surface)
    return normalizadas


def validar_redirects_next_legado(options):
    configured_surfaces = normalizar_surfaces(
        getattr(settings, "NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES", [])
    )
    requested_surfaces = normalizar_surfaces(options.get("surfaces"))
    candidate_surfaces = requested_surfaces or configured_surfaces
    frontend_base_url = next_frontend_base_url()
    redirects_enabled = bool(
        getattr(settings, "NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED", False)
    )
    issues = []
    surface_results = []

    if redirects_enabled and not configured_surfaces and not requested_surfaces:
        issues.append(
            {
                "code": "redirectEnabledWithoutAllowlist",
                "detail": "Redirect global ativo sem allowlist configurada.",
            }
        )

    if options.get("exigir_unitario") and len(candidate_surfaces) != 1:
        issues.append(
            {
                "code": "expectedSingleSurface",
                "detail": "Validacao unitaria exige exatamente uma superficie.",
            }
        )

    for surface_key in candidate_surfaces:
        surface = LEGACY_FRONTEND_SURFACES.get(surface_key)
        if not surface:
            issues.append(
                {
                    "code": "unknownSurface",
                    "surface": surface_key,
                    "detail": "Superficie nao cadastrada para ponte Next.js.",
                }
            )
            surface_results.append(
                {
                    "surface": surface_key,
                    "known": False,
                    "redirectEligible": False,
                }
            )
            continue

        django_url = resolver_django_url(surface_key)
        next_url = build_next_frontend_url_for_surface(surface_key)
        redirect_eligible = surface["status"] == "migrated" and bool(next_url)

        if surface["status"] != "migrated":
            issues.append(
                {
                    "code": "surfaceNotMigrated",
                    "surface": surface_key,
                    "status": surface["status"],
                    "detail": "Apenas superficies migrated podem receber redirect.",
                }
            )

        if not next_url:
            issues.append(
                {
                    "code": "missingFrontendUrl",
                    "surface": surface_key,
                    "detail": "NEXT_FRONTEND_URL ausente para montar o destino.",
                }
            )

        if not django_url:
            issues.append(
                {
                    "code": "missingDjangoRoute",
                    "surface": surface_key,
                    "detail": "Nao foi possivel resolver a rota Django da superficie.",
                }
            )

        surface_results.append(
            {
                "surface": surface_key,
                "known": True,
                "status": surface["status"],
                "djangoUrl": django_url,
                "nextUrl": next_url,
                "redirectEligible": redirect_eligible,
            }
        )

    ready = not issues
    recommended_surfaces = [
        surface["surface"]
        for surface in surface_results
        if surface.get("redirectEligible")
    ]
    activation = montar_plano_ativacao(
        ready=ready,
        frontend_base_url=frontend_base_url,
        recommended_surfaces=recommended_surfaces,
    )
    resultado = {
        "ready": ready,
        "redirectsEnabled": redirects_enabled,
        "frontendBaseUrl": frontend_base_url,
        "source": "argument" if requested_surfaces else "settings",
        "configuredSurfaces": configured_surfaces,
        "candidateSurfaces": candidate_surfaces,
        "surfaces": surface_results,
        "issues": issues,
        "activation": activation,
    }
    resultado["executionRecord"] = {
        "format": "markdown",
        "markdown": registro_redirects_next_legado(resultado),
    }
    return resultado


def montar_plano_ativacao(*, ready, frontend_base_url, recommended_surfaces):
    surfaces_value = ",".join(recommended_surfaces)
    ready_to_activate = ready and bool(recommended_surfaces)
    candidate_surface = recommended_surfaces[0] if len(recommended_surfaces) == 1 else ""
    validate_candidate_command = ""
    if candidate_surface:
        validate_candidate_command = (
            "python manage.py validar_redirects_next_legado "
            f"--surface={candidate_surface} --exigir-unitario --falhar --json"
        )

    return {
        "readyToActivate": ready_to_activate,
        "recommendedEnabledValue": "True",
        "recommendedSurfacesValue": surfaces_value,
        "recommendedEnvironment": {
            "NEXT_FRONTEND_URL": frontend_base_url,
            "NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED": (
                "True" if ready_to_activate else "False"
            ),
            "NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES": surfaces_value,
        },
        "rollbackEnvironment": {
            "NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED": "False",
            "NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES": "",
        },
        "commands": {
            "validateCandidate": validate_candidate_command,
            "validateEnvironment": (
                "python manage.py validar_redirects_next_legado --falhar --json"
            ),
            "rollbackValidation": (
                "python manage.py validar_redirects_next_legado --json"
            ),
        },
    }


def resolver_django_url(surface_key):
    surface = LEGACY_FRONTEND_SURFACES.get(surface_key) or {}
    try:
        return reverse(f"caixa:{surface_key}", args=surface.get("routeArgs", []))
    except NoReverseMatch:
        return ""


def formatar_erro_redirects_next_legado(resultado):
    if not resultado["issues"]:
        return "Redirects Next legado aprovados."

    primeira_issue = resultado["issues"][0]
    detalhe = primeira_issue.get("detail") or primeira_issue["code"]
    surface = primeira_issue.get("surface")
    if surface:
        return f"Redirects Next legado reprovados: {surface}: {detalhe}"
    return f"Redirects Next legado reprovados: {detalhe}"


def registro_redirects_next_legado(resultado):
    activation = resultado["activation"]
    lines = [
        "### Registro PM-06.1104 - canario de redirect Next legado",
        "",
        f"- ready: {resultado['ready']}",
        f"- source: {resultado['source']}",
        f"- frontendBaseUrl: {resultado['frontendBaseUrl'] or '-'}",
        f"- redirectsEnabled: {resultado['redirectsEnabled']}",
        "- candidateSurfaces: "
        f"{','.join(resultado['candidateSurfaces']) or '-'}",
        "- recommendedSurfaces: "
        f"{activation['recommendedSurfacesValue'] or '-'}",
        f"- readyToActivate: {activation['readyToActivate']}",
        "",
        "#### Superficies avaliadas",
    ]

    if resultado["surfaces"]:
        for surface in resultado["surfaces"]:
            lines.append(
                "- "
                f"{surface['surface']}: status={surface.get('status') or '-'}; "
                f"django={surface.get('djangoUrl') or '-'}; "
                f"next={surface.get('nextUrl') or '-'}; "
                f"redirectEligible={surface.get('redirectEligible') is True}"
            )
    else:
        lines.append("- -")

    lines.extend(["", "#### Pendencias"])
    if resultado["issues"]:
        for issue in resultado["issues"]:
            surface = issue.get("surface")
            prefix = f"{surface}: " if surface else ""
            lines.append(f"- {prefix}{issue['detail']}")
    else:
        lines.append("- nenhuma")

    env = activation["recommendedEnvironment"]
    rollback_env = activation["rollbackEnvironment"]
    commands = activation["commands"]
    output_files = resultado.get("outputEvidenceFiles") or {}
    lines.extend(
        [
            "",
            "#### Ativacao sugerida",
            f"- NEXT_FRONTEND_URL={env['NEXT_FRONTEND_URL'] or '-'}",
            "- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED="
            f"{env['NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED']}",
            "- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES="
            f"{env['NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES'] or '-'}",
            "",
            "#### Comandos",
            f"- validateCandidate: {commands['validateCandidate'] or '-'}",
            f"- validateEnvironment: {commands['validateEnvironment']}",
            f"- rollbackValidation: {commands['rollbackValidation']}",
            "",
            "#### Rollback",
            "- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED="
            f"{rollback_env['NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED']}",
            "- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES="
            f"{rollback_env['NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES'] or '<vazio>'}",
            "",
            "#### Arquivos salvos",
            f"- json: {output_files.get('json') or '-'}",
            f"- registro: {output_files.get('record') or '-'}",
        ]
    )

    return "\n".join(lines)


class Command(BaseCommand):
    help = (
        "Valida a configuracao de redirects controlados das telas Django "
        "legadas para o frontend Next.js."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado consolidado em JSON.",
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro quando a validacao reprovar.",
        )
        parser.add_argument(
            "--surface",
            action="append",
            dest="surfaces",
            default=[],
            help="Superficie Django a validar como candidata de redirect.",
        )
        parser.add_argument(
            "--exigir-unitario",
            action="store_true",
            help="Reprova se a validacao nao tiver exatamente uma superficie.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON da validacao em arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o executionRecord.markdown em arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help=(
                "Diretorio usado para salvar JSON e Markdown com nomes "
                "padronizados da PM-06.1105."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            action="store_true",
            help="Reprova se os caminhos de JSON e registro nao forem informados.",
        )

    def handle(self, *args, **options):
        output_files = normalizar_arquivos_saida(options)
        resultado = validar_redirects_next_legado(options)
        resultado["outputEvidenceFiles"] = output_files
        _aplicar_issues_arquivos_saida(
            resultado,
            validar_arquivos_saida(
                output_files,
                exigir=options["exigir_arquivos_evidencia"],
            ),
        )
        atualizar_execution_record(resultado)
        salvar_resultado(resultado)

        if options["json_output"]:
            self.stdout.write(
                json.dumps(resultado, ensure_ascii=False, sort_keys=True)
            )
        else:
            self._imprimir_relatorio(resultado)

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_redirects_next_legado(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Redirects Next legado aprovados.")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Redirects Next legado com pendencias.")
            )

        self.stdout.write(f"Origem: {resultado['source']}")
        self.stdout.write(
            "Redirect global ativo: "
            f"{'sim' if resultado['redirectsEnabled'] else 'nao'}"
        )
        self.stdout.write(
            f"Frontend Next.js: {resultado['frontendBaseUrl'] or '-'}"
        )

        if resultado["surfaces"]:
            self.stdout.write("Superficies avaliadas:")
            for surface in resultado["surfaces"]:
                status = surface.get("status") or "desconhecida"
                next_url = surface.get("nextUrl") or "-"
                elegivel = "sim" if surface.get("redirectEligible") else "nao"
                self.stdout.write(
                    f"- {surface['surface']}: status={status}; "
                    f"redirectEligible={elegivel}; next={next_url}"
                )
        else:
            self.stdout.write("Superficies avaliadas: -")

        if resultado["issues"]:
            self.stdout.write("Pendencias:")
            for issue in resultado["issues"]:
                surface = issue.get("surface")
                prefixo = f"{surface}: " if surface else ""
                self.stdout.write(f"- {prefixo}{issue['detail']}")

        ativacao = resultado["activation"]
        self.stdout.write(
            "Sugestao allowlist: "
            f"{ativacao['recommendedSurfacesValue'] or '-'}"
        )
        self.stdout.write("Registro markdown:")
        self.stdout.write(resultado["executionRecord"]["markdown"])


def normalizar_arquivos_saida(options):
    evidence_dir = options.get("diretorio_evidencias") or ""
    save_json = options.get("salvar_json") or ""
    save_record = options.get("salvar_registro") or ""
    if evidence_dir:
        base_path = Path(evidence_dir).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError("--diretorio-evidencias deve apontar para um diretorio")
        if not save_json:
            save_json = str(base_path / DEFAULT_OUTPUT_JSON)
        if not save_record:
            save_record = str(base_path / DEFAULT_OUTPUT_RECORD)
    return {
        "directory": evidence_dir,
        "json": save_json,
        "record": save_record,
    }


def validar_arquivos_saida(output_files, *, exigir=False):
    if not exigir:
        return []
    issues = []
    if not (output_files.get("json") or ""):
        issues.append("arquivo JSON de evidencia PM-06.1105 nao informado")
    if not (output_files.get("record") or ""):
        issues.append("registro markdown de evidencia PM-06.1105 nao informado")
    return issues


def _aplicar_issues_arquivos_saida(resultado, output_issues):
    if not output_issues:
        return
    resultado["ready"] = False
    for issue in output_issues:
        resultado["issues"].append(
            {
                "code": "missingEvidenceOutput",
                "detail": issue,
            }
        )
    recommended_surfaces = [
        surface["surface"]
        for surface in resultado["surfaces"]
        if surface.get("redirectEligible")
    ]
    resultado["activation"] = montar_plano_ativacao(
        ready=False,
        frontend_base_url=resultado["frontendBaseUrl"],
        recommended_surfaces=recommended_surfaces,
    )


def atualizar_execution_record(resultado):
    resultado["executionRecord"] = {
        "format": "markdown",
        "markdown": registro_redirects_next_legado(resultado),
    }


def salvar_resultado(resultado):
    output_files = resultado.get("outputEvidenceFiles") or {}
    json_path = output_files.get("json")
    record_path = output_files.get("record")
    if json_path:
        salvar_texto(
            json_path,
            json.dumps(resultado, ensure_ascii=False, sort_keys=True, indent=2),
        )
    if record_path:
        salvar_texto(record_path, resultado["executionRecord"]["markdown"])


def salvar_texto(path, content):
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
