# Plano PM-26 - Migracao incremental de `GET /api/lancamentos-financeiros/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar exclusivamente `GET /api/lancamentos-financeiros/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de leitura de lancamentos
financeiros, sem alterar regra de negocio, selectors, serializers manuais,
permissoes, CORS, headers, status HTTP, JSON, filtros, aliases, paginacao,
totais, agregacoes, ordenacao, query count ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET /api/lancamentos-financeiros/` em testes
  antes da migracao.
- Migrar somente a view `api_lancamentos_financeiros`.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissao manual `caixa.view_lancamentofinanceiro`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar Content-Type, Cache-Control/no-store, status HTTP e shape atual das
  respostas JSON.
- Preservar filtros HTTP canonicos, aliases atuais, paginacao, totais,
  agregacoes, ordenacao e query count atuais.
- Reaproveitar selectors e serializers manuais atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Obrigacoes financeiras.
- Baixas financeiras canonicas.
- Dashboard financeiro.
- Mes financeiro.
- Custos por evento.
- Modelagem financeira canonica.
- Outros endpoints financeiros canonicos.
- Endpoints de clientes.
- Endpoints de eventos.
- Endpoints de orcamentos.
- Mutations financeiras.
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

Nesta PM, somente `GET /api/lancamentos-financeiros/` deve ser migrado.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
GETs financeiros antes de mutations financeiras, sempre com paridade congelada
antes da migracao.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, CORS, filtros, aliases,
paginacao, totais, ordenacao, queries ou comportamento runtime apenas para
melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-26.1

Arquivo atual:

- `caixa/views_lancamentos.py`

View atual:

- `api_lancamentos_financeiros`

Rota atual:

- `path("api/lancamentos-financeiros/", api_lancamentos_financeiros, name="api_lancamentos_financeiros")`

Nome da rota:

- `caixa:api_lancamentos_financeiros`

Decoradores atuais:

- `@require_GET`
- `@require_api_permission(FINANCIAL_LEDGER_PERMISSION)`

Metodo aceito:

- `GET`

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
    "pagination": {},
    "meta": {}
  }
}
```

Shape de `data.items[]`:

- `id`.
- `date`.
- `data`.
- `type`.
- `tipo`.
- `typeLabel`.
- `cashFlowGroup`.
- `fluxo`.
- `cashFlowGroupLabel`.
- `nature`.
- `natureza`.
- `natureLabel`.
- `amount`.
- `ledgerAmount`.
- `valorLancamento`.
- `valor_lancamento`.
- `valor`.
- `description`.
- `ledgerDescription`.
- `descricao`.
- `status`.
- `statusLabel`.
- `origin`.
- `origem`.
- `originId`.
- `originLabel`.
- `source`.
- `sourceId`.
- `sourceLabel`.
- `clientId`.
- `clientName`.
- `cliente_id`.
- `cliente_nome`.
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

Shape de `data.summary`:

- `entradas`.
- `inflowAmount`.
- `saidas`.
- `outflowAmount`.
- `resultadoFinanceiro`.
- `financialResultAmount`.
- `resultado_financeiro`.
- `cashFlows`.

Shape de `data.summary.cashFlows`:

- `fco`.
- `fci`.
- `fcf`.

Cada fluxo em `cashFlows` possui:

- `entradas`.
- `inflowAmount`.
- `saidas`.
- `outflowAmount`.
- `resultadoFinanceiro`.
- `financialResultAmount`.
- `resultado_financeiro`.

Shape de `data.filters`:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `cashFlowGroup`.
- `type`.
- `nature`.
- `origin`.
- `originLabel`.
- `source`.
- `sourceLabel`.
- `sourceId`.
- `sourceDetail`.
- `status`.
- `search`.

Observacao sobre paginacao:

- `limit` e `offset` sao filtros HTTP de entrada.
- No contrato atual, `limit` e `offset` retornam em `data.pagination`, nao em
  `data.filters`.

Shape de `data.pagination`:

- `limit`.
- `offset`.
- `total`.
- `hasMore`.

Regras atuais de paginacao:

- `limit` padrao: `100`.
- `limit` minimo: `1`.
- `limit` maximo: `200`.
- `offset` padrao: `0`.
- `offset` minimo: `0`.
- `offset` maximo: total de registros.

Shape de `data.meta`:

- `generatedAt`.
- `source`, com valor `"backend"`.
- `currency`, com valor `"BRL"`.

Filtros HTTP canonicos aceitos pela view:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `cashFlowGroup`.
- `type`.
- `nature`.
- `origin`.
- `source`.
- `sourceId`.
- `sourceDetail`.
- `status`.
- `search`.
- `limit`.
- `offset`.

Aliases internos entendidos por selectors ou serializers, mas nao coletados
diretamente pela view HTTP atual:

- `costCenterId`.
- `evento`.
- `evento_id`.
- `cliente`.
- `cliente_id`.
- `contrato_codigo`.
- `fluxo`.
- `tipo`.
- `natureza`.
- `origem`.
- `source_id`.
- `source_detail`.
- `originId`.
- `origin_id`.
- `busca`.

Esses aliases internos nao devem ser promovidos automaticamente a contrato HTTP
nesta PM.

Normalizacoes importantes:

- `period` aceita valores frontend como `current-month`, `all`,
  `previous-month`, `quarter`, `semester` e `year`.
- `quickPeriod` aceita valores rapidos atuais como `hoje`, `mes_atual`,
  `30_dias`, `todos` e `vencidos`.
- `startDate` e `endDate` invalidos viram vazio.
- `startDate` e `endDate` invertidos sao normalizados.
- `contractCode` e normalizado pelo helper atual de contratos.
- `eventId`, `clientId` e `sourceId` invalidos viram filtro invalido e geram
  queryset vazio.
- `source` pode filtrar origem direta do ledger ou origem de obrigacao quando
  combinado com `sourceId`.
- `sourceDetail` atua em detalhes de origem, especialmente custo de servico.

Ordenacao atual:

- `-data_lancamento`.
- `-id`.

Totais e agregacoes atuais:

- `calcular_totais_lancamentos_financeiros` agrega entradas, saidas e resultado
  financeiro.
- Os totais sao calculados para consolidado e para os fluxos `fco`, `fci` e
  `fcf`.
- Os totais usam `Sum` condicionado por tipo e fluxo.
- O endpoint retorna valores numericos `float` ja quantizados.

Dependencias atuais:

- `montar_payload_lancamentos_financeiros_api`.
- `normalizar_filtros_lancamentos`.
- `serializar_lancamento_financeiro`.
- `serializar_totais`.
- `serializar_filtros_lancamentos`.
- `filtrar_lancamentos_financeiros`.
- `calcular_totais_lancamentos_financeiros`.
- `serializar_dimensao_operacional_financeira`.
- `resolver_intervalo_periodo_canonico`.
- `normalizar_codigo_contrato_visual`.
- `resolver_codigo_contrato_visual_parametros`.
- `montar_filtro_evento_ou_orcamento_por_contrato_visual`.
- `require_api_permission`.

Complexidade de queries:

- A listagem executa `count()` para total.
- A pagina usa queryset com `select_related` para cliente, evento,
  `evento__cliente` e `evento__orcamento`.
- Os totais executam agregacao separada via selector.
- O serializer foi desenhado para evitar lazy load quando as relacoes esperadas
  estao carregadas.
- O query count deve ser preservado ou explicitamente justificado caso a suite
  revele diferenca.

## Riscos especificos de lancamentos financeiros

- Endpoint financeiro canonico usado como ledger realizado.
- Payload possui muitos aliases de transicao usados pelo frontend.
- Mudanca acidental em filtros pode alterar totais financeiros exibidos.
- Mudanca em `source`, `sourceId` ou `sourceDetail` pode quebrar navegacao entre
  obrigacoes, baixas e ledger.
- Mudanca em `contractCode`, `eventId` ou `clientId` pode quebrar filtros de
  dimensao operacional.
- DRF, se usado sem cuidado, muda `405` para payload JSON padrao.
- DRF, se usar permissao global, pode substituir `401`/`403` atuais.
- Uso direto de `Response` pode perder headers `Cache-Control` atuais.
- OpenAPI tende a ficar generico sem schema manual, mas runtime tem prioridade.
- Query count pode piorar caso selectors/serializers sejam alterados.

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
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Reaproveitar `montar_payload_lancamentos_financeiros_api`.
- Reaproveitar filtros, selectors e serializers manuais atuais.
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
- `GET` anonimo preserva `401` JSON atual.
- `GET` autenticado sem permissao preserva `403` JSON atual.
- `GET` autenticado com permissao preserva `200` e shape atual.
- Headers JSON/no-store preservados em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual.
- Filtros HTTP canonicos preservados.
- Aliases internos nao coletados pela view continuam fora do contrato HTTP.
- Paginacao preservada.
- Ordenacao preservada.
- Totais e agregacoes preservados.
- Query count preservado ou diferenca justificada e aceita.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora de `GET /api/lancamentos-financeiros/` e alterado.

## Criterios de bloqueio

Parar imediatamente se:

- Algum total financeiro mudar.
- Algum filtro HTTP canonico mudar.
- Algum alias atual do payload mudar.
- `limit`/`offset` mudarem de comportamento.
- `405` mudar para JSON DRF padrao.
- `401` ou `403` mudarem.
- Header `Cache-Control` mudar em respostas JSON.
- Query count piorar sem justificativa tecnica clara.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar obrigacoes, baixas, dashboard, mes financeiro ou
  modelagem canonica junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_lancamentos_financeiros`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em outros endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum selector/serializer manual seja alterado.

## Fases

### PM-26.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como financeiro sensivel, com migracao isolada.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-26.1:

- `caixa/views_lancamentos.py`.
- `caixa/urls.py`.
- `caixa/permissions.py`.
- `caixa/serializers_lancamentos.py`.
- `caixa/selectors_lancamentos.py`.
- `caixa/models.py`.
- `caixa/constants_financeiros.py`.
- `caixa/utils_periodos.py`.
- `caixa/services_dimensoes_operacionais.py`.
- `caixa/utils_contratos.py`.
- `caixa/tests.py`.

### PM-26.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `GET` anonimo retorna `401`.
- `GET` autenticado sem `caixa.view_lancamentofinanceiro` retorna `403`.
- `GET` com permissao retorna `200`.
- Headers JSON/no-store em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com:
  - `Allow: GET`;
  - body vazio;
  - `Content-Type: text/html; charset=utf-8`;
  - sem `Cache-Control`, se esse for o contrato atual.
- Shape completo de `data`.
- Shape completo de `data.items[]`.
- Shape completo de `data.summary`.
- Shape completo de `data.summary.cashFlows`.
- Shape completo de `data.filters`.
- Shape completo de `data.pagination`.
- Shape completo de `data.meta`.
- Filtros HTTP canonicos preservados:
  - `period`;
  - `quickPeriod`;
  - `startDate`;
  - `endDate`;
  - `contractCode`;
  - `eventId`;
  - `clientId`;
  - `cashFlowGroup`;
  - `type`;
  - `nature`;
  - `origin`;
  - `source`;
  - `sourceId`;
  - `sourceDetail`;
  - `status`;
  - `search`;
  - `limit`;
  - `offset`.
- `limit` e `offset` preservados como entrada e retorno em
  `data.pagination`.
- Congelar que aliases internos nao coletados pela view HTTP, como
  `costCenterId`, continuam fora do contrato.
- Resposta vazia mantem shape.
- Ordenacao `-data_lancamento`, `-id` preservada.
- Totais preservados.
- Query count constante preservado, se possivel.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de lancamentos financeiros>
```

### PM-26.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_lancamentos_financeiros` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_GET` por fora, ou equivalente, para manter `405` Django
  padrao.
- Usar `AllowAny` local se necessario para preservar `401`/`403` manuais.
- Preservar permissao manual `caixa.view_lancamentofinanceiro`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar filtros atuais.
- Preservar aliases atuais.
- Preservar paginacao atual.
- Preservar totais atuais.
- Preservar ordenacao atual.
- Reaproveitar `montar_payload_lancamentos_financeiros_api`.
- Reaproveitar helpers atuais do selector.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em obrigacoes, baixas, dashboard, mes financeiro ou modelagem
  canonica.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de lancamentos financeiros>
```

### PM-26.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de lancamentos financeiros>
python manage.py test <testes relacionados existentes>
python manage.py test
```

Validar:

- Testes focados de lancamentos financeiros passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui `GET /api/lancamentos-financeiros/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.
- Query count foi preservado ou diferenca foi justificada.

### PM-26.5 - Encerramento

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

### PM-26.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- Endpoint permanece Django puro antes da migracao.
- Endpoint classificado como financeiro sensivel.
- Decisao: migrar sozinho.
- Nenhuma alteracao de arquivo feita na PM-26.1.

### PM-26.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados:

- `test_api_lancamentos_financeiros_autenticacao_permissao_headers_e_shape_vazio`.
- `test_api_lancamentos_financeiros_metodos_nao_permitidos_preservam_405`.
- `test_api_lancamentos_financeiros_preserva_shape_itens_totais_ordenacao_e_paginacao`.
- `test_api_lancamentos_financeiros_preserva_filtros_canonicos_e_aliases_internos_fora_do_contrato`.
- `test_api_lancamentos_financeiros_mantem_query_count_constante_com_mais_registros`.

Helper de teste criado:

- `_assert_lancamento_financeiro_api_fields`.
- `_criar_cenario_lancamentos_financeiros_api`.

Contratos congelados:

- `GET` anonimo retorna `401` JSON atual.
- `GET` autenticado sem `caixa.view_lancamentofinanceiro` retorna `403`
  JSON atual.
- `GET` com permissao retorna `200`.
- Headers JSON/no-store preservados em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com `Allow: GET`,
  body vazio, `Content-Type: text/html; charset=utf-8` e sem
  `Cache-Control`.
- Shape completo de `data`, `data.items[]`, `data.summary`,
  `data.summary.cashFlows`, `data.filters`, `data.pagination` e `data.meta`.
- Filtros HTTP canonicos preservados.
- `limit` e `offset` preservados como entrada e retorno em
  `data.pagination`.
- Aliases internos nao coletados pela view HTTP, como `costCenterId`,
  continuam fora do contrato.
- Resposta vazia mantem shape.
- Ordenacao `-data_lancamento`, `-id` preservada.
- Totais consolidados e por fluxo preservados.
- Query count constante congelado em teste focado.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_autenticacao_permissao_headers_e_shape_vazio caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_preserva_shape_itens_totais_ordenacao_e_paginacao caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_preserva_filtros_canonicos_e_aliases_internos_fora_do_contrato caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_mantem_query_count_constante_com_mais_registros
DEBUG=True SECRET_KEY=local-validation-secret python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_exige_permissao_do_ledger caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_periodo_frontend caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_event_id_canonico caixa.tests.LancamentoFinanceiroDominioTests.test_selector_resume_totais_dos_lancamentos_financeiros
```

Resultados:

- Testes novos: 5 testes OK.
- `python manage.py check`: OK.
- Testes focados existentes: 4 testes OK.

### PM-26.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_lancamentos.py`.

Implementacao:

- Somente `api_lancamentos_financeiros` foi migrado.
- Usado `@api_view(["GET"])`.
- Usado `@permission_classes([AllowAny])` local para impedir que a permissao
  global do DRF substitua os `401`/`403` atuais.
- `@require_GET` foi mantido por fora para preservar `405` Django padrao,
  `Allow: GET`, body vazio, `Content-Type: text/html; charset=utf-8` e
  ausencia de `Cache-Control`.
- `Response` foi usado somente na borda do endpoint migrado.
- `api_authentication_required_response`,
  `api_permission_denied_response` e `api_no_store_json_response` foram
  reaproveitados para preservar payloads e headers.
- A verificacao manual de permissao preserva
  `caixa.view_lancamentofinanceiro`.
- `montar_payload_lancamentos_financeiros_api` e todos os selectors e
  serializers manuais atuais foram reaproveitados sem alteracao.
- Adicionado `extend_schema` seguro para OpenAPI sem alterar runtime.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_autenticacao_permissao_headers_e_shape_vazio caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_preserva_shape_itens_totais_ordenacao_e_paginacao caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_preserva_filtros_canonicos_e_aliases_internos_fora_do_contrato caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_mantem_query_count_constante_com_mais_registros caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_exige_permissao_do_ledger caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_periodo_frontend caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_event_id_canonico caixa.tests.LancamentoFinanceiroDominioTests.test_selector_resume_totais_dos_lancamentos_financeiros
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Testes focados de lancamentos financeiros: 9 testes OK.
- OpenAPI inclui `GET /api/lancamentos-financeiros/`.
- Warnings do spectacular: nenhum warning reportado.

### PM-26.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret ENABLE_API_DOCS=True python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_autenticacao_permissao_headers_e_shape_vazio caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_preserva_shape_itens_totais_ordenacao_e_paginacao caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_preserva_filtros_canonicos_e_aliases_internos_fora_do_contrato caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_mantem_query_count_constante_com_mais_registros caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_exige_permissao_do_ledger caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_periodo_frontend caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_event_id_canonico caixa.tests.LancamentoFinanceiroDominioTests.test_selector_resume_totais_dos_lancamentos_financeiros
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.FiltrosHtmlTests caixa.tests.LancamentoFinanceiroDominioTests
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Testes focados de lancamentos financeiros: 9 testes OK.
- Testes relacionados (`FiltrosHtmlTests` + `LancamentoFinanceiroDominioTests`):
  418 testes OK.
- Suite completa: 745 testes OK.
- Warnings observados durante a suite: warnings esperados de CSRF nos testes de
  autenticacao (`/api/auth/login/` e `/api/auth/logout/`), ja cobertos pela
  suite existente.
- Nenhum warning do spectacular foi reportado.
- Query count constante preservado pelo teste focado.

### PM-26.5 - Encerramento

Status: concluida.

Arquivos alterados nesta PM:

- `caixa/tests.py`.
- `caixa/views_lancamentos.py`.
- `docs/PLANO_PM26_MIGRACAO_LANCAMENTOS_FINANCEIROS_DRF.md`.

Confirmacoes:

- Somente `GET /api/lancamentos-financeiros/` foi migrado.
- Obrigacoes financeiras nao foram alteradas.
- Baixas financeiras canonicas nao foram alteradas.
- Dashboard financeiro nao foi alterado.
- Mes financeiro nao foi alterado.
- Modelagem financeira canonica nao foi alterada.
- Frontend nao foi alterado.
- Settings nao foram alterados.
- CORS nao foi alterado.
- CSRF global nao foi alterado.
- Autenticacao global nao foi alterada.
- Nenhum Serializer DRF foi criado.
- Nenhum ViewSet ou ModelViewSet foi criado.
- Selectors e serializers manuais foram reaproveitados sem alteracao.
- Filtros HTTP canonicos, aliases, paginacao, totais, ordenacao e query count
  foram preservados.
- Paridade runtime prevaleceu sobre OpenAPI.

Riscos residuais:

- O schema OpenAPI ainda documenta o payload como objeto generico, sem schema
  detalhado de `items`, `summary`, `filters`, `pagination` e `meta`.
- O payload continua grande e financeiro; futuras alteracoes em selectors ou
  serializers de lancamentos financeiros devem rodar os testes focados desta
  PM.
- Aliases internos continuam fora do contrato HTTP por decisao de paridade; se
  forem promovidos futuramente, isso deve ser feito em PM separada.

`git status --short` ao fim da validacao antes deste registro:

```text
 M caixa/tests.py
 M caixa/views_lancamentos.py
?? docs/PLANO_PM26_MIGRACAO_LANCAMENTOS_FINANCEIROS_DRF.md
```

Recomendacao final:

- Pronto para commit local manual.
