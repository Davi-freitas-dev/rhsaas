VERSAO_NOMENCLATURA_FINANCEIRA = "financeiro-v2"
VERSAO_REMOCAO_ALIASES_LEGADOS = "financeiro-v3"


TERMOS_CANONICOS_FINANCEIROS = {
    "contrato": {
        "label": "Contrato",
        "description": "Identificador contratual de orçamentos e eventos.",
    },
    "contractCode": {
        "label": "Código do contrato",
        "description": "Número visível do orçamento/evento usado em filtros e telas.",
    },
    "contractName": {
        "label": "Nome do contrato",
        "description": "Nome de apoio para opções de filtro derivadas do evento/orçamento.",
    },
    "contractLabel": {
        "label": "Rótulo do contrato",
        "description": "Texto de exibição do contrato visual derivado do evento/orçamento.",
    },
    "contractDescription": {
        "label": "Descrição do contrato",
        "description": "Texto auxiliar do contrato visual em opções de filtro.",
    },
    "eventLabel": {
        "label": "Rótulo do evento",
        "description": "Texto de exibição do evento com código e nome.",
    },
    "eventDateLabel": {
        "label": "Data exibida do evento",
        "description": "Texto de data do evento usado em opções de filtro.",
    },
    "clientName": {
        "label": "Nome do cliente",
        "description": "Nome ou razão social do cliente vinculado ao registro financeiro.",
    },
    "obligationDescription": {
        "label": "Descrição da obrigação",
        "description": "Descrição de negócio da conta pendente ou obrigação financeira.",
    },
    "ledgerAmount": {
        "label": "Valor do lançamento financeiro",
        "description": "Valor realizado registrado no ledger financeiro.",
    },
    "ledgerDescription": {
        "label": "Descrição do lançamento financeiro",
        "description": "Descrição de negócio do lançamento realizado no ledger financeiro.",
    },
    "settlementAmount": {
        "label": "Valor da baixa financeira",
        "description": "Valor realizado registrado em uma baixa financeira canônica.",
    },
    "settlementDescription": {
        "label": "Descrição da baixa financeira",
        "description": "Descrição de negócio da baixa financeira canônica.",
    },
    "investmentDescription": {
        "label": "Descrição do investimento",
        "description": "Descrição de negócio de um item do fluxo de investimento.",
    },
    "debtDescription": {
        "label": "Descrição da dívida",
        "description": "Descrição de negócio da dívida financeira.",
    },
    "creditorId": {
        "label": "ID do credor",
        "description": "Identificador estavel do credor cadastrado usado por dividas FCF.",
    },
    "creditorName": {
        "label": "Nome do credor",
        "description": "Nome de exibicao do credor cadastrado vinculado a divida FCF.",
    },
    "financingMovementDescription": {
        "label": "Descrição da movimentação de financiamento",
        "description": "Descrição de negócio de uma entrada ou saída de financiamento.",
    },
    "receivableDescription": {
        "label": "Descrição da conta a receber",
        "description": "Descrição de negócio de uma receita ou conta a receber.",
    },
    "payableDescription": {
        "label": "Descrição da conta a pagar",
        "description": "Descrição de negócio de uma despesa, parcela ou conta a pagar.",
    },
    "movementDescription": {
        "label": "Descrição da movimentação",
        "description": "Descrição de negócio de uma movimentação financeira consolidada.",
    },
    "clientLabel": {
        "label": "Rótulo do cliente",
        "description": "Texto de exibição do cliente em filtros e tabelas financeiras.",
    },
    "startDate": {
        "label": "Data inicial",
        "description": "Início do período filtrado em APIs financeiras.",
    },
    "endDate": {
        "label": "Data final",
        "description": "Fim do período filtrado em APIs financeiras.",
    },
    "resultadoFinanceiro": {
        "label": "Resultado financeiro",
        "description": "Resultado final do fluxo no recorte filtrado.",
    },
    "deficitCaixa": {
        "label": "Déficit de caixa",
        "description": "Falta de caixa/cobertura quando o resultado projetado fica negativo.",
    },
    "contasPendentes": {
        "label": "Contas pendentes",
        "description": "Valor ainda não liquidado em contas a pagar ou receber.",
    },
    "contas_pendentes_total": {
        "label": "Contas pendentes",
        "description": "Valor pendente total de um item operacional.",
    },
    "subtotal_contas_pendentes_geral": {
        "label": "Subtotal de contas pendentes",
        "description": "Subtotal pendente consolidado de um grupo operacional.",
    },
    "subtotal_contas_pendentes_custos_extras": {
        "label": "Subtotal de custos extras pendentes",
        "description": "Subtotal pendente de custos extras e despesas manuais de evento.",
    },
    "total_contas_pendentes_eventos": {
        "label": "Total de contas pendentes dos eventos",
        "description": "Total pendente dos custos agrupados por evento.",
    },
    "contas_pendentes_por_evento": {
        "label": "Contas pendentes por evento",
        "description": "Mapa de valores pendentes agrupados por evento.",
    },
    "eventos_operacionais_ativos": {
        "label": "Eventos operacionais ativos",
        "description": "Quantidade de eventos planejados, confirmados ou em andamento.",
    },
    "activeOperationalEventsCount": {
        "label": "Eventos operacionais ativos",
        "description": "Alias camelCase para eventos planejados, confirmados ou em andamento.",
    },
    "valorPendentePagamento": {
        "label": "Valor pendente de pagamento",
        "description": "Valor restante de uma obrigação financeira a pagar.",
    },
    "pendingPaymentAmount": {
        "label": "Valor pendente de pagamento",
        "description": "Alias camelCase para valor ainda pendente em contas a pagar.",
    },
    "plannedRevenueAmount": {
        "label": "Receitas previstas",
        "description": "Alias camelCase para receitas previstas no periodo.",
    },
    "receivedRevenueAmount": {
        "label": "Receitas recebidas",
        "description": "Alias camelCase para receitas efetivamente recebidas no periodo.",
    },
    "plannedAmount": {
        "label": "Valor previsto",
        "description": "Valor projetado ou previsto antes da liquidação financeira.",
    },
    "paidAmount": {
        "label": "Valor pago",
        "description": "Valor efetivamente pago em uma conta a pagar.",
    },
    "receivedAmount": {
        "label": "Valor recebido",
        "description": "Valor efetivamente recebido em uma conta a receber.",
    },
    "pendingAmount": {
        "label": "Valor pendente",
        "description": "Valor ainda não liquidado, aplicável a contas a pagar ou receber.",
    },
    "pendingRealizationAmount": {
        "label": "Valor pendente de realização",
        "description": "Valor previsto ainda não realizado em fluxos de investimento ou financiamento.",
    },
    "valorPendenteRecebimento": {
        "label": "Valor pendente de recebimento",
        "description": "Valor restante de uma receita a receber.",
    },
    "receita_pendente_recebimento": {
        "label": "Receita pendente de recebimento",
        "description": "Total de receitas ainda não recebidas no período.",
    },
    "divida_pendente_pagamento": {
        "label": "Dívida pendente de pagamento",
        "description": "Total de contas/dívidas ainda não pagas no período.",
    },
    "quantidade_dividas_pendentes": {
        "label": "Dívidas pendentes",
        "description": "Quantidade de dívidas FCF com valor financeiro ainda pendente.",
    },
    "quantidade_dividas_listadas": {
        "label": "Dívidas listadas",
        "description": "Quantidade de dívidas FCF retornadas pelo filtro atual.",
    },
    "pendingDebtsCount": {
        "label": "Dívidas pendentes",
        "description": "Quantidade de dívidas FCF com valor financeiro ainda pendente.",
    },
    "listedDebtsCount": {
        "label": "Dívidas listadas",
        "description": "Quantidade de dívidas FCF retornadas pelo filtro atual.",
    },
    "pendingReceivableAmount": {
        "label": "Valor pendente de recebimento",
        "description": "Alias camelCase para valor ainda pendente em contas a receber.",
    },
    "plannedPayablesAmount": {
        "label": "Contas previstas",
        "description": "Alias camelCase para contas a pagar previstas no periodo.",
    },
    "paidPayablesAmount": {
        "label": "Contas pagas",
        "description": "Alias camelCase para contas efetivamente pagas no periodo.",
    },
    "overdueAccountsAmount": {
        "label": "Contas vencidas",
        "description": "Alias camelCase para contas vencidas no periodo.",
    },
    "installmentLabel": {
        "label": "Rótulo da parcela",
        "description": "Identificação visual da parcela, como 1/3.",
    },
    "availableForPayment": {
        "label": "Disponivel para pagamento",
        "description": "Booleano calculado pelo backend indicando se a parcela FCF pode receber pagamento.",
    },
    "sourceType": {
        "label": "Tipo de origem da movimentacao",
        "description": "Indica se a movimentacao FCF e manual ou gerada automaticamente por uma divida.",
    },
    "sourceTypeLabel": {
        "label": "Rotulo do tipo de origem da movimentacao",
        "description": "Texto de exibicao do tipo de origem da movimentacao FCF.",
    },
    "automaticFromDebt": {
        "label": "Automatica por divida",
        "description": "Indica se a movimentacao FCF foi gerada automaticamente a partir de uma divida.",
    },
    "financingMovementSourceTypes": {
        "label": "Tipos de origem da movimentacao FCF",
        "description": "Opcoes de filtro para separar movimentacoes FCF manuais e automaticas por divida.",
    },
    "debtId": {
        "label": "ID da divida",
        "description": "Identificador da divida financeira que originou a movimentacao FCF.",
    },
    "debtCreditorId": {
        "label": "ID do credor da divida",
        "description": "Identificador do credor cadastrado da divida que originou a movimentacao FCF.",
    },
    "debtCreditorName": {
        "label": "Nome do credor da divida",
        "description": "Nome de exibicao do credor da divida que originou a movimentacao FCF.",
    },
    "quantidade_parcelas_pendentes": {
        "label": "Quantidade de parcelas pendentes",
        "description": "Contagem de parcelas ainda não liquidadas.",
    },
    "pendingInstallmentsCount": {
        "label": "Quantidade de parcelas pendentes",
        "description": "Alias camelCase para contagem de parcelas ainda não liquidadas.",
    },
    "installmentsCount": {
        "label": "Parcelas listadas",
        "description": "Quantidade de parcelas FCF retornadas pelo filtro atual.",
    },
    "overdueInstallmentsCount": {
        "label": "Parcelas vencidas",
        "description": "Quantidade de parcelas FCF vencidas no filtro atual.",
    },
    "financingMovementsCount": {
        "label": "Movimentações de financiamento",
        "description": "Quantidade de movimentações FCF retornadas pelo filtro atual.",
    },
    "overdueFinancingMovementsCount": {
        "label": "Movimentações de financiamento vencidas",
        "description": "Quantidade de movimentações FCF vencidas no filtro atual.",
    },
    "origemDespesaOperacional": {
        "label": "Origem da despesa operacional",
        "description": "Classifica a despesa como manual, custo de serviço ou custo extra.",
    },
    "cashBasisRealizedFlow": {
        "label": "Fluxo realizado por caixa",
        "description": "Entradas e saídas realizadas pela data efetiva do lançamento.",
    },
    "competenceBasisRealizedFlow": {
        "label": "Fluxo realizado por competência",
        "description": "Comparativo legado usado durante a transição do dashboard.",
    },
    "obrigacaoFinanceira": {
        "label": "Obrigação financeira",
        "description": "Conta a pagar ou a receber, prevista ou pendente de liquidação.",
    },
    "baixaFinanceira": {
        "label": "Baixa financeira",
        "description": "Recebimento ou pagamento efetivamente realizado no caixa.",
    },
    "baixaFinanceiraAlocacao": {
        "label": "Alocação de baixa financeira",
        "description": "Vínculo entre uma baixa realizada e a obrigação que ela liquida.",
    },
    "valorExcedenteRealizado": {
        "label": "Realizado acima do previsto",
        "description": "Valor realizado que excede o previsto, sem gerar pendencia negativa.",
    },
    "readyForCanonicalReads": {
        "label": "Pronto para leitura canônica",
        "description": "Indica que a camada canônica está sincronizada e em paridade.",
    },
    "canonicalParity": {
        "label": "Paridade canônica",
        "description": "Comparação entre origens legadas, ledger e models canônicos.",
    },
    "dataSource": {
        "label": "Fonte de leitura",
        "description": "Define se a API lê obrigações pelo legado ou pela modelagem canônica.",
    },
    "readModelSource": {
        "label": "Read model da obrigação",
        "description": "Indica a base efetiva usada para montar cada obrigação entregue ao frontend.",
    },
    "readModelStatus": {
        "label": "Status da fonte de leitura",
        "description": "Contrato consolidado da fonte solicitada, fonte efetiva, status visual e paridade canônica.",
    },
    "readModelStatusDiagnostics": {
        "label": "Diagnóstico da fonte de leitura",
        "description": "Resumo operacional da leitura solicitada, leitura efetiva, leitura legada e paridade canônica.",
    },
    "readModelStatusReason": {
        "label": "Motivo do status da fonte de leitura",
        "description": "Código técnico que explica por que a API usou leitura legada segura.",
    },
    "amountSemantics": {
        "label": "Semântica dos valores",
        "description": "Contrato que explica o significado financeiro dos campos de valor publicados para o frontend.",
    },
    "filterSemantics": {
        "label": "Semântica dos filtros",
        "description": "Contrato que explica como filtros financeiros sao combinados e interpretados.",
    },
    "cashFlowSemantics": {
        "label": "Semântica do fluxo de caixa",
        "description": "Contrato que diferencia resultado financeiro, deficit de caixa e contas pendentes no dashboard.",
    },
    "legacyReadReason": {
        "label": "Motivo da leitura legada",
        "description": "Código técnico que explica por que a leitura efetiva permaneceu no legado.",
    },
    "writeModelSource": {
        "label": "Fonte de escrita da baixa",
        "description": "Indica se a baixa foi escrita por adapter legado sincronizado ou pelo caminho canonical-first.",
    },
    "source": {
        "label": "Origem financeira",
        "description": "Origem de negócio da obrigação, baixa ou lançamento financeiro.",
    },
    "sourceId": {
        "label": "ID da origem financeira",
        "description": "Identificador da origem de negócio vinculada ao registro financeiro.",
    },
    "sourceDetail": {
        "label": "Detalhe da origem financeira",
        "description": "Recorte adicional da origem, como tipo de custo de serviço.",
    },
    "cashFlowGroup": {
        "label": "Grupo do fluxo de caixa",
        "description": "Classificação do fluxo em FCO, FCI ou FCF.",
    },
    "nature": {
        "label": "Natureza financeira",
        "description": "Natureza contábil/financeira do lançamento ou baixa.",
    },
    "settlementStatus": {
        "label": "Status de liquidação",
        "description": "Situação de liquidação da obrigação financeira.",
    },
    "search": {
        "label": "Busca textual",
        "description": "Termo usado para busca livre em filtros financeiros.",
    },
    "serviceName": {
        "label": "Nome do serviço",
        "description": "Nome do serviço operacional em resumos do dashboard.",
    },
    "categoryName": {
        "label": "Nome da categoria",
        "description": "Nome da categoria financeira em resumos de despesas do dashboard.",
    },
    "contractCount": {
        "label": "Quantidade de contratos",
        "description": "Quantidade de contratos/eventos associados ao resumo operacional.",
    },
    "operationalEventsCount": {
        "label": "Quantidade de eventos operacionais",
        "description": "Quantidade de eventos associados ao resumo operacional por serviço.",
    },
    "revenueAmount": {
        "label": "Valor de receita",
        "description": "Valor de receita associado ao serviço, evento ou orçamento.",
    },
    "expenseAmount": {
        "label": "Valor de despesa",
        "description": "Valor de despesa associado a uma categoria financeira.",
    },
    "accumulatedFinancialResult": {
        "label": "Resultado financeiro acumulado",
        "description": "Resultado financeiro acumulado ao longo da serie temporal.",
    },
    "accumulatedFinancialResultAmount": {
        "label": "Valor do resultado financeiro acumulado",
        "description": "Campo canonico para resultado financeiro acumulado ao longo da serie temporal.",
    },
    "initialCashAmount": {
        "label": "Caixa inicial",
        "description": "Valor inicial de caixa considerado no fluxo do período.",
    },
    "inflowAmount": {
        "label": "Entradas financeiras",
        "description": "Total de entradas financeiras no período.",
    },
    "outflowAmount": {
        "label": "Saídas financeiras",
        "description": "Total de saídas financeiras no período.",
    },
    "plannedInflowAmount": {
        "label": "Entradas previstas",
        "description": "Alias camelCase para entradas previstas em FCI, FCF ou Mes Financeiro.",
    },
    "plannedOutflowAmount": {
        "label": "Saidas previstas",
        "description": "Alias camelCase para saidas previstas em FCI, FCF ou Mes Financeiro.",
    },
    "realizedInflowAmount": {
        "label": "Entradas realizadas",
        "description": "Alias camelCase para entradas efetivamente realizadas.",
    },
    "realizedOutflowAmount": {
        "label": "Saidas realizadas",
        "description": "Alias camelCase para saidas efetivamente realizadas.",
    },
    "projectedInflowAmount": {
        "label": "Entradas projetadas",
        "description": "Alias camelCase para entradas projetadas no fluxo de investimento.",
    },
    "projectedOutflowAmount": {
        "label": "Saidas projetadas",
        "description": "Alias camelCase para saidas projetadas no fluxo de investimento.",
    },
    "financialResultAmount": {
        "label": "Valor do resultado financeiro",
        "description": "Valor final do resultado financeiro no período.",
    },
    "plannedFinancialResultAmount": {
        "label": "Resultado financeiro previsto",
        "description": "Alias camelCase para resultado financeiro previsto.",
    },
    "projectedFinancialResultAmount": {
        "label": "Resultado financeiro projetado",
        "description": "Alias camelCase para resultado financeiro projetado.",
    },
    "realizedFinancialResultAmount": {
        "label": "Resultado financeiro realizado",
        "description": "Alias camelCase para resultado financeiro realizado.",
    },
    "pendingFinancialResultAmount": {
        "label": "Resultado financeiro pendente",
        "description": "Alias camelCase para resultado financeiro ainda pendente.",
    },
    "cashDeficitAmount": {
        "label": "Valor do déficit de caixa",
        "description": "Valor de falta de caixa/cobertura no período.",
    },
    "availableCashAmount": {
        "label": "Caixa do periodo",
        "description": (
            "Caixa final disponivel do periodo: saldo inicial mais entradas "
            "efetivamente recebidas menos saidas efetivamente pagas."
        ),
    },
    "finalCashAmount": {
        "label": "Caixa final do periodo",
        "description": "Mesmo conceito canonico de availableCashAmount.",
    },
    "currentAvailableCashAmount": {
        "label": "Caixa disponivel atual",
        "description": (
            "Caixa efetivo disponivel ate hoje, independente dos filtros de "
            "periodo da tela."
        ),
    },
    "accumulatedCashUntilDate": {
        "label": "Caixa acumulado ate a data",
        "description": (
            "Caixa acumulado efetivo ate a data de referencia, usando entradas "
            "e saidas efetivas."
        ),
    },
    "cashAvailableUntilDate": {
        "label": "Data de referência do caixa disponível",
        "description": "Data limite usada para calcular o caixa acumulado disponível.",
    },
    "periodRealizedAmount": {
        "label": "Resultado realizado do período",
        "description": (
            "Recebido menos pago dentro do período filtrado, sem substituir o "
            "caixa acumulado disponível."
        ),
    },
    "pendingPayablesAmount": {
        "label": "Contas a pagar pendentes",
        "description": "Valor pendente de contas a pagar no escopo filtrado.",
    },
    "availableAfterPendingAmount": {
        "label": "Caixa após pendências",
        "description": (
            "Caixa disponível menos contas a pagar pendentes no escopo filtrado."
        ),
    },
    "cashCoverageAfterPendingAmount": {
        "label": "Cobertura de caixa apos pendencias",
        "description": (
            "Caixa disponivel do periodo menos contas a pagar pendentes no "
            "escopo filtrado."
        ),
    },
    "paymentCapacityAfterPendingAmount": {
        "label": "Capacidade de pagamento apos pendencias",
        "description": (
            "Capacidade de pagamento restante depois das contas a pagar "
            "pendentes do escopo."
        ),
    },
    "cashCoverageDeficitAmount": {
        "label": "Déficit de cobertura",
        "description": (
            "Valor que falta para cobrir as contas a pagar pendentes com o caixa "
            "disponível."
        ),
    },
    "projectedAmount": {
        "label": "Valor projetado",
        "description": "Valor financeiro projetado para o período.",
    },
    "realizedAmount": {
        "label": "Valor realizado",
        "description": "Valor financeiro efetivamente realizado no período.",
    },
    "consolidatedProjectedAmount": {
        "label": "Resultado consolidado projetado",
        "description": "Resultado financeiro consolidado projetado no período.",
    },
    "consolidatedRealizedAmount": {
        "label": "Resultado consolidado realizado",
        "description": "Resultado financeiro consolidado realizado no período.",
    },
    "operationalProjectedAmount": {
        "label": "Resultado operacional projetado",
        "description": "Resultado financeiro operacional projetado no período.",
    },
    "operationalRealizedAmount": {
        "label": "Resultado operacional realizado",
        "description": "Resultado financeiro operacional realizado no período.",
    },
    "investmentRealizedAmount": {
        "label": "Resultado de investimentos realizado",
        "description": "Resultado financeiro realizado no fluxo de investimento.",
    },
    "financingRealizedAmount": {
        "label": "Resultado de financiamentos realizado",
        "description": "Resultado financeiro realizado no fluxo de financiamento.",
    },
    "pendingAccountsAmount": {
        "label": "Valor de contas pendentes",
        "description": "Valor total ainda não liquidado no período.",
    },
    "indicatorName": {
        "label": "Nome do indicador",
        "description": "Nome de negócio do indicador financeiro exibido no dashboard.",
    },
    "indicatorValue": {
        "label": "Valor do indicador",
        "description": "Valor formatado do indicador financeiro.",
    },
    "indicatorDetail": {
        "label": "Detalhe do indicador",
        "description": "Texto complementar do indicador financeiro.",
    },
    "goalName": {
        "label": "Nome da meta",
        "description": "Nome de negócio da meta financeira.",
    },
    "currentValue": {
        "label": "Valor atual",
        "description": "Valor atual medido para uma meta financeira.",
    },
    "targetValue": {
        "label": "Valor alvo",
        "description": "Valor alvo esperado para uma meta financeira.",
    },
    "metricValue": {
        "label": "Valor da métrica",
        "description": "Valor numérico principal de uma métrica ou KPI financeiro.",
    },
    "changePercent": {
        "label": "Percentual de variação",
        "description": "Variação percentual associada a uma métrica financeira; pode ser nula quando nao houver base historica real.",
    },
    "changeDescription": {
        "label": "Descrição da variação",
        "description": "Texto contextual da variação de uma métrica financeira.",
    },
    "obligationType": {
        "label": "Tipo da obrigação",
        "description": "Classifica a obrigação como conta a pagar ou conta a receber.",
    },
    "supportedObligationTypes": {
        "label": "Tipos de obrigação liquidáveis",
        "description": "Lista quais tipos de obrigação cada adapter de baixa consegue liquidar.",
    },
    "canonicalFirst": {
        "label": "Escrita canônica primeiro",
        "description": "Modo controlado por feature flag em que a baixa canônica é criada antes do adapter legado.",
    },
    "financialResult": {
        "label": "Resultado financeiro",
        "description": "Objeto consolidado com resultado financeiro projetado, realizado, pendente e déficit de caixa.",
    },
    "projectedInvestmentFlow": {
        "label": "Fluxo de investimento projetado",
        "description": "Entradas, saídas e resultado financeiro projetado do FCI.",
    },
    "realizedInvestmentFlow": {
        "label": "Fluxo de investimento realizado",
        "description": "Entradas, saídas e resultado financeiro realizado do FCI.",
    },
    "projectedFinancingFlow": {
        "label": "Fluxo de financiamento projetado",
        "description": "Entradas, saídas e resultado financeiro projetado do FCF.",
    },
    "realizedFinancingFlow": {
        "label": "Fluxo de financiamento realizado",
        "description": "Entradas, saídas e resultado financeiro realizado do FCF.",
    },
    "filters": {
        "label": "Filtros",
        "description": "Filtros normalizados aplicados a APIs financeiras consumidas pelo frontend.",
    },
    "filterOptions": {
        "label": "Opções de filtro",
        "description": "Opções disponíveis para selects e filtros do frontend financeiro.",
    },
    "totals": {
        "label": "Totais financeiros",
        "description": "Agregados financeiros serializados para indicadores, cards e tabelas.",
    },
    "statistics": {
        "label": "Estatísticas operacionais",
        "description": "Contadores operacionais auxiliares publicados para leitura do frontend.",
    },
    "validateLegacyRead": {
        "label": "Validar leitura legada",
        "description": "Etapa operacional que confirma a leitura legada após rollback de uma janela canonical-first.",
    },
}


ALIASES_LEGADOS_FINANCEIROS = {
    "numero": "contrato",
    "contract": "contractCode",
    "saldoCaixa": "resultadoFinanceiro",
    "saldoFinal": "resultadoFinanceiro",
    "deficitCaixa": "cashDeficitAmount",
    "contasPendentes": "pendingAccountsAmount",
    "contasPendentesTotal": "pendingAccountsAmount",
    "saldo_previsto": "resultado_financeiro_previsto",
    "saldo_realizado": "resultado_financeiro_realizado",
    "saldo_previsto_fci": "resultado_financeiro_fci_projetado",
    "saldo_realizado_fci": "resultado_financeiro_fci_realizado",
    "saldo_previsto_fcf": "resultado_financeiro_fcf_projetado",
    "saldo_realizado_fcf": "resultado_financeiro_fcf_realizado",
    "total_em_aberto_fcf": "total_contas_pendentes_fcf",
    "subtotal_saldo_previsto": "subtotal_resultado_financeiro_projetado",
    "subtotal_saldo_realizado": "subtotal_resultado_financeiro_realizado",
    "saldo_previsto_acumulado": "resultado_financeiro_previsto_acumulado",
    "saldo_realizado_acumulado": "resultado_financeiro_realizado_acumulado",
    "saldo_em_aberto": "valor_pendente_pagamento",
    "receita_aberta": "receita_pendente_recebimento",
    "divida_aberta": "divida_pendente_pagamento",
    "credor": "creditorName",
    "creditor": "creditorName",
    "credor_id": "creditorId",
    "credor_nome": "creditorName",
    "valorBaixa": "settlementAmount",
    "valor_baixa": "settlementAmount",
    "valorTotal": "settlementAmount",
    "valorLancamento": "ledgerAmount",
    "valor_lancamento": "ledgerAmount",
    "eventos_abertos": "eventos_operacionais_ativos",
    "activeContractsCount": "activeOperationalEventsCount",
    "saldo_aberto": "resultado_financeiro_pendente",
    "total_aberto": "total_contas_pendentes",
    "total_em_aberto": "total_contas_pendentes",
    "subtotal_em_aberto": "subtotal_contas_pendentes",
    "total_saldo_eventos": "total_contas_pendentes_eventos",
    "saldo_total": "contas_pendentes_total",
    "subtotal_saldo_geral": "subtotal_contas_pendentes_geral",
    "subtotal_saldo_custos_extras": "subtotal_contas_pendentes_custos_extras",
    "saldos_por_evento": "contas_pendentes_por_evento",
    "saldo_a_pagar": "valor_pendente_pagamento",
    "saldo_geral": "valor_pendente_pagamento",
    "falta_cobrir": "deficit_caixa",
    "origem_pagamento": "origem",
    "realizedCashFlow": "cashBasisRealizedFlow",
    "accumulatedFinancialResult": "accumulatedFinancialResultAmount",
    "fonteDados": "dataSource",
    "fonte_dados": "dataSource",
    "canonicalFallbackReason": "readModelStatusReason",
    "fallbackReason": "legacyReadReason",
    "validateLegacyFallback": "validateLegacyRead",
    "read_model_source": "readModelSource",
    "fonteEscrita": "writeModelSource",
    "fonte_escrita": "writeModelSource",
    "tipoObrigacao": "obligationType",
    "tipo_obrigacao": "obligationType",
    "data_inicial": "startDate",
    "data_final": "endDate",
    "contrato_codigo": "contractCode",
    "costCenterId": "eventId",
    "evento": "eventId",
    "evento_id": "eventId",
    "evento_nome": "eventName",
    "evento_numero": "eventNumber",
    "eventoLabel": "eventLabel",
    "evento_label": "eventLabel",
    "cliente": "clientId",
    "cliente_id": "clientId",
    "clienteLabel": "clientLabel",
    "cliente_label": "clientLabel",
    "cliente_nome": "clientName",
    "valor_pendente_pagamento": "pendingPaymentAmount",
    "valor_pendente_realizacao": "pendingRealizationAmount",
    "saldo_restante": "pendingRealizationAmount",
    "rotulo_parcela": "installmentLabel",
    "disponivel_para_pagamento": "availableForPayment",
    "movementSourceType": "sourceType",
    "origem_movimentacao": "sourceType",
    "movementSourceTypeLabel": "sourceTypeLabel",
    "origem_movimentacao_display": "sourceTypeLabel",
    "isAutomaticFromDebt": "automaticFromDebt",
    "entrada_automatica_divida": "automaticFromDebt",
    "movementSourceTypes": "financingMovementSourceTypes",
    "origens_movimentacao_financiamento": "financingMovementSourceTypes",
    "divida_id": "debtId",
    "credor_divida_id": "debtCreditorId",
    "debtCreditor": "debtCreditorName",
    "credor_divida": "debtCreditorName",
    "nome_credor_divida": "debtCreditorName",
    "receita_prevista": "plannedRevenueAmount",
    "receita_recebida": "receivedRevenueAmount",
    "custo_variavel": "variableCostAmount",
    "margem_contribuicao": "contributionMarginAmount",
    "margem_contribuicao_percentual": "contributionMarginPercent",
    "lucro_operacional_ebit": "operatingProfitEbitAmount",
    "contas_previstas": "plannedPayablesAmount",
    "contas_pagas": "paidPayablesAmount",
    "contas_vencidas": "overdueAccountsAmount",
    "total_previsto_entrada": "plannedInflowAmount",
    "total_previsto_saida": "plannedOutflowAmount",
    "total_realizado_entrada": "realizedInflowAmount",
    "total_realizado_saida": "realizedOutflowAmount",
    "entradas_investimento_projetadas": "projectedInflowAmount",
    "saidas_investimento_projetadas": "projectedOutflowAmount",
    "resultado_financeiro_previsto": "plannedFinancialResultAmount",
    "resultado_financeiro_projetado": "projectedFinancialResultAmount",
    "resultado_financeiro_realizado": "realizedFinancialResultAmount",
    "resultado_financeiro_pendente": "pendingFinancialResultAmount",
    "resultado_financeiro_fci_previsto": "plannedFinancialResultAmount",
    "resultado_financeiro_fci_projetado": "projectedFinancialResultAmount",
    "resultado_financeiro_fci_realizado": "realizedFinancialResultAmount",
    "resultado_financeiro_fcf_projetado": "projectedFinancialResultAmount",
    "resultado_financeiro_fcf_realizado": "realizedFinancialResultAmount",
    "resultado_financeiro_investimentos_projetado": "projectedFinancialResultAmount",
    "resultado_financeiro_investimentos_realizado": "realizedFinancialResultAmount",
    "total_contas_pendentes": "pendingAccountsAmount",
    "total_contas_vencidas": "overdueAccountsAmount",
    "total_vencido": "overdueAccountsAmount",
    "deficit_caixa": "cashDeficitAmount",
    "caixa_disponivel": "availableCashAmount",
    "quantidade_dividas": "pendingDebtsCount",
    "debtsCount": "pendingDebtsCount",
    "quantidade_parcelas": "installmentsCount",
    "quantidade_parcelas_vencidas": "overdueInstallmentsCount",
    "quantidade_movimentacoes_financiamento": "financingMovementsCount",
    "quantidade_movimentacoes_financiamento_vencidas": "overdueFinancingMovementsCount",
    "quantidade_parcelas_abertas": "quantidade_parcelas_pendentes",
    "openInstallmentsCount": "pendingInstallmentsCount",
    "origem": "source",
    "origem_obrigacao": "source",
    "source_id": "sourceId",
    "origin_id": "sourceId",
    "source_detail": "sourceDetail",
    "fluxo": "cashFlowGroup",
    "natureza": "nature",
    "situacao": "settlementStatus",
    "busca": "search",
    "filtros": "filters",
    "opcoes": "filterOptions",
    "totais": "totals",
    "estatisticas": "statistics",
}


INVENTARIO_USO_ALIASES_LEGADOS = {
    "numero": {
        "replacement": "contractCode",
        "status": "alias_temporario",
        "surfaces": ["models", "admin", "dashboard_api", "mes_financeiro_api"],
        "reason": "Campo físico de orçamento/evento continua sendo a origem do contrato visual publicado como contractCode.",
    },
    "contract": {
        "replacement": "contractCode",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "mes_financeiro_api", "next_filters"],
        "reason": "Alias antigo mantido para filtros e mocks do frontend.",
    },
    "saldoCaixa": {
        "replacement": "resultadoFinanceiro",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "next_kpis"],
        "reason": "Nome visual antigo do card de resultado financeiro.",
    },
    "saldoFinal": {
        "replacement": "resultadoFinanceiro",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api.cashFlow", "next_widgets"],
        "reason": "Mantido no objeto cashFlow enquanto o frontend migra para resultadoFinanceiro.",
    },
    "deficitCaixa": {
        "replacement": "cashDeficitAmount",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "dashboard_api.cashFlow", "next_types"],
        "reason": "Alias de negocio em portugues preservado enquanto novas integracoes usam campo canonico camelCase em ingles.",
    },
    "contasPendentes": {
        "replacement": "pendingAccountsAmount",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api.cashFlow", "dashboard_api.resultadoFinanceiro", "next_types"],
        "reason": "Alias de negocio em portugues preservado enquanto novas integracoes usam campo canonico camelCase em ingles.",
    },
    "contasPendentesTotal": {
        "replacement": "pendingAccountsAmount",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "next_types"],
        "reason": "Alias de topo preservado para compatibilidade com o frontend antigo e normalizadores transicionais.",
    },
    "saldo_previsto": {
        "replacement": "resultado_financeiro_previsto",
        "status": "alias_temporario",
        "surfaces": ["selectors_mes_financeiro", "templates_legados"],
        "reason": "Alias snake_case legado em telas Django antigas.",
    },
    "saldo_realizado": {
        "replacement": "resultado_financeiro_realizado",
        "status": "alias_temporario",
        "surfaces": ["selectors_mes_financeiro", "templates_legados"],
        "reason": "Alias snake_case legado em telas Django antigas.",
    },
    "saldo_previsto_fci": {
        "replacement": "resultado_financeiro_fci_projetado",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "templates_fci"],
        "reason": "Alias legado preservado enquanto FCI migra para resultado financeiro projetado.",
    },
    "saldo_realizado_fci": {
        "replacement": "resultado_financeiro_fci_realizado",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "templates_fci"],
        "reason": "Alias legado preservado enquanto FCI migra para resultado financeiro realizado.",
    },
    "saldo_previsto_fcf": {
        "replacement": "resultado_financeiro_fcf_projetado",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "templates_fcf"],
        "reason": "Alias legado preservado enquanto FCF migra para resultado financeiro projetado.",
    },
    "saldo_realizado_fcf": {
        "replacement": "resultado_financeiro_fcf_realizado",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "templates_fcf"],
        "reason": "Alias legado preservado enquanto FCF migra para resultado financeiro realizado.",
    },
    "total_em_aberto_fcf": {
        "replacement": "total_contas_pendentes_fcf",
        "status": "alias_temporario",
        "surfaces": ["dashboard_context", "templates_dashboard"],
        "reason": "Alias legado preservado enquanto FCF migra para total de contas pendentes.",
    },
    "subtotal_saldo_previsto": {
        "replacement": "subtotal_resultado_financeiro_projetado",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "templates_fci"],
        "reason": "Alias legado de grupo preservado enquanto FCI migra para subtotal de resultado financeiro projetado.",
    },
    "subtotal_saldo_realizado": {
        "replacement": "subtotal_resultado_financeiro_realizado",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "templates_fci"],
        "reason": "Alias legado de grupo preservado enquanto FCI migra para subtotal de resultado financeiro realizado.",
    },
    "saldo_previsto_acumulado": {
        "replacement": "resultado_financeiro_previsto_acumulado",
        "status": "alias_temporario",
        "surfaces": ["api_mes_financeiro", "templates_mes_financeiro"],
        "reason": "Alias legado de movimentacao mantido enquanto consumers migram para resultado financeiro acumulado.",
    },
    "saldo_realizado_acumulado": {
        "replacement": "resultado_financeiro_realizado_acumulado",
        "status": "alias_temporario",
        "surfaces": ["api_mes_financeiro", "templates_mes_financeiro"],
        "reason": "Alias legado de movimentacao mantido enquanto consumers migram para resultado financeiro realizado acumulado.",
    },
    "saldo_em_aberto": {
        "replacement": "valor_pendente_pagamento",
        "status": "alias_temporario",
        "surfaces": ["models", "selectors", "templates_legados"],
        "reason": "Campos físicos antigos ainda sustentam cálculos e histórico.",
    },
    "receita_aberta": {
        "replacement": "receita_pendente_recebimento",
        "status": "alias_temporario",
        "surfaces": ["mes_financeiro_api", "selectors_mes_financeiro"],
        "reason": "Total antigo preservado enquanto mês financeiro migra para receita pendente de recebimento.",
    },
    "divida_aberta": {
        "replacement": "divida_pendente_pagamento",
        "status": "alias_temporario",
        "surfaces": ["mes_financeiro_api", "selectors_mes_financeiro"],
        "reason": "Total antigo preservado enquanto mês financeiro migra para dívida pendente de pagamento.",
    },
    "credor": {
        "replacement": "creditorName",
        "status": "alias_temporario",
        "surfaces": ["models_dividas", "admin", "api_fcf", "templates_fcf"],
        "reason": "Campo textual preservado enquanto DividaFinanceira migra para cadastro mestre de credores.",
    },
    "creditor": {
        "replacement": "creditorName",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias textual mantido como label de exibicao; novas integracoes devem usar creditorId e creditorName.",
    },
    "credor_id": {
        "replacement": "creditorId",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Alias snake_case publicado para transicao de consumidores em portugues.",
    },
    "credor_nome": {
        "replacement": "creditorName",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado para exibicao do nome do credor cadastrado.",
    },
    "valorTotal": {
        "replacement": "settlementAmount",
        "status": "alias_temporario",
        "surfaces": ["api_baixas_financeiras_canonicas", "api_canonical_settlements"],
        "reason": "Alias legado do valor da baixa preservado enquanto consumers migram para settlementAmount.",
    },
    "valorBaixa": {
        "replacement": "settlementAmount",
        "status": "alias_temporario",
        "surfaces": ["api_baixas_financeiras_canonicas", "api_canonical_settlements"],
        "reason": "Alias em português preservado para transição; o campo canônico para Next.js é settlementAmount.",
    },
    "valor_baixa": {
        "replacement": "settlementAmount",
        "status": "alias_temporario",
        "surfaces": ["api_baixas_financeiras_canonicas", "api_canonical_settlements"],
        "reason": "Alias snake_case preservado para automações; o campo canônico para Next.js é settlementAmount.",
    },
    "valorLancamento": {
        "replacement": "ledgerAmount",
        "status": "alias_temporario",
        "surfaces": ["api_lancamentos_financeiros"],
        "reason": "Alias em português preservado para transição; o campo canônico para Next.js é ledgerAmount.",
    },
    "valor_lancamento": {
        "replacement": "ledgerAmount",
        "status": "alias_temporario",
        "surfaces": ["api_lancamentos_financeiros"],
        "reason": "Alias snake_case preservado para automações; o campo canônico para Next.js é ledgerAmount.",
    },
    "quantidade_parcelas_abertas": {
        "replacement": "quantidade_parcelas_pendentes",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "templates_fcf"],
        "reason": "Contagem antiga preservada enquanto FCF migra para parcelas pendentes.",
    },
    "quantidade_parcelas": {
        "replacement": "installmentsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado enquanto estatisticas FCF migram para contagens camelCase canonicas.",
    },
    "quantidade_parcelas_vencidas": {
        "replacement": "overdueInstallmentsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado enquanto estatisticas FCF migram para contagens camelCase canonicas.",
    },
    "quantidade_movimentacoes_financiamento": {
        "replacement": "financingMovementsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado enquanto estatisticas FCF migram para contagens camelCase canonicas.",
    },
    "quantidade_movimentacoes_financiamento_vencidas": {
        "replacement": "overdueFinancingMovementsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado enquanto estatisticas FCF migram para contagens camelCase canonicas.",
    },
    "openInstallmentsCount": {
        "replacement": "pendingInstallmentsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias em ingles antigo preservado enquanto consumers migram para contagem de parcelas pendentes.",
    },
    "quantidade_dividas": {
        "replacement": "pendingDebtsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "templates_fcf", "next_types"],
        "reason": "Nome generico preservado para compatibilidade; o significado correto e dividas com saldo financeiro real pendente.",
    },
    "debtsCount": {
        "replacement": "pendingDebtsCount",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias generico preservado para compatibilidade; use pendingDebtsCount para dividas pendentes ou listedDebtsCount para total listado.",
    },
    "eventos_abertos": {
        "replacement": "eventos_operacionais_ativos",
        "status": "alias_temporario",
        "surfaces": ["dashboard_context", "dashboard_api"],
        "reason": "Contagem antiga representa eventos ainda operacionais, não necessariamente um status textual aberto.",
    },
    "activeContractsCount": {
        "replacement": "activeOperationalEventsCount",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "next_summary"],
        "reason": "Campo antigo do resumo visual preservado enquanto o frontend migra para contagem explícita de eventos operacionais ativos.",
    },
    "saldo_aberto": {
        "replacement": "resultado_financeiro_pendente",
        "status": "alias_temporario",
        "surfaces": ["selectors_mes_financeiro", "mes_financeiro_api"],
        "reason": "Alias antigo mantido enquanto consumers migram para resultado financeiro pendente.",
    },
    "total_aberto": {
        "replacement": "total_contas_pendentes",
        "status": "alias_temporario",
        "surfaces": ["views_cadastros", "templates_legados"],
        "reason": "Alias antigo preservado em receitas/despesas enquanto templates e testes migram para contas pendentes.",
    },
    "total_em_aberto": {
        "replacement": "total_contas_pendentes",
        "status": "alias_temporario",
        "surfaces": ["selectors", "templates_legados"],
        "reason": "Agregacao antiga preservada como compatibilidade.",
    },
    "subtotal_em_aberto": {
        "replacement": "subtotal_contas_pendentes",
        "status": "alias_temporario",
        "surfaces": ["selectors", "templates_legados"],
        "reason": "Agregacao antiga de grupos preservada como compatibilidade.",
    },
    "total_saldo_eventos": {
        "replacement": "total_contas_pendentes_eventos",
        "status": "alias_temporario",
        "surfaces": ["selectors_dashboard_custos_evento", "templates_custos_por_evento"],
        "reason": "Total antigo de saldo em custos por evento agora tem alias explicito de contas pendentes.",
    },
    "saldo_total": {
        "replacement": "contas_pendentes_total",
        "status": "alias_temporario",
        "surfaces": ["selectors_dashboard_custos_evento", "templates_custos_por_evento"],
        "reason": "Campo de item preservado enquanto custos por evento migra para contas pendentes total.",
    },
    "subtotal_saldo_geral": {
        "replacement": "subtotal_contas_pendentes_geral",
        "status": "alias_temporario",
        "surfaces": ["selectors_dashboard_custos_evento", "templates_custos_por_evento"],
        "reason": "Subtotal antigo de saldo preservado como compatibilidade.",
    },
    "subtotal_saldo_custos_extras": {
        "replacement": "subtotal_contas_pendentes_custos_extras",
        "status": "alias_temporario",
        "surfaces": ["selectors_dashboard_custos_evento"],
        "reason": "Subtotal antigo de saldo dos extras preservado como compatibilidade.",
    },
    "saldos_por_evento": {
        "replacement": "contas_pendentes_por_evento",
        "status": "alias_temporario",
        "surfaces": ["selectors_dashboard_custos_evento"],
        "reason": "Mapa antigo de saldos preservado enquanto relatórios adotam contas pendentes por evento.",
    },
    "saldo_a_pagar": {
        "replacement": "valor_pendente_pagamento",
        "status": "alias_temporario",
        "surfaces": ["models", "admin", "templates_legados"],
        "reason": "Propriedade legada de despesas e custos extras preservada enquanto consumers migram para valor pendente de pagamento.",
    },
    "saldo_geral": {
        "replacement": "valor_pendente_pagamento",
        "status": "alias_temporario",
        "surfaces": ["models", "admin", "templates_legados"],
        "reason": "Propriedade legada de custos de servico preservada enquanto consumers migram para valor pendente de pagamento.",
    },
    "falta_cobrir": {
        "replacement": "deficit_caixa",
        "status": "alias_temporario",
        "surfaces": ["selectors", "templates_legados"],
        "reason": "Termo antigo mantido para não quebrar contexto de template.",
    },
    "origem_pagamento": {
        "replacement": "origem",
        "status": "alias_temporario",
        "surfaces": ["models", "admin", "templates_legados"],
        "reason": "Nome operacional antigo mantido enquanto despesas usam origem explícita.",
    },
    "realizedCashFlow": {
        "replacement": "cashBasisRealizedFlow",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "next_dashboard"],
        "reason": "Alias mantido enquanto o frontend adota a base de data explícita.",
    },
    "accumulatedFinancialResult": {
        "replacement": "accumulatedFinancialResultAmount",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "next_dashboard"],
        "reason": "Alias mantido enquanto a evolucao de caixa migra para valor acumulado canonico.",
    },
    "fonteDados": {
        "replacement": "dataSource",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes"],
        "reason": "Alias em português mantido durante a transição para leitura canônica.",
    },
    "fonte_dados": {
        "replacement": "dataSource",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api"],
        "reason": "Alias snake_case mantido para integrações transicionais.",
    },
    "canonicalFallbackReason": {
        "replacement": "readModelStatusReason",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes"],
        "reason": "Nome técnico antigo mantido enquanto consumidores migram para o motivo da fonte de leitura.",
    },
    "fallbackReason": {
        "replacement": "legacyReadReason",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes", "csv_obrigacoes"],
        "reason": "Alias interno do diagnóstico mantido durante a transição para leitura legada segura.",
    },
    "validateLegacyFallback": {
        "replacement": "validateLegacyRead",
        "status": "alias_temporario",
        "surfaces": ["validar_janela_canonical_first", "operationalChecklist"],
        "reason": "Nome antigo do passo de rollback mantido como alias para automações existentes.",
    },
    "read_model_source": {
        "replacement": "readModelSource",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api"],
        "reason": "Alias snake_case mantido para integrações transicionais.",
    },
    "fonteEscrita": {
        "replacement": "writeModelSource",
        "status": "alias_temporario",
        "surfaces": ["baixas_canonicas_api", "next_obrigacoes"],
        "reason": "Alias em portugues mantido para auditoria da origem de escrita da baixa.",
    },
    "fonte_escrita": {
        "replacement": "writeModelSource",
        "status": "alias_temporario",
        "surfaces": ["baixas_canonicas_api"],
        "reason": "Alias snake_case mantido para integrações transicionais.",
    },
    "tipoObrigacao": {
        "replacement": "obligationType",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes"],
        "reason": "Alias em português mantido enquanto o frontend consolida o nome canônico.",
    },
    "tipo_obrigacao": {
        "replacement": "obligationType",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api"],
        "reason": "Alias snake_case mantido para integrações transicionais.",
    },
    "data_inicial": {
        "replacement": "startDate",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "obrigacoes_api", "ledger_api", "canonical_settlements_api", "templates_legados"],
        "reason": "Alias em portugues mantido enquanto filtros antigos e telas Django usam nomes legados.",
    },
    "data_final": {
        "replacement": "endDate",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "obrigacoes_api", "ledger_api", "canonical_settlements_api", "templates_legados"],
        "reason": "Alias em portugues mantido enquanto filtros antigos e telas Django usam nomes legados.",
    },
    "contrato_codigo": {
        "replacement": "contractCode",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "canonical_settlements_api", "dimensioned_flows_api"],
        "reason": "Alias snake_case mantido para exibicao transicional do codigo de contrato.",
    },
    "costCenterId": {
        "replacement": "eventId",
        "status": "alias_temporario",
        "surfaces": [
            "dashboard_api",
            "api_mes_financeiro",
            "api_fci",
            "api_fcf",
            "obrigacoes_api",
            "ledger_api",
            "canonical_settlements_api",
            "next_filters",
        ],
        "reason": "Alias legado do filtro global de centro de custo mantido para compatibilidade; novas chamadas devem usar eventId.",
    },
    "evento": {
        "replacement": "eventId",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "obrigacoes_api", "ledger_api", "templates_legados"],
        "reason": "Alias de filtro mantido para compatibilidade com telas Django e integrações transicionais.",
    },
    "evento_id": {
        "replacement": "eventId",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "ledger_api", "canonical_settlements_api"],
        "reason": "Alias snake_case mantido enquanto filtros e tabelas migram para camelCase.",
    },
    "evento_nome": {
        "replacement": "eventName",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "canonical_settlements_api", "dimensioned_flows_api"],
        "reason": "Alias snake_case mantido para exibicao transicional do nome do evento.",
    },
    "evento_numero": {
        "replacement": "eventNumber",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "canonical_settlements_api", "dimensioned_flows_api"],
        "reason": "Alias snake_case mantido enquanto o campo físico `numero` continua congelado.",
    },
    "evento_label": {
        "replacement": "eventLabel",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "canonical_settlements_api", "dimensioned_flows_api"],
        "reason": "Alias snake_case mantido para exibicao transicional do rotulo do evento.",
    },
    "eventoLabel": {
        "replacement": "eventLabel",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes"],
        "reason": "Alias camelCase legado em portugues mantido enquanto o frontend migra para eventLabel.",
    },
    "cliente": {
        "replacement": "clientId",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "obrigacoes_api", "templates_legados"],
        "reason": "Alias de filtro mantido para compatibilidade com telas Django e integrações transicionais.",
    },
    "cliente_id": {
        "replacement": "clientId",
        "status": "alias_temporario",
        "surfaces": ["dashboard_api", "ledger_api", "canonical_settlements_api"],
        "reason": "Alias snake_case mantido enquanto filtros e tabelas migram para camelCase.",
    },
    "clienteLabel": {
        "replacement": "clientLabel",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes"],
        "reason": "Alias de rotulo mantido para compatibilidade com badges de filtro do frontend.",
    },
    "cliente_label": {
        "replacement": "clientLabel",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "next_obrigacoes"],
        "reason": "Alias snake_case mantido para compatibilidade com filtros transicionais.",
    },
    "cliente_nome": {
        "replacement": "clientName",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "canonical_settlements_api", "dimensioned_flows_api"],
        "reason": "Alias snake_case mantido para exibicao transicional do nome do cliente.",
    },
    "valor_pendente_pagamento": {
        "replacement": "pendingPaymentAmount",
        "status": "alias_temporario",
        "surfaces": ["admin_ajax", "mes_financeiro_api", "fci_fcf_api"],
        "reason": "Alias snake_case mantido para telas legadas que ainda leem valor pendente de pagamento.",
    },
    "valor_pendente_realizacao": {
        "replacement": "pendingRealizationAmount",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "api_fcf", "templates_legados"],
        "reason": "Alias snake_case mantido para valores previstos ainda não realizados em FCI/FCF.",
    },
    "saldo_restante": {
        "replacement": "pendingRealizationAmount",
        "status": "alias_temporario",
        "surfaces": ["models_fci_fcf", "api_fci", "templates_legados"],
        "reason": "Nome legado mantido enquanto models e templates antigos ainda usam saldo para pendência de realização.",
    },
    "rotulo_parcela": {
        "replacement": "installmentLabel",
        "status": "alias_temporario",
        "surfaces": ["admin_ajax", "fcf_api"],
        "reason": "Alias snake_case mantido para identificar parcelas em telas legadas.",
    },
    "disponivel_para_pagamento": {
        "replacement": "availableForPayment",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado enquanto consumidores usam o booleano canonico availableForPayment.",
    },
    "movementSourceType": {
        "replacement": "sourceType",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias especifico de movimentacao preservado enquanto consumers usam sourceType.",
    },
    "origem_movimentacao": {
        "replacement": "sourceType",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Alias snake_case preservado para indicar origem manual ou automatica da movimentacao FCF.",
    },
    "movementSourceTypeLabel": {
        "replacement": "sourceTypeLabel",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias especifico de movimentacao preservado enquanto consumers usam sourceTypeLabel.",
    },
    "origem_movimentacao_display": {
        "replacement": "sourceTypeLabel",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Alias snake_case preservado para exibicao do tipo de origem da movimentacao FCF.",
    },
    "isAutomaticFromDebt": {
        "replacement": "automaticFromDebt",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias booleano preservado enquanto consumers usam automaticFromDebt.",
    },
    "entrada_automatica_divida": {
        "replacement": "automaticFromDebt",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Alias snake_case preservado para entradas FCF automaticas geradas por dividas.",
    },
    "movementSourceTypes": {
        "replacement": "financingMovementSourceTypes",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias curto preservado enquanto consumers migram para a lista canonica de tipos de origem FCF.",
    },
    "origens_movimentacao_financiamento": {
        "replacement": "financingMovementSourceTypes",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Alias snake_case preservado para filtros legados de origem da movimentacao FCF.",
    },
    "divida_id": {
        "replacement": "debtId",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado para identificar a divida vinculada.",
    },
    "credor_divida_id": {
        "replacement": "debtCreditorId",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado para o credor cadastrado da divida vinculada.",
    },
    "debtCreditor": {
        "replacement": "debtCreditorName",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias textual preservado enquanto consumers usam debtCreditorName.",
    },
    "credor_divida": {
        "replacement": "debtCreditorName",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Alias snake_case preservado para exibicao do credor da divida vinculada.",
    },
    "nome_credor_divida": {
        "replacement": "debtCreditorName",
        "status": "alias_temporario",
        "surfaces": ["api_fcf", "next_types"],
        "reason": "Alias snake_case preservado para exibicao do credor da divida vinculada.",
    },
    "origem": {
        "replacement": "source",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "ledger_api", "canonical_settlements_api", "templates_legados"],
        "reason": "Alias em portugues mantido enquanto telas e filtros legados usam origem.",
    },
    "origem_obrigacao": {
        "replacement": "source",
        "status": "alias_temporario",
        "surfaces": ["ledger_api"],
        "reason": "Alias de filtro mantido para localizar lançamentos vinculados a obrigações.",
    },
    "source_id": {
        "replacement": "sourceId",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "views_obrigacoes"],
        "reason": "Alias snake_case mantido para integrações transicionais que filtram por origem.",
    },
    "origin_id": {
        "replacement": "sourceId",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "views_obrigacoes"],
        "reason": "Alias antigo mantido enquanto a API consolida sourceId como identificador preferencial.",
    },
    "source_detail": {
        "replacement": "sourceDetail",
        "status": "alias_temporario",
        "surfaces": ["ledger_api", "views_obrigacoes"],
        "reason": "Alias snake_case mantido para detalhes de origem como tipo de custo de serviço.",
    },
    "fluxo": {
        "replacement": "cashFlowGroup",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "ledger_api", "canonical_settlements_api", "templates_legados"],
        "reason": "Alias em portugues preservado enquanto filtros legados usam fluxo.",
    },
    "natureza": {
        "replacement": "nature",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "ledger_api", "canonical_settlements_api"],
        "reason": "Alias em portugues preservado enquanto filtros legados usam natureza.",
    },
    "situacao": {
        "replacement": "settlementStatus",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "templates_pagamentos", "next_obrigacoes"],
        "reason": "Alias de filtro legado mantido para situação de liquidação.",
    },
    "busca": {
        "replacement": "search",
        "status": "alias_temporario",
        "surfaces": ["obrigacoes_api", "ledger_api", "canonical_settlements_api", "templates_legados"],
        "reason": "Alias em portugues mantido para busca textual em telas antigas.",
    },
    "filtros": {
        "replacement": "filters",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "api_fcf", "api_mes_financeiro"],
        "reason": "Envelope antigo em português preservado enquanto o Next.js migra para filtros canônicos.",
    },
    "opcoes": {
        "replacement": "filterOptions",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "api_fcf", "api_mes_financeiro"],
        "reason": "Envelope antigo em português preservado enquanto o Next.js migra para opções de filtro canônicas.",
    },
    "totais": {
        "replacement": "totals",
        "status": "alias_temporario",
        "surfaces": ["api_fci", "api_fcf", "api_mes_financeiro"],
        "reason": "Envelope antigo em português preservado enquanto o Next.js migra para totais canônicos.",
    },
    "estatisticas": {
        "replacement": "statistics",
        "status": "alias_temporario",
        "surfaces": ["api_fcf"],
        "reason": "Envelope antigo em português preservado enquanto o Next.js migra para estatísticas operacionais canônicas.",
    },
}


INVENTARIO_USO_ALIASES_LEGADOS.update(
    {
        "receita_prevista": {
            "replacement": "plannedRevenueAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para totais camelCase canonicos.",
        },
        "receita_recebida": {
            "replacement": "receivedRevenueAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para totais camelCase canonicos.",
        },
        "custo_variavel": {
            "replacement": "variableCostAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado para o indicador tecnico de Custo Variavel do Mes Financeiro.",
        },
        "margem_contribuicao": {
            "replacement": "contributionMarginAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado para o indicador tecnico de Margem de Contribuicao do Mes Financeiro.",
        },
        "margem_contribuicao_percentual": {
            "replacement": "contributionMarginPercent",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado para o percentual de Margem de Contribuicao do Mes Financeiro.",
        },
        "lucro_operacional_ebit": {
            "replacement": "operatingProfitEbitAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado para o indicador tecnico de Lucro Operacional / EBIT do Mes Financeiro.",
        },
        "contas_previstas": {
            "replacement": "plannedPayablesAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para totais camelCase canonicos.",
        },
        "contas_pagas": {
            "replacement": "paidPayablesAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para totais camelCase canonicos.",
        },
        "contas_vencidas": {
            "replacement": "overdueAccountsAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para totais camelCase canonicos.",
        },
        "total_previsto_entrada": {
            "replacement": "plannedInflowAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "api_fcf", "next_types"],
            "reason": "Alias snake_case preservado enquanto FCI e FCF migram para totais camelCase canonicos.",
        },
        "total_previsto_saida": {
            "replacement": "plannedOutflowAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "api_fcf", "next_types"],
            "reason": "Alias snake_case preservado enquanto FCI e FCF migram para totais camelCase canonicos.",
        },
        "total_realizado_entrada": {
            "replacement": "realizedInflowAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "api_fcf", "next_types"],
            "reason": "Alias snake_case preservado enquanto FCI e FCF migram para totais camelCase canonicos.",
        },
        "total_realizado_saida": {
            "replacement": "realizedOutflowAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "api_fcf", "next_types"],
            "reason": "Alias snake_case preservado enquanto FCI e FCF migram para totais camelCase canonicos.",
        },
        "entradas_investimento_projetadas": {
            "replacement": "projectedInflowAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias antigo de FCI mantido enquanto o frontend consome entradas projetadas canonicas.",
        },
        "saidas_investimento_projetadas": {
            "replacement": "projectedOutflowAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias antigo de FCI mantido enquanto o frontend consome saidas projetadas canonicas.",
        },
        "resultado_financeiro_previsto": {
            "replacement": "plannedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para resultado financeiro canonico.",
        },
        "resultado_financeiro_projetado": {
            "replacement": "projectedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para resultado financeiro canonico.",
        },
        "resultado_financeiro_realizado": {
            "replacement": "realizedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para resultado financeiro canonico.",
        },
        "resultado_financeiro_pendente": {
            "replacement": "pendingFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para resultado financeiro canonico.",
        },
        "resultado_financeiro_fci_previsto": {
            "replacement": "plannedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias especifico de FCI mantido enquanto o frontend consome resultado previsto canonico.",
        },
        "resultado_financeiro_fci_projetado": {
            "replacement": "projectedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias especifico de FCI mantido enquanto o frontend consome resultado projetado canonico.",
        },
        "resultado_financeiro_fci_realizado": {
            "replacement": "realizedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias especifico de FCI mantido enquanto o frontend consome resultado realizado canonico.",
        },
        "resultado_financeiro_fcf_projetado": {
            "replacement": "projectedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fcf", "templates_fcf", "next_types"],
            "reason": "Alias especifico de FCF mantido enquanto o frontend consome resultado projetado canonico.",
        },
        "resultado_financeiro_fcf_realizado": {
            "replacement": "realizedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fcf", "templates_fcf", "next_types"],
            "reason": "Alias especifico de FCF mantido enquanto o frontend consome resultado realizado canonico.",
        },
        "resultado_financeiro_investimentos_projetado": {
            "replacement": "projectedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias antigo de investimentos mantido enquanto FCI usa resultado financeiro canonico.",
        },
        "resultado_financeiro_investimentos_realizado": {
            "replacement": "realizedFinancialResultAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fci", "templates_fci", "next_types"],
            "reason": "Alias antigo de investimentos mantido enquanto FCI usa resultado financeiro canonico.",
        },
        "total_contas_pendentes": {
            "replacement": "pendingAccountsAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado enquanto Mes Financeiro migra para contas pendentes canonicas.",
        },
        "total_contas_vencidas": {
            "replacement": "overdueAccountsAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fcf", "next_types"],
            "reason": "Alias snake_case preservado enquanto FCF migra para totais vencidos camelCase canonicos.",
        },
        "total_vencido": {
            "replacement": "overdueAccountsAmount",
            "status": "alias_temporario",
            "surfaces": ["api_fcf", "templates_fcf", "next_types"],
            "reason": "Alias antigo preservado enquanto FCF migra para totais vencidos camelCase canonicos.",
        },
        "deficit_caixa": {
            "replacement": "cashDeficitAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado para transicao do indicador de deficit de caixa.",
        },
        "caixa_disponivel": {
            "replacement": "availableCashAmount",
            "status": "alias_temporario",
            "surfaces": ["api_mes_financeiro", "templates_mes_financeiro", "next_types"],
            "reason": "Alias snake_case preservado para transicao do indicador de caixa disponivel.",
        },
    }
)


CAMPOS_FISICOS_PENDENTES_MIGRACAO = (
    "numero",
    "saldo_previsto",
    "saldo_realizado",
    "saldo_em_aberto",
)


CAMPOS_GENERICOS_CONGELADOS = {
    "numero": {
        "replacement": "contractCode quando for código visível de orçamento/evento",
        "scope": "novos payloads de contrato visual, evento e orçamento",
        "policy": "Não criar novos campos físicos genéricos com esse nome sem qualificar a dimensão operacional.",
    },
    "saldo": {
        "replacement": "resultado_financeiro, valor_pendente ou deficit_caixa",
        "scope": "novos selectors, serializers, APIs e contexts",
        "policy": "Não criar novos campos genéricos de saldo sem qualificador financeiro.",
    },
    "em_aberto": {
        "replacement": "contas_pendentes ou valor_pendente",
        "scope": "novos agregados e labels de dashboard",
        "policy": "Usar pendente/liquidado para diferenciar contas não quitadas.",
    },
    "pagamento": {
        "replacement": "baixa_financeira quando representar liquidação realizada",
        "scope": "novos models canônicos, APIs e relatórios financeiros",
        "policy": "Usar pagamento apenas como linguagem operacional; no domínio financeiro canônico, usar baixa.",
    },
}


ALIASES_VALORES_NEGOCIO = {
    "settlementStatus": {
        "pago": {
            "canonicalValue": "liquidado",
            "scope": {"obligationType": "pagar"},
            "status": "alias_entrada",
            "reason": "Linguagem operacional aceita em contas a pagar; internamente o status canônico continua liquidado.",
        },
        "recebido": {
            "canonicalValue": "liquidado",
            "scope": {"obligationType": "receber"},
            "status": "alias_entrada",
            "reason": "Linguagem operacional aceita em contas a receber; internamente o status canônico continua liquidado.",
        },
    },
}


RENAMES_FISICOS_PLANEJADOS = {
    "Orcamento.numero": {
        "replacement": "campo físico preservado; publicado como contractCode",
        "phase": VERSAO_REMOCAO_ALIASES_LEGADOS,
        "requires": ["frontend_usando_contractCode", "evento_orcamento_como_dimensao_contabil"],
    },
    "Evento.numero": {
        "replacement": "código técnico do evento; contrato visual vem de Evento.orcamento.numero",
        "phase": VERSAO_REMOCAO_ALIASES_LEGADOS,
        "requires": ["frontend_usando_eventId_contractCode", "filtros_por_contractCode_do_evento"],
    },
    "saldo_em_aberto": {
        "replacement": "valor_pendente_pagamento / valor_pendente_recebimento",
        "phase": VERSAO_REMOCAO_ALIASES_LEGADOS,
        "requires": ["migrations_pequenas_por_model", "templates_sem_alias_antigo"],
    },
}


POLITICA_REMOCAO_ALIASES = {
    "currentVersion": VERSAO_NOMENCLATURA_FINANCEIRA,
    "removeOnlyInVersion": VERSAO_REMOCAO_ALIASES_LEGADOS,
    "rule": "Não remover aliases nem renomear campos físicos enquanto APIs e frontend v2 dependem deles.",
}


def montar_metadados_nomenclatura_financeira():
    return {
        "version": VERSAO_NOMENCLATURA_FINANCEIRA,
        "canonicalFields": TERMOS_CANONICOS_FINANCEIROS,
        "legacyAliases": ALIASES_LEGADOS_FINANCEIROS,
        "legacyAliasUsage": INVENTARIO_USO_ALIASES_LEGADOS,
        "deprecatedAliases": INVENTARIO_USO_ALIASES_LEGADOS,
        "frozenGenericFields": CAMPOS_GENERICOS_CONGELADOS,
        "businessValueAliases": ALIASES_VALORES_NEGOCIO,
        "physicalFieldsPendingMigration": list(CAMPOS_FISICOS_PENDENTES_MIGRACAO),
        "plannedPhysicalRenames": RENAMES_FISICOS_PLANEJADOS,
        "aliasRemovalPolicy": POLITICA_REMOCAO_ALIASES,
    }
