# Plano PM-35 - Migracao incremental de `GET/POST /api/fcf/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar de forma incremental e controlada o endpoint `GET/POST /api/fcf/` para
Django REST Framework, preservando integralmente o contrato atual consumido
pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da view de FCF, sem alterar regra de
negocio, permissoes, CSRF, filtros, aliases, status HTTP, payloads, selectors,
serializers manuais, signals, lancamentos financeiros, obrigacoes canonicas,
baixas canonicas ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET/POST /api/fcf/` em testes antes da
  migracao.
- Migrar somente a view `api_financiamentos`.
- Manter a URL atual `/api/fcf/`.
- Manter o nome de rota `caixa:api_financiamentos`.
- Manter os metodos `GET` e `POST`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` apenas na borda.
- Preservar `405` manual atual sem promover para `405` padrao Django/DRF.
- Preservar CSRF real no `POST`.
- Preservar permissoes manuais:
  - `GET` exige `caixa.view_parceladivida`;
  - `POST` exige `caixa.view_parceladivida` e
    `caixa.add_financiamentomovimentacao`.
- Preservar filtros, aliases, defaults e validacoes atuais.
- Reaproveitar selectors, serializers manuais e helpers atuais.
- Preservar signals e efeitos financeiros atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `/api/fcf/debts/`.
- `/api/fcf/creditors/`.
- Pagamento/liquidacao de parcelas FCF.
- Obrigacoes financeiras.
- Exportacao de obrigacoes.
- Baixas financeiras canonicas.
- Modelagem financeira canonica.
- Dashboard financeiro.
- Mes financeiro.
- Lancamentos financeiros.
- FCI.
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
- Criacao de financiamento/movimentacao real na etapa de planejamento.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, migrar somente `GET/POST /api/fcf/`.

Como o `POST` de FCF cria movimentacao de financiamento e aciona efeitos
financeiros por signals, a PM deve manter a regra de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, filtros, aliases,
validacoes, defaults, signals, efeitos financeiros ou comportamento runtime
apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-35.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_financiamentos.py`.
- `caixa/permissions.py`.
- `caixa/selectors_financiamentos.py`.
- `caixa/serializers_financiamentos.py`.
- `caixa/models_fcf.py`.
- `caixa/signals.py`.
- `caixa/services_lancamentos.py`.
- `caixa/services_modelagem_canonica.py`.
- `caixa/tests.py`.

View atual:

- `api_financiamentos`.

Rota atual:

- `path("api/fcf/", api_financiamentos, name="api_financiamentos")`.

Nome de rota:

- `caixa:api_financiamentos`.

Implementacao atual:

- Django puro.
- Usa `JsonResponse` e `api_no_store_json_response`.
- Ainda nao esta migrado para DRF.

Decorador atual:

- `@require_api_permission(FINANCIAL_DEBT_INSTALLMENTS_PERMISSION)`.

Permissoes atuais:

- `FINANCIAL_DEBT_INSTALLMENTS_PERMISSION = caixa.view_parceladivida`.
- `ADD_FINANCIAL_FINANCING_MOVEMENT_PERMISSION =
  caixa.add_financiamentomovimentacao`.
- `ADD_FINANCIAL_DEBT_PERMISSION = caixa.add_dividafinanceira`.

Metodo `GET`:

- Exige usuario autenticado.
- Exige `caixa.view_parceladivida`.
- Monta payload via `montar_payload_financiamentos_api`.
- Acrescenta `permissions.canCreate` conforme `caixa.add_dividafinanceira`.
- Acrescenta `permissions.canCreateDebt` conforme `caixa.add_dividafinanceira`.
- Acrescenta `permissions.canCreateFinancingMovement` conforme
  `caixa.add_financiamentomovimentacao`.

Metodo `POST`:

- Exige usuario autenticado.
- Exige `caixa.view_parceladivida` pelo wrapper externo.
- Exige `caixa.add_financiamentomovimentacao` dentro de
  `_api_criar_movimentacao_financiamento`.
- Exige `Content-Type: application/json`.
- Cria `FinanciamentoMovimentacao` por `_financing_movement_from_payload`.
- Retorna `201` com `data.financingMovement` e `data.message`.

Metodos nao permitidos:

- Metodos diferentes de `GET` e `POST` retornam `405` manual.
- Payload atual:

```json
{"detail": "Metodo nao permitido."}
```

- Nao ha header `Allow` no contrato manual atual.
- A resposta JSON recebe headers no-store via `require_api_permission`.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado sem `caixa.view_parceladivida`:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento no `POST` para usuario com `caixa.view_parceladivida`, mas sem
`caixa.add_financiamentomovimentacao`:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

CSRF atual:

- `POST` usa CSRF real do Django.
- Sem token valido, a requisicao deve ser bloqueada antes da view com `403`
  HTML.
- A migracao nao pode alterar CSRF global.

Content-Type no `POST`:

- Aceito: `application/json`.
- Qualquer outro `Content-Type` retorna `415`:

```json
{"detail": "Content-Type deve ser application/json."}
```

JSON invalido:

- JSON invalido, body nao UTF-8 ou body JSON nao-dict retornam `400`:

```json
{"detail": "JSON invalido."}
```

Payload aceito no `POST`:

- `description` / `descricao`.
- `category` / `categoria`.
- `flowType` / `tipo_fluxo`.
- `plannedAmount` / `valor_previsto`.
- `realizedAmount` / `valor_realizado`.
- `plannedDate` / `data_prevista`.
- `realizedDate` / `data_realizacao`.
- `eventId` / `evento` / `evento_id`.
- `notes` / `observacao`.

Defaults e normalizacoes do `POST`:

- `realizedAmount` default: `0.00`.
- Se `realizedAmount > 0` e `realizedDate` nao for informado, usa
  `plannedDate`.
- Valores decimais aceitam virgula ou ponto por conversao com `Decimal`.
- Evento ausente e aceito.
- Evento invalido ou inexistente retorna erro de validacao em `eventId`.

Validacoes principais:

- `plannedAmount` invalido retorna erro em `plannedAmount`.
- `realizedAmount` invalido retorna erro em `realizedAmount`.
- `plannedDate` invalida retorna erro em `plannedDate`.
- Evento invalido retorna erro em `eventId`.
- Evento inexistente retorna erro em `eventId`.
- Validacoes do model `FinanciamentoMovimentacao` continuam valendo:
  - valores nao negativos;
  - valor realizado nao maior que previsto;
  - choices validos de categoria, tipo de fluxo e status;
  - dimensao operacional por evento;
  - caixa suficiente para aumento de saida realizada;
  - status calculado por valor previsto/realizado.

Shape de erro de validacao:

```json
{"errors": {}}
```

Shape top-level do `GET` sucesso:

- `filters` / `filtros`.
- `filterOptions` / `opcoes`.
- `totals` / `totais`.
- `statistics` / `estatisticas`.
- `projectedFinancingFlow`.
- `realizedFinancingFlow`.
- `dateBasis`.
- `debts` / `dividas`.
- `installments` / `parcelas`.
- `financingMovements` / `movimentacoes_financiamento`.
- `creditorGroups` / `grupos_credor`.
- `permissions`.

`permissions`:

```json
{
  "canCreate": true,
  "canCreateDebt": true,
  "canCreateFinancingMovement": true
}
```

Filtros HTTP canonicos aceitos no `GET`:

- `startDate`.
- `endDate`.
- `type`.
- `status`.
- `creditor`.
- `creditorId`.
- `sourceType`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `period`.
- `quickPeriod`.

Aliases internos no selector:

- `data_inicial`.
- `data_final`.
- `tipo`.
- `credor`.
- `credor_id`.
- `movementSourceType`.
- `origem_movimentacao`.
- `automaticFromDebt`.
- `evento`.
- `evento_id`.
- `costCenterId`.
- `cliente`.
- `cliente_id`.
- `contrato_codigo`.

Observacao:

- A PM deve preservar o comportamento atual desses aliases sem promover novos
  contratos HTTP sem decisao explicita.

Totais/agregacoes retornadas:

- `total_previsto_entrada`.
- `total_previsto_saida`.
- `total_realizado_entrada`.
- `total_realizado_saida`.
- `saldo_previsto_fcf`.
- `saldo_realizado_fcf`.
- `resultado_financeiro_fcf_projetado`.
- `resultado_financeiro_fcf_realizado`.
- `total_contas_pendentes`.
- `total_em_aberto`.
- `total_contas_vencidas`.
- `total_vencido`.
- `contas_pendentes`.
- `contas_vencidas`.
- `total_parcelas_previsto_saida`.
- `total_parcelas_realizado_saida`.
- `total_parcelas_contas_pendentes`.
- `total_movimentacoes_financiamento_previsto_entrada`.
- `total_movimentacoes_financiamento_previsto_saida`.
- `total_movimentacoes_financiamento_realizado_entrada`.
- `total_movimentacoes_financiamento_realizado_saida`.
- `total_movimentacoes_financiamento_contas_pendentes`.
- Aliases camelCase em `totals`.

Estatisticas retornadas:

- `quantidade_dividas`.
- `quantidade_dividas_pendentes`.
- `quantidade_dividas_listadas`.
- `quantidade_parcelas`.
- `quantidade_parcelas_vencidas`.
- `quantidade_movimentacoes_financiamento`.
- `quantidade_movimentacoes_financiamento_vencidas`.
- `quantidade_movimentacoes_financiamento_automaticas`.
- `quantidade_movimentacoes_financiamento_manuais`.
- Aliases camelCase em `statistics`.

Shape do `POST` sucesso:

```json
{
  "data": {
    "financingMovement": {},
    "message": "Movimentacao FCF cadastrada com sucesso."
  }
}
```

Shape de `financingMovement`:

- `id`.
- `description`.
- `financingMovementDescription`.
- `descricao`.
- `category`.
- `categoria`.
- `categoryLabel`.
- `categoria_display`.
- `flowType`.
- `tipo_fluxo`.
- `flowTypeLabel`.
- `tipo_fluxo_display`.
- `plannedAmount`.
- `valor_previsto`.
- `realizedAmount`.
- `valor_realizado`.
- `pendingAmount`.
- `pendingRealizationAmount`.
- `valor_pendente_realizacao`.
- `plannedDate`.
- `data_prevista`.
- `realizedDate`.
- `data_realizacao`.
- `status`.
- `statusLabel`.
- `status_display`.
- `sourceType`.
- `movementSourceType`.
- `origem_movimentacao`.
- `sourceTypeLabel`.
- `movementSourceTypeLabel`.
- `origem_movimentacao_display`.
- `automaticFromDebt`.
- `isAutomaticFromDebt`.
- `entrada_automatica_divida`.
- `debtId`.
- `divida_id`.
- `debtCreditorId`.
- `credor_divida_id`.
- `debtCreditor`.
- `credor_divida`.
- `debtCreditorName`.
- `nome_credor_divida`.
- `debtDescription`.
- `descricao_divida`.
- `dias_atraso`.
- `overdueDays`.
- Campos de dimensao operacional serializados por
  `serializar_dimensao_operacional`.

Status codes atuais:

- `200` para `GET` sucesso.
- `201` para `POST` sucesso.
- `400` para JSON invalido/body nao-dict e validacoes.
- `401` para anonimo.
- `403` para usuario sem permissao.
- `405` manual para metodo nao permitido.
- `415` para `Content-Type` invalido no `POST`.

Headers relevantes:

- Respostas JSON devem ter `Content-Type: application/json`.
- Respostas JSON controladas pela API devem ter `Cache-Control` com `no-store`.
- `405` manual atual nao deve ganhar header `Allow` sem decisao explicita.

Efeitos colaterais do `POST`:

- Cria `FinanciamentoMovimentacao`.
- Nao cria `DividaFinanceira`; isso pertence a `/api/fcf/debts/`.
- Nao cria `ParcelaDivida`; isso pertence a `/api/fcf/debts/`.
- Ao salvar `FinanciamentoMovimentacao`, signals executam:
  - `sincronizar_lancamento_financiamento`;
  - `sincronizar_obrigacao_financiamento_canonica`;
  - `sincronizar_baixa_canonica_por_origem(
    "financiamento_movimentacao", instance)`.
- Pode criar/atualizar `LancamentoFinanceiro` quando `valor_realizado > 0` e
  status nao for cancelado.
- Cria/atualiza `ObrigacaoFinanceira` canonica.
- Pode criar/remover `BaixaFinanceira` canonica conforme lancamento.
- Impacta FCF, caixa, dashboard, mes financeiro, obrigacoes e lancamentos por
  meio das sincronizacoes existentes.

Transacoes:

- Nao ha `transaction.atomic` explicito na view `api_financiamentos`.
- Esta PM nao deve alterar esse comportamento.

Testes existentes:

- Rota `/api/fcf/`.
- Anonimo `401` para FCI/FCF.
- `GET` sucesso com `caixa.view_parceladivida`.
- Contrato JSON do `GET`.
- Headers JSON/no-store em GET de sucesso.
- Permissao `permissions.canCreate`, `canCreateDebt` e
  `canCreateFinancingMovement`.
- Filtros por `creditor`, `creditorId`, `startDate`, `endDate`, `period`,
  `quickPeriod`, `type`, `status` e `sourceType`.
- Descarte de filtros invalidos de `type`, `status` e `sourceType`.
- Inclusao de movimentacoes FCF manuais e automaticas separadas de parcelas.
- Action hints de pagamento conforme permissao.
- Query count do contexto de FCF.
- Testes de divida FCF em `/api/fcf/debts/`, fora do escopo desta PM.
- Testes de obrigacoes/liquidacao que usam origem `financiamento_movimentacao`.

Lacunas identificadas:

- GET autenticado sem `caixa.view_parceladivida`.
- POST anonimo.
- POST sem `caixa.view_parceladivida`.
- POST com `caixa.view_parceladivida`, mas sem
  `caixa.add_financiamentomovimentacao`.
- CSRF real no POST.
- `Content-Type` invalido `415`.
- JSON invalido/body nao-dict `400`.
- Validacoes criticas com `{"errors": ...}`.
- Evento inexistente/invalido.
- Shape completo do POST sucesso.
- Shape completo de `financingMovement`.
- `405` manual sem `Allow`.
- Headers JSON/no-store.
- Efeitos colaterais do POST:
  - cria `FinanciamentoMovimentacao`;
  - nao cria `DividaFinanceira`;
  - nao cria `ParcelaDivida`;
  - sincroniza lancamento;
  - sincroniza obrigacao canonica;
  - sincroniza baixa canonica quando aplicavel;
  - nao duplica lancamento/obrigacao/baixa.

## Riscos especificos do FCF

- `POST` cria entidade financeira real.
- Signals sincronizam ledger, obrigacoes e baixas canonicas.
- Alterar parsing de body via DRF pode mudar `Content-Type`, JSON invalido e
  body nao-dict.
- DRF pode trocar o `405` manual atual por `405` padrao com `Allow`.
- Permissao global DRF pode mudar o contrato de `401`/`403`.
- `SessionAuthentication` pode alterar o ponto de bloqueio de CSRF se a ordem
  de decorators nao for controlada.
- Valores realizados podem afetar caixa, status e disponibilidade.
- Validacoes de model e services podem ter efeitos indiretos em totais.
- O endpoint mistura parcelas de dividas, movimentacoes manuais, movimentacoes
  automaticas, grupos por credor, totais e estatisticas.
- Schema OpenAPI pode ficar generico, mas isso nao justifica mudar runtime.

## Guardrails

- Nao criar financiamento/movimentacao real durante planejamento.
- Em testes de criacao, usar banco de teste e fixtures controladas.
- Nao acessar `request.data` se isso mudar `Content-Type`/JSON invalido.
- Nao trocar o `405` manual por DRF/Django padrao.
- Nao criar serializer DRF.
- Nao criar ViewSet ou ModelViewSet.
- Nao alterar `FinanciamentoMovimentacao`.
- Nao alterar `DividaFinanceira`.
- Nao alterar `ParcelaDivida`.
- Nao alterar signals.
- Nao alterar services de lancamento, obrigacao ou baixa.
- Nao alterar selectors ou serializers manuais.
- Nao alterar `/api/fcf/debts/`, credores, liquidacao, obrigacoes, dashboard ou
  outros endpoints financeiros.
- Nao alterar frontend, settings, CORS, CSRF global ou auth global.
- Preservar runtime mesmo que o schema OpenAPI fique generico.

## Fases

### PM-35.1 - Diagnostico read-only

Status: concluida.

Objetivo:

- Mapear contrato atual de `GET/POST /api/fcf/`.
- Identificar arquivos, permissoes, CSRF, filtros, aliases, payloads, headers,
  efeitos colaterais e lacunas de teste.

Resultado:

- Endpoint permanece Django puro.
- Contrato atual foi mapeado por leitura de codigo e testes existentes.
- Nenhum arquivo foi alterado.
- Nenhum financiamento/movimentacao real foi criado.

### PM-35.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.

Cobrir:

- `GET` anonimo `401`.
- `GET` autenticado sem `caixa.view_parceladivida` `403`.
- `GET` com `caixa.view_parceladivida` retorna `200`.
- `POST` anonimo `401`.
- `POST` autenticado sem `caixa.view_parceladivida` `403`.
- `POST` com `caixa.view_parceladivida`, mas sem
  `caixa.add_financiamentomovimentacao`, retorna `403`.
- CSRF real: `POST` sem token valido bloqueia antes da view com `403` HTML.
- `POST` com CSRF valido chega na view.
- `Content-Type` invalido retorna `415`.
- JSON invalido retorna `400`.
- Body JSON nao-dict retorna `400`.
- Validacoes criticas retornam `{"errors": ...}`.
- Evento inexistente/invalido retorna erro de validacao.
- Metodos nao permitidos preservam `405` manual:

```json
{"detail": "Metodo nao permitido."}
```

- `405` manual nao deve ganhar header `Allow`, se esse for o contrato atual.
- Headers JSON/no-store em respostas JSON.
- Shape completo do `GET`:
  - `filters` / `filtros`;
  - `filterOptions` / `opcoes`;
  - `totals` / `totais`;
  - `statistics` / `estatisticas`;
  - `projectedFinancingFlow`;
  - `realizedFinancingFlow`;
  - `dateBasis`;
  - `debts` / `dividas`;
  - `installments` / `parcelas`;
  - `financingMovements` / `movimentacoes_financiamento`;
  - `creditorGroups` / `grupos_credor`;
  - `permissions`.
- Shape completo do `POST` sucesso:
  - `data.financingMovement`;
  - `data.message`.
- Shape completo de `financingMovement`.
- Filtros GET preservados:
  - `startDate`;
  - `endDate`;
  - `type`;
  - `status`;
  - `creditor`;
  - `creditorId`;
  - `sourceType`;
  - `contractCode`;
  - `eventId`;
  - `clientId`;
  - `period`;
  - `quickPeriod`.
- Aliases POST preservados:
  - `description` / `descricao`;
  - `category` / `categoria`;
  - `flowType` / `tipo_fluxo`;
  - `plannedAmount` / `valor_previsto`;
  - `realizedAmount` / `valor_realizado`;
  - `plannedDate` / `data_prevista`;
  - `realizedDate` / `data_realizacao`;
  - `eventId` / `evento` / `evento_id`;
  - `notes` / `observacao`.
- Default `realizedAmount = 0.00` preservado.
- Regra `realizedAmount > 0` sem `realizedDate` usa `plannedDate`.
- Efeitos colaterais preservados:
  - cria `FinanciamentoMovimentacao`;
  - nao cria `DividaFinanceira`;
  - nao cria `ParcelaDivida`;
  - sincroniza `LancamentoFinanceiro` quando aplicavel;
  - sincroniza `ObrigacaoFinanceira` canonica;
  - sincroniza `BaixaFinanceira` canonica quando aplicavel;
  - nao duplica lancamento/obrigacao/baixa.

Comandos previstos:

```bash
python manage.py check
python manage.py test caixa.tests.FiltrosHtmlTests
```

Criterio de aceite da fase:

- Testes focados passam.
- Nenhum arquivo runtime alterado.
- Endpoint ainda nao migrado para DRF.

### PM-35.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Migrar somente `api_financiamentos` para DRF, preservando o contrato runtime
  congelado na PM-35.2.

Regras:

- Converter somente `api_financiamentos`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` apenas na borda.
- Preservar `405` manual sem `Allow`.
- Preservar CSRF real no `POST`.
- Preservar permissoes manuais:
  - `GET` exige `view_parceladivida`;
  - `POST` exige `view_parceladivida` + `add_financiamentomovimentacao`.
- Preservar `Content-Type`, JSON invalido e body nao-dict atuais.
- Preservar filtros, aliases, defaults e validacoes.
- Preservar signals/efeitos financeiros atuais.
- Reaproveitar selectors, serializers manuais e helpers atuais.
- Nao criar Serializer, ViewSet ou ModelViewSet.
- Nao mexer em `/api/fcf/debts/`, credores, liquidacao, obrigacoes, dashboard
  ou outros endpoints financeiros.

Comandos previstos:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
```

Criterio de aceite da fase:

- Testes focados passam.
- `check` passa.
- `spectacular --validate` passa, mesmo que o schema seja generico.
- OpenAPI inclui `/api/fcf/`.
- Nenhum contrato runtime alterado.

### PM-35.4 - Validacao completa

Status: concluida.

Objetivo:

- Validar que a migracao nao causou regressao em FCF, ledger, obrigacoes,
  baixas canonicas e suite geral.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Validar:

- Testes focados de FCF.
- Testes relacionados existentes de financiamento/ledger/obrigacao canonica.
- Suite completa.
- Sem mudanca em `/api/fcf/debts/`, credores, liquidacao, obrigacoes,
  dashboard ou outros endpoints.
- Sem mudanca em settings, CORS, CSRF global ou autenticacao global.

Criterio de aceite da fase:

- Todos os comandos passam.
- Sem mudanca de contrato.
- Sem mudanca de efeitos financeiros.

### PM-35.5 - Encerramento

Status: concluida.

Objetivo:

- Atualizar este documento com registro final da execucao.

Registrar:

- Arquivos alterados.
- Testes criados/alterados.
- Comandos executados e resultados.
- Resultado do `check`.
- Resultado do `spectacular --validate`.
- Resultado dos testes focados.
- Resultado da suite completa.
- Warnings, se houver.
- Confirmacao de que `/api/fcf/debts/`, credores, liquidacao, obrigacoes,
  dashboard e outros endpoints financeiros nao foram alterados.
- Confirmacao de que settings, CORS, CSRF global e auth global nao foram
  alterados.
- Confirmacao de pronto ou nao para commit manual.

## Criterios de aceite da PM

- `GET/POST /api/fcf/` migrado para DRF.
- URL e nome de rota preservados.
- Metodos `GET` e `POST` preservados.
- `405` manual preservado.
- CSRF real preservado.
- Anonimo recebe `401` atual.
- Usuario sem permissao recebe `403` atual.
- `POST` sem `add_financiamentomovimentacao` recebe `403` atual.
- `Content-Type` invalido preservado como `415`.
- JSON invalido/body nao-dict preservado como `400`.
- Shape do `GET` preservado.
- Shape do `POST` preservado.
- Shape de `financingMovement` preservado.
- Filtros e aliases preservados.
- Defaults e validacoes preservados.
- Signals e efeitos financeiros preservados.
- `/api/fcf/debts/`, credores, liquidacao, obrigacoes, dashboard e outros
  endpoints nao alterados.
- Frontend nao alterado.
- Settings, CORS, CSRF global e auth global nao alterados.
- Sem Serializer DRF, ViewSet ou ModelViewSet.
- `python manage.py check` passa.
- `python manage.py spectacular --validate` passa.
- Testes focados passam.
- Suite completa passa.

## Criterios de bloqueio

Parar imediatamente se:

- CSRF mudar.
- `Content-Type` invalido mudar.
- JSON invalido/body nao-dict mudar.
- `401`, `403`, `405`, `415` ou status de sucesso mudarem.
- `405` manual ganhar/remover caracteristicas fora do contrato atual.
- Shape do `GET` mudar.
- Shape do `POST` mudar.
- Shape de `financingMovement` mudar.
- Algum filtro ou alias mudar.
- Defaults mudarem.
- Validacoes mudarem.
- Lancamento, obrigacao ou baixa canonica duplicar.
- Algum efeito financeiro mudar.
- `/api/fcf/debts/`, credores, liquidacao, obrigacoes, dashboard ou outros
  endpoints precisarem ser alterados.
- For necessario criar Serializer, ViewSet ou ModelViewSet.
- For necessaria decisao arquitetural fora do escopo.

## Estrategia de rollback

Se a migracao causar qualquer divergencia de contrato:

- Reverter apenas as alteracoes da PM-35.3 em `api_financiamentos`.
- Manter os testes de paridade da PM-35.2, se eles estiverem corretos e
  representarem o contrato atual.
- Remover somente ajustes de teste que dependam da implementacao migrada.
- Confirmar que `GET/POST /api/fcf/` voltou ao comportamento Django puro.
- Rodar testes focados de FCF e `python manage.py check`.

Nao usar rollback destrutivo de git sem aprovacao explicita.

## Registro de execucao

### PM-35.1

Status: concluida.

Resumo:

- Diagnostico read-only realizado.
- Nenhum arquivo alterado.
- Nenhum financiamento/movimentacao real criado.
- Contrato atual documentado neste plano.

### PM-35.2

Status: concluida.

Resumo:

- Testes de paridade de `GET/POST /api/fcf/` criados em `caixa/tests.py`.
- O contrato de autenticacao, permissoes, CSRF real, `Content-Type`, JSON
  invalido, validacoes, `405` manual, headers JSON/no-store, filtros, aliases,
  defaults, shapes e efeitos financeiros foi congelado antes da migracao.
- Foram criados 6 testes focados de FCF:
  - `test_api_financiamentos_preserva_auth_permissoes_e_headers`;
  - `test_api_financiamentos_preserva_csrf_real_no_post`;
  - `test_api_financiamentos_preserva_erros_de_content_type_json_e_validacao`;
  - `test_api_financiamentos_preserva_405_manual_sem_allow`;
  - `test_api_financiamentos_preserva_shape_get_filtros_aliases_e_resposta_vazia`;
  - `test_api_financiamentos_post_preserva_aliases_defaults_shape_e_efeitos`.
- Resultado final da fase: 6 testes focados OK.

Observacao PM-35A:

- Antes da migracao, os testes de paridade revelaram um bug pre-existente no
  runtime Django puro: `FinanciamentoMovimentacao` nao possuia atributo
  `dias_atraso` durante a serializacao do POST de FCF.
- A correcao preparatoria foi feita em `caixa/serializers_financiamentos.py`
  com fallback seguro:

```python
dias_atraso = getattr(movimentacao, "dias_atraso", 0)
```

- A correcao preservou o shape de `financingMovement` e nao alterou model,
  migration, regra financeira, signals, services ou frontend.

### PM-35.3

Status: concluida.

Resumo:

- `api_financiamentos` foi migrado para DRF com `@api_view(["GET", "POST"])`.
- `Response` foi usado apenas na borda da view.
- `POST` continua reaproveitando `_api_criar_movimentacao_financiamento`.
- `GET` continua reaproveitando `montar_payload_financiamentos_api`.
- O helper/decorator existente para metodo manual foi reaproveitado para manter
  o `405` manual sem header `Allow`.
- `csrf_protect_drf_view` foi usado para preservar CSRF real no `POST`.
- Permissoes manuais preservadas:
  - `GET`: `caixa.view_parceladivida`;
  - `POST`: `caixa.view_parceladivida` +
    `caixa.add_financiamentomovimentacao`.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- `/api/fcf/debts/`, credores, liquidacao, obrigacoes, dashboard e demais
  endpoints financeiros nao foram alterados.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_auth_permissoes_e_headers caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_csrf_real_no_post caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_erros_de_content_type_json_e_validacao caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_405_manual_sem_allow caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_shape_get_filtros_aliases_e_resposta_vazia caixa.tests.FiltrosHtmlTests.test_api_financiamentos_post_preserva_aliases_defaults_shape_e_efeitos
```

Resultados:

- `check`: OK.
- `spectacular --validate`: OK.
- Testes focados: 6 testes OK.
- OpenAPI passou a incluir `/api/fcf/`.

### PM-35.4

Status: concluida.

Resumo:

- Validacao completa executada depois da migracao.
- Os comandos foram executados com variaveis locais temporarias de validacao
  quando necessario:
  - `DEBUG=True`;
  - `SECRET_KEY=local-validation-secret`.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_auth_permissoes_e_headers caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_csrf_real_no_post caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_erros_de_content_type_json_e_validacao caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_405_manual_sem_allow caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_shape_get_filtros_aliases_e_resposta_vazia caixa.tests.FiltrosHtmlTests.test_api_financiamentos_post_preserva_aliases_defaults_shape_e_efeitos
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK.
- `spectacular --validate`: OK, sem warnings reportados em stderr.
- Testes focados de FCF: 6 testes OK.
- Suite completa: 795 testes OK.
- Warnings/logs observados na suite:
  - warnings esperados de CSRF em testes com `Client(enforce_csrf_checks=True)`;
  - logs esperados do Axes em testes de login invalido;
  - erro simulado esperado de backup manual em teste de falha mockada.
- Nenhuma mudanca de contrato runtime foi identificada.
- Nenhuma duplicacao de `LancamentoFinanceiro`, `ObrigacaoFinanceira`
  canonica ou `BaixaFinanceira` canonica foi observada nos testes focados.
- Nenhuma criacao indevida de `DividaFinanceira` ou `ParcelaDivida` foi
  observada nos testes focados.

### PM-35.5

Status: concluida.

Resumo:

- Este documento foi atualizado com o registro final da execucao.

Arquivos alterados nesta PM/correcao preparatoria:

- `caixa/tests.py`.
- `caixa/views_financiamentos.py`.
- `caixa/serializers_financiamentos.py`.
- `docs/PLANO_PM35_MIGRACAO_FCF_DRF.md`.

Arquivos de contexto ja alterados por PM anterior e presentes no working tree:

- `caixa/views_investimentos.py`.
- `docs/PLANO_PM34_MIGRACAO_FCI_DRF.md`.

Confirmacoes finais:

- `GET/POST /api/fcf/` foi migrado para DRF.
- URL e nome de rota foram preservados.
- `405` manual sem header `Allow` foi preservado.
- CSRF real foi preservado.
- `401`, `403`, `400`, `405`, `415`, `200` e `201` foram preservados nos
  testes de paridade.
- Filtros, aliases, defaults, validacoes, shapes e headers foram preservados.
- Signals e efeitos financeiros atuais foram preservados nos testes focados.
- `/api/fcf/debts/`, credores, liquidacao, obrigacoes, dashboard e outros
  endpoints financeiros nao foram alterados.
- Frontend, settings, CORS, CSRF global e autenticacao global nao foram
  alterados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- PM-35 pronta para commit local manual, junto da decisao do usuario sobre
  agrupar ou separar a correcao preparatoria PM-35A.
