# Plano PM-12 - Migracao incremental de `GET /api/eventos/` para DRF

Atualizado em: 2026-06-15

## Objetivo

Migrar exclusivamente `GET /api/eventos/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

Esta PM cobre somente:

- `GET /api/eventos/`

## Fora do escopo

- `/api/eventos/<id>/`.
- `POST`/`PUT` de eventos.
- Custos extras.
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
- 1 PM = 1 par de metodos quando o contrato for pequeno e coeso.

Ordem geral recomendada:

- endpoints de autenticacao simples primeiro;
- cadastros e operacoes antes de endpoints financeiros;
- endpoints financeiros read-only antes de mutations financeiras;
- mutations financeiras somente depois de GETs financeiros estarem estaveis em
  DRF.

Endpoints financeiros so devem ser migrados depois de cadastros e operacoes
estarem estaveis em DRF.

## Regra-mae

DRF deve entrar apenas como casca HTTP do endpoint de lista de eventos, sem
mudar regra de negocio, helpers, services, selectors ou contrato JSON.

Antes da migracao deve existir teste de paridade cobrindo:

- `GET`;
- autenticacao;
- permissao;
- filtros e aliases;
- payload de sucesso;
- payloads de erro;
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

- Mesma URL: `/api/eventos/`.
- Mesmo nome de rota: `caixa:api_eventos`.
- Mesmo metodo HTTP: `GET`.
- Mesmo JSON.
- Mesmo status HTTP.
- Mesma permissao.
- Mesmo comportamento para usuario anonimo.
- Mesmo comportamento para usuario autenticado sem permissao.
- Mesmo CORS.
- Mesmo CSRF global.
- Mesmo `Content-Type`.
- Mesmo `Cache-Control`/`no-store`.
- Mesmos filtros e aliases aceitos pelo frontend.
- Mesmo contrato consumido pelo frontend.

## Proibicoes

- Nao migrar `/api/eventos/<id>/`.
- Nao migrar `PUT /api/eventos/<id>/`.
- Nao migrar custos extras.
- Nao migrar clientes novamente.
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

## Regra especial de permissao

`GET /api/eventos/` exige:

- `caixa.view_evento`

A migracao para DRF deve preservar os mesmos status e JSONs de erro atuais.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global da view, ou permissao
DRF generica como substituto direto se isso mudar status, JSON de erro ou
contrato atual.

## Regra especial de CSRF

`GET /api/eventos/` nao deve depender de token CSRF para leitura.

A PM nao deve alterar `CsrfViewMiddleware`, cookies CSRF, headers CORS ou
autenticacao por sessao.

Se testes de CORS/CSRF existirem em torno do frontend, eles devem continuar
passando sem alteracao.

## Regra especial de implementacao

Reaproveitar os helpers atuais de `caixa/views_eventos_api.py`:

- `_money`;
- `_date_or_empty`;
- `_datetime_or_empty`;
- `_choice_options`;
- `_serialize_cliente_option`;
- `_eventos_queryset`;
- `_serialize_evento`;
- `_summary_payload`;
- `_eventos_response`;
- `api_no_store_json_response`;
- `require_api_permission`, ou resposta equivalente preservando contrato.

Reaproveitar selectors atuais:

- `filtrar_eventos`;
- `resolver_periodo_eventos_lista`;
- `status_eventos_para_filtro`;
- `totais_eventos`;
- `listar_clientes_filtro`.

Nao criar serializer DRF nesta PM, salvo necessidade tecnica demonstrada.

Nao transformar este endpoint em `ViewSet` ou `ModelViewSet`.

## Contratos de erro que nao podem mudar

Os seguintes JSONs devem ser preservados:

```json
{"detail": "Authentication credentials were not provided."}
```

```json
{"detail": "Permission denied."}
```

Metodo diferente de `GET` deve preservar o comportamento atual de metodo nao
permitido, incluindo status e headers relevantes.

## Estado atual conhecido

Arquivo atual:

- `caixa/views_eventos_api.py`

View atual:

- `api_eventos`

Rota atual:

- `path("api/eventos/", api_eventos, name="api_eventos")`

Permissao atual:

- `VIEW_EVENT_PERMISSION = "caixa.view_evento"`

Decoradores atuais:

- `@require_GET`
- `@require_api_permission(VIEW_EVENT_PERMISSION)`

Payload de sucesso esperado:

- `data.events`
- `data.summary`
- `data.filters`
- `data.filterOptions`
- `data.permissions`
- `data.meta`

Campos de `data.events[]` esperados:

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

Filtros e aliases aceitos:

- `search` / `busca`
- `status`
- `clientId` / `cliente` / `cliente_id`
- `quickPeriod` / `periodo_rapido`
- `startDate` / `data_inicial`
- `endDate` / `data_final`

Opcoes de filtro esperadas:

- `filterOptions.statuses`
- `filterOptions.clients`
- `filterOptions.quickPeriods`

## PM-12.1 - Diagnostico read-only

Status: planejada.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas:

- Mapear a view atual.
- Mapear `GET /api/eventos/`.
- Mapear permissao atual.
- Mapear payload de sucesso.
- Mapear payloads de erro.
- Mapear filtros e aliases.
- Mapear headers relevantes.
- Mapar comportamento de metodos nao permitidos.
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
- selectors de cadastros/opcoes usados pela view
- frontend de eventos, se existir no workspace

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum codigo runtime alterado.

## PM-12.2 - Testes de paridade antes da migracao

Status: planejada.

Objetivo: congelar o comportamento atual de `GET /api/eventos/` antes de migrar
para DRF.

Criar ou reforcar testes para:

- usuario anonimo recebe `401` JSON atual;
- usuario autenticado sem `caixa.view_evento` recebe `403` JSON atual;
- usuario com `caixa.view_evento` recebe `200`;
- `Content-Type` continua JSON;
- `Cache-Control` contem `no-store`;
- shape top-level continua `{"data": ...}`;
- `data.events` mantem o mesmo conjunto de campos;
- `data.summary` mantem o mesmo conjunto de campos;
- `data.filters` preserva filtros canonicos e aliases;
- `data.filterOptions.statuses` preservado;
- `data.filterOptions.clients` preservado;
- `data.filterOptions.quickPeriods` preservado;
- `data.permissions.canView` preservado;
- `data.permissions.canUpdate` preservado;
- `data.permissions.canManageInAdmin` preservado;
- `data.meta.source` preservado;
- busca por `search`/`busca` preservada;
- filtro por `status` preservado;
- filtro por `clientId`/`cliente`/`cliente_id` preservado;
- filtro por `quickPeriod`/`periodo_rapido` preservado;
- filtro por `startDate`/`data_inicial` e `endDate`/`data_final` preservado;
- periodo personalizado sem datas continua publicando `todos`, se esse for o
  contrato atual;
- metodos nao permitidos continuam com status e headers atuais, por exemplo:
  - `POST /api/eventos/`;
  - `PUT /api/eventos/`;
  - `PATCH /api/eventos/`;
  - `DELETE /api/eventos/`.

Gate de saida:

- Testes de paridade passam contra a implementacao atual.
- Nenhuma migracao feita ainda.

Validacao recomendada:

```bash
python manage.py test <testes_focados_de_eventos_lista>
```

## PM-12.3 - Migracao de `GET /api/eventos/` para DRF

Status: planejada.

Objetivo: migrar somente `GET /api/eventos/` para DRF com paridade comprovada.

Preferencia de implementacao:

- usar `@api_view(["GET"])`;
- usar `Response` somente se os testes provarem paridade;
- usar permissao local equivalente ou checagem manual equivalente;
- reaproveitar helpers atuais de eventos;
- manter helpers atuais de erro ou respostas equivalentes no JSON.

Regras:

- Manter URL.
- Manter nome de rota.
- Manter metodo `GET`.
- Manter status HTTP.
- Manter JSON.
- Manter headers relevantes.
- Manter autenticacao por sessao Django.
- Manter CORS sem alteracao.
- Manter CSRF global sem alteracao.
- Nao criar serializer DRF complexo.
- Nao migrar `/api/eventos/<id>/`.
- Nao alterar `/api/clientes/` ou `/api/clientes/<id>/`.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- Permissao deve continuar exigindo `caixa.view_evento`.
- DRF nao deve substituir os JSONs atuais de `401`, `403` ou `405` por
  respostas padrao se isso mudar contrato.
- Se o `drf-spectacular` emitir warning, preferir anotacao local segura via
  `extend_schema` em vez de configurar algo global.
- Melhorar OpenAPI apenas quando isso nao alterar runtime.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_eventos_lista>
```

Gate de saida:

- `GET /api/eventos/` migrado para DRF.
- Paridade mantida.
- Nenhum outro endpoint alterado.

## PM-12.4 - Revisao pos-migracao

Status: planejada.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_eventos_lista>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/eventos/`;
- nenhuma regressao;
- `/api/eventos/<id>/` nao migrado;
- custos extras nao alterados;
- clientes e orcamentos nao alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint de lista de eventos, testes e registro do plano;
- `GET /api/eventos/` preservado;
- `/api/eventos/<id>/` nao alterado;
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

## PM-12.5 - Fechamento e decisao sobre proximo endpoint

Status: planejada.

Objetivo: decidir se a migracao de eventos lista esta estavel antes de abrir
PM-13.

Tarefas:

- Registrar arquivos alterados.
- Registrar comandos executados.
- Registrar resultado dos testes.
- Registrar resultado do schema.
- Registrar riscos residuais.
- Confirmar que `/api/eventos/<id>/` ficou fora do escopo.
- Recomendar se PM-13 pode iniciar.

Proximo endpoint natural, somente se PM-12 estiver estavel:

- PM-13: `GET`/`PUT /api/eventos/<id>/`.

## Criterios globais de aceite

- `GET /api/eventos/` mantem paridade.
- Autenticacao por sessao Django preservada.
- Permissao `caixa.view_evento` preservada.
- CSRF global preservado.
- CORS preservado.
- JSON de sucesso preservado.
- JSONs de erro preservados.
- Status HTTP preservados.
- Headers relevantes preservados.
- Filtros e aliases preservados.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/eventos/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- headers relevantes mudarem;
- CSRF global mudar;
- CORS mudar;
- permissao mudar;
- usuario anonimo receber contrato diferente;
- usuario sem permissao receber contrato diferente;
- filtros ou aliases mudarem;
- frontend precisar ser alterado;
- `/api/eventos/<id>/` precisar ser migrado junto;
- outro endpoint precisar ser migrado;
- DRF gerar resposta padrao diferente para `401`, `403` ou `405`;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar services, selectors ou models.

## Registro de execucao

Cada fase executada deve registrar:

- data;
- fase;
- endpoint alvo;
- arquivos lidos;
- arquivos alterados;
- testes criados ou alterados;
- comandos executados;
- resultado dos testes;
- resultado do `spectacular`;
- diferencas encontradas na paridade;
- riscos residuais;
- `git status --short`;
- decisao de avancar, ajustar ou parar.

## Proxima acao recomendada

Executar PM-12.1 como diagnostico read-only de `GET /api/eventos/`, sem
migracao e sem alteracao de codigo runtime.
