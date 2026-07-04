# Plano PM-21 - Migracao incremental de `GET/PUT /api/custos-fixos/<id>/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET/PUT /api/custos-fixos/<id>/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de detalhe e atualizacao de
custo fixo, sem alterar regra de negocio, helpers, selectors, serializers
manuais, permissoes, CSRF, CORS, headers, status HTTP, JSON ou contrato do
frontend.

## Escopo

- Congelar o contrato atual de `GET/PUT /api/custos-fixos/<id>/` em testes
  antes da migracao.
- Migrar somente a view `api_custo_fixo_detalhe`.
- Usar `@api_view(["GET", "PUT"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissoes manuais por metodo:
  - `GET`: `caixa.view_custofixo`;
  - `PUT`: `caixa.change_custofixo`.
- Preservar CSRF real no `PUT`.
- Preservar Content-Type, JSON invalido, status HTTP, headers e shape atual.
- Preservar 404 Django padrao para registro inexistente.
- Reaproveitar helpers, selectors e serializers manuais atuais.
- Preservar recalculo de status e sincronizacoes financeiras atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET /api/custos-fixos/`.
- `POST /api/custos-fixos/`.
- Qualquer alteracao no endpoint de lista/criacao de custos fixos.
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
- Alteracao de model.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de metodos quando o contrato for pequeno.

Nesta PM, somente `GET/PUT /api/custos-fixos/<id>/` deve ser migrado. O
endpoint `GET/POST /api/custos-fixos/` ja pertence a PM-20 e nao deve ser
alterado novamente nesta PM.

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

## Contrato atual identificado na PM-21.1

Arquivo atual:

- `caixa/views_custos_fixos_api.py`

View atual:

- `api_custo_fixo_detalhe`

Rota atual:

- `path("api/custos-fixos/<int:pk>/", api_custo_fixo_detalhe, name="api_custo_fixo_detalhe")`

Nome da rota:

- `caixa:api_custo_fixo_detalhe`

Decorador atual:

- `@require_http_methods(["GET", "PUT"])`

Metodos aceitos:

- `GET`
- `PUT`

Metodos nao permitidos:

- `POST`, `PATCH` e `DELETE` retornam `405`.
- Header `Allow` esperado: `GET, PUT`.
- Resposta de `405` e HTML vazia do Django devem ser preservadas.

Permissoes atuais:

- `GET` exige `caixa.view_custofixo`.
- `PUT` exige `caixa.change_custofixo`.
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

Registro inexistente:

- Com autenticacao e permissao validas, usa `get_object_or_404(CustoFixo, pk=pk)`.
- Retorna `404` Django padrao em HTML.
- Nao retorna JSON customizado.

CSRF atual no `PUT`:

- `PUT` nao usa `csrf_exempt`.
- Com `Client(enforce_csrf_checks=True)`, ausencia de CSRF valido deve ser
  bloqueada antes da view pelo comportamento Django atual.
- Com CSRF valido, a requisicao chega na view e segue para autenticacao,
  permissao, 404, validacao ou atualizacao.

Content-Type aceito no `PUT`:

- `application/json`.

Content-Type invalido no `PUT`:

```json
{"detail": "Content-Type deve ser application/json."}
```

com status `415`.

JSON invalido ou body nao-dict no `PUT`:

```json
{"detail": "JSON invalido."}
```

com status `400`.

Payload de sucesso do `GET`:

Status `200`:

```json
{
  "data": {
    "fixedCost": {},
    "permissions": {
      "canUpdate": true
    },
    "meta": {
      "source": "backend"
    }
  }
}
```

Payload de sucesso do `PUT`:

Status `200`:

```json
{
  "data": {
    "fixedCost": {},
    "message": "Custo fixo atualizado com sucesso."
  }
}
```

Shape de `data.fixedCost`:

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

Aliases aceitos no payload `PUT`:

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

Erro de integridade na atualizacao:

```json
{"errors": {"detail": ["Nao foi possivel atualizar o custo fixo."]}}
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

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- `405` preserva `Allow: GET, PUT`.
- `404` preserva resposta Django padrao em HTML.

Efeitos de dominio do `PUT`:

- Atualiza o `CustoFixo` existente.
- Define `atualizado_por` com `request.user`.
- Nao altera `criado_por`.
- Executa `full_clean()`.
- Executa `save()`, que recalcula status automaticamente.
- Nao chama `gerar_recorrencias()`.
- `post_save` sincroniza:
  - lancamento financeiro de custo fixo;
  - obrigacao financeira canonica;
  - baixa canonica por origem `custo_fixo`.

Diferença relevante entre criacao e atualizacao:

- `POST /api/custos-fixos/` chama `gerar_recorrencias()`.
- `PUT /api/custos-fixos/<id>/` nao chama `gerar_recorrencias()`.
- A atualizacao pode alterar status e sincronizacoes financeiras do registro
  existente, inclusive criando, atualizando ou removendo lancamento/baixa
  conforme `valor_pago`, `status`, `ativo` e validacoes atuais.

## Riscos especificos de atualizacao de custo fixo

- DRF pode substituir `401` e `403` atuais por respostas padrao.
- DRF pode alterar `405` e o header `Allow: GET, PUT`.
- DRF pode transformar o `404` Django padrao em JSON.
- DRF pode parsear `request.data` antes da view e mudar o erro atual de JSON
  invalido.
- DRF pode acionar erro de media type diferente do `415` atual.
- `PUT` e mutation financeira com efeitos colaterais.
- `save()` recalcula status automaticamente.
- Signals sincronizam lancamento financeiro, obrigacao financeira canonica e
  baixa canonica.
- Atualizacao de `ativo=False` pode remover obrigacao canonica.
- Atualizacao de `valor_pago`, `data_pagamento`, `status` ou baixa manual pode
  criar, alterar ou remover lancamento/baixa.
- Validacao de caixa disponivel pode bloquear aumento de `valor_pago`.
- Campos e aliases legados podem ser perdidos se houver serializer novo.
- `Cache-Control`/`no-store` pode ser perdido se a resposta mudar.
- OpenAPI pode ficar generico sem serializer DRF, mas isso nao deve motivar
  alteracao runtime.

## Guardrails

- Nao alterar `GET/POST /api/custos-fixos/`.
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
- Reaproveitar `_custo_fixo_detalhe_response`.
- Reaproveitar `_atualizar_custo_fixo_response`.
- Reaproveitar `_serialize_custo_fixo`.
- Reaproveitar `_custo_fixo_data_from_payload`.
- Reaproveitar `_payload_json`.
- Reaproveitar `_is_json_request`.
- Preservar permissoes manuais por metodo.
- Preservar `get_object_or_404`/404 Django padrao.
- Priorizar paridade runtime sobre schema OpenAPI.

## PM-21.1 - Diagnostico read-only

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
- Registro inexistente identificado.
- Shape de sucesso e erro identificado.
- Status HTTP atuais identificados.
- Headers relevantes identificados.
- Campos retornados e aliases identificados.
- Efeitos colaterais de dominio identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum arquivo alterado.

## PM-21.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

Criar ou reforcar testes para `GET`:

- anonimo retorna `401` com JSON atual;
- autenticado sem `caixa.view_custofixo` retorna `403` com JSON atual;
- autenticado com `caixa.view_custofixo` retorna `200`;
- shape completo de `data.fixedCost`;
- `data.permissions.canUpdate` preservado;
- `data.meta.source == "backend"`;
- usuario com apenas `view_custofixo` tem `canUpdate == false`;
- usuario com `view_custofixo` e `change_custofixo` tem `canUpdate == true`;
- registro inexistente retorna `404` Django padrao;
- headers JSON/no-store.

Criar ou reforcar testes para `PUT`:

- sem CSRF valido usando `Client(enforce_csrf_checks=True)` bloqueia antes da
  view;
- com CSRF valido chega na view;
- anonimo retorna `401` quando chega na view;
- autenticado sem `caixa.change_custofixo` retorna `403`;
- registro inexistente retorna `404` Django padrao;
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
- aliases de payload canonicos e legados preservados;
- sucesso retorna `200` com `data.fixedCost` e `data.message`;
- atualizacao de status preservada;
- `atualizado_por` preservado;
- `criado_por` nao e alterado;
- `gerar_recorrencias()` nao e chamado;
- sincronizacoes principais preservadas:
  - lancamento financeiro;
  - obrigacao financeira canonica;
  - baixa canonica quando aplicavel;
- headers JSON/no-store.

Criar ou reforcar testes para metodos nao permitidos:

- `POST`, `PATCH` e `DELETE` retornam `405`;
- header `Allow: GET, PUT` preservado;
- contrato de `405` Django padrao preservado.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_custo_fixo_detalhe>
```

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.
- Nenhuma alteracao em `GET/POST /api/custos-fixos/`.

## PM-21.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_custo_fixo_detalhe` para DRF com paridade
comprovada.

Implementacao esperada:

- converter somente `api_custo_fixo_detalhe`;
- usar `@api_view(["GET", "PUT"])`;
- usar `Response` somente na borda;
- preservar `@require_http_methods(["GET", "PUT"])` ou alternativa local
  equivalente se necessario para manter `405` e `Allow: GET, PUT`;
- preservar permissao manual por metodo;
- preservar `401` e `403` atuais;
- preservar `404` Django padrao;
- preservar `415`;
- preservar `400` de JSON invalido;
- preservar `{"errors": ...}` de validacao;
- preservar `200` de detalhe e atualizacao;
- preservar `405` e `Allow: GET, PUT`;
- preservar `Cache-Control`/`no-store`;
- reaproveitar `_custo_fixo_detalhe_response`;
- reaproveitar `_atualizar_custo_fixo_response`;
- reaproveitar helpers, selectors e serializers manuais atuais;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao mexer no endpoint de lista/criacao.

Regras:

- Manter URL `/api/custos-fixos/<id>/`.
- Manter nome de rota `caixa:api_custo_fixo_detalhe`.
- Manter metodos `GET` e `PUT`.
- Manter status HTTP.
- Manter JSON de sucesso.
- Manter JSONs de erro.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow: GET, PUT`.
- Manter CSRF real no `PUT`.
- Manter permissoes atuais por metodo.
- Manter CORS sem alteracao.
- Nao deixar DRF substituir erros atuais por erros padrao.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_custo_fixo_detalhe>
```

Gate de saida:

- `/api/custos-fixos/<id>/` migrado para DRF.
- `GET` mantem paridade.
- `PUT` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-21.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_custo_fixo_detalhe>
python manage.py test <testes_relacionados_de_custos_fixos>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/custos-fixos/{id}/`;
- nenhuma regressao;
- `GET/POST /api/custos-fixos/` nao foi alterado;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado a `/api/custos-fixos/<id>/`, testes e registro do plano;
- endpoint de lista/criacao nao alterado;
- helpers atuais reaproveitados;
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

## PM-21.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-21 antes de avancar para outro
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
- Confirmar que `GET/POST /api/custos-fixos/` nao foi alterado.
- Confirmar que nenhum outro endpoint foi migrado.
- Confirmar que frontend nao foi alterado.
- Confirmar que settings, CORS, CSRF global e auth global nao foram alterados.
- Registrar riscos residuais.
- Registrar recomendacao: pronto, ajustar ou reverter.

Proximo passo natural, somente se PM-21 estiver estavel:

- retomar o roadmap e escolher o proximo endpoint de menor risco, mantendo
  diagnostico read-only antes de qualquer migracao.

## Criterios globais de aceite

- `GET /api/custos-fixos/<id>/` mantem paridade.
- `PUT /api/custos-fixos/<id>/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodos `GET` e `PUT` preservados.
- Status HTTP preservados.
- JSON de sucesso preservado.
- JSONs de erro preservados.
- 404 Django padrao preservado.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow: GET, PUT` preservado nos `405`.
- Permissoes por metodo preservadas.
- CSRF real preservado no `PUT`.
- Content-Type atual preservado.
- JSON invalido atual preservado.
- Campos e aliases legados preservados.
- Atualizacao de status preservada.
- Sincronizacoes financeiras preservadas.
- Frontend nao alterado.
- `GET/POST /api/custos-fixos/` nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/custos-fixos/{id}/`.
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
- `Allow: GET, PUT` mudar;
- 404 Django padrao mudar para JSON;
- Content-Type invalido deixar de retornar `415` atual;
- JSON invalido deixar de retornar `400` atual;
- erros de validacao deixarem de retornar `{"errors": ...}`;
- atualizacao de status mudar comportamento;
- signals/sincronizacoes deixarem de ocorrer;
- lancamento financeiro for criado/removido indevidamente;
- obrigacao financeira canonica for criada/removida indevidamente;
- baixa canonica for criada/removida indevidamente;
- aliases legados forem removidos;
- outro endpoint precisar ser alterado;
- `GET/POST /api/custos-fixos/` precisar ser alterado;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar settings, CORS, CSRF global ou auth global.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_custo_fixo_detalhe`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_custo_fixo_detalhe`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

Se status, signals ou sincronizacoes divergirem:

- Parar a PM.
- Reverter a migracao runtime.
- Manter testes que detectaram a divergencia.
- Registrar exatamente qual efeito divergiu.

## Registro de execucao

### Registro de execucao - PM-21.1

Fase: diagnostico read-only.

Endpoint alvo:

- `GET/PUT /api/custos-fixos/<id>/`

Arquivos lidos:

- `caixa/views_custos_fixos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/models_custo_fixo.py`
- `caixa/signals.py`
- `caixa/services_lancamentos.py`
- `caixa/services_modelagem_canonica.py`
- `caixa/tests.py`

Resultado:

- Contrato atual de `/api/custos-fixos/<id>/` mapeado.
- View ainda estava Django puro.
- Permissoes por metodo identificadas.
- CSRF real no `PUT` identificado.
- Content-Type e JSON invalido identificados.
- 404 Django padrao identificado.
- Shape de sucesso e erro identificado.
- Campos e aliases identificados.
- Efeitos de dominio identificados.
- Lacunas de paridade identificadas.
- Nenhum arquivo alterado nesta fase.

### Registro de execucao - PM-21.2

Status: concluida.

Fase: congelamento de contrato em testes.

Arquivo alterado:

- `caixa/tests.py`

Testes criados:

- `FiltrosHtmlTests.test_api_custo_fixo_detalhe_get_preserva_auth_permissao_shape_e_404`
  - congela `401` anonimo;
  - congela `403` sem `view_custofixo`;
  - congela `200` com `view_custofixo`;
  - congela shape completo de `data.fixedCost`;
  - congela `permissions.canUpdate`;
  - congela `meta.source`;
  - congela `404` Django padrao.
- `FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_preserva_csrf_auth_permissao_e_404`
  - congela CSRF real bloqueando `PUT` sem token;
  - congela `401` anonimo quando a requisicao chega na view;
  - congela `403` sem `change_custofixo`;
  - congela `404` Django padrao.
- `FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_erros_de_payload_preservam_contrato`
  - congela Content-Type invalido `415`;
  - congela JSON invalido `400`;
  - congela body nao-dict `400`;
  - congela erros de validacao em `{"errors": ...}`.
- `FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_sucesso_preserva_aliases_status_e_sincronizacoes`
  - congela aliases legados do `PUT`;
  - congela sucesso `200`;
  - congela `data.fixedCost` e `data.message`;
  - congela recalculo automatico de status;
  - congela `atualizado_por`;
  - congela preservacao de `criado_por`;
  - congela ausencia de novas recorrencias na atualizacao;
  - congela sincronizacao de lancamento financeiro;
  - congela sincronizacao de obrigacao financeira canonica;
  - congela baixa canonica aplicavel.
- `FiltrosHtmlTests.test_api_custo_fixo_detalhe_metodos_nao_permitidos_preservam_405`
  - congela `POST`, `PATCH` e `DELETE` como `405`;
  - congela `Allow: GET, PUT`.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_get_preserva_auth_permissao_shape_e_404 caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_preserva_csrf_auth_permissao_e_404 caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_sucesso_preserva_aliases_status_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_metodos_nao_permitidos_preservam_405
venv\Scripts\python.exe manage.py check
```

Resultados:

- Testes focados: 5 testes executados, todos OK.
- `check`: OK, sem issues.
- Nenhuma view foi migrada nesta fase.
- Nenhuma alteracao em `GET/POST /api/custos-fixos/`.

### Registro de execucao - PM-21.3

Status: concluida.

Fase: migracao controlada para DRF.

Arquivo alterado:

- `caixa/views_custos_fixos_api.py`

Implementacao:

- `api_custo_fixo_detalhe` foi migrada para DRF com
  `@api_view(["GET", "PUT"])`.
- `Response` passou a ser usado somente na borda deste endpoint.
- `@require_http_methods(["GET", "PUT"])` foi preservado para manter `405` e
  `Allow: GET, PUT`.
- `JsonBodySafeSessionAuthentication` foi reaproveitado para preservar CSRF
  real e evitar que DRF substitua o contrato de JSON invalido.
- `AllowAny` foi usado localmente para impedir que a permissao global do DRF
  substitua `401`/`403` atuais.
- Permissoes manuais por metodo foram preservadas:
  - `GET`: `caixa.view_custofixo`;
  - `PUT`: `caixa.change_custofixo`.
- `_custo_fixo_detalhe_response` foi reaproveitado.
- `_atualizar_custo_fixo_response` foi reaproveitado.
- Helpers e serializer manual atual foram reaproveitados.
- O `404` Django padrao foi preservado com `page_not_found`.

Nao alterado:

- `GET/POST /api/custos-fixos/`.
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
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_get_preserva_auth_permissao_shape_e_404 caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_preserva_csrf_auth_permissao_e_404 caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_sucesso_preserva_aliases_status_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_metodos_nao_permitidos_preservam_405
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados; schema inclui
  `/api/custos-fixos/{id}/`.
- Testes focados: 5 testes executados, todos OK.

### Registro de execucao - PM-21.4

Status: concluida.

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_get_preserva_auth_permissao_shape_e_404 caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_preserva_csrf_auth_permissao_e_404 caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_put_sucesso_preserva_aliases_status_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custo_fixo_detalhe_metodos_nao_permitidos_preservam_405
venv\Scripts\python.exe manage.py test caixa.tests.CustoFixoTests caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_lista_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_criacao_sucesso_preserva_shape_recorrencia_e_sincronizacoes caixa.tests.FiltrosHtmlTests.test_api_custos_fixos_metodos_nao_permitidos_preservam_405 caixa.tests.FiltrosHtmlTests.test_custos_fixos_periodo_todos_nao_forca_mes_atual caixa.tests.FiltrosHtmlTests.test_custos_fixos_filtros_usam_choices_do_modelo caixa.tests.FiltrosHtmlTests.test_custos_fixos_periodo_vencidos_respeita_intervalo_informado caixa.tests.LancamentoFinanceiroDominioTests.test_lancamento_financeiro_sincroniza_custo_fixo
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados; schema inclui
  `/api/custos-fixos/{id}/`.
- Testes focados de detalhe: 5 testes executados, todos OK.
- Testes relacionados de custos fixos/lista/dominio: 11 testes executados,
  todos OK.
- Suite completa: 722 testes executados, todos OK.
- Warnings de log durante a suite completa ficaram limitados a cenarios
  esperados de CSRF/login/logout ja cobertos por testes.
- `schema.yml` nao foi gerado nesta PM.
- Nenhuma regressao identificada.

### Registro de execucao - PM-21.5

Status: concluida.

Fase: encerramento.

Arquivos alterados pela PM-21:

- `caixa/tests.py`
- `caixa/views_custos_fixos_api.py`
- `docs/PLANO_PM21_MIGRACAO_CUSTO_FIXO_DETALHE_DRF.md`

Dependencias adicionadas:

- Nenhuma.

Endpoint migrado:

- `GET/PUT /api/custos-fixos/<id>/`

Endpoint explicitamente nao alterado:

- `GET/POST /api/custos-fixos/`

Confirmacoes finais:

- URL preservada.
- Nome de rota `caixa:api_custo_fixo_detalhe` preservado.
- Metodos `GET` e `PUT` preservados.
- `401`, `403`, `415`, `400`, `200`, `404` e `405` preservados pelos testes.
- 404 Django padrao preservado.
- JSONs de erro preservados.
- Shape de sucesso de detalhe preservado.
- Shape de sucesso de atualizacao preservado.
- Aliases de payload preservados.
- Recalculo automatico de status preservado.
- Sincronizacoes financeiras principais preservadas.
- `Allow: GET, PUT` preservado.
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
- A mutation de atualizacao continua dependendo dos efeitos atuais de `save()`
  e signals; os testes cobrem os principais efeitos, mas mudancas futuras
  nesses services/signals ainda exigem paridade propria.

Recomendacao:

- PM-21 pronta para commit local manual.
