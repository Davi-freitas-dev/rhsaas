# Plano PM-20 - Migracao incremental de `GET/POST /api/custos-fixos/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET/POST /api/custos-fixos/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP da listagem e criacao de custos fixos,
sem alterar regra de negocio, selectors, helpers, serializers manuais,
permissoes, CSRF, CORS, headers, status HTTP, JSON ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET/POST /api/custos-fixos/` em testes antes
  da migracao.
- Migrar somente a view `api_custos_fixos`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissoes manuais por metodo:
  - `GET`: `caixa.view_custofixo`;
  - `POST`: `caixa.add_custofixo`.
- Preservar CSRF real no `POST`.
- Preservar Content-Type, JSON invalido, status HTTP, headers e shape atual.
- Reaproveitar helpers, selectors e serializers manuais atuais.
- Preservar criacao com recorrencia.
- Preservar signals e sincronizacoes acionadas pelo `CustoFixo.save()`.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET /api/custos-fixos/<id>/`.
- `PUT /api/custos-fixos/<id>/`.
- Qualquer endpoint de detalhe de custo fixo.
- Endpoints de eventos.
- Endpoints de clientes.
- Endpoints de orcamentos.
- Endpoints financeiros canonicos.
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
- Alteracao de services.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de metodos quando o contrato for pequeno.

Nesta PM, somente `GET/POST /api/custos-fixos/` deve ser migrado. O endpoint
`GET/PUT /api/custos-fixos/<id>/` deve ficar para PM futura, porque possui
contrato proprio de detalhe/atualizacao.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
cadastros e operacoes estaveis primeiro; GETs financeiros antes de mutations
financeiras.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, CSRF, CORS, efeitos de
dominio ou comportamento runtime apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-20.1

Arquivo atual:

- `caixa/views_custos_fixos_api.py`

View atual:

- `api_custos_fixos`

Rota atual:

- `path("api/custos-fixos/", api_custos_fixos, name="api_custos_fixos")`

Nome da rota:

- `caixa:api_custos_fixos`

Decorador atual:

- `@require_http_methods(["GET", "POST"])`

Metodos aceitos:

- `GET`
- `POST`

Metodos nao permitidos:

- `PUT`, `PATCH` e `DELETE` retornam `405`.
- Header `Allow` esperado: `GET, POST`.
- Resposta de `405` e HTML vazia do Django devem ser preservadas.

Permissoes atuais:

- `GET` exige `caixa.view_custofixo`.
- `POST` exige `caixa.add_custofixo`.
- As permissoes sao verificadas manualmente dentro da view.
- Nao usar `DjangoModelPermissions`, `IsAuthenticated` global ou permissao DRF
  generica se isso mudar contrato.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem permissao:

```json
{"detail": "Permission denied."}
```

com status `403`.

CSRF atual:

- `POST` nao usa `csrf_exempt`.
- Com `Client(enforce_csrf_checks=True)`, ausencia de CSRF valido deve ser
  bloqueada antes da view pelo comportamento Django atual.
- Com CSRF valido, a requisicao chega na view e segue para autenticacao,
  permissao, validacao ou criacao.

Content-Type aceito no `POST`:

- `application/json`.

Content-Type invalido no `POST`:

```json
{"detail": "Content-Type deve ser application/json."}
```

com status `415`.

JSON invalido ou body nao-dict no `POST`:

```json
{"detail": "JSON invalido."}
```

com status `400`.

Payload de sucesso do `GET`:

```json
{
  "data": {
    "fixedCosts": [],
    "groups": [],
    "summary": {},
    "filters": {},
    "filterOptions": {},
    "permissions": {
      "canCreate": true,
      "canUpdate": true
    },
    "meta": {
      "source": "backend"
    }
  }
}
```

Shape de cada item em `data.fixedCosts`:

- `id`
- `description`
- `category`
- `categoryLabel`
- `plannedAmount`
- `paidAmount`
- `pendingPaymentAmount`
- `dueDate`
- `paymentDate`
- `status`
- `statusLabel`
- `manuallySettled`
- `settlementReason`
- `notes`
- `isActive`
- `isRecurring`
- `monthsCount`
- `parentId`
- `generatedAutomatically`
- `recordType`
- `recordTypeLabel`
- `isOverdue`
- `createdAt`
- `updatedAt`

Shape de cada item em `data.groups`:

- `category`
- `categoryLabel`
- `items`
- `plannedAmount`
- `paidAmount`
- `pendingPaymentAmount`
- `total`
- `overdueCount`

Shape de `data.summary`:

- `plannedAmount`
- `paidAmount`
- `pendingPaymentAmount`
- `total`
- `manualCount`
- `automaticCount`
- `overdueCount`

Shape de `data.filterOptions`:

- `categories`
- `statuses`
- `recurring`
- `recordTypes`
- `activeStatuses`
- `quickPeriods`

Filtros e aliases aceitos no `GET`:

- `search` e `busca`;
- `active` e `ativo`;
- `startDate` e `data_inicial`;
- `endDate` e `data_final`;
- `category` e `categoria`;
- `recurring` e `recorrente`;
- `recordType` e `tipo_registro`;
- `quickPeriod` e `periodo_rapido`;
- `status`.

Regra de periodo no `GET`:

- Quando ha filtro personalizado sem periodo explicito, `periodo_rapido` passa
  para `todos`, preservando a busca historica sem limitar ao mes atual.

Ordenacao atual:

- Reaproveita `listar_custos_fixos_ordenados`.
- Ordena por `categoria`, `data_vencimento`, `descricao` e `id`.

Payload de sucesso do `POST`:

Status `201`:

```json
{
  "data": {
    "fixedCost": {},
    "message": "Custo fixo cadastrado com sucesso."
  }
}
```

Aliases aceitos no payload `POST`:

- `description` e `descricao`;
- `category` e `categoria`;
- `plannedAmount` e `valor_previsto`;
- `paidAmount` e `valor_pago`;
- `dueDate` e `data_vencimento`;
- `paymentDate` e `data_pagamento`;
- `manuallySettled` e `baixado_manualmente`;
- `settlementReason` e `motivo_baixa`;
- `notes` e `observacao`;
- `isActive` e `ativo`;
- `isRecurring` e `recorrente`;
- `monthsCount` e `quantidade_meses`;
- `status`.

Erros de validacao:

```json
{"errors": ...}
```

com status `400`.

Principais validacoes atuais:

- `valor_previsto` deve ser numerico e nao negativo.
- `valor_pago` deve ser numerico e nao negativo.
- `valor_pago` nao pode ser maior que `valor_previsto`.
- `data_vencimento` e obrigatoria e deve ser valida.
- `data_pagamento`, quando informada, deve ser valida.
- `quantidade_meses` deve ser no minimo `1`.
- baixa manual exige `motivo_baixa`.
- `categoria` respeita choices do model.
- `status` respeita choices do model.
- aumento de `valor_pago` pode ser bloqueado por validacao de caixa
  disponivel.

Erro de integridade na criacao:

```json
{"errors": {"detail": ["Nao foi possivel cadastrar o custo fixo."]}}
```

com status `400`.

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- `405` preserva `Allow: GET, POST`.

Efeitos de dominio do `POST`:

- Cria `CustoFixo`.
- Define `criado_por` e `atualizado_por` com `request.user`.
- Executa `full_clean()`.
- Executa `save()`, que recalcula status automaticamente.
- Executa `gerar_recorrencias()` quando aplicavel.
- `post_save` sincroniza:
  - lancamento financeiro de custo fixo;
  - obrigacao financeira canonica;
  - baixa canonica por origem `custo_fixo`.

## Riscos especificos de custos fixos

- DRF pode substituir `401` e `403` atuais por respostas padrao.
- DRF pode alterar `405` e o header `Allow: GET, POST`.
- DRF pode parsear `request.data` antes da view e mudar o erro atual de JSON
  invalido.
- DRF pode acionar erro de media type diferente do `415` atual.
- `POST` e mutation financeira com efeitos colaterais.
- Criacao recorrente pode criar registros filhos; qualquer mudanca no fluxo
  pode duplicar ou deixar de criar recorrencias.
- `save()` recalcula status automaticamente.
- Signals sincronizam lancamento financeiro, obrigacao financeira canonica e
  baixa canonica.
- Validacao de caixa disponivel pode bloquear alteracoes de `valor_pago`.
- Campos e aliases legados podem ser perdidos se houver serializer novo.
- `Cache-Control`/`no-store` pode ser perdido se a resposta mudar.
- OpenAPI pode ficar generico sem serializer DRF, mas isso nao deve motivar
  alteracao runtime.

## Guardrails

- Nao alterar `GET/PUT /api/custos-fixos/<id>/`.
- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao criar serializer DRF.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao mover regra de negocio para serializer DRF.
- Nao mover calculo financeiro para frontend.
- Nao alterar selectors.
- Nao alterar services.
- Nao alterar signals.
- Nao alterar model.
- Nao alterar helpers existentes salvo necessidade tecnica demonstrada e
  registrada.
- Reaproveitar `_custos_fixos_response`.
- Reaproveitar `_criar_custo_fixo_response`.
- Reaproveitar `_serialize_custo_fixo`.
- Reaproveitar `_serialize_group`.
- Reaproveitar `_custo_fixo_data_from_payload`.
- Reaproveitar `_payload_json`.
- Reaproveitar `_is_json_request`.
- Reaproveitar selectors atuais de custos fixos.
- Preservar permissoes manuais por metodo.
- Priorizar paridade runtime sobre schema OpenAPI.

## PM-20.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas realizadas:

- View atual identificada.
- URL e nome de rota identificados.
- Metodos aceitos identificados.
- Comportamento de metodos nao permitidos identificado.
- Permissoes por metodo identificadas.
- Comportamento de anonimo identificado.
- Comportamento de autenticado sem permissao identificado.
- CSRF atual identificado.
- Content-Type aceito identificado.
- JSON invalido identificado.
- Shape de sucesso e erro identificado.
- Status HTTP atuais identificados.
- Headers relevantes identificados.
- Campos retornados e aliases identificados.
- Dependencias de dominio identificadas.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum arquivo alterado.

## PM-20.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

Criar ou reforcar testes para `GET`:

- anonimo retorna `401` com JSON atual;
- autenticado sem `caixa.view_custofixo` retorna `403` com JSON atual;
- autenticado com `caixa.view_custofixo` retorna `200`;
- shape completo de `data.fixedCosts`;
- shape completo de `data.groups`;
- shape completo de `data.summary`;
- shape completo de `data.filters`;
- shape completo de `data.filterOptions`;
- shape completo de `data.permissions`;
- `data.meta.source == "backend"`;
- aliases de filtros preservados:
  - `search` e `busca`;
  - `active` e `ativo`;
  - `startDate` e `data_inicial`;
  - `endDate` e `data_final`;
  - `category` e `categoria`;
  - `recurring` e `recorrente`;
  - `recordType` e `tipo_registro`;
  - `quickPeriod` e `periodo_rapido`;
  - `status`;
- filtro personalizado sem periodo explicito preserva `periodo_rapido=todos`;
- resposta com lista vazia;
- ordenacao atual por `categoria`, `data_vencimento`, `descricao` e `id`;
- headers JSON/no-store.

Criar ou reforcar testes para `POST`:

- sem CSRF valido usando `Client(enforce_csrf_checks=True)` bloqueia antes da
  view;
- com CSRF valido chega na view;
- anonimo retorna `401` quando chega na view;
- autenticado sem `caixa.add_custofixo` retorna `403`;
- Content-Type invalido retorna `415`;
- JSON invalido retorna `400`;
- body JSON nao-dict retorna `400`;
- validacoes criticas retornam `{"errors": ...}`;
- valor previsto negativo;
- valor pago negativo;
- valor pago maior que valor previsto;
- data de vencimento ausente/invalida;
- quantidade de meses menor que `1`;
- baixa manual sem motivo;
- categoria invalida;
- status invalido;
- erro de integridade preserva payload atual, se houver caminho pratico e
  estavel para provocar;
- sucesso retorna `201` com `data.fixedCost` e `data.message`;
- aliases de payload canonicos e legados preservados;
- criacao com recorrencia preserva comportamento atual;
- signals/sincronizacoes principais preservados:
  - lancamento financeiro quando ha `valor_pago`;
  - obrigacao financeira canonica;
  - baixa canonica quando aplicavel;
- headers JSON/no-store.

Criar ou reforcar testes para metodos nao permitidos:

- `PUT`, `PATCH` e `DELETE` retornam `405`;
- header `Allow: GET, POST` preservado;
- contrato de `405` Django padrao preservado.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_custos_fixos_lista_criacao>
```

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.
- Nenhuma alteracao em `GET/PUT /api/custos-fixos/<id>/`.

## PM-20.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_custos_fixos` para DRF com paridade comprovada.

Implementacao esperada:

- converter somente `api_custos_fixos`;
- usar `@api_view(["GET", "POST"])`;
- usar `Response` somente na borda;
- preservar `@require_http_methods(["GET", "POST"])` ou alternativa local
  equivalente se necessario para manter `405` e `Allow: GET, POST`;
- preservar permissao manual por metodo;
- preservar `401` e `403` atuais;
- preservar `415`;
- preservar `400` de JSON invalido;
- preservar `{"errors": ...}` de validacao;
- preservar `201` de criacao;
- preservar `405` e `Allow: GET, POST`;
- preservar `Cache-Control`/`no-store`;
- reaproveitar `_custos_fixos_response`;
- reaproveitar `_criar_custo_fixo_response`;
- reaproveitar helpers, selectors e serializers manuais atuais;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao mexer no endpoint de detalhe.

Regras:

- Manter URL `/api/custos-fixos/`.
- Manter nome de rota `caixa:api_custos_fixos`.
- Manter metodos `GET` e `POST`.
- Manter status HTTP.
- Manter JSON de sucesso.
- Manter JSONs de erro.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow: GET, POST`.
- Manter CSRF real no `POST`.
- Manter permissoes atuais por metodo.
- Manter CORS sem alteracao.
- Nao deixar DRF substituir erros atuais por erros padrao.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_custos_fixos_lista_criacao>
```

Gate de saida:

- `/api/custos-fixos/` migrado para DRF.
- `GET` mantem paridade.
- `POST` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-20.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_custos_fixos_lista_criacao>
python manage.py test <testes_relacionados_de_custos_fixos>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/custos-fixos/`;
- nenhuma regressao;
- `GET/PUT /api/custos-fixos/<id>/` nao foi alterado;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado a `/api/custos-fixos/`, testes e registro do plano;
- endpoint de detalhe nao alterado;
- helpers atuais reaproveitados;
- selectors atuais reaproveitados;
- serializer manual atual reaproveitado;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- testes focados passam;
- testes relacionados de custos fixos passam;
- suite geral passa;
- warnings do spectacular registrados;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-20.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-20 antes de avancar para outro
endpoint.

Tarefas:

- Atualizar este documento.
- Registrar arquivos alterados.
- Registrar testes criados.
- Registrar comandos executados.
- Registrar resultado dos testes focados.
- Registrar resultado dos testes relacionados de custos fixos.
- Registrar resultado da suite completa.
- Registrar resultado do `spectacular --validate`.
- Registrar warnings encontrados.
- Registrar diferencas encontradas, se houver.
- Registrar decisao sobre `schema.yml`, se tiver sido gerado.
- Confirmar que `GET/PUT /api/custos-fixos/<id>/` nao foi alterado.
- Confirmar que nenhum outro endpoint foi migrado.
- Confirmar que frontend nao foi alterado.
- Confirmar que settings, CORS, CSRF global e auth global nao foram alterados.
- Registrar riscos residuais.
- Registrar recomendacao: pronto, ajustar ou reverter.

Proximo passo natural, somente se PM-20 estiver estavel:

- criar PM futura para `GET/PUT /api/custos-fixos/<id>/`, com diagnostico
  read-only proprio antes de qualquer migracao.

## Criterios globais de aceite

- `GET /api/custos-fixos/` mantem paridade.
- `POST /api/custos-fixos/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodos `GET` e `POST` preservados.
- Status HTTP preservados.
- JSON de sucesso preservado.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow: GET, POST` preservado nos `405`.
- Permissoes por metodo preservadas.
- CSRF real preservado no `POST`.
- Content-Type atual preservado.
- JSON invalido atual preservado.
- Campos e aliases legados preservados.
- Filtros e aliases preservados.
- Criacao com recorrencia preservada.
- Signals/sincronizacoes principais preservados.
- Frontend nao alterado.
- `GET/PUT /api/custos-fixos/<id>/` nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/custos-fixos/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- header relevante mudar;
- permissao mudar;
- CSRF mudar;
- CORS precisar mudar;
- frontend precisar mudar;
- usuario anonimo receber contrato diferente;
- usuario autenticado sem permissao receber contrato diferente;
- `Allow: GET, POST` mudar;
- Content-Type invalido deixar de retornar `415` atual;
- JSON invalido deixar de retornar `400` atual;
- erros de validacao deixarem de retornar `{"errors": ...}`;
- criacao recorrente mudar comportamento;
- signals/sincronizacoes deixarem de ocorrer;
- lancamento financeiro for criado/removido indevidamente;
- obrigacao financeira canonica for criada/removida indevidamente;
- aliases legados forem removidos;
- outro endpoint precisar ser alterado;
- `GET/PUT /api/custos-fixos/<id>/` precisar ser alterado;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar settings, CORS, CSRF global ou auth global.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_custos_fixos`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_custos_fixos`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

Se recorrencia, signals ou sincronizacoes divergirem:

- Parar a PM.
- Reverter a migracao runtime.
- Manter testes que detectaram a divergencia.
- Registrar exatamente qual efeito divergiu.

## Registro de execucao

### Registro de execucao - PM-20.1

Fase: diagnostico read-only.

Endpoint alvo:

- `GET/POST /api/custos-fixos/`

Arquivos lidos:

- `caixa/views_custos_fixos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/models_custo_fixo.py`
- `caixa/selectors_custos_fixos.py`
- `caixa/signals.py`
- `caixa/services_lancamentos.py`
- `caixa/services_modelagem_canonica.py`
- `caixa/tests.py`

Resultado:

- Contrato atual de `/api/custos-fixos/` mapeado.
- View ainda estava Django puro.
- Permissoes por metodo identificadas.
- CSRF real no `POST` identificado.
- Content-Type e JSON invalido identificados.
- Shape de sucesso e erro identificado.
- Filtros e aliases identificados.
- Dependencias de dominio identificadas.
- Lacunas de paridade identificadas.
- Nenhum arquivo alterado nesta fase.

### Registro de execucao - PM-20.2

Status: concluida.

Fase: congelamento de contrato em testes.

Arquivo alterado:

- `caixa/tests.py`

Testes criados/reforcados:

- `FiltrosHtmlTests.test_api_custos_fixos_lista_exige_autenticacao_e_permissao`
  - congela `401` anonimo;
  - congela `403` sem `view_custofixo`;
  - congela `200` com `view_custofixo`;
  - congela headers JSON/no-store.
- `FiltrosHtmlTests.test_api_custos_fixos_lista_preserva_shape_aliases_e_ordenacao`
  - congela shape de `data.fixedCosts`;
  - congela shape de `data.groups`;
  - congela shape de `data.summary`;
  - congela shape de `data.filters`;
  - congela shape de `data.filterOptions`;
  - congela `data.permissions`;
  - congela `data.meta.source`;
  - congela aliases de filtros;
  - congela ordenacao por `categoria`, `data_vencimento`, `descricao` e `id`.
- `FiltrosHtmlTests.test_api_custos_fixos_lista_vazia_preserva_shape`
  - congela lista vazia;
  - congela `periodo_rapido`/`quickPeriod=todos`.
- `FiltrosHtmlTests.test_api_custos_fixos_criacao_csrf_autenticacao_e_permissao`
  - congela CSRF real bloqueando `POST` sem token;
  - congela `401` anonimo quando a requisicao chega na view;
  - congela `403` sem `add_custofixo`.
- `FiltrosHtmlTests.test_api_custos_fixos_criacao_erros_de_payload_preservam_contrato`
  - congela Content-Type invalido `415`;
  - congela JSON invalido `400`;
  - congela body nao-dict `400`;
  - congela erros de validacao em `{"errors": ...}`.
- `FiltrosHtmlTests.test_api_custos_fixos_criacao_sucesso_preserva_shape_recorrencia_e_sincronizacoes`
  - congela sucesso `201`;
  - congela `data.fixedCost` e `data.message`;
  - congela criacao recorrente;
  - congela sincronizacao de lancamento financeiro;
  - congela sincronizacao de obrigacao financeira canonica;
  - congela baixa canonica aplicavel.
- `FiltrosHtmlTests.test_api_custos_fixos_metodos_nao_permitidos_preservam_405`
  - congela `PUT`, `PATCH` e `DELETE` como `405`;
  - congela `Allow: GET, POST`.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_preserva_shape_aliases_e_ordenacao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_csrf_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_sucesso_preserva_shape_recorrencia_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_aceita_filtros_canonicos_e_preserva_aliases caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_busca_sem_periodo_nao_limita_mes_atual
venv\Scripts\python.exe manage.py check
```

Resultados:

- Testes focados: 9 testes executados, todos OK.
- `check`: OK, sem issues.
- Nenhuma view foi migrada nesta fase.
- Nenhuma alteracao em `GET/PUT /api/custos-fixos/<id>/`.

### Registro de execucao - PM-20.3

Status: concluida.

Fase: migracao controlada para DRF.

Arquivo alterado:

- `caixa/views_custos_fixos_api.py`

Implementacao:

- `api_custos_fixos` foi migrada para DRF com `@api_view(["GET", "POST"])`.
- `Response` passou a ser usado somente na borda deste endpoint.
- `@require_http_methods(["GET", "POST"])` foi preservado para manter `405` e
  `Allow: GET, POST`.
- `JsonBodySafeSessionAuthentication` foi reaproveitado para preservar CSRF
  real e evitar que DRF substitua o contrato de JSON invalido.
- `AllowAny` foi usado localmente para impedir que a permissao global do DRF
  substitua `401`/`403` atuais.
- Permissoes manuais por metodo foram preservadas:
  - `GET`: `caixa.view_custofixo`;
  - `POST`: `caixa.add_custofixo`.
- `_custos_fixos_response` foi reaproveitado.
- `_criar_custo_fixo_response` foi reaproveitado.
- Helpers, selectors e serializers manuais atuais foram reaproveitados.

Nao alterado:

- `GET/PUT /api/custos-fixos/<id>/`.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Selectors.
- Services.
- Signals.
- Model.
- Serializer DRF, ViewSet ou ModelViewSet.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_preserva_shape_aliases_e_ordenacao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_csrf_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_sucesso_preserva_shape_recorrencia_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_aceita_filtros_canonicos_e_preserva_aliases caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_busca_sem_periodo_nao_limita_mes_atual
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados; schema inclui
  `/api/custos-fixos/`.
- Testes focados: 9 testes executados, todos OK.

### Registro de execucao - PM-20.4

Status: concluida.

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_preserva_shape_aliases_e_ordenacao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_vazia_preserva_shape caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_csrf_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_sucesso_preserva_shape_recorrencia_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_aceita_filtros_canonicos_e_preserva_aliases caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_busca_sem_periodo_nao_limita_mes_atual
venv\Scripts\python.exe manage.py test caixa.tests.CustoFixoTests caixa.tests.FiltrosHtmlTests.test_custos_fixos_periodo_todos_nao_forca_mes_atual caixa.tests.FiltrosHtmlTests.test_custos_fixos_filtros_usam_choices_do_modelo caixa.tests.FiltrosHtmlTests.test_custos_fixos_periodo_vencidos_respeita_intervalo_informado caixa.tests.LancamentoFinanceiroDominioTests.test_lancamento_financeiro_sincroniza_custo_fixo
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados; schema inclui
  `/api/custos-fixos/`.
- Testes focados de API: 9 testes executados, todos OK.
- Testes relacionados de custos fixos/dominio: 8 testes executados, todos OK.
- Suite completa: 717 testes executados, todos OK.
- Warnings de log durante a suite completa ficaram limitados a cenarios
  esperados de CSRF/login/logout ja cobertos por testes.
- `schema.yml` nao foi gerado nesta PM.
- Nenhuma regressao identificada.

### Registro de execucao - PM-20.5

Status: concluida.

Fase: encerramento.

Arquivos alterados pela PM-20:

- `caixa/tests.py`
- `caixa/views_custos_fixos_api.py`
- `docs/PLANO_PM20_MIGRACAO_CUSTOS_FIXOS_LISTA_CRIACAO_DRF.md`

Dependencias adicionadas:

- Nenhuma.

Endpoint migrado:

- `GET/POST /api/custos-fixos/`

Endpoint explicitamente nao alterado:

- `GET/PUT /api/custos-fixos/<id>/`

Confirmacoes finais:

- URL preservada.
- Nome de rota `caixa:api_custos_fixos` preservado.
- Metodos `GET` e `POST` preservados.
- `401`, `403`, `415`, `400`, `201`, `200` e `405` preservados pelos testes.
- JSONs de erro preservados.
- Shape de sucesso de lista preservado.
- Shape de sucesso de criacao preservado.
- Aliases de filtros preservados.
- Aliases de payload preservados.
- Criacao recorrente preservada.
- Signals/sincronizacoes principais preservados.
- `Allow: GET, POST` preservado.
- `Cache-Control` com `no-store` preservado nas respostas JSON.
- Frontend nao alterado.
- Settings nao alterado.
- CORS nao alterado.
- CSRF global nao alterado.
- Autenticacao global nao alterada.
- Nenhum Serializer, ViewSet ou ModelViewSet criado.

Riscos residuais:

- A documentacao OpenAPI inicial segue generica para este endpoint, pois a PM
  priorizou paridade runtime e nao criou serializer DRF.
- A mutation de criacao continua dependendo dos efeitos atuais de `save()` e
  signals; os testes cobrem os principais efeitos, mas mudancas futuras nesses
  services/signals ainda exigem paridade propria.

Recomendacao:

- PM-20 pronta para commit local manual.
