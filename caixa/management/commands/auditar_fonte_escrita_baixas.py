import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from caixa.serializers_modelagem_canonica import (
    montar_payload_baixas_financeiras_canonicas_api,
)
from caixa.models import FONTE_ESCRITA_BAIXA_CHOICES
from tenancy.command_guards import ensure_tenant_schema


FONTES_ESCRITA = tuple(valor for valor, _rotulo in FONTE_ESCRITA_BAIXA_CHOICES)


class Command(BaseCommand):
    help = (
        "Audita baixas canonicas por fonte de escrita. "
        "Use apos janelas canonical-first para conferir o que foi gerado."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-inicial",
            "--data-ativacao",
            dest="data_inicial",
            help=(
                "Inicio da janela de auditoria. Use a data em que a origem "
                "foi ativada em canonical-first."
            ),
        )
        parser.add_argument("--data-final", dest="data_final")
        parser.add_argument("--source")
        parser.add_argument(
            "--write-model-source",
            "--fonte-escrita",
            dest="write_model_source",
            choices=FONTES_ESCRITA,
            help="Filtra baixas por legacyAdapterSynced ou canonicalFirst.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime a auditoria em JSON para automacoes.",
        )
        parser.add_argument(
            "--salvar-json",
            "--save-json",
            default="",
            help="Salva o payload JSON da auditoria em um arquivo.",
        )
        parser.add_argument(
            "--salvar-registro",
            "--save-record",
            default="",
            help="Salva o registro markdown da auditoria em um arquivo.",
        )
        parser.add_argument(
            "--diretorio-evidencias",
            "--evidence-directory",
            default="",
            help=(
                "Diretorio opcional para gerar arquivos padronizados de "
                "evidencia da auditoria PM-03."
            ),
        )
        parser.add_argument(
            "--exigir-arquivos-evidencia",
            "--require-evidence-files",
            action="store_true",
            help=(
                "Reprova se os caminhos de evidencia PM-03 nao forem "
                "informados por --diretorio-evidencias ou caminhos explicitos."
            ),
        )
        parser.add_argument(
            "--exigir-canonical-first",
            action="store_true",
            help="Retorna erro quando nenhuma baixa canonical-first for encontrada.",
        )
        parser.add_argument(
            "--exigir-data-ativacao",
            action="store_true",
            help=(
                "Retorna erro quando a data inicial da janela canonical-first "
                "nao for informada."
            ),
        )

    def handle(self, *args, **options):
        ensure_tenant_schema("auditar_fonte_escrita_baixas", action="auditar dados operacionais")
        evidence_files = _normalizar_arquivos_evidencia(options)
        if options["exigir_arquivos_evidencia"]:
            _exigir_arquivos_evidencia(evidence_files)
        resultado = auditar_fonte_escrita_baixas(
            data_inicial=options.get("data_inicial"),
            data_final=options.get("data_final"),
            source=options.get("source"),
            write_model_source=options.get("write_model_source"),
            exigir_data_ativacao=options["exigir_data_ativacao"],
        )
        resultado["evidenceFiles"] = evidence_files
        resultado["executionRecord"] = {
            "format": "markdown",
            "markdown": _registro_auditoria_fonte_pm03(resultado),
        }
        _salvar_evidencias_auditoria(resultado)

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if options["exigir_data_ativacao"] and resultado["issues"]:
            raise CommandError("Data de ativacao da janela canonical-first nao informada.")
        if (
            options["exigir_canonical_first"]
            and resultado["canonicalFirst"]["count"] == 0
        ):
            raise CommandError(
                "Nenhuma baixa canonical-first encontrada: "
                f"{formatar_contexto_auditoria(resultado)}"
            )

    def _imprimir_relatorio(self, resultado):
        self.stdout.write("Auditoria de fonte de escrita das baixas concluida.")
        self.stdout.write(f"Gerado em: {resultado['generatedAt']}")
        self.stdout.write("Modo: somente leitura")
        if resultado["filters"].get("writeModelSource"):
            self.stdout.write(
                f"Fonte de escrita: {resultado['filters']['writeModelSource']}"
            )
        self.stdout.write(f"Total de baixas: {resultado['count']}")
        self.stdout.write(
            "Legacy adapter synced: "
            f"count={resultado['legacyAdapterSynced']['count']}; "
            f"valor={resultado['legacyAdapterSynced']['outflowAmount']:.2f}"
        )
        self.stdout.write(
            "Canonical-first: "
            f"count={resultado['canonicalFirst']['count']}; "
            f"valor={resultado['canonicalFirst']['outflowAmount']:.2f}"
        )
        for issue in resultado["issues"]:
            self.stdout.write(f"- {issue}")


def auditar_fonte_escrita_baixas(
    data_inicial=None,
    data_final=None,
    source=None,
    write_model_source=None,
    exigir_data_ativacao=False,
):
    payload = montar_payload_baixas_financeiras_canonicas_api(
        {
            "data_inicial": data_inicial or "",
            "data_final": data_final or "",
            "source": source or "",
            "writeModelSource": write_model_source or "",
            "limit": 1,
        }
    )["data"]
    resumo = payload["summary"]
    por_fonte = resumo.get("byWriteModelSource") or {}
    legacy = _grupo_fonte(por_fonte, "legacyAdapterSynced")
    canonical_first = _grupo_fonte(por_fonte, "canonicalFirst")
    issues = []

    if exigir_data_ativacao and not data_inicial:
        issues.append("Informe a data de ativacao da janela canonical-first.")

    return {
        "generatedAt": timezone.now().isoformat(),
        "readOnly": True,
        "filters": payload["filters"],
        "count": resumo["count"],
        "legacyAdapterSynced": legacy,
        "canonicalFirst": canonical_first,
        "byWriteModelSource": por_fonte,
        "requiresActivationDate": exigir_data_ativacao,
        "issues": issues,
    }


def _grupo_fonte(por_fonte, fonte):
    return {
        "count": int((por_fonte.get(fonte) or {}).get("count") or 0),
        "inflowAmount": float((por_fonte.get(fonte) or {}).get("inflowAmount") or 0),
        "outflowAmount": float((por_fonte.get(fonte) or {}).get("outflowAmount") or 0),
        "financialResult": float(
            (por_fonte.get(fonte) or {}).get("financialResult") or 0
        ),
        "allocatedAmount": float(
            (por_fonte.get(fonte) or {}).get("allocatedAmount") or 0
        ),
        "unallocatedAmount": float(
            (por_fonte.get(fonte) or {}).get("unallocatedAmount") or 0
        ),
    }


def formatar_contexto_auditoria(resultado):
    filtros = resultado.get("filters") or {}
    return (
        f"source={filtros.get('source') or '-'}; "
        f"writeModelSource={filtros.get('writeModelSource') or '-'}; "
        f"dataInicial={filtros.get('startDate') or filtros.get('data_inicial') or '-'}; "
        f"dataFinal={filtros.get('endDate') or filtros.get('data_final') or '-'}"
    )


def _normalizar_arquivos_evidencia(options):
    directory = options.get("diretorio_evidencias", "")
    save_json = options.get("salvar_json", "")
    save_record = options.get("salvar_registro", "")

    if directory:
        base_path = Path(directory).expanduser()
        if base_path.exists() and not base_path.is_dir():
            raise CommandError(
                "--diretorio-evidencias deve apontar para um diretorio"
            )
        if not save_json:
            save_json = str(base_path / "pm03-auditoria-fonte-escrita.json")
        if not save_record:
            save_record = str(base_path / "pm03-auditoria-fonte-escrita.md")

    return {
        "directory": directory,
        "json": save_json,
        "record": save_record,
    }


def _exigir_arquivos_evidencia(evidence_files):
    missing = [
        label
        for label, path in (
            ("json", evidence_files.get("json")),
            ("record", evidence_files.get("record")),
        )
        if not path
    ]
    if missing:
        raise CommandError(
            "arquivos de evidencia PM-03 incompletos: " + ", ".join(missing)
        )


def _salvar_evidencias_auditoria(resultado):
    evidence_files = resultado.get("evidenceFiles") or {}
    json_path = evidence_files.get("json")
    record_path = evidence_files.get("record")

    if json_path:
        _salvar_texto(
            json_path,
            json.dumps(resultado, ensure_ascii=False, sort_keys=True, indent=2),
        )
    if record_path:
        _salvar_texto(record_path, resultado["executionRecord"]["markdown"])


def _salvar_texto(path, content):
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _registro_auditoria_fonte_pm03(resultado):
    filtros = resultado.get("filters") or {}
    legacy = resultado["legacyAdapterSynced"]
    canonical_first = resultado["canonicalFirst"]
    issues = "; ".join(resultado["issues"]) if resultado["issues"] else "nenhuma"
    evidence_files = resultado.get("evidenceFiles") or {}
    evidence_summary = (
        f"diretorio={evidence_files.get('directory') or '-'}; "
        f"json={evidence_files.get('json') or '-'}; "
        f"registro={evidence_files.get('record') or '-'}"
    )

    return "\n".join(
        [
            "### Registro PM-03 - auditoria de fonte de escrita",
            "",
            f"Data/hora da auditoria: {resultado['generatedAt']}",
            f"Origem: {filtros.get('source') or '-'}",
            (
                "Periodo auditado: "
                f"{filtros.get('startDate') or filtros.get('data_inicial') or '-'} "
                f"a {filtros.get('endDate') or filtros.get('data_final') or '-'}"
            ),
            f"Filtro fonte de escrita: {filtros.get('writeModelSource') or '-'}",
            f"Total de baixas: {resultado['count']}",
            (
                "Canonical-first: "
                f"count={canonical_first['count']}; "
                f"valor={canonical_first['outflowAmount']:.2f}"
            ),
            (
                "Legacy adapter synced: "
                f"count={legacy['count']}; "
                f"valor={legacy['outflowAmount']:.2f}"
            ),
            f"requiresActivationDate: {resultado['requiresActivationDate']}",
            f"issues: {issues}",
            f"Arquivos salvos: {evidence_summary}",
        ]
    )
