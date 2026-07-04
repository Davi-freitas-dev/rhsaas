# Plano PM-09 - Migracao incremental para DRF endpoint por endpoint

Atualizado em: 2026-06-15

## Objetivo

Migrar APIs Django puro para Django REST Framework de forma incremental,
endpoint por endpoint, preservando totalmente os contratos atuais consumidos
pelo frontend Next.js.

Esta PM nao deve iniciar por endpoints financeiros complexos nem por cadastros
com multiplos metodos. O primeiro endpoint candidato e `/api/auth/session/`,
por ser pequeno, ja ter testes existentes e permitir validar a estrategia de
paridade antes de avancar para areas com maior risco.

## Regra-mae de escopo

Cada endpoint deve ser migrado isoladamente.

Nenhuma migracao pode avancar sem:

- diagnostico read-only do endpoint;
- teste de paridade escrito contra o comportamento atual;
- validacao de que a URL, metodo, status, JSON, headers relevantes,
  autenticacao, CSRF, CORS, permissoes e contrato frontend foram preservados;
- revisao final antes de escolher o proximo endpoint.

## Preservacoes obrigatorias

- Mesmas URLs.
- Mesmos nomes de rota quando ja existirem.
- Mesmos metodos HTTP.
- Mesmos JSONs.
- Mesmos status HTTP.
- Mesmas permissoes.
- Mesma autenticacao por sessao Django.
- Mesmo comportamento de CSRF.
- Mesmo CORS.
- Mesmos contratos consumidos pelo frontend.
- Mesmos helpers, selectors, services e serializers manuais quando ja forem a
  fonte da regra atual.

## Proibicoes

- Nao migrar varios endpoints na mesma fase.
- Nao trocar sessao Django por JWT, token ou outro mecanismo.
- Nao alterar frontend para compensar mudanca evitavel no backend.
- Nao mover regra financeira para serializers DRF, ViewSets ou frontend.
- Nao alterar services, selectors, permissoes ou serializers manuais sem
  necessidade demonstrada do endpoint em migracao.
- Nao usar `ModelViewSet` em endpoint existente sem prova de paridade e sem
  decisao especifica.
- Nao mudar status HTTP, envelope JSON, nomes de campos, aliases ou formato de
  erro.
- Nao usar o schema OpenAPI como justificativa para mudar contrato runtime.
- Nao fazer commit, push, merge ou deploy automaticamente.

## Principio tecnico

DRF entra como camada HTTP incremental, nao como redesenho da arquitetura.

Para cada endpoint, preferir a menor adaptacao possivel:

1. manter URL e nome da rota;
2. reaproveitar helpers existentes;
3. preservar decorators de cache, CSRF e seguranca quando aplicavel;
4. usar `APIView` ou `@api_view` apenas no endpoint migrado;
5. usar `Response` somente no endpoint migrado e somente se os testes provarem
   paridade de contrato;
6. documentar schema depois da paridade runtime, nao antes.

## Estado inicial conhecido

- PM-08 adicionou DRF e drf-spectacular como infraestrutura.
- As APIs atuais continuam Django puro com `JsonResponse`.
- `REST_FRAMEWORK` usa `SessionAuthentication` e permissao default
  `IsAuthenticated`.
- Endpoints publicos atuais, como `/api/auth/session/`, precisam declarar
  explicitamente permissao equivalente ao comportamento atual quando forem
  migrados para DRF.
- O frontend usa `credentials: include`, cookie HttpOnly e `X-CSRFToken` nas
  mutations.

## PM-09.1 - Diagnostico read-only dos endpoints simples

Status: planejada.

Objetivo: selecionar endpoints de menor risco antes de qualquer migracao.

Tarefas:

- Mapear endpoints candidatos simples.
- Classificar por risco, metodo HTTP, autenticacao, permissao, CSRF, uso pelo
  frontend e tamanho do payload.
- Confirmar quais endpoints ja possuem testes de contrato suficientes.
- Identificar lacunas de teste antes de migrar.
- Registrar arquivos envolvidos e `git status --short`.

Criterios para endpoint simples:

- payload pequeno;
- pouca ou nenhuma regra de negocio;
- metodo unico, preferencialmente `GET`;
- contrato claro no frontend;
- teste existente ou facil de reforcar;
- sem escrita no banco;
- sem fluxo financeiro complexo.

Classificacao inicial:

- Primeiro candidato: `/api/auth/session/`.
- Candidatos futuros possiveis: `/api/auth/csrf/`, depois de avaliar efeitos de
  cookie/CSRF.
- Nao iniciar por `/api/clientes/`: possui `GET` e `POST`, permissoes manuais,
  payload de lista e mutacao.
- Nao iniciar por endpoints financeiros: maior risco de regra de dominio e
  contrato.

Gate de saida:

- Endpoint inicial confirmado.
- Contrato atual descrito.
- Testes de paridade necessarios listados.
- Nenhum codigo runtime alterado.

## PM-09.2 - Teste de paridade antes da migracao de `/api/auth/session/`

Status: planejada.

Objetivo: congelar o comportamento atual antes de trocar a implementacao para
DRF.

Contrato atual esperado:

- URL: `/api/auth/session/`.
- Nome de rota: `caixa:api_auth_session`.
- Metodo: `GET`.
- Usuario anonimo:
  - status `200`;
  - JSON exato: `{"authenticated": false}`;
  - resposta nao cacheavel.
- Usuario autenticado:
  - status `200`;
  - JSON com `authenticated: true`;
  - objeto `user` gerado por `_user_payload`;
  - `csrfToken` presente;
  - resposta nao cacheavel.

Regras de teste:

- Testar anonimo e autenticado.
- Comparar status HTTP.
- Comparar JSON sem depender do valor literal de `csrfToken`.
- Validar chaves principais do usuario e permissoes publicadas.
- Validar `Cache-Control`/nao cache quando ja for comportamento atual.
- Validar que o frontend continuaria recebendo o mesmo shape.

Gate de saida:

- Teste de paridade passa com a implementacao Django pura atual.
- Nenhuma migracao feita ainda.

## PM-09.3 - Migracao de `/api/auth/session/` para DRF

Status: planejada.

Objetivo: migrar somente `/api/auth/session/` para DRF, mantendo contrato.

Regras especificas:

- Manter a mesma URL.
- Manter o mesmo nome de rota.
- Manter metodo `GET`.
- Manter sessao Django.
- Manter comportamento publico atual para anonimo.
- Declarar permissao DRF equivalente, como `AllowAny`, apenas nesse endpoint se
  necessario para preservar o contrato atual.
- Manter `never_cache`.
- Reaproveitar `_user_payload`.
- Nao migrar login, logout ou CSRF nesta fase.
- Nao alterar frontend.

Validacoes obrigatorias:

- Teste de paridade de `/api/auth/session/`.
- Testes existentes de auth/session/CSRF.
- `python manage.py check`.
- `python manage.py spectacular --validate`.

Gate de saida:

- `/api/auth/session/` migrado para DRF com paridade comprovada.
- Nenhum outro endpoint alterado.
- Nenhum contrato JSON alterado.

## PM-09.4 - Revisao pos-migracao do primeiro endpoint

Status: planejada.

Objetivo: decidir se a estrategia e segura antes de migrar qualquer outro
endpoint.

Checklist:

- Diff limitado ao endpoint e testes.
- Nenhuma permissao global alterada.
- Nenhum CORS/CSRF alterado.
- Nenhuma mudanca no frontend.
- Schema OpenAPI melhorou sem forcar mudanca runtime.
- Testes passam.
- `git status --short` registrado.

Decisao possivel:

- Avancar para proximo endpoint simples.
- Ajustar estrategia de teste.
- Parar e reverter a migracao se houver divergencia.

## PM-09.5 - Diagnostico antes de pensar em `/api/clientes/`

Status: planejada.

Objetivo: avaliar `/api/clientes/` somente depois de `/api/auth/session/`
estar migrado e validado.

Pontos de atencao:

- `/api/clientes/` possui `GET` e `POST`.
- Usa permissoes manuais com respostas JSON `401`/`403`.
- Publica metadados de permissao, como `canCreate` e `canUpdate`.
- Aceita payload JSON em criacao.
- Pode exigir testes de paridade separados para lista, criacao, erro de JSON,
  erro de permissao e usuario anonimo.

Regra:

- Nao migrar `/api/clientes/` na mesma fase de `/api/auth/session/`.
- Antes de migrar, criar plano ou subfase propria de paridade para clientes.

## Criterios globais de aceite da PM-09

- Pelo menos o primeiro endpoint migrado possui teste de paridade antes/depois.
- URLs, metodos, status, JSONs e headers relevantes foram preservados.
- Sessao Django e CSRF foram preservados.
- CORS nao foi alterado.
- Permissoes atuais foram preservadas.
- Frontend nao foi alterado.
- Nenhum endpoint fora do escopo foi migrado.
- `python manage.py check` passa.
- Testes focados passam.
- Suite existente relevante passa ou impossibilidade fica registrada.

## Criterios de bloqueio

A execucao deve parar se qualquer ponto ocorrer:

- usuario anonimo passar a receber status diferente em `/api/auth/session/`;
- JSON de `/api/auth/session/` mudar de shape;
- `csrfToken` sumir para usuario autenticado;
- resposta deixar de ser nao cacheavel;
- DRF `IsAuthenticated` bloquear endpoint que hoje e publico;
- frontend precisar mudar para continuar funcionando;
- login, logout, CSRF ou clientes forem migrados junto sem autorizacao;
- permissao, CORS ou CSRF forem alterados globalmente;
- schema OpenAPI virar prioridade acima da paridade runtime.

## Registro de execucao

Cada fase executada deve registrar:

- data;
- fase;
- endpoint alvo;
- arquivos alterados;
- testes adicionados;
- comandos executados;
- resultado dos testes;
- diferencas encontradas na paridade;
- riscos residuais;
- `git status --short`;
- decisao de avancar ou parar.

## Registro de execucao - 2026-06-15 - PM-09.3

Fase executada: migracao de `/api/auth/session/` para DRF.

Endpoint alvo:

- `/api/auth/session/`
- rota: `caixa:api_auth_session`
- metodo: `GET`

Arquivos alterados:

- `caixa/views_api_auth.py`
- `caixa/tests.py`
- `docs/PLANO_PM09_MIGRACAO_INCREMENTAL_DRF.md`

Mudanca aplicada:

- Somente `api_auth_session` foi migrada para DRF.
- A view passou a usar `@api_view(["GET"])`.
- Foi usada permissao local `AllowAny` para preservar o comportamento publico
  de usuario anonimo com status `200`.
- A resposta passou a usar DRF `Response` somente neste endpoint.
- `@never_cache` foi mantido para preservar `Cache-Control` nao cacheavel.
- `_user_payload` foi preservado sem alteracao.
- Foi adicionada anotacao `@extend_schema(responses=OpenApiTypes.OBJECT)` para
  permitir introspeccao basica sem criar serializer DRF.

Confirmacoes:

- Login, logout e CSRF nao foram migrados.
- Nenhum outro endpoint foi alterado.
- Nenhum serializer DRF foi criado.
- Nenhuma autenticacao global foi alterada.
- CSRF, CORS e frontend nao foram alterados.
- URL, nome de rota, metodo, status, JSON e headers relevantes de
  `/api/auth/session/` foram preservados pelos testes de paridade.

Validacoes executadas:

- `python manage.py check`: passou, sem issues.
- `python manage.py spectacular --validate`: passou; schema passou a incluir
  `/api/auth/session/` com resposta `object`.
- Testes focados de rota/auth-session: 8 executados, 8 passaram.

Warnings/limitacoes:

- Sem warnings finais do `drf-spectacular` para o endpoint migrado.
- O schema ainda usa resposta generica `object`; detalhamento fino do contrato
  pode ser plano futuro, sem mudar runtime.

Decisao:

- PM-09.3 concluida.
- Proxima etapa recomendada: PM-09.4, revisao pos-migracao antes de escolher
  qualquer outro endpoint.

## Fora do escopo inicial

- Migrar `/api/clientes/` antes de concluir `/api/auth/session/`.
- Migrar endpoints financeiros.
- Migrar login/logout.
- Criar arquitetura nova de API.
- Criar ViewSets globais.
- Gerar tipos TypeScript oficiais.
- Alterar contratos do frontend.

## Proxima acao recomendada

Executar PM-09.1 como diagnostico read-only e, em seguida, PM-09.2 criando o
teste de paridade de `/api/auth/session/` contra a implementacao atual.
