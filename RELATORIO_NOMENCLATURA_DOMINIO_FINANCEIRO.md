# Relatorio de nomenclatura do dominio financeiro

Atualizado em: 2026-05-22

Este relatorio resume as decisoes de nomenclatura aplicadas no backend Django e
nos contratos consumidos pelo frontend Next.js. O objetivo e manter clareza de
negocio sem quebrar models, migrations, APIs, admin, templates ou testes.

Este relatorio apoia a nomenclatura dos contratos. O roteiro oficial para
concluir a arquitetura financeira premium/canonical-first fica em
`PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md`, secao `Plano mestre para conclusao da
arquitetura premium`.

## Tabela de padronizacao

| Nome atual/legado | Nome canonico sugerido/aplicado | Motivo | Impacto tecnico |
| --- | --- | --- | --- |
| Em aberto | Contas pendentes | Representa contas ainda nao liquidadas. | Labels e agregados novos usam `contasPendentes`; aliases antigos continuam onde necessario. |
| Falta cobrir | Deficit de caixa | Define falta de caixa/cobertura. | APIs expõem `deficitCaixa`; `falta_cobrir` fica como alias transicional. |
| Saldo previsto | Resultado financeiro projetado/previsto | Evita confundir saldo bancario com resultado do fluxo. | Selectors e serializers publicam `resultado_financeiro_*`; `saldo_*` permanece como alias. |
| Saldo realizado | Resultado financeiro realizado | Distingue realizado de projecao. | Ledger e dashboard usam `resultadoFinanceiro`; aliases preservados. |
| Numero em orcamento/evento | Contrato | O campo identifica contrato no contexto operacional. | Admin/formulario exibem `Contrato`; campo fisico `numero` fica ate `financeiro-v3`. |
| total_em_aberto | total_contas_pendentes | Agregado de pendencias financeiras. | Mantido como alias tecnico em selectors/templates antigos. |
| saldo_em_aberto | valor_pendente_pagamento | Valor restante de uma obrigacao a pagar. | Campo legado preservado em models com aliases semanticos. |
| origem_pagamento | origem | A origem da despesa agora e explicita: manual, custo de servico ou custo extra. | Alias registrado nos metadados de nomenclatura. |
| Pagamento especifico por origem | BaixaFinanceira | Baixa representa o ato financeiro realizado, seja pagamento ou recebimento. | Nova camada canonica em paralelo; models legados ainda operam. |
| Pagamento alocado | BaixaFinanceiraAlocacao | Permite uma baixa liquidar uma ou mais obrigacoes. | Camada canonica sincronizada e auditavel. |
| Fonte de dados generica | dataSource/readModelSource | Deixa claro se a leitura veio do legado ou da modelagem canonica. | Next solicita `dataSource=canonical`; API informa leitura legada segura quando necessario. |
| Status de leitura das obrigacoes | readModelStatus | Objeto canonico para label, detalhe, tom, motivo, fonte efetiva e paridade canonica. | Next deve consumir este objeto primeiro; campos planos permanecem como aliases transicionais. |
| Diagnostico de fonte de leitura | readModelStatusDiagnostics | Concentra leitura solicitada, leitura efetiva, leitura legada e paridade canonica em um contrato compacto. | Next usa o diagnostico para tooltip/hover; `canonicalReadiness` fica como detalhe tecnico transicional. |
| Motivo tecnico da leitura legada | readModelStatusReason | Evita que o frontend dependa do nome legado `canonicalFallbackReason`. | `canonicalFallbackReason` e `fallbackReason` continuam como aliases temporarios de compatibilidade. |
| Motivo da leitura legada no diagnostico | legacyReadReason | Nome claro para o motivo interno de a leitura efetiva permanecer no legado. | `fallbackReason` permanece apenas como alias transicional dentro do diagnostico. |
| Etapa de rollback validateLegacyFallback | validateLegacyRead | Descreve a validacao da leitura legada apos desligar canonical-first, sem usar fallback como nome de negocio. | O checklist operacional publica `legacyStep` com o nome antigo para compatibilidade. |
| Totais soltos de FCI | projectedInvestmentFlow/realizedInvestmentFlow | Agrupa entradas, saidas e resultado financeiro do FCI em objetos claros. | `/api/fci/` preserva `totais` antigos e publica objetos canonicos para Next.js. |
| Grupos FCI em snake_case | aliases camelCase em grupos de categoria | Alinha grupos FCI ao formato dos itens e ao contrato esperado pelo Next.js. | `/api/fci/` preserva `grupos_categoria`/`itens` e adiciona `category`, `categoryLabel`, `quantity` e `items`. |
| Subtotais FCI em snake_case | aliases camelCase em grupos de categoria | Evita que o Next leia subtotais por `subtotal_previsto_*` e `subtotal_resultado_*`. | `/api/fci/` preserva os campos antigos e adiciona `subtotalPlannedInflowAmount`, `subtotalRealizedInflowAmount`, `subtotalProjectedFinancialResult`, etc. |
| Itens/grupos FCF em snake_case | aliases camelCase em parcelas, movimentacoes e grupos | Alinha FCF ao formato ja usado por FCI e Obrigacoes. | `/api/fcf/` preserva campos antigos e adiciona `plannedAmount`, `pendingAmount`, `installmentLabel`, `debts`, `installments`, etc. |
| Dividas FCF em portugues | aliases camelCase em dividas | Evita que o Next consuma `descricao`, `credor`, `tipo`, `data_contratacao` e `valor_contratado` diretamente. | `/api/fcf/` preserva campos antigos e adiciona `description`, `creditor`, `type`, `contractedDate`, `contractedAmount`, etc. |
| Colecoes em portugues | aliases camelCase de colecoes | Evita que o Next dependa de `investimentos`, `grupos_categoria`, `contas_a_pagar`, `movimentacoes_financiamento` e similares. | APIs preservam colecoes antigas e adicionam `investments`, `categoryGroups`, `creditorGroups`, `receivables`, `payables`, `movements`, etc. |
| Blocos top-level em portugues | filters/filterOptions/totals/statistics | Padroniza os envelopes auxiliares de FCI, FCF e Mes Financeiro com os contratos ja usados nas APIs Next-first. | APIs preservam `filtros`, `opcoes`, `totais` e `estatisticas` como compatibilidade. |
| Fonte de escrita generica | writeModelSource | Diferencia adapter legado sincronizado de canonical-first. | API de baixas e auditorias expõem `legacyAdapterSynced` e `canonicalFirst`. |
| Tipo da conta | obligationType | Distingue conta a pagar e conta a receber. | API publica `obligationType`; `A pagar` segue como padrao e `A receber` fica opt-in por `ReceitaOperacional`, entradas FCI e entradas FCF, tanto no canonico quanto na leitura legada; aliases `tipoObrigacao` e `tipo_obrigacao` ficam transicionais. |
| Tipo liquidavel por adapter | supportedObligationTypes | Evita o frontend habilitar baixa nativa para tipo errado. | Contrato de baixa e adapters canonicos publicam `["pagar"]` hoje. |
| Totais soltos de FCF | projectedFinancingFlow/realizedFinancingFlow | Aproxima FCF do contrato ja usado em FCI, com entradas, saidas e resultado financeiro em objetos claros. | `/api/fcf/` preserva `totais` antigos e adiciona objetos canonicos para Next.js. |
| Totais soltos do mes financeiro | financialResult | Agrupa resultado projetado, realizado, pendente e deficit de caixa em um contrato claro. | `/api/mes-financeiro/` preserva `totais` antigos e adiciona objeto canonico para Next.js. |
| Itens do mes financeiro em snake_case | aliases camelCase em receitas, contas e movimentacoes | Facilita consumo pelo Next.js sem depender de `descricao`, `valor_*`, `falta_cobrir_*` e similares. | `/api/mes-financeiro/` preserva campos antigos e adiciona `description`, `plannedAmount`, `pendingAmount`, `accumulatedFinancialResult`, etc. |
| Opcoes do Mes Financeiro em portugues | aliases camelCase/value-label em filterOptions | Permite que o Next consuma selects sem depender de `contratos`, `eventos`, `clientes`, `origens`, `status`, `valor` e `rotulo`. | `/api/mes-financeiro/` preserva listas antigas e adiciona `contracts`, `events`, `clients`, `sources`, `statuses`, `label`, `name`, `value`, etc. |
| Opcoes FCI/FCF em portugues | aliases camelCase/value-label em filterOptions | Mantem o mesmo padrao de selects do Mes Financeiro nas telas auxiliares de investimento e financiamento. | `/api/fci/` e `/api/fcf/` preservam listas antigas e adicionam `categories`, `flowTypes`, `debtTypes`, `installmentStatuses`, `financingCategories`, etc. |
| Dimensao operacional incompleta | contractLabel/eventLabel/clientId/clientName | Evita o frontend inferir cliente e labels a partir de contrato/evento. | Serializers compartilhados de FCI/FCF preservam campos antigos e adicionam labels/cliente como aliases canonicos. |
| Ledger com dimensao parcial | contractLabel/eventLabel/clientId/clientName e aliases transicionais | Deixa lancamentos financeiros prontos para tabelas e filtros do Next.js sem inferencia manual. | `/api/lancamentos-financeiros/` preserva campos antigos e adiciona labels/aliases de filtros e dimensao operacional. |
| AJAX de parcelas usando saldo_em_aberto | pendingPaymentAmount/installmentLabel/dueDate | Evita que o admin legado dependa de `saldo_em_aberto` para preencher pagamento. | Endpoint `parcelas-por-divida/` mantem aliases antigos e adiciona campos canonicos para o JS. |
| Baixas canonicas com dimensao parcial | contractLabel/eventLabel/clientName e filtros camelCase | Mantem baixas/alocacoes alinhadas ao contrato operacional do ledger e das obrigacoes. | `/api/canonical-settlements/` adiciona aliases em itens, alocacoes e filtros, sem alterar reconciliacao. |
| Mocks do Next sem contexto operacional completo | DashboardEntityFilterOption expandido | Evita desenvolvimento local contra mock menos expressivo que o backend real. | `dashboardOverviewMock` e respostas vazias acompanham aliases de contrato/evento/cliente e filtros do ledger. |
| Baixar saldo restante | Baixar valor pendente | Evita ambiguidade entre saldo de caixa e valor pendente da obrigacao. | Label visual ajustado no Next; payload tecnico preservado como compatibilidade. |
| Opcoes globais do dashboard com contexto parcial | filterOptions com name/clientId/clientName/eventId/eventName | Mantem o painel inicial do Next alinhado ao contrato das demais APIs financeiras. | Dashboard overview adiciona campos semanticos e ajusta `select_related` para nao gerar consultas extras. |
| Catalogo de nomenclatura incompleto | termos canonicos e aliases operacionais registrados | Permite que o frontend consulte metadados coerentes com os payloads reais. | `constants_nomenclatura.py` inclui labels/descricoes para labels operacionais, valor pendente e parcela. |
| Aliases de filtros fora do catalogo | startDate/endDate/source/sourceId/settlementStatus/search | Evita divergencia entre filtros publicados e metadados de nomenclatura. | `constants_nomenclatura.py` inventaria aliases como `data_inicial`, `situacao`, `origem`, `source_id`, `source_detail`, `fluxo`, `natureza` e `busca`. |
| Mock de nomenclatura antigo | mock alinhado ao catalogo backend | Evita que o fallback local do Next exponha metadados mais pobres que a API real. | `dashboardOverviewMock.meta.nomenclature` inclui termos e aliases de filtros/dimensoes recentes. |
| Contas resumidas com value/pendingValue | plannedAmount/paidAmount/receivedAmount/pendingAmount | Reduz ambiguidade nos cards/tabelas do dashboard inicial. | `accountsPayable` e `accountsReceivable` preservam campos antigos e adicionam aliases financeiros claros. |
| Resumo de contratos com service/contracts/value | serviceName/contractCount/revenueAmount | Explicita que o valor do resumo representa receita por servico e quantidade operacional. | `contractSummary` preserva campos antigos e adiciona aliases consumidos pelo widget e exportacao. |
| Categorias/receitas do dashboard com name/value/service/revenue | categoryName/expenseAmount/serviceName/revenueAmount | Evita campos genericos em graficos e tabelas do dashboard inicial. | `expenseCategories` e `serviceRevenue` preservam campos antigos e adicionam aliases consumidos por componentes, totais e exportacao. |
| Serie mensal com receitas/despesas | revenueAmount/expenseAmount | Padroniza valores mensais no contrato camelCase usado pelo Next.js. | `revenueExpense` preserva `receitas`/`despesas` e adiciona aliases consumidos pelo grafico e exportacao. |
| Evolucao de caixa com value | accumulatedFinancialResult | Explicita que a barra representa resultado financeiro acumulado, nao um valor generico. | `cashEvolution` preserva `value` e adiciona alias consumido pelo grafico. |
| Fluxo de caixa com saldoInicial/entradas/saidas/saldoFinal | initialCashAmount/inflowAmount/outflowAmount/financialResultAmount/cashDeficitAmount | Padroniza o contrato do widget de fluxo com nomes financeiros camelCase. | `cashFlow` preserva nomes antigos e adiciona aliases consumidos por normalizador, widget e exportacao. |
| Resultado financeiro com projetado/realizado em portugues | projectedAmount/realizedAmount/consolidatedRealizedAmount/pendingAccountsAmount | Padroniza o resumo de resultado financeiro para consumo Next-first sem remover os nomes atuais. | `resultadoFinanceiro` preserva campos antigos e adiciona aliases camelCase preenchidos pelo backend e normalizador. |
| Totais do ledger com entradas/saidas | inflowAmount/outflowAmount/financialResultAmount | Alinha o ledger e o fluxo realizado ao mesmo contrato camelCase do dashboard. | `/api/lancamentos-financeiros/` e `realizedCashFlow` preservam campos antigos e adicionam aliases nos totais e subtotais FCO/FCI/FCF. |
| Contas resumidas com description/client | obligationDescription/clientName | Evita que o Next dependa de nomes genericos para conta pendente e cliente da conta a receber. | `accountsPayable` e `accountsReceivable` preservam campos antigos e adicionam aliases consumidos por tabelas, normalizador e exportacao. |
| Indicadores/metas com title/value/current/target | indicatorName/indicatorValue/indicatorDetail/goalName/currentValue/targetValue | Separa nomes de componente visual dos nomes de contrato de negocio. | `financialIndicators` e `financialGoals` preservam campos antigos e adicionam aliases consumidos por widgets e mock. |
| KPIs com value/change/changeLabel | metricValue/changePercent/changeDescription | Evita nomes de componente em metricas financeiras principais. | `kpis` preserva campos antigos e adiciona aliases consumidos por cards, normalizador, mock e exportacao. |
| Opcoes de filtro com description generico | contractDescription/eventDateLabel | Deixa claro se o texto auxiliar representa cliente do contrato ou data do evento. | `filterOptions.contracts/events` preservam `description` e adicionam aliases para o Next.js. |
| Opcoes de filtro com name generico | contractName/clientName | Deixa claro se o nome pertence ao contrato operacional ou ao cliente. | Dashboard, Mes Financeiro, Obrigacoes e serializers compartilhados preservam `name`/`nome` e adicionam aliases camelCase. |
| Itens de obrigacoes com contexto parcial | contractName/contractLabel/eventLabel | Evita que a tela de obrigacoes e exportacao exibam somente codigo do contrato ou nome cru do evento. | Leitura legada e canonica publicam aliases operacionais sem alterar filtros, conciliacao ou totais. |
| Itens do ledger com amount/description | ledgerAmount/ledgerDescription | Deixa claro que o valor e a descricao pertencem ao lancamento financeiro realizado. | `/api/lancamentos-financeiros/` preserva `amount`/`description` e adiciona aliases consumidos pela tela de obrigacoes. |
| Baixas canonicas com amount/description | settlementAmount/settlementDescription | Deixa claro que o valor e a descricao pertencem a uma baixa financeira canonica. | API de baixas canonicas e contexto de liquidacao preservam `amount`/`description` e adicionam aliases transicionais. |
| Alocacoes de baixa com description | obligationDescription | Explicita que a descricao da alocacao representa a obrigacao liquidada. | Alocacoes canonicas preservam `description` e adicionam `obligationDescription` com contexto operacional completo. |
| Descricoes FCI/FCF genericas | investmentDescription/debtDescription/financingMovementDescription | Explicita se a descricao pertence a investimento, divida ou movimentacao de financiamento. | APIs FCI/FCF preservam `description` e adicionam aliases especificos para o Next.js. |
| Descricoes do Mes Financeiro genericas | receivableDescription/payableDescription/movementDescription | Explicita se a descricao pertence a conta a receber, conta a pagar ou movimentacao consolidada. | `/api/mes-financeiro/` preserva `description` e adiciona aliases especificos por lista. |
| Itens de obrigacoes com description | obligationDescription | Explicita que a descricao do item representa uma obrigacao financeira. | APIs de obrigacoes preservam `description`; dashboard e Next passam a preferir `obligationDescription`/`payableDescription`. |
| Contexto operacional do dashboard por codigo cru | contractLabel/eventLabel | Exibe contrato/evento com label de negocio quando disponivel. | Next preserva fallbacks antigos e prioriza aliases operacionais nos resumos derivados de obrigacoes. |

## Arquivos principais alterados

- `caixa/models.py`
- `caixa/admin.py`
- `caixa/constants_nomenclatura.py`
- `caixa/contracts_obrigacoes.py`
- `caixa/serializers_obrigacoes.py`
- `caixa/serializers_modelagem_canonica.py`
- `caixa/serializers_lancamentos.py`
- `caixa/serializers_dimensoes_operacionais.py`
- `caixa/serializers_financiamentos.py`
- `caixa/serializers_investimentos.py`
- `caixa/serializers_mes_financeiro.py`
- `caixa/serializers_utils.py`
- `caixa/selectors_obrigacoes.py`
- `caixa/selectors_obrigacoes_canonicas.py`
- `caixa/selectors_opcoes_filtros.py`
- `caixa/services_modelagem_canonica.py`
- `caixa/services_escrita_canonica.py`
- `caixa/signals.py`
- `caixa/static/caixa/js/pagamento_parcela_admin.js`
- `caixa/tests.py`
- comandos em `caixa/management/commands/`
- `features/financial-dashboard/components/financial-obligations-view.tsx`
- `features/financial-dashboard/services/financial-dashboard-service.ts`
- `features/financial-dashboard/utils/dashboard-export.ts`
- `features/financial-dashboard/utils/financial-obligations-read-model.ts`
- `lib/data/mock-data.ts`
- `lib/types/dashboard.ts`

## Aliases temporarios

- `numero` -> `contrato`/`contractCode`
- `contract` -> `contractCode`
- `saldoCaixa` e `saldoFinal` -> `resultadoFinanceiro`
- `saldo_previsto` -> `resultado_financeiro_previsto`
- `saldo_realizado` -> `resultado_financeiro_realizado`
- `saldo_em_aberto` -> `valor_pendente_pagamento`
- `total_em_aberto` -> `total_contas_pendentes`
- `subtotal_em_aberto` -> `subtotal_contas_pendentes`
- `falta_cobrir` -> `deficit_caixa`
- `fonteDados`/`fonte_dados` -> `dataSource`
- `canonicalFallbackReason`/`fallbackReason` -> `readModelStatusReason`/`legacyReadReason`
- `validateLegacyFallback` -> `validateLegacyRead`
- `fonteEscrita`/`fonte_escrita` -> `writeModelSource`
- `tipoObrigacao`/`tipo_obrigacao` -> `obligationType`
- `data_inicial` -> `startDate`
- `data_final` -> `endDate`
- `contrato_operacional`/`contrato_operacional_id` -> `contractId`
- `contrato_codigo` -> `contractCode`
- `contratoOperacionalLabel`/`contrato_operacional_label` -> `contractLabel`
- `evento`/`evento_id` -> `eventId`
- `evento_nome` -> `eventName`
- `evento_numero` -> `eventNumber`
- `eventoLabel`/`evento_label` -> `eventLabel`
- `cliente`/`cliente_id` -> `clientId`
- `cliente_nome` -> `clientName`
- `clienteLabel`/`cliente_label` -> `clientLabel`
- `valor_pendente_pagamento` -> `pendingPaymentAmount`
- `rotulo_parcela` -> `installmentLabel`
- `origem` -> `source`/`origin`
- `fluxo` -> `cashFlowGroup`
- `natureza` -> `nature`
- `situacao` -> `settlementStatus`
- `pago` -> `liquidado` em filtros da tela de obrigacoes
- `busca` -> `search`
- `realizedCashFlow` -> `cashBasisRealizedFlow`
- `filtros` -> `filters`
- `opcoes` -> `filterOptions`
- `totais` -> `totals`
- `estatisticas` -> `statistics`

## Pontos de atencao para o Next.js

- Consumir `contractId` e `contractCode`; tratar `contract` como alias legado.
- Consumir `readModelStatus` como contrato preferencial de fonte de leitura.
- Usar `dataSourceRequested`, `dataSourceActual`, `readModelStatusReason`, `readModelStatusLabel`, `readModelStatusDetail`, `readModelStatusTone` e `readModelStatusDiagnostics` apenas como aliases/fallbacks transicionais.
- No Next.js, usar `getFinancialObligationReadModelStatus` para badge e exportacoes, evitando remontar labels/motivos de leitura em componentes isolados.
- Exibir alerta operacional quando `dataSource=canonical` cair para legado, usando `Leitura legada: modelagem canonica incompleta` quando a paridade canonica ainda nao estiver pronta.
- Usar `obligationType` para diferenciar `A pagar` e `A receber`.
- Considerar que `/api/obrigacoes-financeiras/` usa `A pagar` como padrao e aceita `obligationType=receber` de forma opt-in por `ReceitaOperacional`, `Investimento` com `tipo_fluxo=entrada` e `FinanciamentoMovimentacao` com `tipo_fluxo=entrada`.
- A tela de obrigacoes financeiras exibe esse escopo como `Escopo: A pagar` ou `Escopo: A receber`, evitando leitura operacional ambigua.
- A API normaliza `obligationType` e aliases; no legado, requests de `A receber` retornam apenas origens de entrada e podem retornar vazio quando nao houver contas a receber.
- O cliente Next.js dessa tela envia `obligationType=pagar` por padrao para preservar o escopo atual quando a API evoluir.
- Para `A receber`, as origens publicadas sao `receita_operacional`, `investimento` e `financiamento_movimentacao`; receita tem atalho para a tela antiga de receitas e todas as origens mantem atalho de admin quando disponivel.
- As opcoes de origem da tela de obrigacoes sao filtradas por `obligationType`, evitando misturar fontes de entrada com fontes de contas a pagar.
- `filterOptions` da tela de obrigacoes tambem publica `contracts`, `events` e `clients` para alimentar os selects globais de contrato, evento e cliente.
- O filtro global de status da tela de obrigacoes usa `settlementStatuses`; `pago` e mantido apenas como alias de entrada para `liquidado`.
- No Next.js, `DashboardFilterStatus` separa o status aceito pelo filtro compartilhado do `DashboardStatus` generico dos indicadores.
- Quando `settlementStatus` local estiver ativo, o Next nao envia `status` global para evitar conflito de liquidacao.
- Labels e opcoes de obrigacoes no Next ficam centralizados em `features/financial-dashboard/constants/financial-obligations.ts`.
- O frontend deve tratar `filterOptions` como contrato ativo: se tipo ou origem selecionados deixarem de existir para o escopo atual, a tela volta para uma combinacao segura e reinicia a paginacao.
- `filters` publica aliases em portugues (`data_inicial`, `data_final`, `contrato_operacional`, `contrato_operacional_id`, `contratoOperacionalLabel`, `contrato_operacional_label`, `evento`, `evento_id`, `eventoLabel`, `evento_label`, `cliente`, `cliente_id`, `clienteLabel`, `cliente_label`, `origem`, `fluxo`, `natureza`, `situacao`, `busca`) como transicao; o Next deve preferir os nomes canonicos, usando aliases como fallback.
- A tela de obrigacoes mostra badges dos filtros aplicados pela API, usando aliases apenas como fallback e labels de `filterOptions` quando houver.
- A fila de divergencias tambem carrega `obligationType`, evitando agrupar futuramente contas a pagar e a receber no mesmo diagnostico operacional.
- A tela de divergencias mostra o tipo do grupo para manter a leitura alinhada ao CSV e ao contrato da API.
- O clique `Ver` da fila preserva internamente o tipo do grupo para evitar troca acidental de escopo em futuras telas com `A receber`.
- O filtro visual `Tipo` mostra `A pagar` diretamente enquanto a visao continua restrita a contas a pagar.
- Usar `supportedObligationTypes` antes de habilitar baixa nativa.
- Usar `writeModelSource` para auditar baixas `legacyAdapterSynced` versus `canonicalFirst`.
- Exportacoes CSV de obrigacoes e fila de divergencias carregam escopo, fonte de leitura, periodo, labels e ids de dimensoes operacionais e demais filtros ativos para conferencias fora da tela.
- Exportacoes CSV de obrigacoes e fila de divergencias usam `readModelStatus` via helper central, incluindo prontidao canonica e totais de paridade.
- Para FCI, preferir `projectedInvestmentFlow` e `realizedInvestmentFlow` em vez de remontar resultado financeiro a partir de `saldo_previsto_fci`/`saldo_realizado_fci`.
- Para grupos de FCI, preferir `category`, `categoryLabel`, `quantity`, `items` e aliases de subtotal em camelCase, mantendo `categoria`, `categoria_nome`, `quantidade`, `itens` e `subtotal_*` como compatibilidade.
- Para FCF, preferir `projectedFinancingFlow` e `realizedFinancingFlow` em vez de remontar resultado financeiro a partir de `saldo_previsto_fcf`/`saldo_realizado_fcf`.
- Para itens, dividas e grupos de FCF, preferir aliases camelCase (`description`, `creditor`, `installmentLabel`, `pendingPaymentAmount`, `plannedAmount`, `pendingAmount`, `flowType`, `debts`, `installments`) e usar snake_case apenas como compatibilidade.
- Para Mes Financeiro, preferir `financialResult` em vez de consumir diretamente `saldo_previsto`, `saldo_realizado` ou `falta_cobrir`.
- Para itens do Mes Financeiro, preferir aliases camelCase (`description`, `plannedAmount`, `pendingAmount`, `accumulatedFinancialResult`, `accumulatedCashDeficit`) e usar snake_case como compatibilidade.
- Para opcoes do Mes Financeiro, preferir `filterOptions.contracts`, `filterOptions.events`, `filterOptions.clients`, `filterOptions.sources` e `filterOptions.statuses`; usar `contratos`, `eventos`, `clientes`, `origens`, `status`, `valor` e `rotulo` apenas como compatibilidade.
- Para opcoes de FCI/FCF, preferir listas camelCase com `value`/`label`; manter `valor`/`rotulo` e nomes em portugues como fallback transicional.
- Para itens de FCI/FCF, consumir `contractLabel`, `eventLabel`, `clientId` e `clientName` quando precisar exibir contexto operacional; evitar inferir cliente a partir de contrato no frontend.
- Para o ledger/lancamentos financeiros, consumir `contractLabel`, `eventLabel`, `clientId` e `clientName`; aliases como `contrato_operacional_id`, `contrato_codigo`, `evento_nome` e `cliente_nome` existem apenas para transicao.
- Para filtros do ledger, preferir `startDate`, `endDate`, `contractId`, `eventId`, `clientId`, `cashFlowGroup`, `type`, `nature`, `origin`, `source`, `sourceId`, `sourceDetail` e `search`; usar os aliases em portugues apenas como fallback.
- No admin legado de pagamentos de parcelas, preferir `pendingPaymentAmount`, `installmentLabel` e `dueDate`; `valor_pendente_pagamento` e `saldo_em_aberto` permanecem como compatibilidade.
- Para baixas canonicas, preferir `contractLabel`, `eventLabel`, `clientName`, `writeModelSource` e filtros camelCase; aliases snake_case/portugues ficam apenas para transicao.
- Na baixa operacional do Next.js, a acao visual usa `Baixar valor pendente`; `settleRemainingBalance` permanece apenas como nome tecnico transicional do payload.
- Para colecoes de FCI/FCF/Mes, preferir `investments`, `categoryGroups`, `debts`, `installments`, `financingMovements`, `creditorGroups`, `receivables`, `payables` e `movements`.
- Para envelopes auxiliares de FCI/FCF/Mes, preferir `filters`, `filterOptions`, `totals` e `statistics` quando existirem.
- O Next.js ja possui tipos preparatorios `FinancialInvestmentResponseApi`, `FinancialFinancingResponseApi` e `FinancialMonthResponseApi` para migracao futura dessas telas, incluindo aliases canonicos e legados publicados pelo backend.
- Mocks e respostas vazias do Next devem acompanhar o contrato real: `DashboardEntityFilterOption` aceita contexto operacional completo e o ledger vazio carrega aliases de filtros para fallback seguro.
- Manter compatibilidade com aliases ate a versao `financeiro-v3`.

## Roteiro operacional canonical-first

O comando `validar_janela_canonical_first` publica `operationalChecklist` em
JSON e tambem mostra o roteiro na saida humana.

Fluxo recomendado:

1. Rodar sincronizacao canonica em dry-run.
2. Aplicar sincronizacao canonica somente se o dry-run estiver coerente.
3. Validar paridade canonica.
4. Rodar pre-flight operacional com leitura e escrita canonica.
5. Rodar canario rollback-only para uma origem direta.
6. Ativar `CANONICAL_FIRST_SETTLEMENT_ENABLED=True` e permitir apenas uma origem em `CANONICAL_FIRST_SETTLEMENT_SOURCES`.
7. Validar a flag ativa para a origem.
8. Auditar baixas `canonicalFirst` apos a janela.
9. Validar a janela exigindo baixa canonical-first.
10. Desligar a flag se aparecer divergencia, ausencia de baixa esperada ou comportamento operacional inesperado.

## Nomenclatura mantida por seguranca

- Campos fisicos `numero`, `saldo_*`, `saldo_em_aberto` e `total_em_aberto`.
- Models legados de pagamento: `PagamentoEventoCustoServico`, `PagamentoEventoCustoExtra` e `PagamentoParcelaDivida`.
- Fluxos especificos de admin e templates antigos que ainda dependem dos aliases.
- Leitura canonica com leitura legada segura quando a paridade ainda nao estiver pronta.

## Validacoes executadas recentemente

- `python manage.py test` (282 testes OK)
- `python manage.py check` (OK)
- `python manage.py makemigrations --check --dry-run` (sem migrations pendentes)
- `npm run typecheck` (OK)
- `npm run build` (OK)
- `git diff --check` no backend/frontend (OK; apenas avisos CRLF conhecidos)
- Testes focados de contrato, obrigacoes, baixa canonica, nomenclatura e custos de servico (OK)
- Teste focado de `/api/lancamentos-financeiros/` com aliases de dimensao operacional e filtros transicionais (OK)
- Teste focado do AJAX legado de parcelas no admin com `pendingPaymentAmount` e aliases legados (OK)
- `npm run typecheck` apos alinhamento de mocks e fallback do Next.js (OK)
- Teste focado de `/api/canonical-settlements/` com aliases de dimensao operacional em baixas e alocacoes (OK)
- `npm run typecheck` apos ajuste do label `Baixar valor pendente` no Next.js (OK)
- Testes focados do dashboard overview e das opcoes compartilhadas de filtros com contexto operacional completo (OK)
- Teste focado do dashboard overview validando catalogo de nomenclatura atualizado (OK)
- Teste focado do dashboard overview validando aliases de filtros/labels no catalogo de nomenclatura (OK)
- `npm run typecheck` apos alinhamento do mock de nomenclatura do Next.js (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases financeiros em contas resumidas (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases semanticos em `contractSummary` (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases em categorias de despesa e receitas por servico (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases mensais em `revenueExpense` (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos alias em `cashEvolution` (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases em `cashFlow` (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases em `resultadoFinanceiro` (OK)
- Testes focados do dashboard overview, `/api/lancamentos-financeiros/` e `npm run typecheck` apos aliases nos totais do ledger (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases de descricao/cliente em contas resumidas (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases em indicadores e metas (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases em KPIs (OK)
- Teste focado do dashboard overview e `npm run typecheck` apos aliases de descricao em opcoes de filtro (OK)
- Testes focados de dashboard, mes financeiro e obrigacoes mais `npm run typecheck` apos aliases `contractName`/`clientName` em opcoes de filtro (OK)
- Revisao consolidada apos aliases de opcoes de filtro: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de obrigacoes legadas/canonicas e `npm run typecheck` apos aliases `contractName`/`contractLabel`/`eventLabel` nos itens (OK)
- Testes focados de `/api/lancamentos-financeiros/`, dashboard overview e `npm run typecheck` apos aliases `ledgerAmount`/`ledgerDescription` (OK)
- Testes focados de liquidacao operacional, baixas canonicas, dashboard overview e `npm run typecheck` apos aliases `settlementAmount`/`settlementDescription` (OK)
- Teste focado de baixas canonicas e `npm run typecheck` apos alias `obligationDescription` em alocacoes (OK)
- Revisao consolidada apos aliases de baixas/alocacoes: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de FCI/FCF, dashboard overview e `npm run typecheck` apos aliases especificos de descricao em investimentos/dividas/financiamentos (OK)
- Testes focados de Mes Financeiro, dashboard overview e `npm run typecheck` apos aliases especificos de descricao mensal (OK)
- Teste de dashboard reforcado para catalogo de aliases de descricao e `npm run typecheck` apos revisao complementar (OK)
- Revisao consolidada apos aliases FCI/FCF/Mes: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de obrigacoes/dashboard e `npm run typecheck` apos `obligationDescription` nos itens e `payableDescription` no resumo de contas a pagar (OK)
- `npm run typecheck` apos consumo de `contractLabel`/`eventLabel` no resumo visual de contas a pagar do dashboard (OK)
- Revisao consolidada apos aliases de obrigacoes/dashboard: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de FCI/FCF e Mes Financeiro mais `npm run typecheck` apos alinhamento dos contratos TypeScript para aliases `contractName`, `contractDescription` e `eventDateLabel` em opcoes de filtro operacionais (OK)
- Teste focado de Mes Financeiro e `npm run typecheck` apos paridade dos tipos `FinancialMonth*OptionApi` com aliases operacionais publicados pelo backend (OK)
- Teste focado de obrigacoes divergentes e `npm run typecheck` apos aliases `contractName`/`contractLabel` na fila de conciliacao (OK)
- Teste focado de baixas canonicas e `npm run typecheck` apos publicacao de opcoes de filtro operacionais em `/api/canonical-settlements/` (OK)
- Revisao consolidada apos Fases 201-204: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK)
- `npm run typecheck` apos consumo de `contractLabel` na fila de divergencias, CSV e resumo de contas a pagar do Next.js (OK)
- Teste focado do dashboard e `npm run typecheck` apos aliases de descricao e dimensao operacional em `accountsReceivable` (OK)
- Testes focados de Mes Financeiro/Dashboard e `npm run typecheck` apos aliases de dimensao operacional em contas a pagar e movimentacoes (OK)
- Testes corretivos de movimentacoes, contas a pagar e performance de queries apos helpers defensivos de dimensao operacional (OK)
- Revisao consolidada apos Fases 205-207: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de paginas de pagamento apos troca visual de coluna `Valor` para `Valor pago` em historicos legados (OK)
- `python manage.py check` e `python manage.py test caixa.tests.PermissoesTests` apos rotulos `Valor pago` nos admins de pagamentos (OK)
- Testes focados de movimentacoes/Mes/Dashboard e `npm run typecheck` apos centralizar `serializar_dimensao_operacional_financeira` (OK)
- Revisao consolidada final apos Fases 208-210: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Teste focado de baixas canonicas e `npm run typecheck` apos rotulos explicitos de origem e `sourceLabel` em alocacoes canonicas (OK)
- Teste focado de `/api/lancamentos-financeiros/` e `npm run typecheck` apos aliases `source`/`sourceId`/`sourceLabel` no ledger (OK)
- `npm run typecheck` apos consumo de `sourceLabel` nos lancamentos vinculados ao ledger na tela de obrigacoes (OK)
- Teste focado de `/api/lancamentos-financeiros/` e `npm run typecheck` apos `originLabel`/`sourceLabel` nos filtros do ledger (OK)
- Revisao consolidada apos Fases 211-214: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Teste focado de FCI/FCF e `npm run typecheck` apos `value`, `startDate` e `eventDateLabel` nas opcoes operacionais compartilhadas (OK)
- Testes focados de Dashboard, Mes Financeiro, Obrigacoes e Baixas canonicas mais `npm run typecheck` apos padronizar `value` em opcoes de contratos/eventos/clientes (OK)
- `npm run typecheck` apos o header de filtros do Next.js passar a preferir `value` com fallback em `id` (OK)
- Revisao consolidada apos Fases 215-217: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run build` (OK), `python manage.py test` reexecutado apos ajuste de expectativa do novo alias `value` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de FCI/FCF e `npm run typecheck` apos aliases `*FinancialResultAmount` e `pendingPaymentAmount` em totais/subtotais (OK)
- Testes focados de Mes Financeiro/Dashboard e `npm run typecheck` apos aliases `*Amount` em acumulados de resultado financeiro e deficit de caixa (OK)
- Revisao consolidada apos Fases 218-219: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run build` (OK), `python manage.py test` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Testes focados de Dashboard, Obrigacoes, Baixas canonicas e FCI/FCF mais `npm run typecheck` apos centralizar opcoes operacionais (OK)
- Revisao consolidada apos Fase 220: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run build` (OK), `python manage.py test` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Revisao por `rg` em backend/frontend confirmando ausencia de pendencia visual obrigatoria para `Em aberto`, `Falta cobrir`, `Saldo previsto` e `Numero` como label de orcamento/evento (OK)
- `npm run typecheck` apos o grafico de evolucao de caixa preferir `accumulatedFinancialResultAmount` com fallback legado (OK)
- `npm run typecheck` apos o grafico de categorias de despesa usar `expenseAmount` como dataKey interno (OK)
- `npm run typecheck` apos tabelas/exportacao preferirem `pendingPaymentAmount` e `pendingReceivableAmount` antes de `pendingAmount` (OK)
- `npm run typecheck` apos normalizadores do Next.js priorizarem `pendingPaymentAmount` e `pendingReceivableAmount` antes de `pendingAmount` (OK)
- `npm run build` apos fases frontend 222-225 (OK)
- Testes focados de obrigacoes legadas/canonicas e `npm run typecheck` apos publicacao de `pendingPaymentAmount`/`pendingReceivableAmount` nos itens de obrigacoes (OK)
- Revisao consolidada apos Fases 222-226: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run build` (OK), `python manage.py test` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- `npm run typecheck` apos helpers semanticos de pendencia por tipo na tela de obrigacoes do Next.js (OK)
- `npm run build` apos helpers semanticos de pendencia na tela de obrigacoes (OK)
- `npm run typecheck` apos exportacao CSV de obrigacoes usar helpers de pendencia por tipo (OK)
- `npm run typecheck` e `npm run build` apos centralizar helpers de pendencia de obrigacoes no frontend (OK)
- `npm run typecheck` apos renomear variaveis internas do normalizador principal para `financialResultAmount`, `cashDeficitAmount` e `pendingAccountsAmount` (OK)
- `npm run build` apos renomeacao interna do normalizador principal (OK)
- Testes focados de parcelas e custos de servico apos trocar labels de baixa para "Baixar valor pendente restante" (OK)
- `python manage.py check` apos labels de baixa de valor pendente (OK)
- Testes focados de custos por evento e `python manage.py check` apos aliases `valor_pendente_*` no contexto antigo (OK)
- Revisao consolidada apos Fases 227-232: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run typecheck` (OK), `npm run build` (OK), `python manage.py test` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Teste focado de custos fixos apos aliases `total_valor_pendente_pagamento` e `subtotal_valor_pendente_pagamento` (OK)
- Testes focados de FCI/FCF apos alias `pendingRealizationAmount` em itens de investimento e movimentacoes de financiamento (OK)
- `npm run typecheck` e `python manage.py check` apos atualizar tipos FCI/FCF do Next para `pendingRealizationAmount` (OK)
- Revisao consolidada apos Fases 233-234: `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run build` (OK), `python manage.py test` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Teste focado do dashboard apos documentar `pendingRealizationAmount` no catalogo de nomenclatura (OK)
- Revisao consolidada final apos Fases 233-235: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `npm run typecheck` (OK), `npm run build` (OK), `python manage.py test` (282 OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Bug de edicao de divida financeira confirmado e corrigido: `valor_contratado` editado no admin agora sincroniza `valor_principal` das parcelas, `saldo_devedor`, FCF, obrigacao canonica e pagamento de parcelas.
- Teste de regressao da edicao de divida e suite completa apos correcao: `python manage.py test` (283 OK), `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes)
- Regra geral de substituicao de valores editaveis documentada e coberta: divida sincroniza `valor_contratado`, `quantidade_parcelas` e `dia_vencimento`; orcamento aprovado ressincroniza evento/receita/custos em transacao atomica; custos de evento e valores diretos atualizam ledger e obrigacoes canonicas. Reducoes inseguras de parcelas movimentadas sao bloqueadas.
- Testes focados da regra geral: dividas/parcelas, custos de evento, orcamento aprovado e valores diretos de receita/despesa/custo fixo/FCI/FCF (OK), `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), 70 testes dos modulos afetados (OK), suite completa `python manage.py test` (292 OK)
- Auditoria operacional adicionada: `verificar_integridade_valores_editaveis` detecta e corrige, quando seguro, divergencias historicas de dividas/parcelas, orcamentos aprovados, eventos, receitas previstas e custos de servico derivados. A ressincronizacao de orcamento aprovado preserva custos de servico com pagamentos/baixas, zerando somente o previsto quando o servico foi removido.
- Pre-flight operacional atualizado: `validar_operacao_obrigacoes --validar-valores-editaveis` inclui a auditoria read-only desses valores no mesmo roteiro de contrato, conciliacao, modelagem canonica e escrita canonica. `--falhar-com-valores-editaveis` ativa a checagem e retorna erro para automacoes.
- Janela canonical-first atualizada: `validar_janela_canonical_first --validar-valores-editaveis` tambem consegue reprovar uma janela quando valores editaveis antigos ainda deixam parcelas, eventos ou orcamentos derivados desatualizados.
- Fotografia operacional atualizada: `auditar_totais_negocio --validar-valores-editaveis` permite comparar totais de negocio, ledger, obrigacoes e integridade de valores editaveis no mesmo relatorio read-only.
- Arquitetura interna ajustada: a regra de integridade de valores editaveis foi movida para `services_valores_editaveis`, deixando os management commands apenas como wrappers operacionais.
- Operacao mais segura: `verificar_integridade_valores_editaveis` aceita `--escopo` e `--object-id` para auditar ou corrigir divergencias historicas em lotes pequenos.
- Os comandos consolidados (`validar_operacao_obrigacoes`, `validar_janela_canonical_first` e `auditar_totais_negocio`) tambem aceitam filtros especificos de valores editaveis por `--valores-editaveis-escopo` e `--valores-editaveis-object-id`.
- Testes focados da auditoria de valores editaveis e preservacao de pagamentos de custos de servico removidos do orcamento aprovado (OK); comando em modo somente leitura na base local encontrou 29 divergencias historicas e nenhuma correcao foi aplicada; suite completa `python manage.py test` (295 OK).
- Revisao consolidada apos aliases de obrigacoes/ledger: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Revisao consolidada apos KPIs: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Revisao consolidada apos aliases do ledger: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Revisao consolidada apos `cashEvolution`, `cashFlow` e `resultadoFinanceiro`: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run typecheck` (OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Revisao consolidada apos aliases do dashboard inicial: `python manage.py check` (OK), `python manage.py makemigrations --check --dry-run` (sem migrations pendentes), `python manage.py test` (282 OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)
- Suite consolidada apos as fases recentes: `python manage.py test` (282 OK), `npm run typecheck` (OK), `npm run build` (OK), `git diff --check` (OK; avisos CRLF conhecidos)

## Proximos passos

1. Validar em producao com dados reais usando os comandos de pre-flight e auditoria.
2. Ativar `canonical-first` em janela curta para uma origem direta por vez, com canario rollback-only antes.
3. Auditar `writeModelSource` apos a janela e confirmar divergencia zero.
4. So depois consolidar a escrita canonica como padrao.
5. Planejar `financeiro-v3` para remocao fisica gradual dos aliases antigos.
