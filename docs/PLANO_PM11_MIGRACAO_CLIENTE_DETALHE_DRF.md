# Plano PM-11 - Migracao incremental de `/api/clientes/<id>/` para DRF

Atualizado em: 2026-06-15

## Objetivo

Migrar exclusivamente `/api/clientes/<id>/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

Esta PM cobre somente:

- `GET /api/clientes/<id>/`
- `PUT /api/clientes/<id>/`

Esta PM nao cobre `/api/clientes/`.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = 1 par `GET`/`PUT` quando o contrato for pequeno.

Ordem geral recomendada:

- endpoints de autenticacao simples primeiro;
- cadastros e operacoes antes de endpoints financeiros;
- endpoints financeiros read-only antes de mutations financeiras;
- mutations financeiras somente depois de GETs financeiros estarem estaveis em
  DRF.

Endpoints financeiros so devem ser migrados depois de cadastros e operacoes
estarem estaveis em DRF.

## Regra-mae

DRF deve entrar apenas como casca HTTP do endpoint de detalhe, sem mudar regra de
negocio, helpers, services, selectors ou contrato JSON.

Antes da migracao deve existir teste de paridade cobrindo:

- `GET`;
- `PUT`;
- autenticacao;
- permissoes por metodo;
- cliente inexistente;
- CSRF real no `PUT`;
- erros atuais;
- validacoes;
- contrato JSON;
- headers relevantes.

Nenhuma alteracao de frontend e permitida nesta PM.

## Preservacoes obrigatorias

- Mesma URL: `/api/clientes/<id>/`.
- Mesmo nome de rota: `caixa:api_cliente_detalhe`.
- Mesmos metodos HTTP: `GET` e `PUT`.
- Mesmo JSON.
- Mesmo status HTTP.
- Mesmas permissoes.
- Mesmo comportamento para usuario anonimo.
- Mesmo comportamento para usuario autenticado sem permissao.
- Mesmo comportamento para cliente inexistente.
- Mesmo CSRF no `PUT`.
- Mesmo CORS.
- Mesmo `Content-Type`.
- Mesmo `Cache-Control`/`no-store` quando existir no contrato atual.
- Mesmos aliases de payload aceitos pelo frontend no `PUT`.
- Mesmo contrato consumido por
  `features/financial-dashboard/services/financial-clients-service.ts`.

## Proibicoes

- Nao migrar `/api/clientes/` novamente.
- Nao migrar `/api/eventos/`.
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

`/api/clientes/<id>/` possui permissoes diferentes por metodo:

- `GET` exige `caixa.view_cliente`.
- `PUT` exige `caixa.change_cliente`.

A migracao para DRF deve preservar os mesmos status e JSONs de erro atuais.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global da view, ou
permissao DRF generica como substituto direto das permissoes atuais se isso
mudar status, JSON de erro ou regra por metodo.

## Regra especial de CSRF

`PUT /api/clientes/<id>/` deve ser testado com
`Client(enforce_csrf_checks=True)`:

- sem CSRF valido: deve ser bloqueado pelo comportamento atual;
- com CSRF valido: deve seguir para permissao, validacao ou atualizacao.

Se o DRF tentar substituir `{"detail": "JSON invalido."}` por erro padrao de
parser, a migracao deve ser ajustada para preservar o contrato atual, como foi
feito na PM-10.

## Regra especial de implementacao

Reaproveitar os helpers atuais de `caixa/views_clientes_api.py`:

- `_is_json_request`;
- `_payload_json`;
- `_first_payload_value`;
- `_string_payload_value`;
- `_boolean_payload_value`;
- `_datetime_or_empty`;
- `_errors_from_validation_error`;
- `_serialize_cliente`;
- `_cliente_data_from_payload`;
- `_cliente_detalhe_response`;
- `_atualizar_cliente_response`;
- `api_authentication_required_response`;
- `api_permission_denied_response`;
- `api_no_store_json_response`.

Se a PM-10 ja tiver introduzido suporte local para DRF em
`views_clientes_api.py`, reaproveitar essa estrutura em vez de criar nova classe
ou helper.

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

```json
{"errors": "..."}
```

Para CPF/CNPJ duplicado, preservar exatamente o erro atual observado nos testes
de paridade. A PM-11 nao deve assumir a mensagem antes do diagnostico, porque o
erro pode vir de `full_clean()` ou de `IntegrityError`.

Para cliente inexistente, congelar exatamente o comportamento atual:

- status HTTP;
- `Content-Type`;
- corpo da resposta;
- headers relevantes.

Nao converter `404` para JSON se o comportamento atual nao for JSON.

## Estado atual conhecido

Arquivo atual:

- `caixa/views_clientes_api.py`

View atual:

- `api_cliente_detalhe`

Rota atual:

- `path("api/clientes/<int:pk>/", api_cliente_detalhe, name="api_cliente_detalhe")`

Frontend consumidor:

- `features/financial-dashboard/services/financial-clients-service.ts`

Helpers atuais de resposta:

- `_cliente_detalhe_response()`
- `_atualizar_cliente_response()`
- `api_authentication_required_response()`
- `api_permission_denied_response()`
- `api_no_store_json_response()`

Payload de `GET` esperado a confirmar no diagnostico:

- `data.client`
- `data.permissions.canUpdate`
- `data.meta.source`

Payload de sucesso de `PUT` esperado a confirmar no diagnostico:

- `data.client`
- `data.message`

Aliases aceitos no `PUT`:

- `name`, `nome_razao_social`, `nomeRazaoSocial`
- `tradeName`, `nome_fantasia`
- `personType`, `tipo_pessoa`
- `document`, `cpf_cnpj`, `cpfCnpj`
- `phone`, `telefone`
- `email`
- `responsible`, `responsavel`
- `address`, `endereco`
- `notes`, `observacoes`
- `isActive`, `ativo`

## PM-11.1 - Diagnostico read-only

Status: planejada.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas:

- Mapear a view atual.
- Mapear `GET /api/clientes/<id>/`.
- Mapear `PUT /api/clientes/<id>/`.
- Mapear permissoes por metodo.
- Mapear payloads de sucesso.
- Mapear payloads de erro.
- Mapear comportamento de cliente inexistente.
- Mapear headers relevantes.
- Mapear uso de CSRF no frontend.
- Mapear dependencias do frontend.
- Mapear testes existentes.
- Identificar lacunas de teste.
- Registrar arquivos envolvidos.
- Registrar `git status --short`.

Arquivos previstos para leitura:

- `caixa/views_clientes_api.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/tests.py`
- frontend `features/financial-dashboard/services/financial-clients-service.ts`
- frontend `features/auth/services/backend-auth-service.ts`

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum codigo runtime alterado.

## PM-11.2 - Testes de paridade antes da migracao

Status: planejada.

Objetivo: congelar o comportamento atual de `/api/clientes/<id>/` antes de
migrar para DRF.

### Paridade de GET

Criar ou reforcar testes para:

- usuario anonimo recebe o status e JSON atuais;
- usuario autenticado sem `caixa.view_cliente` recebe o status e JSON atuais;
- usuario com `caixa.view_cliente` recebe `200`;
- cliente inexistente preserva status, corpo e `Content-Type` atuais;
- `Content-Type` continua como no contrato atual;
- `Cache-Control` contem `no-store` quando o comportamento atual tiver esse
  header;
- shape top-level continua `{"data": ...}` para sucesso;
- `data.client` mantem o mesmo conjunto de campos de `_serialize_cliente`;
- `data.permissions.canUpdate` preservado;
- `data.meta.source` preservado.

### Paridade de PUT

Criar ou reforcar testes para:

- usuario anonimo recebe o status e JSON atuais quando a requisicao chega na
  view;
- usuario autenticado sem `caixa.change_cliente` recebe o status e JSON atuais;
- `PUT` sem CSRF valido e bloqueado pelo comportamento atual com
  `Client(enforce_csrf_checks=True)`;
- `PUT` com CSRF valido segue para permissao, validacao ou atualizacao;
- cliente inexistente preserva status, corpo e `Content-Type` atuais;
- `Content-Type` invalido retorna status e JSON atuais;
- JSON invalido retorna status e JSON atuais;
- erro de validacao retorna status e `{"errors": ...}` atuais;
- CPF/CNPJ duplicado retorna status e erro atual;
- atualizacao com sucesso retorna status atual;
- payload de sucesso contem:
  - `data.client`;
  - `data.message`;
- `data.client` mantem o mesmo conjunto de campos de `_serialize_cliente`;
- `Cache-Control` contem `no-store` quando o comportamento atual tiver esse
  header;
- `Content-Type` continua JSON para respostas JSON.

### Metodos nao permitidos

Validar que metodos fora do contrato continuam bloqueados, por exemplo:

- `POST /api/clientes/<id>/`;
- `PATCH /api/clientes/<id>/`;
- `DELETE /api/clientes/<id>/`.

Gate de saida:

- Testes de paridade passam contra a implementacao atual.
- Nenhuma migracao feita ainda.

Validacoes recomendadas:

```bash
python manage.py test <testes_focados_de_cliente_detalhe>
```

## PM-11.3 - Migracao de `/api/clientes/<id>/` para DRF

Status: planejada.

Objetivo: migrar somente `/api/clientes/<id>/` para DRF com paridade
comprovada.

Preferencia de implementacao:

- usar `@api_view(["GET", "PUT"])`;
- usar `Response` somente se os testes provarem paridade;
- usar permissoes locais equivalentes por metodo;
- reaproveitar helpers atuais de clientes;
- reaproveitar suporte local de autenticacao/CSRF da PM-10 se necessario;
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
- Nao migrar `/api/clientes/` novamente.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- `SessionAuthentication` deve preservar CSRF em mutations.
- Permissao por metodo deve continuar diferenciando `view_cliente` e
  `change_cliente`.
- DRF nao deve substituir os JSONs atuais de `401`, `403`, `400`, `415`, `404`
  ou `405` por respostas padrao se isso mudar contrato.
- Se houver classe local de autenticacao criada na PM-10, avaliar reutilizacao
  direta em vez de criar uma segunda classe.
- Se o `drf-spectacular` emitir warning por classe local de autenticacao,
  preferir anotacao local segura via `extend_schema(auth=[{"cookieAuth": []}])`
  em vez de configurar algo global.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_cliente_detalhe>
```

Gate de saida:

- `/api/clientes/<id>/` migrado para DRF.
- `GET` e `PUT` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-11.4 - Revisao pos-migracao

Status: planejada.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_cliente_detalhe>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/clientes/{id}/`;
- nenhuma regressao;
- nenhum outro endpoint migrado;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint de detalhe, testes e registro do plano;
- `GET /api/clientes/<id>/` preservado;
- `PUT /api/clientes/<id>/` preservado;
- `/api/clientes/` nao alterado novamente;
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

## PM-11.5 - Fechamento e decisao sobre proximo endpoint

Status: planejada.

Objetivo: decidir se a migracao de clientes detalhe esta estavel antes de abrir
PM-12.

Tarefas:

- Registrar arquivos alterados.
- Registrar comandos executados.
- Registrar resultado dos testes.
- Registrar resultado do schema.
- Registrar riscos residuais.
- Confirmar que `/api/clientes/` nao foi remigrado.
- Recomendar se PM-12 pode iniciar.

Proximo endpoint natural, somente se PM-11 estiver estavel:

- PM-12: `GET /api/eventos/`.

## Criterios globais de aceite

- `GET /api/clientes/<id>/` mantem paridade.
- `PUT /api/clientes/<id>/` mantem paridade.
- Autenticacao por sessao Django preservada.
- CSRF preservado.
- CORS preservado.
- Permissoes por metodo preservadas.
- Comportamento de cliente inexistente preservado.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Status HTTP preservados.
- Headers relevantes preservados.
- Aliases de payload preservados.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/clientes/{id}/`.
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
- cliente inexistente receber contrato diferente;
- frontend precisar ser alterado;
- `/api/clientes/` precisar ser alterado novamente sem justificativa tecnica;
- outro endpoint precisar ser migrado;
- DRF gerar resposta padrao diferente para `401`, `403`, `400`, `404`, `415` ou
  `405`;
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

## Fora do escopo

- `/api/clientes/`.
- `/api/eventos/`.
- `/api/orcamentos/`.
- Endpoints financeiros.
- Frontend.
- ViewSets.
- ModelViewSets.
- Serializers DRF de regra de negocio.
- Alteracoes em services/selectors.
- Alteracoes em models/migrations.

## Proxima acao recomendada

Executar PM-11.1 como diagnostico read-only de `/api/clientes/<id>/`, sem
migracao e sem alteracao de codigo runtime.
