# Plano PM-33 - Migracao incremental de `POST /api/backups/criar/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar de forma incremental e controlada o endpoint
`POST /api/backups/criar/` para Django REST Framework, preservando
integralmente o contrato atual consumido pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da view de criacao manual de backup,
sem alterar regra de negocio, permissao, CSRF, headers, status HTTP, payloads,
nome dos arquivos, metadata, limpeza de backups antigos ou contrato do
frontend.

## Escopo

- Congelar o contrato atual de criacao manual de backup em testes antes da
  migracao.
- Migrar somente a view `api_backup_criar_manual`.
- Manter a URL atual `/api/backups/criar/`.
- Manter o nome de rota `caixa:api_backup_criar_manual`.
- Manter somente o metodo `POST`.
- Usar `@api_view(["POST"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_POST`, ou mecanismo equivalente, para manter o `405`
  atual.
- Preservar CSRF real no `POST`.
- Preservar autenticacao e permissao manual de superuser.
- Preservar comportamento atual de ignorar body, `Content-Type` e JSON
  invalido.
- Reaproveitar `criar_backup_banco(force=True)` e o helper atual
  `serializar_backup`.
- Preservar criacao de `.json`, `.meta.json`, nome, `downloadPath` e limpeza
  de backups antigos.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Listagem de backups `GET /api/backups/`.
- Download de backups `/backups/<nome_arquivo>/download/`.
- Tela HTML/redirect de backups.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Serializers DRF.
- ViewSets.
- ModelViewSets.
- Refatoracao do service de backup.
- Alteracao de selectors/helpers compartilhados.
- Alteracao de formato, local ou politica de retencao de backups.
- Criacao de backup real na etapa de planejamento.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, migrar somente `POST /api/backups/criar/`.

Como este endpoint possui efeito colateral em filesystem e executa `dumpdata`,
a PM deve manter a regra de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- testes com diretório temporario para impedir backup real;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, comportamento de
body, criacao de arquivos, metadata ou limpeza de backups apenas para melhorar
a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-33.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_backups.py`.
- `caixa/permissions.py`.
- `caixa/services_backups.py`.
- `caixa/selectors_backups.py`.
- `caixa/tests.py`.

View atual:

- `api_backup_criar_manual`.

Rota atual:

- `path("api/backups/criar/", api_backup_criar_manual, name="api_backup_criar_manual")`.

Nome de rota:

- `caixa:api_backup_criar_manual`.

Decoradores atuais:

- `@require_api_superuser`.
- `@require_POST`.

Metodo aceito:

- `POST`.

Metodos nao permitidos:

- `GET`, `PUT`, `PATCH`, `DELETE` e outros devem preservar `405`.
- Header `Allow`: `POST`.
- A migracao deve preservar o comportamento atual observado para `405`,
  considerando a ordem dos decorators e a permissao de superuser.

Autenticacao e permissao:

- Usuario anonimo recebe `401`.
- Usuario autenticado nao-superuser recebe `403`.
- Usuario superuser pode criar backup manual.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado nao-superuser:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

CSRF atual:

- `POST` usa CSRF real do Django.
- Sem token valido, a requisicao deve ser bloqueada antes da view com `403`
  HTML.
- A migracao nao pode alterar CSRF global.

Body, payload e Content-Type:

- A view nao le `request.body`.
- A view nao acessa `request.POST`.
- A view nao acessa `request.data`.
- A view nao exige `application/json`.
- `Content-Type` invalido continua aceito/ignorado quando a requisicao passa
  por CSRF, autenticacao e permissao.
- JSON invalido continua ignorado quando a requisicao passa por CSRF,
  autenticacao e permissao.
- Nenhum body/payload altera o comportamento atual.

Fluxo de sucesso:

- A view chama `criar_backup_banco(force=True)`.
- Se `resultado["arquivo"]` existir, procura o backup recem-criado em
  `listar_backups_disponiveis()`.
- Serializa o backup com `serializar_backup`.
- Retorna JSON com headers no-store.

Status de sucesso:

- `201` quando `resultado["criado"]` e verdadeiro.
- `200` quando `resultado["criado"]` e falso.

Shape completo de sucesso:

```json
{
  "created": true,
  "criado": true,
  "message": "...",
  "mensagem": "...",
  "removedCount": 0,
  "removidos": 0,
  "backup": {}
}
```

Shape completo de `backup`:

```json
{
  "name": "...",
  "nome": "...",
  "sizeMb": 0.0,
  "tamanho_mb": 0.0,
  "createdAt": "...",
  "criado_em": 0.0,
  "downloadPath": "/backups/.../download/"
}
```

Erro interno:

```json
{"detail": "Não foi possível criar o backup manual. Verifique os logs do servidor."}
```

com status `500`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Efeitos colaterais:

- Cria diretorio `BASE_DIR/backups/db`, se necessario.
- Executa `dumpdata` para arquivo temporario.
- Cria arquivo `backup_banco_{YYYY-MM}_{YYYYMMDD_HHMMSS_micro}.json`.
- Cria arquivo `backup_banco_{YYYY-MM}_{YYYYMMDD_HHMMSS_micro}.meta.json`.
- Escreve metadata em UTF-8 com `ensure_ascii=False`.
- Remove backups antigos mantendo 3 por padrao.
- Remove o arquivo temporario ao final.

Metadata atual:

```json
{
  "arquivo": "...",
  "criado_em": "...",
  "mes_referencia": "...",
  "sha256": "...",
  "tamanho_bytes": 0
}
```

Dependencias atuais:

- `criar_backup_banco(force=True)`.
- `listar_backups_disponiveis`.
- `serializar_backup`.
- `api_no_store_json_response`.
- `require_api_superuser`.
- `require_POST`.
- `dumpdata`.
- Filesystem local em `BASE_DIR/backups/db`.

Transacoes ou lock:

- Nao ha `transaction.atomic` identificado.
- Nao ha lock explicito identificado.
- Existe risco de concorrencia se duas criacoes manuais ocorrerem ao mesmo
  tempo; esta PM nao deve alterar esse comportamento.

Testes existentes:

- `test_backup_manual_exige_superusuario`.
- `test_superusuario_cria_backup_manual_pela_api`.
- `test_comando_backup_mensal_continua_criando_e_evitando_duplicado`.
- Testes relacionados de listagem/download em `SegurancaTests`.

Lacunas identificadas:

- CSRF real com `Client(enforce_csrf_checks=True)`.
- Anonimo `401` com JSON/no-store.
- Nao-superuser `403` com JSON/no-store.
- `Content-Type` invalido aceito/ignorado.
- JSON invalido aceito/ignorado.
- Body/payload sem efeito.
- `405` e `Allow: POST`.
- Shape completo do sucesso e de `backup`.
- Erro interno mockado `500`.
- Criacao de `.json` e `.meta.json`.
- Metadata completa.
- Remocao de backups antigos.
- Garantia de que testes nao criam backup real fora de diretorio temporario.

## Riscos especificos do backup manual

- Cria arquivos reais se `BASE_DIR` nao for isolado nos testes.
- Executa `dumpdata`, podendo ser mais lento que endpoints comuns.
- Possui efeito colateral em filesystem e metadata.
- Pode remover backups antigos por politica de retencao.
- Nao possui lock explicito contra execucoes concorrentes.
- A ordem dos decorators influencia `401`, `403`, `405` e CSRF.
- Migrar para DRF pode tentar parsear body automaticamente e mudar o contrato
  de `Content-Type`/JSON invalido.
- `Response` DRF pode alterar headers se usado fora da borda.
- O schema OpenAPI pode ficar incompleto, mas isso nao justifica mudar runtime.

## Guardrails

- Nao executar backup real durante planejamento.
- Em testes, sempre usar `TemporaryDirectory` e `override_settings(BASE_DIR=...)`
  para qualquer caso que crie arquivo.
- Nao acessar `request.data` na view migrada.
- Nao exigir `application/json`.
- Nao validar body.
- Nao criar serializer DRF.
- Nao criar ViewSet ou ModelViewSet.
- Nao alterar `criar_backup_banco`.
- Nao alterar `serializar_backup`.
- Nao alterar `listar_backups_disponiveis`.
- Nao alterar listagem/download de backups.
- Nao alterar CSRF global, auth global, CORS ou settings.
- Preservar runtime mesmo que o schema OpenAPI fique generico.

## Fases

### PM-33.1 - Diagnostico read-only

Status: concluida.

Objetivo:

- Mapear contrato atual de `POST /api/backups/criar/`.
- Identificar arquivos, permissao, CSRF, payloads, headers, efeitos colaterais
  e lacunas de teste.

Resultado:

- Endpoint permanece Django puro.
- Contrato atual foi mapeado por leitura de codigo e testes existentes.
- Nenhum arquivo foi alterado.
- Nenhum backup real foi criado.

### PM-33.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.
- Garantir que toda criacao de backup nos testes use diretorio temporario.

Cobrir:

- `POST` anonimo `401` com JSON/no-store.
- `POST` autenticado nao-superuser `403` com JSON/no-store.
- `POST` superuser com CSRF valido chega na view.
- CSRF real: sem token valido bloqueia antes da view com `403` HTML.
- `Content-Type` invalido continua aceito/ignorado.
- JSON invalido continua ignorado.
- Nenhum body/payload altera o comportamento.
- `GET`, `PUT`, `PATCH` e `DELETE` preservam `405` com `Allow: POST`.
- Shape completo do sucesso:
  - `created`.
  - `criado`.
  - `message`.
  - `mensagem`.
  - `removedCount`.
  - `removidos`.
  - `backup`.
- Shape completo de `backup`:
  - `name`.
  - `nome`.
  - `sizeMb`.
  - `tamanho_mb`.
  - `createdAt`.
  - `criado_em`.
  - `downloadPath`.
- Erro interno mockado retorna `500` com:

```json
{"detail": "Não foi possível criar o backup manual. Verifique os logs do servidor."}
```

- Criacao de `.json` e `.meta.json` em diretorio temporario.
- Metadata preserva:
  - `arquivo`.
  - `criado_em`.
  - `mes_referencia`.
  - `sha256`.
  - `tamanho_bytes`.
- Remocao de backups antigos preservada.
- Nenhum backup real deve ser criado durante os testes.

Comandos previstos:

```bash
python manage.py check
python manage.py test caixa.tests.SegurancaTests
```

Critério de aceite da fase:

- Testes focados passam.
- Nenhum arquivo runtime alterado.
- Endpoint ainda nao migrado para DRF.
- Nenhum backup real criado.

Resultado:

- Testes de paridade adicionados em `caixa/tests.py`.
- Cobertos auth/permissao, CSRF real, body/Content-Type/JSON ignorados,
  metodos nao permitidos, erro interno, shape de sucesso, shape de `backup`,
  metadata e limpeza de backups antigos.
- Casos que criam backup usam `TemporaryDirectory` e
  `override_settings(BASE_DIR=...)`.
- Testes focados passaram antes da migracao.

### PM-33.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Migrar somente `api_backup_criar_manual` para DRF, preservando o contrato
  runtime congelado na PM-33.2.

Regras:

- Converter somente `api_backup_criar_manual`.
- Usar `@api_view(["POST"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_POST`, ou equivalente, para manter `405`.
- Preservar CSRF real no `POST`.
- Preservar autenticacao/superuser manual:
  - anonimo `401`;
  - nao-superuser `403`;
  - superuser permitido.
- Preservar comportamento de ignorar body, `Content-Type` e JSON invalido.
- Reaproveitar `criar_backup_banco(force=True)`.
- Reaproveitar `serializar_backup`.
- Preservar criacao de `.json`, `.meta.json`, nome, `downloadPath` e limpeza
  de antigos.
- Nao criar Serializer, ViewSet ou ModelViewSet.
- Nao mexer na listagem/download de backups.

Comandos previstos:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.SegurancaTests
```

Critério de aceite da fase:

- Testes focados passam.
- `check` passa.
- `spectacular --validate` passa, mesmo que o schema seja generico.
- OpenAPI inclui `/api/backups/criar/`.
- Nenhum contrato runtime alterado.

Resultado:

- `api_backup_criar_manual` migrado para DRF.
- Usado `@api_view(["POST"])`.
- Usado `Response` apenas na borda de sucesso e erro interno.
- Reaproveitado `csrf_protect_drf_view` ja existente.
- Reaproveitado `IgnoreBodyParser` ja existente para preservar body ignorado.
- Mantidos `require_api_superuser`, `require_POST`,
  `criar_backup_banco(force=True)` e `serializar_backup`.
- OpenAPI passou a incluir `/api/backups/criar/`.

### PM-33.4 - Validacao completa

Status: concluida.

Objetivo:

- Validar que a migracao nao causou regressao em backups, seguranca e suite
  geral.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.SegurancaTests
python manage.py test
```

Validar:

- Testes focados de backup.
- Testes relacionados existentes de seguranca/backups.
- Suite completa.
- Sem mudanca em listagem/download.
- Sem mudanca em settings, CORS, CSRF global ou autenticacao global.
- Nenhum backup real criado fora de diretorio temporario.

Critério de aceite da fase:

- Todos os comandos passam.
- Sem mudanca de contrato.
- Sem efeito colateral fora dos testes isolados.

Resultado:

- `python manage.py check` passou.
- `python manage.py spectacular --validate` passou sem warnings observados.
- `python manage.py test caixa.tests.SegurancaTests` passou com 24 testes.
- `python manage.py test` passou com 783 testes.
- Logs esperados de CSRF e erro interno mockado apareceram durante os testes.

### PM-33.5 - Encerramento

Status: concluida.

Objetivo:

- Atualizar este documento com registro final da execucao.

Registrar:

- Arquivos alterados.
- Testes criados/alterados.
- Comandos executados e resultados.
- Resultado do `check`.
- Resultado do `spectacular --validate`.
- Resultado dos testes focados.
- Resultado da suite completa.
- Warnings, se houver.
- Confirmacao de que nenhum backup real foi criado fora dos testes isolados.
- Confirmacao de que listagem/download de backups nao foram alterados.
- Confirmacao de que settings, CORS, CSRF global e auth global nao foram
  alterados.
- Confirmacao de pronto ou nao para commit manual.

## Criterios de aceite da PM

- `POST /api/backups/criar/` migrado para DRF.
- URL e nome de rota preservados.
- Metodo `POST` preservado.
- `405` e `Allow: POST` preservados.
- CSRF real preservado.
- Anonimo recebe `401` atual.
- Nao-superuser recebe `403` atual.
- Superuser cria backup com o mesmo contrato.
- `Content-Type` invalido e JSON invalido continuam ignorados.
- Shape de sucesso preservado.
- Shape de `backup` preservado.
- Erro interno `500` preservado.
- Arquivo `.json` e `.meta.json` preservados.
- Metadata preservada.
- Limpeza de backups antigos preservada.
- Nenhum backup real criado fora de diretorios temporarios nos testes.
- Listagem/download de backups nao alterados.
- Frontend nao alterado.
- Settings, CORS, CSRF global e auth global nao alterados.
- Sem Serializer DRF, ViewSet ou ModelViewSet.
- `python manage.py check` passa.
- `python manage.py spectacular --validate` passa.
- Testes focados passam.
- Suite completa passa.

## Criterios de bloqueio

Parar imediatamente se:

- CSRF mudar.
- `Content-Type` invalido passar a retornar erro.
- JSON invalido passar a retornar erro.
- Body/payload passar a alterar comportamento.
- `401`, `403`, `405`, `500` ou status de sucesso mudarem.
- Shape de sucesso mudar.
- Shape de `backup` mudar.
- Nome, local ou metadata dos arquivos mudar.
- Limpeza de backups antigos mudar.
- Algum teste criar backup real fora de diretorio temporario.
- Listagem/download de backups precisarem ser alterados.
- For necessario criar Serializer, ViewSet ou ModelViewSet.
- For necessaria decisao arquitetural fora do escopo.

## Estrategia de rollback

Se a migracao causar qualquer divergencia de contrato:

- Reverter apenas as alteracoes da PM-33.3 em `api_backup_criar_manual`.
- Manter os testes de paridade da PM-33.2, se eles estiverem corretos e
  representarem o contrato atual.
- Remover somente ajustes de teste que dependam da implementacao migrada.
- Confirmar que `POST /api/backups/criar/` voltou ao comportamento Django puro.
- Rodar testes focados de backup e `python manage.py check`.

Nao usar rollback destrutivo de git sem aprovacao explicita.

## Registro de execucao

### PM-33.1

Status: concluida.

Resumo:

- Diagnostico read-only realizado.
- Nenhum arquivo alterado.
- Nenhum backup real criado.
- Contrato atual documentado neste plano.

### PM-33.2

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados/reforcados:

- `test_api_backup_criar_manual_preserva_auth_permissao_e_headers`.
- `test_api_backup_criar_manual_preserva_csrf_real`.
- `test_api_backup_criar_manual_ignora_body_content_type_e_json`.
- `test_api_backup_criar_manual_preserva_metodos_nao_permitidos`.
- `test_api_backup_criar_manual_preserva_erro_interno`.
- `test_superusuario_cria_backup_manual_pela_api` reforcado com shape completo,
  arquivo `.json` e metadata.
- `test_api_backup_criar_manual_preserva_limpeza_de_backups_antigos`.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.SegurancaTests
```

Resultado:

- `check`: OK.
- `SegurancaTests`: 24 testes OK.
- Nenhum backup real criado fora de diretorio temporario.

### PM-33.3

Status: concluida.

Arquivos alterados:

- `caixa/views_backups.py`.

Resumo da migracao:

- Migrado somente `api_backup_criar_manual`.
- Adicionado `@api_view(["POST"])`.
- Adicionado `@parser_classes([IgnoreBodyParser])`.
- Adicionado `@permission_classes([AllowAny])`.
- Adicionado `@extend_schema`.
- Reaproveitado `csrf_protect_drf_view`.
- Mantidos `require_api_superuser` e `require_POST`.
- Mantidos `criar_backup_banco(force=True)`, `listar_backups_disponiveis` e
  `serializar_backup`.
- `Response` usado apenas para sucesso e erro interno da borda HTTP.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.SegurancaTests
```

Resultado:

- `check`: OK.
- `spectacular --validate`: OK.
- `SegurancaTests`: 24 testes OK.
- OpenAPI inclui `/api/backups/criar/`.
- Nenhum contrato runtime alterado.

### PM-33.4

Status: concluida.

Comandos executados:

```bash
DEBUG=True SECRET_KEY=local-validation-secret python manage.py check
DEBUG=True SECRET_KEY=local-validation-secret python manage.py spectacular --validate
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test caixa.tests.SegurancaTests
DEBUG=True SECRET_KEY=local-validation-secret python manage.py test
```

Resultado:

- `check`: OK.
- `spectacular --validate`: OK, sem warnings observados.
- `SegurancaTests`: 24 testes OK.
- Suite completa: 783 testes OK.
- Logs esperados:
  - CSRF bloqueado nos testes de CSRF real.
  - Erro interno mockado no teste de `500`.
- Nenhum backup real criado fora de diretorio temporario.
- Listagem/download de backups nao foram alterados.
- Settings, CORS, CSRF global e auth global nao foram alterados.

### PM-33.5

Status: concluida.

Arquivos alterados na PM-33:

- `caixa/tests.py`.
- `caixa/views_backups.py`.
- `docs/PLANO_PM33_MIGRACAO_BACKUP_MANUAL_DRF.md`.

Confirmacoes finais:

- `POST /api/backups/criar/` migrado para DRF.
- URL e nome de rota preservados.
- Metodo `POST` preservado.
- Auth/superuser preservados.
- CSRF real preservado.
- Body, `Content-Type` e JSON invalido continuam ignorados.
- Shape de sucesso preservado.
- Shape de `backup` preservado.
- Metadata preservada.
- Limpeza de backups antigos preservada.
- Listagem/download de backups nao alterados.
- Nenhum Serializer, ViewSet ou ModelViewSet criado.
- Frontend, settings, CORS, CSRF global e auth global nao alterados.
- Pronto para revisao e commit manual local.
