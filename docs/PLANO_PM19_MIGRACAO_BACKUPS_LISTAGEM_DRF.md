# Plano PM-19 - Migracao incremental de `GET /api/backups/` para DRF

Atualizado em: 2026-06-16

## Objetivo

Migrar exclusivamente `GET /api/backups/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da listagem de backups, sem alterar
regra de permissao, filesystem, selector, serializer manual, headers, status
HTTP, JSON ou contrato do frontend.

## Escopo

- Congelar o contrato atual em testes antes da migracao.
- Migrar apenas a view `api_backups`.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda.
- Preservar permissao atual de superuser.
- Preservar status HTTP, JSON, headers e aliases legados atuais.
- Preservar `405` e `Allow: GET`.
- Reaproveitar `listar_backups_disponiveis`.
- Reaproveitar `serializar_backup`.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `POST /api/backups/criar/`.
- Download de backup por `/backups/<nome_arquivo>/download/`.
- `backups_lista`.
- Criacao de backups.
- Limpeza de backups antigos.
- Mudancas no filesystem.
- Mudancas em storage.
- Mudancas em servicos de backup.
- Frontend.
- ViewSets.
- ModelViewSets.
- Serializers DRF.
- Alteracoes em settings, CORS, CSRF global ou autenticacao global.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = grupo pequeno e coeso quando o contrato for simples.

Nesta PM, somente a listagem `GET /api/backups/` deve ser migrada. A criacao
manual de backup fica para PM futura, por ser mutation com efeitos no
filesystem e no banco.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, filesystem ou comportamento
runtime apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-19.1

Arquivo atual:

- `caixa/views_backups.py`

View atual:

- `api_backups`

Rota atual:

- `path("api/backups/", api_backups, name="api_backups")`

Nome da rota:

- `caixa:api_backups`

Decoradores atuais:

- `@require_api_superuser`
- `@require_GET`

Metodo aceito:

- `GET`

Metodos nao permitidos:

- Para superuser, `POST`, `PUT`, `PATCH` e `DELETE` retornam `405`.
- Header `Allow` esperado: `GET`.
- Resposta atual de `405` e HTML vazia do Django.
- `Cache-Control` tambem recebe `no-store` por causa do decorator externo.

Permissao atual:

- exige usuario autenticado e `is_superuser=True`;
- nao depende de permissao de model;
- usuario staff nao-superuser nao deve ser aceito apenas por ser staff.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado nao-superuser:

```json
{"detail": "Permission denied."}
```

com status `403`.

Payload de sucesso com backups:

```json
{
  "backups": [
    {
      "name": "backup_banco_2026-06_20260601_010203_000001.json",
      "nome": "backup_banco_2026-06_20260601_010203_000001.json",
      "sizeMb": 0.0,
      "tamanho_mb": 0.00000667572021484375,
      "createdAt": "2027-01-15T05:00:00-03:00",
      "criado_em": 1800000000.0,
      "downloadPath": "/backups/backup_banco_2026-06_20260601_010203_000001.json/download/"
    }
  ]
}
```

Payload de sucesso sem backups:

```json
{"backups": []}
```

Campos de cada item:

- `name`
- `nome`
- `sizeMb`
- `tamanho_mb`
- `createdAt`
- `criado_em`
- `downloadPath`

Status codes atuais:

- `200`: sucesso para superuser;
- `401`: usuario anonimo;
- `403`: usuario autenticado nao-superuser;
- `405`: metodo nao permitido.

Headers relevantes:

- respostas JSON usam `Content-Type: application/json`;
- respostas JSON usam `Cache-Control` com `no-store`;
- `405` preserva `Allow: GET`;
- `405` usa `Content-Type: text/html; charset=utf-8`.

Dependencias atuais:

- filesystem local em `BASE_DIR/backups/db`;
- `Path(settings.BASE_DIR)`;
- `Path.glob("backup_banco_*.json")`;
- `Path.stat().st_size`;
- `Path.stat().st_mtime`;
- `timezone.get_current_timezone`;
- `reverse("caixa:backup_download", args=[nome])`;
- selector `listar_backups_disponiveis`;
- serializer manual `serializar_backup`.

Dependencias nao utilizadas pela listagem:

- Oracle Cloud;
- OCI;
- S3/boto;
- storage remoto;
- `criar_backup_banco`;
- `dumpdata`;
- limpeza de backups antigos.

Regras de listagem:

- se `BASE_DIR/backups/db` nao existe, retorna lista vazia;
- lista somente arquivos `backup_banco_*.json`;
- ignora arquivos `.meta.json`;
- ignora diretorios;
- ignora arquivos fora do padrao;
- ordena por nome em ordem reversa;
- calcula `sizeMb` arredondado em 4 casas;
- mantem `tamanho_mb` com valor bruto em MB;
- `createdAt` vem de `mtime` convertido para timezone corrente;
- `criado_em` preserva timestamp bruto do `mtime`.

## Riscos especificos da listagem de backups

- DRF pode trocar `401` e `403` se usar permissao padrao.
- DRF pode trocar `405` e `Allow: GET`.
- DRF pode remover `Cache-Control`/`no-store`.
- Campos duplicados legados podem ser perdidos se houver serializer novo.
- Ordenacao por nome reverso pode mudar se a migracao reimplementar selector.
- Arquivos `.meta.json` ou fora do padrao podem aparecer se o filtro mudar.
- `downloadPath` pode mudar se nao reaproveitar `reverse` atual.
- O endpoint le filesystem local; testes devem usar `BASE_DIR` temporario para
  nao depender do ambiente real.

## Guardrails

- Nao alterar `/api/backups/criar/`.
- Nao alterar download de backup.
- Nao alterar `backups_lista`.
- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao criar serializer DRF.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao alterar `listar_backups_disponiveis`, salvo necessidade tecnica
  demonstrada e registrada.
- Nao alterar `serializar_backup`, salvo necessidade tecnica demonstrada e
  registrada.
- Nao acessar ou criar backups reais fora de `BASE_DIR` temporario em testes.
- Reaproveitar helpers atuais sempre que possivel.
- Usar permissao manual de superuser se necessario para preservar `401` e
  `403`.
- Priorizar paridade runtime sobre schema OpenAPI.

## PM-19.1 - Diagnostico read-only

Status: concluida.

Objetivo: mapear o contrato real antes de alterar qualquer codigo runtime.

Tarefas realizadas:

- View atual identificada.
- URL e nome de rota identificados.
- Metodo aceito identificado.
- Comportamento de metodos nao permitidos identificado.
- Permissao atual identificada.
- Comportamento de anonimo identificado.
- Comportamento de autenticado nao-superuser identificado.
- Dependencias de filesystem identificadas.
- Shape de sucesso e erros identificado.
- Status HTTP atuais identificados.
- Headers relevantes identificados.
- Campos retornados identificados.
- Testes existentes relacionados identificados.
- Lacunas de paridade identificadas.

Gate de saida:

- Contrato atual descrito.
- Lacunas de paridade listadas.
- Nenhum arquivo alterado.

## PM-19.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo: criar ou reforcar testes de paridade contra a implementacao atual,
antes de qualquer migracao para DRF.

Criar ou reforcar testes para:

- anonimo retorna `401` com JSON atual;
- usuario autenticado nao-superuser retorna `403` com JSON atual;
- usuario staff nao-superuser continua `403`;
- superuser retorna `200`;
- shape completo de sucesso com lista nao vazia;
- shape `{"backups": []}` quando nao houver backups;
- headers JSON/no-store em `401`, `403` e `200`;
- metodos `POST`, `PUT`, `PATCH` e `DELETE` retornam `405`;
- header `Allow: GET` preservado;
- arquivos `.meta.json` sao ignorados;
- arquivos fora do padrao `backup_banco_*.json` sao ignorados;
- diretorios com nome compatível sao ignorados;
- `downloadPath` preservado;
- ordenacao por nome em ordem reversa preservada;
- aliases legados preservados:
  - `name` e `nome`;
  - `sizeMb` e `tamanho_mb`;
  - `createdAt` e `criado_em`.

Validacao recomendada:

```bash
python manage.py check
python manage.py test <testes_focados_de_backups>
```

Gate de saida:

- Testes de paridade passam contra a implementacao Django puro atual.
- Nenhuma migracao feita ainda.
- Nenhuma alteracao de frontend.

## PM-19.3 - Migracao controlada para DRF

Status: concluida.

Objetivo: migrar somente `api_backups` para DRF com paridade comprovada.

Implementacao esperada:

- converter somente `api_backups`;
- usar `@api_view(["GET"])`;
- usar `Response` somente na borda;
- preservar `@require_GET` se necessario para manter `405` e `Allow: GET`;
- preservar permissao manual de superuser;
- preservar `401` e `403` atuais;
- preservar `405` e `Allow: GET`;
- reaproveitar `listar_backups_disponiveis`;
- reaproveitar `serializar_backup`;
- nao criar serializer DRF;
- nao criar `ViewSet`;
- nao criar `ModelViewSet`;
- nao mexer em criacao/download de backups.

Regras:

- Manter URL `/api/backups/`.
- Manter nome de rota `caixa:api_backups`.
- Manter metodo `GET`.
- Manter status HTTP.
- Manter JSON de sucesso.
- Manter JSONs de erro.
- Manter headers relevantes.
- Manter `Cache-Control`/`no-store`.
- Manter `Allow: GET`.
- Manter permissao de superuser.
- Manter CORS sem alteracao.
- Reaproveitar helpers atuais.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_backups>
```

Gate de saida:

- `/api/backups/` migrado para DRF.
- `GET` mantem paridade.
- Nenhum outro endpoint alterado.

## PM-19.4 - Validacao completa

Status: concluida.

Objetivo: confirmar que a migracao preservou contrato e nao abriu regressao.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes_focados_de_backups>
python manage.py test <testes_relacionados_de_backups>
python manage.py test
```

Validar:

- frontend preservado;
- contrato preservado;
- OpenAPI inclui `/api/backups/`;
- nenhuma regressao;
- `/api/backups/criar/` nao foi alterado;
- download de backup nao foi alterado;
- settings, CORS, CSRF global e auth global nao foram alterados;
- nenhum `schema.yml` temporario ficou no workspace, se gerado apenas para
  validacao.

Checklist:

- diff limitado a `/api/backups/`, testes e registro do plano;
- filesystem real nao usado nos testes de paridade;
- selector atual reaproveitado;
- serializer manual atual reaproveitado;
- frontend nao alterado;
- `git status --short` registrado.

Gate de saida:

- testes focados passam;
- testes relacionados de backups passam;
- suite geral passa;
- warnings do spectacular registrados;
- riscos residuais registrados;
- recomendacao final registrada.

## PM-19.5 - Encerramento

Status: concluida.

Objetivo: registrar o resultado final da PM-19 antes de avancar para outro
endpoint.

Tarefas:

- Atualizar este documento.
- Registrar arquivos alterados.
- Registrar testes criados.
- Registrar comandos executados.
- Registrar resultado dos testes focados.
- Registrar resultado dos testes relacionados de backups.
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

Proximo passo natural, somente se PM-19 estiver estavel:

- retomar o roadmap PM-17 e escolher o proximo endpoint de baixo risco.

## Criterios globais de aceite

- `GET /api/backups/` mantem paridade.
- URL preservada.
- Nome de rota preservado.
- Metodo `GET` preservado.
- Status HTTP preservados.
- JSON de sucesso preservado.
- JSONs de erro preservados.
- Headers relevantes preservados.
- `Cache-Control`/`no-store` preservado nas respostas JSON.
- Header `Allow: GET` preservado nos `405`.
- Permissao de superuser preservada.
- Usuario staff nao-superuser continua sem acesso.
- Campos e aliases legados preservados.
- Ordenacao por nome reverso preservada.
- Arquivos `.meta.json` ignorados.
- Arquivos fora do padrao ignorados.
- `downloadPath` preservado.
- Frontend nao alterado.
- `/api/backups/criar/` nao alterado.
- Download de backup nao alterado.
- Nenhum outro endpoint migrado.
- OpenAPI passa a documentar `/api/backups/`.
- 100% dos testes focados passam.
- Suite geral passa ou qualquer impossibilidade local fica registrada.

## Criterios de bloqueio

Parar imediatamente se:

- JSON mudar;
- status HTTP mudar;
- header relevante mudar;
- permissao mudar;
- superuser deixar de acessar;
- usuario anonimo receber contrato diferente;
- usuario autenticado nao-superuser receber contrato diferente;
- usuario staff nao-superuser passar a acessar;
- `Allow: GET` mudar;
- ordenacao mudar;
- `.meta.json` passar a aparecer;
- arquivo fora do padrao passar a aparecer;
- `downloadPath` mudar;
- aliases legados forem removidos;
- filesystem real precisar ser alterado;
- frontend precisar ser alterado;
- `/api/backups/criar/` precisar ser alterado;
- download de backup precisar ser alterado;
- outro endpoint precisar ser alterado;
- DRF gerar resposta padrao diferente para `401`, `403` ou `405`;
- serializer DRF se tornar necessario para regra de negocio;
- houver necessidade de alterar settings, CORS, CSRF global ou auth global.

## Estrategia de rollback

Rollback preferencial:

- Reverter somente a alteracao runtime da view `api_backups`.
- Manter testes de paridade quando eles apenas congelam o contrato atual.
- Remover ou ajustar anotacoes OpenAPI locais se elas estiverem ligadas ao
  problema.
- Nao reverter alteracoes de PMs anteriores.

Se a migracao alterar contrato:

- Parar a PM.
- Restaurar a implementacao Django puro da view `api_backups`.
- Rodar testes focados para confirmar retorno ao comportamento anterior.
- Registrar o motivo do rollback neste documento.

Se apenas o schema OpenAPI falhar:

- Nao alterar runtime para satisfazer schema.
- Registrar warning/erro.
- Avaliar `extend_schema` local seguro.
- Se nao houver anotacao segura, aceitar schema incompleto e preservar
  paridade.

Se filesystem, listagem ou ordenacao divergirem:

- Parar a PM.
- Reverter a migracao runtime.
- Manter testes que detectaram a divergencia.
- Registrar exatamente qual efeito divergiu.

## Registro de execucao

### Registro de execucao - PM-19.1

Fase: diagnostico read-only.

Endpoint alvo:

- `GET /api/backups/`

Arquivos lidos:

- `caixa/views_backups.py`
- `caixa/urls.py`
- `caixa/permissions.py`
- `caixa/selectors_backups.py`
- `caixa/services_backups.py`
- `config/settings.py`
- `caixa/tests.py`

Resultado:

- Contrato atual de `/api/backups/` mapeado.
- View ainda estava Django puro.
- Dependencia de filesystem local identificada em `BASE_DIR/backups/db`.
- Nenhuma dependencia de Oracle Cloud, OCI, S3/boto ou storage remoto foi
  identificada na listagem.
- Lacunas de paridade identificadas para autenticao, superuser, headers,
  metodos nao permitidos, shape de sucesso, lista vazia, aliases legados,
  filtros de arquivos e ordenacao.
- Nenhum arquivo alterado nesta fase.

`git status --short` observado ao final da PM-19.1:

```text
 M caixa/tests.py
 M caixa/views_api_auth.py
?? docs/PLANO_PM18_MIGRACAO_AUTH_LOGIN_LOGOUT_DRF.md
```

### Registro de execucao - PM-19.2

Status: concluida.

Fase: congelamento de contrato em testes.

Arquivo alterado:

- `caixa/tests.py`

Testes criados/reforcados:

- `SegurancaTests.test_api_backups_exige_superusuario`
  - passou a validar anonimo `401`, usuario comum `403`, staff
    nao-superuser `403`, superuser `200`, JSON exato de erro e
    `Cache-Control` com `no-store`.
- `SegurancaTests.test_api_backups_lista_vazia_e_metodos_nao_permitidos_preservam_contrato`
  - congela `{"backups": []}` quando nao ha backups;
  - congela `POST`, `PUT`, `PATCH` e `DELETE` como `405`;
  - congela `Allow: GET`.
- `SegurancaTests.test_api_backups_preserva_shape_filtros_de_arquivo_aliases_e_ordenacao`
  - congela campos `name`, `nome`, `sizeMb`, `tamanho_mb`, `createdAt`,
    `criado_em` e `downloadPath`;
  - congela ordenacao por nome em ordem reversa;
  - congela filtro de arquivos para ignorar `.meta.json`, arquivos fora do
    padrao e diretorios.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py test caixa.tests.SegurancaTests
venv\Scripts\python.exe manage.py check
```

Resultados:

- `SegurancaTests`: 18 testes executados, todos OK.
- `check`: OK, sem issues.
- Nenhuma view foi migrada nesta fase.

### Registro de execucao - PM-19.3

Status: concluida.

Fase: migracao controlada para DRF.

Arquivos alterados:

- `caixa/views_backups.py`

Implementacao:

- `api_backups` foi migrada para DRF com `@api_view(["GET"])`.
- `Response` passou a ser usado somente na borda deste endpoint.
- `@require_GET` foi preservado para manter `405` e `Allow: GET`.
- `@never_cache` foi aplicado localmente para preservar `Cache-Control` com
  `no-store`.
- `AllowAny` foi usado localmente para impedir que a permissao global do DRF
  substitua os JSONs atuais.
- A checagem manual de `request.user.is_authenticated` preserva o `401` atual.
- A checagem manual de `request.user.is_superuser` preserva o `403` atual.
- `listar_backups_disponiveis` foi reaproveitado.
- `serializar_backup` foi reaproveitado.

Nao alterado:

- `/api/backups/criar/`.
- `/backups/<nome_arquivo>/download/`.
- `backups_lista`.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Serializer, ViewSet ou ModelViewSet.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.SegurancaTests
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados; schema inclui
  `/api/backups/`.
- `SegurancaTests`: 18 testes executados, todos OK.

### Registro de execucao - PM-19.4

Status: concluida.

Fase: validacao completa.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.SegurancaTests
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK, sem issues.
- `spectacular --validate`: OK, sem warnings observados; schema inclui
  `/api/backups/`.
- `SegurancaTests`: 18 testes executados, todos OK.
- Suite completa: 710 testes executados, todos OK.
- Warnings de log durante a suite completa ficaram limitados a cenarios
  esperados de CSRF/login/logout ja cobertos por testes.
- `schema.yml` nao foi gerado nesta PM.
- Nenhuma regressao identificada.

### Registro de execucao - PM-19.5

Status: concluida.

Fase: encerramento.

Arquivos alterados pela PM-19:

- `caixa/tests.py`
- `caixa/views_backups.py`
- `docs/PLANO_PM19_MIGRACAO_BACKUPS_LISTAGEM_DRF.md`

Dependencias adicionadas:

- Nenhuma.

Endpoint migrado:

- `GET /api/backups/`

Endpoints nao alterados:

- `POST /api/backups/criar/`
- `/backups/<nome_arquivo>/download/`
- `backups_lista`
- Demais endpoints `/api/*`

Confirmacoes finais:

- URL preservada.
- Nome de rota `caixa:api_backups` preservado.
- Metodo `GET` preservado.
- `401`, `403`, `200` e `405` preservados.
- JSONs de erro preservados.
- Shape de sucesso preservado.
- Campos e aliases legados preservados.
- Ordenacao por nome reverso preservada.
- `downloadPath` preservado.
- `Allow: GET` preservado.
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
- A listagem continua dependente do filesystem local em `BASE_DIR/backups/db`,
  como ja ocorria antes da migracao.

Recomendacao:

- PM-19 pronta para commit local manual junto com as demais alteracoes
  pendentes que o mantenedor decidir agrupar.
