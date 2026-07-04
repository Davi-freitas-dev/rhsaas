# Plano PM-28 - Migracao incremental de `GET /api/baixas-financeiras-canonicas/` e `GET /api/canonical-settlements/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar conjuntamente `GET /api/baixas-financeiras-canonicas/` e
`GET /api/canonical-settlements/` para Django REST Framework, preservando
integralmente o contrato atual consumido pelo frontend Next.js.

As duas rotas podem ser tratadas na mesma PM porque apontam para a mesma view
`api_baixas_financeiras_canonicas`.

DRF deve entrar apenas como casca HTTP da view de leitura das baixas
financeiras canonicas, sem alterar regra de negocio, selectors, serializers
manuais, permissoes, CORS, headers, status HTTP, JSON, filtros, aliases,
ordenacao, paginacao, totais, queries ou contrato do frontend.

## Escopo

- Congelar o contrato atual das duas rotas em testes antes da migracao.
- Migrar somente a view `api_baixas_financeiras_canonicas`.
- Manter as duas rotas existentes apontando para a mesma view.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissao manual `caixa.view_lancamentofinanceiro`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar Content-Type, Cache-Control/no-store, status HTTP e shape atual das
  respostas JSON.
- Preservar filtros canonicos atuais.
- Preservar limites e paginacao atuais.
- Preservar ordenacao atual.
- Preservar que aliases externos atualmente ignorados continuam ignorados.
- Reaproveitar selectors, serializers manuais e helpers atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Obrigacoes financeiras.
- Modelagem financeira canonica.
- Dashboard financeiro.
- Mes financeiro.
- Lancamentos financeiros.
- Custos por evento.
- Baixas financeiras mutations.
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
- Alteracao de models.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, somente a view `api_baixas_financeiras_canonicas` deve ser migrada,
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

## Contrato atual identificado na PM-28.1

Arquivo atual:

- `caixa/views_modelagem_canonica.py`.

View atual:

- `api_baixas_financeiras_canonicas`.

Rotas atuais:

- `path("api/baixas-financeiras-canonicas/", api_baixas_financeiras_canonicas, name="api_baixas_financeiras_canonicas")`.
- `path("api/canonical-settlements/", api_baixas_financeiras_canonicas, name="api_canonical_settlements")`.

Nomes das rotas:

- `caixa:api_baixas_financeiras_canonicas`.
- `caixa:api_canonical_settlements`.

As duas rotas apontam para a mesma view.

Decoradores atuais:

- `@require_GET`.
- `@require_api_permission(FINANCIAL_LEDGER_PERMISSION)`.

Metodo aceito:

- `GET`.

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` observado: `GET`.
- Body observado: vazio.
- `Content-Type` observado: `text/html; charset=utf-8`.
- `Cache-Control` observado: ausente.
- A resposta de `405` Django padrao deve ser preservada.
- Como `@require_GET` esta por fora do decorator de permissao, o `405` ocorre
  antes de autenticacao/permissao.

Permissao atual:

- `FINANCIAL_LEDGER_PERMISSION`, que resolve para
  `caixa.view_lancamentofinanceiro`.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global ou permissao DRF
generica se isso mudar contrato.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem `caixa.view_lancamentofinanceiro`:

```json
{"detail": "Permission denied."}
```

com status `403`.

Comportamento para usuario autenticado com `caixa.view_lancamentofinanceiro`:

- Status `200`.
- Resposta JSON com top-level `data`.
- Header `Content-Type` JSON.
- Header `Cache-Control` com `no-store`.

Payload de sucesso:

```json
{
  "data": {
    "items": [],
    "summary": {},
    "filters": {},
    "filterOptions": {},
    "pagination": {},
    "meta": {}
  }
}
```

Shape de `data.items[]`:

- `id`.
- `key`.
- `date`.
- `settlementDate`.
- `type`.
- `tipo`.
- `typeLabel`.
- `cashFlowGroup`.
- `fluxo`.
- `nature`.
- `natureza`.
- `amount`.
- `settlementAmount`.
- `valorBaixa`.
- `valor_baixa`.
- `valorTotal`.
- `allocatedAmount`.
- `unallocatedAmount`.
- `paymentMethod`.
- `description`.
- `settlementDescription`.
- `descricao`.
- `notes`.
- `status`.
- `statusLabel`.
- `writeModelSource`.
- `fonteEscrita`.
- `source`.
- `origin`.
- `origem`.
- `sourceId`.
- `originId`.
- `sourceDetail`.
- `sourceLabel`.
- `clientId`.
- `clientName`.
- `cliente_id`.
- `cliente_nome`.
- `contractCode`.
- `contractName`.
- `contractLabel`.
- `contrato_codigo`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `eventLabel`.
- `evento_id`.
- `evento_nome`.
- `evento_numero`.
- `evento_label`.
- `ledgerEntryId`.
- `allocations`.
- `allocationCount`.

Shape de `data.items[].allocations[]`:

- `id`.
- `obligationId`.
- `obligationKey`.
- `source`.
- `sourceId`.
- `sourceDetail`.
- `sourceLabel`.
- `description`.
- `obligationDescription`.
- `dueDate`.
- `allocatedAmount`.
- `interestAmount`.
- `fineAmount`.
- `discountAmount`.
- `clientId`.
- `clientName`.
- `cliente_id`.
- `cliente_nome`.
- `contractCode`.
- `contractName`.
- `contractLabel`.
- `contrato_codigo`.
- `eventId`.
- `eventName`.
- `eventNumber`.
- `eventLabel`.
- `evento_id`.
- `evento_nome`.
- `evento_numero`.
- `evento_label`.

Shape de `data.summary`:

- `count`.
- `inflowAmount`.
- `outflowAmount`.
- `financialResult`.
- `allocatedAmount`.
- `unallocatedAmount`.
- `byCashFlowGroup`.
- `bySource`.
- `byWriteModelSource`.

Shape dos grupos de resumo:

- `count`.
- `inflowAmount`.
- `outflowAmount`.
- `financialResult`.
- `allocatedAmount`.
- `unallocatedAmount`.

Shape de `data.filters`:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `source`.
- `type`.
- `cashFlowGroup`.
- `nature`.
- `status`.
- `writeModelSource`.
- `search`.

Shape de `data.filterOptions`:

- `contracts`.
- `events`.
- `clients`.
- `types`.
- `cashFlowGroups`.
- `sources`.
- `writeModelSources`.

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

Shape de `filterOptions.types[]`:

- `value`.
- `label`.

Shape de `filterOptions.cashFlowGroups[]`:

- `value`.
- `label`.

Shape de `filterOptions.sources[]`:

- `value`.
- `label`.

Shape de `filterOptions.writeModelSources[]`:

- `value`.
- `label`.

Shape de `data.pagination`:

- `limit`.
- `offset`.
- `total`.
- `hasMore`.

Shape de `data.meta`:

- `generatedAt`.
- `source`, com valor `"backend"`.
- `readOnly`, com valor `true`.
- `currency`, com valor `"BRL"`.
- `dateBasis`, com valor `"settlementDate"`.
- `model`, com valor `"BaixaFinanceira"`.
- `allocationModel`, com valor `"BaixaFinanceiraAlocacao"`.

Filtros canonicos aceitos pela borda HTTP atual:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `limit`.
- `offset`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `source`.
- `type`.
- `cashFlowGroup`.
- `nature`.
- `status`.
- `writeModelSource`.
- `search`.

Regras atuais de limite e paginacao:

- `limit` padrao: `100`.
- `limit` minimo: `1`.
- `limit` maximo: `300`.
- `offset` padrao: `0`.
- `offset` minimo: `0`.
- `offset` maximo: total de registros filtrados.
- `summary` e calculado sobre todos os itens filtrados, nao apenas sobre a
  pagina.

Ordenacao atual:

- `-data_baixa`.
- `-id`.

Aliases internos observados:

- O serializer trabalha internamente com aliases como `data_inicial`,
  `data_final`, `contrato_codigo`, `tipo`, `fluxo`, `natureza`,
  `fonteEscrita`, `write_model_source` e `busca`.
- O contrato HTTP atual observado consome os filtros canonicos listados acima.
- Aliases externos como `costCenterId`, `fonteEscrita` e `write_model_source`
  foram observados como ignorados pelo contrato atual e devem continuar assim
  nesta PM.

Diferencas entre rota PT-BR e rota EN:

- Nao ha diferenca funcional esperada.
- As duas rotas usam a mesma view, mesmas permissoes, mesmos filtros e mesmo
  shape.
- A diferenca atual e apenas URL/nome da rota.

Dependencias atuais:

- `montar_payload_baixas_financeiras_canonicas_api`.
- `normalizar_filtros_baixas_canonicas`.
- `listar_baixas_financeiras_canonicas`.
- `aplicar_filtros_baixas_canonicas`.
- `serializar_baixa_financeira_canonica`.
- `serializar_alocacao_baixa_canonica`.
- `serializar_resumo_baixas_canonicas`.
- `serializar_opcoes_dimensoes_operacionais_canonicas`.
- `montar_opcoes_eventos_clientes_filtro`.
- `serializar_opcoes_entidades_operacionais`.
- `resolver_intervalo_periodo_canonico`.
- `normalizar_codigo_contrato_visual`.
- `montar_filtro_evento_ou_orcamento_por_contrato_visual`.
- Models `BaixaFinanceira`, `BaixaFinanceiraAlocacao` e `ObrigacaoFinanceira`.

Complexidade de queries:

- A view monta a lista completa filtrada antes de aplicar paginacao em memoria.
- `summary` percorre todos os itens filtrados.
- A consulta usa `select_related` em cliente, evento, orcamento, lancamento e
  varias origens financeiras.
- A consulta usa `prefetch_related` para alocacoes e obrigacoes relacionadas.
- `filterOptions` executa consultas adicionais para contratos, eventos e
  clientes.
- Query count pode crescer com volume de baixas, alocacoes, obrigacoes,
  eventos e clientes.

## Riscos especificos de baixas financeiras canonicas

- Endpoint financeiro canonico e sensivel.
- A API e read-only, mas representa auditoria de baixas e alocacoes canonicas.
- Mudanca acidental pode alterar conciliacao visual ou auditoria financeira.
- A pagina e aplicada depois da serializacao completa; alterar isso mudaria
  totais, `pagination.total` ou performance.
- `summary` e intencionalmente calculado sobre todos os itens filtrados; DRF nao
  deve trocar isso por resumo da pagina.
- DRF, se usado sem cuidado, muda `405` para payload JSON padrao.
- DRF, se usar permissao global, pode substituir `401`/`403` atuais.
- Uso direto de `Response` pode perder headers `Cache-Control` atuais.
- Ha aliases historicos documentados que nao sao aceitos pelo contrato runtime
  atual; a PM deve congelar runtime real, nao documentacao historica.
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
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Nao alterar obrigacoes financeiras.
- Nao alterar modelagem financeira canonica.
- Nao alterar dashboard financeiro.
- Nao alterar mes financeiro.
- Nao alterar outros endpoints financeiros.
- Reaproveitar `montar_payload_baixas_financeiras_canonicas_api`.
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
- `GET` autenticado sem permissao preserva `403` JSON atual nas duas rotas.
- `GET` autenticado com permissao preserva `200` e shape atual nas duas rotas.
- As duas rotas preservam igualdade funcional.
- Headers JSON/no-store preservados em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual nas duas
  rotas.
- Filtros canonicos preservados.
- Limites e paginacao preservados.
- Ordenacao `-data_baixa`, `-id` preservada.
- Resposta vazia mantem shape.
- `summary` continua calculado sobre todos os itens filtrados.
- Aliases externos atualmente ignorados continuam ignorados.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora das duas rotas da view `api_baixas_financeiras_canonicas`
  e alterado.

## Criterios de bloqueio

Parar imediatamente se:

- Algum shape de `data` mudar.
- `items`, `allocations`, `summary`, `filters`, `filterOptions`, `pagination`
  ou `meta` mudarem sem previsao.
- Algum filtro canonico mudar.
- Algum alias atualmente ignorado passar a filtrar resultado.
- `limit`, `offset`, `total` ou `hasMore` mudarem.
- `summary` passar a considerar apenas a pagina.
- Ordenacao mudar.
- `405` mudar para JSON DRF padrao.
- `401` ou `403` mudarem.
- Header `Cache-Control` mudar em respostas JSON.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar obrigacoes, modelagem canonica, dashboard, mes
  financeiro ou outros endpoints financeiros junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_baixas_financeiras_canonicas`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em outros endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum selector/serializer manual seja alterado.

## Fases

### PM-28.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como financeiro canonico sensivel.
- Decisao: migrar as duas rotas juntas porque usam a mesma view.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-28.1:

- `caixa/views_modelagem_canonica.py`.
- `caixa/urls.py`.
- `caixa/permissions.py`.
- `caixa/serializers_modelagem_canonica.py`.
- `caixa/serializers_dimensoes_operacionais.py`.
- `caixa/selectors_opcoes_filtros.py`.
- `caixa/utils_periodos.py`.
- `caixa/tests.py`.

### PM-28.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `GET` anonimo retorna `401` em ambas as URLs.
- `GET` autenticado sem `caixa.view_lancamentofinanceiro` retorna `403` em
  ambas as URLs.
- `GET` com permissao retorna `200` em ambas as URLs.
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
  - `items[].allocations`;
  - `summary`;
  - `filters`;
  - `filterOptions`;
  - `pagination`;
  - `meta`.
- Filtros canonicos preservados:
  - `period`;
  - `quickPeriod`;
  - `startDate`;
  - `endDate`;
  - `limit`;
  - `offset`;
  - `contractCode`;
  - `eventId`;
  - `clientId`;
  - `source`;
  - `type`;
  - `cashFlowGroup`;
  - `nature`;
  - `status`;
  - `writeModelSource`;
  - `search`.
- Limites preservados:
  - `limit` padrao `100`;
  - `limit` minimo `1`;
  - `limit` maximo `300`;
  - `offset` padrao `0`.
- Ordenacao `-data_baixa`, `-id` preservada.
- Resposta vazia mantem shape.
- `summary` calculado sobre todos os itens filtrados, nao apenas pagina.
- Aliases externos atualmente ignorados, como `costCenterId`, `fonteEscrita` e
  `write_model_source`, continuam ignorados.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de baixas financeiras canonicas>
```

### PM-28.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_baixas_financeiras_canonicas` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar as duas rotas existentes apontando para a mesma view.
- Preservar `@require_GET` por fora, ou equivalente, para manter `405` Django
  padrao.
- Usar `AllowAny` local se necessario para preservar `401`/`403` manuais.
- Preservar permissao manual `caixa.view_lancamentofinanceiro`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar filtros canonicos atuais.
- Preservar limites e paginacao atuais.
- Preservar ordenacao atual.
- Preservar shape atual.
- Preservar aliases externos ignorados como ignorados.
- Reaproveitar selectors, serializers manuais e helpers atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em obrigacoes, modelagem canonica, dashboard, mes financeiro ou
  outros endpoints financeiros.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de baixas financeiras canonicas>
```

### PM-28.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de baixas financeiras canonicas>
python manage.py test <testes relacionados existentes>
python manage.py test
```

Validar:

- Testes focados de baixas financeiras canonicas passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui as duas rotas:
  - `GET /api/baixas-financeiras-canonicas/`;
  - `GET /api/canonical-settlements/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.

### PM-28.5 - Encerramento

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

### PM-28.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- As duas rotas apontam para a mesma view.
- Endpoint permanece Django puro antes da migracao.
- Endpoint classificado como financeiro canonico sensivel.
- Decisao: migrar as duas rotas juntas porque compartilham a mesma view e o
  mesmo contrato.
- Nenhuma alteracao de arquivo feita na PM-28.1.

### PM-28.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados/reforcados:

- `ModelagemFinanceiraCanonicaTests.test_api_baixas_canonicas_autenticacao_permissao_e_headers_em_ambas_rotas`.
- `ModelagemFinanceiraCanonicaTests.test_api_baixas_canonicas_metodos_nao_permitidos_preservam_405_em_ambas_rotas`.
- `ModelagemFinanceiraCanonicaTests.test_api_baixas_canonicas_preserva_shape_e_igualdade_funcional_das_rotas`.
- `ModelagemFinanceiraCanonicaTests.test_api_baixas_canonicas_preserva_resposta_vazia_e_shape`.
- `ModelagemFinanceiraCanonicaTests.test_api_baixas_canonicas_preserva_limites_paginacao_ordenacao_e_summary_global`.
- `ModelagemFinanceiraCanonicaTests.test_api_baixas_canonicas_preserva_filtros_canonicos_e_aliases_ignorados`.

Contrato congelado:

- `401` anonimo nas duas rotas.
- `403` autenticado sem `caixa.view_lancamentofinanceiro` nas duas rotas.
- `200` autenticado com permissao nas duas rotas.
- Igualdade funcional entre `/api/baixas-financeiras-canonicas/` e
  `/api/canonical-settlements/`.
- Headers JSON/no-store em respostas JSON.
- `405` Django padrao para `POST`, `PUT`, `PATCH` e `DELETE`, com
  `Allow: GET`, body vazio, `Content-Type: text/html; charset=utf-8` e sem
  `Cache-Control`.
- Shape completo de `data`, `items`, `items[].allocations`, `summary`,
  `filters`, `filterOptions`, `pagination` e `meta`.
- Filtros canonicos atuais preservados.
- Limites e paginacao preservados.
- Ordenacao `-data_baixa`, `-id` preservada.
- Resposta vazia mantendo shape.
- `summary` calculado sobre todos os itens filtrados, nao apenas pagina.
- Aliases externos atualmente ignorados, como `costCenterId`, `fonteEscrita`
  e `write_model_source`, congelados como ignorados.

Comandos executados:

```bash
python manage.py test <6 testes novos de baixas financeiras canonicas>
python manage.py check
python manage.py test <7 testes relacionados existentes>
```

Resultados:

- 6 testes novos: OK.
- `python manage.py check`: OK.
- 7 testes relacionados existentes: OK.

### PM-28.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_modelagem_canonica.py`.

Como a view foi migrada:

- `api_baixas_financeiras_canonicas` foi convertida para DRF com
  `@api_view(["GET"])`.
- `Response` foi usado somente na borda do endpoint.
- `@require_GET` permaneceu por fora da view DRF para preservar o `405` Django
  padrao.
- `AllowAny` local foi usado para impedir que a permissao global do DRF
  substitua os `401` e `403` manuais atuais.
- A permissao manual `caixa.view_lancamentofinanceiro` foi preservada por meio
  de checagem explicita.
- O payload continua sendo montado por
  `montar_payload_baixas_financeiras_canonicas_api(request.GET)`.
- Selectors, serializers manuais e helpers de dominio nao foram alterados.
- As duas rotas existentes continuam apontando para a mesma view.
- Nenhum outro endpoint financeiro foi migrado.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <6 testes focados de baixas financeiras canonicas>
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- 6 testes focados: OK.
- OpenAPI inclui:
  - `GET /api/baixas-financeiras-canonicas/`;
  - `GET /api/canonical-settlements/`.
- Warnings do `spectacular`: nenhum warning novo observado.

### PM-28.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.ModelagemFinanceiraCanonicaTests caixa.tests.PermissoesTests
python manage.py test
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Testes relacionados de modelagem canonica/baixas canonicas e permissoes:
  60 testes OK.
- Suite completa: 756 testes OK.
- Warnings do `spectacular`: nenhum warning novo observado.
- Logs esperados de CSRF/AXES apareceram em testes de autenticacao existentes,
  sem falha.
- Nenhum contrato runtime foi alterado fora da view alvo.
- Paginacao, filtros, aliases ignorados, ordenacao e summary global foram
  preservados.

### PM-28.5 - Encerramento

Status: concluida.

Arquivos alterados na PM-28:

- `caixa/tests.py`.
- `caixa/views_modelagem_canonica.py`.
- `docs/PLANO_PM28_MIGRACAO_BAIXAS_FINANCEIRAS_CANONICAS_DRF.md`.

Confirmacoes finais:

- As duas rotas continuam apontando para a mesma view.
- `GET /api/baixas-financeiras-canonicas/` foi migrado para DRF por meio da
  view compartilhada.
- `GET /api/canonical-settlements/` foi migrado junto por compartilhar a mesma
  view.
- `405` Django padrao foi preservado.
- `401` e `403` JSON atuais foram preservados.
- Filtros canonicos atuais foram preservados.
- Limites e paginacao atuais foram preservados.
- Ordenacao `-data_baixa`, `-id` foi preservada.
- `summary` continua calculado sobre todos os itens filtrados.
- Aliases externos atualmente ignorados continuam ignorados.
- Frontend nao foi alterado.
- Settings, CORS, CSRF global e autenticacao global nao foram alterados.
- Obrigacoes, modelagem canonica, dashboard, mes financeiro e outros endpoints
  financeiros nao foram alterados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.

Riscos residuais:

- O schema OpenAPI permanece generico (`type: object`) porque a PM prioriza
  paridade runtime e nao cria Serializer DRF.
- Query count absoluto nao foi congelado em numero fixo; a cobertura garante
  paginacao, ordenacao, filtros, aliases ignorados e summary global.
- O endpoint continua sensivel por representar auditoria de baixas e alocacoes
  financeiras canonicas; futuras mudancas devem manter testes de contrato antes
  de qualquer ajuste.

`git status --short` ao final da validacao antes deste registro:

```text
 M caixa/tests.py
 M caixa/views_modelagem_canonica.py
?? docs/PLANO_PM28_MIGRACAO_BAIXAS_FINANCEIRAS_CANONICAS_DRF.md
```

Recomendacao:

- PM-28 pronta para revisao e commit local manual.
