# Plano PM-16 - Migracao incremental de `POST /api/orcamentos/<id>/aprovar/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `POST /api/orcamentos/<id>/aprovar/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js.

DRF deve entrar apenas como casca HTTP do endpoint de aprovacao de orcamento,
sem mudar regra de negocio, helpers, services, selectors, models, calculos
financeiros, efeitos colaterais ou contrato JSON.

Esta PM cobre somente:

- `POST /api/orcamentos/<id>/aprovar/`

## Escopo

- Congelar o contrato atual em testes antes da migracao.
- Migrar apenas a view `api_aprovar_orcamento`.
- Usar `@api_view(["POST"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar autenticacao por sessao Django.
- Preservar CSRF real no `POST`.
- Preservar permissao atual `caixa.change_orcamento`.
- Preservar exigencia de superuser como regra de negocio com status `400`.
- Preservar status HTTP, JSON, headers e efeitos colaterais atuais.
- Preservar `404` Django padrao para orcamento inexistente.
- Nao exigir `application/json`.
- Nao parsear JSON do body.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET`/`POST /api/orcamentos/`, ja tratado na PM-14.
- `GET`/`PUT /api/orcamentos/<id>/`, ja tratado na PM-15.
- Eventos.
- Clientes.
- Custos extras de eventos fora dos efeitos atuais da aprovacao.
- Endpoints financeiros fora dos efeitos atuais da aprovacao.
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
- 1 PM = um grupo pequeno e coeso quando o contrato for simples.

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

## Contrato atual identificado na PM-16.1

Arquivo atual:

- `caixa/views_orcamentos_api.py`

View atual:

- `api_aprovar_orcamento`

Rota atual:

- `path("api/orcamentos/<int:pk>/aprovar/", api_aprovar_orcamento, name="api_aprovar_orcamento")`

Nome da rota:

- `caixa:api_aprovar_orcamento`

Decoradores atuais:

- `@require_POST`
- `@require_api_permission(CHANGE_BUDGET_PERMISSION)`

Metodo aceito:

- `POST`

Metodos nao permitidos:

- `GET`, `PUT`, `PATCH`, `DELETE` e demais metodos fora do contrato retornam
  `405` pelo decorator do Django.
- O header `Allow` esperado deve ser congelado em teste, especialmente `POST`.

Permissao atual:

- `CHANGE_BUDGET_PERMISSION = "caixa.change_orcamento"`

Regra adicional de negocio:

- alem da permissao, `aprovar_orcamento_como_superuser` exige
  `request.user.is_superuser`;
- usuario com `change_orcamento`, mas nao superuser, recebe `400`, nao `403`.

Comportamento para usuario anonimo quando a requisicao chega na view:

```json
{"detail": "Authentication credentials were not provided."}
```

Comportamento para usuario autenticado sem `caixa.change_orcamento`:

```json
{"detail": "Permission denied."}
```

Comportamento para usuario com `change_orcamento`, mas nao-superuser:

```json
{"detail": "Apenas superusuarios podem aprovar orcamentos por esta tela."}
```

Observacao:

- A mensagem real tem acentos no runtime atual. Os testes de paridade devem
  congelar a string exata retornada pela aplicacao.

CSRF no `POST`:

- A view atual e Django puro e nao usa `csrf_exempt`.
- `POST` sem CSRF valido deve ser bloqueado pelo middleware antes da view quando
  testado com `Client(enforce_csrf_checks=True)`.
- `POST` com CSRF valido deve seguir para autenticacao, permissao, regra de
  superuser, 404, validacao de aprovacao ou sucesso.

Content-Type:

- A view atual nao le `request.body`.
- Nao exige `application/json`.
- `Content-Type` nao JSON deve continuar aceito se CSRF, autenticacao e
  permissao estiverem validos.

JSON invalido:

- O body nao e parseado.
- JSON invalido deve continuar ignorado.
- JSON invalido nao deve virar `400` por parse de DRF.

Orcamento inexistente:

- Depois de autenticacao e permissao, usa
  `get_object_or_404(_budget_queryset(), pk=pk)`.
- Com permissao valida, retorna `404` Django padrao.
- Nao converter para JSON se esse nao for o comportamento atual.

Regras de aprovacao:

- `require_api_permission` exige `caixa.change_orcamento`.
- `aprovar_orcamento_como_superuser` exige `user.is_superuser`.
- Se nao for superuser, retorna:

```json
{"detail": "Apenas superusuarios podem aprovar orcamentos por esta tela."}
```

- Se for superuser, chama `aprovar_orcamento`.
- `aprovar_orcamento` chama `orcamento.aprovar_e_gerar_evento()`.

Regras de bloqueio:

- orcamento sem `pk` gera erro;
- orcamento sem itens gera erro;
- erros em `full_clean`, criacao/atualizacao de evento, movimentacoes ou
  sincronizacoes sao capturados por `aprovar_orcamento` e retornam `400` com
  `detail`;
- usuario com permissao, mas sem superuser, recebe `400` com `detail`;
- CSRF invalido bloqueia antes da view com `403`.

Criacao/atualizacao do evento aprovado:

- `Orcamento.aprovar_e_gerar_evento()` recalcula totais;
- altera `orcamento.status` para `aprovado`;
- salva o orcamento;
- chama `criar_ou_atualizar_evento_do_orcamento`;
- cria ou atualiza `Evento` vinculado por `orcamento`;
- usa numero `EVT-{orcamento.numero}` quando cria o evento;
- sincroniza cliente, nome, datas, local, observacoes e totais previstos.

Efeitos colaterais principais:

- orcamento vira `aprovado`;
- evento e criado ou atualizado;
- receita prevista do evento e criada quando aplicavel;
- despesas previstas sao criadas quando aplicavel;
- custos de servico do evento sao sincronizados;
- custos extras do evento sao sincronizados;
- `OrcamentoCustoExtra.evento_custo_extra` pode ser vinculado;
- signals de `EventoCustoServico`, `EventoCustoExtra`, `ReceitaOperacional` e
  `DespesaOperacional` podem sincronizar lancamentos, obrigacoes, baixas
  canonicas e recalculos financeiros;
- reaprovar deve atualizar/reaproveitar o evento existente, sem duplicar.

Payload de sucesso:

```json
{
  "data": {
    "budget": {},
    "event": {
      "id": 1,
      "contract": "ORC-API-APROVAR",
      "number": "EVT-ORC-API-APROVAR",
      "name": "Evento API Aprovar"
    },
    "message": "Contrato ORC-API-APROVAR aprovado. Evento ORC-API-APROVAR gerado/atualizado."
  }
}
```

Campos esperados de `data.budget`:

- mesmos campos de `_serialize_orcamento`;
- o status deve refletir `aprovado` apos sucesso.

Campos esperados de `data.event`:

- `id`
- `contract`
- `number`
- `name`

Payloads de erro:

Autenticacao:

```json
{"detail": "Authentication credentials were not provided."}
```

Permissao:

```json
{"detail": "Permission denied."}
```

Regra de aprovacao:

```json
{"detail": "..."}
```

404:

- Django padrao HTML.

Status codes atuais:

- `200`: sucesso;
- `400`: regra de aprovacao falha;
- `401`: anonimo;
- `403`: sem permissao ou CSRF invalido;
- `404`: orcamento inexistente;
- `405`: metodo nao permitido.

Headers relevantes:

- Respostas JSON usam `Content-Type: application/json`.
- Respostas JSON usam `Cache-Control` com `no-store`.
- Respostas `405` devem preservar o header `Allow`.
- `404` Django padrao e falhas de CSRF devem preservar o comportamento atual.

Transacoes:

- a view nao usa `transaction.atomic`;
- `aprovar_orcamento_como_superuser` nao usa `transaction.atomic`;
- `aprovar_orcamento` nao usa `transaction.atomic`;
- `Orcamento.aprovar_e_gerar_evento` nao envolve toda a aprovacao em
  transacao explicita;
- ha transacoes internas em rotinas relacionadas do dominio, mas nao cobrindo a
  aprovacao inteira como unidade atomica.

Signals, tasks e integracoes:

- nao ha task assincrona/Celery identificada no fluxo atual;
- signals podem ser acionados por saves em:
  - `EventoCustoServico`;
  - `EventoCustoExtra`;
  - `ReceitaOperacional`;
  - `DespesaOperacional`;
- esses signals sincronizam financeiro/canonico, lancamentos, obrigacoes,
  baixas e recalculos.

Helpers atuais que devem ser reaproveitados:

- `_budget_queryset`
- `_serialize_orcamento`
- `api_no_store_json_response`
- `api_authentication_required_response`, ou resposta equivalente
- `api_permission_denied_response`, ou resposta equivalente
- `aprovar_orcamento_como_superuser`

## Riscos especificos da aprovacao

- A aprovacao e uma mutation com multiplos efeitos colaterais.
- O fluxo cria ou atualiza evento operacional.
- O fluxo altera status do orcamento para `aprovado`.
- O fluxo pode criar receita prevista e despesas previstas.
- O fluxo sincroniza custos de servico e custos extras.
- O fluxo pode disparar signals financeiros/canonicos.
- O fluxo atual nao e atomicamente encapsulado de ponta a ponta.
- DRF pode tentar parsear JSON invalido e mudar o contrato, se a view acessar
  `request.data`.
- DRF pode trocar `401`, `403`, `404` ou `405` por respostas padrao se a
  migracao nao preservar controles locais.
- DRF pode exigir `application/json` indevidamente se a migracao usar parser ou
  serializer sem necessidade.
- A regra de superuser deve permanecer como regra de negocio retornando `400`,
  nao permissao HTTP `403`.
- Reaprovacao nao pode duplicar evento nem duplicar movimentacoes/custos.

## Guardrails

- Nao migrar `GET`/`POST /api/orcamentos/` novamente.
- Nao migrar `GET`/`PUT /api/orcamentos/<id>/` novamente.
- Nao alterar eventos, clientes ou endpoints financeiros fora dos efeitos
  atuais da aprovacao.
- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao criar serializer DRF inicialmente.
- Nao mover regra de aprovacao para serializer, permissao DRF generica ou
  frontend.
- Nao alterar services, selectors, helpers ou regra de negocio.
- Nao alterar JSON, status HTTP ou headers para melhorar OpenAPI.
- Nao acessar `request.data`.
- Nao exigir `application/json`.
- Nao parsear body JSON.
- Reaproveitar helpers atuais sempre que possivel.
- Usar permissao manual para `caixa.change_orcamento`.
- Manter superuser como regra de negocio com `400`.
- Usar `AllowAny` local somente se necessario para impedir respostas padrao do
  DRF e manter os JSONs atuais.
- Reaproveitar `JsonBodySafeSessionAuthentication` se necessario para preservar
  CSRF em `POST`, sem alterar autenticacao global.
- Preservar 404 Django padrao para orcamento inexistente.

## PM-16.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas realizadas:

- View atual identificada.
- URL e nome da rota identificados.
- Metodo aceito identificado.
- Permissao identificada.
- Regra de superuser identificada.
- Comportamento de usuario anonimo identificado.
- Comportamento de usuario sem permissao identificado.
- CSRF atual identificado.
- Content-Type identificado como nao exigido.
- JSON invalido identificado como ignorado.
- Comportamento de orcamento inexistente identificado.
- Regras de aprovacao e bloqueio identificadas.
- Efeitos colaterais identificados.
- Signals/integracoes identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum codigo runtime alterado.

## PM-16.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

Criar ou reforcar testes para:

- `POST` anonimo retorna `401` com JSON atual;
- `POST` autenticado sem `caixa.change_orcamento` retorna `403` com JSON atual;
- usuario com `caixa.change_orcamento`, mas nao-superuser, retorna `400`;
- superuser com sucesso retorna `200`;
- `POST` sem CSRF valido bloqueia antes da view com
  `Client(enforce_csrf_checks=True)`;
- `POST` com CSRF valido chega na view;
- orcamento inexistente preserva `404` Django padrao;
- orcamento sem itens retorna `400` com `detail` atual;
- `GET`, `PUT`, `PATCH` e `DELETE` retornam `405`;
- header `Allow` preservado, especialmente `POST`;
- `Content-Type` nao JSON continua aceito;
- JSON invalido continua ignorado;
- sucesso contem `data.budget`;
- sucesso contem `data.event`;
- sucesso contem `data.message`;
- `data.budget` mantem shape de `_serialize_orcamento`;
- `data.event` contem `id`, `contract`, `number`, `name`;
- headers JSON/no-store em `200`, `400`, `401` e `403`;
- efeitos colaterais principais:
  - orcamento aprovado;
  - evento criado ou atualizado;
  - movimentacoes/custos sincronizados;
- reaprovar nao duplica evento.

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_aprovacao_orcamento>
```

## PM-16.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_aprovar_orcamento` para DRF com paridade
comprovada.

Implementacao esperada:

- converter apenas a view `api_aprovar_orcamento`;
- usar `@api_view(["POST"])`;
- usar `Response` somente na borda;
- manter helpers atuais;
- manter permissao manual `caixa.change_orcamento`;
- manter regra de superuser como regra de negocio com `400`;
- manter CSRF real no `POST`;
- preservar 404 Django padrao;
- nao exigir `application/json`;
- nao parsear JSON;
- nao acessar `request.data`;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao alterar contrato.

Regras:

- Manter URL `/api/orcamentos/<id>/aprovar/`.
- Manter nome de rota `caixa:api_aprovar_orcamento`.
- Manter metodo `POST`.
- Manter status HTTP.
- Manter JSON.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow` do `405`.
- Manter permissao `caixa.change_orcamento`.
- Manter autenticacao por sessao Django.
- Manter CSRF real em `POST`.
- Manter CORS sem alteracao.
- Reaproveitar `aprovar_orcamento_como_superuser`.
- Reaproveitar `_serialize_orcamento`.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- O DRF nao deve trocar os JSONs atuais de `401`, `403`, `400` ou `405`.
- O DRF nao deve trocar o `404` Django padrao por resposta JSON.
- DRF nao deve parsear body invalido.
- DRF nao deve exigir `application/json`.
- Se `SessionAuthentication` interferir no comportamento de CSRF ou erros
  atuais, ajustar localmente sem alterar configuracao global.
- Se for necessario usar classe local ja existente, reaproveitar sem duplicar.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_aprovacao_orcamento>
```

Gate de saida:

- `/api/orcamentos/<id>/aprovar/` migrado para DRF.
- `POST` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-16.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_aprovacao_orcamento>
python manage.py test caixa.tests.OrcamentosApiTests
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/orcamentos/{id}/aprovar/`;
- nenhuma regressao;
- `GET`/`POST /api/orcamentos/` nao foi alterado novamente;
- `GET`/`PUT /api/orcamentos/<id>/` nao foi alterado novamente;
- eventos, clientes e financeiro nao foram alterados fora dos efeitos atuais da
  aprovacao;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint `/api/orcamentos/<id>/aprovar/`, testes e registro
  do plano;
- `POST /api/orcamentos/<id>/aprovar/` preservado;
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

## PM-16.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-16 antes de avancar para endpoints
financeiros ou outra PM.

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

Proximo passo natural, somente se PM-16 estiver estavel:

- revisar sequenciamento antes de iniciar endpoints financeiros.

## Criterios globais de aceite

- `POST /api/orcamentos/<id>/aprovar/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodo preservado.
- Status HTTP preservados.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow` preservado nos `405`.
- 404 Django padrao preservado.
- Autenticacao por sessao Django preservada.
- CSRF real preservado no `POST`.
- CORS preservado.
- Permissao `caixa.change_orcamento` preservada.
- Regra de superuser com `400` preservada.
- `Content-Type` nao JSON continua aceito.
- JSON invalido continua ignorado.
- Efeitos colaterais de aprovacao preservados.
- Reaprovacao nao duplica evento.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/orcamentos/{id}/aprovar/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- header relevante mudar;
- CSRF mudar;
- CORS mudar;
- permissao mudar;
- regra de superuser mudar para `403`;
- usuario anonimo receber contrato diferente;
- usuario sem permissao receber contrato diferente;
- orcamento inexistente receber contrato diferente;
- `Content-Type` passar a ser exigido;
- JSON invalido passar a gerar erro de parse;
- evento aprovado for duplicado;
- movimentacoes/custos forem duplicados;
- efeitos colaterais de aprovacao mudarem;
- frontend precisar ser alterado;
- `GET`/`POST /api/orcamentos/` precisar ser alterado novamente;
- `GET`/`PUT /api/orcamentos/<id>/` precisar ser alterado novamente;
- outro endpoint precisar ser alterado;
- DRF gerar resposta padrao diferente para `401`, `403`, `400`, `404` ou
  `405`;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar services, selectors ou models.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_aprovar_orcamento`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_aprovar_orcamento`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

Se efeitos colaterais divergirem:

- Parar a PM.
- Reverter a migracao runtime.
- Manter testes que detectaram a divergencia.
- Registrar exatamente qual efeito divergiu, por exemplo evento duplicado,
  status incorreto, movimentacao ausente ou custo duplicado.

## Registro de execucao

### Registro de execucao - PM-16.1

Fase: diagnostico read-only.

Endpoint alvo:

- `POST /api/orcamentos/<id>/aprovar/`

Arquivos lidos:

- `caixa/views_orcamentos_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/services_cadastros.py`
- `caixa/models.py`
- `caixa/services_orcamentos.py`
- `caixa/services_evento.py`
- `caixa/signals.py`
- `caixa/tests.py`

Resultado:

- Contrato atual mapeado.
- View ainda estava Django puro.
- Lacunas de paridade identificadas para autenticacao, permissao, superuser,
  CSRF, 404 Django padrao, metodos nao permitidos, Content-Type, JSON invalido,
  sucesso e efeitos colaterais.
- Nenhum arquivo runtime alterado nesta fase.

`git status --short` observado ao final da PM-16.1:

```text
```

### Registro de execucao - PM-16.2

Fase: congelamento de contrato em testes.

Endpoint alvo:

- `POST /api/orcamentos/<id>/aprovar/`

Arquivo alterado:

- `caixa/tests.py`

Testes criados:

- `test_api_aprovar_orcamento_preserva_auth_permissao_superuser_404_e_csrf`
- `test_api_aprovar_orcamento_preserva_content_type_json_invalido_sucesso_e_efeitos`
- `test_api_aprovar_orcamento_sem_itens_retorna_400_com_detail_atual`
- `test_api_aprovar_orcamento_reaprovacao_nao_duplica_evento`
- `test_api_aprovar_orcamento_metodos_nao_permitidos_preservam_405_e_allow`

Cobertura congelada:

- anonimo `401` com JSON atual;
- usuario autenticado sem `caixa.change_orcamento` `403` com JSON atual;
- usuario com `caixa.change_orcamento`, mas nao-superuser, `400`;
- CSRF real com `Client(enforce_csrf_checks=True)`;
- orcamento inexistente com `404` Django padrao;
- orcamento sem itens com `400` e `detail` atual;
- metodos `GET`, `PUT`, `PATCH` e `DELETE` com `405` e `Allow: POST`;
- `Content-Type` nao JSON aceito;
- JSON invalido ignorado;
- sucesso com `data.budget`, `data.event` e `data.message`;
- headers JSON/no-store;
- efeitos colaterais principais de aprovacao;
- reaprovar sem duplicar evento/custos.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
venv\Scripts\python.exe manage.py check
```

Resultado:

- `OrcamentosApiTests`: `27` testes, `OK`.
- `check`: sem issues.
- A primeira execucao dos testes apontou ajuste necessario no proprio teste de
  `GET` 405; corrigido antes de qualquer migracao runtime.
- Nenhuma view foi migrada nesta fase.
- Frontend, settings, CORS, CSRF global e auth global nao foram alterados.

### Registro de execucao - PM-16.3

Fase: migracao controlada para DRF.

Endpoint alvo:

- `POST /api/orcamentos/<id>/aprovar/`

Arquivo alterado:

- `caixa/views_orcamentos_api.py`

Implementacao:

- `api_aprovar_orcamento` foi migrada para DRF com `@api_view(["POST"])`.
- `@require_POST` foi preservado para manter `405` e `Allow: POST`.
- `JsonBodySafeSessionAuthentication` foi reaproveitada localmente para manter
  CSRF de sessao sem parsear body JSON.
- `AllowAny` foi usado localmente para preservar os JSONs manuais de `401` e
  `403`.
- A permissao `caixa.change_orcamento` continuou manual dentro da view.
- A regra de superuser continuou regra de negocio retornando `400`.
- `Response` foi usado somente na borda, convertendo os `JsonResponse`
  existentes.
- `404` Django padrao foi preservado com `page_not_found`.
- `request.data` nao foi acessado.
- `Content-Type` nao JSON continuou aceito.
- JSON invalido continuou ignorado.
- Foi adicionado `request=None` no `extend_schema` para refletir que o endpoint
  nao usa body e para remover erro de inferencia do drf-spectacular sem alterar
  runtime.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
```

Resultado:

- `check`: sem issues.
- `spectacular --validate`: validado, sem warnings/erros apos `request=None`.
- OpenAPI inclui `/api/orcamentos/{id}/aprovar/`.
- `OrcamentosApiTests`: `27` testes, `OK`.
- Nenhum outro endpoint foi migrado.
- `/api/orcamentos/` nao foi alterado.
- `/api/orcamentos/<id>/` nao foi alterado.
- Frontend, settings, CORS, CSRF global e auth global nao foram alterados.

### Registro de execucao - PM-16.4

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.OrcamentosApiTests
venv\Scripts\python.exe manage.py test
```

Resultado:

- `check`: sem issues.
- `spectacular --validate`: validado, sem warnings/erros.
- OpenAPI inclui `/api/orcamentos/{id}/aprovar/`.
- `OrcamentosApiTests`: `27` testes, `OK`.
- Suite completa: `704` testes, `OK`.

Warnings observados na suite completa:

- warnings esperados de testes existentes de CSRF em
  `/api/eventos/custos-extras/` e `/api/auth/logout/`;
- log esperado do django-axes em teste de falha de login.

Confirmacoes:

- `POST /api/orcamentos/<id>/aprovar/` manteve paridade runtime.
- `GET`/`POST /api/orcamentos/` nao foi alterado novamente.
- `GET`/`PUT /api/orcamentos/<id>/` nao foi alterado novamente.
- Nenhum serializer, ViewSet ou ModelViewSet foi criado.
- Nenhum `schema.yml` temporario foi gerado.
- Frontend, settings, CORS, CSRF global e auth global nao foram alterados.

### Registro de execucao - PM-16.5

Fase: encerramento.

Arquivos alterados na PM-16:

- `caixa/tests.py`
- `caixa/views_orcamentos_api.py`
- `docs/PLANO_PM16_MIGRACAO_APROVACAO_ORCAMENTO_DRF.md`

Dependencias adicionadas:

- Nenhuma nesta PM.

Rotas criadas:

- Nenhuma rota nova.

Endpoints migrados nesta PM:

- `POST /api/orcamentos/<id>/aprovar/`

Endpoints nao migrados nesta PM:

- `GET`/`POST /api/orcamentos/`
- `GET`/`PUT /api/orcamentos/<id>/`
- eventos;
- clientes;
- custos extras;
- endpoints financeiros.

Decisao sobre `schema.yml`:

- Nao foi gerado arquivo `schema.yml`; foi usado somente
  `spectacular --validate`.

Riscos residuais:

- A aprovacao continua sendo uma mutation com efeitos colaterais amplos e sem
  transacao atomica envolvendo todo o fluxo, como ja era antes da migracao.
- O schema OpenAPI segue generico (`object`) para preservar a prioridade da
  paridade runtime e evitar serializer DRF nesta PM.
- Signals financeiros/canonicos continuam sendo exercitados pelos testes, mas
  qualquer regra financeira futura deve continuar migrando com diagnostico e
  paridade propria.

Recomendacao:

- PM-16 pronta para commit local manual.
