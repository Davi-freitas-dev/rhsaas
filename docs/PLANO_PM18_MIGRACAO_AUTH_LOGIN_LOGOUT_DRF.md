# Plano PM-18 - Migracao incremental de `POST /api/auth/login/` e `POST /api/auth/logout/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar conjuntamente os endpoints de autenticacao restantes para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js:

- `POST /api/auth/login/`
- `POST /api/auth/logout/`

DRF deve entrar apenas como casca HTTP desses endpoints, sem alterar regra de
autenticacao, sessao Django, cookies, CSRF, payloads, status HTTP, headers ou
contrato do frontend.

## Escopo

- Congelar o contrato atual de login/logout em testes antes da migracao.
- Migrar apenas `api_auth_login` e `api_auth_logout`.
- Usar `@api_view(["POST"])`.
- Usar `Response` somente na borda.
- Preservar autenticacao por sessao Django.
- Preservar CSRF real em `POST`.
- Preservar `@never_cache`.
- Preservar `@sensitive_post_parameters("password")` e
  `@sensitive_variables("password")` no login.
- Preservar `AuthenticationForm`.
- Preservar `_user_payload`.
- Preservar `login(request, user)` e `logout(request)`.
- Preservar cookies `sessionid` e `csrftoken`.
- Preservar `404`, `405`, CORS e preflight conforme comportamento atual.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `/api/auth/csrf/`, ja migrado na PM-09.
- `/api/auth/session/`, ja migrado na PM-09.
- Endpoints de clientes, eventos, orcamentos, custos, financeiro ou backups.
- Frontend.
- ViewSets.
- ModelViewSets.
- Serializers DRF.
- Mudancas em settings, CORS, CSRF global ou autenticacao global.
- Migracao para JWT.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = grupo pequeno e coeso quando o contrato for simples.

Nesta PM, login e logout podem ser tratados juntos porque pertencem ao mesmo
fluxo de autenticacao e compartilham os mesmos guardrails de sessao, cookie e
CSRF.

Endpoints financeiros continuam fora de escopo e so devem ser migrados depois
dos endpoints de cadastro/operacao estarem estaveis em DRF.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, cookies, CSRF, CORS ou comportamento
runtime apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-18.1

Arquivo atual:

- `caixa/views_api_auth.py`

Rotas atuais:

- `path("api/auth/login/", api_auth_login, name="api_auth_login")`
- `path("api/auth/logout/", api_auth_logout, name="api_auth_logout")`

Nomes das rotas:

- `caixa:api_auth_login`
- `caixa:api_auth_logout`

### `POST /api/auth/login/`

View atual:

- `api_auth_login`

Decoradores atuais:

- `@require_POST`
- `@sensitive_post_parameters("password")`
- `@sensitive_variables("password")`
- `@never_cache`

Metodo aceito:

- `POST`

Metodos nao permitidos:

- com CSRF valido, `GET`, `PUT`, `PATCH` e `DELETE` retornam `405`;
- header `Allow` esperado: `POST`;
- resposta atual e HTML vazia do Django para `405`.

Autenticacao:

- aceita usuario anonimo;
- nao exige sessao previa.

CSRF:

- `POST` sem CSRF valido e bloqueado pelo middleware antes da view com `403`
  HTML quando testado com `Client(enforce_csrf_checks=True)`;
- `POST` com CSRF valido chega na view.

Content-Type:

- exige `application/json`;
- aceita `application/json; charset=utf-8`;
- `Content-Type` invalido retorna:

```json
{"detail": "Content-Type deve ser application/json."}
```

com status `415`.

Body:

- le `request.body`;
- body vazio e tratado como payload `{}`;
- JSON invalido ou payload nao-dict retorna:

```json
{"detail": "JSON invalido."}
```

com status `400`.

Credenciais ausentes:

```json
{"detail": "Informe usuario e senha."}
```

com status `400`.

Credenciais invalidas:

```json
{"detail": "Usuario ou senha invalidos."}
```

com status `401`.

Payload de sucesso:

```json
{
  "authenticated": true,
  "user": {},
  "csrfToken": "..."
}
```

Campos de `user`:

- mesmos campos de `_user_payload`;
- inclui identificacao basica (`id`, `username`, `displayName`, `isStaff`,
  `isSuperuser`);
- inclui flags top-level de permissao;
- inclui `permissions` com o mesmo mapa de flags.

Status codes atuais:

- `200`: login com sucesso;
- `400`: JSON invalido, payload nao-dict ou credenciais ausentes;
- `401`: credenciais invalidas;
- `403`: CSRF invalido antes da view;
- `405`: metodo nao permitido;
- `415`: `Content-Type` invalido.

Headers relevantes:

- respostas JSON usam `Content-Type: application/json`;
- respostas JSON usam `Cache-Control` com `no-store`;
- `405` preserva `Allow: POST`;
- sucesso pode ter `Vary: Cookie, Origin` quando chamado pelo frontend.

Cookies e efeitos colaterais:

- sucesso cria sessao Django;
- sucesso define `sessionid`;
- sucesso define/rotaciona `csrftoken`;
- sucesso retorna `csrfToken` novo;
- `sessionid` e `csrftoken` usam as configuracoes atuais do projeto;
- senha nao aparece no payload de resposta.

### `POST /api/auth/logout/`

View atual:

- `api_auth_logout`

Decoradores atuais:

- `@require_POST`
- `@never_cache`

Metodo aceito:

- `POST`

Metodos nao permitidos:

- com CSRF valido, `GET`, `PUT`, `PATCH` e `DELETE` retornam `405`;
- header `Allow` esperado: `POST`;
- resposta atual e HTML vazia do Django para `405`.

Autenticacao:

- aceita usuario anonimo se houver CSRF valido;
- nao exige usuario autenticado.

CSRF:

- `POST` sem CSRF valido e bloqueado pelo middleware antes da view com `403`
  HTML quando testado com `Client(enforce_csrf_checks=True)`;
- `POST` com CSRF valido chega na view.

Content-Type e body:

- nao exige `application/json`;
- nao le body;
- ignora JSON invalido;
- nao deve acessar `request.data` apos migracao.

Payload de sucesso:

```json
{
  "authenticated": false,
  "csrfToken": "..."
}
```

Status codes atuais:

- `200`: logout executado, inclusive para anonimo com CSRF valido;
- `403`: CSRF invalido antes da view;
- `405`: metodo nao permitido.

Headers relevantes:

- respostas JSON usam `Content-Type: application/json`;
- respostas JSON usam `Cache-Control` com `no-store`;
- `405` preserva `Allow: POST`;
- sucesso pode ter `Vary: Cookie, Origin` quando chamado pelo frontend.

Cookies e efeitos colaterais:

- usuario autenticado tem sessao encerrada;
- `sessionid` e removido/expirado;
- `csrftoken` e mantido ou definido;
- resposta retorna novo `csrfToken`;
- apos logout autenticado, `/api/auth/session/` retorna
  `{"authenticated": false}`.

### Comparacao com endpoints ja migrados

`GET /api/auth/csrf/`:

- ja usa DRF;
- `@api_view(["GET"])`;
- `AllowAny`;
- `@ensure_csrf_cookie`;
- `@never_cache`;
- retorna somente `csrfToken`.

`GET /api/auth/session/`:

- ja usa DRF;
- `@api_view(["GET"])`;
- `AllowAny`;
- `@never_cache`;
- anonimo retorna `{"authenticated": false}`;
- autenticado retorna `authenticated`, `user` e `csrfToken`;
- reaproveita `_user_payload`.

## Riscos especificos de autenticacao

- DRF pode trocar `405` e header `Allow` se `@require_POST` nao for preservado
  de forma equivalente.
- DRF pode tentar parsear JSON invalido antes da view se `request.data` for
  acessado indevidamente.
- Logout nao pode passar a exigir `application/json`.
- Login nao pode aceitar `Content-Type` invalido.
- Login nao pode mudar mensagens de erro, status HTTP ou shape de `_user_payload`.
- Login nao pode expor senha ou diferenciar causa real de credenciais invalidas.
- CSRF precisa continuar sendo validado pelo fluxo atual.
- Sessao Django e cookies HttpOnly precisam continuar iguais.
- A rotacao/definicao de `csrftoken` precisa continuar compativel com o frontend.
- O logout precisa encerrar a sessao e expirar `sessionid`.
- O comportamento anonimo do logout com CSRF valido precisa ser preservado.

## Guardrails

- Nao alterar `/api/auth/csrf/`.
- Nao alterar `/api/auth/session/`.
- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao criar serializer DRF.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao migrar para JWT.
- Nao acessar `request.data` no logout.
- Nao exigir `application/json` no logout.
- Preservar `_json_payload`, `_is_json_request`, `_string_value` e
  `_user_payload`, salvo necessidade tecnica demonstrada.
- Preservar `AuthenticationForm`.
- Preservar `login(request, user)` e `logout(request)`.
- Preservar `@never_cache`.
- Preservar `@sensitive_post_parameters("password")` e
  `@sensitive_variables("password")`.
- Usar `AllowAny` local se necessario para evitar respostas padrao do DRF.
- Priorizar paridade runtime sobre schema OpenAPI.

## PM-18.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real de login/logout antes de alterar qualquer
codigo runtime.

Tarefas realizadas:

- Views atuais identificadas.
- URLs e nomes de rota identificados.
- Metodos aceitos identificados.
- Comportamento de metodos nao permitidos identificado.
- CSRF atual identificado.
- Content-Type e leitura de body identificados.
- Payloads de sucesso e erro identificados.
- Status HTTP atuais identificados.
- Headers relevantes identificados.
- Efeitos colaterais de sessao, cookies e CSRF identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.
- Comparacao somente leitura com `/api/auth/csrf/` e `/api/auth/session/`
  realizada.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum arquivo alterado.

## PM-18.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

### Login

Criar ou reforcar testes para:

- CSRF real: sem token retorna `403` antes da view.
- Com CSRF valido chega na view.
- Metodos nao permitidos retornam `405` com `Allow: POST`.
- `Content-Type` invalido retorna `415`.
- JSON invalido retorna `400` com `{"detail": "JSON invalido."}`.
- Payload nao-dict retorna `400` com `{"detail": "JSON invalido."}`.
- Credenciais ausentes retornam `400`.
- Credenciais invalidas retornam `401`.
- Sucesso retorna `200` com `authenticated`, `user` e `csrfToken`.
- Sucesso cria sessao.
- Sucesso define `sessionid`.
- Sucesso define ou rotaciona `csrftoken`.
- `csrfToken` retornado e string nao vazia.
- Shape completo de `user` preservado conforme `_user_payload`.
- Headers JSON/no-store preservados.
- Senha nao aparece na resposta.

### Logout

Criar ou reforcar testes para:

- CSRF real: sem token retorna `403` antes da view.
- Com CSRF valido chega na view.
- Metodos nao permitidos retornam `405` com `Allow: POST`.
- Nao exige `Content-Type`.
- Ignora body.
- JSON invalido continua ignorado.
- Anonimo com CSRF valido retorna `200`.
- Autenticado encerra sessao.
- Remove/expira `sessionid`.
- Mantem ou define `csrftoken`.
- Retorna `200` com `authenticated: false` e `csrfToken`.
- `csrfToken` retornado e string nao vazia.
- Headers JSON/no-store preservados.
- Apos logout autenticado, `/api/auth/session/` retorna
  `{"authenticated": false}`.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_auth_login_logout>
```

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.

## PM-18.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_auth_login` e `api_auth_logout` para DRF com
paridade comprovada.

Implementacao esperada:

- converter somente `api_auth_login` e `api_auth_logout`;
- usar `@api_view(["POST"])`;
- usar `Response` somente na borda;
- preservar `@require_POST` se necessario para manter `405` e `Allow: POST`;
- preservar `@never_cache`;
- preservar decoradores sensiveis do login;
- usar `AllowAny` local se necessario;
- preservar CSRF real;
- nao alterar autenticacao global;
- nao alterar settings;
- login pode continuar parseando body como hoje;
- logout nao deve acessar `request.data`;
- logout nao deve exigir `application/json`;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- preservar cookies, sessao, CSRF e payloads atuais.

Regras:

- Manter URL `/api/auth/login/`.
- Manter URL `/api/auth/logout/`.
- Manter nomes de rota.
- Manter metodo `POST`.
- Manter status HTTP.
- Manter JSONs de sucesso e erro.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow: POST`.
- Manter sessao Django.
- Manter CSRF real.
- Manter CORS sem alteracao.
- Reaproveitar helpers atuais.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_auth_login_logout>
```

Gate de saida:

- `/api/auth/login/` migrado para DRF.
- `/api/auth/logout/` migrado para DRF.
- Login/logout mantem paridade.
- Nenhum outro endpoint alterado.

## PM-18.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_auth_login_logout>
python manage.py test <testes_relacionados_de_auth_session_csrf>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/auth/login/` e `/api/auth/logout/`;
- nenhuma regressao;
- `/api/auth/csrf/` nao foi alterado;
- `/api/auth/session/` nao foi alterado;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado a login/logout, testes e registro do plano;
- CSRF real preservado;
- cookies preservados;
- sessao Django preservada;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- testes focados passam;
- testes relacionados de auth passam;
- suite geral passa;
- warnings do spectacular registrados;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-18.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-18 antes de avancar para outro
endpoint.

Tarefas:

- Atualizar este documento.
- Registrar arquivos alterados.
- Registrar testes criados.
- Registrar comandos executados.
- Registrar resultado dos testes focados.
- Registrar resultado dos testes relacionados de auth.
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

Proximo passo natural, somente se PM-18 estiver estavel:

- retomar o roadmap PM-17 e escolher o proximo endpoint de baixo risco.

## Criterios globais de aceite

- `POST /api/auth/login/` mantem paridade.
- `POST /api/auth/logout/` mantem paridade.
- URLs preservadas.
- Nomes de rota preservados.
- Metodo `POST` preservado.
- Status HTTP preservados.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow: POST` preservado nos `405`.
- CSRF real preservado.
- CORS preservado.
- Sessao Django preservada.
- Cookies `sessionid` e `csrftoken` preservados.
- Login cria sessao.
- Logout encerra sessao.
- Login define/rotaciona `csrftoken`.
- Logout remove/expira `sessionid`.
- Logout nao exige `application/json`.
- Logout ignora body e JSON invalido.
- Login mantem `AuthenticationForm`.
- `_user_payload` preservado.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/auth/login/` e `/api/auth/logout/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- header relevante mudar;
- cookie mudar;
- CSRF mudar;
- CORS mudar;
- sessao Django mudar;
- login deixar de criar sessao;
- logout deixar de encerrar sessao;
- logout passar a exigir `application/json`;
- logout passar a parsear body ou JSON invalido;
- login passar a aceitar `Content-Type` invalido;
- credenciais invalidas retornarem mensagem diferente;
- senha aparecer em resposta ou log de teste;
- usuario autenticado receber shape de `user` diferente;
- `csrfToken` deixar de ser retornado nos sucessos;
- `sessionid` deixar de ser definido no login;
- `sessionid` deixar de ser removido/expirado no logout;
- `@never_cache` for perdido;
- `@sensitive_post_parameters` ou `@sensitive_variables` forem perdidos;
- `/api/auth/csrf/` precisar ser alterado;
- `/api/auth/session/` precisar ser alterado;
- frontend precisar ser alterado;
- outro endpoint precisar ser alterado;
- DRF gerar resposta padrao diferente para `400`, `401`, `403`, `405` ou
  `415`;
- serializer DRF se tornar necessario para regra de autenticacao;
- houver necessidade de alterar settings, CORS, CSRF global ou auth global.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime de `api_auth_login` e
  `api_auth_logout`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro de login/logout.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

Se sessao, cookie ou CSRF divergirem:

- Parar a PM.
- Reverter a migracao runtime.
- Manter testes que detectaram a divergencia.
- Registrar exatamente qual efeito divergiu.

## Registro de execucao

### Registro de execucao - PM-18.1

Fase: diagnostico read-only.

Endpoints alvo:

- `POST /api/auth/login/`
- `POST /api/auth/logout/`

Arquivos lidos:

- `caixa/views_api_auth.py`
- `caixa/urls.py`
- `caixa/tests.py`

Resultado:

- Contrato atual de login/logout mapeado.
- Views ainda estavam Django puro.
- Lacunas de paridade identificadas para CSRF, metodos nao permitidos,
  Content-Type, JSON invalido, credenciais, sucesso, sessao, cookies e
  headers.
- Comparacao com `/api/auth/csrf/` e `/api/auth/session/` realizada somente em
  leitura.
- Nenhum arquivo alterado nesta fase.

`git status --short` observado ao final da PM-18.1:

```text
```

### Registro de execucao - PM-18.2

Fase: congelamento de contrato em testes.

Endpoints alvo:

- `POST /api/auth/login/`
- `POST /api/auth/logout/`

Arquivo alterado:

- `caixa/tests.py`

Testes criados/reforcados:

- `test_api_auth_login_preserva_csrf_405_erros_e_payload_nao_dict`
- `test_api_auth_login_sucesso_preserva_sessao_cookies_csrf_e_shape`
- `test_api_auth_logout_preserva_csrf_405_anonimo_e_body_ignorado`
- `test_api_auth_logout_autenticado_expira_sessao_e_ignora_json_invalido`

Helpers adicionados em `PermissoesTests`:

- `_auth_csrf_token`
- `_assert_json_no_store`
- `_expected_auth_permissions`

Cobertura congelada:

- CSRF real em login/logout com `Client(enforce_csrf_checks=True)`;
- `405` com `Allow: POST`;
- `Content-Type` invalido do login com `415`;
- JSON invalido e payload nao-dict do login com `400`;
- credenciais ausentes com `400`;
- credenciais invalidas com `401`;
- sucesso do login com `authenticated`, `user` e `csrfToken`;
- criacao de sessao e definicao/rotacao de cookies no login;
- shape completo de `_user_payload`;
- logout anonimo com CSRF valido;
- logout autenticado encerrando sessao;
- expiracao de `sessionid` no logout;
- manutencao/definicao de `csrftoken`;
- logout ignorando `Content-Type` nao JSON e JSON invalido;
- headers JSON/no-store;
- senha ausente na resposta.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.PermissoesTests
venv\Scripts\python.exe manage.py check
```

Resultado:

- `PermissoesTests`: `32` testes, `OK`.
- `check`: sem issues.
- Warnings esperados de CSRF e django-axes apareceram nos cenarios que
  exercitam bloqueio CSRF e credenciais invalidas.
- Nenhuma view foi migrada nesta fase.
- Frontend, settings, CORS, CSRF global e auth global nao foram alterados.

### Registro de execucao - PM-18.3

Fase: migracao controlada para DRF.

Endpoints migrados:

- `POST /api/auth/login/`
- `POST /api/auth/logout/`

Arquivo alterado:

- `caixa/views_api_auth.py`

Implementacao:

- `api_auth_login` foi migrada com `@api_view(["POST"])`.
- `api_auth_logout` foi migrada com `@api_view(["POST"])`.
- `Response` passou a ser usado somente na borda.
- `@require_POST` foi preservado para manter `405` e `Allow: POST`.
- `@never_cache` foi preservado.
- `@sensitive_post_parameters("password")` e
  `@sensitive_variables("password")` foram preservados no login.
- `AuthenticationForm` foi preservado.
- `_user_payload` foi preservado.
- `login(request, user)` e `logout(request)` foram preservados usando a
  request Django original.
- `AllowAny` foi usado localmente para manter login/logout publicos e evitar
  respostas padrao do DRF.
- `JSONParser` foi declarado no login para o OpenAPI refletir que o contrato de
  entrada e JSON.

Ajustes locais necessarios para preservar contrato:

- `csrf_protect_drf_view`: helper local que executa `CsrfViewMiddleware` antes
  da view DRF. Foi necessario porque `@api_view` torna a view isenta do
  middleware CSRF padrao do Django; sem esse helper, login anonimo sem token
  chegava na view e mudava o contrato de `403`.
- `IgnoreBodyParser`: parser local usado somente no logout para impedir que DRF
  trate JSON invalido antes da view. Foi necessario para preservar que logout
  nao le body, nao exige `application/json` e ignora JSON invalido.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.PermissoesTests
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
```

Resultado:

- `PermissoesTests`: `32` testes, `OK`.
- `check`: sem issues.
- `spectacular --validate`: validado, sem warnings/erros.
- OpenAPI inclui `/api/auth/login/` e `/api/auth/logout/`.
- Nenhum outro endpoint foi migrado.
- `/api/auth/csrf/` nao foi alterado.
- `/api/auth/session/` nao foi alterado.
- Frontend, settings, CORS, CSRF global e auth global nao foram alterados.

### Registro de execucao - PM-18.4

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.PermissoesTests
venv\Scripts\python.exe manage.py test
```

Resultado:

- `check`: sem issues.
- `spectacular --validate`: validado, sem warnings/erros.
- OpenAPI inclui `/api/auth/login/` e `/api/auth/logout/`.
- `PermissoesTests`: `32` testes, `OK`.
- Suite completa: `708` testes, `OK`.

Warnings observados:

- warnings esperados de CSRF nos testes que validam bloqueio antes da view;
- logs esperados do django-axes nos testes de credenciais invalidas.

Confirmacoes:

- Login/logout mantiveram paridade runtime.
- `/api/auth/csrf/` nao foi alterado.
- `/api/auth/session/` nao foi alterado.
- Nenhum serializer, ViewSet ou ModelViewSet foi criado.
- Nenhum `schema.yml` temporario foi gerado.
- Frontend, settings, CORS, CSRF global e auth global nao foram alterados.

### Registro de execucao - PM-18.5

Fase: encerramento.

Arquivos alterados na PM-18:

- `caixa/tests.py`
- `caixa/views_api_auth.py`
- `docs/PLANO_PM18_MIGRACAO_AUTH_LOGIN_LOGOUT_DRF.md`

Dependencias adicionadas:

- Nenhuma.

Rotas criadas:

- Nenhuma.

Endpoints migrados nesta PM:

- `POST /api/auth/login/`
- `POST /api/auth/logout/`

Endpoints nao alterados nesta PM:

- `GET /api/auth/csrf/`
- `GET /api/auth/session/`
- clientes;
- eventos;
- orcamentos;
- custos;
- financeiro;
- backups.

Decisao sobre `schema.yml`:

- Nao foi gerado arquivo `schema.yml`; foi usado somente
  `spectacular --validate`.

Riscos residuais:

- A protecao CSRF local existe porque DRF isenta a view do middleware CSRF do
  Django. Ela fica restrita a login/logout e deve ser mantida coberta por
  testes antes de qualquer reaproveitamento.
- `IgnoreBodyParser` e propositalmente restrito ao logout; nao deve ser usado
  em endpoints que precisam validar body.
- O schema OpenAPI continua generico (`object`) para preservar a prioridade da
  paridade runtime e evitar serializer DRF nesta PM.

Recomendacao:

- PM-18 pronta para commit local manual.
