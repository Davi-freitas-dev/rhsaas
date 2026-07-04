import json

from django.core.management.base import BaseCommand, CommandError

from caixa.contracts_obrigacoes import (
    CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
    CANONICAL_SETTLEMENT_ADAPTERS,
    NATIVE_SETTLEMENT_CAPABILITIES,
    PERMISSOES_BAIXA_NATIVA,
    READ_ONLY_SETTLEMENT_SOURCES,
    SETTLEMENT_CONTRACT_VERSION,
    SUPPORTED_NATIVE_SETTLEMENT_SOURCES,
    serializar_contrato_baixa_obrigacoes,
)
from caixa.selectors_obrigacoes import FONTES_OBRIGACOES


class Command(BaseCommand):
    help = (
        "Verifica a coerencia do contrato de baixa nativa de obrigacoes. "
        "O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime o contrato e a validacao em JSON para automacoes.",
        )
        parser.add_argument(
            "--falhar-com-inconsistencia",
            action="store_true",
            help="Retorna erro quando o contrato estiver inconsistente.",
        )

    def handle(self, *args, **options):
        resultado = validar_contrato_baixa_obrigacoes()

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if resultado["inconsistencies"] and options["falhar_com_inconsistencia"]:
            raise CommandError(
                f"{len(resultado['inconsistencies'])} inconsistencia(s) "
                "no contrato de baixa: "
                f"{formatar_primeira_inconsistencia(resultado)}"
            )

    def _imprimir_relatorio(self, resultado):
        if not resultado["inconsistencies"]:
            self.stdout.write(
                self.style.SUCCESS("Contrato de baixa de obrigacoes consistente.")
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(resultado['inconsistencies'])} inconsistencia(s) encontrada(s)."
                )
            )
            for inconsistencia in resultado["inconsistencies"]:
                self.stdout.write(f"- {inconsistencia}")

        self.stdout.write(f"Versao: {resultado['version']}")
        self.stdout.write(
            "Origens nativas: " + ", ".join(resultado["nativeSources"] or ["-"])
        )
        self.stdout.write(
            "Origens somente leitura: " + ", ".join(resultado["readOnlySources"] or ["-"])
        )


def validar_contrato_baixa_obrigacoes():
    contrato = serializar_contrato_baixa_obrigacoes()
    inconsistencias = []
    native_sources = set(contrato["nativeSources"])
    read_only_sources = set(contrato["readOnlySources"])
    all_sources = set(contrato["sources"])
    expected_native_sources = set(NATIVE_SETTLEMENT_CAPABILITIES)
    canonical_settlement = contrato.get("canonicalSettlement", {})
    canonical_adapters = canonical_settlement.get("adapters", {})

    if contrato["version"] != SETTLEMENT_CONTRACT_VERSION:
        inconsistencias.append("Versao serializada diverge da constante do contrato.")

    if native_sources != expected_native_sources:
        inconsistencias.append("nativeSources diverge de NATIVE_SETTLEMENT_CAPABILITIES.")

    if set(SUPPORTED_NATIVE_SETTLEMENT_SOURCES) != expected_native_sources:
        inconsistencias.append(
            "SUPPORTED_NATIVE_SETTLEMENT_SOURCES diverge de NATIVE_SETTLEMENT_CAPABILITIES."
        )

    if set(PERMISSOES_BAIXA_NATIVA) != expected_native_sources:
        inconsistencias.append("PERMISSOES_BAIXA_NATIVA nao cobre todas as origens nativas.")

    if read_only_sources != set(READ_ONLY_SETTLEMENT_SOURCES):
        inconsistencias.append("readOnlySources diverge de READ_ONLY_SETTLEMENT_SOURCES.")

    if canonical_settlement.get("settlementModel") != "BaixaFinanceira":
        inconsistencias.append("canonicalSettlement nao aponta para BaixaFinanceira.")

    if canonical_settlement.get("allocationModel") != "BaixaFinanceiraAlocacao":
        inconsistencias.append("canonicalSettlement nao aponta para BaixaFinanceiraAlocacao.")

    if native_sources & read_only_sources:
        inconsistencias.append("Origem aparece ao mesmo tempo como nativa e somente leitura.")

    if all_sources != native_sources | read_only_sources:
        inconsistencias.append("sources nao corresponde a uniao de nativeSources e readOnlySources.")

    if set(canonical_adapters) != set(CANONICAL_SETTLEMENT_ADAPTERS):
        inconsistencias.append("canonicalSettlement.adapters diverge dos adapters canonicos.")

    for source in native_sources:
        capacidade = contrato["sources"].get(source, {})
        adapter = canonical_adapters.get(source, {})
        permissao = PERMISSOES_BAIXA_NATIVA.get(source)
        if not permissao:
            inconsistencias.append(f"Origem {source} nao possui permissao de baixa.")
        if not capacidade.get("nativeSettlement"):
            inconsistencias.append(f"Origem {source} nativa sem nativeSettlement=true.")
        if capacidade.get("source") != source:
            inconsistencias.append(f"Origem {source} serializada com source divergente.")
        if source not in FONTES_OBRIGACOES:
            inconsistencias.append(f"Origem {source} nao possui label em FONTES_OBRIGACOES.")
        if "realizedAmount" not in capacidade.get("acceptedFields", []):
            inconsistencias.append(f"Origem {source} sem realizedAmount em acceptedFields.")
        if capacidade.get("requiresSourceDetail") and not capacidade.get("acceptedSourceDetails"):
            inconsistencias.append(f"Origem {source} exige sourceDetail sem valores aceitos.")
        if capacidade.get("supportsAdjustments") and not capacidade.get("adjustmentFields"):
            inconsistencias.append(f"Origem {source} suporta ajustes sem adjustmentFields.")
        if adapter:
            if adapter.get("supportedObligationTypes") != capacidade.get(
                "supportedObligationTypes"
            ):
                inconsistencias.append(
                    f"Origem {source} com tipos liquidaveis divergentes no adapter."
                )
            if bool(adapter.get("supportsCanonicalFirstWrite")) != (
                source in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES
            ):
                inconsistencias.append(
                    f"Origem {source} com suporte canonical-first divergente no adapter."
                )

    for source in read_only_sources:
        capacidade = contrato["sources"].get(source, {})
        if capacidade.get("nativeSettlement"):
            inconsistencias.append(f"Origem somente leitura {source} marcada como nativa.")
        if capacidade.get("acceptedFields"):
            inconsistencias.append(f"Origem somente leitura {source} possui acceptedFields.")

    return {
        "version": contrato["version"],
        "consistent": not inconsistencias,
        "inconsistencies": inconsistencias,
        "canonicalSettlement": canonical_settlement,
        "nativeSources": contrato["nativeSources"],
        "readOnlySources": contrato["readOnlySources"],
        "sources": contrato["sources"],
    }


def formatar_primeira_inconsistencia(resultado):
    inconsistencias = resultado.get("inconsistencies") or []
    return inconsistencias[0] if inconsistencias else "consulte o relatorio detalhado."
