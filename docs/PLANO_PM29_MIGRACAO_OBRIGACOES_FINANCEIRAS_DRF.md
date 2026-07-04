# Plano PM-29 - Migracao incremental de `GET /api/obrigacoes-financeiras/` e `GET /api/payment-obligations/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar conjuntamente `GET /api/obrigacoes-financeiras/` e
`GET /api/payment-obligations/` para Django REST Framework, preservando
integralmente o contrato atual consumido pelo frontend Next.js.

As duas rotas podem ser tratadas na mesma PM porque apontam para a mesma view
`api_obrigacoes_financeiras`.

DRF deve entrar apenas como casca HTTP da view de leitura das obrigacoes
financeiras, sem alterar regra de negocio, selectors, serializers manuais,
contracts, permissoes, CORS, headers, status HTTP, JSON, filtros, aliases,
ordenacao, paginacao, totais, queries ou contrato do frontend.

## Escopo

- Congelar o contrato atual das duas rotas em testes antes da migracao.
- Migrar somente a view `api_obrigacoes_financeiras`.
- Manter as duas rotas existentes apontando para a mesma view.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissao manual ampla `caixa.view_lancamentofinanceiro`.
- Preservar permissoes parciais por `source`.
- Preservar escopo `permissionScope=payments`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar Content-Type, Cache-Control/no-store, status HTTP e shape atual das
  respostas JSON.
- Preservar filtros canonicos atuais.
- Preservar aliases e normalizacoes atuais.
- Preservar limites, paginacao e ordenacao atuais.
- Preservar `summary`, `cashAvailability` e `paymentQueue`.
- Reaproveitar selectors, serializers manuais, contracts e helpers atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Liquidacao de obrigacoes.
- Exportacao de obrigacoes.
- Dashboard financeiro.
- Baixas financeiras.
- Modelagem financeira canonica.
- Mes financeiro.
- Lancamentos financeiros.
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

Nesta PM, somente a view `api_obrigacoes_financeiras` deve ser migrada,
preservando as duas URLs atuais.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
GETs financeiros antes de mutations financeiras, sempre com paridade congelada
antes da migracao.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, CORS, filtros, aliases,
ordenacao, paginacao, totais, queries ou comportamento runtime apenas para
melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-29.1

Arquivo atual:

- `caixa/views_obrigacoes.py`.

View atual:

- `api_obrigacoes_financeiras`.

Rotas atuais:

- `path("api/obrigacoes-financeiras/", api_obrigacoes_financeiras, name="api_obrigacoes_financeiras")`.
- `path("api/payment-obligations/", api_obrigacoes_financeiras, name="api_payment_obligations")`.

Nomes das rotas:

- `caixa:api_obrigacoes_financeiras`.
- `caixa:api_payment_obligations`.

As duas rotas apontam para a mesma view.

Decoradores atuais:

- `@require_GET`.

Metodo aceito:

- `GET`.

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` observado: `GET`.
- Body observado: vazio.
- `Content-Type` observado: `text/html; charset=utf-8`.
- `Cache-Control` observado: ausente.
- A resposta de `405` Django padrao deve ser preservada.
- Como `@require_GET` esta na view atual, o `405` ocorre antes de
  autenticacao/permissao.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem permissao aplicavel:

```json
{"detail": "Permission denied."}
```

com status `403`.

Comportamento para usuario autenticado com permissao aplicavel:

- Status `200`.
- Resposta JSON com top-level `data`.
- Header `Content-Type` JSON.
- Header `Cache-Control` com `no-store`.

Permissao ampla:

- `caixa.view_lancamentofinanceiro`.

Permissoes parciais por `source`:

- `receita_operacional`: `caixa.view_receitaoperacional`.
- `despesa_operacional`: `caixa.view_despesaoperacional`.
- `custo_fixo`: `caixa.view_custofixo`.
- `custo_servico`: `caixa.view_eventocustoservico`.
- `custo_extra`: `caixa.view_eventocustoextra`.
- `parcela_divida`: `caixa.view_parceladivida`.
- `investimento`: `caixa.view_investimento`.
- `financiamento_movimentacao`: `caixa.view_parceladivida`.

Escopo especial de pagamentos:

- `permissionScope=payments` restringe fontes conforme permissoes de
  baixa/pagamento nativo.
- Se o usuario tem permissoes de pagamento para fontes especificas, a view pode
  limitar `sources` a essas fontes permitidas.
- Se uma fonte solicitada nao for permitida, o contrato atual retorna `403`.
- Esta regra deve ser preservada exatamente.

Payload de sucesso:

```json
{
  "data": {
    "items": [],
    "summary": {},
    "cashAvailability": {},
    "filters": {},
    "filterOptions": {},
    "pagination": {},
    "meta": {}
  }
}
```

Campo opcional:

- `data.paymentQueue`, presente quando `permissionScope=payments` e
  `obligationType=pagar`.

Shape de `data.items[]`:

- `id`.
- `obligationType`.
- `tipoObrigacao`.
- `tipo_obrigacao`.
- `source`.
- `origin`.
- `origem`.
- `sourceId`.
- `originId`.
- `sourceLabel`.
- `sourceDetail`.
- `sourceDetailLabel`.
- `description`.
- `obligationDescription`.
- `descricao`.
- `reference`.
- `referencia`.
- `dueDate`.
- `date`.
- `data`.
- `data_vencimento`.
- `paymentDate`.
- `data_pagamento`.
- `plannedAmount`.
- `valor_previsto`.
- `realizedAmount`.
- `paidAmount`.
- `valor_realizado`.
- `valor_pago`.
- `overRealizedAmount`.
- `realizedAbovePlannedAmount`.
- `excedenteRealizado`.
- `valor_excedente_realizado`.
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
- `pendingAmount`.
- `pendingPaymentAmount`.
- `pendingReceivableAmount`.
- `pendingValue`.
- `valor_pendente_pagamento`.
- `contas_pendentes`.
- `cashFlowGroup`.
- `fluxo`.
- `nature`.
- `natureza`.
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

Shape de `data.items[].actionHints`:

- `primary`.
- `admin`.
- `actions`.

Shape de `data.summary`:

- `plannedAmount`.
- `realizedAmount`.
- `paidAmount`.
- `overRealizedAmount`.
- `realizedAbovePlannedAmount`.
- `pendingAmount`.
- `originRealizedAmount`.
- `originPendingAmount`.
- `originOverRealizedAmount`.
- `ledgerRealizedAmount`.
- `ledgerPendingAmount`.
- `ledgerOverRealizedAmount`.
- `realizedAmountDifference`.
- `reconciledCount`.
- `divergentCount`.
- `overdueAmount`.
- `obligationsCount`.
- `pendingCount`.
- `overdueCount`.
- `liquidatedCount`.
- `ledgerPendingCount`.
- `ledgerOverdueCount`.
- `ledgerLiquidatedCount`.
- `ledgerOverdueAmount`.
- `byCashFlowGroup`.
- `bySource`.
- `byReconciliationDiagnosis`.
- `reconciliationWorklist`.
- `overview`.
- Aliases PT-BR de valores e totais ja publicados.

Shape de `data.cashAvailability`:

- `applicable`.
- `aplicavel`.
- `appliesToObligationType`.
- `obligationTypeScope`.
- `tipoObrigacaoEscopo`.
- `availableCashAmount`.
- `cashAvailableAmount`.
- `caixaDisponivel`.
- `saldoCaixaDisponivel`.
- `finalCashAmount`.
- `currentAvailableCashAmount`.
- `currentCashAvailableUntilDate`.
- `initialCashAmount`.
- `realizedInflowAmount`.
- `realizedOutflowAmount`.
- `periodRealizedAmount`.
- `accumulatedCashUntilDate`.
- `accumulatedAvailableCashAmount`.
- `cashAvailableUntilDate`.
- `pendingScopeAmount`.
- `pendingPayablesAmount`.
- `cashCoverageAfterPendingAmount`.
- `paymentCapacityAfterPendingAmount`.
- `currentCashCoverageAfterPendingAmount`.
- `availableAfterPendingAmount`.
- `cashCoverageDeficitAmount`.
- `currentCashCoverageDeficitAmount`.
- `dateBasis`.
- `formula`.
- `accumulatedDateBasis`.
- `accumulatedFormula`.
- `coverageFormula`.

Shape de `data.filters`:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `contractLabel`.
- `contractCode`.
- `eventId`.
- `eventLabel`.
- `clientId`.
- `clientLabel`.
- `source`.
- `sources`.
- `cashFlowGroup`.
- `nature`.
- `status`.
- `settlementStatus`.
- `reconciliationStatus`.
- `reconciliationDiagnosis`.
- `realizedAmountBasis`.
- `realizedAbovePlanned`.
- `dataSource`.
- `obligationType`.
- `search`.
- `overdueScope`, quando informado.

Shape de `data.filterOptions`:

- `contracts`.
- `events`.
- `clients`.
- `sources`.
- `cashFlowGroups`.
- `settlementStatuses`.
- `reconciliationStatuses`.
- `reconciliationDiagnoses`.
- `realizedAmountBases`.
- `realizedAbovePlannedStatuses`.
- `obligationTypes`.
- `dataSources`.

Shape de `data.pagination`:

- `limit`.
- `offset`.
- `total`.
- `hasMore`.

Shape de `data.meta`:

- `generatedAt`.
- `source`, com valor `"backend"`.
- `currency`, com valor `"BRL"`.
- `dateBasis`.
- `realizedAmountBasis`.
- `availableRealizedAmountBases`.
- `ledgerReconciliation`.
- `settlementCapabilities`.
- `availableObligationTypes`.
- `obligationTypeScope`.
- `dataSourceRequested`.
- `dataSourceActual`.
- `canonicalFallbackReason`.
- `readModelStatusReason`.
- `readModelStatusLabel`.
- `readModelStatusDetail`.
- `readModelStatusTone`.
- `readModelStatus`.
- `readModelStatusDiagnostics`.
- `canonicalReadiness`.
- `nomenclature`.
- `amountSemantics`.
- `filterSemantics`.

Shape de `data.paymentQueue` quando presente:

- `contractVersion`.
- `generatedAt`.
- `referenceDate`.
- `referenceDateSource`.
- `dateBasis`.
- `amountBasis`.
- `scope`.
- `queueSummary`.
- `urgencyBuckets`.
- `facets`.
- `sorting`.
- `readinessRules`.
- `pagination`.
- `items`.

Shape de `data.paymentQueue.items[]`:

- `id`.
- `source`.
- `sourceId`.
- `sourceLabel`.
- `sourceDetail`.
- `sourceDetailLabel`.
- `description`.
- `obligationDescription`.
- `reference`.
- `dueDate`.
- `settlementStatus`.
- `settlementStatusLabel`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `originPendingAmount`.
- `originRealizedAmount`.
- `eventId`.
- `eventLabel`.
- `clientName`.
- `contractCode`.
- `contractLabel`.
- `urgency`.
- `daysUntilDue`.
- `canSettle`.
- `blockedReason`.
- `blockedReasonLabel`.
- `supportsPaymentMethod`.
- `supportsPaymentDescription`.
- `supportsAdjustments`.
- `supportsWriteOff`.
- `requiresSourceDetail`.
- `sortKey`.

Filtros canonicos aceitos pela borda HTTP atual:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `limit`.
- `offset`.
- `queueLimit`.
- `queueOffset`.
- `permissionScope`.
- `overdueScope`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `reconciliationStatus`.
- `realizedAmountBasis`.
- `reconciliationDiagnosis`.
- `realizedAbovePlanned`.
- `dataSource`.
- `obligationType`.
- `source`.
- `sources`.
- `cashFlowGroup`.
- `nature`.
- `search`.
- `settlementStatus`.
- `status`.

Normalizacoes e aliases preservados:

- `status=pago` vira `liquidado` para obrigacao a pagar.
- `status=recebido` vira `liquidado` para obrigacao a receber.
- `obligationType` aceita aliases de pagar/receber, saida/entrada.
- `dataSource` aceita aliases de fonte canonica/legacy.
- `realizedAmountBasis` aceita aliases de ledger/lancamentos.
- `realizedAbovePlanned` aceita aliases truthy/falsey.
- Aliases internos publicados no payload, como `data_inicial`,
  `data_final`, `contrato_codigo`, `evento_id`, `cliente_id`, `busca`,
  `tipoObrigacao`, `tipo_obrigacao`, `origem`, `fluxo` e `natureza`, nao
  devem ser promovidos a contrato HTTP externo sem decisao explicita.

Regras atuais de limite e paginacao:

- `limit` padrao: `100`.
- `limit` minimo: `1`.
- `limit` maximo: `300`.
- `offset` padrao: `0`.
- `queueLimit` e `queueOffset` preservam a paginacao propria de
  `paymentQueue`.
- `summary` e calculado sobre todos os itens filtrados, nao apenas sobre a
  pagina.
- `paymentQueue` calcula summary, buckets e facets sobre os candidatos do
  escopo de pagamentos, nao apenas sobre a pagina da fila.

Ordenacao atual:

- A lista legacy e ordenada por `due_date`, `cash_flow_group`, `source`,
  `description` e `source_id`.
- A fonte canonica/fallback deve manter a ordenacao atualmente entregue pelo
  selector.
- A PM-29.2 deve congelar a ordenacao observada para os cenarios testados.

Diferencas entre rota PT-BR e rota EN:

- Nao ha diferenca funcional esperada.
- As duas rotas usam a mesma view, mesmas permissoes, mesmos filtros e mesmo
  shape.
- A diferenca atual e apenas URL/nome da rota.

Dependencias atuais:

- `api_authentication_required_response`.
- `api_permission_denied_response`.
- `api_no_store_json_response`.
- `_params_obrigacoes_autorizados`.
- `_params_obrigacoes_autorizados_por_usuario`.
- `_params_obrigacoes_pagamentos_autorizados`.
- `_usuario_pode_ver_source_obrigacoes`.
- `normalizar_filtros_obrigacoes`.
- `montar_payload_obrigacoes_financeiras_api`.
- `listar_obrigacoes_com_fonte`.
- `listar_obrigacoes_financeiras`.
- `resumir_obrigacoes_financeiras`.
- `montar_overview_obrigacoes_financeiras`.
- `montar_payment_queue_obrigacoes`.
- `montar_posicao_caixa_periodo`.
- `serializar_obrigacao_financeira`.
- `serializar_resumo_obrigacoes`.
- `serializar_opcoes_dimensoes_operacionais`.
- `contracts_obrigacoes`.
- Selectors/serializers da modelagem canonica, quando a fonte canonica esta
  disponivel.

Complexidade de queries:

- Alta.
- O endpoint pode usar fonte canonica ou fallback legacy.
- A fonte legacy agrega varias origens financeiras em uma lista unica.
- O payload serializa a lista filtrada antes da paginacao.
- `summary`, `overview`, `cashAvailability` e `paymentQueue` dependem da lista
  completa filtrada.
- `filterOptions` executa consultas adicionais de dimensoes operacionais.
- Ha reconciliacao com lancamentos financeiros/canonicos.
- Query count pode crescer com eventos, clientes, contratos, obrigacoes,
  lancamentos, baixas e fontes de origem.

## Riscos especificos de obrigacoes financeiras

- Endpoint financeiro sensivel e usado para leitura operacional de contas a
  pagar/receber.
- Mistura fontes canonicas, fallback legacy e semantica de read model.
- Altera a visibilidade de dados conforme permissao ampla, permissao por
  `source` e `permissionScope=payments`.
- Mudanca acidental pode expor fontes financeiras indevidas.
- `summary` e `paymentQueue` dependem de todos os itens filtrados; resumir pela
  pagina mudaria contrato financeiro.
- `cashAvailability` usa regras de disponibilidade de caixa; qualquer mudanca
  de filtro ou base de data pode alterar totais sensiveis.
- DRF, se usado sem cuidado, muda `405` para payload JSON padrao.
- DRF, se usar permissao global, pode substituir `401`/`403` atuais.
- Uso direto de `Response` pode perder headers `Cache-Control` atuais.
- OpenAPI tende a ficar generico sem schema manual, mas runtime tem prioridade.

## Guardrails

- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao alterar models.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar contracts.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Nao alterar liquidacao.
- Nao alterar exportacao.
- Nao alterar dashboard financeiro.
- Nao alterar baixas financeiras.
- Nao alterar modelagem financeira canonica.
- Nao alterar mes financeiro.
- Nao alterar outros endpoints financeiros.
- Reaproveitar `montar_payload_obrigacoes_financeiras_api`.
- Reaproveitar `_params_obrigacoes_autorizados` e helpers atuais de permissao.
- Reaproveitar serializers manuais e helpers atuais.
- Preservar `@require_GET` por fora da view DRF, ou mecanismo equivalente, para
  manter `405` Django padrao.
- Usar permissao local `AllowAny` se necessario para impedir que a permissao
  global do DRF substitua os `401`/`403` manuais.
- Converter para `Response` apenas na borda, preservando status e headers.
- Priorizar paridade runtime sobre OpenAPI.
- Se algum comportamento atual parecer estranho, congelar como esta antes de
  migrar.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `GET` anonimo preserva `401` JSON atual nas duas rotas.
- `GET` autenticado sem permissao aplicavel preserva `403` JSON atual nas duas
  rotas.
- `GET` autenticado com permissao ampla preserva `200` e shape atual nas duas
  rotas.
- As duas rotas preservam igualdade funcional.
- Headers JSON/no-store preservados em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual nas duas
  rotas.
- Filtros canonicos preservados.
- Aliases e normalizacoes atuais preservados.
- Limites e paginacao preservados.
- Ordenacao atual preservada.
- Resposta vazia mantem shape.
- `summary` continua calculado sobre todos os itens filtrados.
- `cashAvailability` continua calculado com as regras atuais.
- `paymentQueue` continua presente e com shape atual no escopo aplicavel.
- Permissao ampla preservada.
- Permissoes parciais por `source` preservadas.
- `permissionScope=payments` preservado.
- Aliases publicados no payload, mas que nao sao contrato HTTP externo real,
  continuam sem ser promovidos.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora das duas rotas da view `api_obrigacoes_financeiras` e
  alterado.

## Criterios de bloqueio

Parar imediatamente se:

- Algum shape de `data` mudar.
- `items`, `summary`, `cashAvailability`, `filters`, `filterOptions`,
  `pagination`, `meta` ou `paymentQueue` mudarem sem previsao.
- Algum filtro canonico mudar.
- Algum alias ou normalizacao mudar.
- Algum alias interno passar a ser aceito como filtro HTTP externo sem decisao
  explicita.
- `limit`, `offset`, `total`, `hasMore`, `queueLimit` ou `queueOffset` mudarem.
- `summary` passar a considerar apenas a pagina.
- `paymentQueue` passar a considerar apenas a pagina de itens gerais.
- `cashAvailability` mudar total, base de data ou formula.
- Ordenacao mudar.
- `405` mudar para JSON DRF padrao.
- `401` ou `403` mudarem.
- Header `Cache-Control` mudar em respostas JSON.
- Permissao ampla ou parcial por `source` mudar.
- `permissionScope=payments` mudar.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario alterar contracts.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar liquidacao, exportacao, dashboard, baixas, mes
  financeiro ou outros endpoints financeiros junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_obrigacoes_financeiras`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em liquidacao, exportacao, dashboard, baixas ou outros endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum selector, serializer manual ou contract seja
alterado.

## Fases

### PM-29.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como financeiro sensivel.
- Decisao: migrar as duas rotas juntas porque usam a mesma view.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-29.1:

- `caixa/urls.py`.
- `caixa/views_obrigacoes.py`.
- `caixa/permissions.py`.
- `caixa/contracts_obrigacoes.py`.
- `caixa/serializers_obrigacoes.py`.
- `caixa/selectors_obrigacoes.py`.
- `caixa/tests.py`.

### PM-29.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `GET` anonimo retorna `401` em ambas as URLs.
- `GET` autenticado sem permissao aplicavel retorna `403` em ambas as URLs.
- `GET` com permissao ampla `caixa.view_lancamentofinanceiro` retorna `200` em
  ambas as URLs.
- Igualdade funcional entre rota PT-BR e rota EN.
- Headers JSON/no-store em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` em ambas as URLs com:
  - `Allow: GET`;
  - body vazio;
  - `Content-Type: text/html; charset=utf-8`;
  - sem `Cache-Control`.
- Shape completo de `data`.
- Shape completo de:
  - `items`;
  - `summary`;
  - `cashAvailability`;
  - `filters`;
  - `filterOptions`;
  - `pagination`;
  - `meta`.
- Shape completo de `paymentQueue` quando `permissionScope=payments` e
  `obligationType=pagar`.
- Filtros canonicos preservados:
  - `period`;
  - `quickPeriod`;
  - `startDate`;
  - `endDate`;
  - `limit`;
  - `offset`;
  - `queueLimit`;
  - `queueOffset`;
  - `permissionScope`;
  - `overdueScope`;
  - `contractCode`;
  - `eventId`;
  - `clientId`;
  - `reconciliationStatus`;
  - `realizedAmountBasis`;
  - `reconciliationDiagnosis`;
  - `realizedAbovePlanned`;
  - `dataSource`;
  - `obligationType`;
  - `source`;
  - `sources`;
  - `cashFlowGroup`;
  - `nature`;
  - `search`;
  - `settlementStatus`;
  - `status`.
- Status aliases preservados:
  - `status=pago` vira `liquidado` para obrigacao a pagar;
  - `status=recebido` vira `liquidado` para obrigacao a receber.
- `obligationType` aliases preservados.
- `dataSource` aliases preservados.
- `realizedAmountBasis` aliases preservados.
- `realizedAbovePlanned` truthy/falsey preservado.
- Limites e paginacao preservados.
- Ordenacao atual preservada.
- Resposta vazia mantem shape.
- `summary` calculado sobre todos os itens filtrados, nao apenas pagina.
- `cashAvailability` preservado.
- `paymentQueue` preservado no escopo de pagamentos.
- Permissao ampla preservada.
- Permissoes parciais por `source` preservadas.
- `permissionScope=payments` preservado.
- Aliases externos que aparecem no payload, mas nao sao contrato HTTP real,
  congelados como nao promovidos sem decisao explicita.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de obrigacoes financeiras>
```

### PM-29.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_obrigacoes_financeiras` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar as duas rotas existentes apontando para a mesma view.
- Preservar `@require_GET` por fora, ou equivalente, para manter `405` Django
  padrao.
- Usar `AllowAny` local se necessario para preservar `401`/`403` manuais.
- Preservar permissao manual ampla `caixa.view_lancamentofinanceiro`.
- Preservar permissoes parciais por `source`.
- Preservar `permissionScope=payments`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar filtros canonicos atuais.
- Preservar aliases e normalizacoes atuais.
- Preservar limites e paginacao atuais.
- Preservar ordenacao atual.
- Preservar shape atual.
- Preservar `summary`, `cashAvailability` e `paymentQueue`.
- Reaproveitar selectors, serializers manuais, contracts e helpers atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em liquidacao, exportacao, dashboard, baixas ou outros endpoints
  financeiros.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de obrigacoes financeiras>
```

### PM-29.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de obrigacoes financeiras>
python manage.py test <testes relacionados existentes>
python manage.py test
```

Validar:

- Testes focados de obrigacoes financeiras passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui as duas rotas:
  - `GET /api/obrigacoes-financeiras/`;
  - `GET /api/payment-obligations/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.

### PM-29.5 - Encerramento

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

### PM-29.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- As duas rotas apontam para a mesma view.
- Endpoint permanece Django puro antes da migracao.
- Endpoint classificado como financeiro sensivel e de alto risco.
- Decisao: migrar as duas rotas juntas porque compartilham a mesma view e o
  mesmo contrato.
- Nenhuma alteracao de arquivo feita na PM-29.1.

### PM-29.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados/reforcados:

- `FiltrosHtmlTests.test_api_obrigacoes_financeiras_autenticacao_permissao_e_headers_em_ambas_rotas`.
- `FiltrosHtmlTests.test_api_obrigacoes_financeiras_metodos_nao_permitidos_preservam_405_em_ambas_rotas`.
- `FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_shape_igualdade_funcional_paginacao_e_summary_global`.
- `FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_permissoes_parciais_source_e_payments_scope`.
- `FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_filtros_aliases_e_aliases_internos_nao_promovidos`.

Helpers de teste adicionados:

- `_rotas_obrigacoes_financeiras`.
- `_normalizar_payload_obrigacoes_para_comparacao`.
- `_assert_obrigacoes_financeiras_shape`.
- `_assert_obrigacao_financeira_item_shape`.
- `_assert_payment_queue_obrigacoes_shape`.

Contrato congelado:

- `401` anonimo nas duas rotas.
- `403` autenticado sem permissao aplicavel nas duas rotas.
- `200` autenticado com `caixa.view_lancamentofinanceiro` nas duas rotas.
- Igualdade funcional entre `/api/obrigacoes-financeiras/` e
  `/api/payment-obligations/`.
- Headers JSON/no-store em respostas JSON.
- `405` Django padrao para `POST`, `PUT`, `PATCH` e `DELETE`, com
  `Allow: GET`, body vazio, `Content-Type: text/html; charset=utf-8` e sem
  `Cache-Control`.
- Shape completo de `data`, `items`, `summary`, `cashAvailability`, `filters`,
  `filterOptions`, `pagination`, `meta` e `paymentQueue`.
- Permissao ampla `caixa.view_lancamentofinanceiro`.
- Permissao parcial por `source`.
- `permissionScope=payments`.
- Filtros canonicos atuais.
- Aliases e normalizacoes atuais.
- Limites e paginacao.
- Ordenacao observada nos cenarios cobertos.
- `summary` calculado sobre todos os itens filtrados, nao apenas sobre a
  pagina.
- `cashAvailability` preservado.
- `paymentQueue` preservado.
- Aliases internos publicados no payload, mas nao aceitos como contrato HTTP
  externo, permanecem nao promovidos.

Comandos executados:

```bash
python manage.py test caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_autenticacao_permissao_e_headers_em_ambas_rotas caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_metodos_nao_permitidos_preservam_405_em_ambas_rotas caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_shape_igualdade_funcional_paginacao_e_summary_global caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_permissoes_parciais_source_e_payments_scope caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_filtros_aliases_e_aliases_internos_nao_promovidos
python manage.py check
```

Resultados:

- Primeira tentativa de teste foi bloqueada por `SECRET_KEY` ausente no
  ambiente local.
- Reexecucao com `DEBUG=True` e `SECRET_KEY=local-validation-secret`: 5 testes
  OK.
- `python manage.py check`: OK.

### PM-29.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_obrigacoes.py`.

Como a view foi migrada:

- `api_obrigacoes_financeiras` foi convertida para DRF com
  `@api_view(["GET"])`.
- `Response` foi usado somente na borda do endpoint.
- `@require_GET` permaneceu por fora da view DRF para preservar o `405` Django
  padrao.
- `AllowAny` local foi usado para impedir que a permissao global do DRF
  substitua os `401` e `403` manuais atuais.
- `extend_schema` foi usado apenas para expor a rota no OpenAPI sem alterar
  runtime.
- A permissao ampla e as permissoes parciais continuam centralizadas em
  `_params_obrigacoes_autorizados`.
- `permissionScope=payments` continua usando os helpers existentes.
- O payload continua sendo montado por
  `montar_payload_obrigacoes_financeiras_api(params, request.user)`.
- Selectors, serializers manuais, contracts e helpers de dominio nao foram
  alterados.
- As duas rotas existentes continuam apontando para a mesma view.
- Nenhum endpoint de liquidacao, exportacao, dashboard, baixas, modelagem,
  mes financeiro ou outro endpoint financeiro foi migrado nesta PM.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_autenticacao_permissao_e_headers_em_ambas_rotas caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_metodos_nao_permitidos_preservam_405_em_ambas_rotas caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_shape_igualdade_funcional_paginacao_e_summary_global caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_permissoes_parciais_source_e_payments_scope caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_preserva_filtros_aliases_e_aliases_internos_nao_promovidos
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- 5 testes focados: OK.
- OpenAPI inclui:
  - `GET /api/obrigacoes-financeiras/`;
  - `GET /api/payment-obligations/`.
- Warnings do `spectacular`: nenhum warning novo observado.

### PM-29.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py check
python manage.py spectacular --validate
python manage.py test
```

Resultados:

- `caixa.tests.FiltrosHtmlTests`: 392 testes OK.
- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Suite completa: 761 testes OK.
- Warnings do `spectacular`: nenhum warning novo observado.
- Logs esperados de CSRF/AXES apareceram em testes de autenticacao existentes,
  sem falha.
- Nenhum contrato runtime foi alterado fora da view alvo.
- `paymentQueue`, `cashAvailability`, permissoes por `source`,
  `permissionScope=payments`, paginacao, ordenacao e `405` foram preservados.

### PM-29.5 - Encerramento

Status: concluida.

Arquivos alterados na PM-29:

- `caixa/tests.py`.
- `caixa/views_obrigacoes.py`.
- `docs/PLANO_PM29_MIGRACAO_OBRIGACOES_FINANCEIRAS_DRF.md`.

Confirmacoes finais:

- As duas rotas continuam apontando para a mesma view.
- `GET /api/obrigacoes-financeiras/` foi migrado para DRF por meio da view
  compartilhada.
- `GET /api/payment-obligations/` foi migrado junto por compartilhar a mesma
  view.
- `405` Django padrao foi preservado.
- `401` e `403` JSON atuais foram preservados.
- Permissao ampla `caixa.view_lancamentofinanceiro` foi preservada.
- Permissoes parciais por `source` foram preservadas.
- `permissionScope=payments` foi preservado.
- Filtros canonicos atuais foram preservados.
- Aliases e normalizacoes atuais foram preservados.
- Limites, paginacao e ordenacao foram preservados.
- `summary` continua calculado sobre todos os itens filtrados.
- `cashAvailability` foi preservado.
- `paymentQueue` foi preservado.
- Frontend nao foi alterado.
- Settings, CORS, CSRF global e autenticacao global nao foram alterados.
- Liquidacao, exportacao, dashboard financeiro, baixas financeiras, modelagem
  financeira canonica, mes financeiro e outros endpoints financeiros nao foram
  alterados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.

Riscos residuais:

- O schema OpenAPI permanece generico (`type: object`) porque a PM prioriza
  paridade runtime e nao cria Serializer DRF.
- Query count absoluto nao foi congelado em numero fixo nesta PM; a cobertura
  congela contrato, filtros, aliases, paginacao, ordenacao, `summary`,
  `cashAvailability` e `paymentQueue`.
- O endpoint segue sensivel por misturar fonte canonica, fallback legacy,
  permissoes parciais e fila de pagamentos; futuras mudancas devem continuar
  com teste de contrato antes de qualquer ajuste.

`git status --short` ao final da validacao antes deste registro:

```text
 M caixa/tests.py
 M caixa/views_obrigacoes.py
?? docs/PLANO_PM29_MIGRACAO_OBRIGACOES_FINANCEIRAS_DRF.md
```

Recomendacao:

- PM-29 pronta para revisao e commit local manual.
