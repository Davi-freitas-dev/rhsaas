# Plano de liberacao da demo publica automatica

Documento de acompanhamento da preparacao do RH SaaS para abertura publica
como demo tecnica de portfolio com distribuicao automatica de tenants.

Atualizado em: 2026-07-15

Estados usados neste documento:

- `[ ]` nao iniciado;
- `[~]` em andamento;
- `[x]` concluido;
- `[!]` bloqueado;
- `[-]` descartado.

## 1. Objetivo

Deixar a demo pronta para abertura publica com `demo1` como tenant permanente
e distribuicao automatica somente entre `demo2...demo10`, autenticacao sem
credencial manual, isolamento por schema, acesso temporario, permissoes minimas
e limpeza segura antes de devolver a vaga ao pool.

O escopo e uma demo de portfolio. Cobranca, planos, assinatura, trial comercial
e cadastro empresarial permanecem fora de escopo.

## 2. Estado inicial

### Repositorios

| Projeto | Commit | Branch | Upstream | Alteracoes locais |
| --- | --- | --- | --- | --- |
| Backend | `e623d12` | `feat/django-tenants-spike` | sincronizado, 0/0 | nenhuma |
| Frontend | `752b9ed` | `main` | sincronizado, 0/0 | nenhuma |

Comandos executados nos dois repositorios:

```text
git status --short
git log -10 --oneline
git diff --stat
git branch --show-current
git rev-parse --short HEAD
git rev-list --left-right --count HEAD...@{upstream}
```

Resultado: arvores limpas, sem arquivos nao rastreados e sem divergencia com o
upstream. Nao foram encontrados `.env`, bancos, logs ou backups reais
versionados; os arquivos encontrados sao exemplos, runbooks ou codigo.

### Migrations e banco local

- PostgreSQL local em `localhost:5433`, banco de desenvolvimento.
- Schemas locais encontrados: `public`, `demo1` e `rh_teste`.
- Slot local encontrado: somente `demo1`, com status `livre`.
- `tenancy.0002_demotenantslot`: aplicada.
- `caixa.0041_remove_horas_cobradas_decimal_horas_dia`: pendente em `demo1` e
  `rh_teste`.
- O plano de `public` tambem lista `caixa.0040` e `caixa.0041`; nenhuma migration
  foi aplicada nesta execucao.
- `makemigrations --check --dry-run`: nenhuma mudanca detectada antes da
  implementacao.

### Checks e testes iniciais

| Evidencia | Resultado inicial |
| --- | --- |
| `python manage.py check` sem override | falha: `.env` local tem `DEBUG=release` |
| `DEBUG=True python manage.py check` | aprovado, sem issues |
| `DEBUG=False python manage.py check --deploy` local | bloqueado corretamente por LocMem em producao |
| `python manage.py migrate_schemas --plan` | confirmou migrations pendentes, sem aplicar |
| suites focadas de orcamento da revisao anterior | 113 testes aprovados |
| `check:hourly-services` e `check:budget-item-snapshots` | aprovados |
| `lint`, `typecheck`, `build` e E2E anterior | aprovados; E2E 12/12 |
| `check:financial-canonical` | falhas antigas fora do escopo atual |
| `python manage.py test tenancy --keepdb` | inconclusivo: timeout de 10 minutos sem resumo |

### Producao conhecida e observacao externa read-only

- `https://demo-rh.taquiondev.com.br/`: HTTP 200.
- API principal `/api/auth/csrf/`: HTTP 200.
- `demo1` e `demo2` em `/api/auth/csrf/`: HTTP 200.
- CORS de API principal, `demo1` e `demo2`: permite apenas o frontend publico
  observado.
- `demo10` em `/api/auth/csrf/`: HTTP 404.
- `/api/health/`: HTTP 404.
- `/api/demo/lease/`: HTTP 404.
- Nenhum POST, login, reset, migration ou outra alteracao foi executada em
  producao.

O gate historico de 2026-07-07 registra aproximadamente 954 MiB de RAM, 2 GiB
de swap, 16% de disco e Gunicorn com 1 worker/2 threads. Nao ha acesso de
servidor nesta execucao para confirmar metricas atuais.

### Funcionalidades prontas no inicio

- `DemoTenantSlot` no schema publico.
- Comandos de provisionamento, ocupacao, expiracao e reset.
- `select_for_update` na ocupacao manual.
- Guards explicitos para impedir `public`, `rh_teste` e schemas fora de
  `demo1...demo10`.
- Advisory lock e falha fechada no reset.
- Wildcard DNS/TLS/Nginx validado historicamente para tenants provisionados.
- Cookies host-only, CORS restrito, Axes e throttles tenant-aware.
- Chaves de cache separadas por schema.
- Frontend com allowlist de `demo1...demo10`, resolucao por `?tenant=demoN` e
  cache de dados separado pelo runtime da API.

### Limitacoes conhecidas

- Pool local e producao observavel nao comprovam `demo1...demo10` completos.
- Entrada e ocupacao ainda sao manuais.
- Usuario criado pelo comando atual e `staff`/`superuser`.
- Nao existe seed de negocio suficiente apos reset.
- Expiracao atual nao limpa sessoes, Axes e cache.
- Nao existe timer oficial.
- Nao existe health check dedicado.
- Renovacao automatica do certificado wildcard nao esta comprovada.
- Quota de 50 MB e apenas metadata, sem enforcement automatico.

### Estado atual apos a implementacao local

- No inicio da reserva de `demo1`, o backend estava em `8d3efe6`, branch
  `feat/django-tenants-spike`, e o frontend em `3d910ca`, branch `main`; ambos
  estavam um commit a frente do upstream. As mudancas desta solicitacao estao
  somente nas arvores locais, sem commit, push ou deploy.
- A flag `DEMO_PUBLIC_LEASE_ENABLED` permanece `False` por padrao.
- A nova migration `tenancy.0004` remove somente o registro
  `DemoTenantSlot(slot_code="demo1")`; ela nao foi aplicada ao banco de
  desenvolvimento nem a producao nesta solicitacao.
- Os testes relacionados do backend passaram: suite publica 16/16;
  provisionamento 5/5; ocupacao com os nove cenarios validados; expiracao 7/7;
  reset 10/10; guards novos e a classificacao corrigida aprovados.
- `verify:frontend` passou por completo: lint, tipos, guardrails e build de
  producao com 22 rotas.
- `verify:e2e` passou 17/17: cinco cenarios da entrada publica e doze de
  regressao dos filtros canonicos.
- A bateria agregada de cinco classes da pool ultrapassou quinze minutos e foi
  dividida; todas as classes relacionadas produziram resultados deterministas.
  A suite completa `tenancy` permanece como validacao ampliada de CI, nao como
  falha dos cenarios relacionados.
- A integracao real entre frontend e backend ainda precisa ser exercitada no
  ambiente de homologacao com os dez tenants provisionados.

### Diagnostico da reserva de `demo1` em 2026-07-15

- `allocate_demo_lease` selecionava qualquer `DemoTenantSlot` livre e, pela
  ordenacao, preferia `demo1`.
- `expire_due_demo_leases`, `ocupar_tenant_demo` e `expirar_leases_demo`
  tambem assumiam `demo1...demo10` como uma unica pool.
- `manter_pool_demo` processava o resultado da expiracao e podia resetar
  `demo1`.
- `provisionar_pool_demo` criava um `DemoTenantSlot` livre para `demo1`.
- testes backend, concorrencia e E2E simulavam `demo1` como primeira vaga.
- o frontend ja preservava `?tenant=demo1`, mas nao oferecia esse acesso como
  fallback quando a pool temporaria estava cheia.
- documentos historicos e operacionais ainda descreviam `demo1...demo10` como
  pool temporaria.

Decisao implementada: usar `DEMO_PUBLIC_POOL_SLOTS` como fonte central da pool
automatica, com padrao `demo2...demo10`. A migration de dados pequena remove
somente o registro `DemoTenantSlot` de `demo1`, preservando Tenant, Domain,
schema, dados e usuario permanentes.

### Diagnostico do fluxo pos-exchange em 2026-07-15

Estado antes da correcao: backend `8c03da7`, branch
`feat/django-tenants-spike`, e frontend `77df602`, branch `main`; ambos limpos
e sincronizados com seus upstreams. A observacao de producao informou lease
`201`, exchange `200`, `demo2` ocupado e token marcado como consumido, mas o
frontend voltou a entrada com a mensagem generica de preparacao.

Diagnostico read-only confirmado antes de editar:

- o contrato backend devolve `authenticated: true` somente depois de criar a
  sessao;
- o bundle publicado contem a URL publica correta e o mesmo fluxo do commit
  local;
- preflight, CORS, CSP e uma leitura de `/api/auth/session/` feita pelo Chrome
  a partir da origem publica foram aprovados, sem POST ou alteracao externa;
- o frontend persistia o lease apenas depois de interpretar a resposta do
  exchange;
- o mesmo `try/catch` abrangia exchange, persistencia e
  `window.location.replace`, convertendo qualquer excecao posterior ao
  exchange em erro generico;
- na URL temporaria, sessao nao confirmada disparava `allocate()` novamente e
  podia solicitar outra vaga;
- a causa nativa era descartada, sem diagnostico seguro no console.

Decisao: corrigir somente o frontend. Persistir o lease antes da troca,
confirmar a sessao no tenant quando o resultado do POST for ambiguo, navegar
fora do `catch`, nunca realocar automaticamente durante recuperacao e registrar
somente nome/mensagem/status/codigo do erro, sem token ou dados pessoais.

Implementacao aplicada no frontend:

- lease valido e `expiresAt` sao persistidos antes do POST de troca, sem salvar
  o token;
- resposta ambigua do exchange consulta a sessao no host ja reservado e, se a
  sessao existir, segue para o dashboard;
- navegacao explicita ocorre fora do `catch` da alocacao;
- falha de sessao apos redirecionamento nao chama novo lease automaticamente;
- falha real HTTP no exchange remove o lease local e apresenta o detalhe seguro;
- erros nativos registram somente metadados seguros no console.

Tentativa de teste: E2E publico com porta isolada `3111` falhou porque o mock
preexistente autoriza CORS para a porta contratual `3100`. Decisao: nao alterar
o produto por esse falso negativo e repetir com a configuracao oficial.
Correcao/reversao: nenhuma correcao de produto foi necessaria; a repeticao em
`3100` aprovou 13/13 cenarios, incluindo exchange ambiguo recuperado, falha real,
reload sem novo lease, `demo1`, tenant temporario sem lease e logout.

Estado da fase: `[x]` implementacao e validacao local concluidas. Nenhuma
alteracao de backend, pool, Nginx, timer, producao, commit ou push foi realizada.

### Diagnostico de reutilizacao entre navegadores em 2026-07-15

Estado inicial desta fase: backend `d42721f`, branch
`feat/django-tenants-spike`, e frontend `6fef5f3`, branch `main`; arvores
limpas. A pool conhecida em producao possui `demo1` permanente e
`demo2...demo4` temporarios. Nenhum POST ou alteracao de producao foi realizado.

Diagnostico read-only:

- o cookie assinado e `HttpOnly` `rhsaas_demo_visitor` contem identificador
  aleatorio, vale 24 horas por padrao e e convertido em HMAC-SHA256 antes de
  chegar ao banco;
- o IP canonico vindo apenas do proxy confiavel tambem e convertido em HMAC;
  IP puro, user-agent e fingerprint nao sao persistidos;
- `localStorage` contem somente tenant, URL da API e expiracao, sem participar
  da identidade anonima;
- logout remove sessao e lease local, mas preserva corretamente o cookie
  anonimo do host de entrada;
- advisory locks de visitante e rede, transacao e `select_for_update` protegem
  a concorrencia do endpoint;
- a selecao atual usa `visitor_hash OR network_hash`: mesmo navegador reutiliza
  o slot, mas navegadores distintos da mesma rede compartilham o mesmo tenant;
- o throttle atual limita chamadas por IP, mas nao representa uma cota clara de
  leases ativos por rede;
- mudar IP/rede permite ocupar outros slots, portanto o modelo atual e ao mesmo
  tempo restritivo para redes compartilhadas e contornavel por troca de rede.

Alternativas avaliadas: cookie isolado nao limita multiplos perfis; rede isolada
mistura usuarios; cookie + cota de rede preserva isolamento com baixo impacto;
link de retomada fica como evolucao futura. Decisao: reutilizar apenas pelo
cookie e permitir, por padrao, dois leases ativos distintos por hash de rede.
O terceiro recebe `network_limit`, sem consumir slot. O throttle existente
permanece como cooldown. Nao e necessaria migration, nova tabela, fingerprint,
mudanca de Nginx ou timer.

Implementacao concluida:

- a retomada de lease ativo passou a usar somente o hash do visitante, evitando
  que dois navegadores da mesma rede compartilhem dados no mesmo tenant;
- antes de ocupar nova vaga, o servico conta leases ativos do hash de rede sob
  o advisory lock ja existente e aplica a cota configuravel
  `DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2`;
- o terceiro navegador recebe HTTP 429 com codigo `network_limit`; `pool_full`
  e `unavailable` continuam respostas distintas;
- leases expirados e `demo1` nao entram na cota; a expiracao/reset remove os
  hashes conforme o ciclo ja existente;
- nenhuma migration, tabela, fingerprint, mudanca de Nginx, timer ou producao
  foi necessaria.

Validacao final: `DemoPublicFlowTests` 19/19 e
`DemoPublicConcurrencyTests` 3/3 passaram em PostgreSQL; `check`,
`makemigrations --check --dry-run`, lint, tipos, guardrails e build passaram;
E2E publico 15/15 e bateria completa 27 aprovados, com apenas o cenario
opcional `rh_teste` ignorado por falta de configuracao.

Estado da fase: `[x]` implementacao e validacao local concluidas. Homologacao e
producao permanecem intocadas.

## 3. Decisoes arquiteturais

### Fluxo publico de entrada

Decisao: a raiz publica exibira uma apresentacao curta e o botao `Acessar
demo` quando nao houver tenant valido selecionado. O dashboard existente
continuara sendo renderizado quando houver lease automatico ou o parametro
manual permitido.

Razao: preserva as rotas e telas existentes, evita uma migracao ampla de URLs e
mantem `?tenant=demoN` disponivel para diagnostico.

### Alocacao do tenant

Decisao: endpoint publico no schema `public`, com transacao,
`select_for_update(skip_locked=True)` e selecao deterministica do primeiro slot
livre.

Razao: o lock no banco e a autoridade final para impedir dupla alocacao entre
workers. Cache ou Redis nao serao usados como autoridade do estado do slot.

### Composicao da pool e tenant permanente

Decisao: `demo1` e o tenant permanente e nao possui `DemoTenantSlot` de pool.
A lista configuravel `DEMO_PUBLIC_POOL_SLOTS` contem, por padrao,
`demo2...demo10` e sera aplicada em toda selecao automatica. Os guards gerais
continuam reconhecendo `demo1...demo10` como tenants tecnicos validos para
validacoes de infraestrutura, mas os comandos de ocupar, expirar e resetar a
pool rejeitam `demo1`; a operacao manual permanente usa somente
`preparar_demo_permanente`.

Razao: separar a lista tecnica da lista automatica evita condicionais
espalhadas, preserva `?tenant=demo1`, protege concorrencia/reinicio e elimina o
estado ambiguo de uma demo permanente marcada como `livre`.

### Autenticacao

Decisao: token aleatorio de troca, de uso unico e vida curta. O endpoint de
lease devolve o token uma vez; apenas o digest HMAC e persistido. O frontend
troca o token no host do tenant e esse host cria a sessao Django host-only.

Razao: o host `api-demo-rh` nao pode criar cookie host-only para
`demoN.api-demo-rh`. Retornar senha aumentaria exposicao e permitiria reuso. O
token de troca resolve a fronteira de host sem compartilhar cookies.

### Duracao do lease

Decisao: 60 minutos por padrao, configuravel por ambiente, com token de troca
valido por poucos minutos.

Razao: nove slots temporarios e uma VM pequena exigem rotacao conservadora.
Tres dias, usados na fase manual, seriam inadequados para entrada publica
anonima.

### Controle de abuso

Decisao: combinar throttle DRF, limite Nginx, cookie anonimo assinado, digest
HMAC de rede com retencao limitada ao lease e reutilizacao da mesma vaga para
solicitacoes repetidas. Nao armazenar IP puro.

Razao: nenhum identificador isolado impede abuso. A combinacao reduz ocupacao
de varias vagas sem exigir cadastro pessoal ou CAPTCHA na primeira versao.

### Permissoes do usuario demo

Decisao: grupo proprio de demo publica; usuario ativo, sem `is_staff` e sem
`is_superuser`. Permitidas operacoes demonstrativas selecionadas, sem admin,
usuarios, backups, downloads de backup, infraestrutura ou permissoes de
exclusao.

Razao: superusuario e bloqueador de seguranca. Um grupo explicito torna o
contrato auditavel e testavel.

### Seed

Decisao: service idempotente com grupos/permissoes, configuracao financeira,
cliente ficticio, servico por diaria, servico por hora e orcamento de exemplo.
O usuario temporario sera ativado somente ao ocupar a vaga.

Razao: o reset precisa devolver uma demo compreensivel sem manter dados do
visitante anterior.

### Expiracao, limpeza e reset

Decisao: ao expirar, desativar usuario, remover sessoes, limpar Axes e cache do
tenant e marcar o slot expirado. Em seguida, o reset existente recria apenas o
schema validado, reaplica seed e libera o slot. Falhas deixam o slot bloqueado.

Razao: bloquear acesso antes da operacao destrutiva reduz a janela de dados
residuais e preserva a estrategia fail-closed existente.

### Agendamento

Decisao: comando periodico idempotente executado por `systemd timer`, sem
Celery. Manter tambem comando manual e `--dry-run`.

Razao: a VM pequena e o volume maximo de dez slots nao justificam infraestrutura
de filas adicional.

### Pool cheia e falha parcial

Decisao: pool cheia retorna resposta generica e temporaria, sem lista ou dados
de slots. Falha antes do commit reverte slot, usuario e token. Falha no reset
bloqueia a vaga e exige diagnostico.

Razao: nao expor metadata interna e nunca liberar uma vaga cujo estado nao foi
comprovadamente limpo.

## 4. Checklist por fase

- [x] diagnostico;
- [x] reserva permanente de `demo1` e pool publica `demo2...demo10`;
- [~] estabilizacao dos testes existentes;
- [x] servico de lease;
- [x] endpoint publico;
- [x] concorrencia e rollback;
- [x] autenticacao automatica;
- [x] frontend publico;
- [x] permissoes;
- [x] seed;
- [x] expiracao;
- [x] limpeza;
- [x] reset;
- [x] protecao contra abuso;
- [x] observabilidade no codigo e no pacote operacional;
- [x] testes backend relacionados;
- [x] testes frontend;
- [x] E2E local;
- [x] documentacao operacional;
- [ ] homologacao;
- [!] deploy, nao autorizado nesta execucao e com pre-requisitos externos;
- [!] validacao pos-deploy, dependente do deploy.

## 5. Evidencias

| Fase | Arquivos | Teste/comando | Resultado | Commit | Limitacao restante |
| --- | --- | --- | --- | --- | --- |
| Diagnostico Git | dois repositorios | comandos Git obrigatorios | limpos e sincronizados | backend `e623d12`, frontend `752b9ed` | nenhum |
| Diagnostico Django | `config/settings.py`, migrations | `check`, `check --deploy`, `makemigrations --check`, `migrate_schemas --plan` | check local passa com override; migrations pendentes identificadas | nao existe commit novo | ambiente local nao simula Redis de producao |
| Diagnostico da pool | `tenancy/models.py`, commands, tests | leitura de codigo e `test tenancy` | gaps confirmados; suite expirou em 10 minutos | nao existe commit novo | baseline tenancy inconclusiva |
| Diagnostico demo permanente | services, cinco commands, timer, testes, seed, docs e frontend | `rg` e leitura dirigida | todos os seletores automaticos e pressupostos `demo1...demo10` mapeados antes de editar | backend `8d3efe6`, frontend `3d910ca`; nenhum commit novo desta solicitacao | nenhuma limitacao de codigo; falta homologacao |
| Producao read-only | URLs publicas | GETs sem autenticacao | frontend/API/demo1/demo2 200; demo10/health/lease 404 | producao nao alterada | sem acesso SSH para metricas atuais |
| Documentacao | este arquivo | revisao de `GATE`, `WILDCARD`, `OPERACAO` e `PLANO_POOL` | documento novo escolhido; anteriores preservados como historico/runbook manual | nao existe commit novo | atualizar continuamente |
| Lease e troca automatica | `tenancy/services_demo_pool.py`, `tenancy/views_demo_public.py`, `config/public_urls.py`, `config/tenant_urls.py`, `tenancy/models.py`, migration `0003` | `venv/Scripts/python.exe manage.py test tenancy.test_demo_public --keepdb` | 13/13 testes aprovados em PostgreSQL; lease 201, troca CSRF e sessao host-only | nao existe commit novo | flag permanece desligada por padrao |
| Concorrencia e rollback | `tenancy/services_demo_pool.py`, `tenancy/test_demo_public.py` | mesma suite focada | advisory locks por visitante/rede + row lock entregaram um unico slot em duas conexoes; falha simulada reverteu slot e seed | nao existe commit novo | teste depende de PostgreSQL, como a aplicacao |
| Permissoes e seed | `caixa/permissions.py`, `tenancy/services_demo_pool.py` | suite publica, cenarios de permissao/seed/isolamento | usuario sem staff/superuser, somente grupo `Demo Publica`, sem delete/backups; seed idempotente e isolado | nao existe commit novo | confirmar a UX contra backend real em homologacao |
| Expiracao e limpeza | `tenancy/services_demo_pool.py`, `expirar_leases_demo.py` | suite publica, cenario de expiracao | token e metadata apagados; usuario desativado; sessoes, cache e tentativa Axes tenant-scoped removidos | nao existe commit novo | executar com Redis real em homologacao |
| Manutencao automatica | `manter_pool_demo.py`, `resetar_tenant_demo.py`, units `.service`/`.timer` | suite publica e 3 testes legados focados | manutencao real expirou, resetou, refez seed e liberou o slot; ocupar/expirar/resetar legados 3/3 | nao existe commit novo | habilitar e observar timer apenas em homologacao |
| Abuso, falhas e health | `caixa/throttling.py`, `views_demo_public.py`, Nginx | suite publica | throttle 429, `X-Forwarded-For` forjado ignorado, pool cheia 503 sem slots, rollback atomico e health agregado minimo | nao existe commit novo | validar limites Nginx e proxy confiavel no servidor |
| Frontend publico | `app/page.tsx`, `features/demo-public/`, `lib/config/api.ts`, `demo-api-runtime.ts`, auth/layout | `corepack pnpm verify:frontend` | lint, tipos, todos os guardrails e build passaram; 22 rotas geradas | nao existe commit novo | avisos Node de deteccao ESM sao nao bloqueantes |
| E2E | `tests/e2e/public-demo.spec.ts`, `contract-filters.spec.ts`, `package.json` | `corepack pnpm verify:e2e` | 5/5 fluxo publico e 12/12 regressoes, total 17/17 | nao existe commit novo | API e navegador sao integrados por contratos mockados; repetir contra homologacao real |
| Operacao | `docs/deploy/demo-publica/README.md`, env/Nginx/systemd | revisao do runbook e `git diff --check` | provisionamento, ativacao, kill switch, timer, recovery, health, logs e rollback documentados | nao existe commit novo | comandos de servidor nao executados |
| Plano final de migrations | migrations `tenancy.0003`, `tenancy.0004` e migrations existentes de `caixa` | `manage.py migrate_schemas --plan` | tres schemas inspecionados em 2026-07-15; `0004` aparece apos `0003`; nenhum SQL aplicado | nao existe commit novo | aplicar somente com backup/restore testado e na sequencia do runbook |
| Checks finais backend | settings, migrations e Python alterado | `manage.py check`; `makemigrations --check --dry-run`; `compileall`; `migrate_schemas --plan` | todos retornaram codigo 0; nenhuma migration adicional detectada | nenhum commit novo desta solicitacao | plano somente leitura; banco nao alterado |
| Reserva de `demo1` | `config/settings.py`, `command_guards.py`, `services_demo_pool.py`, cinco commands e migration `0004` | `manage.py test tenancy.test_demo_public --keepdb` | 16/16 na execucao final; endpoint, expiracao, manutencao e concorrencia ignoram `demo1`; primeira vaga e `demo2` | nenhum commit novo desta solicitacao | aplicar migration somente em deploy autorizado |
| Commands da pool `demo2+` | provisionar, ocupar, expirar, resetar e guards | classes focadas separadas; repeticoes focadas finais | provisionar 5/5; ocupar 10 cenarios validados; expirar 8/8; reset 11 cenarios validados; guards relacionados aprovados; comandos de pool rejeitam `demo1` | nenhum commit novo desta solicitacao | bateria agregada excede 15 minutos; manter classes separadas no CI |
| Demo permanente | `preparar_demo_permanente.py`, seed e usuario minimo | teste de preparacao permanente | `demo1` sem slot; seed presente; usuario ativo, com senha preservada/fornecida por env, sem staff/superuser e grupo unico | nenhum commit novo desta solicitacao | credencial real deve vir do secret manager no ambiente |
| Fallback frontend | `public-demo-entry.tsx`, `demo-api-runtime.ts`, E2E | `corepack pnpm verify:frontend` e `verify:e2e` | frontend completo verde; E2E 17/17; pool cheia oferece `?tenant=demo1` sem segundo lease | nenhum commit novo desta solicitacao | validar login permanente real em homologacao |
| Recuperacao pos-exchange | `public-demo-service.ts`, `public-demo-entry.tsx`, `public-demo.spec.ts` | `corepack pnpm verify:frontend`; `corepack pnpm run test:e2e:public-demo`; `corepack pnpm run test:e2e` | lint, tipos, guardrails oficiais e build aprovados; E2E publico 13/13; bateria completa 25 aprovados e 1 `rh_teste` ignorado por falta da senha opcional | nenhum commit novo desta solicitacao | repetir contra backend real em homologacao; producao nao foi alterada |
| Reutilizacao e cota por rede | `config/settings.py`, `tenancy/services_demo_pool.py`, `tenancy/views_demo_public.py`, `tenancy/test_demo_public.py`, envs, runbook, `public-demo-service.ts`, `public-demo.spec.ts` | `manage.py check`; `makemigrations --check --dry-run`; classes `DemoPublicFlowTests` e `DemoPublicConcurrencyTests`; `corepack pnpm run verify:frontend`; E2E publico e completo | backend 19/19 + 3/3; sem migration nova; frontend completo verde; E2E publico 15/15; bateria completa 27 aprovados e 1 opcional ignorado; mesmo cookie reutiliza, dois cookies ficam isolados e o terceiro recebe `network_limit` sem ocupar slot | nenhum commit novo desta solicitacao | validar proxy/IP canonico, Redis/throttle e expiracao real em homologacao |

### Tentativas, problemas e correcoes durante a implementacao

| Tentativa | Problema | Decisao | Correcao/reversao |
| --- | --- | --- | --- |
| executar checks com `python` global apos o reinicio | Django nao estava instalado nesse interpretador | nao alterar dependencias | usar `venv/Scripts/python.exe`; `check` e `makemigrations --check` passaram |
| primeira execucao da nova suite com timeout curto | o shell terminou antes do processo filho e um segundo runner disputou `test_rhsaas_dev` | invalidar o resultado contaminado | aguardar o runner unico, remover concorrencia externa e usar `--keepdb` |
| override de settings aplicado como decorator no `TenantTestCase` | flag/schema de entrada nao foram alterados e o endpoint respondeu 404 | configurar explicitamente por teste | ativar/desativar `override_settings` em `setUp`/`tearDown`; cenario isolado e suite 10/10 passaram |
| cobertura inicial de 10 testes backend | faltavam evidencias especificas de Axes, concorrencia em duas conexoes e ciclo real de manutencao | ampliar sem substituir os testes anteriores | suite passou a 13 cenarios e terminou 13/13 |
| `pnpm` apos o reinicio | executavel nao estava no `PATH`, embora Node e Corepack estivessem instalados | respeitar a versao fixada no `packageManager` | todos os comandos foram executados com `corepack pnpm` |
| primeira execucao de `verify:frontend` | guardrail financeiro continha 19 allowlists obsoletas e nao conhecia configuracoes financeiras existentes | atualizar somente o contrato estatico para os imports reais | `check:financial-canonical` e a suite completa passaram |
| segunda execucao de `verify:frontend` | boundary proibia o `fetch` cross-host necessario ao handshake apex/tenant | criar excecao nominal somente para o service da demo publica | direct fetch continua proibido fora do HTTP client e desse service; suite completa passou |
| E2E antigo abria `/` esperando dashboard | a raiz agora e corretamente a entrada publica | manter diagnostico manual explicito | testes de regressao usam `?tenant=demo1`, abortam chamadas externas e continuaram 12/12 |
| bateria agregada de cinco classes backend | custo cumulativo de criacao/reset de schemas excedeu 15 minutos sem resumo | encerrar os dois processos filhos confirmados e dividir por classe | classes separadas produziram resultados deterministas; nenhuma disputa de banco permaneceu |
| classe de ocupacao apos a divisao da pool | teste de slot inexistente provisionava `demo2` por engano | corrigir somente o fixture para `--slots=1` | oito cenarios ja aprovados e o cenario corrigido passou isoladamente |
| classe completa de guards | comando anterior `auditar_snapshots_diaria_orcamentos` nao estava classificado | registrar seu comportamento real como somente leitura | falha focada e novo guard da pool passaram juntos 2/2 |
| primeira verificacao frontend | lint exigiu `Link` para navegacao interna do fallback | usar `next/link` sem mudar o destino | `verify:frontend` completo passou na repeticao |
| E2E pos-exchange na porta `3111` | mocks existentes devolvem CORS apenas para a origem contratual `127.0.0.1:3100`, causando `TypeError: Failed to fetch` | tratar como falso negativo de configuracao, sem mudar o produto | repeticao oficial em `3100` passou 13/13; bateria completa passou 25 testes e ignorou somente o E2E opcional sem senha |
| `check:financial-cache-guardrails` adicional | executor Node direto nao resolve o alias TypeScript `@/lib` antes de iniciar as assercoes | nao alterar codigo financeiro fora do escopo nem confundir com os guardrails oficiais | `verify:frontend`, que inclui os guardrails oficiais, passou integralmente; incompatibilidade antiga do script adicional permanece documentada |
| primeiro `manage.py check` desta fase | o ambiente local continha `DEBUG=release`, valor invalido para booleano, e o Django parou antes de carregar o projeto | nao mascarar nem alterar configuracao persistente fora do escopo | repetir somente no processo com `DEBUG=True`; `check` e `makemigrations --check --dry-run` passaram |
| primeiras chamadas de `verify:frontend` e E2E completo | a janela curta do executor encerrou o launcher antes de produzir resultado | nao classificar timeout da ferramenta como falha do projeto | repetir os mesmos comandos com janela adequada; ambos terminaram com codigo 0 |

## 6. Riscos e bloqueadores

| Risco | Severidade | Impacto | Mitigacao | Estado | Evidencia |
| --- | --- | --- | --- | --- | --- |
| Usuario demo superuser/staff | critica | acesso administrativo e a backups | grupo minimo e flags falsas | mitigado no codigo | teste focado confirma flags falsas e grupo unico |
| Endpoint/fluxo automatico inexistente | bloqueador | visitante nao entra sozinho | lease + troca + pagina publica | mitigado no codigo | backend 13/13, frontend verde e E2E publico 13/13 |
| Dupla alocacao | alta | dois visitantes no mesmo schema | advisory lock por identificador + row lock | mitigado no codigo | teste real com duas conexoes aprovou |
| Senha exposta no frontend | alta | credencial reutilizavel | token HMAC de uso unico | mitigado no codigo | token nao e persistido no browser e o digest e consumido uma vez |
| Sessao/Axes/cache residual | alta | acesso ou dados do visitante anterior | limpeza schema-scoped antes do reset | mitigado localmente | sessao, Axes e cache cobertos no teste de expiracao |
| Exchange consumido com resposta ambigua no navegador | alta | vaga ocupada, token inutilizavel e usuario preso na entrada | persistir lease antes da troca, confirmar sessao e redirecionar para o tenant ja reservado | mitigado no frontend | E2E recupera resposta ambigua sem alerta e sem segundo lease |
| Seed insuficiente | alta | nova vaga vazia/inutilizavel | seed idempotente ficticio | mitigado no codigo | cliente/servicos/orcamento/evento isolados em teste |
| Pool incompleta | alta | capacidade menor e 404 | preservar `demo1` e provisionar nove vagas `demo2...demo10` | bloqueado para deploy | demo10 externo 404 |
| Migrations pendentes | alta | schemas divergentes | aplicar na sequencia de deploy aprovada | bloqueado para deploy | `migrate_schemas --plan` |
| Config local `DEBUG=release` | media | comandos falham sem override | corrigir ambiente local, nao o codigo | aberto | `manage.py check` |
| Timer inexistente | alta | leases nunca liberados sozinhos | `manter_pool_demo` + unit/timer systemd | mitigado no pacote | ciclo real testado localmente; ativacao do timer depende do deploy |
| Renovacao TLS wildcard | alta | tenants ficam indisponiveis | automatizar ACME DNS e monitorar | bloqueado operacional | gate historico |
| VM de 1 GB | media | OOM/502 com concorrencia | 1 worker/2 threads, pool conservadora, sem carga agressiva | monitorar | gate historico |
| Guardrail financial-canonical | media | gate frontend global falha | alinhar allowlists aos imports reais | encerrado | `verify:frontend` completo aprovado |
| Integracao em ambiente real | alta | CORS, CSRF, cookies, TLS ou proxy podem divergir do teste | deploy de homologacao com flag inicialmente desligada e checklist | pendente | E2E local 17/17; homologacao nao executada |
| Suite completa de tenancy longa | media | regressao fora dos cenarios focados pode passar despercebida | executar em CI/ambiente com janela maior e medir testes lentos | aberto, nao bloqueia homologacao tecnica | tentativa inicial excedeu 10 minutos sem resumo; relacionados 16/16 |
| Terceiro visitante legitimo na mesma rede compartilhada | media | escolas, escritorios ou CGNAT podem atingir a cota mesmo com pessoas distintas | cota configuravel, mensagem especifica, reutilizacao do navegador original e liberacao por expiracao | risco aceito para abertura controlada | testes confirmam dois tenants isolados e terceiro sem slot; valor inicial 2 |
| Troca de IP, VPN ou multiplas redes | media | agente abusivo pode contornar a cota e consumir outras vagas | throttle existente, pool finita, leases curtos, logs agregados e monitoramento de `network_limit`/`pool_full` | residual, monitorar | nao ha fingerprint nem coleta adicional de PII por decisao de privacidade |
| Rotacao de `SECRET_KEY` durante leases ativos | baixa | o mesmo IP passa a produzir outro HMAC ate os leases anteriores expirarem | nao rotacionar durante janela ativa sem esvaziar a pool; expiracao/reset remove hashes antigos | residual operacional | identificadores persistidos sao apenas HMAC e nao sao reversiveis sem o segredo |

## 7. Mudancas de escopo e decisoes substituidas

### Credencial temporaria

Decisao anterior considerada: retornar username e senha temporaria no endpoint.

Decisao final: token de troca de uso unico, armazenando somente digest.

Motivo: evitar exposicao, persistencia e reuso de senha no frontend.

### Dados pessoais para reservar vaga

Decisao anterior do pool manual: exigir nome e e-mail e aceitar telefone.

Decisao final para a entrada automatica: nao solicitar dados pessoais. Usar
somente identificadores anonimos assinados/hasheados com retencao do lease.

Motivo: finalidade de portfolio e principio de minimizacao de dados.

### Duracao

Decisao anterior do pool manual: tres dias.

Decisao final para entrada publica: uma hora por padrao, configuravel.

Motivo: pool de dez vagas e capacidade limitada da VM.

### Automacao publica

Decisao historica: manter a tela publica e a alocacao automatica fora de
escopo ate validar a pool manual.

Decisao atual: implementar a automacao porque wildcard, guards, isolamento e
reset manual ja possuem base validada; manter os documentos antigos como
historico.

### Composicao da pool automatica

Decisao anterior: `demo1...demo10` eram todos slots temporarios e o primeiro
livre era entregue pelo endpoint.

Decisao final: `demo1` e permanente; somente `demo2...demo10` participam de
lease, expiracao e reset automaticos.

Motivo: manter um ambiente sempre acessivel para demonstracao e oferecer
fallback seguro quando as nove vagas temporarias estiverem ocupadas.

### Extensao de acesso de testadores

Decisao considerada: tornar um usuario de uma vaga temporaria ilimitado.

Decisao final: `demo1` e ilimitado por ser um tenant permanente, sem lease. Em
`demo2...demo10`, qualquer extensao futura deve ser finita e atualizar o lease
da vaga inteira, nao apenas o usuario. Necessidade realmente permanente deve
receber tenant dedicado fora da pool.

Motivo: uma sessao ilimitada dentro de slot temporario impediria reset seguro,
reduziria a capacidade indefinidamente e poderia divergir do estado do lease.

## 8. Operacao

O procedimento completo e os comandos de servidor estao em
`docs/deploy/demo-publica/README.md`. Resumo operacional:

- provisionamento: validar migrations, executar
  `provisionar_pool_demo --slots=10 --dry-run` e somente depois sem `--dry-run`;
  isso cria infraestrutura para dez tenants, mas slots apenas para
  `demo2...demo10`;
- demo permanente: executar `preparar_demo_permanente --dry-run`; depois
  executar sem dry-run, preservando senha existente ou fornecendo senha apenas
  por `--password-env` ligado a secret do ambiente;
- ativacao publica: manter `DEMO_PUBLIC_LEASE_ENABLED=False` durante migrations,
  pool e smoke tests; mudar para `True` apenas depois da homologacao e reiniciar
  `rhsaas-demo`;
- desativacao rapida: voltar a flag para `False` e reiniciar o servico; isso
  interrompe novas reservas sem apagar slots existentes;
- expiracao/limpeza/reset: timer de dois minutos chama `manter_pool_demo`, que
  desativa acesso, limpa sessao/Axes/cache, reseta, semeia e libera; validar
  primeiro com `manter_pool_demo --dry-run`; toda a varredura e restrita a
  `demo2...demo10`;
- recuperacao de slot preso: inspecionar schema, domain, slot, logs e arquivos;
  usar `expirar_leases_demo --slot=demoN --dry-run` e
  `resetar_tenant_demo --slot=demoN --confirm="RESETAR demoN" --dry-run`; nunca
  trocar `bloqueado` diretamente para `livre`;
- pool cheia: HTTP 503 com `code=pool_full`, sem lista de vagas; frontend oferece
  `?tenant=demo1` sem chamar o lease novamente; revisar apenas contagens
  agregadas de `demo2...demo10` e leases vencidos;
- falha parcial: rollback transacional antes do commit; falha de reset deixa
  slot bloqueado e reduz capacidade ate diagnostico;
- rollback: desligar a flag, parar o timer se necessario, preservar logs/slots
  bloqueados, voltar ao artefato aprovado e reverter migration somente com
  plano especifico e restore testado;
- logs: `journalctl` das units da API e manutencao; eventos esperados sao lease,
  troca, expiracao e reset, sem token, senha, hash anonimo, IP puro ou PII;
- health: `/api/health/` no apex e em um tenant, com resposta agregada minima;
- diagnostico de recursos: `free -h`, `df -h`, processos por RSS e
  `systemctl show` para memoria/tarefas;
- ordem obrigatoria: backup e restore testado, codigo com flag off, migrations,
  pool completa, systemd/Nginx/TLS, smoke/health, homologacao E2E, flag on e
  validacao pos-deploy.

## 9. Criterios de conclusao

A tarefa somente pode ser considerada concluida quando todos os itens abaixo
estiverem comprovados:

- [~] fluxo automatico funciona de ponta a ponta local por contratos; falta
  repetir frontend/backend reais juntos em homologacao;
- [x] concorrencia impede dupla alocacao;
- [x] pool cheia e tratada sem vazamento;
- [x] usuario tem permissoes minimas e nao e staff/superuser;
- [x] expiracao automatizada no comando e timer;
- [x] reset e seed funcionam;
- [x] isolamento entre tenants esta testado;
- [x] backend esta verde nos testes relacionados;
- [x] frontend esta verde nos testes relacionados;
- [x] E2E publico local esta passando;
- [x] documentacao operacional esta atualizada;
- [x] nao existe bloqueador de codigo para iniciar homologacao;
- [!] liberacao publica nao pode ser concluida antes de pool completa,
  migrations, TLS/backup/recursos, homologacao e validacao pos-deploy.

Conclusao atual: o pacote de codigo esta pronto para deploy de homologacao com
a flag inicialmente desligada. A abertura publica em producao nao esta pronta
e nao sera marcada como concluida sem autorizacao explicita e evidencia dos
pre-requisitos e do ambiente.

## 10. Sequencia exata para homologacao e producao

O runbook executavel, arquivos de systemd/Nginx e checklist detalhado estao em
`docs/deploy/demo-publica/README.md`. A ordem abaixo nao autoriza deploy; ela
deve ser executada primeiro em homologacao e somente depois, com as evidencias
aprovadas, repetida em producao.

### Homologacao

1. Registrar commit/artefato candidato, manter
   `DEMO_PUBLIC_LEASE_ENABLED=False`, configurar `demo1` permanente e
   `demo2...demo10` na pool.
2. Criar backup do banco de homologacao e comprovar restauracao em ambiente
   separado.
3. Publicar backend e frontend candidatos sem ativar a entrada publica.
4. No diretorio do backend, executar, nesta ordem:

```bash
venv/bin/python manage.py check --deploy
venv/bin/python manage.py makemigrations --check --dry-run
venv/bin/python manage.py migrate_schemas --plan
venv/bin/python manage.py migrate_schemas --shared
venv/bin/python manage.py migrate_schemas
venv/bin/python manage.py provisionar_pool_demo --slots=10 --dry-run
venv/bin/python manage.py provisionar_pool_demo --slots=10
venv/bin/python manage.py preparar_demo_permanente --dry-run
venv/bin/python manage.py manter_pool_demo --dry-run
```

5. Se o dry-run informar `usuario_pronto=sim`, executar
   `preparar_demo_permanente` sem senha. Se informar `nao`, carregar a senha
   do secret manager em `DEMO_PERMANENT_PASSWORD`, executar com
   `--password-env=DEMO_PERMANENT_PASSWORD` e remover a variavel.
6. Instalar/recarregar as units e o Nginx conforme o runbook; validar timer,
   health, DNS e TLS, ainda com a flag desligada.
7. Homologar `?tenant=demo1`, login permanente, seed e permissoes minimas.
8. Confirmar no schema `public` que nao existe slot `demo1` e que existem
   exatamente nove slots `demo2...demo10`.
9. Ativar a flag, reiniciar a API e executar o E2E real: alocacao em `demo2+`,
   troca de token, isolamento, concorrencia, pool cheia/fallback e um ciclo
   completo de expiracao/reset pelo timer.
10. Desativar novamente a flag se qualquer gate falhar; nao liberar slot
    manualmente para contornar falha.

### Producao

1. Exigir o artefato exato aprovado em homologacao e anexar as evidencias do
   E2E real, backup/restore, capacidade, TLS e timer.
2. Manter a flag desligada, fazer backup de producao e comprovar o ponto de
   restauracao; registrar health e recursos antes da mudanca.
3. Publicar o mesmo backend, executar os checks, plano, migrations,
   provisionamento e preparacao de `demo1` na mesma ordem de homologacao.
4. Confirmar preservacao de schema, Domain, dados e usuario de `demo1`; nunca
   executar comandos de ocupar, expirar ou resetar contra ele.
5. Publicar o mesmo frontend, validar health, `?tenant=demo1`, nove slots,
   systemd, Nginx e TLS com a entrada ainda desligada.
6. Ativar a flag, reiniciar `rhsaas-demo`, executar um smoke publico completo
   e acompanhar logs/health/timer ate a vaga usada expirar, resetar e voltar
   limpa para a pool.
7. Em falha, desligar a flag e reiniciar a API; parar o timer apenas se ele for
   a causa, preservar slots bloqueados/evidencias e seguir o rollback do
   runbook. Nao reverter `0004` nem recriar slot para `demo1` sem plano de dados
   especifico e restore testado.
