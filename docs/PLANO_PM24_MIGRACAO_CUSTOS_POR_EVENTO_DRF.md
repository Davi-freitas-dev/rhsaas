# Plano PM-24 - Migracao incremental de `GET /api/custos-por-evento/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET /api/custos-por-evento/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de leitura de custos por
evento, sem alterar regra de negocio, selectors, serializers manuais,
permissoes, CORS, headers, status HTTP, JSON, filtros, totais ou contrato do
frontend.

## Escopo

- Congelar o contrato atual de `GET /api/custos-por-evento/` em testes antes
  da migracao.
- Migrar somente a view `api_custos_por_evento`.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissao manual `caixa.view_evento`.
- Preservar `401` e `403` atuais.
- Preservar `405` e header `Allow: GET`.
- Preservar Content-Type, Cache-Control/no-store, status HTTP e shape atual.
- Preservar filtros, aliases, ordenacao, breakdowns e totais atuais.
- Reaproveitar os filtros atuais do dashboard.
- Reaproveitar selectors e serializers manuais atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET /api/dashboard/financial-overview/`.
- `GET /api/mes-financeiro/`.
- Lancamentos financeiros.
- Obrigacoes financeiras.
- Baixas financeiras.
- Modelagem financeira canonica.
- Outros endpoints financeiros.
- Endpoints de eventos.
- Endpoints de clientes.
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

Nesta PM, somente `GET /api/custos-por-evento/` deve ser migrado.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
cadastros e operacoes estaveis primeiro; GETs financeiros antes de mutations
financeiras.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, CORS, efeitos de dominio,
queries, totais ou comportamento runtime apenas para melhorar a documentacao
OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-24.1

Arquivo atual:

- `caixa/views_dashboard.py`

View atual:

- `api_custos_por_evento`

Rota atual:

- `path("api/custos-por-evento/", api_custos_por_evento, name="api_custos_por_evento")`

Nome da rota:

- `caixa:api_custos_por_evento`

Decoradores atuais:

- `@require_GET`
- `@require_api_permission(DASHBOARD_PERMISSION)`

Metodo aceito:

- `GET`

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` esperado: `GET`.
- Resposta de `405` Django padrao deve ser preservada.
- Como `@require_GET` esta por fora do decorator de permissao, o `405` ocorre
  antes de autenticacao/permissao.

Permissao atual:

- `DASHBOARD_PERMISSION`, que resolve para `caixa.view_evento`.
- Nao usar `DjangoModelPermissions`, `IsAuthenticated` global ou permissao DRF
  generica se isso mudar contrato.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem `caixa.view_evento`:

```json
{"detail": "Permission denied."}
```

com status `403`.

Comportamento para usuario autenticado com `caixa.view_evento`:

- Status `200`.
- Resposta JSON com top-level `data`.
- Header `Content-Type` JSON.
- Header `Cache-Control` com `no-store`.

Filtros aceitos:

- `startDate`.
- `endDate`.
- `period`.
- `quickPeriod`.
- `eventId`.
- `clientId`.
- `contractCode`.
- `status`.

Valores aceitos em `period`:

- `current-month`.
- `all`.
- `previous-month`.
- `quarter`.
- `semester`.
- `year`.

Valores aceitos em `quickPeriod`:

- `hoje`.
- `mes_atual`.
- `30_dias`.
- `todos`.
- `vencidos`.

Valores aceitos em `status`:

- `pendente`.
- `parcial`.
- `recebido`.
- `pago`.
- `vencido`.
- `cancelado`.
- `planejado`.
- `realizado`.

Normalizacoes importantes:

- Datas invalidas sao tratadas como vazias.
- `startDate` e `endDate` invertidas sao normalizadas.
- `eventId` e `clientId` so aceitam strings numericas.
- `contractCode` e normalizado pelo helper atual de contratos.
- `period=all` vira `periodo_rapido=todos`.
- Sem periodo explicito, filtros de entidade levam a `periodo_rapido=todos`.
- Sem periodo e sem filtro de entidade, o padrao e `periodo_rapido=mes_atual`.

Payload de sucesso:

Status `200`:

```json
{
  "data": {
    "groups": [],
    "summary": {},
    "filters": {},
    "filterOptions": {},
    "pagination": {},
    "meta": {}
  }
}
```

Shape de `data.summary`:

- `eventsCount`.
- `plannedCostAmount`.
- `realizedCostAmount`.
- `pendingCostAmount`.
- `plannedRevenueAmount`.
- `realizedRevenueAmount`.
- `projectedResultAmount`.
- `realizedResultAmount`.
- `pendingItemsCount`.
- `overdueItemsCount`.

Shape de `data.filters`:

- `data_inicial`.
- `data_final`.
- `evento`.
- `cliente`.
- `status`.
- `periodo_rapido`.
- `quickPeriod`.
- `contractCode`, quando houver filtro de contrato.
- `contrato_codigo`, quando houver filtro de contrato.

Shape de `data.pagination`:

- `limit`.
- `offset`.
- `total`.
- `hasMore`.

Shape de `data.meta`:

- `generatedAt`.
- `source`.
- `currency`.
- `dateBasis`.
- `requiredPermission`.
- `periodLabel`.
- `nomenclature`.

Shape de cada item de `data.groups`:

- `key`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `eventLabel`.
- `clientName`.
- `contractLabel`.
- `firstDueDate`.
- `plannedCostAmount`.
- `realizedCostAmount`.
- `pendingCostAmount`.
- `plannedRevenueAmount`.
- `realizedRevenueAmount`.
- `projectedResultAmount`.
- `realizedResultAmount`.
- `pendingItemsCount`.
- `overdueItemsCount`.
- `serviceCostAmount`.
- `dailyAmount`.
- `foodAmount`.
- `transportAmount`.
- `extraCostAmount`.
- `manualCostAmount`.
- `serviceCostBreakdown`.
- `extraCostBreakdown`.
- `manualCostBreakdown`.
- `items`.

Shape de cada item dos breakdowns:

- `category`.
- `categoryLabel`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `items`.

Shape de cada detalhe dos breakdowns:

- `description`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.

Shape de cada item de `groups[].items`:

- `id`.
- `source`.
- `sourceLabel`.
- `sourceDetailLabel`.
- `description`.
- `dueDate`.
- `status`.
- `statusLabel`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `isOverdue`.

Fontes atuais de `groups[].items[].source`:

- `custo_servico`.
- `custo_extra`.
- `despesa_operacional`.

Dependencias atuais:

- `filtros_dashboard_financial_overview`.
- `montar_payload_custos_por_evento_api`.
- `montar_contexto_custos_por_evento`.
- `montar_custos_por_evento_dashboard`.
- `querysets_dashboard_filtrados`.
- `calcular_totais_basicos_dashboard`.
- `montar_contexto_base_dashboard`.
- `montar_opcoes_filtros_dashboard_api`.
- Selectors/serializers manuais de dimensoes operacionais.

Complexidade das queries e totais:

- O endpoint agrega receitas, despesas, custos de servico, custos extras,
  pagamentos, despesas manuais e totais por evento.
- Usa `select_related`, `prefetch_related`, `Sum`, agrupamento em Python e
  consultas adicionais para informacoes do evento/cliente/orcamento.
- Ja existe cobertura de query count constante para o contexto de custos por
  evento.

## Riscos especificos de custos por evento

- Endpoint GET-only, mas com regra financeira agregada e sensivel.
- Alto acoplamento com filtros compartilhados do dashboard financeiro.
- Risco de alterar periodo padrao, filtros de entidade ou normalizacao de
  contrato sem perceber.
- Risco de alterar shape de breakdowns ou itens usados pelo frontend.
- Risco de alterar totais financeiros por mudanca indireta de selector.
- Risco de DRF trocar automaticamente `401`, `403` ou `405` por payload/header
  diferente.
- Risco de OpenAPI incentivar mudanca de runtime para documentar melhor.

Classificacao de risco:

- Medio-alto.

Motivo:

- Nao ha mutacao nem CSRF de escrita, mas o payload e grande, agregado e
  financeiro.

Decisao de agrupamento:

- Deve ser migrado sozinho.
- Nao agrupar com dashboard financeiro, mes financeiro ou outros endpoints
  financeiros.

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
- Nao alterar JSON, status HTTP, headers ou contrato para melhorar OpenAPI.
- Reaproveitar a estrutura existente sempre que possivel.
- Preservar runtime acima de schema.

## PM-24.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Endpoint mapeado.
- Contrato atual documentado neste plano.
- Nenhum arquivo alterado durante o diagnostico.

## PM-24.2 - Congelamento de contrato em testes

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.
- Nao migrar endpoint nesta fase.
- Nao usar DRF neste endpoint nesta fase.

Cobrir obrigatoriamente:

- `GET` anonimo retorna `401`.
- `GET` autenticado sem `caixa.view_evento` retorna `403`.
- `GET` com `caixa.view_evento` retorna `200`.
- Headers JSON/no-store nas respostas JSON.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com `Allow: GET`.
- Shape completo de `data.groups`.
- Shape completo de `data.summary`.
- Shape completo de `data.filters`.
- Shape completo de `data.filterOptions`.
- Shape completo de `data.pagination`.
- Shape completo de `data.meta`.
- Shape completo de `groups[]`.
- Shape completo de `groups[].items[]`.
- Breakdowns de servicos preservados.
- Breakdowns de custos extras preservados.
- Breakdowns de despesas manuais preservados.
- Filtros `startDate` e `endDate`.
- Filtro `period`.
- Filtro `quickPeriod`.
- Filtro `eventId`.
- Filtro `clientId`.
- Filtro `contractCode`.
- Filtro `status`.
- Resposta vazia mantem shape.
- Ordenacao preservada.
- Totais preservados.
- Query count constante preservado, reaproveitando teste existente se possivel.

Comandos esperados:

```bash
python manage.py check
python manage.py test caixa.tests.FiltrosHtmlTests
```

Se os testes de paridade forem adicionados em outra classe, rodar tambem a
classe/teste focado correspondente.

## PM-24.3 - Migracao controlada para DRF

Objetivo:

- Converter somente `api_custos_por_evento` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar a mesma URL.
- Preservar o mesmo nome de rota.
- Preservar permissao manual `caixa.view_evento`.
- Preservar `401` atual.
- Preservar `403` atual.
- Preservar `405` e `Allow: GET`.
- Preservar `Content-Type`.
- Preservar `Cache-Control/no-store`.
- Preservar status HTTP.
- Preservar shape JSON.
- Preservar filtros e aliases atuais.
- Preservar ordenacao e totais atuais.
- Reaproveitar `filtros_dashboard_financial_overview`.
- Reaproveitar `montar_payload_custos_por_evento_api`.
- Reaproveitar `montar_contexto_custos_por_evento`.
- Reaproveitar selectors e serializers manuais atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em dashboard financeiro.
- Nao mexer em mes financeiro.
- Nao mexer em outros endpoints financeiros.

Validacoes da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
```

Se houver testes focados novos em outra classe, rodar tambem esses testes.

## PM-24.4 - Validacao completa

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Validar:

- Testes focados de custos por evento.
- Testes relacionados existentes de dashboard/custos por evento.
- Query count constante.
- OpenAPI valido.
- Suite completa verde.
- Nenhuma alteracao em frontend.
- Nenhuma alteracao em settings.
- Nenhuma alteracao em CORS, CSRF global ou autenticacao global.
- Nenhuma alteracao em outros endpoints financeiros.

## PM-24.5 - Encerramento

Atualizar este documento com:

- Arquivos alterados.
- Testes criados/alterados.
- Comandos executados.
- Resultado dos testes focados.
- Resultado do `check`.
- Resultado do `spectacular --validate`.
- Resultado da suite completa.
- Warnings do spectacular, se houver.
- Confirmacao de que somente `GET /api/custos-por-evento/` foi migrado.
- Confirmacao de que runtime prevaleceu sobre OpenAPI.
- Riscos residuais.
- `git status --short`.
- Recomendacao final: pronto ou nao para commit local manual.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `GET /api/custos-por-evento/` migrado para DRF.
- Nenhum outro endpoint migrado nesta PM.
- Mesma URL.
- Mesmo nome de rota.
- Mesmo metodo aceito.
- Mesmo `401`.
- Mesmo `403`.
- Mesmo `405` e `Allow: GET`.
- Mesmo JSON.
- Mesmo status HTTP.
- Mesmos headers.
- Mesmos filtros.
- Mesma ordenacao.
- Mesmos totais.
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
- Filtros mudarem.
- Ordenacao mudar.
- Totais mudarem.
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

- Reverter a alteracao da view `api_custos_por_evento`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em outros endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum selector/serializer manual seja alterado.

## Registro de execucao

### PM-24.1 - Diagnostico read-only

Status: concluida.

Arquivos lidos:

- `caixa/views_dashboard.py`.
- `caixa/urls.py`.
- `caixa/permissions.py`.
- `caixa/serializers_dashboard.py`.
- `caixa/selectors_dashboard.py`.
- `caixa/selectors_dashboard_custos_evento.py`.
- `caixa/selectors_dashboard_filtros.py`.
- `caixa/selectors_dashboard_contexto.py`.
- `caixa/utils_periodos.py`.
- `caixa/utils_request.py`.
- `caixa/tests.py`.

Resultado:

- Contrato atual mapeado.
- Lacunas de paridade identificadas.
- Endpoint classificado como risco medio-alto.
- Decisao: migrar sozinho.
- Nenhuma alteracao de arquivo feita na PM-24.1.

### PM-24.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados:

- `test_api_custos_por_evento_exige_autenticacao_e_permissao`.
- `test_api_custos_por_evento_metodos_nao_permitidos_preservam_allow`.
- `test_api_custos_por_evento_resposta_vazia_preserva_shape`.
- `test_api_custos_por_evento_preserva_shape_filtros_totais_e_breakdowns`.
- `test_api_custos_por_evento_ordena_por_data_e_preserva_period_quick_period`.

Contratos congelados:

- `GET` anonimo retorna `401` com JSON atual.
- `GET` autenticado sem `caixa.view_evento` retorna `403` com JSON atual.
- `GET` autorizado retorna `200`.
- Respostas JSON preservam `Content-Type` JSON e `Cache-Control` com
  `no-store`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com `Allow: GET`.
- Resposta vazia preserva shape completo.
- Shape de `groups`, `summary`, `filters`, `filterOptions`, `pagination`,
  `meta`, breakdowns e `items` foi congelado.
- Filtros `startDate`, `endDate`, `quickPeriod`, `eventId`, `clientId`,
  `contractCode` e `status` foram cobertos.
- `contractCode` preserva normalizacao atual sem prefixo `EVT-`.
- Ordenacao por data do evento foi congelada.
- Query count constante segue coberto pelo teste existente
  `test_custos_por_evento_mantem_queries_constantes_com_mais_registros`.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_metodos_nao_permitidos_preservam_allow caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_resposta_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_preserva_shape_filtros_totais_e_breakdowns caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_ordena_por_data_e_preserva_period_quick_period
DEBUG=True SECRET_KEY=local-validation-secret python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests
```

Resultados:

- Testes novos: 5 testes OK.
- `python manage.py check`: OK.
- `caixa.tests.FiltrosHtmlTests`: 377 testes OK.

### PM-24.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_dashboard.py`.

Implementacao:

- Somente `api_custos_por_evento` foi migrado.
- Usado `@api_view(["GET"])`.
- Usado `@permission_classes([AllowAny])` local para impedir que a permissao
  global do DRF substitua os `401`/`403` atuais.
- `@require_GET` foi mantido por fora para preservar `405` Django padrao e
  `Allow: GET`.
- `Response` foi usado somente na borda do endpoint migrado.
- `api_authentication_required_response`,
  `api_permission_denied_response` e `api_no_store_json_response` foram
  reaproveitados para preservar payloads e headers.
- `montar_payload_custos_por_evento_api`,
  `filtros_dashboard_financial_overview` e selectors/serializers manuais
  atuais foram reaproveitados sem alteracao.
- Adicionado `extend_schema` seguro para OpenAPI sem alterar runtime.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_metodos_nao_permitidos_preservam_allow caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_resposta_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_preserva_shape_filtros_totais_e_breakdowns caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_ordena_por_data_e_preserva_period_quick_period caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_period_all_canonico_inclui_evento_historico caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_agrupa_orcamentos_aprovados_por_evento caixa.tests.FiltrosHtmlTests.test_api_custos_por_evento_evento_sem_periodo_nao_limita_mes_atual caixa.tests.FiltrosHtmlTests.test_custos_por_evento_mantem_queries_constantes_com_mais_registros
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Testes focados de custos por evento: 9 testes OK.
- OpenAPI passou a incluir `GET /api/custos-por-evento/`.
- Warnings do spectacular: nenhum warning reportado.

### PM-24.4 - Validacao completa

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
- `caixa.tests.FiltrosHtmlTests`: 377 testes OK.
- Suite completa: 735 testes OK.
- Warnings observados durante a suite: warnings esperados de CSRF nos testes de
  autenticacao (`/api/auth/login/` e `/api/auth/logout/`), ja cobertos pela
  suite existente.
- Nenhum warning do spectacular foi reportado.
- Query count constante preservado pela suite focada.

### PM-24.5 - Encerramento

Status: concluida.

Arquivos alterados nesta PM:

- `caixa/tests.py`.
- `caixa/views_dashboard.py`.
- `docs/PLANO_PM24_MIGRACAO_CUSTOS_POR_EVENTO_DRF.md`.

Confirmacoes:

- Somente `GET /api/custos-por-evento/` foi migrado.
- `GET /api/dashboard/financial-overview/` nao foi alterado.
- `GET /api/mes-financeiro/` nao foi alterado.
- Outros endpoints financeiros nao foram alterados.
- Frontend nao foi alterado.
- Settings nao foram alterados.
- CORS nao foi alterado.
- CSRF global nao foi alterado.
- Autenticacao global nao foi alterada.
- Nenhum Serializer DRF foi criado.
- Nenhum ViewSet ou ModelViewSet foi criado.
- Selectors e serializers manuais foram reaproveitados sem alteracao.
- Filtros, totais, ordenacao, query count e contrato runtime foram
  preservados.
- Paridade runtime prevaleceu sobre OpenAPI.

Riscos residuais:

- O schema OpenAPI ainda documenta o payload como objeto generico, sem schema
  detalhado de `groups`, `summary` e breakdowns.
- O payload continua grande e financeiro; futuras alteracoes de selectors
  compartilhados do dashboard devem rodar os testes focados desta PM.

`git status --short` ao fim da validacao antes deste registro:

```text
 M caixa/tests.py
 M caixa/views_dashboard.py
?? docs/PLANO_PM24_MIGRACAO_CUSTOS_POR_EVENTO_DRF.md
```

Recomendacao final:

- Pronto para commit local manual.
