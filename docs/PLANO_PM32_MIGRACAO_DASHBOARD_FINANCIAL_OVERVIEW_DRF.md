# Plano PM-32 - Migracao incremental de `GET /api/dashboard/financial-overview/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar de forma incremental e controlada o endpoint
`GET /api/dashboard/financial-overview/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da view de dashboard financeiro, sem
alterar regra de negocio, filtros, selectors, serializers manuais, totais,
agregacoes, query count, permissoes, CORS, headers, status HTTP ou contrato do
frontend.

## Escopo

- Congelar o contrato atual do dashboard financeiro em testes antes da migracao.
- Migrar somente a view `api_dashboard_financial_overview`.
- Manter a URL atual `/api/dashboard/financial-overview/`.
- Manter o nome de rota `caixa:api_dashboard_financial_overview`.
- Manter somente o metodo `GET`.
- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_GET` por fora, ou mecanismo equivalente, para manter o
  `405` Django padrao.
- Preservar permissao manual `caixa.view_evento`.
- Preservar `401`, `403`, `405`, headers e payloads atuais.
- Preservar filtros HTTP atuais.
- Preservar aliases HTTP internos atualmente ignorados como ignorados.
- Preservar shape completo do payload e secoes condicionais.
- Preservar totais, agregacoes e query count.
- Reaproveitar selectors e serializers manuais atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Mes financeiro.
- Custos por evento.
- Obrigacoes financeiras.
- Liquidacao de obrigacoes.
- Exportacao de obrigacoes.
- Lancamentos financeiros.
- Baixas financeiras canonicas.
- Modelagem financeira canonica.
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
- Alteracao de services.
- Alteracao de models.
- Alteracao de signals.
- Otimizacao de queries fora do escopo da migracao.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, migrar somente `GET /api/dashboard/financial-overview/`.

Como este endpoint consolida diversas visoes financeiras, a PM deve manter a
regra de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, filtros, aliases,
agregacoes, totais, query count ou comportamento runtime apenas para melhorar a
documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-32.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_dashboard.py`.
- `caixa/permissions.py`.
- `caixa/serializers_dashboard.py`.
- `caixa/selectors_dashboard.py`.
- `caixa/selectors_dashboard_filtros.py`.
- `caixa/selectors_dashboard_totais.py`.
- `caixa/selectors_dashboard_movimentacoes.py`.
- `caixa/selectors_dashboard_contexto.py`.
- `docs/PLANO_CORRECAO_QUERY_COUNT_FINANCIAL_OVERVIEW.md`.
- `caixa/tests.py`.

View atual:

- `api_dashboard_financial_overview`.

Rota atual:

- `path("api/dashboard/financial-overview/", api_dashboard_financial_overview, name="api_dashboard_financial_overview")`.

Nome de rota:

- `caixa:api_dashboard_financial_overview`.

Decoradores atuais:

- `@require_GET`.
- `@require_api_permission(DASHBOARD_PERMISSION)`.

Permissao atual:

- `DASHBOARD_PERMISSION = caixa.view_evento`.

Metodo aceito:

- `GET`.

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` observado: `GET`.
- Body observado: vazio.
- `Content-Type` observado: `text/html; charset=utf-8`.
- `Cache-Control` observado: ausente.
- A resposta de `405` Django padrao deve ser preservada.

CSRF atual:

- Nao e relevante para o contrato funcional porque o endpoint aceita somente
  `GET`.
- A migracao nao pode alterar CSRF global.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado sem `caixa.view_evento`:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado com `caixa.view_evento`:

- Status `200`.
- `Content-Type: application/json`.
- `Cache-Control` com `no-store`.
- Payload top-level:

```json
{"data": {}}
```

Filtros HTTP aceitos pela view:

- `startDate`.
- `endDate`.
- `period`.
- `quickPeriod`.
- `eventId`.
- `clientId`.
- `contractCode`.
- `status`.

Valores reconhecidos de `period`:

- `current-month`.
- `all`.
- `previous-month`.
- `quarter`.
- `semester`.
- `year`.

Valores reconhecidos de `quickPeriod`:

- `hoje`.
- `mes_atual`.
- `30_dias`.
- `todos`.
- `vencidos`.

Valores reconhecidos de `status`:

- `pendente`.
- `parcial`.
- `recebido`.
- `pago`.
- `vencido`.
- `cancelado`.
- `planejado`.
- `realizado`.

Normalizacoes atuais:

- `startDate` e `endDate` aceitam datas ISO validas.
- Se `startDate` vier depois de `endDate`, o intervalo e invertido.
- `eventId` e `clientId` aceitam somente valores numericos.
- `contractCode` remove o prefixo visual `EVT-`.
- Se houver filtro de entidade (`eventId`, `clientId` ou `contractCode`) sem
  periodo explicito, `quickPeriod` padrao vira `todos`.
- Sem filtros de entidade e sem periodo explicito, `quickPeriod` padrao vira
  `mes_atual`.
- Se `period` estiver em `current-month` ou `all`, ele e convertido para
  `quickPeriod`.
- Se `period` estiver em `previous-month`, `quarter`, `semester` ou `year`, ele
  e convertido em intervalo de datas.

Aliases HTTP internos atualmente ignorados:

- `data_inicial`.
- `data_final`.
- `evento`.
- `cliente`.
- `contrato_codigo`.

Esses aliases nao sao contrato HTTP real deste endpoint e nao devem ser
promovidos durante a migracao sem decisao explicita.

Shape top-level de `data` observado:

- `total_despesa_prevista`.
- `totalDespesaPrevista`.
- `kpis`.
- `resultadoFinanceiro`.
- `cashDeficitAmount`.
- `pendingAccountsAmount`.
- `deficitCaixa`.
- `contasPendentesTotal`.
- `cashAvailability`.
- `revenueExpense`.
- `operationalRevenueExpense`.
- `expenseCategories`.
- `serviceRevenue`.
- `accountsPayable`.
- `overduePayablesAllTime`.
- `accountsReceivable`.
- `contractSummary`.
- `financialIndicators`.
- `financialGoals`.
- `cashEvolution`.
- `cashFlow`.
- `summary`.
- `filterOptions`.
- `meta`.

Campos condicionais presentes quando nao ha filtro `status`:

- `cashBasisRealizedFlow`.
- `competenceBasisRealizedFlow`.
- `realizedCashFlow`.
- `realizedCashFlowComparison`.

Secao `kpis`:

- `receitaTotal`.
- `receitaOperacional`.
- `despesasTotais`.
- `lucroLiquido`.
- `margemLiquida`.
- `custoVariavel`.
- `margemContribuicao`.
- `margemContribuicaoPercentual`.
- `lucroOperacionalEbit`.
- `resultadoFinanceiro`.
- `saldoCaixa`.

Shape de cada KPI:

- `value`.
- `metricValue`.
- `change`.
- `changePercent`.
- `changeLabel`.
- `changeDescription`.
- `unit` quando aplicavel.

Secao `resultadoFinanceiro`:

- `projetado`.
- `projectedAmount`.
- `realizado`.
- `realizedAmount`.
- `consolidadoProjetado`.
- `consolidatedProjectedAmount`.
- `consolidadoRealizado`.
- `consolidatedRealizedAmount`.
- `operacionalProjetado`.
- `operationalProjectedAmount`.
- `operacionalRealizado`.
- `operationalRealizedAmount`.
- `investimentosRealizado`.
- `investmentRealizedAmount`.
- `financiamentosRealizado`.
- `financingRealizedAmount`.
- `realizedSource`.
- `realizadoFonte`.
- `deficitCaixa`.
- `cashDeficitAmount`.
- `contasPendentes`.
- `pendingAccountsAmount`.

Secao `cashAvailability`:

- `initialCashAmount`.
- `saldoInicial`.
- `realizedInflowAmount`.
- `realizedOutflowAmount`.
- `availableCashAmount`.
- `cashAvailableAmount`.
- `caixaDisponivel`.
- `saldoCaixaDisponivel`.
- `finalCashAmount`.
- `currentAvailableCashAmount`.
- `accumulatedCashUntilDate`.
- `accumulatedAvailableCashAmount`.
- `cashAvailableUntilDate`.
- `currentCashAvailableUntilDate`.
- `periodRealizedAmount`.
- `differenceFromPeriodRealizedAmount`.
- `formula`.
- `accumulatedFormula`.
- `periodRealizedFormula`.
- `finalCashFormula`.

Secao `cashFlow`:

- `saldoInicial`.
- `initialCashAmount`.
- `entradas`.
- `inflowAmount`.
- `realizedInflowAmount`.
- `saidas`.
- `outflowAmount`.
- `realizedOutflowAmount`.
- `contasPendentes`.
- `pendingAccountsAmount`.
- `saldoFinal`.
- `resultadoFinanceiro`.
- `financialResultAmount`.
- `deficitCaixa`.
- `cashDeficitAmount`.
- `availableCashAmount`.
- `cashAvailableAmount`.
- `caixaDisponivel`.
- `saldoCaixaDisponivel`.
- `finalCashAmount`.
- `realizedFinalCashAmount`.
- `currentAvailableCashAmount`.
- `currentCashAvailableUntilDate`.
- `projectedFinalCashAmount`.
- `periodRealizedAmount`.
- `periodProjectedAmount`.
- `accumulatedCashUntilDate`.
- `accumulatedAvailableCashAmount`.
- `cashAvailableUntilDate`.
- `cashFlows`.
- `fluxosCaixa`.

Shape de `cashFlow.cashFlows` e `cashFlow.fluxosCaixa` por fluxo (`fco`,
`fci`, `fcf`):

- `code`.
- `codigo`.
- `inflowAmount`.
- `outflowAmount`.
- `financialResultAmount`.
- `realizedInflowAmount`.
- `realizedOutflowAmount`.
- `realizedFinancialResultAmount`.
- `entradas`.
- `saidas`.
- `resultadoFinanceiro`.

Secoes em lista:

- `revenueExpense[]`:
  - `month`;
  - `receitas`;
  - `revenueAmount`;
  - `despesas`;
  - `expenseAmount`.
- `operationalRevenueExpense[]`:
  - `month`;
  - `operationalRevenueAmount`;
  - `operationalExpenseAmount`.
- `expenseCategories[]`:
  - `name`;
  - `categoryName`;
  - `value`;
  - `expenseAmount`;
  - `percentage`;
  - `color`.
- `serviceRevenue[]`:
  - `service`;
  - `serviceName`;
  - `revenue`;
  - `revenueAmount`;
  - `percentage`;
  - `variation`.
- `accountsPayable[]`:
  - `description`;
  - `obligationDescription`;
  - `payableDescription`;
  - `contractCode`;
  - `contractName`;
  - `contractLabel`;
  - `eventId`;
  - `eventName`;
  - `eventNumber`;
  - `eventLabel`;
  - `clientId`;
  - `clientName`;
  - `dueDate`;
  - `value`;
  - `pendingValue`;
  - `plannedAmount`;
  - `paidAmount`;
  - `pendingAmount`;
  - `pendingPaymentAmount`;
  - `status`.
- `accountsReceivable[]`:
  - `description`;
  - `receivableDescription`;
  - `client`;
  - `clientName`;
  - `contractCode`;
  - `contractName`;
  - `contractLabel`;
  - `eventId`;
  - `eventName`;
  - `eventNumber`;
  - `eventLabel`;
  - `dueDate`;
  - `value`;
  - `pendingValue`;
  - `plannedAmount`;
  - `receivedAmount`;
  - `pendingAmount`;
  - `pendingReceivableAmount`;
  - `status`.
- `contractSummary[]`:
  - `service`;
  - `serviceName`;
  - `operationalEventsCount`;
  - `contracts`;
  - `contractCount`;
  - `value`;
  - `revenueAmount`.
- `financialIndicators[]`:
  - `title`;
  - `indicatorName`;
  - `value`;
  - `indicatorValue`;
  - `label`;
  - `indicatorDetail`;
  - `status`.
- `financialGoals[]`:
  - `title`;
  - `goalName`;
  - `current`;
  - `currentValue`;
  - `target`;
  - `targetValue`;
  - `percentage`;
  - `status`.
- `cashEvolution[]`:
  - `month`;
  - `value`;
  - `accumulatedFinancialResult`;
  - `accumulatedFinancialResultAmount`.

Secao `overduePayablesAllTime`:

- `count`.
- `amount`.
- `pendingAmount`.
- `referenceDate`.
- `dateBasis`.
- `overdueScope`.
- `periodIgnored`.
- `filters`.
- `readModel`.

Secao `summary`:

- `serviceRevenueTotalVariation`.
- `accountsPayableCount`.
- `accountsReceivableCount`.
- `overduePayablesAllTimeCount`.
- `overduePayablesAllTimeAmount`.
- `activeOperationalEventsCount`.
- `activeContractsCount`.
- `pendingAccountsCount`.

Secao `filterOptions`:

- `contracts`.
- `events`.
- `clients`.
- `statuses`.

Shape de `filterOptions.events[]`:

- `id`.
- `value`.
- `label`.
- `name`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `startDate`.
- `dataInicio`.
- `contractCode`.
- `contractName`.
- `contract`.
- `clientId`.
- `clientName`.
- `description`.
- `eventDateLabel`.
- `numero`.

Shape de `filterOptions.clients[]`:

- `id`.
- `value`.
- `label`.
- `name`.
- `clientId`.
- `clientName`.

Shape de `filterOptions.contracts[]`:

- `id`.
- `value`.
- `label`.
- `contractCode`.
- `contractName`.
- `contract`.
- `name`.
- `clientId`.
- `clientName`.
- `description`.
- `contractDescription`.

Shape de `filterOptions.statuses[]`:

- `value`.
- `label`.

Secao `meta`:

- `generatedAt`.
- `source`.
- `periodLabel`.
- `currency`.
- `nomenclature`.
- `cashFlowSemantics`.

Valores importantes de `meta`:

- `source` deve permanecer `backend`.
- `currency` deve permanecer `BRL`.

Dependencias principais:

- `montar_payload_dashboard_financial_overview_api`.
- `montar_dados_dashboard`.
- `querysets_dashboard_filtrados`.
- `calcular_totais_basicos_dashboard`.
- `calcular_totais_financeiros_dashboard`.
- `montar_movimentacoes_dashboard`.
- `montar_contas_vencidas_all_time_dashboard`.
- `montar_realized_cash_flow_dashboard`.
- `montar_comparativo_dashboard`.
- `montar_disponibilidade_caixa_dashboard`.
- `montar_payload_disponibilidade_caixa_dashboard`.
- `montar_resultado_financeiro_api`.
- `montar_receitas_despesas_por_mes`.
- `montar_receitas_despesas_operacionais_por_mes`.
- `montar_despesas_por_categoria`.
- `montar_resumo_receitas_servico`.
- `montar_contas_a_pagar_dashboard`.
- `montar_contas_a_receber_dashboard`.
- `montar_indicadores_financeiros`.
- `montar_metas_financeiras`.
- `montar_fluxo_caixa`.
- `montar_opcoes_filtros_dashboard_api`.
- `montar_metadados_nomenclatura_financeira`.

Totais e agregacoes calculadas:

- KPIs de receita, despesa, lucro, margem, EBIT, resultado financeiro e saldo.
- Resultado financeiro projetado e realizado.
- Resultado por FCO, FCI e FCF.
- Caixa inicial, caixa disponivel, caixa final e caixa acumulado.
- Entradas e saidas previstas e realizadas.
- Contas pendentes e deficit de caixa.
- Series mensais de receita/despesa e fluxo operacional.
- Categorias de despesa.
- Receita por servico e resumo por contrato.
- Contas a pagar, contas a receber e vencidos all-time.
- Comparacao de fluxo realizado em base caixa vs legado quando aplicavel.

Complexidade de queries:

- Alta.
- Ja existe historico de plano especifico de query count para este endpoint em
  `docs/PLANO_CORRECAO_QUERY_COUNT_FINANCIAL_OVERVIEW.md`.
- O teste atual relevante e
  `test_api_dashboard_financial_overview_mantem_queries_constantes`.
- A migracao nao pode aumentar query count nem mascarar N+1.

Testes existentes identificados:

- `test_filtros_dashboard_financial_overview_normalizam_params_do_frontend`.
- `test_api_dashboard_financial_overview_exige_permissao_da_tela`.
- `test_api_dashboard_financial_overview_nao_autenticada_retorna_json_401`.
- `test_api_dashboard_financial_overview_mantem_queries_constantes`.
- `test_api_dashboard_financial_overview_usa_mesma_regra_saldo_inicial`.
- `test_api_dashboard_financial_overview_retorna_arrays_vazios_sem_dados`.
- `test_api_dashboard_filtro_cliente_nao_mistura_custos_globais`.
- `test_api_dashboard_filtra_por_numero_de_orcamento_sem_contrato_operacional`.
- `test_api_dashboard_margem_contribuicao_percentual_zero_sem_receita`.
- `test_api_dashboard_variacoes_sem_periodo_anterior_sao_nulas`.
- `test_api_dashboard_variacoes_comparam_mes_anterior_com_dados_mesmo_com_gap`.
- `test_api_dashboard_receita_por_servico_em_queda_retorna_variacao_negativa`.
- `test_api_dashboard_variacao_com_prejuizo_menor_fica_positiva`.
- `test_api_dashboard_variacao_com_anterior_zero_retorna_nula`.
- `test_api_dashboard_variacoes_tecnicas_com_base_anterior_zero_sao_nulas`.
- `test_api_dashboard_saldo_caixa_reflete_fluxo_previsto_filtrado`.
- `test_api_dashboard_operational_revenue_expense_publica_serie_fco_mensal`.
- `test_api_dashboard_operational_revenue_expense_respeita_filtros_operacionais`.
- `test_api_dashboard_operational_revenue_expense_nao_usa_recorte_visual`.
- `test_api_dashboard_operational_revenue_expense_preserva_campos_antigos`.
- `test_api_dashboard_status_vencido_combina_com_periodo_personalizado`.
- `test_api_dashboard_publica_contas_vencidas_all_time_sem_alterar_periodo`.
- `test_api_dashboard_contas_vencidas_all_time_respeita_cliente_contrato_evento`.
- `test_api_dashboard_status_recebido_publica_contas_recebidas`.
- `test_api_dashboard_status_pago_mantem_card_de_pendencias_vazio`.

Lacunas identificadas para PM-32.2:

- `405` completo para `POST`, `PUT`, `PATCH` e `DELETE`.
- Headers JSON/no-store em `200`, `401` e `403`.
- Shape top-level `{"data": ...}`.
- Shape das secoes principais e itens de listas.
- Presenca/ausencia condicional dos campos `realizedCashFlow*`.
- Filtros HTTP aceitos.
- Confirmacao de que aliases HTTP internos continuam ignorados.
- Resposta sem dados mantendo arrays vazios e shape.
- Query count constante.
- Totais sensiveis de `overduePayablesAllTime`, `cashAvailability`,
  `cashFlow`, `resultadoFinanceiro` e `filterOptions`.

## Riscos especificos do dashboard financeiro

- Endpoint de alta complexidade e alto risco de regressao visual/financeira.
- Payload grande e consumido diretamente pelo frontend Next.js.
- Muitas secoes publicam aliases legados e camelCase simultaneamente.
- Campos condicionais dependem de filtros, especialmente `status`.
- Agregacoes combinam FCO, FCI, FCF, ledger, dados legados e posicao de caixa.
- `overduePayablesAllTime` ignora o periodo visual por contrato atual.
- `cashAvailability` e `cashFlow` compartilham regras de saldo inicial e caixa
  disponivel.
- DRF pode substituir `401`/`403` manuais por respostas padrao.
- DRF pode substituir `405` Django vazio por JSON padrao.
- Migrar usando `request.data` ou parsers DRF e desnecessario e pode alterar
  comportamento.
- OpenAPI tende a exigir schema formal, mas runtime tem prioridade.
- Qualquer otimizacao oportunista durante a migracao pode mudar query count,
  totais ou ordenacao.

## Guardrails

- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao alterar regra de negocio.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar models.
- Nao alterar signals.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Nao mexer em mes financeiro.
- Nao mexer em custos por evento.
- Nao mexer em obrigacoes.
- Nao mexer em lancamentos.
- Nao mexer em baixas.
- Nao mexer em outros endpoints financeiros.
- Reaproveitar `filtros_dashboard_financial_overview`.
- Reaproveitar `montar_payload_dashboard_financial_overview_api`.
- Reaproveitar selectors e serializers manuais atuais.
- Preservar `@require_GET` por fora da view DRF, ou mecanismo equivalente, para
  manter `405` Django padrao.
- Usar permissao local `AllowAny` se necessario para impedir que a permissao
  global do DRF substitua os `401`/`403` manuais.
- Priorizar paridade runtime sobre OpenAPI.
- Se algum comportamento atual parecer estranho, congelar como esta antes de
  migrar.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `GET` anonimo preserva `401` JSON/no-store.
- `GET` sem `caixa.view_evento` preserva `403` JSON/no-store.
- `GET` com `caixa.view_evento` retorna `200` JSON/no-store.
- `POST`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual.
- Shape top-level `{"data": ...}` preservado.
- Shape das secoes principais preservado.
- `total_despesa_prevista` e `totalDespesaPrevista` preservados.
- Campos condicionais `cashBasisRealizedFlow`, `competenceBasisRealizedFlow`,
  `realizedCashFlow` e `realizedCashFlowComparison` preservam presenca/ausencia.
- Filtros HTTP atuais preservados.
- Aliases HTTP internos atualmente ignorados continuam ignorados.
- Resposta sem dados preserva arrays vazios e shape.
- `overduePayablesAllTime` preservado.
- `cashAvailability` preservado.
- `cashFlow` preservado.
- `resultadoFinanceiro` preservado.
- `filterOptions` preservado.
- Query count constante preservado.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora de `api_dashboard_financial_overview` e alterado.

## Criterios de bloqueio

Parar imediatamente se:

- `405` mudar para JSON DRF padrao.
- `401` ou `403` mudarem.
- Headers JSON/no-store mudarem.
- Algum filtro HTTP mudar.
- Algum alias ignorado passar a filtrar.
- Campos `realizedCashFlow*` mudarem presenca/ausencia.
- Shape top-level mudar.
- Shape de secoes principais mudar.
- Algum total financeiro mudar.
- `overduePayablesAllTime` mudar sem decisao explicita.
- `cashAvailability` mudar.
- `cashFlow` mudar.
- `resultadoFinanceiro` mudar.
- `filterOptions` mudar.
- Query count piorar sem justificativa.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar mes financeiro, custos por evento, obrigacoes,
  lancamentos, baixas ou outro endpoint junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_dashboard_financial_overview`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em mes financeiro, custos por evento, obrigacoes, lancamentos,
  baixas ou outros endpoints financeiros.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar services.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco em codigo, mas o endpoint em si continua de alto risco de negocio
por consolidar o dashboard financeiro.

## Fases

### PM-32.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Filtros, permissoes, headers e shape principal identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como dashboard financeiro de alta complexidade.
- Decisao: migrar sozinho, sem agrupar com mes financeiro, custos por evento,
  obrigacoes, lancamentos, baixas ou outros endpoints financeiros.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-32.1:

- `caixa/views_dashboard.py`.
- `caixa/urls.py`.
- `caixa/permissions.py`.
- `caixa/serializers_dashboard.py`.
- `caixa/selectors_dashboard.py`.
- `caixa/selectors_dashboard_filtros.py`.
- `caixa/selectors_dashboard_totais.py`.
- `caixa/selectors_dashboard_movimentacoes.py`.
- `caixa/selectors_dashboard_contexto.py`.
- `caixa/utils_periodos.py`.
- `caixa/utils_contratos.py`.
- `docs/PLANO_CORRECAO_QUERY_COUNT_FINANCIAL_OVERVIEW.md`.
- `caixa/tests.py`.

### PM-32.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `GET` anonimo `401`.
- `GET` autenticado sem `caixa.view_evento` `403`.
- `GET` com `caixa.view_evento` retorna `200`.
- Headers JSON/no-store em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com:
  - `Allow: GET`;
  - body vazio;
  - `Content-Type: text/html; charset=utf-8`;
  - sem `Cache-Control`.
- Shape top-level `{"data": ...}`.
- Shape completo das secoes principais:
  - `kpis`;
  - `resultadoFinanceiro`;
  - `cashDeficitAmount`;
  - `pendingAccountsAmount`;
  - `deficitCaixa`;
  - `contasPendentesTotal`;
  - `cashAvailability`;
  - `revenueExpense`;
  - `operationalRevenueExpense`;
  - `expenseCategories`;
  - `serviceRevenue`;
  - `accountsPayable`;
  - `overduePayablesAllTime`;
  - `accountsReceivable`;
  - `contractSummary`;
  - `financialIndicators`;
  - `financialGoals`;
  - `cashEvolution`;
  - `cashFlow`;
  - `summary`;
  - `filterOptions`;
  - `meta`.
- Campos `total_despesa_prevista` e `totalDespesaPrevista`.
- Campos condicionais sem filtro de `status`:
  - `cashBasisRealizedFlow`;
  - `competenceBasisRealizedFlow`;
  - `realizedCashFlow`;
  - `realizedCashFlowComparison`.
- Ausencia/presenca condicional desses campos quando ha filtro `status`.
- Filtros preservados:
  - `startDate`;
  - `endDate`;
  - `period`;
  - `quickPeriod`;
  - `eventId`;
  - `clientId`;
  - `contractCode`;
  - `status`.
- Aliases HTTP internos atualmente ignorados continuam ignorados:
  - `data_inicial`;
  - `data_final`;
  - `evento`;
  - `cliente`;
  - `contrato_codigo`.
- Resposta sem dados mantem arrays vazios e shape.
- Query count constante preservado.
- Totais e secoes sensiveis preservadas:
  - `overduePayablesAllTime`;
  - `cashAvailability`;
  - `cashFlow`;
  - `resultadoFinanceiro`;
  - `filterOptions`.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de dashboard financial overview>
```

### PM-32.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_dashboard_financial_overview` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_GET` por fora, ou equivalente, para manter `405` Django
  padrao.
- Preservar permissao manual `caixa.view_evento`.
- Preservar `401`/`403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar filtros atuais.
- Preservar aliases ignorados como ignorados.
- Preservar shape, totais, query count e secoes condicionais.
- Reaproveitar selectors e serializers manuais atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em mes financeiro, custos por evento, obrigacoes, lancamentos,
  baixas ou outros endpoints financeiros.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de dashboard financial overview>
```

### PM-32.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de dashboard financial overview>
python manage.py test <testes relacionados existentes de dashboard>
python manage.py test
```

Validar:

- Testes focados de dashboard financeiro passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui `GET /api/dashboard/financial-overview/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.
- Nenhum total financeiro mudou.
- Query count constante foi preservado.

### PM-32.5 - Encerramento

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

### PM-32.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- Endpoint permanece Django puro antes da migracao.
- Permissao atual confirmada: `caixa.view_evento`.
- Metodo aceito confirmado: `GET`.
- `405` Django padrao confirmado para metodos nao permitidos.
- Shape principal do payload identificado.
- Dependencias principais identificadas.
- Endpoint classificado como alto risco por consolidar dashboard financeiro,
  agregacoes FCO/FCI/FCF, caixa, vencidos all-time, filtros e metadados.
- Decisao: migrar sozinho, sem agrupar com mes financeiro, custos por evento,
  obrigacoes, lancamentos, baixas ou outros endpoints financeiros.
- Nenhuma alteracao de arquivo feita na PM-32.1.

### PM-32.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados:

- `test_api_dashboard_financial_overview_preserva_auth_permissao_e_headers`.
- `test_api_dashboard_financial_overview_metodos_nao_permitidos_preservam_405`.
- `test_api_dashboard_financial_overview_preserva_shape_secoes_e_condicionais`.
- `test_api_dashboard_financial_overview_preserva_filtros_e_aliases_ignorados`.

Contrato congelado:

- `GET` anonimo retorna `401` JSON/no-store.
- `GET` autenticado sem `caixa.view_evento` retorna `403` JSON/no-store.
- `GET` com `caixa.view_evento` retorna `200` JSON/no-store.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` Django padrao com
  `Allow: GET`, body vazio, `Content-Type: text/html; charset=utf-8` e sem
  `Cache-Control`.
- Shape top-level `{"data": ...}` preservado.
- Shape das secoes sensiveis preservado.
- Campos condicionais `cashBasisRealizedFlow`, `competenceBasisRealizedFlow`,
  `realizedCashFlow` e `realizedCashFlowComparison` presentes sem `status` e
  ausentes com `status`.
- Filtros HTTP canonicos preservados.
- Aliases internos `data_inicial`, `data_final`, `evento`, `cliente` e
  `contrato_codigo` continuam ignorados.
- `overduePayablesAllTime`, `cashAvailability`, `cashFlow`,
  `resultadoFinanceiro` e `filterOptions` preservados por shape.
- Query count constante continua coberto por teste existente.

Comandos executados:

```bash
python manage.py check
python manage.py test caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_preserva_auth_permissao_e_headers caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_preserva_shape_secoes_e_condicionais caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_preserva_filtros_e_aliases_ignorados caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_mantem_queries_constantes caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_retorna_arrays_vazios_sem_dados
```

Resultado:

- `python manage.py check` passou sem issues.
- 6 testes focados passaram.
- Nenhuma view foi migrada nesta fase.

### PM-32.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_dashboard.py`.

Como a view foi migrada:

- Somente `api_dashboard_financial_overview` foi convertida para DRF.
- A view passou a usar `@api_view(["GET"])`.
- Foi usada permissao local `@permission_classes([AllowAny])` para preservar os
  `401`/`403` manuais e impedir que a permissao global do DRF substitua o
  contrato atual.
- `@require_GET` foi preservado por fora para manter o `405` Django padrao.
- `Response` foi usado apenas na borda, convertendo os `JsonResponse` manuais
  existentes em `Response` sem alterar payload, status ou headers relevantes.
- `filtros_dashboard_financial_overview` e
  `montar_payload_dashboard_financial_overview_api` foram reaproveitados.
- Selectors e serializers manuais atuais foram preservados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- Mes financeiro, custos por evento, obrigacoes, lancamentos, baixas e outros
  endpoints financeiros nao foram alterados.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_preserva_auth_permissao_e_headers caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_preserva_shape_secoes_e_condicionais caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_preserva_filtros_e_aliases_ignorados caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_mantem_queries_constantes caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_retorna_arrays_vazios_sem_dados
```

Resultado:

- `python manage.py check` passou sem issues.
- `python manage.py spectacular --validate` passou.
- OpenAPI passou a incluir `GET /api/dashboard/financial-overview/`.
- 6 testes focados passaram.
- Nenhuma mudanca de contrato runtime foi detectada.

### PM-32.4 - Validacao completa

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
- `python manage.py test caixa.tests.FiltrosHtmlTests`: 408 testes passaram.
- `python manage.py test`: 777 testes passaram.
- Logs esperados de CSRF apareceram em testes que validam bloqueio sem token.
- OpenAPI inclui `GET /api/dashboard/financial-overview/`.
- Nenhum total financeiro mudou nos testes.
- `overduePayablesAllTime`, `cashAvailability`, `cashFlow`,
  `resultadoFinanceiro`, `filterOptions` e campos condicionais permaneceram
  cobertos e preservados.
- Query count constante permaneceu coberto e verde.

### PM-32.5 - Encerramento

Status: concluida.

Arquivos alterados na PM-32:

- `caixa/tests.py`.
- `caixa/views_dashboard.py`.
- `docs/PLANO_PM32_MIGRACAO_DASHBOARD_FINANCIAL_OVERVIEW_DRF.md`.

Resumo final:

- PM-32.2 criou testes de paridade antes da migracao.
- PM-32.3 migrou somente `api_dashboard_financial_overview` para DRF.
- A URL `/api/dashboard/financial-overview/` e o nome de rota
  `caixa:api_dashboard_financial_overview` foram preservados.
- `@require_GET` foi preservado para manter o `405` Django padrao.
- Permissao manual `caixa.view_evento` foi preservada.
- `401` e `403` atuais foram preservados.
- Filtros HTTP atuais foram preservados.
- Aliases internos ignorados continuaram ignorados.
- Shape completo, totais, query count e campos condicionais foram preservados.
- Nenhum frontend, settings, CORS, CSRF global ou auth global foi alterado.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- Nenhum endpoint fora do dashboard financial overview foi migrado.

Riscos residuais:

- O endpoint continua sendo de alto risco por consolidar dashboard financeiro,
  FCO, FCI, FCF, caixa, vencidos all-time, filtros e metadados.
- O schema OpenAPI permanece generico (`object`) por escolha consciente de
  preservar runtime e nao introduzir serializers DRF nesta PM.
- Os testes cobrem contrato, headers, filtros, aliases ignorados, shape,
  query count e secoes sensiveis, mas mudancas futuras em agregacoes financeiras
  ainda devem ser avaliadas com revisao de negocio.

Status final:

- PM-32 concluida.
- Pronta para revisao e commit local manual.
