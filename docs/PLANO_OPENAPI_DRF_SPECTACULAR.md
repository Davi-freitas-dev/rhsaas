# Plano OpenAPI inicial com DRF e drf-spectacular

Atualizado em: 2026-06-15

## Objetivo

Adicionar Django REST Framework e drf-spectacular como infraestrutura inicial de
OpenAPI/Swagger, sem migracao funcional das APIs existentes.

Esta etapa deve permitir validacao inicial de schema, Swagger UI e ReDoc, mas
nao deve alterar o comportamento runtime das APIs consumidas pelo frontend
Next.js.

Regra-mae de escopo:

Esta PM nao tem como objetivo migrar as APIs existentes para DRF. O objetivo e
preparar infraestrutura OpenAPI segura e validavel. A migracao funcional para
DRF sera uma PM futura, endpoint por endpoint.

Nenhum contrato JSON consumido pelo frontend deve mudar nesta PM.

## Principio principal

OpenAPI entra primeiro como infraestrutura de contrato e documentacao.

DRF nao deve virar camada runtime dos endpoints atuais nesta etapa. Qualquer
migracao de view Django pura para `APIView`, `ViewSet`, `ModelViewSet` ou
`Response` fica bloqueada para plano posterior, endpoint por endpoint, com teste
de paridade de contrato.

## Regra de arquitetura backend-first

O projeto ja segue uma arquitetura backend-first.

Esta PM deve preservar esse desenho.

DRF e drf-spectacular nao devem mudar a arquitetura funcional do sistema. Eles
entram apenas como infraestrutura de borda HTTP, schema e documentacao.

As regras financeiras continuam no backend, em selectors, services, permissoes,
helpers e serializers manuais ja existentes.

O frontend nao deve receber novas responsabilidades de regra de negocio.

Nenhum calculo financeiro deve ser movido para serializers DRF, ViewSets ou
frontend nesta PM.

O schema OpenAPI deve descrever contratos existentes, nao criar novos contratos
funcionais.

Qualquer serializer DRF futuro deve ser tratado como camada de contrato/DTO, nao
como lugar de calculo financeiro, permissao ou regra de negocio.

Nesta PM, nao criar serializers DRF para substituir serializers manuais.

## Contexto

- O backend atual e Django puro.
- As APIs JSON existentes ja estao em producao.
- O frontend Next.js depende dos contratos atuais.
- A autenticacao atual usa sessao Django, cookie HttpOnly e CSRF.
- JWT nao faz parte desta etapa.
- Seguranca, compatibilidade e baixo risco sao prioridade.

## Observacoes da revisao da aplicacao

- `requirements.txt` ainda nao possui `djangorestframework` nem
  `drf-spectacular`; as dependencias devem entrar como dependencias runtime,
  nao apenas no ambiente virtual local.
- `config/settings.py` ainda nao possui `REST_FRAMEWORK`, `ENABLE_API_DOCS` nem
  `SPECTACULAR_SETTINGS`.
- As rotas atuais estao em `caixa/urls.py` e sao views Django puras; por isso a
  introspeccao automatica do schema deve ser tratada como limitada nesta PM.
- As permissoes das APIs atuais passam principalmente por
  `require_api_permission()` e `require_api_superuser()`, com respostas JSON
  `401`/`403` e `Cache-Control: no-store`. Esse comportamento nao deve ser
  substituido pelo fluxo padrao do DRF nesta etapa.
- O frontend Next.js usa `credentials: include`, sessao Django e `X-CSRFToken`
  nas mutations. Qualquer mudanca no fluxo de auth/CSRF quebra contrato
  operacional.
- O projeto possui `ConfiguredCorsMiddleware` proprio. A PM-08 nao deve trocar
  para outro pacote/middleware de CORS nem alterar headers permitidos.
- O projeto possui CSP restritiva em `SecurityHeadersMiddleware`:
  `script-src 'self'` e `style-src 'self'`. Swagger UI/ReDoc podem nao renderizar
  corretamente se dependerem de CDN ou script/style inline. Essa possibilidade
  deve ser testada e registrada; nao afrouxar CSP global automaticamente.

## Regras obrigatorias

- Nao alterar regra de negocio.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais existentes.
- Nao alterar permissoes atuais.
- Nao alterar autenticacao.
- Nao alterar CSRF.
- Nao alterar CORS.
- Nao alterar formato das respostas JSON.
- Nao alterar status HTTP.
- Nao alterar contratos consumidos pelo frontend.
- Nao converter `JsonResponse` para DRF `Response` nesta etapa.
- Nao migrar views para `APIView`, `ViewSet` ou `ModelViewSet` nesta etapa.
- Nao fazer deploy, commit, push ou merge.
- Nao tratar `schema.yml` gerado como contrato oficial do frontend nesta etapa.

## Regra de versionamento e checkpoints

- Esta PM nao deve gerar commit automaticamente apos cada fase.
- O Codex nao deve executar `git commit`, `git push`, `git merge` ou deploy.
- Ao final de cada fase com diagnostico ou alteracao, registrar
  `git status --short`.
- Quando houver alteracao de arquivo, registrar tambem os arquivos modificados e
  o motivo da mudanca.
- Commit local so deve acontecer com autorizacao explicita do responsavel e
  depois das validacoes da fase.
- Se alguma fase falhar, parar, registrar o motivo e nao avancar para a fase
  seguinte ate decisao explicita.

## Evidencias obrigatorias por fase

Cada fase executada deve registrar, conforme aplicavel:

- endpoints `/api/...` observados ou afetados;
- arquivos lidos e arquivos alterados;
- configuracoes adicionadas ou preservadas;
- dependencias adicionadas e versoes resolvidas;
- rotas criadas e condicoes de exposicao;
- autenticacao, CSRF, CORS e permissoes preservadas;
- resultado de `python manage.py check`;
- resultado de `python manage.py spectacular --file schema.yml`;
- resultado de `python manage.py spectacular --validate`;
- resultado dos testes executados;
- warnings do schema e limitacoes de introspeccao;
- compatibilidade com o frontend atual;
- decisao sobre manter, ignorar ou remover `schema.yml`;
- `git status --short` ao final da fase.

## Regra de reaproveitamento e mudanca minima

Aproveitar ao maximo a estrutura existente.

Antes de criar arquivo, helper, classe, configuracao ou abstracao nova,
verificar se ja existe algo equivalente no projeto.

Priorizar reaproveitar:

- settings existentes;
- padrao atual de URLs;
- padrao atual de permissoes;
- testes existentes;
- helpers ja usados para variaveis de ambiente;
- autenticacao por sessao e CSRF atuais;
- organizacao atual do app `caixa`;
- padrao de validacao ja usado no projeto.

Criar algo novo somente se for realmente necessario para a fase atual, com
justificativa no relatorio final.

Nao criar abstracoes antecipadas para uma migracao futura.

Nao criar app novo, camada nova de API, helper novo ou classe base nova nesta
PM, salvo se houver necessidade tecnica demonstrada.

Consequencias praticas nesta PM:

- Nao criar app novo, como `api` ou `docs_api`, salvo necessidade tecnica
  demonstrada.
- Nao criar camada nova de permissoes DRF para substituir permissoes atuais.
- Nao criar helpers novos de ambiente se `env.bool()` e os padroes existentes
  resolverem.
- Nao criar serializers DRF de contrato nesta PM, exceto se forem estritamente
  necessarios para a infraestrutura minima e com justificativa registrada.

## Matriz de decisao da PM-08

| Sinal observado | Decisao segura | Evitar |
| --- | --- | --- |
| Schema inicial vazio ou incompleto | Registrar como esperado para views Django puras | Reescrever endpoints para satisfazer o schema |
| Warning de introspeccao do drf-spectacular | Classificar e documentar | Tratar warning como motivo para migrar view nesta PM |
| `/api/schema/` acessivel sem staff | Bloquear a fase e corrigir protecao | Avancar com documentacao exposta |
| Swagger/ReDoc retornam `200`, mas nao renderizam por CSP | Registrar e abrir decisao especifica de CSP/assets | Afrouxar CSP global automaticamente |
| `override_settings(ENABLE_API_DOCS=...)` nao muda as URLs no teste | Recarregar URLConf ou usar URLConf isolada | Aceitar teste falso positivo |
| DRF muda resposta `401`/`403` de endpoint existente | Bloquear e revisar escopo | Substituir permissoes atuais por permissoes DRF |
| Dependencia nova altera pacote transitorio sensivel | Registrar diff e validar | Ignorar downgrade/remocao inesperada |
| `schema.yml` gerado localmente | Remover, ignorar ou justificar permanencia | Versionar como contrato oficial sem aprovacao |

## Ponto de retomada

Status inicial: planejada.

Proxima acao permitida: executar PM-08.1 como diagnostico read-only antes de
qualquer alteracao de arquivo runtime.

Acoes bloqueadas ate fechamento deste plano:

- Migrar endpoint existente para DRF.
- Trocar autenticacao por JWT ou token.
- Abrir documentacao publica por padrao.
- Gerar tipos frontend como fonte oficial de contrato.
- Remover aliases, adapters ou compatibilidade de resposta.
- Relaxar CSP global para fazer Swagger/ReDoc funcionar sem aprovacao explicita.

## PM-08.1 - Diagnostico read-only

Status: planejada.

Objetivo: mapear o estado atual antes de modificar qualquer arquivo.

Gate de entrada:

- Ler este plano.
- Confirmar que a mudanca desejada e infraestrutura OpenAPI, nao migracao de
  API.

Tarefas:

- Mapear endpoints `/api/...` existentes em `caixa/urls.py`.
- Mapear autenticacao atual em `config/settings.py`, `caixa/views_api_auth.py`
  e frontend Next.js.
- Mapear permissoes atuais em `caixa/permissions.py` e views protegidas.
- Mapear respostas JSON principais e envelopes usados pelo frontend.
- Identificar arquivos envolvidos.
- Classificar endpoints por risco:
  - auth e sessao;
  - GET financeiro complexo;
  - GET simples;
  - POST/PUT com CSRF;
  - download tecnico ou endpoint administrativo.

Gate de saida:

- Relatorio do diagnostico registrado na resposta ou no registro de execucao.
- Nenhum arquivo runtime alterado.

Validacoes:

- `git status --short`
- Leitura das rotas e views, sem modificacao.

## PM-08.2 - Instalacao segura da infraestrutura

Status: planejada.

Objetivo: instalar DRF e drf-spectacular sem alterar comportamento das APIs
existentes.

Tarefas:

- Adicionar dependencias:
  - `djangorestframework`
  - `drf-spectacular`
- Registrar as dependencias em `requirements.txt` com versoes resolvidas e
  compativeis com `Django==6.0.5`.
- Se a instalacao alterar dependencias transitivas ja existentes, registrar o
  diff e validar que nao houve downgrade ou remocao inesperada.
- Adicionar em `INSTALLED_APPS`:
  - `rest_framework`
  - `drf_spectacular`
- Configurar `REST_FRAMEWORK` preservando sessao Django:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
```

- Se `REST_FRAMEWORK` ja existir, mesclar sem apagar configuracoes existentes.
- Adicionar configuracao segura:

```python
ENABLE_API_DOCS = env.bool("ENABLE_API_DOCS", default=DEBUG)
```

- Adicionar `SPECTACULAR_SETTINGS` minimo:

```python
SPECTACULAR_SETTINGS = {
    "TITLE": "RH SaaS API",
    "DESCRIPTION": "Schema OpenAPI inicial para validacao incremental.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
```

Gate de saida:

- Dependencias instaladas.
- `manage.py check` sem erro.
- `requirements.txt` atualizado e revisado.
- Nenhum endpoint existente migrado.
- Nenhum contrato JSON alterado.

Validacoes:

- `python manage.py check`

## PM-08.3 - Rotas condicionais e protegidas

Status: planejada.

Objetivo: expor schema, Swagger UI e ReDoc somente quando habilitados por
configuracao e sempre protegidos por staff.

Rotas condicionais:

- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

Notas de implementacao:

- As rotas devem ficar em `config/urls.py`, preferencialmente antes do
  `include("caixa.urls")`, para deixar a prioridade explicita.
- Usar nomes de rota claros, por exemplo `api_schema`, `api_docs` e
  `api_redoc`.
- Envolver `SpectacularAPIView.as_view()`, `SpectacularSwaggerView.as_view()` e
  `SpectacularRedocView.as_view()` com `staff_member_required`.
- O comportamento padrao de `staff_member_required` pode redirecionar anonimos
  ou usuarios nao-staff para o login do admin. Os testes devem validar que esses
  usuarios nao recebem `200`, sem exigir obrigatoriamente `403`.

Regra de seguranca:

- As rotas so podem existir quando `settings.ENABLE_API_DOCS == True`.
- Todas as rotas de documentacao, incluindo `/api/schema/`, devem usar
  `staff_member_required`.
- Em producao, a documentacao nao pode ficar publica por padrao.

Gate de saida:

- Com `ENABLE_API_DOCS=False`, as rotas nao ficam disponiveis.
- Com `ENABLE_API_DOCS=True`, anonimo nao acessa.
- Com `ENABLE_API_DOCS=True`, usuario autenticado nao-staff nao acessa.
- Com `ENABLE_API_DOCS=True`, usuario staff acessa.
- Swagger UI e ReDoc devem ser testados com usuario staff para confirmar que a
  resposta nao fica quebrada por CSP. Se a UI nao renderizar por causa de CSP,
  registrar o problema e abrir decisao separada entre:
  - usar assets locais/sidecar;
  - criar excecao CSP especifica para docs;
  - manter apenas `/api/schema/` nesta etapa.

Validacoes:

- Testes automatizados especificos das rotas de documentacao.
- `python manage.py check`

Nota para testes:

Como `urlpatterns` e montado no import de `config.urls`, testes que alternam
`ENABLE_API_DOCS` devem limpar cache de URL e recarregar a URLConf, ou usar
URLConf isolada de teste. Apenas `override_settings(ENABLE_API_DOCS=True/False)`
pode nao ser suficiente.

## PM-08.4 - Schema inicial de validacao

Status: planejada.

Objetivo: gerar schema somente para validar a infraestrutura.

Comandos:

```bash
python manage.py spectacular --file schema.yml
python manage.py spectacular --validate
```

Regra importante:

Como os endpoints atuais sao Django puro com `JsonResponse`, e esperado que o
schema inicial venha incompleto ou quase vazio. Isso nao e erro desta etapa.

Se algum endpoint nao puder ser documentado automaticamente pelo
drf-spectacular, apenas reportar. Nao reescrever a implementacao para satisfazer
o schema nesta PM.

Gate de saida:

- Schema gerado para validacao inicial.
- Warnings registrados.
- Limitacoes documentadas.
- Nenhuma API existente reescrita.
- `schema.yml` nao versionado como contrato oficial, salvo aprovacao explicita.
- Se o arquivo for gerado apenas para validacao local, remover o artefato ao fim
  da etapa ou registrar por que ele deve permanecer no workspace.

## PM-08.5 - Testes e regressao

Status: planejada.

Objetivo: provar que a infraestrutura OpenAPI nao alterou comportamento
existente.

Validacoes obrigatorias:

```bash
python manage.py check
python manage.py spectacular --file schema.yml
python manage.py spectacular --validate
python manage.py test
```

Observacao local:

Se o ambiente local nao possuir `.env` valido, executar os comandos com
variaveis temporarias de desenvolvimento, por exemplo `DEBUG=True` e
`SECRET_KEY=local-validation-secret`, sem alterar arquivos de configuracao.

Quando a suite completa for impraticavel no ambiente local, registrar o motivo e
executar suite focada minima cobrindo:

- auth/session/CSRF;
- permissoes 401/403;
- endpoints financeiros principais;
- rotas novas de documentacao;
- contratos usados pelo frontend;
- verificacao de ausencia das rotas de documentacao com
  `ENABLE_API_DOCS=False`;
- verificacao de acesso negado ou redirect para anonimo e usuario nao-staff com
  `ENABLE_API_DOCS=True`;
- verificacao de acesso `200` para usuario staff com `ENABLE_API_DOCS=True`.

Gate de saida:

- Testes executados e resultado registrado.
- Warnings do schema classificados.
- Nenhum comportamento funcional indesejado identificado.

## PM-08.6 - Revisao final da PM-08

Status: planejada.

Objetivo: fechar a etapa como infraestrutura inicial, sem iniciar migracao
funcional de endpoints.

Checklist de revisao:

- [ ] Arquivos alterados listados.
- [ ] Dependencias adicionadas listadas.
- [ ] Rotas criadas listadas.
- [ ] Resultado dos testes registrado.
- [ ] Warnings do schema registrados.
- [ ] Endpoints `/api/...` detectados listados.
- [ ] Riscos residuais registrados.
- [ ] Decisao sobre `schema.yml` registrada: removido, ignorado ou mantido
  explicitamente.
- [ ] Comportamento da CSP em Swagger/ReDoc registrado.
- [ ] Compatibilidade com frontend atual avaliada.
- [ ] Confirmado que sessao Django e CSRF foram preservados.
- [ ] Confirmado que CORS nao foi alterado.
- [ ] Confirmado que nenhuma API existente foi migrada para DRF runtime.
- [ ] Confirmado que nenhum contrato JSON foi alterado.

Gate de saida:

- DRF instalado.
- drf-spectacular instalado.
- Infraestrutura OpenAPI criada.
- Swagger/ReDoc disponiveis apenas quando habilitados por configuracao.
- `/api/schema/` protegido.
- Seguranca atual preservada.
- Nenhuma mudanca funcional nas APIs existentes.

## Criterios globais de aceite

A PM-08 so deve ser considerada concluida quando todos os itens abaixo forem
verdadeiros:

- `djangorestframework` e `drf-spectacular` estao registrados nas dependencias
  do projeto.
- `rest_framework` e `drf_spectacular` estao em `INSTALLED_APPS`.
- `REST_FRAMEWORK` preserva `SessionAuthentication`.
- `DEFAULT_PERMISSION_CLASSES` nao altera o comportamento das views Django
  puras existentes.
- `ENABLE_API_DOCS` usa `env.bool("ENABLE_API_DOCS", default=DEBUG)`.
- `/api/schema/`, `/api/docs/` e `/api/redoc/` existem somente quando
  `ENABLE_API_DOCS=True`.
- Todas as rotas de documentacao, incluindo `/api/schema/`, exigem staff.
- `python manage.py check` passa.
- `python manage.py spectacular --validate` executa e seus warnings ficam
  registrados.
- Testes das rotas de documentacao passam.
- Testes existentes relevantes continuam passando ou qualquer impossibilidade
  local fica registrada.
- Nenhum endpoint existente foi convertido para DRF runtime.
- Nenhum `JsonResponse` existente foi convertido para `Response`.
- Nenhum contrato JSON consumido pelo frontend foi alterado.
- Sessao Django, cookie HttpOnly, CSRF e CORS foram preservados.
- `schema.yml` nao foi tratado como contrato oficial sem aprovacao explicita.
- `git status --short` final foi registrado.

## Criterios de bloqueio

A execucao deve parar se qualquer um destes pontos ocorrer:

- qualquer rota de documentacao ficar acessivel publicamente;
- `/api/schema/` ficar sem protecao de staff;
- alguma API existente mudar status HTTP, payload, autenticacao, CSRF ou CORS;
- alguma view existente precisar ser reescrita para o schema ser gerado;
- dependencia nova causar downgrade, remocao inesperada ou incompatibilidade
  com o Django atual;
- Swagger/ReDoc exigirem relaxamento global de CSP para funcionar;
- os testes de documentacao nao conseguirem provar `ENABLE_API_DOCS=True/False`
  por cache de URLConf;
- `schema.yml` passar a ser usado como contrato oficial do frontend nesta PM;
- aparecer necessidade de criar app novo, helper novo ou camada nova sem
  justificativa tecnica imediata.

## Registro de execucao

Cada execucao deve adicionar ou reportar um registro com:

- data da execucao;
- fase executada;
- resumo do que foi feito;
- arquivos alterados;
- comandos executados;
- resultado dos testes;
- warnings do schema;
- riscos encontrados;
- decisao de avancar, parar ou abrir plano separado.

## Registro de execucao - 2026-06-15 - PM-08.6

Fase executada: revisao final da PM-08.

Resumo:

- PM-08 concluida como infraestrutura inicial de OpenAPI com DRF e
  drf-spectacular.
- Nenhuma API existente foi migrada para DRF runtime.
- Nenhuma view existente foi convertida para `APIView`, `ViewSet` ou
  `ModelViewSet`.
- Nenhum `JsonResponse` existente foi convertido para DRF `Response`.
- Nenhum serializer DRF foi criado para substituir serializers manuais.
- Nenhum contrato JSON consumido pelo frontend foi alterado.
- Sessao Django, cookie HttpOnly, CSRF, CORS e permissoes atuais foram
  preservados.
- Swagger/ReDoc/schema foram criados apenas como rotas condicionais e
  protegidas por staff.

Arquivos alterados na PM-08:

- `requirements.txt`
- `config/settings.py`
- `config/urls.py`
- `caixa/tests.py`
- `docs/PLANO_OPENAPI_DRF_SPECTACULAR.md`

Dependencias adicionadas:

- `djangorestframework==3.17.1`
- `drf-spectacular==0.29.0`
- dependencias transitivas resolvidas e pinadas:
  `attrs==26.1.0`, `inflection==0.5.1`, `jsonschema==4.26.0`,
  `jsonschema-specifications==2025.9.1`, `PyYAML==6.0.3`,
  `referencing==0.37.0`, `rpds-py==2026.5.1` e `uritemplate==4.2.0`.

Rotas criadas:

- `/api/schema/`
- `/api/docs/`
- `/api/redoc/`

Resultado das validacoes:

- `python manage.py check`: passou, sem issues.
- `python manage.py spectacular --file schema.yml`: passou.
- `python manage.py spectacular --validate`: passou.
- `python manage.py test`: 670 testes executados, 670 passaram.
- Testes focados das rotas de documentacao: 4 executados, 4 passaram.

Warnings e limitacoes:

- O `drf-spectacular` nao exibiu warnings na geracao/validacao inicial.
- O schema inicial ficou com `paths: {}` porque as APIs atuais sao views Django
  puras com `JsonResponse`; isso e esperado nesta PM.
- Durante a suite de testes apareceram logs esperados de cenarios negativos de
  CSRF e Axes, sem falha de teste.
- Swagger/ReDoc ainda precisam de validacao visual em navegador por causa da CSP
  restritiva. Nenhum relaxamento global de CSP foi feito.

Decisao sobre `schema.yml`:

- Gerado apenas como artefato local de validacao.
- Removido ao final.
- Nao tratado como contrato oficial do frontend.

Riscos residuais:

- Schema inicial vazio pode gerar falsa confianca se for confundido com contrato
  oficial.
- Endpoints Django puro exigirao documentacao/migracao futura endpoint por
  endpoint para aparecerem no OpenAPI com detalhe.
- Swagger/ReDoc podem retornar `200`, mas ainda precisam ser validados
  visualmente por causa da CSP.
- Futuras configuracoes de producao devem garantir `ENABLE_API_DOCS=False` ou
  acesso staff protegido quando habilitado.

Decisao:

- PM-08 pronta para revisao e commit local manual pelo responsavel.
- Nao foi feito commit, push, merge ou deploy.

## Riscos residuais esperados

- Schema inicial incompleto por causa de views Django puras com `JsonResponse`.
- Warnings de introspeccao do drf-spectacular em endpoints nao DRF.
- Risco de falsa confianca se `schema.yml` for tratado como contrato oficial
  antes da documentacao manual/migracao gradual dos endpoints.
- Risco de exposicao indevida se `/api/schema/` nao for protegido junto com
  Swagger/ReDoc.
- Risco de Swagger UI/ReDoc retornarem `200`, mas nao renderizarem por CSP
  restritiva. Isso deve ser validado antes de declarar a UI disponivel.
- Risco de teste de rotas condicionais usar URLConf cacheada e nao testar de
  fato `ENABLE_API_DOCS=True/False`.

## Fora do escopo

- Migrar endpoints existentes para DRF.
- Criar `APIView`, `ViewSet` ou `ModelViewSet`.
- Substituir serializers manuais.
- Trocar autenticacao por JWT.
- Gerar tipos TypeScript oficiais para o frontend.
- Remover aliases ou adapters do frontend.
- Alterar regras financeiras, permissoes, filtros, services ou selectors.

## Proximo plano recomendado

Somente depois do fechamento da PM-08, abrir um plano separado para
documentacao incremental de endpoints prioritarios, com paridade entre JSON real
e OpenAPI.

Sugestao de ordem futura:

1. `/api/auth/session/`
2. `/api/dashboard/financial-overview/`
3. `/api/orcamentos/`
4. endpoints GET financeiros principais
5. mutations com CSRF, uma a uma

Cada endpoint futuro deve ter teste de contrato antes/depois e nao deve mudar
formato de resposta sem decisao explicita.
