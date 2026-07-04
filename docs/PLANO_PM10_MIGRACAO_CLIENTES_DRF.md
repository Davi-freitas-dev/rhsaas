# Plano PM-10 - Migracao incremental de `/api/clientes/` para DRF

Atualizado em: 2026-06-15

## Objetivo

Migrar exclusivamente `/api/clientes/` para Django REST Framework, preservando
integralmente o contrato atual consumido pelo frontend Next.js.

Esta PM cobre somente:

- `GET /api/clientes/`
- `POST /api/clientes/`

Esta PM nao cobre `/api/clientes/<id>/`.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = `GET`/`POST` juntos apenas quando o contrato for pequeno.

Ordem geral recomendada:

- endpoints de autenticacao simples primeiro;
- cadastros e operacoes antes de endpoints financeiros;
- endpoints financeiros read-only antes de mutations financeiras;
- mutations financeiras somente depois de GETs financeiros estarem estaveis em
  DRF.

Endpoints financeiros so devem ser migrados depois de cadastros e operacoes
estarem estaveis em DRF.

## Regra-mae

DRF deve entrar apenas como casca HTTP do endpoint, sem mudar regra de negocio,
helpers, services, selectors ou contrato JSON.

Antes da migracao deve existir teste de paridade cobrindo:

- `GET`;
- `POST`;
- autenticacao;
- permissoes por metodo;
- CSRF real;
- erros atuais;
- validacoes;
- contrato JSON;
- headers relevantes.

Nenhuma alteracao de frontend e permitida nesta PM.

## Preservacoes obrigatorias

- Mesma URL: `/api/clientes/`.
- Mesmo nome de rota: `caixa:api_clientes`.
- Mesmos metodos HTTP: `GET` e `POST`.
- Mesmo JSON.
- Mesmo status HTTP.
- Mesmas permissoes.
- Mesmo comportamento para usuario anonimo.
- Mesmo comportamento para usuario autenticado sem permissao.
- Mesmo CSRF.
- Mesmo CORS.
- Mesmo `Content-Type`.
- Mesmo `Cache-Control`/`no-store`.
- Mesmos aliases e filtros aceitos pelo frontend.
- Mesmo contrato consumido por
  `features/financial-dashboard/services/financial-clients-service.ts`.

## Proibicoes

- Nao migrar `/api/clientes/<id>/`.
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

`/api/clientes/` possui permissoes diferentes por metodo:

- `GET` exige `caixa.view_cliente`.
- `POST` exige `caixa.add_cliente`.

A migracao para DRF deve preservar os mesmos status e JSONs de erro atuais.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global da view, ou
permissao DRF generica como substituto direto das permissoes atuais se isso
mudar status, JSON de erro ou regra por metodo.

A view DRF deve continuar retornando os mesmos helpers de erro ou respostas
equivalentes no JSON.

## Regra especial de CSRF

`POST /api/clientes/` deve ser testado com
`Client(enforce_csrf_checks=True)`:

- sem CSRF valido: deve ser bloqueado pelo comportamento atual;
- com CSRF valido: deve seguir para validacao, permissao ou criacao.

O teste de `POST` sem CSRF pode retornar `403` antes da logica da view, desde
que esse seja o comportamento atual preservado.

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
- `_clientes_response`;
- `_criar_cliente_response`.

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

```json
{"detail": "Content-Type deve ser application/json."}
```

```json
{"detail": "JSON invalido."}
```

```json
{"errors": "..."}
```

Para `IntegrityError` de CPF/CNPJ duplicado, preservar:

```json
{"errors": {"cpf_cnpj": ["Ja existe um cliente com este CPF/CNPJ."]}}
```

## Estado atual conhecido

Arquivo atual:

- `caixa/views_clientes_api.py`

View atual:

- `api_clientes`

Rota atual:

- `path("api/clientes/", api_clientes, name="api_clientes")`

Frontend consumidor:

- `features/financial-dashboard/services/financial-clients-service.ts`

Helpers atuais de resposta:

- `api_authentication_required_response()`
- `api_permission_denied_response()`
- `api_no_store_json_response()`

Filtros aceitos no `GET`:

- `search`
- `busca`
- `personType`
- `tipo_pessoa`
- `active`
- `ativo`

Aliases aceitos no `POST`:

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

## PM-10.1 - Diagnostico read-only

Status: planejada.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas:

- Mapear a view atual.
- Mapear `GET /api/clientes/`.
- Mapear `POST /api/clientes/`.
- Mapear permissoes por metodo.
- Mapear payloads de sucesso.
- Mapear payloads de erro.
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

## PM-10.2 - Testes de paridade antes da migracao

Status: planejada.

Objetivo: congelar o comportamento atual de `/api/clientes/` antes de migrar
para DRF.

### Paridade de GET

Criar ou reforcar testes para:

- usuario anonimo recebe `401`;
- usuario autenticado sem `caixa.view_cliente` recebe `403`;
- usuario com `caixa.view_cliente` recebe `200`;
- `Content-Type` continua JSON;
- `Cache-Control` contem `no-store`;
- shape top-level continua `{"data": ...}`;
- `data.clients` mantem o mesmo conjunto de campos;
- `data.summary` mantem:
  - `total`;
  - `active`;
  - `inactive`;
  - `legalPersons`;
  - `naturalPersons`;
- `data.filters` preserva aliases:
  - `busca`;
  - `tipo_pessoa`;
  - `ativo`;
  - `search`;
  - `personType`;
  - `active`;
- `data.filterOptions.personTypes` preservado;
- `data.filterOptions.activeStatuses` preservado;
- `data.permissions.canCreate` preservado;
- `data.permissions.canUpdate` preservado;
- `data.meta.source` preservado;
- filtros canonicos e aliases continuam funcionando.

### Paridade de POST

Criar ou reforcar testes para:

- usuario anonimo recebe `401` quando a requisicao chega na view;
- usuario autenticado sem `caixa.add_cliente` recebe `403`;
- `POST` sem CSRF valido e bloqueado pelo comportamento atual com
  `Client(enforce_csrf_checks=True)`;
- `POST` com CSRF valido segue para permissao, validacao ou criacao;
- `Content-Type` invalido retorna `415`;
- JSON invalido retorna `400`;
- erro de validacao retorna `400` com `{"errors": ...}`;
- CPF/CNPJ duplicado retorna `400` com erro atual;
- criacao com sucesso retorna `201`;
- payload de sucesso contem:
  - `data.client`;
  - `data.message`;
- `data.client` mantem o mesmo conjunto de campos de `_serialize_cliente`;
- `Cache-Control` contem `no-store`;
- `Content-Type` continua JSON.

### Metodos nao permitidos

Validar que metodos fora do contrato continuam bloqueados, por exemplo:

- `PUT /api/clientes/`;
- `PATCH /api/clientes/`;
- `DELETE /api/clientes/`.

Gate de saida:

- Testes de paridade passam contra a implementacao Django pura atual.
- Nenhuma migracao feita ainda.

Validacoes recomendadas:

```bash
python manage.py test <testes_focados_de_clientes>
```

## PM-10.3 - Migracao de `/api/clientes/` para DRF

Status: planejada.

Objetivo: migrar somente `/api/clientes/` para DRF com paridade comprovada.

Preferencia de implementacao:

- usar `@api_view(["GET", "POST"])`;
- usar `Response` somente se os testes provarem paridade;
- usar permissoes locais equivalentes por metodo;
- reaproveitar helpers atuais de clientes;
- manter helpers atuais de erro ou respostas equivalentes no JSON.

Regras:

- Manter URL.
- Manter nome de rota.
- Manter metodos `GET` e `POST`.
- Manter status HTTP.
- Manter JSON.
- Manter headers relevantes.
- Manter CSRF real em `POST`.
- Manter autenticacao por sessao Django.
- Manter CORS sem alteracao.
- Nao criar serializer DRF complexo.
- Nao migrar `/api/clientes/<id>/`.

Cuidados tecnicos:

- O default global `IsAuthenticated` do DRF nao pode alterar contrato de erro.
- `SessionAuthentication` deve preservar CSRF em mutations.
- Permissao por metodo deve continuar diferenciando `view_cliente` e
  `add_cliente`.
- DRF nao deve substituir os JSONs atuais de `401`/`403` por respostas padrao
  se isso mudar contrato.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_clientes>
```

Gate de saida:

- `/api/clientes/` migrado para DRF.
- `GET` e `POST` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-10.4 - Revisao pos-migracao

Status: planejada.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_clientes>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/clientes/`;
- nenhuma regressao;
- nenhum outro endpoint migrado;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado ao endpoint, testes e registro do plano;
- `GET /api/clientes/` preservado;
- `POST /api/clientes/` preservado;
- `/api/clientes/<id>/` nao migrado;
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

## PM-10.5 - Fechamento e decisao sobre proximo endpoint

Status: planejada.

Objetivo: decidir se a migracao de clientes lista/criacao esta estavel antes de
abrir PM-11.

Tarefas:

- Registrar arquivos alterados.
- Registrar comandos executados.
- Registrar resultado dos testes.
- Registrar resultado do schema.
- Registrar riscos residuais.
- Confirmar que `/api/clientes/<id>/` ficou fora do escopo.
- Recomendar se PM-11 pode iniciar.

Proximo endpoint natural, somente se PM-10 estiver estavel:

- PM-11: `GET /api/clientes/<id>/` e `PUT /api/clientes/<id>/`.

## Criterios globais de aceite

- `GET /api/clientes/` mantem paridade.
- `POST /api/clientes/` mantem paridade.
- Autenticacao por sessao Django preservada.
- CSRF preservado.
- CORS preservado.
- Permissoes por metodo preservadas.
- JSONs de sucesso preservados.
- JSONs de erro preservados.
- Status HTTP preservados.
- Headers relevantes preservados.
- Aliases de filtro e payload preservados.
- Frontend nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/clientes/`.
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
- frontend precisar ser alterado;
- `/api/clientes/<id>/` precisar ser migrado junto;
- outro endpoint precisar ser migrado;
- DRF gerar resposta padrao diferente para `401`, `403`, `400`, `415` ou
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

- `/api/clientes/<id>/`.
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

Executar PM-10.1 como diagnostico read-only de `/api/clientes/`, sem migracao
e sem alteracao de codigo runtime.
