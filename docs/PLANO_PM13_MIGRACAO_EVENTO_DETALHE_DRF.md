# Plano PM-13 - Migracao incremental de `/api/eventos/<id>/` para DRF

Atualizado em: 2026-06-15

## Objetivo

Migrar exclusivamente `/api/eventos/<id>/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

Esta PM cobre somente:

- `GET /api/eventos/<id>/`
- `PUT /api/eventos/<id>/`

Esta PM nao cobre `GET /api/eventos/`, ja migrado na PM-12.

## Fora do escopo

- `GET /api/eventos/`.
- `/api/eventos/custos-extras/`.
- `/api/clientes/`.
- `/api/clientes/<id>/`.
- `/api/orcamentos/`.
- Endpoints financeiros.
- Frontend.
- ViewSets.
- ModelViewSets.
- Serializers DRF de regra de negocio.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = 1 par `GET`/`PUT` quando o contrato for pequeno e coeso.

Ordem geral recomendada:

- endpoints de autenticacao simples primeiro;
- cadastros e operacoes antes de endpoints financeiros;
- endpoints financeiros read-only antes de mutations financeiras;
- mutations financeiras somente depois de GETs financeiros estarem estaveis em
  DRF.

Endpoints financeiros so devem ser migrados depois de cadastros e operacoes
estarem estaveis em DRF.

## Regra-mae

DRF deve entrar apenas como casca HTTP do endpoint de detalhe de evento, sem
mudar regra de negocio, helpers, services, selectors ou contrato JSON.

Antes da migracao deve existir teste de paridade cobrindo:

- `GET`;
- `PUT`;
- autenticacao;
- permissoes por metodo;
- evento inexistente;
- CSRF real no `PUT`;
- erros atuais;
- validacoes;
- contrato JSON;
- headers relevantes;
- metodos nao permitidos.

Nenhuma alteracao de frontend e permitida nesta PM.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, CORS ou comportamento
runtime apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

Nao criar serializer DRF apenas para melhorar o schema nesta PM, salvo
necessidade tecnica demonstrada e sem impacto no contrato atual.

## Preservacoes obrigatorias

- Mesma URL: `/api/eventos/<id>/`.
- Mesmo nome de rota: `caixa:api_evento_detalhe`.
- Mesmos metodos HTTP: `GET` e `PUT`.
- Mesmo JSON.
- Mesmo status HTTP.
- Mesmas permissoes.
- Mesmo comportamento para usuario anonimo.
- Mesmo comportamento para usuario autenticado sem permissao.
- Mesmo comportamento para evento inexistente.
- Mesmo CSRF no `PUT`.
- Mesmo CORS.
- Mesmo `Content-Type`.
- Mesmo `Cache-Control`/`no-store` quando existir no contrato atual.
- Mesmos aliases de payload aceitos pelo frontend no `PUT`.
- Mesmo contrato consumido pelo frontend.

## Proibicoes

- Nao migrar `GET /api/eventos/` novamente.
- Nao migrar `/api/eventos/custos-extras/`.
- Nao migrar clientes.
- Nao migrar orcamentos.
- Nao migrar endpoints financeiros.
- Nao migrar login, logout ou auth nesta PM.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao criar serializer DRF nesta PM, salvo necessidade tecnica demonstrada.
- Nao alterar frontend.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar regra de negocio.
- Nao alterar CSRF global.
- Nao alterar CORS.
- Nao alterar autenticacao global.
- Nao alterar `settings.py`.
- Nao fazer commit, push, merge ou deploy automaticamente.

## Regra especial de permissoes

`/api/eventos/<id>/` possui permissoes diferentes por metodo:

- `GET` exige `caixa.view_evento`.
- `PUT` exige `caixa.change_evento`.

A migracao para DRF deve preservar os mesmos status e JSONs de erro atuais.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global da view, ou
permissao DRF generica como substituto direto das permissoes atuais se isso
mudar status, JSON de erro ou regra por metodo.

## Regra especial de CSRF

`PUT /api/eventos/<id>/` deve ser testado com
`Client(enforce_csrf_checks=True)`:

- sem CSRF valido: deve ser bloqueado pelo comportamento atual;
- com CSRF valido: deve seguir para permissao, validacao ou atualizacao.

Se o DRF tentar substituir o JSON atual de payload invalido por erro padrao de
parser, a migracao deve ser ajustada para preservar o contrato atual observado.

## Regra especial de implementacao

Reaproveitar os helpers atuais de `caixa/views_eventos_api.py`:

- `_is_json_request`;
- `_payload_json`;
- `_first_payload_value`;
- `_string_payload_value`;
- `_date_payload_value`;
- `_integer_payload_value`;
- `_errors_from_validation_error`;
- `_eventos_queryset`;
- `_serialize_evento`;
- `_evento_data_from_payload`;
- `_atualizar_evento_response`;
- `api_authentication_required_response`;
- `api_permission_denied_response`;
- `api_no_store_json_response`.

Reaproveitar a estrategia ja usada nos endpoints migrados:

- converter payload/status/headers de `JsonResponse` para DRF `Response`
  somente na borda do endpoint;
- usar `AllowAny` local apenas se necessario para impedir que o DRF substitua
  os JSONs atuais de `401` e `403`;
- se o `PUT` precisar de protecao de CSRF equivalente a Django puro, avaliar
  reutilizacao de `JsonBodySafeSessionAuthentication` em vez de criar uma nova
  classe.

Nao criar serializer DRF nesta PM, salvo necessidade tecnica demonstrada.

Nao transformar este endpoint em `ViewSet` ou `ModelViewSet`.

## Contratos de erro que nao podem mudar

Os seguintes JSONs devem ser preservados quando fizerem parte do contrato atual:

```json
{"detail": "Authentication credentials were not provided."}
```

```json
{"detail": "Permission denied."}
```

```json
{"detail": "Content-Type deve ser application/json."}
```

```json
{"detail": "JSON invalido."}
```

A grafia exata da mensagem de JSON invalido deve ser confirmada na PM-13.1 e
congelada nos testes antes da migracao.

```json
{"errors": "..."}
```

Para numero/contrato duplicado, preservar exatamente o erro atual observado nos
testes de paridade. A PM-13 nao deve assumir a mensagem antes do diagnostico,
porque o erro pode vir de `full_clean()` ou de `IntegrityError`.

Para evento inexistente, congelar exatamente o comportamento atual:

- status HTTP;
- `Content-Type`;
- corpo da resposta;
- headers relevantes.

Nao converter `404` para JSON se o comportamento atual nao for JSON.

## Estado atual conhecido

Arquivo atual:

- `caixa/views_eventos_api.py`

View atual:

- `api_evento_detalhe`

Rota atual:

- `path("api/eventos/<int:pk>/", api_evento_detalhe, name="api_evento_detalhe")`

Helpers atuais de resposta:

- `_serialize_evento()`
- `_atualizar_evento_response()`
- `api_authentication_required_response()`
- `api_permission_denied_response()`
- `api_no_store_json_response()`

Decorador atual:

- `@require_http_methods(["GET", "PUT"])`

Permissoes atuais:

- `GET`: `VIEW_EVENT_PERMISSION = "caixa.view_evento"`
- `PUT`: `CHANGE_EVENT_PERMISSION = "caixa.change_evento"`

Payload de `GET` esperado a confirmar no diagnostico:

- `data.event`
- `data.permissions.canView`
- `data.permissions.canUpdate`
- `data.permissions.canManageInAdmin`
- `data.meta.source`

Payload de sucesso de `PUT` esperado a confirmar no diagnostico:

- `data.event`
- `data.message`

Aliases aceitos no `PUT`:

- `clientId`, `cliente`, `cliente_id`
- `number`, `numero`, `contract`
- `eventName`, `nome_evento`
- `startDate`, `data_inicio`
- `endDate`, `data_fim`
- `local`
- `status`
- `notes`, `observacoes`

Campos esperados de `data.event`:

- `id`
- `number`
- `contract`
- `eventName`
- `clientId`
- `clientName`
- `clientTradeName`
- `clientDisplayName`
- `budgetId`
- `budgetNumber`
- `contractCode`
- `contractName`
- `startDate`
- `endDate`
- `local`
- `status`
- `statusLabel`
- `notes`
- `plannedRevenueAmount`
- `realizedRevenueAmount`
- `plannedCostAmount`
- `realizedCostAmount`
- `plannedResultAmount`
- `realizedResultAmount`
- `plannedProfitAmount`
- `realizedProfitAmount`
- `createdAt`
- `updatedAt`

## PM-13.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas:

- Mapear a view atual.
- Mapear `GET /api/eventos/<id>/`.
- Mapear `PUT /api/eventos/<id>/`.
- Mapear permissoes por metodo.
- Mapear payloads de sucesso.
- Mapear payloads de erro.
- Mapear comportamento de evento inexistente.
- Mapear headers relevantes.
- Mapear uso de CSRF no `PUT`.
- Mapear aliases de payload aceitos pelo frontend.
- Mapear dependencias do frontend, se disponiveis no workspace.
- Mapear testes existentes.
- Identificar lacunas de teste.
- Registrar arquivos envolvidos.
- Registrar `git status --short`.

Arquivos previstos para leitura:

- `caixa/views_eventos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/tests.py`
- frontend de eventos, se existir no workspace

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum codigo runtime alterado.

## PM-13.2 - Testes de paridade antes da migracao

Status: concluida.

Objetivo: congelar o comportamento atual de `/api/eventos/<id>/` antes de
migrar para DRF.

### Paridade de GET

Criar ou reforcar testes para:

- usuario anonimo recebe o status e JSON atuais;
- usuario autenticado sem `caixa.view_evento` recebe o status e JSON atuais;
- usuario com `caixa.view_evento` recebe `200`;
- evento inexistente preserva status, corpo e `Content-Type` atuais;
- `Content-Type` continua como no contrato atual;
- `Cache-Control` contem `no-store` quando o comportamento atual tiver esse
  header;
- shape top-level continua `{"data": ...}` para sucesso;
- `data.event` mantem o mesmo conjunto de campos de `_serialize_evento`;
- `data.permissions.canView` preservado;
- `data.permissions.canUpdate` preservado;
- `data.permissions.canManageInAdmin` preservado;
- `data.meta.source` preservado.

### Paridade de PUT

Criar ou reforcar testes para:

- usuario anonimo recebe o status e JSON atuais quando a requisicao chega na
  view;
- usuario autenticado sem `caixa.change_evento` recebe o status e JSON atuais;
- `PUT` sem CSRF valido e bloqueado pelo comportamento atual com
  `Client(enforce_csrf_checks=True)`;
- `PUT` com CSRF valido segue para permissao, validacao ou atualizacao;
- evento inexistente preserva status, corpo e `Content-Type` atuais;
- `Content-Type` invalido retorna status e JSON atuais;
- JSON invalido retorna status e JSON atuais;
- erro de validacao retorna status e `{"errors": ...}` atuais;
- cliente inexistente retorna status e erro atual;
- numero/contrato duplicado retorna status e erro atual;
- atualizacao com sucesso retorna status atual;
- payload de sucesso contem:
  - `data.event`;
  - `data.message`;
- `data.event` mantem o mesmo conjunto de campos de `_serialize_evento`;
- aliases de payload continuam aceitos;
- `Cache-Control` contem `no-store` quando o comportamento atual tiver esse
  header;
- `Content-Type` continua JSON para respostas JSON.

### Metodos nao permitidos

Validar que metodos fora do contrato continuam bloqueados, por exemplo:

- `POST /api/eventos/<id>/`;
- `PATCH /api/eventos/<id>/`;
- `DELETE /api/eventos/<id>/`.

Validar tambem o header `Allow`, se ele fizer parte do contrato atual
observado, especialmente `GET, PUT` ou equivalente.

Gate de saida:

- Testes de paridade passam contra a implementacao atual.
- Nenhuma migracao feita ainda.

Validacao recomendada:

```bash
python manage.py test <testes_focados_de_evento_detalhe>
```

## PM-13.3 - Migracao de `/api/eventos/<id>/` para DRF

Status: concluida.

Objetivo: migrar somente `/api/eventos/<id>/` para DRF com paridade
comprovada.

Preferencia de implementacao:

- usar `@api_view(["GET", "PUT"])`;
- usar `Response` somente se os testes provarem paridade;
- usar permissoes locais equivalentes por metodo;
- reaproveitar helpers atuais de eventos;
- reaproveitar suporte local de autenticacao/CSRF ja existente se necessario;
- manter helpers atuais de erro ou respostas equivalentes no JSON.

Regras:

- Manter URL.
- Manter nome de rota.
- Manter metodos `GET` e `PUT`.
- Manter status HTTP.
- Manter JSON.
- Manter headers relevantes.
- Manter CSRF real em `PUT`.
- Manter autenticacao por sessao Django.
- Manter CORS sem alteracao.
- Nao criar serializer DRF complexo.
- Nao migrar `GET /api/eventos/` novamente.
- Nao migrar custos extras.
- Nao alterar clientes ou orcamentos.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- `SessionAuthentication` deve preservar CSRF em mutations.
- Permissao por metodo deve continuar diferenciando `view_evento` e
  `change_evento`.
- DRF nao deve substituir os JSONs atuais de `401`, `403`, `400`, `404`, `415`
  ou `405` por respostas padrao se isso mudar contrato.
- Se houver classe local de autenticacao criada em PM anterior, avaliar
  reutilizacao direta em vez de criar uma segunda classe.
- Se o `drf-spectacular` emitir warning por classe local de autenticacao,
  preferir anotacao local segura via `extend_schema(auth=[{"cookieAuth": []}])`
  em vez de configurar algo global.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema`, sem alterar
  runtime.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_evento_detalhe>
```

Gate de saida:

- `/api/eventos/<id>/` migrado para DRF.
- `GET` e `PUT` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-13.4 - Revisao pos-migracao

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_evento_detalhe>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/eventos/{id}/`;
- nenhuma regressao;
- `GET /api/eventos/` nao foi alterado novamente;
- custos extras nao foram alterados;
- clientes e orcamentos nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint de detalhe de eventos, testes e registro do plano;
- `GET /api/eventos/<id>/` preservado;
- `PUT /api/eventos/<id>/` preservado;
- `GET /api/eventos/` nao alterado novamente;
- CSRF global nao alterado;
- CORS nao alterado;
- autenticacao global nao alterada;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- suite focada passa;
- suite geral passa;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-13.5 - Fechamento e decisao sobre proximo endpoint

Status: concluida.

Objetivo: decidir se a migracao de detalhe de eventos esta estavel antes de
abrir PM-14.

Tarefas:

- Registrar arquivos alterados.
- Registrar comandos executados.
- Registrar resultado dos testes.
- Registrar resultado do schema.
- Registrar riscos residuais.
- Confirmar que `GET /api/eventos/` nao foi remigrado.
- Confirmar que custos extras ficaram fora do escopo.
- Recomendar se PM-14 pode iniciar.

Proximo endpoint natural, somente se PM-13 estiver estavel:

- PM-14: `GET`/`POST /api/orcamentos/`.

## Criterios globais de aceite

- `GET /api/eventos/<id>/` mantem paridade.
- `PUT /api/eventos/<id>/` mantem paridade.
- Autenticacao por sessao Django preservada.
- CSRF preservado.
- CORS preservado.
- Permissoes por metodo preservadas.
- Comportamento de evento inexistente preservado.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Status HTTP preservados.
- Headers relevantes preservados.
- Aliases de payload preservados.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/eventos/{id}/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- CSRF mudar;
- CORS mudar;
- permissao por metodo mudar;
- usuario anonimo receber contrato diferente;
- usuario sem permissao receber contrato diferente;
- evento inexistente receber contrato diferente;
- payload de `GET` ou `PUT` mudar;
- aliases de payload mudarem;
- frontend precisar ser alterado;
- `GET /api/eventos/` precisar ser alterado novamente sem justificativa
  tecnica;
- custos extras precisarem ser migrados junto;
- outro endpoint precisar ser migrado;
- DRF gerar resposta padrao diferente para `401`, `403`, `400`, `404`, `415` ou
  `405`;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar services, selectors ou models.

## Registro de execucao

### Registro de execucao - PM-13.1

Fase: diagnostico read-only.

Endpoint alvo:

- `GET /api/eventos/<id>/`
- `PUT /api/eventos/<id>/`

Arquivos lidos:

- `caixa/views_eventos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/models.py`
- `caixa/tests.py`

Resultado:

- Contrato atual mapeado.
- View ainda estava Django puro.
- Lacunas de paridade identificadas para `GET` e `PUT`.
- Nenhum arquivo alterado nesta fase.

### Registro de execucao - PM-13.2

Fase: testes de paridade do `GET /api/eventos/<id>/`.

Arquivos alterados:

- `caixa/tests.py`

Testes criados:

- `test_api_evento_detalhe_get_preserva_auth_permissao_shape_headers_e_404`
- `test_api_evento_detalhe_get_can_update_reflete_change_evento`

Comandos executados:

```bash
python manage.py test caixa.tests.EventosApiTests.test_api_evento_detalhe_get_preserva_auth_permissao_shape_headers_e_404 caixa.tests.EventosApiTests.test_api_evento_detalhe_get_can_update_reflete_change_evento caixa.tests.EventosApiTests.test_api_evento_detalhe_edita_quando_usuario_tem_permissao caixa.tests.EventosApiTests.test_api_evento_detalhe_bloqueia_edicao_sem_permissao
python manage.py check
git diff -- caixa/tests.py
git status --short
```

Resultado:

- 4 testes focados executados e aprovados.
- `python manage.py check` passou sem issues.
- Nenhuma alteracao de producao.

### Registro de execucao - PM-13.3

Fase: migracao de `/api/eventos/<id>/` para DRF.

Arquivos alterados:

- `caixa/views_eventos_api.py`
- `caixa/tests.py`

Mudanca aplicada:

- `api_evento_detalhe` passou a usar `@api_view(["GET", "PUT"])`.
- Foi usada `Response` somente na borda do endpoint.
- Foi usada permissao local `AllowAny` com validacao manual de:
  - `caixa.view_evento` para `GET`;
  - `caixa.change_evento` para `PUT`.
- Foi reaproveitada `JsonBodySafeSessionAuthentication` para preservar CSRF em
  `PUT`.
- O comportamento de 404 Django padrao foi preservado via `page_not_found`.
- Helpers atuais de eventos foram reaproveitados.
- Nenhum serializer DRF, ViewSet ou ModelViewSet foi criado.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.EventosApiTests.test_api_evento_detalhe_get_preserva_auth_permissao_shape_headers_e_404 caixa.tests.EventosApiTests.test_api_evento_detalhe_get_can_update_reflete_change_evento caixa.tests.EventosApiTests.test_api_evento_detalhe_edita_quando_usuario_tem_permissao caixa.tests.EventosApiTests.test_api_evento_detalhe_bloqueia_edicao_sem_permissao
python manage.py test caixa.tests.EventosApiTests
git diff --stat
git status --short
```

Resultado:

- `python manage.py check` passou sem issues.
- `python manage.py spectacular --validate` passou sem warnings observados.
- 4 testes focados passaram.
- `EventosApiTests` passou com 11 testes.
- OpenAPI passou a incluir `/api/eventos/{id}/`.

### Registro de execucao - PM-13.4

Fase: revisao pos-migracao.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.EventosApiTests
python manage.py test
git diff --stat
git status --short
```

Resultado:

- `python manage.py check` passou sem issues.
- `python manage.py spectacular --validate` passou sem warnings observados.
- `EventosApiTests` passou com 11 testes.
- Suite completa passou com 688 testes.
- Nenhum `schema.yml` residual foi gerado.
- `GET /api/eventos/` nao foi remigrado.
- Custos extras, clientes, orcamentos, settings, CORS, CSRF global, auth global e
  frontend nao foram alterados.

Warnings observados:

- Warnings esperados de CSRF em testes negativos:
  - `/api/eventos/custos-extras/`;
  - `/api/auth/logout/`.
- Aviso local de line ending em `caixa/views_eventos_api.py`:
  `CRLF will be replaced by LF`.

Riscos residuais:

- O schema OpenAPI segue generico (`object`) porque a PM nao criou serializer
  DRF, por prioridade de paridade runtime.
- O `PUT` ainda tem cobertura menor que clientes detalhe para erros finos de
  payload; recomenda-se reforcar esses casos antes de ampliar migrations de
  eventos ou orcamentos.

Decisao:

- PM-13 concluida e estavel.
- Proximo endpoint recomendado: PM-14, `GET`/`POST /api/orcamentos/`, iniciando
  por diagnostico read-only.

## Proxima acao recomendada

Executar PM-14.1 como diagnostico read-only de `GET`/`POST /api/orcamentos/`,
sem migracao e sem alteracao de codigo runtime.
