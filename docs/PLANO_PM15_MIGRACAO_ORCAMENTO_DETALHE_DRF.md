# Plano PM-15 - Migracao incremental de `/api/orcamentos/<id>/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET`/`PUT /api/orcamentos/<id>/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de detalhe de orcamento, sem
mudar regra de negocio, helpers, services, selectors, models, calculos
financeiros ou contrato JSON.

Esta PM cobre somente:

- `GET /api/orcamentos/<id>/`
- `PUT /api/orcamentos/<id>/`

## Escopo

- Congelar o contrato atual em testes antes da migracao.
- Migrar apenas a view `api_orcamento_detalhe`.
- Usar `@api_view(["GET", "PUT"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar autenticacao por sessao Django.
- Preservar CSRF real no `PUT`.
- Preservar permissoes atuais por metodo.
- Preservar status HTTP, JSON, headers e aliases aceitos pelo frontend.
- Preservar `404` Django padrao para orcamento inexistente.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET`/`POST /api/orcamentos/`, ja tratado na PM-14.
- `/api/orcamentos/<id>/aprovar/`.
- Eventos.
- Clientes.
- Custos extras de eventos.
- Endpoints financeiros.
- Frontend.
- ViewSets.
- ModelViewSets.
- Serializers DRF de regra de negocio.
- Alteracoes em services, selectors, models ou calculos financeiros.
- Alteracoes em settings, CORS, CSRF global ou autenticacao global.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = `GET`/`PUT` juntos quando o contrato for coeso.

Endpoints financeiros so devem ser migrados depois de cadastros e operacoes
estarem estaveis em DRF.

Mutations financeiras so devem ser migradas depois dos GETs financeiros.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, CORS ou comportamento
runtime apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

Nao criar serializer DRF apenas para melhorar schema nesta PM, salvo necessidade
tecnica demonstrada e sem impacto no contrato atual.

## Contrato atual identificado na PM-15.1

Arquivo atual:

- `caixa/views_orcamentos_api.py`

View atual:

- `api_orcamento_detalhe`

Rota atual:

- `path("api/orcamentos/<int:pk>/", api_orcamento_detalhe, name="api_orcamento_detalhe")`

Nome da rota:

- `caixa:api_orcamento_detalhe`

Decorador atual:

- `@require_http_methods(["GET", "PUT"])`

Metodos aceitos:

- `GET`
- `PUT`

Metodos nao permitidos:

- `POST`, `PATCH`, `DELETE` e demais metodos fora do contrato retornam `405`
  pelo decorator do Django.
- O header `Allow` esperado deve ser congelado em teste, especialmente
  `GET, PUT`.

Permissao atual do `GET`:

- `VIEW_BUDGET_PERMISSION = "caixa.view_orcamento"`

Permissao atual do `PUT`:

- `CHANGE_BUDGET_PERMISSION = "caixa.change_orcamento"`

Comportamento para usuario anonimo quando a requisicao chega na view:

```json
{"detail": "Authentication credentials were not provided."}
```

Comportamento para usuario autenticado sem permissao:

```json
{"detail": "Permission denied."}
```

CSRF no `PUT`:

- A view atual e Django puro e nao usa `csrf_exempt`.
- `PUT` sem CSRF valido deve ser bloqueado pelo middleware antes da view quando
  testado com `Client(enforce_csrf_checks=True)`.
- `PUT` com CSRF valido deve seguir para autenticacao, permissao, 404,
  validacao ou atualizacao.

Content-Type aceito no `PUT`:

- `application/json`
- parametros como charset sao aceitos porque a view considera apenas o valor
  antes de `;`.

Content-Type invalido no `PUT`:

```json
{"detail": "Content-Type deve ser application/json."}
```

Status atual esperado:

- `415`

JSON invalido no `PUT`:

```json
{"detail": "JSON invalido."}
```

Status atual esperado:

- `400`

Orcamento inexistente:

- Depois de autenticacao e permissao, usa
  `get_object_or_404(_budget_queryset(), pk=pk)`.
- Com permissao valida, retorna `404` Django padrao.
- Nao converter para JSON se esse nao for o comportamento atual.

Erros de validacao:

```json
{"errors": "..."}
```

Para duplicidade/integridade de numero/contrato, preservar exatamente o erro
atual observado nos testes de paridade.

Para orcamento aprovado, recusado ou cancelado, preservar o erro atual de
edicao bloqueada:

```json
{"errors": {"status": "..."}}
```

Payload de sucesso do `GET`:

```json
{
  "data": {
    "budget": {},
    "permissions": {
      "canCreate": false,
      "canUpdate": false,
      "canApprove": false
    },
    "filterOptions": {
      "statuses": [],
      "editableStatuses": [],
      "clients": [],
      "configurations": [],
      "services": [],
      "extraCostCategories": []
    },
    "meta": {
      "source": "backend"
    }
  }
}
```

Payload de sucesso do `PUT`:

```json
{
  "data": {
    "budget": {},
    "message": "Orcamento atualizado com sucesso."
  }
}
```

Observacao:

- A mensagem real tem acento no runtime atual. Os testes de paridade devem
  congelar a string exata retornada pela aplicacao.

Campos esperados de `data.budget`:

- `id`
- `number`
- `contract`
- `contractCode`
- `contractName`
- `contractLabel`
- `clientId`
- `clientName`
- `clientTradeName`
- `clientDisplayName`
- `configurationId`
- `configurationName`
- `eventName`
- `eventDate`
- `local`
- `validUntil`
- `status`
- `statusLabel`
- `notes`
- `subtotalCosts`
- `taxAmount`
- `profitAmount`
- `saleAmount`
- `items`
- `extraCosts`
- `isEditable`
- `approvedEventId`
- `createdAt`
- `updatedAt`

Campos esperados de cada item em `data.budget.items`:

- `id`
- `serviceId`
- `serviceName`
- `hoursPerDay`
- `daysCount`
- `peopleCount`
- `dailyRateUsed`
- `mealAmountUsed`
- `transportAmountUsed`
- `profitMarginUsed`
- `taxRateUsed`
- `usesSpecialRule`
- `dayValuePerPerson`
- `mealQuantityPerDay`
- `transportQuantityPerDay`
- `serviceCostAmount`
- `mealCostAmount`
- `transportCostAmount`
- `overtimeAmount`
- `costAmount`
- `amountWithMargin`
- `taxAmount`
- `profitAmount`
- `saleAmount`

Campos esperados de cada item em `data.budget.extraCosts`:

- `id`
- `category`
- `categoryLabel`
- `description`
- `plannedAmount`
- `dueDate`
- `notes`
- `eventExtraCostId`

Aliases aceitos no payload do `PUT`:

- `clientId`, `cliente`
- `configurationId`, `configuracao_financeira`
- `number`, `numero`, `contract`, `contrato`
- `eventName`, `nome_evento`
- `eventDate`, `data_evento`
- `validUntil`, `validade`
- `notes`, `observacoes`
- `items`, `itens`
- `extraCosts`, `custos_extras`
- aliases internos de itens e custos extras ja aceitos pelos helpers atuais

Helpers atuais que devem ser reaproveitados:

- `_json_required_response`
- `_atualizar_orcamento_response`
- `_serialize_orcamento`
- `_serialize_orcamento_item`
- `_serialize_custo_extra`
- `_filter_options`
- `_permissions_payload`
- `_orcamento_data_from_payload`
- `_itens_from_payload`
- `_custos_extras_from_payload`
- `_salvar_orcamento_from_payload`
- `_budget_queryset`
- `api_no_store_json_response`
- `require_api_permission`, ou resposta equivalente com os mesmos JSONs

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- Respostas `405` devem preservar o header `Allow`.
- `404` Django padrao e falhas de CSRF devem preservar o comportamento atual.

## Riscos

- O `PUT` substitui itens e custos extras do orcamento.
- O `PUT` dispara validacoes de model e recalculo de totais.
- O endpoint permite editar campos financeiros dos itens.
- Orcamentos aprovados, recusados ou cancelados devem continuar bloqueados.
- DRF pode tentar substituir `401`, `403`, `400`, `404`, `415` ou `405` por
  erros padrao se a migracao nao mantiver controles locais.
- `SessionAuthentication` do DRF pode interferir no fluxo de CSRF ou no parse
  de JSON invalido se nao for controlado com testes.
- `Response` pode alterar detalhes de headers ou renderizacao se usado fora da
  borda.
- `404` Django padrao pode mudar para JSON se a migracao usar comportamento
  padrao do DRF sem cuidado.
- OpenAPI pode ficar generico sem serializer DRF, mas isso e aceitavel se a
  paridade runtime for preservada.

## Guardrails

- Nao migrar `GET`/`POST /api/orcamentos/` novamente.
- Nao migrar `/api/orcamentos/<id>/aprovar/`.
- Nao alterar eventos, clientes ou endpoints financeiros.
- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao criar serializer DRF inicialmente.
- Nao mover calculo financeiro para serializer, view DRF ou frontend.
- Nao alterar services, selectors, helpers ou regra de negocio.
- Nao alterar JSON, status HTTP ou headers para melhorar OpenAPI.
- Reaproveitar helpers atuais sempre que possivel.
- Usar permissoes manuais por metodo para preservar contrato.
- Usar `AllowAny` local somente se necessario para impedir respostas padrao do
  DRF e manter os JSONs atuais.
- Reaproveitar `JsonBodySafeSessionAuthentication` se necessario para preservar
  CSRF em `PUT`, sem alterar autenticacao global.
- Preservar 404 Django padrao para orcamento inexistente.

## PM-15.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas realizadas:

- View atual identificada.
- URL e nome da rota identificados.
- Metodos aceitos identificados.
- Permissoes por metodo identificadas.
- Comportamento de usuario anonimo identificado.
- Comportamento de usuario sem permissao identificado.
- CSRF no `PUT` identificado.
- Content-Type aceito identificado.
- JSON invalido identificado.
- Comportamento de orcamento inexistente identificado.
- Shapes principais de sucesso identificados.
- Headers relevantes identificados.
- Aliases de `PUT` identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum codigo runtime alterado.

## PM-15.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

### Paridade de GET

Criar ou reforcar testes para:

- usuario anonimo retorna `401` com JSON atual;
- usuario autenticado sem `caixa.view_orcamento` retorna `403` com JSON atual;
- usuario com `caixa.view_orcamento` retorna `200`;
- sucesso contem `data.budget`;
- sucesso contem `data.permissions`;
- sucesso contem `data.filterOptions`;
- sucesso contem `data.meta.source == "backend"`;
- `data.budget` mantem shape completo de `_serialize_orcamento`;
- itens e custos extras mantem shapes atuais;
- orcamento inexistente preserva `404` Django padrao;
- `Content-Type` contem `application/json` nas respostas JSON;
- `Cache-Control` contem `no-store` nas respostas JSON.

### Paridade de PUT

Criar ou reforcar testes para:

- `PUT` sem CSRF valido bloqueia antes da view com
  `Client(enforce_csrf_checks=True)`;
- `PUT` com CSRF valido segue para autenticacao, permissao, 404, validacao ou
  atualizacao;
- usuario anonimo retorna `401` com JSON atual quando a requisicao chega na
  view;
- usuario autenticado sem `caixa.change_orcamento` retorna `403` com JSON
  atual;
- orcamento inexistente preserva `404` Django padrao;
- `Content-Type` invalido retorna `415` com JSON atual;
- JSON invalido retorna `400` com JSON atual;
- validacoes criticas retornam `400` com `{"errors": ...}`;
- duplicidade de numero/contrato retorna o erro atual observado;
- orcamento aprovado, recusado ou cancelado continua bloqueado;
- sucesso retorna `200`;
- sucesso contem `data.budget`;
- sucesso contem `data.message`;
- `data.message` preserva texto atual;
- `data.budget` mantem shape completo de `_serialize_orcamento`;
- aliases principais do `PUT` continuam aceitos;
- `Content-Type` contem `application/json` nas respostas JSON;
- `Cache-Control` contem `no-store` nas respostas JSON.

### Metodos nao permitidos

Criar ou reforcar testes para:

- `POST /api/orcamentos/<id>/` continua `405`;
- `PATCH /api/orcamentos/<id>/` continua `405`;
- `DELETE /api/orcamentos/<id>/` continua `405`;
- header `Allow` preservado, especialmente `GET, PUT`.

### Validacoes criticas

Congelar ao menos:

- cliente obrigatorio/invalido;
- configuracao financeira obrigatoria/invalida;
- data do evento obrigatoria/invalida;
- status fora de `rascunho` ou `enviado`;
- lista de itens ausente ou vazia;
- item sem servico;
- item com horas, dias ou pessoas invalidos;
- custo extra com categoria invalida;
- custo extra sem descricao;
- custo extra com valor ou vencimento invalido;
- duplicidade de numero/contrato;
- bloqueio de edicao de orcamento aprovado.

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_orcamento_detalhe>
```

## PM-15.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_orcamento_detalhe` para DRF com paridade
comprovada.

Implementacao esperada:

- converter apenas a view `api_orcamento_detalhe`;
- usar `@api_view(["GET", "PUT"])`;
- usar `Response` somente na borda;
- manter helpers atuais de GET e PUT;
- manter permissoes manuais por metodo;
- manter CSRF real no `PUT`;
- preservar 404 Django padrao;
- nao criar serializer DRF inicialmente;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao alterar contrato.

Regras:

- Manter URL `/api/orcamentos/<id>/`.
- Manter nome de rota `caixa:api_orcamento_detalhe`.
- Manter metodos `GET` e `PUT`.
- Manter status HTTP.
- Manter JSON.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow` do `405`.
- Manter permissao `caixa.view_orcamento` no `GET`.
- Manter permissao `caixa.change_orcamento` no `PUT`.
- Manter autenticacao por sessao Django.
- Manter CSRF real em `PUT`.
- Manter CORS sem alteracao.
- Manter aliases de payload.
- Reaproveitar `_salvar_orcamento_from_payload`.
- Reaproveitar serializacao atual de orcamento, itens e custos extras.
- Reaproveitar `_filter_options` e `_permissions_payload`.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- O DRF nao deve trocar os JSONs atuais de `401`, `403`, `400`, `415` ou `405`.
- O DRF nao deve trocar o `404` Django padrao por resposta JSON.
- Se `SessionAuthentication` interferir no comportamento de JSON invalido, CSRF
  ou erros atuais, ajustar localmente sem alterar configuracao global.
- Se for necessario usar classe local ja existente, reaproveitar sem duplicar.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_orcamento_detalhe>
```

Gate de saida:

- `/api/orcamentos/<id>/` migrado para DRF.
- `GET` e `PUT` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-15.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_orcamento_detalhe>
python manage.py test caixa.tests.OrcamentosApiTests
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/orcamentos/{id}/`;
- nenhuma regressao;
- `GET`/`POST /api/orcamentos/` nao foi alterado novamente;
- `/api/orcamentos/<id>/aprovar/` nao foi alterado;
- eventos, clientes e financeiro nao foram alterados;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint `/api/orcamentos/<id>/`, testes e registro do
  plano;
- `GET /api/orcamentos/<id>/` preservado;
- `PUT /api/orcamentos/<id>/` preservado;
- 404 Django padrao preservado;
- CSRF global nao alterado;
- CORS nao alterado;
- autenticacao global nao alterada;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- suite focada passa;
- testes relacionados de orcamentos passam;
- suite geral passa;
- warnings do spectacular registrados;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-15.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-15 antes de avancar para
`/api/orcamentos/<id>/aprovar/` ou outra PM.

Tarefas:

- Atualizar este documento.
- Registrar arquivos alterados.
- Registrar testes criados.
- Registrar comandos executados.
- Registrar resultado dos testes focados.
- Registrar resultado dos testes relacionados de orcamentos.
- Registrar resultado da suite completa.
- Registrar resultado do `spectacular --validate`.
- Registrar warnings encontrados.
- Registrar diferencas encontradas, se houver.
- Registrar decisao sobre `schema.yml`, se tiver sido gerado.
- Confirmar que nenhum outro endpoint foi migrado.
- Confirmar que frontend nao foi alterado.
- Confirmar que settings, CORS, CSRF global e auth global nao foram alterados.
- Registrar riscos residuais.
- Registrar recomendacao: pronto, ajustar ou reverter.

Proximo endpoint natural, somente se PM-15 estiver estavel:

- PM-16: `POST /api/orcamentos/<id>/aprovar/`.

## Criterios globais de aceite

- `GET /api/orcamentos/<id>/` mantem paridade.
- `PUT /api/orcamentos/<id>/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodos preservados.
- Status HTTP preservados.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow` preservado nos `405`.
- 404 Django padrao preservado.
- Autenticacao por sessao Django preservada.
- CSRF real preservado no `PUT`.
- CORS preservado.
- Permissao `caixa.view_orcamento` preservada no `GET`.
- Permissao `caixa.change_orcamento` preservada no `PUT`.
- Aliases de payload preservados.
- Regras financeiras e recalculo de totais preservados.
- Bloqueio de orcamentos nao editaveis preservado.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/orcamentos/{id}/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- header relevante mudar;
- CSRF mudar;
- CORS mudar;
- permissao por metodo mudar;
- usuario anonimo receber contrato diferente;
- usuario sem permissao receber contrato diferente;
- orcamento inexistente receber contrato diferente;
- payload de `GET` ou `PUT` mudar;
- aliases de payload mudarem;
- recalculo de totais mudar;
- edicao de itens ou custos extras mudar;
- bloqueio de orcamento aprovado mudar;
- frontend precisar ser alterado;
- `GET`/`POST /api/orcamentos/` precisar ser alterado novamente sem
  justificativa tecnica;
- `/api/orcamentos/<id>/aprovar/` precisar ser migrado junto;
- outro endpoint precisar ser alterado;
- DRF gerar resposta padrao diferente para `401`, `403`, `400`, `404`, `415`
  ou `405`;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar services, selectors ou models.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_orcamento_detalhe`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_orcamento_detalhe`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

## Registro de execucao

### Registro de execucao - PM-15.1

Fase: diagnostico read-only.

Endpoint alvo:

- `GET /api/orcamentos/<id>/`
- `PUT /api/orcamentos/<id>/`

Arquivos lidos:

- `caixa/views_orcamentos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/models.py`
- `caixa/tests.py`

Resultado:

- Contrato atual mapeado.
- View ainda estava Django puro.
- Lacunas de paridade identificadas para `GET`, `PUT`, CSRF, headers,
  metodos nao permitidos, 404 Django padrao e validacoes criticas.
- Nenhum arquivo runtime alterado nesta fase.

`git status --short` observado ao final da PM-15.1:

```text
```

### Registro de execucao - PM-15.2

Fase: congelamento de contrato em testes.

Arquivos alterados:

- `caixa/tests.py`

Testes criados:

- `test_api_orcamento_detalhe_get_preserva_auth_permissao_shape_headers_e_404`
- `test_api_orcamento_detalhe_put_requer_csrf_antes_da_view`
- `test_api_orcamento_detalhe_put_preserva_auth_permissao_404_e_erros_de_payload`
- `test_api_orcamento_detalhe_put_preserva_duplicidade_aliases_e_sucesso`
- `test_api_orcamento_detalhe_metodos_nao_permitidos_preservam_405_e_allow`

Teste reforcado:

- `test_api_orcamento_detalhe_bloqueia_edicao_de_orcamento_aprovado`

Cobertura adicionada:

- `GET` anonimo `401`.
- `GET` autenticado sem `caixa.view_orcamento` `403`.
- `GET` com permissao `200`.
- Shape completo de `data.budget`, `data.permissions`, `data.filterOptions` e
  `data.meta`.
- 404 Django padrao no `GET`.
- Headers JSON e `Cache-Control` com `no-store`.
- `PUT` sem CSRF valido bloqueado antes da view.
- `PUT` com CSRF valido chegando na view.
- `PUT` anonimo `401`.
- `PUT` autenticado sem `caixa.change_orcamento` `403`.
- 404 Django padrao no `PUT`.
- `Content-Type` invalido `415`.
- JSON invalido `400`.
- Validacoes criticas com `{"errors": ...}`.
- Duplicidade de numero/contrato.
- Bloqueio de orcamento aprovado.
- Sucesso `200` com `data.budget` e `data.message`.
- Aliases legados principais do payload de atualizacao.
- `POST`, `PATCH` e `DELETE` retornando `405` com `Allow: GET, PUT`.

Comandos executados:

```bash
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py check
git diff --stat
git status --short
```

Resultado:

- `OrcamentosApiTests`: 22 testes executados, todos aprovados.
- `python manage.py check`: sem issues.
- Nenhuma migracao runtime feita ainda nesta fase.

### Registro de execucao - PM-15.3

Fase: migracao controlada de `api_orcamento_detalhe` para DRF.

Arquivos alterados:

- `caixa/views_orcamentos_api.py`

Mudanca aplicada:

- `api_orcamento_detalhe` passou a usar `@api_view(["GET", "PUT"])`.
- Foi mantido `@require_http_methods(["GET", "PUT"])` para preservar `405` e
  header `Allow`.
- Foi usada `Response` somente na borda do endpoint.
- Foram reaproveitados os helpers atuais de resposta, serializacao, validacao,
  atualizacao e recalculo.
- Foi reaproveitada `JsonBodySafeSessionAuthentication` para preservar CSRF real
  em `PUT`.
- Foi usada permissao local `AllowAny` para impedir que o DRF substitua os JSONs
  manuais atuais de `401` e `403`.
- Permissoes manuais preservadas:
  - `GET`: `caixa.view_orcamento`;
  - `PUT`: `caixa.change_orcamento`.
- 404 Django padrao preservado via `page_not_found`.
- `extend_schema` local foi adicionado para refletir `GET` e `PUT`.

Nao foi criado:

- serializer DRF;
- `ViewSet`;
- `ModelViewSet`;
- app novo;
- helper global novo.

Comandos executados:

```bash
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py check
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; $env:ENABLE_API_DOCS='True'; venv\Scripts\python.exe manage.py spectacular --validate
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
git diff --stat
git status --short
```

Resultado:

- `python manage.py check`: sem issues.
- `python manage.py spectacular --validate`: passou sem warnings observados.
- OpenAPI passou a incluir `/api/orcamentos/{id}/`.
- `OrcamentosApiTests`: 22 testes executados, todos aprovados.
- Nenhum outro endpoint foi migrado nesta fase.
- `GET`/`POST /api/orcamentos/` nao foi alterado novamente.
- `/api/orcamentos/<id>/aprovar/` nao foi alterado.

### Registro de execucao - PM-15.4

Fase: validacao completa.

Comandos executados:

```bash
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py check
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; $env:ENABLE_API_DOCS='True'; venv\Scripts\python.exe manage.py spectacular --validate
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py test
git diff --stat
git status --short
```

Resultado:

- `python manage.py check`: sem issues.
- `python manage.py spectacular --validate`: passou sem warnings observados.
- `OrcamentosApiTests`: 22 testes executados, todos aprovados.
- Suite completa: 699 testes executados, todos aprovados.
- A primeira execucao da suite completa estourou o timeout local de 5 minutos
  antes de devolver resultado; a execucao repetida com timeout maior passou.
- Nenhum `schema.yml` residual foi gerado.

Warnings observados:

- Warnings esperados de CSRF em testes negativos:
  - `/api/eventos/custos-extras/`;
  - `/api/auth/logout/`.
- Log esperado do `django-axes` em teste de login invalido.

Confirmacoes:

- `GET`/`POST /api/orcamentos/` nao foi alterado novamente.
- `/api/orcamentos/<id>/aprovar/` nao foi migrado.
- Eventos, clientes e financeiro nao foram alterados pela PM-15.
- Frontend nao foi alterado.
- Settings, CORS, CSRF global e autenticacao global nao foram alterados.
- Contrato runtime de `GET`/`PUT /api/orcamentos/<id>/` ficou preservado pelos
  testes de paridade.

### Registro de execucao - PM-15.5

Fase: encerramento.

Arquivos alterados pela PM-15:

- `caixa/tests.py`
- `caixa/views_orcamentos_api.py`
- `docs/PLANO_PM15_MIGRACAO_ORCAMENTO_DETALHE_DRF.md`

Resultado final:

- PM-15 concluida.
- `GET /api/orcamentos/<id>/` migrado para DRF.
- `PUT /api/orcamentos/<id>/` migrado para DRF.
- 404 Django padrao preservado.
- Nenhum outro endpoint de orcamento foi migrado.
- Nenhum serializer DRF foi criado.
- Nenhum `ViewSet` ou `ModelViewSet` foi criado.
- OpenAPI inclui `/api/orcamentos/{id}/`.
- Paridade runtime prevaleceu sobre documentacao.

Riscos residuais:

- O schema OpenAPI segue generico (`object`) porque a PM nao criou serializer
  DRF, por prioridade de paridade runtime.
- `PUT /api/orcamentos/<id>/` permanece um endpoint de maior risco funcional
  porque substitui itens e custos extras e recalcula totais; a cobertura de
  paridade criada nesta PM deve ser mantida antes da PM-16.
- A acao de aprovacao de orcamento ainda permanece fora de DRF e deve ser
  tratada em PM propria.

`git status --short` ao final da PM-15.5:

```text
 M caixa/tests.py
 M caixa/views_orcamentos_api.py
?? docs/PLANO_PM15_MIGRACAO_ORCAMENTO_DETALHE_DRF.md
```

Recomendacao:

- PM-15 pronta para commit local manual.
- Proximo passo natural: PM-16, iniciando por diagnostico read-only de
  `POST /api/orcamentos/<id>/aprovar/`.
