# Plano PM-31 - Migracao incremental de `POST /api/obrigacoes-financeiras/liquidar/` e `POST /api/payment-obligations/settle/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar de forma incremental e controlada os endpoints de liquidacao de
obrigacoes financeiras para Django REST Framework, preservando integralmente o
contrato atual consumido pelo frontend Next.js.

Endpoints no escopo:

- `POST /api/obrigacoes-financeiras/liquidar/`
- `POST /api/payment-obligations/settle/`

DRF deve entrar apenas como casca HTTP da view de liquidacao, sem alterar regra
de negocio, services, selectors, serializers manuais, contracts, permissoes,
CSRF, CORS, headers, status HTTP, aliases, transacoes, efeitos colaterais ou
contrato do frontend.

## Escopo

- Congelar o contrato atual de liquidacao em testes antes da migracao.
- Migrar somente a view `api_liquidar_obrigacao_financeira`.
- Preservar as duas rotas existentes apontando para a mesma view.
- Manter URLs e nomes de rota atuais.
- Usar `@api_view(["POST"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_POST` por fora, ou mecanismo equivalente, para manter o
  `405` Django padrao.
- Preservar CSRF real no `POST`.
- Preservar autenticacao manual com `401` atual.
- Preservar permissao por `source`, sem exigir permissao ampla.
- Preservar `Content-Type`/JSON/body nao-dict como `400` atual.
- Preservar aliases atuais de payload.
- Preservar transacoes atuais.
- Preservar efeitos colaterais atuais.
- Reaproveitar services, contracts, selectors, serializers manuais e helpers
  atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Listagem de obrigacoes.
- Exportacao de obrigacoes.
- Baixas financeiras canonicas.
- Dashboard financeiro.
- Mes financeiro.
- Lancamentos financeiros.
- Modelagem financeira canonica.
- Custos por evento.
- Outros endpoints financeiros.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Serializers DRF.
- ViewSets.
- ModelViewSets.
- Refatoracao de regra de negocio.
- Alteracao de services.
- Alteracao de selectors.
- Alteracao de serializers manuais.
- Alteracao de contracts.
- Alteracao de models.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, as duas rotas podem ser tratadas juntas porque apontam para a mesma
view `api_liquidar_obrigacao_financeira`.

Como este endpoint e uma mutation financeira sensivel, a PM deve manter a regra
de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, CORS, aliases,
transacoes, efeitos colaterais ou comportamento runtime apenas para melhorar a
documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-31.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_obrigacoes.py`.
- `caixa/services_obrigacoes.py`.
- `caixa/contracts_obrigacoes.py`.
- `caixa/services_escrita_canonica.py`.
- `caixa/serializers_obrigacoes.py`.
- `caixa/permissions.py`.
- `caixa/tests.py`.

View atual:

- `api_liquidar_obrigacao_financeira`.

Rotas atuais:

- `path("api/obrigacoes-financeiras/liquidar/", api_liquidar_obrigacao_financeira, name="api_liquidar_obrigacao_financeira")`.
- `path("api/payment-obligations/settle/", api_liquidar_obrigacao_financeira, name="api_settle_payment_obligation")`.

Nomes de rota:

- `caixa:api_liquidar_obrigacao_financeira`.
- `caixa:api_settle_payment_obligation`.

As duas rotas apontam para a mesma view.

Decorador atual:

- `@require_POST`.

Metodo aceito:

- `POST`.

Metodos nao permitidos:

- `GET`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` observado: `POST`.
- Body observado: vazio.
- `Content-Type` observado: `text/html; charset=utf-8`.
- `Cache-Control` observado: ausente.
- A resposta de `405` Django padrao deve ser preservada.
- Como `@require_POST` esta fora da view, o `405` ocorre antes de
  autenticacao, permissao e parsing.

CSRF atual:

- A view nao e `csrf_exempt`.
- Com `Client(enforce_csrf_checks=True)`, `POST` sem token valido bloqueia antes
  da view com `403` HTML.
- Com CSRF valido, a requisicao chega na view.
- A migracao nao pode alterar CSRF global nem relaxar CSRF.

Comportamento para usuario anonimo quando chega na view:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado sem permissao da origem:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

`Content-Type` aceito:

- `application/json`.
- `application/json; charset=utf-8` deve continuar aceito pela regra atual.

`Content-Type` invalido:

- Retorna `400`, nao `415`.

JSON invalido:

- Retorna `400`.

Body JSON nao-dict:

- Retorna `400`.

Contrato comum para `Content-Type` invalido, JSON invalido ou body nao-dict:

```json
{"detail": "JSON inválido ou Content-Type incorreto."}
```

com status `400`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Payload base aceito:

- `source`.
- `sourceId`.
- `realizedAmount`.
- `paymentDate`.
- `notes`.
- `settleRemainingBalance`.
- `writeOffReason`.

Aliases de valor realizado/pago:

- `realizedAmount`.
- `valorRealizado`.
- `valor_realizado`.
- `paidAmount`.
- `valor_pago`.
- Para FCI/FCF tambem existem campos especificos:
  - `valor_realizado_fci`;
  - `valor_realizado_fcf`.

Aliases de data de pagamento/realizacao:

- `paymentDate`.
- `dataPagamento`.
- `data_pagamento`.
- Para FCI/FCF tambem:
  - `realizationDate`;
  - `dataRealizacao`;
  - `data_realizacao`.

Aliases de observacao:

- `notes`.
- `observacao`.

Aliases de baixa de saldo restante:

- `settleRemainingBalance`.
- `baixarSaldo`.
- `baixar_saldo`.

Aliases de motivo de baixa:

- `writeOffReason`.
- `motivoBaixa`.
- `motivo_baixa`.

Aliases de forma de pagamento:

- `paymentMethod`.
- `formaPagamento`.
- `forma_pagamento`.

Aliases de descricao de pagamento:

- `paymentDescription`.
- `descricaoPagamento`.
- `descricao_pagamento`.

Aliases de detalhe de custo de servico:

- `sourceDetail`.
- `source_detail`.
- `originDetail`.
- `tipo`.
- `tipoCustoServico`.
- `tipo_custo_servico`.
- `component`.
- `componente`.

Aliases de juros/multa/desconto de parcela FCF:

- Juros:
  - `interestAmount`;
  - `valorJuros`;
  - `valor_juros`;
  - `juros`.
- Multa:
  - `fineAmount`;
  - `valorMulta`;
  - `valor_multa`;
  - `multa`.
- Desconto:
  - `discountAmount`;
  - `valorDesconto`;
  - `valor_desconto`;
  - `desconto`.

Permissoes atuais por `source`:

- `despesa_operacional`: `caixa.change_despesaoperacional`.
- `custo_fixo`: `caixa.change_custofixo`.
- `custo_extra`: `caixa.add_pagamentoeventocustoextra`.
- `custo_servico`: `caixa.add_pagamentoeventocustoservico`.
- `parcela_divida`: `caixa.add_pagamentoparceladivida`.
- `investimento`: `caixa.change_investimento`.
- `financiamento_movimentacao`: `caixa.change_financiamentomovimentacao`.

Regra importante de permissao:

- A view nao exige `caixa.view_lancamentofinanceiro` para liquidar.
- A permissao de liquidacao e resolvida por `source`.
- A migracao nao deve promover `caixa.view_lancamentofinanceiro` para requisito
  obrigatorio.

Sources com baixa nativa suportada:

- `despesa_operacional`.
- `custo_fixo`.
- `custo_extra`.
- `custo_servico`.
- `parcela_divida`.
- `investimento`.
- `financiamento_movimentacao`.

Source sem baixa nativa:

- Retorna `400` com `{"errors": ...}`.

Validacoes principais:

- `source` precisa estar entre as origens suportadas.
- Usuario precisa ter permissao da origem.
- `sourceId` precisa apontar para registro existente.
- `realizedAmount` e obrigatorio.
- `realizedAmount` nao pode ser negativo.
- `realizedAmount` acumulado nao pode ser menor que valor ja registrado.
- `realizedAmount` acumulado nao pode superar o previsto.
- Quando ha novo valor realizado positivo, `paymentDate` e obrigatorio.
- `settleRemainingBalance=True` exige `writeOffReason` quando ha saldo a baixar.
- Custo de servico exige `sourceDetail`.
- `sourceDetail` de custo de servico precisa ser valido.
- Parcela FCF valida juros/multa/desconto e rejeita desconto maior que o devido.
- Financiamento FCF nao suporta `settleRemainingBalance`.
- Registros cancelados ou ja baixados/pagos podem ser rejeitados conforme regra
  atual da origem.

Shape de sucesso:

```json
{
  "data": {
    "item": {},
    "canonicalSettlement": {},
    "settlement": {},
    "message": "Obrigação financeira atualizada com sucesso."
  }
}
```

Status de sucesso:

- `200`.

Headers de sucesso:

- `Content-Type: application/json`.
- `Cache-Control` com `no-store`.

Regra de igualdade:

- `settlement` deve continuar igual a `canonicalSettlement`.

Shape de `data.item`:

- `id`.
- `obligationType`, `tipoObrigacao`, `tipo_obrigacao`.
- `source`, `origin`, `origem`.
- `sourceId`, `originId`.
- `sourceLabel`.
- `sourceDetail`.
- `sourceDetailLabel`.
- `description`, `obligationDescription`, `descricao`.
- `reference`, `referencia`.
- `dueDate`, `date`, `data`, `data_vencimento`.
- `paymentDate`, `data_pagamento`.
- `plannedAmount`, `valor_previsto`.
- `realizedAmount`, `paidAmount`, `valor_realizado`, `valor_pago`.
- `overRealizedAmount`, `realizedAbovePlannedAmount`,
  `excedenteRealizado`, `valor_excedente_realizado`.
- `realizedAmountSource`.
- `originRealizedAmount`.
- `originPendingAmount`.
- `originOverRealizedAmount`.
- `ledgerRealizedAmount`.
- `ledgerPendingAmount`.
- `ledgerOverRealizedAmount`.
- `ledgerSettlementStatus`.
- `ledgerSettlementStatusLabel`.
- `ledgerIsOverdue`.
- `ledgerDaysOverdue`.
- `ledgerEntryCount`.
- `realizedAmountDifference`.
- `isLedgerReconciled`.
- `reconciliationStatus`.
- `reconciliationDiagnosis`.
- `reconciliationDiagnosisLabel`.
- `diagnosticoConciliacao`.
- `diagnosticoConciliacaoLabel`.
- `reconciliationGuidance`.
- `orientacaoConciliacao`.
- `valor_realizado_origem`.
- `valor_pendente_origem`.
- `valor_excedente_origem`.
- `valor_realizado_ledger`.
- `valor_pendente_ledger`.
- `valor_excedente_ledger`.
- `diferenca_realizado_ledger`.
- `conciliado_ledger`.
- `pendingAmount`.
- `pendingPaymentAmount`.
- `pendingReceivableAmount`.
- `pendingValue`.
- `valor_pendente_pagamento`.
- `contas_pendentes`.
- `cashFlowGroup`, `fluxo`.
- `nature`, `natureza`.
- `status`.
- `statusLabel`.
- `status_display`.
- `settlementStatus`.
- `settlementStatusLabel`.
- `isOverdue`.
- `daysOverdue`.
- `clientId`.
- `clientName`.
- `contractCode`.
- `contractName`.
- `contractLabel`.
- `contract`.
- `contrato_codigo`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `eventLabel`.
- `evento_id`.
- `evento_nome`.
- `evento_numero`.
- `evento_label`.
- `actionHints`.
- `readModelSource`.
- `dataSource`.

Shape de `data.canonicalSettlement` e `data.settlement` quando ha obrigacao
canonica:

- `available`.
- `synced`.
- `writeModelSource`.
- `obligationKey`.
- `obligationId`.
- `settlementModel`.
- `allocationModel`.
- `settlementCount`.
- `allocationCount`.
- `allocatedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `latestSettlement`.
- `reason`.

Shape de `latestSettlement`:

- `id`.
- `key`.
- `amount`.
- `settlementAmount`.
- `date`.
- `settlementDate`.
- `type`.
- `cashFlowGroup`.
- `nature`.
- `description`.
- `settlementDescription`.
- `status`.
- `writeModelSource`.
- `ledgerEntryId`.

Shape quando a obrigacao canonica nao existe:

- `available: false`.
- `synced: false`.
- `writeModelSource`.
- `obligationKey`.
- `obligationId: null`.
- `settlementCount: 0`.
- `allocationCount: 0`.
- `allocatedAmount: 0.0`.
- `latestSettlement: null`.
- `reason: "canonical_obligation_missing"`.

Shape de erros de validacao de dominio:

```json
{"errors": {...}}
```

Status:

- `400`.

Headers:

- `Content-Type: application/json`.
- `Cache-Control` com `no-store`.

Services principais:

- `liquidar_obrigacao_financeira_com_contexto_canonico`.
- `liquidar_obrigacao_financeira`.
- `validar_permissao_baixa_nativa`.
- `liquidar_despesa_operacional_manual`.
- `liquidar_custo_fixo`.
- `liquidar_custo_extra_evento`.
- `liquidar_custo_servico_evento`.
- `liquidar_parcela_divida_fcf`.
- `liquidar_investimento_fci`.
- `liquidar_financiamento_fcf`.
- `serializar_contexto_baixa_canonica`.
- `serializar_obrigacao_por_origem`.
- `serializar_obrigacao_financeira`.

Contracts principais:

- `SETTLEMENT_CONTRACT_VERSION`.
- `NATIVE_SETTLEMENT_CAPABILITIES`.
- `PERMISSOES_BAIXA_NATIVA`.
- `CANONICAL_SETTLEMENT_ADAPTERS`.
- `CANONICAL_FIRST_DIRECT_SETTLEMENT_SOURCES`.

Transacoes:

- Fluxos por origem usam `transaction.atomic()`.
- O caminho `canonical-first` tambem usa `transaction.atomic()`.

Feature flags relacionadas:

- `CANONICAL_FIRST_SETTLEMENT_ENABLED`.
- `CANONICAL_FIRST_SETTLEMENT_SOURCES`.

Efeitos colaterais por origem:

- `despesa_operacional`:
  - atualiza `valor_pago`, `data_pagamento`, `forma_pagamento`, `observacao`,
    status e baixa manual;
  - sincroniza `LancamentoFinanceiro`;
  - sincroniza contexto de baixa canonica.
- `custo_fixo`:
  - atualiza `valor_pago`, `data_pagamento`, `observacao`, status e baixa
    manual;
  - sincroniza `LancamentoFinanceiro`;
  - sincroniza contexto de baixa canonica.
- `custo_extra`:
  - cria pagamento dedicado quando ha delta positivo;
  - atualiza custo extra;
  - sincroniza despesa operacional vinculada;
  - sincroniza `LancamentoFinanceiro`;
  - pode baixar saldo restante;
  - sincroniza contexto de baixa canonica.
- `custo_servico`:
  - exige `sourceDetail`;
  - cria pagamento dedicado por tipo quando ha delta positivo;
  - atualiza componente do custo de servico;
  - sincroniza despesa operacional vinculada;
  - sincroniza `LancamentoFinanceiro`;
  - pode baixar saldo restante;
  - sincroniza contexto de baixa canonica.
- `parcela_divida`:
  - cria pagamento dedicado quando ha delta positivo;
  - aplica forma de pagamento e observacao;
  - pode aplicar juros, multa e desconto;
  - pode baixar saldo restante;
  - atualiza parcela e status da divida;
  - sincroniza `LancamentoFinanceiro`;
  - sincroniza contexto de baixa canonica.
- `investimento`:
  - atualiza valor realizado, data de realizacao, observacao, status e baixa
    manual;
  - sincroniza `LancamentoFinanceiro`;
  - pode usar caminho `canonical-first`;
  - sincroniza contexto de baixa canonica.
- `financiamento_movimentacao`:
  - atualiza valor realizado, data de realizacao, observacao e status;
  - sincroniza `LancamentoFinanceiro`;
  - rejeita baixa de saldo restante;
  - pode usar caminho `canonical-first`;
  - sincroniza contexto de baixa canonica.

Testes existentes identificados:

- `FiltrosHtmlTests.test_api_liquidar_obrigacao_manual_define_realizado_total_idempotente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_manual_pode_usar_canonical_first_flag`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_extra_cria_pagamento_dedicado_idempotente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_extra_baixa_saldo_restante`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_extra_exige_permissao_de_pagamento`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_nao_autenticada_retorna_json_401`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_json_invalido_retorna_no_store`.
- `FiltrosHtmlTests.test_api_settle_payment_obligation_alias_json_invalido_retorna_no_store`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_servico_cria_pagamento_por_tipo_idempotente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_servico_baixa_saldo_restante`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_servico_exige_tipo_do_componente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_parcela_fcf_cria_pagamento_dedicado_idempotente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_parcela_fcf_baixa_saldo_restante`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_parcela_fcf_ajusta_juros_multa_desconto`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_fixo_define_realizado_total_idempotente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_fixo_pode_usar_canonical_first_flag`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_custo_fixo_baixa_saldo_restante`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_investimento_fci_define_realizado_idempotente_com_baixa`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_investimento_fci_pode_usar_canonical_first_flag`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_financiamento_fcf_define_realizado_idempotente`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_financiamento_fcf_pode_usar_canonical_first_flag`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_financiamento_fcf_rejeita_baixa_de_saldo`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_rejeita_origem_sem_baixa_nativa`.
- `FiltrosHtmlTests.test_api_liquidar_obrigacao_manual_nao_reduz_valor_realizado`.

Lacunas identificadas para PM-31.2:

- CSRF real com `Client(enforce_csrf_checks=True)`.
- `405` nas duas URLs, com body vazio, `Allow: POST`, HTML e sem
  `Cache-Control`.
- Igualdade funcional entre rota PT-BR e rota EN em sucesso.
- Sucesso minimo na rota EN.
- `Content-Type` invalido retornando `400`, nao `415`.
- Body JSON nao-dict retornando o mesmo erro atual.
- Shape completo de `data`, `item`, `canonicalSettlement`, `settlement` e
  `message`.
- Confirmacao explicita de `settlement == canonicalSettlement`.
- Confirmacao de que `caixa.view_lancamentofinanceiro` nao vira requisito
  obrigatorio.
- Cobertura explicita dos aliases principais.
- Garantia explicita de nao duplicar baixa, pagamento, alocacao ou lancamento
  nos fluxos sensiveis.

## Riscos especificos da liquidacao de obrigacoes

- Endpoint de mutation financeira sensivel.
- Pode alterar caixa, saldos, status, pagamentos, baixas, alocacoes e
  lancamentos financeiros.
- Uma mudanca pequena em parsing, permissao ou CSRF pode expor baixa indevida.
- DRF pode substituir erros manuais por erros padrao.
- DRF pode transformar `400` atual de `Content-Type` invalido em `415`.
- DRF pode transformar `405` Django vazio em JSON padrao.
- DRF pode aplicar permissao global `IsAuthenticated` antes da regra manual.
- DRF pode parsear body antes da logica atual e alterar mensagens/status.
- Exigir `caixa.view_lancamentofinanceiro` seria quebra funcional.
- `canonical-first` depende de flags e precisa manter comportamento atual.
- Idempotencia por delta de pagamento nao pode ser quebrada.
- Nao duplicar `BaixaFinanceira`, `BaixaFinanceiraAlocacao`,
  `LancamentoFinanceiro` ou pagamentos dedicados.
- OpenAPI tende a exigir schema mais formal, mas runtime tem prioridade.

## Guardrails

- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao alterar models.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar contracts.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Nao mexer em listagem de obrigacoes.
- Nao mexer em exportacao de obrigacoes.
- Nao mexer em baixas financeiras canonicas.
- Nao mexer em dashboard financeiro.
- Nao mexer em outros endpoints financeiros.
- Reaproveitar `liquidar_obrigacao_financeira_com_contexto_canonico`.
- Reaproveitar `_payload_json`.
- Reaproveitar `_erro_validacao_payload`.
- Reaproveitar `api_authentication_required_response`.
- Reaproveitar `api_permission_denied_response`.
- Reaproveitar `api_no_store_json_response`.
- Preservar `@require_POST` por fora da view DRF, ou mecanismo equivalente, para
  manter `405` Django padrao.
- Usar permissao local `AllowAny` se necessario para impedir que a permissao
  global do DRF substitua os `401`/`403` manuais.
- Se for necessario evitar parsing automatico do DRF, fazer isso localmente na
  view, sem alterar `REST_FRAMEWORK` global.
- Priorizar paridade runtime sobre OpenAPI.
- Se algum comportamento atual parecer estranho, congelar como esta antes de
  migrar.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `POST` anonimo preserva `401` JSON/no-store nas duas URLs quando chega na
  view.
- `POST` sem permissao da origem preserva `403` JSON/no-store.
- CSRF real preservado.
- `POST` com CSRF valido chega na view.
- `GET`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual nas duas URLs.
- `Content-Type` invalido preserva `400`, nao vira `415`.
- JSON invalido preserva `400`.
- Body JSON nao-dict preserva `400`.
- Erro de `Content-Type`/JSON/body nao-dict preserva
  `{"detail": "JSON inválido ou Content-Type incorreto."}`.
- Rota PT-BR e rota EN permanecem funcionalmente equivalentes.
- Sucesso minimo funciona nas duas URLs.
- Shape completo de `data` preservado.
- Shape completo de `item`, `canonicalSettlement`, `settlement` e `message`
  preservado.
- `settlement == canonicalSettlement` preservado.
- Permissoes por `source` preservadas.
- `caixa.view_lancamentofinanceiro` nao vira requisito obrigatorio.
- Aliases de payload preservados.
- `settleRemainingBalance` preservado.
- Juros/multa/desconto de parcela FCF preservados.
- Caminho `canonical-first` preservado quando flags estiverem habilitadas.
- Nenhuma baixa duplicada.
- Nenhum pagamento duplicado.
- Nenhuma alocacao duplicada.
- Nenhum lancamento duplicado.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora de `api_liquidar_obrigacao_financeira` e alterado.

## Criterios de bloqueio

Parar imediatamente se:

- `405` mudar para JSON DRF padrao.
- `Content-Type` invalido mudar de `400` para `415`.
- JSON invalido mudar de payload/status.
- Body nao-dict mudar de payload/status.
- CSRF mudar.
- `401` ou `403` mudarem.
- Permissao por `source` mudar.
- `caixa.view_lancamentofinanceiro` passar a ser exigido.
- Rota PT-BR e rota EN divergirem.
- `settlement` divergir de `canonicalSettlement`.
- Shape de `data.item` mudar.
- Shape de `canonicalSettlement` mudar.
- Algum alias deixar de funcionar.
- `settleRemainingBalance` mudar.
- Juros/multa/desconto de parcela FCF mudarem.
- Caminho `canonical-first` mudar.
- Baixa, pagamento, alocacao ou lancamento forem duplicados.
- Algum saldo, status, realizado ou pendente mudar sem decisao explicita.
- For necessario alterar services.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario alterar contracts.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar listagem, exportacao, baixas, dashboard ou outros
  endpoints financeiros junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_liquidar_obrigacao_financeira`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em listagem, exportacao, baixas, dashboard ou outros endpoints
  financeiros.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar contracts.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco em codigo, mas o endpoint em si continua de alto risco de negocio
por ser mutation financeira.

## Fases

### PM-31.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como mutation financeira sensivel.
- Decisao: migrar sozinho, sem agrupar com listagem, exportacao, baixas,
  dashboard ou outros endpoints financeiros.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-31.1:

- `caixa/urls.py`.
- `caixa/views_obrigacoes.py`.
- `caixa/services_obrigacoes.py`.
- `caixa/contracts_obrigacoes.py`.
- `caixa/services_escrita_canonica.py`.
- `caixa/serializers_obrigacoes.py`.
- `caixa/permissions.py`.
- `caixa/tests.py`.

### PM-31.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `POST` anonimo `401` nas duas URLs quando chega na view.
- `POST` autenticado sem permissao da origem retorna `403`.
- CSRF real: sem token valido bloqueia antes da view com `403` HTML.
- `POST` com CSRF valido chega na view.
- `GET`, `PUT`, `PATCH` e `DELETE` retornam `405` nas duas URLs com:
  - `Allow: POST`;
  - body vazio;
  - `Content-Type: text/html; charset=utf-8`;
  - sem `Cache-Control`.
- `Content-Type` invalido retorna `400`, nao `415`.
- JSON invalido retorna `400`.
- Body JSON nao-dict retorna `400`.
- O erro de `Content-Type`/JSON/body nao-dict preserva:
  - `{"detail": "JSON inválido ou Content-Type incorreto."}`.
- Igualdade funcional entre rota PT-BR e rota EN.
- Sucesso minimo nas duas URLs.
- Shape completo de `data`.
- Shape completo de:
  - `item`;
  - `canonicalSettlement`;
  - `settlement`;
  - `message`.
- Confirmar `settlement == canonicalSettlement`.
- Permissoes por `source` preservadas:
  - `despesa_operacional`;
  - `custo_fixo`;
  - `custo_extra`;
  - `custo_servico`;
  - `parcela_divida`;
  - `investimento`;
  - `financiamento_movimentacao`.
- Confirmar que `caixa.view_lancamentofinanceiro` nao vira requisito
  obrigatorio.
- Aliases de payload preservados:
  - valores realizados/pagos;
  - data de pagamento/realizacao;
  - observacao;
  - baixa de saldo restante;
  - motivo de baixa;
  - forma/descricao de pagamento;
  - detalhes de custo servico;
  - juros/multa/desconto de parcela FCF.
- Efeitos colaterais principais preservados:
  - nao duplicar baixa;
  - nao duplicar pagamento;
  - nao duplicar alocacao;
  - nao duplicar lancamento;
  - atualizar status/realizado/pendente conforme regra atual;
  - preservar `settleRemainingBalance`;
  - preservar juros/multa/desconto em parcela FCF;
  - preservar caminho `canonical-first` quando flags estiverem habilitadas.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de liquidacao de obrigacoes>
```

### PM-31.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_liquidar_obrigacao_financeira` para DRF.

Regras:

- Usar `@api_view(["POST"])`.
- Usar `Response` apenas na borda.
- Preservar as duas rotas existentes apontando para a mesma view.
- Preservar `@require_POST` por fora, ou equivalente, para manter `405` Django
  padrao.
- Preservar CSRF real no `POST`.
- Preservar autenticacao manual `401`.
- Preservar permissao por `source`, sem exigir permissao ampla.
- Preservar `Content-Type`/JSON/body nao-dict como `400` atual.
- Preservar aliases atuais.
- Preservar transacoes atuais.
- Preservar efeitos colaterais atuais.
- Reaproveitar services, contracts, serializers e helpers atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em listagem, exportacao, baixas, dashboard ou outros endpoints
  financeiros.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de liquidacao de obrigacoes>
```

### PM-31.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de liquidacao de obrigacoes>
python manage.py test <testes relacionados existentes>
python manage.py test
```

Validar:

- Testes focados de liquidacao de obrigacoes passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui:
  - `POST /api/obrigacoes-financeiras/liquidar/`;
  - `POST /api/payment-obligations/settle/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.
- Nenhum efeito colateral financeiro mudou.

### PM-31.5 - Encerramento

Status: concluida.

Atualizar este documento com:

- Arquivos alterados.
- Testes criados.
- Como a view foi migrada.
- Comandos executados.
- Resultados dos testes.
- Resultado do `spectacular`.
- Warnings encontrados.
- Riscos residuais.
- `git status --short`.
- Confirmacao se esta pronto para commit manual.

## Registro de execucao

### PM-31.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- As duas rotas apontam para a mesma view.
- Endpoint permanece Django puro antes da migracao.
- Endpoint classificado como mutation financeira sensivel e de alto risco.
- Decisao: migrar sozinho, sem agrupar com listagem, exportacao, baixas,
  dashboard ou outros endpoints financeiros.
- Nenhuma alteracao de arquivo feita na PM-31.1.

### PM-31.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados:

- `test_api_liquidar_obrigacao_preserva_405_django_nas_duas_rotas`.
- `test_api_liquidar_obrigacao_preserva_csrf_real`.
- `test_api_liquidar_obrigacao_preserva_autenticacao_e_borda_json_nas_duas_rotas`.
- `test_api_liquidar_obrigacao_preserva_permissoes_por_source`.
- `test_api_liquidar_obrigacao_preserva_sucesso_shape_alias_e_sem_view_lancamento`.
- `test_api_liquidar_obrigacao_preserva_aliases_baixa_saldo_e_idempotencia`.
- `test_api_liquidar_obrigacao_preserva_alias_tipo_e_descricao_pagamento_servico`.
- `test_api_liquidar_obrigacao_preserva_aliases_ajustes_parcela_fcf`.

Contrato congelado:

- `405` Django padrao nas duas rotas, com `Allow: POST`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- CSRF real com `Client(enforce_csrf_checks=True)`.
- `401`, `403`, `400` e `200` JSON/no-store preservados.
- `Content-Type` invalido continua `400`, nao `415`.
- JSON invalido/body nao-dict preservam o detalhe atual.
- Permissoes por `source` preservadas.
- `caixa.view_lancamentofinanceiro` nao e requisito obrigatorio.
- Rotas PT-BR e EN preservam comportamento equivalente.
- `settlement == canonicalSettlement`.
- Aliases principais preservados.
- Idempotencia representativa preservada sem duplicar baixa, pagamento,
  alocacao ou lancamento nos fluxos cobertos.

Comandos executados:

```bash
python manage.py test caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_405_django_nas_duas_rotas caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_csrf_real caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_autenticacao_e_borda_json_nas_duas_rotas caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_permissoes_por_source caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_sucesso_shape_alias_e_sem_view_lancamento caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_aliases_baixa_saldo_e_idempotencia caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_alias_tipo_e_descricao_pagamento_servico caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_aliases_ajustes_parcela_fcf
python manage.py check
```

Resultado:

- 8 testes focados passaram.
- `python manage.py check` passou sem issues.
- Nenhuma view foi migrada nesta fase.

### PM-31.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_obrigacoes.py`.

Como a view foi migrada:

- Somente `api_liquidar_obrigacao_financeira` foi convertida para DRF.
- A view passou a usar `@api_view(["POST"])`.
- Foi usada permissao local `@permission_classes([AllowAny])` para preservar os
  `401`/`403` manuais e evitar substituicao pela permissao global do DRF.
- `@require_POST` foi preservado para manter o `405` Django padrao.
- `@csrf_protect` e `api_liquidar_obrigacao_financeira.csrf_exempt = False`
  foram aplicados localmente porque o wrapper do DRF marca APIView como
  `csrf_exempt`; sem isso, o bloqueio CSRF mudava de HTML Django para JSON DRF.
- `Response` foi usado apenas na borda, convertendo os `JsonResponse` manuais
  existentes em `Response` sem alterar payload, status ou headers relevantes.
- `_payload_json`, `_erro_validacao_payload`, services, contracts, selectors e
  serializers manuais foram reaproveitados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- Listagem, exportacao, baixas, dashboard e outros endpoints financeiros nao
  foram alterados.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_405_django_nas_duas_rotas caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_csrf_real caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_autenticacao_e_borda_json_nas_duas_rotas caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_permissoes_por_source caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_sucesso_shape_alias_e_sem_view_lancamento caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_aliases_baixa_saldo_e_idempotencia caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_alias_tipo_e_descricao_pagamento_servico caixa.tests.FiltrosHtmlTests.test_api_liquidar_obrigacao_preserva_aliases_ajustes_parcela_fcf
```

Resultado:

- `python manage.py check` passou sem issues.
- `python manage.py spectacular --validate` passou.
- OpenAPI passou a incluir:
  - `POST /api/obrigacoes-financeiras/liquidar/`;
  - `POST /api/payment-obligations/settle/`.
- 8 testes focados passaram.
- Durante a validacao inicial, foi detectado que DRF alterava o bloqueio CSRF
  para JSON. A correcao local com `csrf_protect` e `csrf_exempt = False`
  restaurou o contrato runtime atual.

### PM-31.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Resultado:

- `python manage.py check`: passou sem issues.
- `python manage.py spectacular --validate`: passou.
- Warnings do spectacular: nenhum warning observado.
- `python manage.py test caixa.tests.FiltrosHtmlTests`: 404 testes passaram.
- `python manage.py test`: 773 testes passaram.
- Logs esperados de CSRF apareceram em testes que validam bloqueio sem token.
- Nenhuma mudanca de contrato runtime foi detectada.
- Nenhum efeito colateral financeiro inesperado foi detectado nos testes.

### PM-31.5 - Encerramento

Status: concluida.

Arquivos alterados na PM-31:

- `caixa/tests.py`.
- `caixa/views_obrigacoes.py`.
- `docs/PLANO_PM31_MIGRACAO_LIQUIDACAO_OBRIGACOES_DRF.md`.

Resumo final:

- PM-31.2 criou testes de paridade antes da migracao.
- PM-31.3 migrou somente `api_liquidar_obrigacao_financeira` para DRF.
- As duas rotas continuam apontando para a mesma view.
- CSRF real foi preservado localmente.
- Permissoes por `source` foram preservadas.
- `Content-Type` invalido continua `400`, nao `415`.
- `405` Django padrao foi preservado.
- `settlement == canonicalSettlement` foi preservado.
- Idempotencia e efeitos financeiros cobertos pelos testes foram preservados.
- Nenhum frontend, settings, CORS, CSRF global ou auth global foi alterado.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- Nenhum endpoint fora da liquidacao foi migrado.

Riscos residuais:

- O endpoint continua sendo mutation financeira de alto risco de negocio.
- Os testes cobrem os fluxos representativos e os pontos sensiveis do contrato,
  mas nao substituem uma revisao manual de negocio para todas as combinacoes de
  payload/source/flags.
- O schema OpenAPI permanece generico (`object`) por escolha consciente de
  preservar runtime e nao introduzir serializers DRF nesta PM.
- A linha local `api_liquidar_obrigacao_financeira.csrf_exempt = False` deve ser
  mantida enquanto a view estiver em DRF para preservar o bloqueio CSRF Django
  atual.

Status final:

- PM-31 concluida.
- Pronta para revisao e commit local manual.
