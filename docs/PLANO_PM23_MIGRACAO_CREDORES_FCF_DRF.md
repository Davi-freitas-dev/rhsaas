# Plano PM-23 - Migracao incremental de `GET/POST /api/fcf/creditors/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET/POST /api/fcf/creditors/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de listagem e criacao de
credores FCF, sem alterar regra de negocio, helpers, serializers manuais,
permissoes, CSRF, CORS, headers, status HTTP, JSON ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET/POST /api/fcf/creditors/` em testes antes
  da migracao.
- Migrar somente a view `api_credores_financiamentos`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissoes manuais:
  - `GET`: `caixa.view_credor`;
  - `POST`: `caixa.view_credor` e `caixa.add_credor`.
- Preservar CSRF real no `POST`.
- Preservar Content-Type, JSON invalido, status HTTP, headers e shape atual.
- Preservar `405` JSON manual sem header `Allow`.
- Reaproveitar helpers atuais da view.
- Reaproveitar serializer manual `serializar_credor_financiamento`.
- Reaproveitar `montar_payload_credores_financiamentos_api`.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET/POST /api/fcf/`.
- `POST /api/fcf/debts/`.
- Parcelas FCF.
- Pagamentos FCF.
- Obrigacoes financeiras.
- Baixas financeiras.
- Lancamentos financeiros.
- Endpoints financeiros canonicos.
- Outros endpoints FCF.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Serializers DRF.
- ViewSets.
- ModelViewSets.
- Refatoracao de regra de negocio.
- Alteracao de models.
- Alteracao de services.
- Alteracao de selectors.
- Alteracao de serializers manuais.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de metodos quando o contrato for pequeno.

Nesta PM, `GET` e `POST` de `/api/fcf/creditors/` podem seguir juntos porque
formam um contrato pequeno e coeso de cadastro mestre.

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

## Contrato atual identificado na PM-23.1

Arquivo atual:

- `caixa/views_financiamentos.py`

View atual:

- `api_credores_financiamentos`

Auxiliar de criacao:

- `_api_criar_credor_financiamento`

Rota atual:

- `path("api/fcf/creditors/", api_credores_financiamentos, name="api_credores_financiamentos")`

Nome da rota:

- `caixa:api_credores_financiamentos`

Decorador atual:

- `@require_api_permission(FINANCIAL_CREDITORS_PERMISSION)`

Metodos aceitos:

- `GET`
- `POST`

Metodos nao permitidos:

- `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- O `405` atual e JSON manual:

```json
{"detail": "Metodo nao permitido."}
```

- O codigo atual nao define header `Allow`.
- Esta ausencia de `Allow` deve ser tratada como contrato atual.

Permissoes atuais:

- `GET` exige `caixa.view_credor`.
- `POST` exige `caixa.view_credor` no decorator externo.
- `POST` tambem exige `caixa.add_credor` dentro de
  `_api_criar_credor_financiamento`.
- Nao usar `DjangoModelPermissions`, `IsAuthenticated` global ou permissao DRF
  generica se isso mudar contrato.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem `view_credor`:

```json
{"detail": "Permission denied."}
```

com status `403`.

Comportamento para usuario autenticado com `view_credor`, mas sem
`add_credor`, no `POST`:

```json
{"detail": "Permission denied."}
```

com status `403`.

CSRF atual no `POST`:

- O endpoint nao usa `csrf_exempt`.
- Com `Client(enforce_csrf_checks=True)`, ausencia de CSRF valido deve bloquear
  o `POST` antes da view.
- Com CSRF valido, a requisicao chega na view e segue para autenticacao,
  permissao, Content-Type, parse de JSON, validacao ou criacao.

Content-Type aceito no `POST`:

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

Payload aceito no `POST`:

- Nome: `name`, `nome`.
- Documento: `document`, `documento`.
- Ativo: `isActive`, `ativo`.
- Observacao: `notes`, `observacao`, `observation`.

Default atual:

- `isActive`/`ativo` ausente preserva `ativo=True`.

Payload de sucesso do `GET`:

Status `200`:

```json
{
  "creditors": [],
  "credores": [],
  "meta": {
    "count": 0,
    "onlyActive": true,
    "source": "cadastro_credor"
  },
  "permissions": {
    "canCreate": false
  }
}
```

Shape de cada item de `creditors`:

- `id`
- `value`
- `label`
- `name`
- `credor_id`
- `creditorId`
- `credor_nome`
- `creditorName`
- `document`
- `isActive`
- `notes`
- `observacao`
- `createdAt`
- `criado_em`
- `updatedAt`
- `atualizado_em`

Filtros do `GET`:

- Por padrao lista somente credores ativos.
- `includeInactive` truthy inclui credores inativos.
- Valores truthy atuais: `1`, `true`, `sim`, `yes`, `all`, `todos`.
- Ordenacao atual: `nome`, `id`.

Payload de sucesso do `POST`:

Status `201`:

```json
{
  "data": {
    "creditor": {},
    "message": "Credor cadastrado com sucesso."
  }
}
```

`data.creditor` usa o mesmo shape dos itens de `creditors`.

Erros de validacao:

```json
{"errors": ...}
```

com status `400`.

Principais validacoes atuais:

- `nome` e obrigatorio.
- `nome` sofre trim.
- `nome` e unico de forma case-insensitive.
- `documento` sofre trim.
- limites de campos do model sao aplicados por `full_clean()`.

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- `405` atual e JSON manual.
- `405` atual nao define header `Allow`.
- Falha de CSRF acontece antes da view e preserva comportamento Django atual.

Efeitos de dominio do `POST`:

- Cria um registro `Credor`.
- Define `criado_por` e `atualizado_por` com `request.user`.
- Nao cria divida financeira.
- Nao cria parcela.
- Nao cria obrigacao financeira.
- Nao cria baixa financeira.
- Nao cria lancamento financeiro.

Testes existentes relacionados:

- rota em `UrlsTests`;
- anonimo `401` em testes de seguranca;
- sem permissao `403` em testes de permissoes financeiras;
- GET lista ativos;
- GET `includeInactive`;
- GET `permissions.canCreate`;
- POST sucesso;
- POST sem `add_credor`;
- POST duplicado case-insensitive.

## Riscos especificos de credores FCF

- DRF pode substituir `401` e `403` atuais por respostas padrao.
- DRF pode alterar `405` JSON manual para `405` padrao com header `Allow`.
- DRF pode parsear `request.data` antes da view e mudar o erro atual de JSON
  invalido.
- DRF pode transformar Content-Type invalido em erro padrao diferente do `415`
  atual.
- A permissao global `view_credor` no decorator externo pode ser perdida no
  `POST`.
- A permissao adicional `add_credor` pode ser confundida com a permissao do
  `GET`.
- Aliases legados podem ser removidos se houver serializer DRF novo.
- O default `ativo=True` pode mudar se o payload nao trouxer `isActive`.
- `Cache-Control`/`no-store` pode ser perdido se a resposta mudar.
- OpenAPI pode ficar generico sem serializer DRF, mas isso nao deve motivar
  alteracao runtime.

## Guardrails

- Nao agrupar com FCF.
- Nao agrupar com dividas.
- Nao agrupar com parcelas.
- Nao agrupar com endpoints financeiros.
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
- Nao alterar model `Credor`.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar signals.
- Reaproveitar `_is_json_request`.
- Reaproveitar `_payload_json`.
- Reaproveitar `_first_payload_value`.
- Reaproveitar `_text_payload_value`.
- Reaproveitar `_bool_payload_value`.
- Reaproveitar `_credores_queryset_para_request`.
- Reaproveitar `_credor_from_payload`.
- Reaproveitar `_api_criar_credor_financiamento` quando possivel.
- Reaproveitar `serializar_credor_financiamento`.
- Reaproveitar `montar_payload_credores_financiamentos_api`.
- Preservar permissoes manuais por metodo.
- Preservar `405` JSON manual sem `Allow`.
- Priorizar paridade runtime sobre schema OpenAPI.

## PM-23.1 - Diagnostico read-only

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
- Campos retornados e aliases aceitos identificados.
- Efeitos colaterais do `POST` identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum arquivo alterado.

## PM-23.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

Criar ou reforcar testes para `GET`:

- anonimo retorna `401` com JSON atual;
- autenticado sem `caixa.view_credor` retorna `403` com JSON atual;
- autenticado com `caixa.view_credor` retorna `200`;
- shape completo do payload:
  - `creditors`;
  - `credores`;
  - `meta`;
  - `permissions`;
- shape completo de cada credor;
- filtro padrao lista somente ativos;
- `includeInactive` truthy inclui inativos;
- `permissions.canCreate` reflete `caixa.add_credor`;
- headers JSON/no-store em `200`, `401` e `403`.

Criar ou reforcar testes para `POST`:

- sem CSRF valido usando `Client(enforce_csrf_checks=True)` bloqueia antes da
  view;
- com CSRF valido chega na view;
- anonimo retorna `401` quando a requisicao chega na view;
- autenticado sem `caixa.view_credor` retorna `403`;
- autenticado com `caixa.view_credor`, mas sem `caixa.add_credor`, retorna
  `403`;
- Content-Type invalido retorna `415`;
- JSON invalido retorna `400`;
- body JSON nao-dict retorna `400`;
- nome vazio retorna `400` com `{"errors": ...}`;
- nome duplicado case-insensitive retorna erro atual;
- sucesso retorna `201` com `data.creditor` e `data.message`;
- shape completo de `data.creditor`;
- aliases de payload preservados:
  - `name`, `nome`;
  - `document`, `documento`;
  - `isActive`, `ativo`;
  - `notes`, `observacao`, `observation`;
- default de `isActive=True` preservado;
- `criado_por` e `atualizado_por` preservados;
- confirmar que POST cria apenas `Credor`;
- confirmar que POST nao cria divida, parcela, obrigacao, baixa ou lancamento
  financeiro;
- headers JSON/no-store em `201`, `400`, `401`, `403` e `415`.

Criar ou reforcar testes para metodos nao permitidos:

- `PUT`, `PATCH` e `DELETE` retornam `405`;
- payload do `405` e `{"detail": "Metodo nao permitido."}`;
- ausencia de header `Allow` preservada;
- headers JSON/no-store em `405`.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_credores_fcf>
```

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.
- Nenhuma alteracao em FCF, dividas, parcelas ou endpoints financeiros.

## PM-23.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_credores_financiamentos` para DRF com paridade
comprovada.

Implementacao esperada:

- converter somente `api_credores_financiamentos`;
- usar `@api_view(["GET", "POST"])`;
- usar `Response` somente na borda;
- preservar permissao manual por metodo:
  - `GET`: `caixa.view_credor`;
  - `POST`: `caixa.view_credor` e `caixa.add_credor`;
- preservar `401` e `403` atuais;
- preservar CSRF real no `POST`;
- preservar `415`;
- preservar `400` de JSON invalido;
- preservar `{"errors": ...}` de validacao;
- preservar `200` de listagem;
- preservar `201` de criacao;
- preservar `405` JSON manual;
- preservar ausencia de header `Allow` no `405`;
- preservar `Cache-Control`/`no-store`;
- reaproveitar helpers atuais da view;
- reaproveitar serializer manual atual;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao mexer em FCF, dividas, parcelas ou endpoints financeiros.

Regras:

- Manter URL `/api/fcf/creditors/`.
- Manter nome de rota `caixa:api_credores_financiamentos`.
- Manter metodos `GET` e `POST`.
- Manter status HTTP.
- Manter JSON de sucesso.
- Manter JSONs de erro.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `405` manual sem `Allow`.
- Manter CSRF real no `POST`.
- Manter permissoes atuais por metodo.
- Manter CORS sem alteracao.
- Nao deixar DRF substituir erros atuais por erros padrao.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_credores_fcf>
```

Gate de saida:

- `/api/fcf/creditors/` migrado para DRF.
- `GET` mantem paridade.
- `POST` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-23.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_credores_fcf>
python manage.py test <testes_relacionados_de_fcf>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/fcf/creditors/`;
- nenhuma regressao;
- FCF nao foi alterado alem do endpoint de credores;
- dividas nao foram alteradas;
- parcelas nao foram alteradas;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado a `/api/fcf/creditors/`, testes e registro do plano;
- FCF, dividas e parcelas nao alterados;
- helpers atuais reaproveitados;
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

## PM-23.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-23 antes de avancar para outro
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
- Confirmar que FCF, dividas, parcelas e endpoints financeiros nao foram
  alterados.
- Confirmar que nenhum outro endpoint foi migrado.
- Confirmar que frontend nao foi alterado.
- Confirmar que settings, CORS, CSRF global e auth global nao foram alterados.
- Registrar riscos residuais.
- Registrar recomendacao: pronto, ajustar ou reverter.

Proximo passo natural, somente se PM-23 estiver estavel:

- retomar o roadmap e escolher o proximo endpoint de menor risco, mantendo
  diagnostico read-only antes de qualquer migracao.

## Criterios globais de aceite

- `GET /api/fcf/creditors/` mantem paridade.
- `POST /api/fcf/creditors/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodos `GET` e `POST` preservados.
- Status HTTP preservados.
- JSON de sucesso preservado.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- `405` JSON manual preservado.
- Ausencia de `Allow` no `405` preservada.
- Permissao `caixa.view_credor` preservada no `GET`.
- Permissoes `caixa.view_credor` e `caixa.add_credor` preservadas no `POST`.
- CSRF real preservado no `POST`.
- Content-Type atual preservado.
- JSON invalido atual preservado.
- Campos e aliases legados preservados.
- Default de `isActive=True` preservado.
- POST cria somente `Credor`.
- POST nao cria divida, parcela, obrigacao, baixa ou lancamento financeiro.
- Frontend nao alterado.
- FCF, dividas, parcelas e endpoints financeiros nao alterados.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/fcf/creditors/`.
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
- usuario com `view_credor` mas sem `add_credor` receber contrato diferente no
  `POST`;
- `405` deixar de ser JSON manual;
- header `Allow` aparecer no `405`;
- Content-Type invalido deixar de retornar `415` atual;
- JSON invalido deixar de retornar `400` atual;
- body nao-dict deixar de retornar `400` atual;
- erros de validacao deixarem de retornar `{"errors": ...}`;
- aliases legados forem removidos;
- default de `ativo=True` mudar;
- POST criar divida, parcela, obrigacao, baixa ou lancamento financeiro;
- outro endpoint precisar ser alterado;
- FCF, dividas, parcelas ou endpoints financeiros precisarem ser alterados;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar settings, CORS, CSRF global ou auth global.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_credores_financiamentos`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_credores_financiamentos`.
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

### Registro de execucao - PM-23.1

Status: concluida.

Fase: diagnostico read-only.

Endpoint alvo:

- `GET/POST /api/fcf/creditors/`

Arquivos lidos:

- `caixa/views_financiamentos.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/models_dividas.py`
- `caixa/serializers_financiamentos.py`
- `caixa/selectors_opcoes_filtros.py`
- `caixa/tests.py`

Resultado:

- Contrato atual de `/api/fcf/creditors/` mapeado.
- View ainda estava Django puro.
- Permissoes por metodo identificadas.
- CSRF real no `POST` identificado.
- Content-Type e JSON invalido identificados.
- `405` JSON manual sem `Allow` identificado.
- Shape de sucesso e erro identificado.
- Campos e aliases identificados.
- Efeitos de dominio identificados.
- Lacunas de paridade identificadas.
- Nenhum arquivo alterado nesta fase.

### Registro de execucao - PM-23.2

Status: concluida.

Fase: congelamento de contrato em testes.

Arquivo alterado:

- `caixa/tests.py`

Testes criados ou reforcados:

- `FiltrosHtmlTests.test_api_credores_financiamentos_retorna_cadastro_ativo_para_frontend`
  - reforcado para congelar shape completo do GET;
  - congela `creditors`, `credores`, `meta`, `permissions`;
  - congela shape completo de cada credor;
  - congela ordenacao por `nome`, `id`;
  - congela somente ativos por padrao;
  - congela headers JSON/no-store.
- `FiltrosHtmlTests.test_api_credores_financiamentos_include_inactive_para_tela_mestre`
  - reforcado para congelar valores truthy de `includeInactive`:
    `1`, `true`, `sim`, `yes`, `all`, `todos`;
  - congela inclusao de inativos e `meta.onlyActive == false`.
- `FiltrosHtmlTests.test_api_credores_financiamentos_informa_permissao_de_cadastro`
  - reforcado para congelar `permissions.canCreate` e headers.
- `FiltrosHtmlTests.test_api_credores_financiamentos_post_cria_credor`
  - reforcado para congelar `201`;
  - congela shape completo de `data.creditor`;
  - congela `data.message`;
  - congela `criado_por` e `atualizado_por`;
  - congela ausencia de criacao de divida, parcela, obrigacao, baixa e
    lancamento financeiro.
- `FiltrosHtmlTests.test_api_credores_financiamentos_post_exige_add_credor`
  - reforcado para congelar `403`, JSON atual e headers.
- `FiltrosHtmlTests.test_api_credores_financiamentos_post_valida_nome_duplicado`
  - reforcado para congelar erro de nome duplicado case-insensitive e headers.
- `FiltrosHtmlTests.test_api_credores_financiamentos_get_preserva_auth_permissao_e_headers`
  - criado para congelar `401` anonimo;
  - criado para congelar `403` sem `view_credor`;
  - congela headers JSON/no-store.
- `FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_csrf_auth_e_permissoes`
  - criado para congelar CSRF real bloqueando sem token;
  - criado para confirmar que CSRF valido chega na view;
  - congela `401` anonimo;
  - congela `403` sem `view_credor`;
  - congela `403` com `view_credor` mas sem `add_credor`.
- `FiltrosHtmlTests.test_api_credores_financiamentos_post_erros_de_payload_preservam_contrato`
  - criado para congelar Content-Type invalido `415`;
  - criado para congelar JSON invalido `400`;
  - criado para congelar body nao-dict `400`;
  - criado para congelar nome vazio em `{"errors": ...}`;
  - congela headers JSON/no-store.
- `FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_aliases_defaults_e_efeitos`
  - criado para congelar aliases `nome`, `documento`, `observacao`,
    `ativo`, `name`, `document`, `observation`;
  - congela default de `ativo=True`;
  - congela criacao somente de `Credor`;
  - congela ausencia de efeitos financeiros.
- `FiltrosHtmlTests.test_api_credores_financiamentos_metodos_nao_permitidos_preservam_405`
  - criado para congelar `PUT`, `PATCH` e `DELETE` como `405`;
  - congela payload `{"detail": "Metodo nao permitido."}`;
  - congela ausencia de header `Allow`;
  - congela headers JSON/no-store.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_retorna_cadastro_ativo_para_frontend caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_include_inactive_para_tela_mestre caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_informa_permissao_de_cadastro caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_cria_credor caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_exige_add_credor caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_valida_nome_duplicado caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_get_preserva_auth_permissao_e_headers caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_csrf_auth_e_permissoes caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_aliases_defaults_e_efeitos caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_metodos_nao_permitidos_preservam_405
```

Variaveis locais usadas nos comandos:

```bash
DEBUG=True
SECRET_KEY=local-validation-secret
```

Resultados:

- `check`: OK, sem issues.
- Testes focados: 11 testes executados, todos OK.
- Nenhuma view foi migrada nesta fase.
- Nenhuma alteracao em FCF, dividas, parcelas ou endpoints financeiros.

### Registro de execucao - PM-23.3

Status: concluida.

Fase: migracao controlada para DRF.

Arquivo alterado:

- `caixa/views_financiamentos.py`

Implementacao:

- `api_credores_financiamentos` foi migrada para DRF com
  `@api_view(["GET", "POST"])`.
- `JsonBodySafeSessionAuthentication` foi reaproveitado para preservar CSRF
  real e evitar que DRF substitua o contrato de JSON invalido.
- `AllowAny` foi usado localmente para impedir que a permissao global do DRF
  substitua `401`/`403` atuais.
- `require_api_permission(FINANCIAL_CREDITORS_PERMISSION)` foi preservado por
  fora da view DRF para manter `view_credor` no `GET` e no `POST`.
- A permissao `add_credor` foi preservada em `_api_criar_credor_financiamento`.
- `Response` passou a ser usado somente na borda deste endpoint.
- Respostas continuam sendo montadas a partir dos `JsonResponse` atuais, com
  copia de `Cache-Control` e `Expires`.
- `_preservar_metodo_manual_credores_fcf` foi criado localmente e somente para
  este endpoint para preservar o `405` JSON manual sem `Allow`, porque o
  `405` padrao do DRF mudaria o contrato.
- `_credores_queryset_para_request` foi reaproveitado.
- `_api_criar_credor_financiamento` foi reaproveitado.
- `serializar_credor_financiamento` foi reaproveitado.
- `montar_payload_credores_financiamentos_api` foi reaproveitado.

Nao alterado:

- `GET/POST /api/fcf/`.
- `POST /api/fcf/debts/`.
- Dividas.
- Parcelas.
- Pagamentos FCF.
- Obrigacoes financeiras.
- Baixas financeiras.
- Lancamentos financeiros.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Model `Credor`.
- Services.
- Selectors.
- Serializers manuais.
- Serializer DRF, ViewSet ou ModelViewSet.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_retorna_cadastro_ativo_para_frontend caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_include_inactive_para_tela_mestre caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_informa_permissao_de_cadastro caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_cria_credor caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_exige_add_credor caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_valida_nome_duplicado caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_get_preserva_auth_permissao_e_headers caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_csrf_auth_e_permissoes caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_aliases_defaults_e_efeitos caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_metodos_nao_permitidos_preservam_405
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados.
- OpenAPI inclui `/api/fcf/creditors/`.
- Testes focados: 11 testes executados, todos OK.

### Registro de execucao - PM-23.4

Status: concluida.

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_retorna_cadastro_ativo_para_frontend caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_include_inactive_para_tela_mestre caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_informa_permissao_de_cadastro caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_cria_credor caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_exige_add_credor caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_valida_nome_duplicado caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_get_preserva_auth_permissao_e_headers caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_csrf_auth_e_permissoes caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_erros_de_payload_preservam_contrato caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_post_preserva_aliases_defaults_e_efeitos caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_metodos_nao_permitidos_preservam_405
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados.
- Testes focados de credores FCF: 11 testes executados, todos OK.
- Testes relacionados de `FiltrosHtmlTests`: 372 testes executados, todos OK.
- Suite completa: 730 testes executados, todos OK.
- Warnings de log durante a suite completa ficaram limitados a cenarios
  esperados de CSRF/login/logout e AXES ja cobertos por testes.
- `schema.yml` nao foi gerado nesta PM.
- Nenhuma regressao identificada.

### Registro de execucao - PM-23.5

Status: concluida.

Fase: encerramento.

Arquivos alterados pela PM-23:

- `caixa/tests.py`
- `caixa/views_financiamentos.py`
- `docs/PLANO_PM23_MIGRACAO_CREDORES_FCF_DRF.md`

Dependencias adicionadas:

- Nenhuma.

Endpoint migrado:

- `GET/POST /api/fcf/creditors/`

Endpoints explicitamente nao alterados:

- `GET/POST /api/fcf/`.
- `POST /api/fcf/debts/`.
- Dividas.
- Parcelas.
- Pagamentos FCF.
- Obrigacoes financeiras.
- Baixas financeiras.
- Lancamentos financeiros.
- Demais endpoints financeiros.

Confirmacoes finais:

- URL preservada.
- Nome de rota `caixa:api_credores_financiamentos` preservado.
- Metodos `GET` e `POST` preservados.
- `401`, `403`, `415`, `400`, `200`, `201` e `405` preservados pelos testes.
- `405` JSON manual preservado.
- Ausencia de header `Allow` no `405` preservada.
- JSONs de erro preservados.
- Shape de sucesso do GET preservado.
- Shape de sucesso do POST preservado.
- Aliases de payload preservados.
- Default de `isActive=True` preservado.
- `criado_por` e `atualizado_por` preservados.
- POST cria somente `Credor`.
- POST nao cria divida, parcela, obrigacao, baixa ou lancamento financeiro.
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
- O pequeno guard local `_preservar_metodo_manual_credores_fcf` existe apenas
  para manter o `405` manual sem `Allow`; ele deve ser removido somente se o
  contrato do endpoint for alterado conscientemente em PM futura.

Recomendacao:

- PM-23 pronta para commit local manual.
