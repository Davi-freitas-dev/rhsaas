import json

from django.core.management.base import BaseCommand, CommandError

from caixa.contracts_obrigacoes import (
    CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
    CANONICAL_SETTLEMENT_ADAPTERS,
    CANONICAL_WRITE_MODE_CANONICAL_FIRST,
    CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
    NATIVE_SETTLEMENT_CAPABILITIES,
    ORIGEM_CUSTO_EXTRA,
    ORIGEM_CUSTO_SERVICO,
    ORIGEM_PARCELA_DIVIDA,
    estado_ativacao_canonical_first,
)
from caixa.models import (
    ORIGEM_OBRIGACAO_CANONICA_POR_CAMPO,
    ORIGENS_BAIXA_FINANCEIRA,
)


class Command(BaseCommand):
    help = (
        "Verifica se as origens nativas de baixa estao prontas para a "
        "transicao de escrita canonica. O comando e somente leitura."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Imprime a validacao em JSON para automacoes.",
        )
        parser.add_argument(
            "--falhar-com-inconsistencia",
            action="store_true",
            help="Retorna erro quando houver inconsistencia.",
        )

    def handle(self, *args, **options):
        resultado = verificar_prontidao_escrita_canonica()

        if options["json_output"]:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False, sort_keys=True))
        else:
            self._imprimir_relatorio(resultado)

        if resultado["inconsistencies"] and options["falhar_com_inconsistencia"]:
            primeira_inconsistencia = resultado["inconsistencies"][0]
            raise CommandError(
                f"{len(resultado['inconsistencies'])} inconsistencia(s) de "
                "prontidao para escrita canonica: "
                f"{primeira_inconsistencia}"
            )

    def _imprimir_relatorio(self, resultado):
        if resultado["ready"]:
            self.stdout.write(
                self.style.SUCCESS("Prontidao de escrita canonica consistente.")
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(resultado['inconsistencies'])} inconsistencia(s) encontrada(s)."
                )
            )
            for inconsistencia in resultado["inconsistencies"]:
                self.stdout.write(f"- {inconsistencia}")

        self.stdout.write(f"Modo atual: {resultado['currentWriteMode']}")
        self.stdout.write(
            "Origens avaliadas: " + ", ".join(resultado["sources"] or ["-"])
        )
        self.stdout.write(
            "Canonical-first pronto: "
            + ("sim" if resultado["canonicalFirstReady"] else "nao")
        )
        self.stdout.write(
            "Feature flag canonical-first: "
            + ("ligada" if resultado["featureFlagEnabled"] else "desligada")
        )
        self.stdout.write(
            "Origens canonical-first habilitadas: "
            + ", ".join(resultado["enabledCanonicalFirstSources"] or ["-"])
        )
        self.stdout.write(
            "Origens adapter-only PM-04: "
            + ", ".join(resultado["adapterOnlySources"] or ["-"])
        )


def verificar_prontidao_escrita_canonica():
    inconsistencias = []
    adapters = {}
    ativacao_canonical_first = estado_ativacao_canonical_first()
    native_sources = set(NATIVE_SETTLEMENT_CAPABILITIES)
    adapter_sources = set(CANONICAL_SETTLEMENT_ADAPTERS)
    obligation_sources = set(ORIGEM_OBRIGACAO_CANONICA_POR_CAMPO.values())
    invalid_feature_sources = set(ativacao_canonical_first["invalidSources"])

    if native_sources != adapter_sources:
        inconsistencias.append(
            "CANONICAL_SETTLEMENT_ADAPTERS nao cobre exatamente as origens nativas."
        )
    if invalid_feature_sources:
        inconsistencias.append(
            "CANONICAL_FIRST_SETTLEMENT_SOURCES contem origem sem suporte direto: "
            + ", ".join(sorted(invalid_feature_sources))
        )

    for source in sorted(native_sources | adapter_sources):
        capacidade = NATIVE_SETTLEMENT_CAPABILITIES.get(source, {})
        adapter = CANONICAL_SETTLEMENT_ADAPTERS.get(source, {})
        issues = []

        if not adapter:
            issues.append("Adapter canonico ausente.")
        else:
            if adapter.get("mode") != CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED:
                issues.append("Modo de escrita transicional invalido.")
            if not adapter.get("legacyAdapter"):
                issues.append("Adapter legado nao informado.")
            if adapter.get("canonicalObligationSource") not in obligation_sources:
                issues.append("Origem de obrigacao canonica invalida.")
            if adapter.get("canonicalSettlementOriginField") not in ORIGENS_BAIXA_FINANCEIRA:
                issues.append("Campo de origem da baixa canonica invalido.")
            if bool(adapter.get("requiresSourceDetail")) != bool(
                capacidade.get("requiresSourceDetail")
            ):
                issues.append("Exigencia de sourceDetail diverge do contrato de baixa.")

        for issue in issues:
            inconsistencias.append(f"{source}: {issue}")

        adapters[source] = {
            "ready": not issues,
            "issues": issues,
            "supportsCanonicalFirstWrite": source
            in CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES,
            "supportedObligationTypes": list(
                capacidade.get("supportedObligationTypes") or []
            ),
            **adapter,
        }

    canonical_first_ready = all(
        adapter.get("canonicalFirstReady") for adapter in adapters.values()
    )
    adapter_only_sources = sorted(
        source
        for source, adapter in adapters.items()
        if not adapter.get("supportsCanonicalFirstWrite")
    )

    return {
        "ready": not inconsistencias,
        "canonicalFirstReady": canonical_first_ready,
        "featureFlagEnabled": ativacao_canonical_first["featureFlagEnabled"],
        "featureFlagSources": ativacao_canonical_first["featureFlagSources"],
        "enabledCanonicalFirstSources": ativacao_canonical_first["enabledSources"],
        "invalidFeatureFlagSources": ativacao_canonical_first["invalidSources"],
        "currentWriteMode": CANONICAL_WRITE_MODE_LEGACY_ADAPTER_SYNCED,
        "targetWriteMode": CANONICAL_WRITE_MODE_CANONICAL_FIRST,
        "directCanonicalFirstSources": sorted(CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES),
        "adapterOnlySources": adapter_only_sources,
        "pm04DecisionMatrix": montar_matriz_decisao_pm04(adapters),
        "sources": sorted(native_sources),
        "adapters": adapters,
        "inconsistencies": inconsistencias,
    }


PM04_ADAPTER_ONLY_RECOMMENDATIONS = {
    ORIGEM_CUSTO_EXTRA: (
        "Decidir se a baixa canonica direta deve apontar para o custo extra "
        "ou manter PagamentoEventoCustoExtra como origem operacional durante "
        "a transicao."
    ),
    ORIGEM_CUSTO_SERVICO: (
        "Preservar sourceDetail por componente antes de qualquer promocao: "
        "diarias, alimentacao e transporte continuam tendo saldos e baixas "
        "parciais proprias."
    ),
    ORIGEM_PARCELA_DIVIDA: (
        "Preservar juros, multa, desconto, forma de pagamento e a regra FCF "
        "de emprestimo/financiamento antes de promover a baixa direta."
    ),
}


def montar_matriz_decisao_pm04(adapters):
    items = []
    for source, adapter in sorted(adapters.items()):
        supports_direct_write = adapter.get("supportsCanonicalFirstWrite") is True
        items.append(
            {
                "source": source,
                "recommendedPhase": "PM-03" if supports_direct_write else "PM-04",
                "decisionRequired": not supports_direct_write,
                "supportsCanonicalFirstWrite": supports_direct_write,
                "requiresSourceDetail": adapter.get("requiresSourceDetail") is True,
                "supportsAdjustments": bool(
                    NATIVE_SETTLEMENT_CAPABILITIES.get(source, {}).get(
                        "supportsAdjustments"
                    )
                ),
                "legacyAdapter": adapter.get("legacyAdapter") or "",
                "canonicalSettlementOriginField": (
                    adapter.get("canonicalSettlementOriginField") or ""
                ),
                "recommendation": PM04_ADAPTER_ONLY_RECOMMENDATIONS.get(
                    source,
                    "Promover por PM-03 somente com canario, allowlist e auditoria.",
                ),
            }
        )
    return {
        "phase": "PM-04",
        "adapterOnlySources": [
            item["source"] for item in items if item["decisionRequired"]
        ],
        "directSources": [
            item["source"] for item in items if not item["decisionRequired"]
        ],
        "items": items,
    }
