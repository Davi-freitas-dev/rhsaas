import json
import subprocess
from io import StringIO
from pathlib import Path
from urllib.parse import urlsplit

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.management.commands.auditar_totais_negocio import auditar_totais_negocio
from caixa.management.commands.gerar_snapshot_baseline_financeira import (
    PM02_AGGREGATE_COMMAND,
    PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION,
    PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL,
    PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE,
    PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_EVIDENCE,
    PM02_STRICT_SERVER_COMMAND,
    PM02_STRICT_SERVER_COMMAND_WITH_DEPLOY_URL,
    _sanitize_url_or_value,
    gerar_snapshot_baseline_financeira,
)
from caixa.management.commands.validar_operacao_obrigacoes import (
    validar_operacao_obrigacoes,
)
from caixa.management.commands.validar_preflight_deploy_financeiro import (
    validar_preflight_deploy_financeiro,
)
from tenancy.command_guards import ensure_tenant_schema


PM02_MANUAL_REQUIREMENTS = [
    {
        "key": "releaseReference",
        "label": "Criar tag/referencia exata do codigo publicado",
        "suggestedCommand": "git rev-parse HEAD",
    },
    {
        "key": "databaseBackup",
        "label": "Fazer backup do banco real antes da janela",
        "suggestedCommand": "python manage.py backup_banco_mensal --force --manter 12",
    },
    {
        "key": "environmentLabel",
        "label": "Identificar ambiente operacional da janela",
        "suggestedCommand": "--ambiente=producao",
        "suggestedLegacyCommand": "DESATIVADO no RH SaaS: perfil legado do projeto antigo.",
    },
    {
        "key": "environmentSnapshot",
        "label": "Registrar variaveis reais de canonical-first, cache, cookies, banco e frontend",
        "suggestedCommand": "python manage.py gerar_snapshot_baseline_financeira --json",
    },
    {
        "key": "serverValidationRecord",
        "label": "Registrar data, ambiente, commit/tag, backup, comandos e resultados no plano mestre",
        "suggestedCommand": PM02_STRICT_SERVER_COMMAND,
        "suggestedLegacyCommand": PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION,
        "suggestedLegacyCommandWithDeployUrl": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL
        ),
        "suggestedLegacyCommandWithEvidence": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_EVIDENCE
        ),
        "suggestedLegacyCommandWithDeployUrlAndEvidence": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE
        ),
    },
]
PM02_STRICT_FLAG_REQUIREMENTS = [
    {
        "key": "failOnValidation",
        "label": "Reprovar validacoes automaticas",
        "option": "falhar",
        "flag": "--falhar",
    },
    {
        "key": "failIfDirty",
        "label": "Reprovar worktree dirty",
        "option": "falhar_se_dirty",
        "flag": "--falhar-se-dirty",
    },
    {
        "key": "failIfDebug",
        "label": "Reprovar DEBUG ativo",
        "option": "falhar_se_debug",
        "flag": "--falhar-se-debug",
    },
    {
        "key": "requireFrontendReference",
        "label": "Exigir referencia do frontend",
        "option": "exigir_frontend_referencia",
        "flag": "--exigir-frontend-referencia",
    },
    {
        "key": "requireReleaseReference",
        "label": "Exigir release/tag/commit do backend",
        "option": "exigir_release_ref",
        "flag": "--exigir-release-ref",
    },
    {
        "key": "requireBackupReference",
        "label": "Exigir backup real",
        "option": "exigir_backup_ref",
        "flag": "--exigir-backup-ref",
    },
    {
        "key": "requireEnvironmentLabel",
        "label": "Exigir nome operacional do ambiente",
        "option": "exigir_ambiente",
        "flag": "--exigir-ambiente",
    },
    {
        "key": "requirePm02Closure",
        "label": "Exigir fechamento PM-02",
        "option": "exigir_fechamento_pm02",
        "flag": "--exigir-fechamento-pm02",
    },
]
LEGACY_PRODUCTION_PROFILE_DEFAULTS = {
}
LEGACY_PRODUCTION_PROFILE_LABEL = "perfil-legado-desativado"


class Command(BaseCommand):
    help = (
        "Executa a baseline PM-02 em modo somente leitura: snapshot, check, "
        "makemigrations dry-run, pre-flight, validacao operacional e auditoria."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o resultado consolidado em JSON.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o resultado JSON consolidado em um arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o bloco executionRecord.markdown em um arquivo.",
        )
        parser.add_argument(
            "--salvar-snapshot-json",
            "--save-snapshot-json",
            default="",
            help="Salva o snapshot interno da baseline em um arquivo JSON.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-dir",
            default="",
            help=(
                "Diretorio para salvar pm02-baseline.json, pm02-registro.md "
                "e pm02-snapshot.json quando caminhos especificos nao forem "
                "informados."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os tres caminhos de evidencia PM-02 nao forem "
                "informados por --diretorio-evidencias ou caminhos explicitos."
            ),
        )
        parser.add_argument(
            "--falhar",
            action="store_true",
            help="Retorna erro se qualquer etapa da baseline PM-02 reprovar.",
        )
        parser.add_argument(
            "--modo-servidor-estrito",
            "--strict-server",
            action="store_true",
            help=(
                "Ativa todas as travas da janela PM-02 real: --falhar, "
                "--falhar-se-dirty, --falhar-se-debug, exigencias de "
                "frontend, release, backup, ambiente e fechamento PM-02."
            ),
        )
        parser.add_argument(
            "--frontend-path",
            default="",
            help="Caminho opcional do frontend Next.js usado no snapshot.",
        )
        parser.add_argument(
            "--frontend-ref",
            default="",
            help="Referencia manual do frontend publicado, por exemplo commit da Vercel.",
        )
        parser.add_argument(
            "--frontend-deploy-url",
            default="",
            help="URL opcional do deploy frontend usado na janela PM-02.",
        )
        parser.add_argument(
            "--release-ref",
            default="",
            help="Tag, commit ou referencia exata do codigo publicado.",
        )
        parser.add_argument(
            "--backup-ref",
            default="",
            help="Nome, caminho ou identificador do backup real usado na janela.",
        )
        parser.add_argument(
            "--ambiente",
            default="",
            help="Nome operacional do ambiente da janela, por exemplo producao.",
        )
        parser.add_argument(
            "--perfil-legado-producao",
            "--legacy-production-profile",
            action="store_true",
            help=(
                "Perfil legado do projeto antigo. Esta opcao fica desativada "
                "no RH SaaS."
            ),
        )
        parser.add_argument(
            "--esperar-session-cookie-domain",
            "--expected-session-cookie-domain",
            default="",
            help="Valor esperado de SESSION_COOKIE_DOMAIN na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-csrf-cookie-domain",
            "--expected-csrf-cookie-domain",
            default="",
            help="Valor esperado de CSRF_COOKIE_DOMAIN na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-session-cookie-secure",
            "--expected-session-cookie-secure",
            default="",
            help="Valor esperado de SESSION_COOKIE_SECURE na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-csrf-cookie-secure",
            "--expected-csrf-cookie-secure",
            default="",
            help="Valor esperado de CSRF_COOKIE_SECURE na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-session-cookie-samesite",
            "--expected-session-cookie-samesite",
            default="",
            help="Valor esperado de SESSION_COOKIE_SAMESITE na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-csrf-cookie-samesite",
            "--expected-csrf-cookie-samesite",
            default="",
            help="Valor esperado de CSRF_COOKIE_SAMESITE na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-cache-backend",
            "--expected-cache-backend",
            default="",
            help="Backend de cache esperado na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-cache-location",
            "--expected-cache-location",
            default="",
            help="LOCATION de cache esperado na janela PM-02.",
        )
        parser.add_argument(
            "--esperar-canonical-first-enabled",
            "--expected-canonical-first-enabled",
            default="",
            help="Valor esperado de CANONICAL_FIRST_SETTLEMENT_ENABLED.",
        )
        parser.add_argument(
            "--esperar-canonical-first-sources",
            "--expected-canonical-first-sources",
            default="",
            help="Lista esperada de CANONICAL_FIRST_SETTLEMENT_SOURCES separada por virgula.",
        )
        parser.add_argument(
            "--esperar-database-engine",
            "--expected-database-engine",
            default="",
            help="ENGINE esperado do banco da janela PM-02.",
        )
        parser.add_argument(
            "--esperar-database-name",
            "--expected-database-name",
            default="",
            help="NAME esperado do banco da janela PM-02.",
        )
        parser.add_argument(
            "--esperar-database-host",
            "--expected-database-host",
            default="",
            help="HOST esperado do banco da janela PM-02.",
        )
        parser.add_argument(
            "--esperar-database-port",
            "--expected-database-port",
            default="",
            help="PORT esperado do banco da janela PM-02.",
        )
        parser.add_argument(
            "--esperar-allowed-hosts",
            "--expected-allowed-hosts",
            default="",
            help="Lista esperada de ALLOWED_HOSTS separada por virgula.",
        )
        parser.add_argument(
            "--esperar-csrf-trusted-origins",
            "--expected-csrf-trusted-origins",
            default="",
            help="Lista esperada de CSRF_TRUSTED_ORIGINS separada por virgula.",
        )
        parser.add_argument(
            "--esperar-cors-allowed-origins",
            "--expected-cors-allowed-origins",
            default="",
            help="Lista esperada de CORS_ALLOWED_ORIGINS separada por virgula.",
        )
        parser.add_argument(
            "--exigir-release-ref",
            "--require-release-ref",
            action="store_true",
            help="Reprova se --release-ref nao for informado.",
        )
        parser.add_argument(
            "--exigir-release-git-ref-existente",
            "--require-release-git-ref-exists",
            action="store_true",
            help=(
                "Reprova se --release-ref nao existir como commit/ref no git "
                "local do backend. Use quando a referencia for tag ou commit."
            ),
        )
        parser.add_argument(
            "--exigir-backup-ref",
            "--require-backup-ref",
            action="store_true",
            help="Reprova se --backup-ref nao for informado.",
        )
        parser.add_argument(
            "--exigir-backup-arquivo-existente",
            "--require-backup-file-exists",
            action="store_true",
            help=(
                "Reprova se --backup-ref nao apontar para um arquivo local "
                "existente. Use apenas quando o backup for caminho de arquivo."
            ),
        )
        parser.add_argument(
            "--exigir-ambiente",
            "--require-environment-label",
            action="store_true",
            help="Reprova se --ambiente nao for informado.",
        )
        parser.add_argument(
            "--exigir-frontend-referencia",
            "--require-frontend-ref",
            action="store_true",
            help=(
                "Reprova se nao houver checkout do frontend com commit git, "
                "referencia manual via --frontend-ref ou URL via "
                "--frontend-deploy-url."
            ),
        )
        parser.add_argument(
            "--exigir-frontend-deploy-url-https",
            "--require-frontend-deploy-url-https",
            action="store_true",
            help=(
                "Reprova se --frontend-deploy-url nao for uma URL HTTPS. "
                "Use quando a evidencia do frontend for URL publicada."
            ),
        )
        parser.add_argument(
            "--falhar-se-dirty",
            action="store_true",
            help="Reprova se backend ou frontend estiverem com alteracoes git.",
        )
        parser.add_argument(
            "--falhar-se-debug",
            action="store_true",
            help="Reprova se DEBUG estiver ativo.",
        )
        parser.add_argument(
            "--exigir-fechamento-pm02",
            "--require-pm02-closure",
            action="store_true",
            help=(
                "Reprova se a PM-02 nao estiver pronta para fechamento "
                "apos validacoes automaticas e evidencias manuais."
            ),
        )

    def handle(self, *args, **options):
        options = _normalizar_opcoes_pm02(options)
        ensure_tenant_schema("validar_baseline_pm02", action="validar dados operacionais")
        resultado = validar_baseline_pm02(options)
        json_text = json.dumps(resultado, ensure_ascii=False, sort_keys=True)

        if options["json_output"]:
            self.stdout.write(json_text)
        else:
            self._imprimir_relatorio(resultado)

        if options.get("salvar_json"):
            _salvar_arquivo_pm02(options["salvar_json"], f"{json_text}\n")
        if options.get("salvar_registro"):
            _salvar_arquivo_pm02(
                options["salvar_registro"],
                f"{resultado['executionRecord']['markdown']}\n",
            )
        if options.get("salvar_snapshot_json"):
            _salvar_arquivo_pm02(
                options["salvar_snapshot_json"],
                (
                    json.dumps(
                        resultado["snapshot"],
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                ),
            )

        if options["falhar"] and not resultado["ready"]:
            raise CommandError(formatar_erro_baseline_pm02(resultado))
        if options["exigir_fechamento_pm02"] and not resultado["pm02ClosureReady"]:
            raise CommandError(formatar_erro_fechamento_pm02(resultado))

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Baseline PM-02 automatica aprovada.")
            )
            self.stdout.write(
                "Conclusao operacional ainda depende de release, backup, "
                "ambiente e referencia do frontend no servidor."
            )
        else:
            self.stdout.write(
                self.style.WARNING("Baseline PM-02 com pontos de atencao.")
            )

        for check in resultado["checks"]:
            status = "ok" if check["ok"] else "falhou"
            self.stdout.write(f"- {check['label']}: {status}")
            if check["issues"]:
                self.stdout.write(f"  primeira pendencia: {check['issues'][0]}")

        snapshot = resultado["snapshot"]
        self.stdout.write(
            "Backend: "
            f"commit={snapshot['git']['commitShort'] or '-'}; "
            f"dirty={'sim' if snapshot['git']['dirty'] else 'nao'}"
        )
        frontend = snapshot["frontend"]
        if frontend["exists"]:
            self.stdout.write(
                "Frontend: "
                f"commit={frontend['git']['commitShort'] or '-'}; "
                f"dirty={'sim' if frontend['git']['dirty'] else 'nao'}; "
                f"packageManager={frontend['packageManager'] or '-'}"
            )
        evidence = resultado["serverEvidence"]
        self.stdout.write(
            "Evidencias informadas: "
            f"release={evidence['releaseRef'] or '-'}; "
            f"backup={evidence['backupRef'] or '-'}; "
            f"frontendRef={evidence['frontendRef'] or '-'}; "
            f"frontendDeployUrl={evidence['frontendDeployUrl'] or '-'}"
        )
        self.stdout.write(
            f"Ambiente informado: {resultado['environmentLabel'] or '-'}"
        )
        self.stdout.write(
            f"Perfil de ambiente: {resultado['environmentProfile'] or '-'}"
        )
        self.stdout.write(
            "Evidencias manuais: "
            f"{'completas' if resultado['manualEvidenceComplete'] else 'pendentes'}"
        )
        self.stdout.write(
            "PM-02 pronta para fechamento apos revisoes: "
            f"{'sim' if resultado['pm02ClosureReady'] else 'nao'}"
        )
        self.stdout.write(
            f"Proxima acao PM-02: {resultado['pm02NextAction']['label']}"
        )
        if resultado["pm02NextAction"].get("suggestedCommand"):
            self.stdout.write(
                "Comando sugerido para proxima acao: "
                f"{resultado['pm02NextAction']['suggestedCommand']}"
            )
        if resultado["pm02NextAction"].get("suggestedLegacyCommand"):
            self.stdout.write(
                "Comando legado sugerido para proxima acao: "
                f"{resultado['pm02NextAction']['suggestedLegacyCommand']}"
            )
        self.stdout.write(
            "Flags estritas de servidor: "
            f"{'completas' if resultado['strictServerFlagsComplete'] else 'pendentes'}"
        )
        self.stdout.write(
            "Modo servidor estrito: "
            f"{'sim' if resultado['strictServerMode'] else 'nao'}"
        )
        if resultado["pm02ClosureBlockers"]:
            self.stdout.write("Bloqueios para fechamento PM-02:")
            for blocker in resultado["pm02ClosureBlockers"]:
                self.stdout.write(f"- {blocker}")
        for evidence_item in resultado["manualEvidenceStatus"]:
            status = "ok" if evidence_item["ok"] else "pendente"
            self.stdout.write(f"- {evidence_item['label']}: {status}")
        for flag_item in resultado["strictServerFlagsStatus"]:
            status = "ok" if flag_item["ok"] else "pendente"
            self.stdout.write(f"- {flag_item['flag']} ({flag_item['label']}): {status}")
        self.stdout.write("Comando estrito PM-02 para servidor:")
        self.stdout.write(resultado["strictServerCommand"])
        self.stdout.write("Comando estrito PM-02 usando URL do deploy:")
        self.stdout.write(resultado["strictServerCommandWithDeployUrl"])
        self.stdout.write("Comando estrito PM-02 para producao legado:")
        self.stdout.write(resultado["strictServerCommandLegacyProduction"])
        self.stdout.write("Comando estrito PM-02 legado usando URL do deploy:")
        self.stdout.write(
            resultado["strictServerCommandLegacyProductionWithDeployUrl"]
        )
        self.stdout.write("Comando estrito PM-02 legado com evidencias:")
        self.stdout.write(
            resultado["strictServerCommandLegacyProductionWithEvidence"]
        )
        self.stdout.write(
            "Comando estrito PM-02 legado usando URL e evidencias:"
        )
        self.stdout.write(
            resultado[
                "strictServerCommandLegacyProductionWithDeployUrlAndEvidence"
            ]
        )
        self.stdout.write("Comando estrito PM-02 preenchido:")
        self.stdout.write(resultado["strictServerCommandResolved"])
        self.stdout.write("Registro sugerido para o plano mestre:")
        self.stdout.write(resultado["executionRecord"]["markdown"])
        self.stdout.write("Confirmacoes manuais que ainda fecham a PM-02:")
        for requirement in resultado["manualRequirements"]:
            self.stdout.write(f"- {requirement['label']}")
            if requirement.get("suggestedCommand"):
                self.stdout.write(
                    f"  comando sugerido: {requirement['suggestedCommand']}"
                )
            if requirement.get("suggestedLegacyCommand"):
                self.stdout.write(
                    "  comando legado sugerido: "
                    f"{requirement['suggestedLegacyCommand']}"
                )
            if requirement.get("suggestedLegacyCommandWithDeployUrl"):
                self.stdout.write(
                    "  comando legado com URL sugerido: "
                    f"{requirement['suggestedLegacyCommandWithDeployUrl']}"
                )
            if requirement.get("suggestedLegacyCommandWithEvidence"):
                self.stdout.write(
                    "  comando legado com evidencias sugerido: "
                    f"{requirement['suggestedLegacyCommandWithEvidence']}"
                )
            if requirement.get("suggestedLegacyCommandWithDeployUrlAndEvidence"):
                suggested_command = requirement[
                    "suggestedLegacyCommandWithDeployUrlAndEvidence"
                ]
                self.stdout.write(
                    "  comando legado com URL e evidencias sugerido: "
                    f"{suggested_command}"
                )


def validar_baseline_pm02(options=None):
    options = _normalizar_opcoes_pm02(options)
    ensure_tenant_schema("validar_baseline_pm02", action="validar dados operacionais")
    snapshot = gerar_snapshot_baseline_financeira(
        frontend_path=options.get("frontend_path"),
        frontend_ref=options.get("frontend_ref"),
        frontend_deploy_url=options.get("frontend_deploy_url"),
    )
    environment_expectations = _environment_expectation_status(
        snapshot,
        expected_session_cookie_domain=options.get(
            "esperar_session_cookie_domain",
            "",
        ),
        expected_csrf_cookie_domain=options.get("esperar_csrf_cookie_domain", ""),
        expected_session_cookie_secure=options.get(
            "esperar_session_cookie_secure",
            "",
        ),
        expected_csrf_cookie_secure=options.get(
            "esperar_csrf_cookie_secure",
            "",
        ),
        expected_session_cookie_samesite=options.get(
            "esperar_session_cookie_samesite",
            "",
        ),
        expected_csrf_cookie_samesite=options.get(
            "esperar_csrf_cookie_samesite",
            "",
        ),
        expected_cache_backend=options.get("esperar_cache_backend", ""),
        expected_cache_location=options.get("esperar_cache_location", ""),
        expected_canonical_first_enabled=options.get(
            "esperar_canonical_first_enabled",
            "",
        ),
        expected_canonical_first_sources=options.get(
            "esperar_canonical_first_sources",
            "",
        ),
        expected_database_engine=options.get("esperar_database_engine", ""),
        expected_database_name=options.get("esperar_database_name", ""),
        expected_database_host=options.get("esperar_database_host", ""),
        expected_database_port=options.get("esperar_database_port", ""),
        expected_allowed_hosts=options.get("esperar_allowed_hosts", ""),
        expected_csrf_trusted_origins=options.get(
            "esperar_csrf_trusted_origins",
            "",
        ),
        expected_cors_allowed_origins=options.get(
            "esperar_cors_allowed_origins",
            "",
        ),
    )
    evidence_files = {
        "directory": options.get("diretorio_evidencias", ""),
        "json": options.get("salvar_json", ""),
        "record": options.get("salvar_registro", ""),
        "snapshotJson": options.get("salvar_snapshot_json", ""),
    }
    checks = [
        _validar_snapshot(
            snapshot,
            falhar_se_dirty=options.get("falhar_se_dirty", False),
            falhar_se_debug=options.get("falhar_se_debug", False),
            exigir_frontend_referencia=options.get(
                "exigir_frontend_referencia",
                False,
            ),
            release_ref=options.get("release_ref", ""),
            backup_ref=options.get("backup_ref", ""),
            environment_label=options.get("ambiente", ""),
            frontend_ref=options.get("frontend_ref", ""),
            frontend_deploy_url=options.get("frontend_deploy_url", ""),
            exigir_release_ref=options.get("exigir_release_ref", False),
            exigir_backup_ref=options.get("exigir_backup_ref", False),
            exigir_backup_arquivo_existente=options.get(
                "exigir_backup_arquivo_existente",
                False,
            ),
            exigir_ambiente=options.get("exigir_ambiente", False),
            exigir_frontend_deploy_ref=options.get("modo_servidor_estrito", False),
            exigir_release_git_ref_existente=options.get(
                "exigir_release_git_ref_existente",
                False,
            ),
            exigir_frontend_deploy_url_https=options.get(
                "exigir_frontend_deploy_url_https",
                False,
            ),
        ),
        _validar_expectativas_ambiente(environment_expectations),
        _validar_arquivos_evidencia(
            evidence_files,
            exigir=options.get("exigir_arquivos_evidencia", False),
        ),
        _executar_comando_django(
            "djangoCheck",
            "Django check",
            "check",
        ),
        _executar_comando_django(
            "makemigrationsCheck",
            "Makemigrations dry-run",
            "makemigrations",
            "--check",
            "--dry-run",
        ),
        _validar_preflight(),
        _validar_operacao(),
        _auditar_totais(),
    ]

    manual_evidence_status = _manual_evidence_status(
        snapshot,
        release_ref=options.get("release_ref", ""),
        backup_ref=options.get("backup_ref", ""),
        environment_label=options.get("ambiente", ""),
        exigir_frontend_deploy_ref=options.get("modo_servidor_estrito", False),
    )
    generated_at = timezone.now().isoformat()
    ready = all(check["ok"] for check in checks)
    issues = [
        issue
        for check in checks
        for issue in check["issues"]
    ]
    server_evidence = {
        "releaseRef": options.get("release_ref", ""),
        "backupRef": options.get("backup_ref", ""),
        "frontendRef": options.get("frontend_ref", ""),
        "frontendDeployUrl": options.get("frontend_deploy_url", ""),
        "environmentLabel": options.get("ambiente", ""),
        "environmentProfile": _environment_profile_label(options),
    }
    manual_evidence_complete = all(
        evidence["ok"] for evidence in manual_evidence_status
    )
    strict_server_flags_status = _strict_server_flags_status(options)
    strict_server_flags_complete = all(
        flag["ok"] for flag in strict_server_flags_status
    )
    pm02_closure_ready = (
        ready
        and manual_evidence_complete
        and strict_server_flags_complete
    )
    pm02_closure_blockers = _pm02_closure_blockers(
        ready=ready,
        issues=issues,
        manual_evidence_status=manual_evidence_status,
        strict_server_flags_status=strict_server_flags_status,
    )
    pm02_next_action = _pm02_next_action(
        ready=ready,
        issues=issues,
        manual_evidence_complete=manual_evidence_complete,
        strict_server_flags_complete=strict_server_flags_complete,
        pm02_closure_ready=pm02_closure_ready,
    )
    strict_server_command_resolved = _pm02_strict_server_command_resolved(
        server_evidence,
        environment_expectations=environment_expectations,
        save_directory=options.get("diretorio_evidencias", ""),
        save_json=options.get("salvar_json", ""),
        save_record=options.get("salvar_registro", ""),
        save_snapshot_json=options.get("salvar_snapshot_json", ""),
        require_backup_file_exists=options.get(
            "exigir_backup_arquivo_existente",
            False,
        ),
        require_release_git_ref_exists=options.get(
            "exigir_release_git_ref_existente",
            False,
        ),
        require_frontend_deploy_url_https=options.get(
            "exigir_frontend_deploy_url_https",
            False,
        ),
        require_evidence_files=options.get("exigir_arquivos_evidencia", False),
    )

    return {
        "generatedAt": generated_at,
        "readOnly": True,
        "ready": ready,
        "snapshot": snapshot,
        "serverEvidence": server_evidence,
        "environmentLabel": options.get("ambiente", ""),
        "environmentProfile": _environment_profile_label(options),
        "environmentProfileDefaults": _environment_profile_defaults(options),
        "environmentProfileDefaultsApplied": (
            _environment_profile_defaults_applied(options)
        ),
        "environmentProfileOverrides": _environment_profile_overrides(options),
        "environmentExpectations": environment_expectations,
        "strictServerCommand": PM02_STRICT_SERVER_COMMAND,
        "strictServerCommandWithDeployUrl": PM02_STRICT_SERVER_COMMAND_WITH_DEPLOY_URL,
        "strictServerCommandLegacyProduction": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION
        ),
        "strictServerCommandLegacyProductionWithDeployUrl": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL
        ),
        "strictServerCommandLegacyProductionWithEvidence": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_EVIDENCE
        ),
        "strictServerCommandLegacyProductionWithDeployUrlAndEvidence": (
            PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE
        ),
        "strictServerCommandResolved": strict_server_command_resolved,
        "strictServerMode": bool(options.get("modo_servidor_estrito", False)),
        "manualEvidenceComplete": manual_evidence_complete,
        "manualEvidenceStatus": manual_evidence_status,
        "strictServerFlagsComplete": strict_server_flags_complete,
        "strictServerFlagsStatus": strict_server_flags_status,
        "pm02ClosureReady": pm02_closure_ready,
        "pm02ClosureBlockers": pm02_closure_blockers,
        "pm02NextAction": pm02_next_action,
        "executionRecord": _pm02_execution_record(
            generated_at=generated_at,
            ready=ready,
            issues=issues,
            snapshot=snapshot,
            server_evidence=server_evidence,
            environment_label=options.get("ambiente", ""),
            strict_server_command=strict_server_command_resolved,
            strict_server_mode=bool(options.get("modo_servidor_estrito", False)),
            manual_evidence_complete=manual_evidence_complete,
            strict_server_flags_complete=strict_server_flags_complete,
            pm02_closure_ready=pm02_closure_ready,
            pm02_closure_blockers=pm02_closure_blockers,
            pm02_next_action=pm02_next_action,
            environment_profile_defaults=_environment_profile_defaults(options),
            environment_profile_defaults_applied=(
                _environment_profile_defaults_applied(options)
            ),
            environment_profile_overrides=_environment_profile_overrides(options),
            manual_evidence_status=manual_evidence_status,
            strict_server_flags_status=strict_server_flags_status,
            environment_expectations=environment_expectations,
            checks=checks,
            evidence_files=evidence_files,
        ),
        "evidenceFiles": evidence_files,
        "checks": checks,
        "manualRequirements": PM02_MANUAL_REQUIREMENTS,
        "issues": issues,
    }


def _normalizar_opcoes_pm02(options=None):
    options = dict(options or {})
    options.setdefault("_environment_profile_defaults_applied", {})
    options.setdefault("_environment_profile_overrides", {})
    if options.get("modo_servidor_estrito", False):
        for requirement in PM02_STRICT_FLAG_REQUIREMENTS:
            options[requirement["option"]] = True
    if options.get("perfil_legado_producao", False):
        raise CommandError(
            "O perfil legado --perfil-legado-producao esta desativado no RH SaaS. "
            "Informe os parametros esperados explicitamente para o ambiente atual."
        )
    evidence_dir = options.get("diretorio_evidencias", "")
    if evidence_dir:
        base_path = Path(evidence_dir).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError(
                "--diretorio-evidencias deve apontar para um diretorio"
            )
        if not options.get("salvar_json"):
            options["salvar_json"] = str(base_path / "pm02-baseline.json")
        if not options.get("salvar_registro"):
            options["salvar_registro"] = str(base_path / "pm02-registro.md")
        if not options.get("salvar_snapshot_json"):
            options["salvar_snapshot_json"] = str(base_path / "pm02-snapshot.json")
    return options


def _environment_profile_label(options):
    if options.get("perfil_legado_producao", False):
        return LEGACY_PRODUCTION_PROFILE_LABEL
    return ""


def _environment_profile_defaults(options):
    if options.get("perfil_legado_producao", False):
        return dict(LEGACY_PRODUCTION_PROFILE_DEFAULTS)
    return {}


def _environment_profile_defaults_applied(options):
    return dict(options.get("_environment_profile_defaults_applied") or {})


def _environment_profile_overrides(options):
    return dict(options.get("_environment_profile_overrides") or {})


def _salvar_arquivo_pm02(path_value, content):
    path = Path(path_value).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git_ref_existe(repo_path, release_ref):
    if not release_ref:
        return False
    try:
        resultado = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{release_ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return False
    return resultado.returncode == 0


def _url_https_valida(url):
    if not url:
        return False
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validar_snapshot(
    snapshot,
    falhar_se_dirty=False,
    falhar_se_debug=False,
    exigir_frontend_referencia=False,
    release_ref="",
    backup_ref="",
    environment_label="",
    frontend_ref="",
    frontend_deploy_url="",
    exigir_release_ref=False,
    exigir_backup_ref=False,
    exigir_backup_arquivo_existente=False,
    exigir_ambiente=False,
    exigir_frontend_deploy_ref=False,
    exigir_release_git_ref_existente=False,
    exigir_frontend_deploy_url_https=False,
):
    issues = []
    if falhar_se_dirty and snapshot["git"]["dirty"]:
        issues.append("backend com alteracoes git")
    if (
        falhar_se_dirty
        and snapshot["frontend"]["exists"]
        and snapshot["frontend"]["git"]["dirty"]
    ):
        issues.append("frontend com alteracoes git")
    if falhar_se_debug and snapshot["environment"]["debug"]:
        issues.append("DEBUG ativo")
    if exigir_frontend_referencia and not _snapshot_tem_referencia_frontend(snapshot):
        issues.append("frontend sem referencia publicada")
    if exigir_frontend_deploy_ref and not (frontend_ref or frontend_deploy_url):
        issues.append("frontend sem referencia declarada do deploy")
    frontend_deploy_url_https = _url_https_valida(frontend_deploy_url)
    if exigir_frontend_deploy_url_https:
        if not frontend_deploy_url:
            issues.append("frontend deploy URL sem referencia para validar HTTPS")
        elif not frontend_deploy_url_https:
            issues.append("frontend deploy URL nao HTTPS")
    if exigir_release_ref and not release_ref:
        issues.append("release sem referencia publicada")
    release_git_ref_exists = (
        _git_ref_existe(snapshot["project"]["backendRoot"], release_ref)
        if release_ref and exigir_release_git_ref_existente
        else False
    )
    if exigir_release_git_ref_existente:
        if not release_ref:
            issues.append("release sem referencia para validar git")
        elif not release_git_ref_exists:
            issues.append("release/ref git nao encontrado no repositorio local")
    if exigir_backup_ref and not backup_ref:
        issues.append("backup real sem referencia")
    if exigir_backup_arquivo_existente:
        if not backup_ref:
            issues.append("backup real sem referencia para validar arquivo")
        elif not Path(backup_ref).expanduser().exists():
            issues.append("backup real nao encontrado no caminho informado")
    if exigir_ambiente and not environment_label:
        issues.append("ambiente sem identificacao")

    backup_file_path = Path(backup_ref).expanduser() if backup_ref else None
    return _check_result(
        "snapshot",
        "Snapshot PM-02",
        not issues,
        issues=issues,
        detail={
            "backendCommit": snapshot["git"]["commitShort"],
            "frontendCommit": snapshot["frontend"]["git"]["commitShort"],
            "frontendDeclaredReference": snapshot["frontend"]["declaredReference"],
            "frontendExists": snapshot["frontend"]["exists"],
            "frontendDeployUrl": frontend_deploy_url,
            "frontendDeployUrlHttpsRequired": exigir_frontend_deploy_url_https,
            "frontendDeployUrlHttps": frontend_deploy_url_https,
            "releaseRef": release_ref,
            "releaseGitRefExistsRequired": exigir_release_git_ref_existente,
            "releaseGitRefExists": release_git_ref_exists,
            "backupRef": backup_ref,
            "backupFileExistsRequired": exigir_backup_arquivo_existente,
            "backupFileExists": (
                backup_file_path.exists() if backup_file_path else False
            ),
            "environmentLabel": environment_label,
        },
    )


def _environment_expectation_status(
    snapshot,
    expected_session_cookie_domain="",
    expected_csrf_cookie_domain="",
    expected_session_cookie_secure="",
    expected_csrf_cookie_secure="",
    expected_session_cookie_samesite="",
    expected_csrf_cookie_samesite="",
    expected_cache_backend="",
    expected_cache_location="",
    expected_canonical_first_enabled="",
    expected_canonical_first_sources="",
    expected_database_engine="",
    expected_database_name="",
    expected_database_host="",
    expected_database_port="",
    expected_allowed_hosts="",
    expected_csrf_trusted_origins="",
    expected_cors_allowed_origins="",
):
    environment = snapshot["environment"]
    cookies = snapshot["cookies"]
    cache = snapshot["cache"]
    canonical = snapshot["canonicalFirst"]
    database = snapshot["database"]
    expected_cache_location = _sanitize_url_or_value(expected_cache_location)
    expected_session_cookie_secure = _normalizar_booleano_texto(
        expected_session_cookie_secure
    )
    expected_csrf_cookie_secure = _normalizar_booleano_texto(
        expected_csrf_cookie_secure
    )
    expected_session_cookie_samesite = _normalizar_samesite_texto(
        expected_session_cookie_samesite
    )
    expected_csrf_cookie_samesite = _normalizar_samesite_texto(
        expected_csrf_cookie_samesite
    )
    expected_canonical_first_enabled = _normalizar_booleano_texto(
        expected_canonical_first_enabled
    )
    expected_canonical_first_sources = _normalizar_lista_origens(
        expected_canonical_first_sources
    )
    actual_canonical_first_sources = _normalizar_lista_origens(
        ",".join(canonical.get("sources", []))
    )
    expected_allowed_hosts = _normalizar_lista_texto(expected_allowed_hosts)
    expected_csrf_trusted_origins = _normalizar_lista_texto(
        expected_csrf_trusted_origins
    )
    expected_cors_allowed_origins = _normalizar_lista_texto(
        expected_cors_allowed_origins
    )
    expectations = [
        {
            "key": "allowedHosts",
            "label": "ALLOWED_HOSTS",
            "expected": expected_allowed_hosts or "",
            "actual": _normalizar_lista_texto(environment.get("allowedHosts", [])),
        },
        {
            "key": "csrfTrustedOrigins",
            "label": "CSRF_TRUSTED_ORIGINS",
            "expected": expected_csrf_trusted_origins or "",
            "actual": _normalizar_lista_texto(
                environment.get("csrfTrustedOrigins", [])
            ),
        },
        {
            "key": "corsAllowedOrigins",
            "label": "CORS_ALLOWED_ORIGINS",
            "expected": expected_cors_allowed_origins or "",
            "actual": _normalizar_lista_texto(
                environment.get("corsAllowedOrigins", [])
            ),
        },
        {
            "key": "sessionCookieDomain",
            "label": "SESSION_COOKIE_DOMAIN",
            "expected": expected_session_cookie_domain or "",
            "actual": cookies.get("sessionCookieDomain") or "",
        },
        {
            "key": "csrfCookieDomain",
            "label": "CSRF_COOKIE_DOMAIN",
            "expected": expected_csrf_cookie_domain or "",
            "actual": cookies.get("csrfCookieDomain") or "",
        },
        {
            "key": "sessionCookieSecure",
            "label": "SESSION_COOKIE_SECURE",
            "expected": expected_session_cookie_secure or "",
            "actual": _normalizar_booleano_texto(
                cookies.get("sessionCookieSecure")
            ),
        },
        {
            "key": "csrfCookieSecure",
            "label": "CSRF_COOKIE_SECURE",
            "expected": expected_csrf_cookie_secure or "",
            "actual": _normalizar_booleano_texto(cookies.get("csrfCookieSecure")),
        },
        {
            "key": "sessionCookieSameSite",
            "label": "SESSION_COOKIE_SAMESITE",
            "expected": expected_session_cookie_samesite or "",
            "actual": _normalizar_samesite_texto(
                cookies.get("sessionCookieSameSite")
            ),
        },
        {
            "key": "csrfCookieSameSite",
            "label": "CSRF_COOKIE_SAMESITE",
            "expected": expected_csrf_cookie_samesite or "",
            "actual": _normalizar_samesite_texto(cookies.get("csrfCookieSameSite")),
        },
        {
            "key": "cacheBackend",
            "label": "CACHE_BACKEND",
            "expected": expected_cache_backend or "",
            "actual": cache.get("backend") or "",
        },
        {
            "key": "cacheLocation",
            "label": "CACHE_LOCATION",
            "expected": expected_cache_location or "",
            "actual": cache.get("location") or "",
        },
        {
            "key": "canonicalFirstEnabled",
            "label": "CANONICAL_FIRST_SETTLEMENT_ENABLED",
            "expected": expected_canonical_first_enabled or "",
            "actual": _normalizar_booleano_texto(canonical.get("enabled")),
        },
        {
            "key": "canonicalFirstSources",
            "label": "CANONICAL_FIRST_SETTLEMENT_SOURCES",
            "expected": expected_canonical_first_sources or "",
            "actual": actual_canonical_first_sources,
        },
        {
            "key": "databaseEngine",
            "label": "DATABASE_ENGINE",
            "expected": expected_database_engine or "",
            "actual": database.get("engine") or "",
        },
        {
            "key": "databaseName",
            "label": "DATABASE_NAME",
            "expected": expected_database_name or "",
            "actual": database.get("name") or "",
        },
        {
            "key": "databaseHost",
            "label": "DATABASE_HOST",
            "expected": expected_database_host or "",
            "actual": database.get("host") or "",
        },
        {
            "key": "databasePort",
            "label": "DATABASE_PORT",
            "expected": str(expected_database_port or ""),
            "actual": str(database.get("port") or ""),
        },
    ]
    for expectation in expectations:
        expectation["required"] = bool(expectation["expected"])
        expectation["ok"] = (
            not expectation["expected"]
            or expectation["actual"] == expectation["expected"]
        )
    return expectations


def _normalizar_booleano_texto(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    normalized = str(value).strip().lower()
    if not normalized:
        return ""
    if normalized in {"1", "true", "sim", "yes", "on"}:
        return "true"
    if normalized in {"0", "false", "nao", "no", "off"}:
        return "false"
    return normalized


def _normalizar_samesite_texto(value):
    if value is None:
        return ""
    normalized = str(value).strip().lower()
    if not normalized:
        return ""
    if normalized in {"none", "lax", "strict"}:
        return normalized
    return normalized


def _normalizar_lista_origens(value):
    return _normalizar_lista_texto(value)


def _normalizar_lista_texto(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = str(value).split(",")
    normalized = sorted(
        item.strip()
        for item in items
        if str(item).strip()
    )
    return ",".join(normalized)


def _validar_expectativas_ambiente(environment_expectations):
    issues = [
        (
            f"{expectation['label']} diferente do esperado: "
            f"atual={expectation['actual'] or '-'}; "
            f"esperado={expectation['expected']}"
        )
        for expectation in environment_expectations
        if not expectation["ok"]
    ]
    return _check_result(
        "environmentExpectations",
        "Expectativas de ambiente",
        not issues,
        issues=issues,
        detail={
            "expectations": environment_expectations,
        },
    )


def _validar_arquivos_evidencia(evidence_files, exigir=False):
    missing = [
        label
        for key, label in [
            ("json", "json"),
            ("record", "registro"),
            ("snapshotJson", "snapshot"),
        ]
        if not evidence_files.get(key)
    ]
    issues = []
    if exigir and missing:
        issues.append(
            "arquivos de evidencia PM-02 incompletos: " + ", ".join(missing)
        )
    return _check_result(
        "evidenceFiles",
        "Arquivos de evidencia PM-02",
        not issues,
        issues=issues,
        detail={
            "required": exigir,
            "files": evidence_files,
            "missing": missing,
        },
    )


def _manual_evidence_status(
    snapshot,
    release_ref="",
    backup_ref="",
    environment_label="",
    exigir_frontend_deploy_ref=False,
):
    frontend = snapshot["frontend"]
    frontend_reference = frontend.get("declaredReference") or frontend.get("deployUrl") or ""
    if not exigir_frontend_deploy_ref:
        frontend_reference = (
            frontend_reference
            or frontend.get("git", {}).get("commitShort")
            or ""
        )
    return [
        {
            "key": "releaseReference",
            "label": "Release/tag/commit do backend",
            "ok": bool(release_ref),
            "value": release_ref or "",
        },
        {
            "key": "databaseBackup",
            "label": "Backup real do banco",
            "ok": bool(backup_ref),
            "value": backup_ref or "",
        },
        {
            "key": "frontendReference",
            "label": "Referencia do frontend publicado",
            "ok": bool(frontend_reference),
            "value": frontend_reference,
        },
        {
            "key": "environmentSnapshot",
            "label": "Snapshot de ambiente gerado",
            "ok": bool(snapshot.get("generatedAt")),
            "value": snapshot.get("generatedAt", ""),
        },
        {
            "key": "environmentLabel",
            "label": "Nome operacional do ambiente",
            "ok": bool(environment_label),
            "value": environment_label or "",
        },
    ]


def _strict_server_flags_status(options):
    return [
        {
            "key": requirement["key"],
            "label": requirement["label"],
            "flag": requirement["flag"],
            "ok": bool(options.get(requirement["option"], False)),
        }
        for requirement in PM02_STRICT_FLAG_REQUIREMENTS
    ]


def _pm02_closure_blockers(
    ready,
    issues,
    manual_evidence_status,
    strict_server_flags_status,
):
    blockers = []
    if not ready:
        if issues:
            blockers.extend(
                f"validacao automatica pendente: {issue}"
                for issue in issues
            )
        else:
            blockers.append("validacoes automaticas nao aprovadas")

    blockers.extend(
        f"evidencia pendente: {item['label']}"
        for item in manual_evidence_status
        if not item["ok"]
    )
    blockers.extend(
        f"flag estrita pendente: {item['flag']} ({item['label']})"
        for item in strict_server_flags_status
        if not item["ok"]
    )
    return blockers


def _pm02_next_action(
    ready,
    issues,
    manual_evidence_complete,
    strict_server_flags_complete,
    pm02_closure_ready,
):
    if not ready:
        return {
            "key": "fixAutomaticValidation",
            "label": "Corrigir validacoes automaticas reprovadas",
            "detail": "; ".join(issues) if issues else "baseline automatica reprovada",
            "suggestedCommand": PM02_AGGREGATE_COMMAND,
        }
    if not manual_evidence_complete:
        return {
            "key": "provideManualEvidence",
            "label": "Executar PM-02 no servidor com release, backup, ambiente e frontend publicados",
            "detail": "usar o comando estrito apropriado e informar evidencias reais",
            "suggestedCommand": PM02_STRICT_SERVER_COMMAND,
            "suggestedLegacyCommand": (
                PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE
            ),
        }
    if not strict_server_flags_complete:
        return {
            "key": "rerunStrictServerMode",
            "label": "Reexecutar validacao com o comando estrito completo",
            "detail": "usar --modo-servidor-estrito ou a sugestao legada equivalente",
            "suggestedCommand": PM02_STRICT_SERVER_COMMAND,
            "suggestedLegacyCommand": (
                PM02_STRICT_SERVER_COMMAND_LEGACY_PRODUCTION_WITH_DEPLOY_URL_AND_EVIDENCE
            ),
        }
    if pm02_closure_ready:
        return {
            "key": "recordReviews",
            "label": "Registrar revisoes obrigatorias e decidir fechamento da PM-02",
            "detail": "colar executionRecord.markdown no plano mestre apos revisoes",
        }
    return {
        "key": "reviewBlockers",
        "label": "Revisar bloqueios PM-02 antes de avancar",
        "detail": "consultar pm02ClosureBlockers",
    }


def _pm02_execution_record(
    generated_at,
    ready,
    issues,
    snapshot,
    server_evidence,
    environment_label,
    strict_server_command,
    strict_server_mode,
    manual_evidence_complete,
    strict_server_flags_complete,
    pm02_closure_ready,
    pm02_closure_blockers,
    pm02_next_action,
    environment_profile_defaults,
    environment_profile_defaults_applied,
    environment_profile_overrides,
    manual_evidence_status,
    strict_server_flags_status,
    environment_expectations,
    checks,
    evidence_files,
):
    frontend = snapshot["frontend"]
    canonical = snapshot["canonicalFirst"]
    cache = snapshot["cache"]
    cookies = snapshot["cookies"]
    frontend_ref = (
        server_evidence["frontendRef"]
        or server_evidence["frontendDeployUrl"]
        or frontend.get("declaredReference")
        or frontend.get("deployUrl")
        or frontend.get("git", {}).get("commitShort")
        or "-"
    )
    release_ref = (
        server_evidence["releaseRef"]
        or snapshot["git"]["commitShort"]
        or "-"
    )
    backup_ref = server_evidence["backupRef"] or "-"
    environment_name = environment_label or "-"
    environment_profile = server_evidence.get("environmentProfile") or "-"
    sources = ", ".join(canonical["sources"]) or "-"
    issue_summary = "; ".join(issues) if issues else "nenhuma"
    evidence_summary = "; ".join(
        f"{item['key']}={'ok' if item['ok'] else 'pendente'}"
        for item in manual_evidence_status
    )
    strict_flags_summary = "; ".join(
        f"{item['key']}={'ok' if item['ok'] else 'pendente'}"
        for item in strict_server_flags_status
    )
    checks_summary = "; ".join(
        f"{check['key']}={'ok' if check['ok'] else 'falhou'}"
        for check in checks
    )
    environment_expectation_summary = _environment_expectation_summary(
        environment_expectations
    )
    blocker_summary = (
        "; ".join(pm02_closure_blockers)
        if pm02_closure_blockers
        else "nenhum"
    )
    evidence_files_summary = (
        f"diretorio={evidence_files.get('directory') or '-'}; "
        f"json={evidence_files.get('json') or '-'}; "
        f"registro={evidence_files.get('record') or '-'}; "
        f"snapshot={evidence_files.get('snapshotJson') or '-'}"
    )
    next_action_suggested_command = pm02_next_action.get("suggestedCommand") or "-"
    next_action_legacy_command = (
        pm02_next_action.get("suggestedLegacyCommand") or "-"
    )
    profile_defaults_summary = _profile_mapping_summary(environment_profile_defaults)
    profile_defaults_applied_summary = _profile_mapping_summary(
        environment_profile_defaults_applied
    )
    profile_overrides_summary = _profile_overrides_summary(
        environment_profile_overrides
    )

    markdown = "\n".join(
        [
            "### Registro PM-02 - evidencia real da baseline",
            "",
            f"Data/hora da janela: {generated_at}",
            f"Ambiente: {environment_name}",
            f"Perfil de ambiente: {environment_profile}",
            f"Defaults do perfil de ambiente: {profile_defaults_summary}",
            (
                "Defaults aplicados do perfil de ambiente: "
                f"{profile_defaults_applied_summary}"
            ),
            f"Overrides do perfil de ambiente: {profile_overrides_summary}",
            f"Backend release/tag/commit: {release_ref}",
            f"Frontend ref/deploy Vercel: {frontend_ref}",
            f"Backup real: {backup_ref}",
            (
                "CANONICAL_FIRST_SETTLEMENT_ENABLED: "
                f"{canonical['enabled']}"
            ),
            f"CANONICAL_FIRST_SETTLEMENT_SOURCES: {sources}",
            (
                "Cache backend/location: "
                f"{cache['backend'] or '-'}; {cache['location'] or '-'}"
            ),
            (
                "Cookie domain/session/csrf: "
                f"session={cookies['sessionCookieDomain'] or '-'}; "
                f"csrf={cookies['csrfCookieDomain'] or '-'}; "
                f"sessionSecure={cookies['sessionCookieSecure']}; "
                f"csrfSecure={cookies['csrfCookieSecure']}; "
                f"sessionSameSite={cookies['sessionCookieSameSite'] or '-'}; "
                f"csrfSameSite={cookies['csrfCookieSameSite'] or '-'}"
            ),
            f"Expectativas de ambiente: {environment_expectation_summary}",
            f"Comando estrito executado: {strict_server_command}",
            f"strictServerMode: {strict_server_mode}",
            f"Resultado ready/issues: ready={ready}; issues={issue_summary}",
            f"manualEvidenceComplete: {manual_evidence_complete}",
            f"strictServerFlagsComplete: {strict_server_flags_complete}",
            f"pm02ClosureReady: {pm02_closure_ready}",
            f"pm02ClosureBlockers: {blocker_summary}",
            f"pm02NextAction: {pm02_next_action['key']} - {pm02_next_action['label']}",
            f"pm02NextActionSuggestedCommand: {next_action_suggested_command}",
            f"pm02NextActionSuggestedLegacyCommand: {next_action_legacy_command}",
            f"manualEvidenceStatus: {evidence_summary}",
            f"strictServerFlagsStatus: {strict_flags_summary}",
            f"Arquivos salvos: {evidence_files_summary}",
            f"Observacoes de auditoria: {checks_summary}",
            (
                "Decisao: manter PM-02 pendente ou marcar concluida apos "
                "revisoes."
            ),
        ]
    )
    return {
        "format": "markdown",
        "markdown": markdown,
    }


def _profile_mapping_summary(values):
    return (
        "; ".join(f"{key}={value}" for key, value in sorted(values.items()))
        or "-"
    )


def _profile_overrides_summary(overrides):
    if not overrides:
        return "-"
    return "; ".join(
        (
            f"{key}: default={value.get('profileDefault')}; "
            f"efetivo={value.get('effective')}"
        )
        for key, value in sorted(overrides.items())
    )


def _pm02_strict_server_command_resolved(
    server_evidence,
    environment_expectations=None,
    save_directory="",
    save_json="",
    save_record="",
    save_snapshot_json="",
    require_backup_file_exists=False,
    require_release_git_ref_exists=False,
    require_frontend_deploy_url_https=False,
    require_evidence_files=False,
):
    release_ref = server_evidence["releaseRef"] or "<tag-ou-commit-backend>"
    backup_ref = server_evidence["backupRef"] or "<arquivo-ou-id-backup>"
    parts = [
        "python manage.py validar_baseline_pm02",
        "--modo-servidor-estrito",
    ]
    if server_evidence.get("environmentProfile") == LEGACY_PRODUCTION_PROFILE_LABEL:
        parts.append("perfil-legado-desativado")
    if server_evidence["frontendRef"]:
        parts.append(f"--frontend-ref={server_evidence['frontendRef']}")
    elif server_evidence["frontendDeployUrl"]:
        parts.append(f"--frontend-deploy-url={server_evidence['frontendDeployUrl']}")
    else:
        parts.append("--frontend-ref=<commit-ou-deploy-vercel>")
    environment_label = (
        server_evidence.get("environmentLabel") or "<producao-ou-homologacao>"
    )
    parts.append(f"--ambiente={environment_label}")
    parts.extend(
        [
            f"--release-ref={release_ref}",
            f"--backup-ref={backup_ref}",
        ]
    )
    parts.extend(_environment_expectation_flags(environment_expectations or []))
    if require_frontend_deploy_url_https:
        parts.append("--exigir-frontend-deploy-url-https")
    if require_release_git_ref_exists:
        parts.append("--exigir-release-git-ref-existente")
    if require_backup_file_exists:
        parts.append("--exigir-backup-arquivo-existente")
    if save_directory:
        parts.append(f"--diretorio-evidencias={save_directory}")
    if save_json:
        parts.append(f"--salvar-json={save_json}")
    if save_record:
        parts.append(f"--salvar-registro={save_record}")
    if save_snapshot_json:
        parts.append(f"--salvar-snapshot-json={save_snapshot_json}")
    if require_evidence_files:
        parts.append("--exigir-arquivos-evidencia")
    parts.append("--json")
    return " ".join(parts)


def _environment_expectation_flags(environment_expectations):
    flag_by_key = {
        "sessionCookieDomain": "--esperar-session-cookie-domain",
        "csrfCookieDomain": "--esperar-csrf-cookie-domain",
        "sessionCookieSecure": "--esperar-session-cookie-secure",
        "csrfCookieSecure": "--esperar-csrf-cookie-secure",
        "sessionCookieSameSite": "--esperar-session-cookie-samesite",
        "csrfCookieSameSite": "--esperar-csrf-cookie-samesite",
        "cacheBackend": "--esperar-cache-backend",
        "cacheLocation": "--esperar-cache-location",
        "canonicalFirstEnabled": "--esperar-canonical-first-enabled",
        "canonicalFirstSources": "--esperar-canonical-first-sources",
        "databaseEngine": "--esperar-database-engine",
        "databaseName": "--esperar-database-name",
        "databaseHost": "--esperar-database-host",
        "databasePort": "--esperar-database-port",
        "allowedHosts": "--esperar-allowed-hosts",
        "csrfTrustedOrigins": "--esperar-csrf-trusted-origins",
        "corsAllowedOrigins": "--esperar-cors-allowed-origins",
    }
    return [
        f"{flag_by_key[expectation['key']]}={expectation['expected']}"
        for expectation in environment_expectations
        if expectation.get("expected") and expectation["key"] in flag_by_key
    ]


def _environment_expectation_summary(environment_expectations):
    expected_items = [
        (
            f"{expectation['label']} esperado={expectation['expected']}; "
            f"atual={expectation['actual'] or '-'}; "
            f"status={'ok' if expectation['ok'] else 'pendente'}"
        )
        for expectation in environment_expectations
        if expectation.get("expected")
    ]
    return "; ".join(expected_items) if expected_items else "nenhuma"


def _snapshot_tem_referencia_frontend(snapshot):
    frontend = snapshot["frontend"]
    return bool(
        frontend.get("declaredReference")
        or frontend.get("deployUrl")
        or frontend.get("git", {}).get("commitShort")
    )


def _executar_comando_django(key, label, command_name, *args):
    stdout = StringIO()
    try:
        call_command(command_name, *args, stdout=stdout)
    except CommandError as exc:
        return _check_result(
            key,
            label,
            False,
            output=stdout.getvalue(),
            issues=[str(exc)],
        )

    return _check_result(
        key,
        label,
        True,
        output=stdout.getvalue(),
    )


def _validar_preflight():
    resultado = validar_preflight_deploy_financeiro({})
    return _check_result(
        "financialPreflight",
        "Pre-flight financeiro",
        resultado["ready"],
        issues=resultado["issues"],
        detail={
            "ready": resultado["ready"],
            "businessDivergences": resultado["businessTotalsAudit"]["obligations"][
                "divergentCount"
            ],
            "ledgerConsistent": resultado["financialLedgerIntegrity"]["consistent"],
        },
    )


def _validar_operacao():
    resultado = validar_operacao_obrigacoes(
        {
            "validar_canonico": True,
            "validar_escrita_canonica": True,
            "validar_valores_editaveis": True,
        }
    )
    issues = [] if resultado["ready"] else ["validacao operacional com pendencias"]
    return _check_result(
        "operationalValidation",
        "Validacao operacional",
        resultado["ready"],
        issues=issues,
        detail={
            "ready": resultado["ready"],
            "contractConsistent": resultado["contract"]["consistent"],
            "reconciliationDivergences": resultado["reconciliation"][
                "divergentCount"
            ],
            "canonicalModelingChecked": resultado["canonicalModeling"]["checked"],
            "canonicalWriteReadinessChecked": resultado[
                "canonicalWriteReadiness"
            ]["checked"],
        },
    )


def _auditar_totais():
    resultado = auditar_totais_negocio(validar_valores_editaveis=True)
    obrigacoes = resultado["obligations"]
    valores_editaveis = resultado["editableValuesIntegrity"]
    ok = obrigacoes["divergentCount"] == 0 and valores_editaveis["consistent"]
    issues = []
    if obrigacoes["divergentCount"] > 0:
        issues.append("auditoria de totais com divergencias")
    if not valores_editaveis["consistent"]:
        issues.append("valores editaveis com efeitos derivados inconsistentes")

    return _check_result(
        "businessTotalsAudit",
        "Auditoria de totais",
        ok,
        issues=issues,
        detail={
            "obligationDivergences": obrigacoes["divergentCount"],
            "realizedAmountDifference": obrigacoes["realizedAmountDifference"],
            "editableValuesConsistent": valores_editaveis["consistent"],
        },
    )


def _check_result(key, label, ok, issues=None, output="", detail=None):
    return {
        "key": key,
        "label": label,
        "ok": bool(ok),
        "issues": issues or [],
        "output": output,
        "detail": detail or {},
    }


def formatar_erro_baseline_pm02(resultado):
    issues = resultado.get("issues") or []
    if issues:
        return f"Baseline PM-02 nao aprovada: {issues[0]}"
    return "Baseline PM-02 nao aprovada."


def formatar_erro_fechamento_pm02(resultado):
    blockers = resultado.get("pm02ClosureBlockers") or []
    if blockers:
        return f"PM-02 nao esta pronta para fechamento: {blockers[0]}"
    return "PM-02 nao esta pronta para fechamento."
