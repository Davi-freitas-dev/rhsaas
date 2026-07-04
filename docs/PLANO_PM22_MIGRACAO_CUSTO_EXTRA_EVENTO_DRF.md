# Plano PM-22 - Migracao incremental de `POST /api/eventos/custos-extras/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `POST /api/eventos/custos-extras/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de criacao de custo extra
de evento, sem alterar regra de negocio, helpers, form, service, serializer
manual, permissoes, CSRF, CORS, headers, status HTTP, JSON ou contrato do
frontend.

## Escopo

- Congelar o contrato atual de `POST /api/eventos/custos-extras/` em testes
  antes da migracao.
- Migrar somente a view `api_criar_custo_extra_evento`.
- Usar `@api_view(["POST"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissao manual `caixa.add_eventocustoextra`.
- Preservar CSRF real no `POST`.
- Preservar Content-Type, JSON invalido, status HTTP, headers e shape atual.
- Preservar evento inexistente como erro de validacao `400`, nao `404`.
- Reaproveitar helpers atuais da view.
- Reaproveitar `EventoCustoExtraForm`.
- Reaproveitar `criar_custo_extra`.
- Reaproveitar serializer manual `_serialize_event_extra_cost`.
- Preservar sincronizacoes de dominio atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Pagamento de custo extra.
- Endpoints de detalhe de evento.
- `GET /api/eventos/`.
- `GET/PUT /api/eventos/<id>/`.
- Endpoints de clientes.
- Endpoints de orcamentos.
- Endpoints de custos fixos.
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
- Alteracao de forms.
- Alteracao de services.
- Alteracao de selectors.
- Alteracao de serializers manuais.
- Alteracao de signals.
- Alteracao de model.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de metodos quando o contrato for pequeno.

Nesta PM, somente `POST /api/eventos/custos-extras/` deve ser migrado.

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

## Contrato atual identificado na PM-22.1

Arquivo atual:

- `caixa/views_custos_extras_api.py`

View atual:

- `api_criar_custo_extra_evento`

Rota atual:

- `path("api/eventos/custos-extras/", api_criar_custo_extra_evento, name="api_criar_custo_extra_evento")`

Nome da rota:

- `caixa:api_criar_custo_extra_evento`

Decorador atual:

- `@require_POST`
- `@require_api_permission(ADD_EVENT_EXTRA_COST_PERMISSION)`

Metodo aceito:

- `POST`

Metodos nao permitidos:

- `GET`, `PUT`, `PATCH` e `DELETE` retornam `405`.
- Header `Allow` esperado: `POST`.
- Resposta de `405` Django padrao deve ser preservada.

Permissao atual:

- `caixa.add_eventocustoextra`.
- A permissao e verificada pelo decorator `require_api_permission`.
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

- O endpoint nao usa `csrf_exempt`.
- Com `Client(enforce_csrf_checks=True)`, ausencia de CSRF valido bloqueia o
  `POST` antes da view.
- Com CSRF valido, a requisicao chega na view e segue para autenticacao,
  permissao, Content-Type, parse de JSON, validacao ou criacao.

Content-Type aceito:

- `application/json`, incluindo parametros como charset.

Content-Type invalido:

```json
{"detail": "Content-Type deve ser application/json."}
```

com status `415`.

JSON invalido ou body nao-dict:

```json
{"detail": "JSON invalido."}
```

com status `400`.

Evento inexistente:

- Nao retorna `404`.
- O id do evento e validado via `EventoCustoExtraForm`.
- Deve retornar `400` com shape:

```json
{"errors": {"evento": [...]}}
```

Payload aceito:

- Evento: `eventId`, `evento`, `evento_id`.
- Categoria: `category`, `categoria`.
- Descricao: `description`, `descricao`.
- Valor previsto: `plannedAmount`, `valor_previsto`.
- Data de vencimento: `dueDate`, `data_vencimento`.
- Observacao: `notes`, `observacao`.

Campos explicitamente ignorados na criacao:

- `paidAmount`.
- `valor_pago`.

A view sempre envia `valor_pago = "0.00"` para o form.

Payload de sucesso:

Status `201`:

```json
{
  "data": {
    "extraCost": {
      "id": 1,
      "eventId": 1,
      "eventNumber": "...",
      "eventName": "...",
      "eventLabel": "...",
      "contractCode": "...",
      "contractName": "",
      "contractLabel": "...",
      "clientId": 1,
      "clientName": "...",
      "category": "material",
      "categoryLabel": "Material",
      "description": "...",
      "plannedAmount": "123.45",
      "paidAmount": "0.00",
      "pendingPaymentAmount": "123.45",
      "dueDate": "2026-06-21",
      "notes": "...",
      "createdAt": "...",
      "updatedAt": "..."
    },
    "message": "Custo extra cadastrado com sucesso."
  }
}
```

Contrato importante do shape:

- `contractId` nao existe no payload atual.
- `paidAmount` retorna `"0.00"` mesmo se o cliente enviar `paidAmount` ou
  `valor_pago` no payload.

Erros de validacao:

```json
{"errors": ...}
```

com status `400`.

Principais validacoes atuais:

- `evento` e obrigatorio e deve existir.
- `categoria` respeita choices de `EventoCustoExtra`.
- `descricao` e obrigatoria.
- `valor_previsto` deve ser numerico e nao negativo.
- `data_vencimento` e obrigatoria e deve ser valida.
- validacoes de `EventoCustoExtra.clean()` tambem sao aplicadas no `save()`.

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- `405` preserva `Allow: POST`.
- Falha de CSRF acontece antes da view e preserva comportamento Django atual.

Efeitos de dominio:

- Cria um registro `EventoCustoExtra`.
- Define `criado_por` e `atualizado_por` com `request.user`.
- `post_save` de `EventoCustoExtra` sincroniza despesas operacionais do evento.
- `post_save` de `EventoCustoExtra` cria/atualiza obrigacao financeira canonica
  de origem `custo_extra`.
- A criacao do custo extra nao cria pagamento de custo extra.
- A criacao do custo extra nao cria lancamento financeiro direto.
- Lancamento financeiro de custo extra e sincronizado no fluxo de pagamento de
  custo extra, nao neste `POST`.

Testes existentes relacionados:

- `test_api_criar_custo_extra_evento_exige_autenticacao_e_permissao`
- `test_api_criar_custo_extra_evento_exige_json_valido`
- `test_api_criar_custo_extra_evento_rejeita_payload_invalido`
- `test_api_criar_custo_extra_evento_requer_csrf_em_cliente_real`
- `test_api_criar_custo_extra_evento_cria_e_sincroniza_modelagem`

## Riscos especificos de custo extra de evento

- DRF pode substituir `401` e `403` atuais por respostas padrao.
- DRF pode alterar `405` e o header `Allow: POST`.
- DRF pode parsear `request.data` antes da view e mudar o erro atual de JSON
  invalido.
- DRF pode transformar Content-Type invalido em erro padrao diferente do `415`
  atual.
- Evento inexistente pode virar `404` se for usado lookup fora do form; o
  contrato atual e `400` em `{"errors": {"evento": [...]}}`.
- `paidAmount` e `valor_pago` podem passar a ser aceitos por engano.
- O shape de `extraCost` pode mudar se for introduzido serializer DRF.
- O campo ausente `contractId` pode ser adicionado por engano.
- A migration pode perder `Cache-Control`/`no-store`.
- A mutation aciona sincronizacao de despesas operacionais e obrigacao
  canonica.
- OpenAPI pode ficar generico sem serializer DRF, mas isso nao deve motivar
  alteracao runtime.

## Guardrails

- Nao agrupar com pagamento de custo extra.
- Nao agrupar com detalhe de evento.
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
- Nao alterar forms.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar signals.
- Nao alterar model.
- Reaproveitar `_is_json_request`.
- Reaproveitar `_payload_json`.
- Reaproveitar `_first_payload_value`.
- Reaproveitar `_form_data_from_payload`.
- Reaproveitar `_errors_from_form`.
- Reaproveitar `_errors_from_validation_error`.
- Reaproveitar `_serialize_event_extra_cost`.
- Reaproveitar `EventoCustoExtraForm`.
- Reaproveitar `criar_custo_extra`.
- Preservar permissao manual `caixa.add_eventocustoextra`.
- Preservar evento inexistente como `400` de validacao.
- Priorizar paridade runtime sobre schema OpenAPI.

## PM-22.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas realizadas:

- View atual identificada.
- URL e nome de rota identificados.
- Metodo aceito identificado.
- Comportamento de metodos nao permitidos identificado.
- Permissao atual identificada.
- Comportamento de anonimo identificado.
- Comportamento de autenticado sem permissao identificado.
- CSRF atual identificado.
- Content-Type aceito identificado.
- JSON invalido identificado.
- Evento inexistente identificado.
- Shape de sucesso e erro identificado.
- Status HTTP atuais identificados.
- Headers relevantes identificados.
- Campos e aliases aceitos identificados.
- Efeitos colaterais de dominio identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum arquivo alterado.

## PM-22.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

Criar ou reforcar testes para `POST`:

- anonimo retorna `401` com JSON atual;
- autenticado sem `caixa.add_eventocustoextra` retorna `403` com JSON atual;
- sem CSRF valido usando `Client(enforce_csrf_checks=True)` bloqueia antes da
  view;
- com CSRF valido chega na view;
- Content-Type invalido retorna `415`;
- JSON invalido retorna `400`;
- body JSON nao-dict retorna `400`;
- payload invalido retorna `{"errors": ...}`;
- evento inexistente retorna `400` com `{"errors": {"evento": [...]}}`;
- sucesso retorna `201` com `data.extraCost` e `data.message`;
- shape completo de `data.extraCost`;
- ausencia de `contractId`;
- aliases de payload preservados:
  - `eventId`, `evento`, `evento_id`;
  - `category`, `categoria`;
  - `description`, `descricao`;
  - `plannedAmount`, `valor_previsto`;
  - `dueDate`, `data_vencimento`;
  - `notes`, `observacao`;
- `paidAmount` e `valor_pago` continuam ignorados;
- `paidAmount` da resposta retorna `"0.00"`;
- sincronizacao de despesa operacional preservada;
- obrigacao financeira canonica preservada;
- pagamento de custo extra nao e criado neste `POST`;
- lancamento financeiro direto nao e criado neste `POST`;
- headers JSON/no-store em `201`, `400`, `401`, `403` e `415`.

Criar ou reforcar testes para metodos nao permitidos:

- `GET`, `PUT`, `PATCH` e `DELETE` retornam `405`;
- header `Allow: POST` preservado;
- contrato de `405` Django padrao preservado.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_custo_extra_evento>
```

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.
- Nenhuma alteracao em pagamentos de custo extra ou detalhe de evento.

## PM-22.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_criar_custo_extra_evento` para DRF com paridade
comprovada.

Implementacao esperada:

- converter somente `api_criar_custo_extra_evento`;
- usar `@api_view(["POST"])`;
- usar `Response` somente na borda;
- preservar `@require_POST` ou alternativa local equivalente se necessario
  para manter `405` e `Allow: POST`;
- preservar permissao manual `caixa.add_eventocustoextra`;
- preservar `401` e `403` atuais;
- preservar CSRF real no `POST`;
- preservar `415`;
- preservar `400` de JSON invalido;
- preservar evento inexistente como `400` de validacao;
- preservar `{"errors": ...}` de validacao;
- preservar `201` de sucesso;
- preservar `405` e `Allow: POST`;
- preservar `Cache-Control`/`no-store`;
- reaproveitar helpers atuais da view;
- reaproveitar `EventoCustoExtraForm`;
- reaproveitar `criar_custo_extra`;
- reaproveitar `_serialize_event_extra_cost`;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao mexer em pagamento de custo extra;
- nao mexer em detalhe de evento.

Regras:

- Manter URL `/api/eventos/custos-extras/`.
- Manter nome de rota `caixa:api_criar_custo_extra_evento`.
- Manter metodo `POST`.
- Manter status HTTP.
- Manter JSON de sucesso.
- Manter JSONs de erro.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow: POST`.
- Manter CSRF real no `POST`.
- Manter permissao atual.
- Manter CORS sem alteracao.
- Nao deixar DRF substituir erros atuais por erros padrao.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_custo_extra_evento>
```

Gate de saida:

- `/api/eventos/custos-extras/` migrado para DRF.
- `POST` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-22.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_custo_extra_evento>
python manage.py test <testes_relacionados_de_eventos_custos_extras>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/eventos/custos-extras/`;
- nenhuma regressao;
- pagamento de custo extra nao foi alterado;
- detalhe de evento nao foi alterado;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado a `/api/eventos/custos-extras/`, testes e registro do plano;
- pagamento de custo extra nao alterado;
- detalhe de evento nao alterado;
- helpers atuais reaproveitados;
- form atual reaproveitado;
- service atual reaproveitado;
- serializer manual atual reaproveitado;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- testes focados passam;
- testes relacionados passam;
- suite geral passa;
- warnings do spectacular registrados;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-22.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-22 antes de avancar para outro
endpoint.

Tarefas:

- Atualizar este documento.
- Registrar arquivos alterados.
- Registrar testes criados.
- Registrar comandos executados.
- Registrar resultado dos testes focados.
- Registrar resultado dos testes relacionados.
- Registrar resultado da suite completa.
- Registrar resultado do `spectacular --validate`.
- Registrar warnings encontrados.
- Registrar diferencas encontradas, se houver.
- Registrar decisao sobre `schema.yml`, se tiver sido gerado.
- Confirmar que pagamento de custo extra nao foi alterado.
- Confirmar que detalhe de evento nao foi alterado.
- Confirmar que nenhum outro endpoint foi migrado.
- Confirmar que frontend nao foi alterado.
- Confirmar que settings, CORS, CSRF global e auth global nao foram alterados.
- Registrar riscos residuais.
- Registrar recomendacao: pronto, ajustar ou reverter.

Proximo passo natural, somente se PM-22 estiver estavel:

- retomar o roadmap e escolher o proximo endpoint de menor risco, mantendo
  diagnostico read-only antes de qualquer migracao.

## Criterios globais de aceite

- `POST /api/eventos/custos-extras/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodo `POST` preservado.
- Status HTTP preservados.
- JSON de sucesso preservado.
- JSONs de erro preservados.
- Evento inexistente preservado como `400` de validacao.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow: POST` preservado nos `405`.
- Permissao `caixa.add_eventocustoextra` preservada.
- CSRF real preservado no `POST`.
- Content-Type atual preservado.
- JSON invalido atual preservado.
- Campos e aliases legados preservados.
- `paidAmount`/`valor_pago` continuam ignorados na criacao.
- `contractId` continua ausente.
- Sincronizacao de despesa operacional preservada.
- Obrigacao financeira canonica preservada.
- Nenhum pagamento de custo extra criado neste `POST`.
- Nenhum lancamento financeiro direto criado neste `POST`.
- Frontend nao alterado.
- Pagamento de custo extra nao alterado.
- Detalhe de evento nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/eventos/custos-extras/`.
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
- `Allow: POST` mudar;
- Content-Type invalido deixar de retornar `415` atual;
- JSON invalido deixar de retornar `400` atual;
- body nao-dict deixar de retornar `400` atual;
- evento inexistente mudar de `400` para `404`;
- erros de validacao deixarem de retornar `{"errors": ...}`;
- `paidAmount` ou `valor_pago` passarem a alterar `valor_pago` na criacao;
- `contractId` passar a existir na resposta;
- sincronizacao de despesa operacional deixar de ocorrer;
- obrigacao financeira canonica deixar de ocorrer;
- pagamento de custo extra for criado indevidamente;
- lancamento financeiro direto for criado indevidamente;
- aliases legados forem removidos;
- outro endpoint precisar ser alterado;
- pagamento de custo extra precisar ser alterado;
- detalhe de evento precisar ser alterado;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar settings, CORS, CSRF global ou auth global.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_criar_custo_extra_evento`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_criar_custo_extra_evento`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

Se efeitos de dominio divergirem:

- Parar a PM.
- Reverter a migracao runtime.
- Manter testes que detectaram a divergencia.
- Registrar exatamente qual efeito divergiu.

## Registro de execucao

### Registro de execucao - PM-22.1

Status: concluida.

Fase: diagnostico read-only.

Endpoint alvo:

- `POST /api/eventos/custos-extras/`

Arquivos lidos:

- `caixa/views_custos_extras_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/forms_custos_extras.py`
- `caixa/models_custos_extras.py`
- `caixa/services_cadastros.py`
- `caixa/services_custos_extras.py`
- `caixa/services_modelagem_canonica.py`
- `caixa/services_lancamentos.py`
- `caixa/services_obrigacoes.py`
- `caixa/signals.py`
- `caixa/models_pagamentos.py`
- `caixa/serializers_dimensoes_operacionais.py`
- `caixa/tests.py`

Resultado:

- Contrato atual de `/api/eventos/custos-extras/` mapeado.
- View ainda estava Django puro.
- Permissao atual identificada.
- CSRF real no `POST` identificado.
- Content-Type e JSON invalido identificados.
- Evento inexistente identificado como `400` de validacao.
- Shape de sucesso e erro identificado.
- Campos e aliases identificados.
- Efeitos de dominio identificados.
- Lacunas de paridade identificadas.
- Nenhum arquivo alterado nesta fase.

### Registro de execucao - PM-22.2

Status: concluida.

Fase: congelamento de contrato em testes.

Arquivo alterado:

- `caixa/tests.py`

Testes criados ou reforcados:

- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_autenticacao_e_permissao`
  - reforcado para congelar `Content-Type: application/json` em `401` e
    `403`.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_json_valido`
  - reforcado para congelar `415` de Content-Type invalido;
  - reforcado para congelar `400` de JSON invalido;
  - reforcado para congelar body JSON nao-dict como `400`;
  - reforcado para congelar headers JSON/no-store.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_rejeita_payload_invalido`
  - reforcado para congelar headers JSON/no-store nos erros `{"errors": ...}`.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_inexistente_preserva_400_de_validacao`
  - criado para congelar evento inexistente como `400` de validacao em
    `{"errors": {"evento": [...]}}`.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_requer_csrf_em_cliente_real`
  - reforcado para congelar bloqueio sem CSRF;
  - reforcado para confirmar que CSRF valido chega na view.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_cria_e_sincroniza_modelagem`
  - reforcado para congelar shape completo de `data.extraCost`;
  - reforcado para congelar ausencia de `contractId`;
  - reforcado para congelar `paidAmount` como `"0.00"`;
  - reforcado para congelar ausencia de pagamento de custo extra;
  - reforcado para congelar ausencia de lancamento financeiro direto.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_preserva_aliases_de_payload`
  - criado para congelar aliases `evento`, `evento_id`, `categoria`,
    `descricao`, `valor_previsto`, `data_vencimento` e `observacao`.
- `FiltrosHtmlTests.test_api_criar_custo_extra_evento_metodos_nao_permitidos_preservam_405`
  - criado para congelar `GET`, `PUT`, `PATCH` e `DELETE` como `405`;
  - congela `Allow: POST`.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_json_valido caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_rejeita_payload_invalido caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_inexistente_preserva_400_de_validacao caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_requer_csrf_em_cliente_real caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_cria_e_sincroniza_modelagem caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_preserva_aliases_de_payload caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_metodos_nao_permitidos_preservam_405
venv\Scripts\python.exe manage.py check
```

Observacao local:

- A primeira tentativa sem variaveis locais abortou antes de carregar Django
  porque o ambiente estava sem `SECRET_KEY`.
- Os comandos foram reexecutados com:

```bash
DEBUG=True
SECRET_KEY=local-validation-secret
```

Resultados:

- Testes focados: 8 testes executados, todos OK.
- `check`: OK, sem issues.
- Nenhuma view foi migrada nesta fase.
- Nenhuma alteracao em pagamento de custo extra.
- Nenhuma alteracao em detalhe de evento.

### Registro de execucao - PM-22.3

Status: concluida.

Fase: migracao controlada para DRF.

Arquivo alterado:

- `caixa/views_custos_extras_api.py`

Implementacao:

- `api_criar_custo_extra_evento` foi migrada para DRF com
  `@api_view(["POST"])`.
- `@require_POST` foi preservado para manter `405` e `Allow: POST`.
- `JsonBodySafeSessionAuthentication` foi reaproveitado para preservar CSRF
  real e evitar que DRF substitua o contrato de JSON invalido.
- `AllowAny` foi usado localmente para impedir que a permissao global do DRF
  substitua `401`/`403` atuais.
- Permissao manual `caixa.add_eventocustoextra` foi preservada.
- `Response` passou a ser usado somente na borda deste endpoint.
- Respostas continuam sendo montadas a partir dos `JsonResponse` atuais, com
  copia de `Cache-Control` e `Expires`.
- `_is_json_request` foi reaproveitado.
- `_payload_json` foi reaproveitado sobre o request Django interno.
- `_form_data_from_payload` foi reaproveitado.
- `EventoCustoExtraForm` foi reaproveitado.
- `criar_custo_extra` foi reaproveitado.
- `_serialize_event_extra_cost` foi reaproveitado.
- `paidAmount` e `valor_pago` continuam ignorados na criacao.
- Evento inexistente continua como `400` de validacao.

Nao alterado:

- Pagamento de custo extra.
- Detalhe de evento.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Forms.
- Services.
- Selectors.
- Serializers manuais.
- Signals.
- Models.
- Serializer DRF, ViewSet ou ModelViewSet.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_json_valido caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_rejeita_payload_invalido caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_inexistente_preserva_400_de_validacao caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_requer_csrf_em_cliente_real caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_cria_e_sincroniza_modelagem caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_preserva_aliases_de_payload caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_metodos_nao_permitidos_preservam_405
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados.
- OpenAPI inclui `/api/eventos/custos-extras/`.
- Testes focados: 8 testes executados, todos OK.

### Registro de execucao - PM-22.4

Status: concluida.

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_autenticacao_e_permissao caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_exige_json_valido caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_rejeita_payload_invalido caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_inexistente_preserva_400_de_validacao caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_requer_csrf_em_cliente_real caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_cria_e_sincroniza_modelagem caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_preserva_aliases_de_payload caixa.tests.FiltrosHtmlTests.test_api_criar_custo_extra_evento_metodos_nao_permitidos_preservam_405
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados.
- Testes focados de custo extra de evento: 8 testes executados, todos OK.
- Testes relacionados de `FiltrosHtmlTests`: 367 testes executados, todos OK.
- Suite completa: 725 testes executados, todos OK.
- Warnings de log durante a suite completa ficaram limitados a cenarios
  esperados de CSRF/login/logout e AXES ja cobertos por testes.
- `schema.yml` nao foi gerado nesta PM.
- Nenhuma regressao identificada.

### Registro de execucao - PM-22.5

Status: concluida.

Fase: encerramento.

Arquivos alterados pela PM-22:

- `caixa/tests.py`
- `caixa/views_custos_extras_api.py`
- `docs/PLANO_PM22_MIGRACAO_CUSTO_EXTRA_EVENTO_DRF.md`

Dependencias adicionadas:

- Nenhuma.

Endpoint migrado:

- `POST /api/eventos/custos-extras/`

Endpoints explicitamente nao alterados:

- Pagamento de custo extra.
- Detalhe de evento.
- `GET /api/eventos/`.
- `GET/PUT /api/eventos/<id>/`.

Confirmacoes finais:

- URL preservada.
- Nome de rota `caixa:api_criar_custo_extra_evento` preservado.
- Metodo `POST` preservado.
- `401`, `403`, `415`, `400`, `201` e `405` preservados pelos testes.
- Evento inexistente preservado como `400` de validacao.
- JSONs de erro preservados.
- Shape de sucesso preservado.
- Aliases de payload preservados.
- `paidAmount`/`valor_pago` continuam ignorados.
- `contractId` continua ausente.
- Sincronizacao de despesa operacional preservada.
- Obrigacao financeira canonica preservada.
- Nenhum pagamento de custo extra criado neste `POST`.
- Nenhum lancamento financeiro direto criado neste `POST`.
- `Allow: POST` preservado.
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
- A mutation continua dependendo dos efeitos atuais de form, service e signals;
  os testes cobrem os principais efeitos, mas mudancas futuras nesses pontos
  ainda exigem paridade propria.

Recomendacao:

- PM-22 pronta para commit local manual.
