# Plano PM-14 - Migracao incremental de `/api/orcamentos/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET`/`POST /api/orcamentos/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint, sem mudar regra de negocio,
helpers, services, selectors, models, calculos financeiros ou contrato JSON.

Esta PM cobre somente:

- `GET /api/orcamentos/`
- `POST /api/orcamentos/`

## Escopo

- Congelar o contrato atual em testes antes da migracao.
- Migrar apenas a view `api_orcamentos`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar autenticacao por sessao Django.
- Preservar CSRF real no `POST`.
- Preservar permissoes atuais por metodo.
- Preservar status HTTP, JSON, headers e aliases aceitos pelo frontend.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `/api/orcamentos/<id>/`.
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
- 1 PM = `GET`/`POST` juntos apenas quando o contrato for pequeno e coeso.

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

## Contrato atual identificado na PM-14.1

Arquivo atual:

- `caixa/views_orcamentos_api.py`

View atual:

- `api_orcamentos`

Rota atual:

- `path("api/orcamentos/", api_orcamentos, name="api_orcamentos")`

Nome da rota:

- `caixa:api_orcamentos`

Decorador atual:

- `@require_http_methods(["GET", "POST"])`

Metodos aceitos:

- `GET`
- `POST`

Metodos nao permitidos:

- `PUT`, `PATCH`, `DELETE` e demais metodos fora do contrato retornam `405`
  pelo decorator do Django.
- O header `Allow` esperado deve ser congelado em teste, especialmente
  `GET, POST`.

Permissao atual do `GET`:

- `VIEW_BUDGET_PERMISSION = "caixa.view_orcamento"`

Permissoes atuais do `POST`:

- `ADD_BUDGET_PERMISSION = "caixa.add_orcamento"`
- `ADD_BUDGET_ITEM_PERMISSION = "caixa.add_orcamentoitem"`

O `POST` exige as duas permissoes.

Comportamento para usuario anonimo quando a requisicao chega na view:

```json
{"detail": "Authentication credentials were not provided."}
```

Comportamento para usuario autenticado sem permissao:

```json
{"detail": "Permission denied."}
```

CSRF no `POST`:

- A view atual e Django puro e nao usa `csrf_exempt`.
- `POST` sem CSRF valido deve ser bloqueado pelo middleware antes da view
  quando testado com `Client(enforce_csrf_checks=True)`.
- `POST` com CSRF valido deve seguir para autenticacao, permissao, validacao ou
  criacao.

Content-Type aceito no `POST`:

- `application/json`
- parametros como charset sao aceitos porque a view considera apenas o valor
  antes de `;`.

Content-Type invalido no `POST`:

```json
{"detail": "Content-Type deve ser application/json."}
```

Status atual esperado:

- `415`

JSON invalido no `POST`:

```json
{"detail": "JSON invalido."}
```

Status atual esperado:

- `400`

Erros de validacao:

```json
{"errors": "..."}
```

Para duplicidade/integridade de numero/contrato, preservar exatamente o erro
atual observado nos testes de paridade.

Payload de sucesso do `GET`:

```json
{
  "data": {
    "budgets": [],
    "summary": {
      "total": 0,
      "draftCount": 0,
      "sentCount": 0,
      "approvedCount": 0,
      "saleAmount": "0.00"
    },
    "filters": {
      "busca": "",
      "status": "",
      "search": ""
    },
    "filterOptions": {
      "statuses": [],
      "editableStatuses": [],
      "clients": [],
      "configurations": [],
      "services": [],
      "extraCostCategories": []
    },
    "permissions": {
      "canCreate": false,
      "canUpdate": false,
      "canApprove": false
    },
    "meta": {
      "source": "backend"
    }
  }
}
```

Aliases de filtro aceitos no `GET`:

- `search`
- `busca`
- `status`

Campos esperados de cada item em `data.budgets`:

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

Campos esperados de cada item em `data.budgets[].items`:

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

Campos esperados de cada item em `data.budgets[].extraCosts`:

- `id`
- `category`
- `categoryLabel`
- `description`
- `plannedAmount`
- `dueDate`
- `notes`
- `eventExtraCostId`

Payload de sucesso do `POST`:

```json
{
  "data": {
    "budget": {},
    "message": "Orçamento cadastrado com sucesso."
  }
}
```

Status atual esperado:

- `201`

Aliases aceitos no payload do `POST`:

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

- `_is_json_request`
- `_payload_json`
- `_orcamentos_response`
- `_criar_orcamento_response`
- `_json_required_response`
- `_serialize_orcamento`
- `_serialize_orcamento_item`
- `_serialize_custo_extra`
- `_filter_options`
- `_orcamento_data_from_payload`
- `_itens_from_payload`
- `_custos_extras_from_payload`
- `_salvar_orcamento_from_payload`
- `api_no_store_json_response`
- `require_api_permission`

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- Respostas `405` devem preservar o header `Allow`.

## Riscos

- O `POST` cria orcamento, itens e custos extras dentro de transacao.
- O `POST` dispara validacoes de model e recalculo de totais.
- O endpoint exige duas permissoes no `POST`, nao apenas uma.
- DRF pode tentar substituir `401`, `403`, `400`, `415` ou `405` por erros
  padrao se a migracao nao mantiver controles locais.
- `SessionAuthentication` do DRF pode interferir no fluxo de CSRF ou no parse
  de JSON invalido se nao for controlado com testes.
- `Response` pode alterar detalhes de headers ou renderizacao se usado fora da
  borda.
- OpenAPI pode ficar generico sem serializer DRF, mas isso e aceitavel se a
  paridade runtime for preservada.
- O schema pode exigir anotacoes locais seguras; isso nao deve justificar
  mudanca de contrato.

## Guardrails

- Nao migrar `/api/orcamentos/<id>/`.
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
- Se necessario, reaproveitar classe local de autenticacao/CSRF ja existente em
  PMs anteriores em vez de duplicar abstracao.

## PM-14.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas realizadas:

- View atual identificada.
- URL e nome da rota identificados.
- Metodos aceitos identificados.
- Permissoes por metodo identificadas.
- Comportamento de usuario anonimo identificado.
- Comportamento de usuario sem permissao identificado.
- CSRF no `POST` identificado.
- Content-Type aceito no `POST` identificado.
- JSON invalido identificado.
- Shapes principais de sucesso identificados.
- Headers relevantes identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum codigo runtime alterado.

## PM-14.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

### Paridade de GET

Criar ou reforcar testes para:

- usuario anonimo retorna `401` com JSON atual;
- usuario autenticado sem `caixa.view_orcamento` retorna `403` com JSON atual;
- usuario com `caixa.view_orcamento` retorna `200`;
- `Content-Type` contem `application/json`;
- `Cache-Control` contem `no-store`;
- shape completo de `data.budgets`;
- shape completo de `data.summary`;
- shape completo de `data.filters`;
- shape completo de `data.filterOptions`;
- shape completo de `data.permissions`;
- `data.meta.source == "backend"`;
- aliases `search` e `busca`;
- filtro `status`;
- resposta com lista vazia;
- permissoes derivadas:
  - `canCreate`;
  - `canUpdate`;
  - `canApprove`.

### Paridade de POST

Criar ou reforcar testes para:

- `POST` sem CSRF valido bloqueia antes da view com
  `Client(enforce_csrf_checks=True)`;
- `POST` com CSRF valido segue para autenticacao, permissao, validacao ou
  criacao;
- usuario anonimo retorna `401` com JSON atual quando a requisicao chega na
  view;
- usuario autenticado sem `caixa.add_orcamento` retorna `403`;
- usuario autenticado sem `caixa.add_orcamentoitem` retorna `403`;
- usuario autenticado com as duas permissoes segue para validacao ou criacao;
- `Content-Type` invalido retorna `415` com JSON atual;
- JSON invalido retorna `400` com JSON atual;
- erro de validacao retorna `400` com `{"errors": ...}`;
- duplicidade/integridade de numero/contrato retorna o erro atual observado;
- criacao com sucesso retorna `201`;
- sucesso contem `data.budget`;
- sucesso contem `data.message`;
- `data.message` preserva texto atual;
- `Content-Type` contem `application/json`;
- `Cache-Control` contem `no-store`;
- aliases principais de payload continuam aceitos.

### Metodos nao permitidos

Criar ou reforcar testes para:

- `PUT /api/orcamentos/` continua `405`;
- `PATCH /api/orcamentos/` continua `405`;
- `DELETE /api/orcamentos/` continua `405`;
- header `Allow` preservado, especialmente `GET, POST`.

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
- custo extra com valor ou vencimento invalido.

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_orcamentos_lista_criacao>
```

## PM-14.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_orcamentos` para DRF com paridade comprovada.

Implementacao esperada:

- converter apenas a view `api_orcamentos`;
- usar `@api_view(["GET", "POST"])`;
- usar `Response` somente na borda;
- manter helpers atuais de GET e POST;
- manter permissoes manuais por metodo;
- manter CSRF real no `POST`;
- nao criar serializer DRF inicialmente;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao alterar contrato.

Regras:

- Manter URL `/api/orcamentos/`.
- Manter nome de rota `caixa:api_orcamentos`.
- Manter metodos `GET` e `POST`.
- Manter status HTTP.
- Manter JSON.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow` do `405`.
- Manter permissao `caixa.view_orcamento` no `GET`.
- Manter permissoes `caixa.add_orcamento` e `caixa.add_orcamentoitem` no
  `POST`.
- Manter autenticacao por sessao Django.
- Manter CSRF real em `POST`.
- Manter CORS sem alteracao.
- Manter aliases de filtros e payload.
- Reaproveitar `_salvar_orcamento_from_payload`.
- Reaproveitar serializacao atual de orcamento, itens e custos extras.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- O DRF nao deve trocar os JSONs atuais de `401`, `403`, `400`, `415` ou `405`.
- Se `SessionAuthentication` interferir no comportamento de JSON invalido, CSRF
  ou erros atuais, ajustar localmente sem alterar configuracao global.
- Se for necessario usar classe local ja existente, reaproveitar sem duplicar.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_orcamentos_lista_criacao>
```

Gate de saida:

- `/api/orcamentos/` migrado para DRF.
- `GET` e `POST` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-14.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_orcamentos_lista_criacao>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/orcamentos/`;
- nenhuma regressao;
- `/api/orcamentos/<id>/` nao foi alterado;
- `/api/orcamentos/<id>/aprovar/` nao foi alterado;
- eventos, clientes e financeiro nao foram alterados;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint `/api/orcamentos/`, testes e registro do plano;
- `GET /api/orcamentos/` preservado;
- `POST /api/orcamentos/` preservado;
- CSRF global nao alterado;
- CORS nao alterado;
- autenticacao global nao alterada;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- suite focada passa;
- suite geral passa;
- warnings do spectacular registrados;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-14.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-14 antes de avancar para
`/api/orcamentos/<id>/`.

Tarefas:

- Atualizar este documento.
- Registrar arquivos alterados.
- Registrar comandos executados.
- Registrar resultado dos testes focados.
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

Proximo endpoint natural, somente se PM-14 estiver estavel:

- PM-15: `GET`/`PUT /api/orcamentos/<id>/`.

## Criterios globais de aceite

- `GET /api/orcamentos/` mantem paridade.
- `POST /api/orcamentos/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodos preservados.
- Status HTTP preservados.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow` preservado nos `405`.
- Autenticacao por sessao Django preservada.
- CSRF real preservado no `POST`.
- CORS preservado.
- Permissao `caixa.view_orcamento` preservada no `GET`.
- Permissoes `caixa.add_orcamento` e `caixa.add_orcamentoitem` preservadas no
  `POST`.
- Aliases de filtros e payload preservados.
- Regras financeiras e recalculo de totais preservados.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/orcamentos/`.
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
- `POST` exigir permissao diferente das duas permissoes atuais;
- payload de `GET` ou `POST` mudar;
- aliases de filtros ou payload mudarem;
- recalculo de totais mudar;
- criacao de itens ou custos extras mudar;
- frontend precisar ser alterado;
- `/api/orcamentos/<id>/` precisar ser migrado junto;
- `/api/orcamentos/<id>/aprovar/` precisar ser migrado junto;
- outro endpoint precisar ser alterado;
- DRF gerar resposta padrao diferente para `401`, `403`, `400`, `415` ou
  `405`;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar services, selectors ou models.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_orcamentos`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_orcamentos`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

## Registro de execucao

### Registro de execucao - PM-14.1

Fase: diagnostico read-only.

Endpoint alvo:

- `GET /api/orcamentos/`
- `POST /api/orcamentos/`

Arquivos lidos:

- `caixa/views_orcamentos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/selectors_cadastros.py`
- `caixa/models.py`
- `caixa/tests.py`

Resultado:

- Contrato atual mapeado.
- View ainda estava Django puro.
- Lacunas de paridade identificadas para `GET`, `POST`, CSRF, headers,
  metodos nao permitidos e validacoes criticas.
- Nenhum arquivo runtime alterado nesta fase.

`git status --short` observado ao final da PM-14.1:

```text
 M caixa/tests.py
 M caixa/views_eventos_api.py
?? docs/PLANO_PM13_MIGRACAO_EVENTO_DETALHE_DRF.md
```

Observacao:

- Essas pendencias eram da PM-13 e ja existiam antes da criacao deste plano.

### Registro de execucao - PM-14.2

Fase: congelamento de contrato em testes.

Arquivos alterados:

- `caixa/tests.py`

Testes criados:

- `test_api_orcamentos_get_preserva_auth_permissao_shape_headers_e_aliases`
- `test_api_orcamentos_get_lista_vazia_preserva_shape_e_headers`
- `test_api_orcamentos_post_requer_csrf_antes_da_view`
- `test_api_orcamentos_post_preserva_auth_permissoes_content_type_json_e_validacoes`
- `test_api_orcamentos_post_preserva_duplicidade_aliases_e_criacao`
- `test_api_orcamentos_metodos_nao_permitidos_preservam_405_e_allow`

Cobertura adicionada:

- `GET` anonimo `401`.
- `GET` autenticado sem `caixa.view_orcamento` `403`.
- `GET` com permissao `200`.
- Shape completo de `data.budgets`, `data.summary`, `data.filters`,
  `data.filterOptions`, `data.permissions` e `data.meta`.
- Headers JSON e `Cache-Control` com `no-store`.
- Lista vazia.
- Aliases de filtro `search`/`busca` e filtro `status`.
- `POST` sem CSRF valido bloqueado antes da view com
  `Client(enforce_csrf_checks=True)`.
- `POST` com CSRF valido chegando na view.
- `POST` anonimo `401`.
- `POST` sem `caixa.add_orcamento` ou sem `caixa.add_orcamentoitem` `403`.
- `Content-Type` invalido `415`.
- JSON invalido `400`.
- Validacoes criticas com `{"errors": ...}`.
- Duplicidade de numero/contrato.
- Criacao com sucesso `201`.
- Aliases legados principais do payload de criacao.
- `PUT`, `PATCH` e `DELETE` retornando `405` com `Allow: GET, POST`.

Comandos executados:

```bash
python manage.py test caixa.tests.OrcamentosApiTests
```

Resultado:

- Falhou no `python` global porque Django nao estava instalado nesse
  interpretador.

Comandos executados com ambiente local:

```bash
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
$env:DEBUG='True'; $env:SECRET_KEY='local-validation-secret'; venv\Scripts\python.exe manage.py check
git diff --stat
git status --short
```

Resultado:

- `OrcamentosApiTests`: 17 testes executados, todos aprovados.
- `python manage.py check`: sem issues.
- Nenhuma migracao runtime feita ainda nesta fase.

Observacao:

- Nos testes com `Client(enforce_csrf_checks=True)`, as requisicoes com token
  CSRF valido foram mantidas sem `secure=True` para evitar bloqueio adicional
  de Referer do middleware e realmente validar a chegada na view.

### Registro de execucao - PM-14.3

Fase: migracao controlada de `api_orcamentos` para DRF.

Arquivos alterados:

- `caixa/views_orcamentos_api.py`

Mudanca aplicada:

- `api_orcamentos` passou a usar `@api_view(["GET", "POST"])`.
- Foi mantido `@require_http_methods(["GET", "POST"])` para preservar `405` e
  header `Allow`.
- Foi usada `Response` somente na borda do endpoint.
- Foram reaproveitados os helpers atuais de resposta, serializacao, validacao,
  criacao e recalculo.
- Foi reaproveitada `JsonBodySafeSessionAuthentication` para preservar CSRF real
  em `POST`.
- Foi usada permissao local `AllowAny` para impedir que o DRF substitua os JSONs
  manuais atuais de `401` e `403`.
- Permissoes manuais preservadas:
  - `GET`: `caixa.view_orcamento`;
  - `POST`: `caixa.add_orcamento` e `caixa.add_orcamentoitem`.
- `_payload_json` passou a aceitar `Request` do DRF e capturar `ParseError`,
  preservando `{"detail": "JSON invalido."}`.
- `extend_schema` local foi adicionado para refletir GET `200` e POST `201`.

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
- OpenAPI passou a incluir `/api/orcamentos/`.
- Schema local mostra `GET /api/orcamentos/` com resposta `200`.
- Schema local mostra `POST /api/orcamentos/` com resposta `201`.
- `OrcamentosApiTests`: 17 testes executados, todos aprovados.
- Nenhum outro endpoint foi migrado nesta fase.

### Registro de execucao - PM-14.4

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
- `OrcamentosApiTests`: 17 testes executados, todos aprovados.
- Suite completa: 694 testes executados, todos aprovados.
- Nenhum `schema.yml` residual foi gerado.

Warnings observados:

- Warnings esperados de CSRF em testes negativos:
  - `/api/eventos/custos-extras/`;
  - `/api/auth/logout/`.
- Aviso local de line ending em `caixa/views_eventos_api.py`:
  `CRLF will be replaced by LF`.

Confirmacoes:

- `/api/orcamentos/<id>/` nao foi migrado.
- `/api/orcamentos/<id>/aprovar/` nao foi migrado.
- Eventos, clientes e financeiro nao foram alterados pela PM-14.
- Frontend nao foi alterado.
- Settings, CORS, CSRF global e autenticacao global nao foram alterados.
- Contrato runtime de `GET`/`POST /api/orcamentos/` ficou preservado pelos
  testes de paridade.

### Registro de execucao - PM-14.5

Fase: encerramento.

Arquivos alterados pela PM-14:

- `caixa/tests.py`
- `caixa/views_orcamentos_api.py`
- `docs/PLANO_PM14_MIGRACAO_ORCAMENTOS_DRF.md`

Arquivos ja pendentes antes da PM-14 e preservados:

- `caixa/views_eventos_api.py`
- `docs/PLANO_PM13_MIGRACAO_EVENTO_DETALHE_DRF.md`

Resultado final:

- PM-14 concluida.
- `GET /api/orcamentos/` migrado para DRF.
- `POST /api/orcamentos/` migrado para DRF.
- Nenhum outro endpoint de orcamento foi migrado.
- Nenhum serializer DRF foi criado.
- Nenhum `ViewSet` ou `ModelViewSet` foi criado.
- OpenAPI inclui `/api/orcamentos/`.
- Paridade runtime prevaleceu sobre documentacao.

Riscos residuais:

- O schema OpenAPI segue generico (`object`) porque a PM nao criou serializer
  DRF, por prioridade de paridade runtime.
- `POST /api/orcamentos/` permanece um endpoint de maior risco funcional porque
  cria orcamento, itens, custos extras e recalcula totais; a cobertura de
  paridade criada nesta PM deve ser mantida antes da PM-15.
- Endpoints de detalhe e aprovacao de orcamento ainda permanecem fora de DRF e
  devem ser tratados em PM propria.

`git status --short` ao final da PM-14.5:

```text
 M caixa/tests.py
 M caixa/views_eventos_api.py
 M caixa/views_orcamentos_api.py
?? docs/PLANO_PM13_MIGRACAO_EVENTO_DETALHE_DRF.md
?? docs/PLANO_PM14_MIGRACAO_ORCAMENTOS_DRF.md
```

Recomendacao:

- PM-14 pronta para commit local manual, junto com as pendencias ja existentes
  da PM-13 se essa for a unidade de commit escolhida.
- Proximo passo natural: PM-15, iniciando por diagnostico read-only de
  `GET`/`PUT /api/orcamentos/<id>/`.
