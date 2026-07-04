# Plano PM-25 - Migracao incremental de `GET /api/mes-financeiro/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET /api/mes-financeiro/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de leitura do mes
financeiro, sem alterar regra de negocio, selectors, serializers manuais,
permissoes, CORS, headers, status HTTP, JSON, filtros, totais, agregacoes,
query count ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET /api/mes-financeiro/` em testes antes da
  migracao.
- Migrar somente a view `api_mes_financeiro`.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissoes manuais:
  - `caixa.view_parceladivida`;
  - `caixa.view_receitaoperacional`.
- Preservar `401` e `403` atuais.
- Preservar `405` e header `Allow: GET`.
- Preservar Content-Type, Cache-Control/no-store, status HTTP e shape atual.
- Preservar filtros, aliases, ordenacao, totais, agregacoes e query count
  atuais.
- Reaproveitar selectors e serializers manuais atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Dashboard financeiro.
- Custos por evento.
- Obrigacoes financeiras.
- Baixas financeiras.
- Lancamentos financeiros.
- Modelagem financeira canonica.
- Endpoints financeiros canonicos.
- Endpoints de clientes.
- Endpoints de eventos.
- Endpoints de orcamentos.
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
- Alteracao de services.
- Alteracao de models.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de metodos quando o contrato for pequeno.

Nesta PM, somente `GET /api/mes-financeiro/` deve ser migrado.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
GETs financeiros antes de mutations financeiras, sempre com paridade congelada
antes da migracao.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, CORS, efeitos de dominio,
queries, filtros, aliases, totais ou comportamento runtime apenas para melhorar
a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-25.1

Arquivo atual:

- `caixa/views_mes_financeiro.py`

View atual:

- `api_mes_financeiro`

Rota atual:

- `path("api/mes-financeiro/", api_mes_financeiro, name="api_mes_financeiro")`

Nome da rota:

- `caixa:api_mes_financeiro`

Decoradores atuais:

- `@require_GET`
- `@require_api_permission(FINANCIAL_MONTH_PERMISSIONS)`

Metodo aceito:

- `GET`

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` esperado: `GET`.
- Resposta de `405` Django padrao deve ser preservada.
- Como `@require_GET` esta por fora do decorator de permissao, o `405` ocorre
  antes de autenticacao/permissao.

Permissoes atuais:

- `caixa.view_parceladivida`.
- `caixa.view_receitaoperacional`.

As duas permissoes sao obrigatorias.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global ou permissao DRF
generica se isso mudar contrato.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem uma ou ambas as permissoes:

```json
{"detail": "Permission denied."}
```

com status `403`.

Comportamento para usuario autenticado com as duas permissoes:

- Status `200`.
- Resposta JSON sem wrapper `data`.
- Header `Content-Type` JSON.
- Header `Cache-Control` com `no-store`.

Filtros HTTP canonicos coletados pela view:

- `mes`.
- `period`.
- `startDate`.
- `endDate`.
- `quickPeriod`.
- `eventId`.
- `clientId`.
- `contractCode`.
- `status`.
- `source`.

Aliases adicionados pela view:

- `quickPeriod` tambem vira `periodo_rapido`.
- `source` tambem vira `origem`.

Aliases internos entendidos pelos selectors, mas nao coletados diretamente pela
view HTTP atual:

- `data_inicial`.
- `data_final`.
- `evento`.
- `evento_id`.
- `costCenterId`.
- `cliente`.
- `cliente_id`.
- `contrato_codigo`.

Esses aliases internos nao devem ser promovidos automaticamente a contrato HTTP
nesta PM.

Normalizacoes importantes:

- `mes` e normalizado como `YYYY-MM`.
- `startDate` e `endDate` tambem aparecem como `data_inicial` e `data_final`
  depois da normalizacao.
- Datas invalidas sao tratadas como vazias.
- `startDate` e `endDate` invertidas sao normalizadas.
- `eventId` e `clientId` so aceitam strings numericas.
- `contractCode` e normalizado pelo helper atual de contratos.
- `period=all` vira `periodo_rapido=todos`.
- Periodos frontend como `previous-month`, `quarter`, `semester` e `year`
  resolvem intervalo de datas.
- Sem periodo explicito, o padrao e o mes atual.

Payload de sucesso:

Status `200`:

```json
{
  "filters": {},
  "filtros": {},
  "filterOptions": {},
  "opcoes": {},
  "totals": {},
  "totais": {},
  "financialResult": {},
  "cashAvailability": {},
  "cashFlows": {},
  "fluxos_caixa": {},
  "dateBasis": {},
  "receivables": [],
  "receitas": [],
  "payables": [],
  "contas_a_pagar": [],
  "movements": [],
  "movimentacoes": []
}
```

Shape de `filters`/`filtros`:

- Preserva os filtros canonicos e os aliases normalizados retornados por
  `resolver_filtros_mes_financeiro`.
- Deve incluir os aliases atuais de periodo, datas, evento, cliente, contrato,
  status e origem quando aplicaveis.

Shape de `filterOptions`/`opcoes`:

- `contracts` e `contratos`.
- `events` e `eventos`.
- `clients` e `clientes`.
- `sources` e `origens`.
- `statuses` e `status`.

Shape de `totals`/`totais`:

- `receita_prevista`.
- `receita_recebida`.
- `receita_aberta`.
- `receita_pendente_recebimento`.
- `divida_prevista`.
- `divida_paga`.
- `divida_pendente_pagamento`.
- `divida_aberta`.
- `divida_vencida`.
- `contas_previstas`.
- `contas_pagas`.
- `contas_pendentes`.
- `contas_vencidas`.
- `custo_variavel`.
- `margem_contribuicao`.
- `margem_contribuicao_percentual`.
- `lucro_operacional_ebit`.
- `saldo_inicial`.
- `saldo_inicial_caixa`.
- `saldo_previsto`.
- `saldo_realizado`.
- `saldo_aberto`.
- `falta_cobrir`.
- `resultado_financeiro`.
- `resultado_financeiro_previsto`.
- `resultado_financeiro_projetado`.
- `resultado_financeiro_realizado`.
- `resultado_financeiro_pendente`.
- `deficit_caixa`.
- `caixa_disponivel`.
- `saldo_caixa_disponivel`.
- `caixa_disponivel_acumulado`.
- `saldo_caixa_disponivel_acumulado`.
- `entrada_prevista_fco`.
- `saida_prevista_fco`.
- `entrada_realizada_fco`.
- `saida_realizada_fco`.
- `resultado_fco_previsto`.
- `resultado_fco_realizado`.
- `entrada_prevista_fci`.
- `saida_prevista_fci`.
- `entrada_realizada_fci`.
- `saida_realizada_fci`.
- `resultado_fci_previsto`.
- `resultado_fci_realizado`.
- `entrada_prevista_fcf`.
- `saida_prevista_fcf`.
- `entrada_realizada_fcf`.
- `saida_realizada_fcf`.
- `resultado_fcf_previsto`.
- `resultado_fcf_realizado`.
- `resultado_previsto_periodo`.
- `resultado_realizado_periodo`.
- `caixa_final_previsto`.
- `caixa_final_realizado`.
- `caixa_final_mes`.
- `finalCashAmount`.
- `projectedFinalCashAmount`.
- `realizedFinalCashAmount`.

Aliases camelCase adicionais em `totals`/`totais`:

- `plannedRevenueAmount`.
- `receivedRevenueAmount`.
- `pendingReceivableAmount`.
- `plannedPayablesAmount`.
- `paidPayablesAmount`.
- `pendingAccountsAmount`.
- `overdueAccountsAmount`.
- `financialResultAmount`.
- `plannedFinancialResultAmount`.
- `projectedFinancialResultAmount`.
- `realizedFinancialResultAmount`.
- `pendingFinancialResultAmount`.
- `cashDeficitAmount`.
- `variableCostAmount`.
- `contributionMarginAmount`.
- `contributionMarginPercent`.
- `operatingProfitEbitAmount`.
- `plannedVariableCostAmount`.
- `plannedContributionMarginAmount`.
- `plannedContributionMarginPercent`.
- `plannedOperatingProfitEbitAmount`.
- `initialCashAmount`.
- `saldoInicial`.
- `availableCashAmount`.
- `cashAvailableAmount`.
- `accumulatedAvailableCashAmount`.

Shape de `financialResult`:

- `projectedAmount`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `cashDeficitAmount`.
- `availableCashAmount`.
- `cashAvailableAmount`.
- `resultadoFinanceiro`.
- `resultadoFinanceiroProjetado`.
- `resultadoFinanceiroRealizado`.
- `deficitCaixa`.
- `caixaDisponivel`.
- `saldoCaixaDisponivel`.

Shape de `cashAvailability`:

- `initialCashAmount`.
- `saldoInicial`.
- `availableCashAmount`.
- `cashAvailableAmount`.
- `caixaDisponivel`.
- `saldoCaixaDisponivel`.
- `finalCashAmount`.
- `accumulatedAvailableCashAmount`.
- `cashAvailableUntilDate`.
- `periodRealizedAmount`.
- `differenceFromPeriodRealizedAmount`.
- `formula`.
- `periodRealizedFormula`.
- `finalCashFormula`.

Shape de `cashFlows`/`fluxos_caixa`:

- Chaves por fluxo: `fco`, `fci`, `fcf`.
- Cada fluxo contem:
  - `code` e `codigo`.
  - `inflowAmount`.
  - `outflowAmount`.
  - `financialResultAmount`.
  - `plannedInflowAmount`.
  - `plannedOutflowAmount`.
  - `realizedInflowAmount`.
  - `realizedOutflowAmount`.
  - `projectedFinancialResultAmount`.
  - `realizedFinancialResultAmount`.
  - aliases legados `entrada_prevista`, `saida_prevista`,
    `entrada_realizada`, `saida_realizada`, `resultado_previsto`,
    `resultado_realizado`.

Shape de `dateBasis`:

- `filters`.
- `receivables`.
- `payables`.
- `realized`.
- `availableCash`.
- `accumulatedAvailableCash`.
- `initialCash`.

Shape de cada item de `receivables`/`receitas`:

- `id`.
- `data`.
- `dueDate`.
- `description`.
- `receivableDescription`.
- `descricao`.
- `cliente`.
- `evento`.
- `plannedAmount`.
- `valor_previsto`.
- `receivedAmount`.
- `valor_recebido`.
- `saldo_a_receber`.
- `pendingReceivableAmount`.
- `valor_pendente_recebimento`.
- `status`.
- `statusLabel`.
- `status_display`.

Shape de cada item de `payables`/`contas_a_pagar`:

- `id`.
- `data`.
- `dueDate`.
- `type`.
- `tipo`.
- `description`.
- `payableDescription`.
- `descricao`.
- `reference`.
- `referencia`.
- `contractCode`.
- `contractName`.
- `contractLabel`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `eventLabel`.
- `clientId`.
- `clientName`.
- `previsto`.
- `pago`.
- `aberto`.
- `plannedAmount`.
- `valor_previsto`.
- `paidAmount`.
- `valor_pago`.
- `pendingAmount`.
- `contas_pendentes`.
- `pendingPaymentAmount`.
- `valor_pendente_pagamento`.
- `status`.
- `statusLabel`.
- `status_display`.
- `overdueDays`.
- `dias_atraso`.

Shape de cada item de `movements`/`movimentacoes`:

- `data`.
- `date`.
- `type`.
- `tipo`.
- `cashFlowGroup`.
- `fluxo_caixa`.
- `origem`.
- `description`.
- `movementDescription`.
- `descricao`.
- `reference`.
- `referencia`.
- `contractCode`.
- `contractName`.
- `contractLabel`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `eventLabel`.
- `clientId`.
- `clientName`.
- `inflowAmount`.
- `entrada`.
- `outflowAmount`.
- `saida`.
- `receivedAmount`.
- `recebido`.
- `paidAmount`.
- `pago`.
- `pendingAmount`.
- `aberto`.
- `plannedInflowAmount`.
- `entrada_prevista`.
- `plannedOutflowAmount`.
- `saida_prevista`.
- `receivedValue`.
- `valor_recebido`.
- `paidValue`.
- `valor_pago`.
- `pendingAccountsAmount`.
- `contas_pendentes`.
- `status`.
- `saldo_previsto_acumulado`.
- `saldo_realizado_acumulado`.
- `falta_cobrir_acumulada`.
- `accumulatedFinancialResult`.
- `accumulatedFinancialResultAmount`.
- `resultado_financeiro_acumulado`.
- `accumulatedProjectedFinancialResult`.
- `accumulatedProjectedFinancialResultAmount`.
- `resultado_financeiro_previsto_acumulado`.
- `accumulatedRealizedFinancialResult`.
- `accumulatedRealizedFinancialResultAmount`.
- `resultado_financeiro_realizado_acumulado`.
- `accumulatedCashDeficit`.
- `accumulatedCashDeficitAmount`.
- `deficit_caixa_acumulado`.

Dependencias atuais:

- `filtros_mes_financeiro_api`.
- `montar_payload_mes_financeiro_api`.
- `montar_contexto_mes_financeiro`.
- `resolver_filtros_mes_financeiro`.
- `buscar_movimentos_mes`.
- `montar_contas_a_pagar`.
- `montar_movimentacoes_mes`.
- `calcular_totais_mes_financeiro`.
- `calcular_totais_fluxos_caixa`.
- `calcular_caixa_disponivel_mes`.
- `saldo_caixa_disponivel`.
- `montar_opcoes_eventos_clientes_filtro`.
- Serializers manuais de dimensoes operacionais.

Complexidade das queries e totais:

- O endpoint agrega receitas, parcelas de divida, despesas, custos fixos,
  investimentos e financiamentos.
- Usa `select_related` em varios querysets.
- Materializa listas de movimentos.
- Ordena receitas, parcelas, despesas, custos fixos, investimentos,
  financiamentos, contas a pagar e movimentacoes.
- Calcula saldo inicial, fluxos FCO/FCI/FCF, resultado previsto/realizado,
  caixa final, disponibilidade de caixa acumulada e acumulados por movimento.
- Ja existe cobertura de query count constante com limite `<= 27`.

## Riscos especificos de mes financeiro

- Endpoint GET-only, mas com regra financeira agregada e sensivel.
- Payload grande e com aliases legados/canonicos duplicados.
- Permissao composta: exige duas permissoes simultaneamente.
- Alto acoplamento com filtros de periodo e filtros operacionais.
- Alto acoplamento com fluxo de caixa FCO/FCI/FCF.
- Risco de alterar saldo inicial, caixa final ou caixa acumulado.
- Risco de alterar filtros HTTP canonicos ao expor aliases internos.
- Risco de alterar query count por materializacao/serializacao indevida.
- Risco de DRF trocar automaticamente `401`, `403` ou `405` por payload/header
  diferente.
- Risco de OpenAPI incentivar mudanca de runtime para documentar melhor.

Classificacao de risco:

- Alto.

Motivo:

- Apesar de ser GET-only, concentra leitura financeira agregada, fluxo de caixa,
  saldo inicial, caixa disponivel e aliases consumidos pelo frontend.

Decisao de agrupamento:

- Deve ser migrado sozinho.
- Nao agrupar com dashboard financeiro, custos por evento, obrigacoes
  financeiras ou endpoints financeiros canonicos.

## Guardrails

- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar services.
- Nao alterar models.
- Nao alterar signals.
- Nao alterar filtros atuais.
- Nao alterar querysets/totais atuais.
- Nao expor aliases internos como contrato HTTP novo.
- Nao alterar JSON, status HTTP, headers ou contrato para melhorar OpenAPI.
- Reaproveitar a estrutura existente sempre que possivel.
- Preservar runtime acima de schema.

## PM-25.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Endpoint mapeado.
- Contrato atual documentado neste plano.
- Nenhum arquivo alterado durante o diagnostico.

## PM-25.2 - Congelamento de contrato em testes

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.
- Nao migrar endpoint nesta fase.
- Nao usar DRF neste endpoint nesta fase.

Cobrir obrigatoriamente:

- `GET` anonimo retorna `401`.
- `GET` autenticado sem uma ou ambas permissoes retorna `403`.
- `GET` com as duas permissoes retorna `200`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com `Allow: GET`.
- Headers JSON/no-store em `200`, `401` e `403`.
- Shape completo top-level:
  - `filters` e `filtros`;
  - `filterOptions` e `opcoes`;
  - `totals` e `totais`;
  - `financialResult`;
  - `cashAvailability`;
  - `cashFlows` e `fluxos_caixa`;
  - `dateBasis`;
  - `receivables` e `receitas`;
  - `payables` e `contas_a_pagar`;
  - `movements` e `movimentacoes`.
- Shape completo de `receivables`.
- Shape completo de `payables`.
- Shape completo de `movements`.
- Totais e aliases camelCase preservados.
- Filtros HTTP canonicos preservados:
  - `mes`;
  - `period`;
  - `startDate`;
  - `endDate`;
  - `quickPeriod`;
  - `eventId`;
  - `clientId`;
  - `contractCode`;
  - `status`;
  - `source`.
- Aliases adicionados pela view:
  - `quickPeriod` -> `periodo_rapido`;
  - `source` -> `origem`.
- Congelar que aliases internos nao coletados pela view HTTP continuam fora do
  contrato.
- Resposta vazia mantem shape.
- Ordenacao de movimentos preservada.
- Query count constante preservado.

Comandos esperados:

```bash
python manage.py check
python manage.py test caixa.tests.FiltrosHtmlTests
```

Se os testes de paridade forem adicionados em outra classe, rodar tambem a
classe/teste focado correspondente.

## PM-25.3 - Migracao controlada para DRF

Objetivo:

- Converter somente `api_mes_financeiro` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar a mesma URL.
- Preservar o mesmo nome de rota.
- Preservar permissoes manuais:
  - `caixa.view_parceladivida`;
  - `caixa.view_receitaoperacional`.
- Preservar `401` atual.
- Preservar `403` atual.
- Preservar `405` e `Allow: GET`.
- Preservar `Content-Type`.
- Preservar `Cache-Control/no-store`.
- Preservar status HTTP.
- Preservar shape JSON.
- Preservar filtros canonicos atuais.
- Preservar aliases atuais.
- Preservar ordenacao, totais e agregacoes atuais.
- Preservar query count atual.
- Reaproveitar `filtros_mes_financeiro_api`.
- Reaproveitar `montar_payload_mes_financeiro_api`.
- Reaproveitar `montar_contexto_mes_financeiro`.
- Reaproveitar demais helpers, selectors e serializers manuais atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em dashboard financeiro.
- Nao mexer em custos por evento.
- Nao mexer em obrigacoes financeiras.
- Nao mexer em endpoints financeiros canonicos.

Validacoes da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
```

Se houver testes focados novos em outra classe, rodar tambem esses testes.

## PM-25.4 - Validacao completa

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Validar:

- Testes focados de mes financeiro.
- Testes relacionados existentes de financeiro/mes.
- Query count constante.
- OpenAPI valido.
- Suite completa verde.
- Nenhuma alteracao em frontend.
- Nenhuma alteracao em settings.
- Nenhuma alteracao em CORS, CSRF global ou autenticacao global.
- Nenhuma alteracao em dashboard financeiro, custos por evento, obrigacoes
  financeiras ou endpoints financeiros canonicos.

## PM-25.5 - Encerramento

Atualizar este documento com:

- Arquivos alterados.
- Testes criados/alterados.
- Comandos executados.
- Resultado dos testes focados.
- Resultado do `check`.
- Resultado do `spectacular --validate`.
- Resultado da suite completa.
- Warnings do spectacular, se houver.
- Confirmacao de que somente `GET /api/mes-financeiro/` foi migrado.
- Confirmacao de que runtime prevaleceu sobre OpenAPI.
- Riscos residuais.
- `git status --short`.
- Recomendacao final: pronto ou nao para commit local manual.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `GET /api/mes-financeiro/` migrado para DRF.
- Nenhum outro endpoint migrado nesta PM.
- Mesma URL.
- Mesmo nome de rota.
- Mesmo metodo aceito.
- Mesmas permissoes compostas.
- Mesmo `401`.
- Mesmo `403`.
- Mesmo `405` e `Allow: GET`.
- Mesmo JSON.
- Mesmo status HTTP.
- Mesmos headers.
- Mesmos filtros HTTP canonicos.
- Mesmos aliases.
- Mesma ordenacao.
- Mesmos totais e agregacoes.
- Mesmo contrato do frontend.
- Query count constante preservado.
- `python manage.py check` verde.
- `python manage.py spectacular --validate` verde ou com warnings aceitos e
  documentados.
- Testes focados verdes.
- Suite completa verde.
- Documento atualizado no encerramento.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar.
- Status HTTP mudar.
- Headers mudarem.
- `401`, `403` ou `405` mudarem.
- `Allow: GET` mudar.
- Permissoes compostas mudarem.
- Filtros mudarem.
- Aliases mudarem.
- Aliases internos virarem contrato HTTP novo sem decisao explicita.
- Ordenacao mudar.
- Totais ou agregacoes mudarem.
- Query count piorar sem explicacao tecnica.
- Frontend precisar ser alterado.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar outro endpoint junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_mes_financeiro`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em outros endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum selector/serializer manual seja alterado.

## Registro de execucao

### PM-25.1 - Diagnostico read-only

Status: concluida.

Arquivos lidos:

- `caixa/views_mes_financeiro.py`.
- `caixa/urls.py`.
- `caixa/permissions.py`.
- `caixa/serializers_mes_financeiro.py`.
- `caixa/selectors_mes_financeiro.py`.
- `caixa/utils_fluxos_caixa.py`.
- `caixa/serializers_utils.py`.
- `caixa/tests.py`.

Resultado:

- Contrato atual mapeado.
- Lacunas de paridade identificadas.
- Endpoint classificado como risco alto.
- Decisao: migrar sozinho.
- Nenhuma alteracao de arquivo feita na PM-25.1.

### PM-25.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados:

- `test_api_mes_financeiro_exige_autenticacao_permissoes_compostas_e_headers`.
- `test_api_mes_financeiro_metodos_nao_permitidos_preservam_allow`.
- `test_api_mes_financeiro_resposta_vazia_preserva_shape`.
- `test_api_mes_financeiro_preserva_shape_itens_totais_aliases_e_ordenacao`.
- `test_api_mes_financeiro_preserva_filtros_canonicos_e_aliases_da_view`.

Contratos congelados:

- `GET` anonimo retorna `401` com JSON atual.
- `GET` autenticado sem uma ou ambas permissoes retorna `403` com JSON atual.
- `GET` com as duas permissoes retorna `200`.
- Respostas JSON preservam `Content-Type` JSON e `Cache-Control` com
  `no-store`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com `Allow: GET`.
- Resposta vazia preserva shape completo.
- Shape de `filters`/`filtros`, `filterOptions`/`opcoes`, `totals`/`totais`,
  `financialResult`, `cashAvailability`, `cashFlows`/`fluxos_caixa`,
  `dateBasis`, `receivables`/`receitas`, `payables`/`contas_a_pagar` e
  `movements`/`movimentacoes` foi congelado.
- Shapes de itens de `receivables`, `payables` e `movements` foram congelados.
- Totais financeiros, aliases camelCase e acumulados foram congelados.
- Ordenacao de `payables` e `movements` foi congelada.
- Filtros HTTP canonicos e aliases adicionados pela view foram congelados.
- Aliases internos nao coletados pela view HTTP foram mantidos fora do contrato.
- Query count constante segue coberto por
  `test_mes_financeiro_mantem_queries_constantes_com_mais_registros`.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_exige_autenticacao_permissoes_compostas_e_headers caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_metodos_nao_permitidos_preservam_allow caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_resposta_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_preserva_shape_itens_totais_aliases_e_ordenacao caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_preserva_filtros_canonicos_e_aliases_da_view
DEBUG=True SECRET_KEY=local-validation-secret python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests
```

Resultados:

- Testes novos: 5 testes OK.
- `python manage.py check`: OK.
- `caixa.tests.FiltrosHtmlTests`: 382 testes OK.

### PM-25.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_mes_financeiro.py`.

Implementacao:

- Somente `api_mes_financeiro` foi migrado.
- Usado `@api_view(["GET"])`.
- Usado `@permission_classes([AllowAny])` local para impedir que a permissao
  global do DRF substitua os `401`/`403` atuais.
- `@require_GET` foi mantido por fora para preservar `405` Django padrao e
  `Allow: GET`.
- `Response` foi usado somente na borda do endpoint migrado.
- `api_authentication_required_response`,
  `api_permission_denied_response` e `api_no_store_json_response` foram
  reaproveitados para preservar payloads e headers.
- A verificacao manual de permissoes compostas preserva:
  - `caixa.view_parceladivida`;
  - `caixa.view_receitaoperacional`.
- `filtros_mes_financeiro_api`, `montar_payload_mes_financeiro_api`,
  `montar_contexto_mes_financeiro` e demais selectors/serializers manuais
  atuais foram reaproveitados sem alteracao.
- Adicionado `extend_schema` seguro para OpenAPI sem alterar runtime.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_exige_autenticacao_permissoes_compostas_e_headers caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_metodos_nao_permitidos_preservam_allow caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_resposta_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_preserva_shape_itens_totais_aliases_e_ordenacao caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_preserva_filtros_canonicos_e_aliases_da_view caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_expoe_indicadores_tecnicos_fco caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_filtra_por_periodo_frontend caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_separa_caixa_final_de_caixa_acumulado caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_filtra_por_codigo_de_orcamento_sem_contrato_operacional caixa.tests.FiltrosHtmlTests.test_mes_financeiro_mantem_queries_constantes_com_mais_registros
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Testes focados de mes financeiro: 10 testes OK.
- OpenAPI passou a incluir `GET /api/mes-financeiro/`.
- Warnings do spectacular: nenhum warning reportado.

### PM-25.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- `caixa.tests.FiltrosHtmlTests`: 382 testes OK.
- Suite completa: 740 testes OK.
- Warnings observados durante a suite: warnings esperados de CSRF nos testes de
  autenticacao (`/api/auth/login/` e `/api/auth/logout/`), ja cobertos pela
  suite existente.
- Nenhum warning do spectacular foi reportado.
- Query count constante preservado pela suite focada.

### PM-25.5 - Encerramento

Status: concluida.

Arquivos alterados nesta PM:

- `caixa/tests.py`.
- `caixa/views_mes_financeiro.py`.
- `docs/PLANO_PM25_MIGRACAO_MES_FINANCEIRO_DRF.md`.

Confirmacoes:

- Somente `GET /api/mes-financeiro/` foi migrado.
- Dashboard financeiro nao foi alterado.
- Custos por evento nao foi alterado.
- Obrigacoes financeiras nao foram alteradas.
- Endpoints financeiros canonicos nao foram alterados.
- Frontend nao foi alterado.
- Settings nao foram alterados.
- CORS nao foi alterado.
- CSRF global nao foi alterado.
- Autenticacao global nao foi alterada.
- Nenhum Serializer DRF foi criado.
- Nenhum ViewSet ou ModelViewSet foi criado.
- Selectors e serializers manuais foram reaproveitados sem alteracao.
- Filtros HTTP canonicos, aliases, totais, agregacoes, saldo inicial, caixa
  disponivel, caixa final, ordenacao e query count foram preservados.
- Paridade runtime prevaleceu sobre OpenAPI.

Riscos residuais:

- O schema OpenAPI ainda documenta o payload como objeto generico, sem schema
  detalhado de `totals`, `receivables`, `payables` e `movements`.
- O payload continua grande e financeiro; futuras alteracoes em selectors do
  mes financeiro devem rodar os testes focados desta PM.
- Aliases internos continuam fora do contrato HTTP por decisao de paridade; se
  forem promovidos futuramente, isso deve ser feito em PM separada.

`git status --short` ao fim da validacao antes deste registro:

```text
 M caixa/tests.py
 M caixa/views_mes_financeiro.py
?? docs/PLANO_PM25_MIGRACAO_MES_FINANCEIRO_DRF.md
```

Recomendacao final:

- Pronto para commit local manual.
