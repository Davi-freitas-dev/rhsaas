# Plano de liberacao da demo publica automatica

Documento de acompanhamento da preparacao do RH SaaS para abertura publica
como demo tecnica de portfolio com distribuicao automatica de tenants.

Atualizado em: 2026-07-16

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

### Diagnostico de retomada imediata apos logout em 2026-07-15

Estado inicial desta fase: backend `f053f3f`, branch
`feat/django-tenants-spike`, e frontend `433a939`, branch `main`, ambos limpos.
Nenhuma consulta ou alteracao de producao foi realizada.

Diagnostico read-only:

- o logout encerra a sessao do tenant, limpa caches financeiros e remove do
  `localStorage` o tenant, a URL da API e a expiracao;
- o cookie assinado e `HttpOnly` `rhsaas_demo_visitor` pertence ao host publico
  de entrada, nao e apagado pelo logout e continua identificando o visitante;
- ao voltar para `/`, o frontend deve continuar exibindo a entrada publica e,
  no novo clique, chama `POST /api/demo/lease/`;
- o backend ja consegue reutilizar o lease pelo cookie e preservar tenant e
  `lease_expires_at`, emitindo somente um novo token de exchange para recriar a
  sessao encerrada;
- entretanto, o `DemoLeaseRateThrottle` do DRF roda antes da view e antes de
  `allocate_demo_lease`; assim, a requisicao pode receber 429 antes de o lease
  existente ser reconhecido;
- a mensagem `Pedido foi suprimido... disponivel em 90 segundos` e o formato do
  throttle do DRF. O Nginx tambem protege `/api/demo/lease/` com `3r/m` e burst
  2, mas nao gera esse detalhe e deixou a requisicao observada chegar ao DRF;
- preservar apenas o lease local nao basta, pois o token de exchange e de uso
  unico e a sessao foi encerrada; criar `/api/demo/resume/` duplicaria contrato
  sem necessidade.

Decisao: opcao B. O throttle reconhece cookie valido com lease ativo e usa a
cota `demo_lease_resume`, padrao `10/hour` por HMAC do visitante, enquanto
visitante sem lease continua em `demo_lease`, padrao `3/hour` por IP canonico.
A requisicao liberada por retomada e marcada como `resume_only`, impedindo nova
alocacao se o lease expirar antes da transacao. Nginx, limite de rede, exchange
throttle e pool cheia permanecem inalterados.

Implementacao e evidencias:

- leitura/geracao do cookie foi centralizada em `tenancy/demo_visitor.py`;
- `has_active_demo_lease` consulta somente HMAC, slot publico ocupado e
  expiracao futura, restaurando o schema original apos a consulta;
- a retomada preserva `apiBaseUrl`, `lease_started_at` e `expiresAt`, cria
  somente novo token de exchange e reabre a sessao no mesmo tenant;
- visitante novo continua recebendo 429 quando a cota de nova alocacao esta
  esgotada; repeticoes abusivas de retomada tambem recebem 429 pela cota propria;
- observacao adicional de producao mostrou `Retry-After` saltando de 90 para
  1876 segundos, comportamento de janela deslizante/historico de throttle, nao
  renovacao do lease; producao nao foi acessada nem alterada nesta execucao;
- `DemoPublicFlowTests` passou 21/21 e concorrencia 3/3; `check`,
  `makemigrations --check --dry-run`, frontend completo e E2E publico 15/15
  passaram. Nenhuma migration ou endpoint novo foi criado.

Estado da fase: `[x]` implementacao e validacao local concluidas. Homologacao e
producao permanecem pendentes e intocadas.

### Diagnostico do aviso transitorio no logout em 2026-07-16

Diagnostico: o dashboard principal encerrava a sessao com
`logoutFromBackend()` e, antes de o cabecalho redirecionar para `/`, chamava
`refetch()`. A nova consulta ja sem autenticacao falhava e renderizava por
instantes o aviso de dados desatualizados. A auditoria global posterior das 16
ocorrencias de `logoutFromBackend()` encontrou o mesmo padrao em backups, FCF,
obrigacoes financeiras e FCI. Custos extras tambem fazia duas consultas
posteriores ao logout: permissao e dados.

Decisao: remover somente consultas executadas dentro dos handlers depois de
`logoutFromBackend()`. A sessao, caches e lease local continuam sendo limpos
pelo service de autenticacao, e o cabecalho continua responsavel pelo
redirecionamento. Os demais `refetch()` de atualizacao, retry e mutacoes com
sessao ativa permanecem intactos. Nao esconder alertas reais de atualizacao.

Evidencia: o E2E observa separadamente consultas posteriores ao
logout no dashboard principal e em backups, aguarda a resposta do logout, a
URL publica final e o estado de rede ociosa, sem espera fixa. Tambem exige
ausencia de estado residual e reutilizacao do mesmo lease e expiracao. E2E
publico passou 16/16. `verify:frontend` passou com lint, typecheck, guardrails
oficiais e build de producao das 22 rotas; `git diff --check` passou.

Estado da fase: `[x]` correcao global e validacao local concluidas; producao nao
foi alterada.

### Diagnostico de disponibilidade e lease ativo na entrada em 2026-07-16

Estado inicial: backend `2318f46`, branch `feat/django-tenants-spike`, e
frontend `c58f42b`, branch `main`, ambos limpos. Nenhuma consulta ou alteracao
de producao foi realizada.

Diagnostico read-only apresentado antes da implementacao:

- nao existe endpoint publico de status da pool; `/api/health/` informa apenas
  `status` e `demoEntryEnabled`;
- o visitante e reconhecido somente pelo cookie assinado e `HttpOnly`
  `rhsaas_demo_visitor`; a raiz limpa corretamente o lease operacional do
  `localStorage`, portanto o estado local nao deve ser usado para restaurar o
  dashboard automaticamente;
- o contador interno usa o `expiresAt` original do backend e recalcula o tempo
  restante pelo relogio local;
- `DemoTenantSlot.Status.LIVRE` e a autoridade de prontidao: expirado,
  bloqueado ou ainda em reset nao e anunciado como disponivel; o reset so muda
  para `livre` depois de recriar schema, tabelas e seed;
- a configuracao central `DEMO_PUBLIC_POOL_SLOTS` permite contar apenas a pool
  automatica e exclui `demo1` sem condicional espalhada;
- consultar disponibilidade no throttle de lease consumiria a cota errada;
  sera usado o escopo separado `demo_status`;
- a disponibilidade e informativa e pode mudar entre GET e POST; a transacao,
  os advisory locks e `select_for_update` do lease continuam como autoridade;
- a retomada visual precisa declarar intencao explicita no POST existente para
  que um lease expirado entre status e clique retorne `resume_unavailable` sem
  ocupar silenciosamente outra vaga.

Decisao: adicionar `GET /api/demo/status/`, somente leitura e `no-store`, com
capacidade agregada e dados do proprio lease quando o cookie corresponder a um
slot ativo. O endpoint nao cria token, nao renova prazo, nao executa seed/reset
e usa throttle proprio. O frontend consulta ao abrir, em polling moderado e ao
voltar para a aba; `/` permanece publica. `Continuar demo` reutiliza o POST de
lease com intencao `resume`, preservando prazo e tenant. Nao e necessario novo
endpoint de retomada, migration ou bloco Nginx.

Contrato implementado:

```json
{
  "enabled": true,
  "capacity": { "total": 3, "available": 2 },
  "activeLease": {
    "exists": true,
    "tenant": "demo2",
    "expiresAt": "2026-07-16T03:43:50Z",
    "remainingSeconds": 2418
  }
}
```

Sem lease proprio, `activeLease` contem apenas `exists=false`. A resposta nunca
lista slots, visitantes, rede, hashes, cookies ou tokens. `total` vem de
`DEMO_PUBLIC_POOL_SLOTS`; `available` conta somente registros `livre`. Em
producao, a configuracao atual `demo2...demo4` resulta em total tres, sem
assuncao desse numero pelo frontend.

Implementacao e evidencias:

- backend: `tenancy/services_demo_pool.py` faz a leitura agregada no schema
  publico; `tenancy/views_demo_public.py` publica o GET e aceita somente
  `{"resume": true}` como retomada explicita; `config/public_urls.py` e
  `config/tenant_urls.py` registram a rota, que devolve 404 nos slots
  temporarios;
- throttle: `caixa/throttling.py` e `config/settings.py` adicionam o escopo
  `demo_status`; `.env.example` e
  `docs/deploy/demo-publica/.env.production.example` registram
  `DRF_THROTTLE_DEMO_STATUS_RATE`, com recomendacao de `30/minute` em ambiente
  publicado;
- frontend: `public-demo-service.ts` valida o contrato, distingue pool cheia,
  limite de rede, retomada expirada e throttle; `public-demo-entry.tsx` mantem a
  landing visivel durante a leitura e usa retomada explicita;
  `public-demo-availability.tsx` e `demo-lease-time.ts` exibem capacidade e
  contador local baseado em `expiresAt`, com polling de status a cada 60 s e
  atualizacao ao voltar para a aba;
- `python manage.py check`: sem problemas; `makemigrations --check --dry-run`:
  nenhuma alteracao; nao existe migration nova;
- oito testes focados de status/retomada em `tenancy/test_demo_public.py`:
  `8/8 OK` em 137,812 s; dois testes concorrentes em execucao independente:
  `2/2 OK` em 267,495 s; o teste de manutencao/reset tambem passou na execucao
  anterior da classe transacional;
- `pnpm run verify:frontend`: passou na repeticao final em 125,8 s, incluindo lint, typecheck,
  guardrails de dominio/layout/cache/acessibilidade/runtime e build das 22
  rotas; `pnpm run test:e2e:public-demo`: `21/21` em 2,7 min;
- limitacao restante: disponibilidade e uma fotografia informativa. A
  transacao do POST continua sendo a autoridade se o estado mudar entre GET e
  clique. Homologacao com backend real, cookies entre hosts e timer permanece
  obrigatoria antes de producao.

Estado da fase: `[x]` implementacao e validacao local concluidas; producao e
Nginx permaneceram intocados.

### Diagnostico da ampliacao de permissoes e protecao do seed em 2026-07-16

Estado: `[!]` diagnostico read-only concluido; ampliacao de permissoes
bloqueada ate existir identificacao explicita dos objetos seed. Nesta etapa
nenhum codigo, model, migration, banco, teste ou ambiente publicado foi
alterado. A unica alteracao autorizada foi este registro documental.

Estado observado: backend `5f90af4`, branch `feat/django-tenants-spike`, e
frontend `a0ebb69`, branch `main`, ambos limpos antes deste registro.

Segunda passada read-only: o diagnostico foi repetido contra os mesmos commits
para revisar omissoes e contradicoes. Foram confirmados quatro pontos novos
para a futura implementacao: replace-all de itens no PUT de orcamento como
efeito da edicao, teste existente que exige reaprovacao idempotente, fixtures
que dependem de seed durante alocacao e necessidade de negar toda escrita
enquanto um schema demo legado ainda nao possuir o conjunto completo de chaves
seed.

#### Grupo, fonte canonica e associacao do usuario

A fonte canonica e a configuracao declarativa `PERMISSION_PROFILES` em
`caixa/permissions.py`. O grupo nao e criado por fixture nem por migration de
dados: `sincronizar_grupos_permissoes()` faz `get_or_create` e substitui o
conjunto inteiro com `group.permissions.set(...)`. Portanto, a futura
allowlist deve continuar nesse ponto; nao deve existir uma segunda lista em
command, seed ou signal.

O perfil `Demo Publica` declara atualmente 22 permissoes, todas do app
`caixa`:

| App label | Model | Codenames atuais |
| --- | --- | --- |
| `caixa` | `Cliente` | `view_cliente`, `add_cliente`, `change_cliente` |
| `caixa` | `Servico` | `view_servico`, `add_servico`, `change_servico` |
| `caixa` | `ConfiguracaoFinanceira` | `view_configuracaofinanceira` |
| `caixa` | `Orcamento` | `view_orcamento`, `add_orcamento`, `change_orcamento`, `approve_orcamento` |
| `caixa` | `OrcamentoItem` | `view_orcamentoitem`, `add_orcamentoitem`, `change_orcamentoitem` |
| `caixa` | `Evento` | `view_evento`, `add_evento`, `change_evento` |
| `caixa` | `ReceitaOperacional` | `view_receitaoperacional` |
| `caixa` | `DespesaOperacional` | `view_despesaoperacional` |
| `caixa` | `CustoFixo` | `view_custofixo` |
| `caixa` | `EventoCustoServico` | `view_eventocustoservico` |
| `caixa` | `EventoCustoExtra` | `view_eventocustoextra` |

`sync_demo_public_user()` e `sync_demo_permanent_user()` executam a
sincronizacao, associam exatamente o grupo `Demo Publica`, limpam permissoes
diretas e forcam `is_staff=False` e `is_superuser=False`. A associacao ocorre
na criacao/reativacao manual, na alocacao automatica, na retomada e na
preparacao de `demo1`.

Mapa do ciclo de sincronizacao:

- tenant novo: `Tenant.save()` cria o schema e executa migrations; o
  `post_migrate` de `caixa/signals.py` sincroniza os grupos em todo schema
  tenant e ignora `public`;
- slot novo para tenant ja existente: a criacao isolada de `DemoTenantSlot`
  nao sincroniza; o grupo sera sincronizado no proximo seed ou usuario;
- provisionamento repetido de tenant existente: nao ha sincronizacao
  explicita no command;
- seed: sincroniza os grupos antes dos dados;
- ocupacao/reocupacao e recriacao do usuario: sincronizam o grupo e removem
  permissoes diretas;
- reset: recria schema e migrations, recebe o `post_migrate` e depois executa
  o seed, que sincroniza novamente;
- deploy com `migrate_schemas`: reaplica pelo `post_migrate` em cada tenant.

Rastreabilidade das fontes atuais:

| Responsabilidade | Arquivo e simbolo canonico | Observacao |
| --- | --- | --- |
| allowlists dos grupos | `caixa/permissions.py::PERMISSION_PROFILES` | unica fonte declarativa; `Demo Publica` tem 22 codenames unicos |
| sincronizacao exata | `caixa/permissions.py::sincronizar_grupos_permissoes` | usa `permissions.set`, mas nao acusa codename ausente |
| sincronizacao por migration | `caixa/signals.py::criar_grupos_permissoes` | `post_migrate` somente em schema tenant |
| usuario temporario | `tenancy/services_demo_pool.py::sync_demo_public_user` | grupo unico, sem permissoes diretas, staff/superuser falsos |
| usuario permanente | `tenancy/services_demo_pool.py::sync_demo_permanent_user` | mesmas flags e grupo; preserva/exige senha utilizavel |
| seed | `tenancy/services_demo_pool.py::seed_demo_tenant` | dados raiz e aprovacao que gera derivados |
| alocacao/retomada | `tenancy/services_demo_pool.py::allocate_demo_lease` | chama seed e usuario nos dois caminhos atuais |
| expiracao | `tenancy/services_demo_pool.py::expire_due_demo_leases` | desativa acesso e muda para `expirado`, sem liberar |
| reset | `tenancy/management/commands/resetar_tenant_demo.py` | drop/recreate/seed antes de `livre`; falha deixa `bloqueado` |
| manutencao | `tenancy/management/commands/manter_pool_demo.py` | expira e chama reset; ignora `demo1` |
| ocupacao manual | `tenancy/management/commands/ocupar_tenant_demo.py` | exige `livre` e sincroniza usuario, mas nao valida seed |
| provisionamento | `tenancy/management/commands/provisionar_pool_demo.py` | cria schema/domain/slot; schema novo recebe grupos por migration, mas nao seed |
| demo permanente | `tenancy/management/commands/preparar_demo_permanente.py` | executa seed e sincroniza usuario de `demo1` |

Risco residual: `permissions.set()` remove permissoes antigas e e idempotente,
mas codenames declarados e ainda ausentes no banco sao silenciosamente
ignorados pelo filtro. O seed valida nomes de grupos, nao a existencia de cada
codename. A futura sincronizacao deve falhar de forma explicita se o conjunto
de codenames encontrado diferir da allowlist e o provisionamento deve validar
o conjunto final. Isso continua sendo implementado na fonte canonica atual.

#### Seed atual, momento de execucao e isolamento

`seed_demo_tenant()` em `tenancy/services_demo_pool.py` e a fonte do seed. Ele
cria diretamente:

- uma `ConfiguracaoFinanceira` ativa, apenas quando nenhuma ativa existe;
- um `Cliente`, localizado por CPF/CNPJ visivel;
- dois `Servico`, localizados por `codigo` visivel;
- um `Orcamento`, localizado pelo numero visivel;
- dois `OrcamentoItem`, apenas quando o orcamento acaba de ser criado.

O seed aprova o orcamento e, por services e signals, cria ou sincroniza tambem
`Evento`, `ReceitaOperacional`, `DespesaOperacional`,
`EventoCustoServico`, `LancamentoFinanceiro` e `ObrigacaoFinanceira`. O seed
atual nao inclui custo extra nem pagamentos porque o orcamento ficticio nao
possui esses itens.

A idempotencia observada e parcial e depende de chaves de negocio. Cliente e
servicos usam `update_or_create` e sao sobrescritos em toda chamada. Se o
visitante mudar CPF/CNPJ ou codigo, a proxima retomada pode criar outro
registro com a chave original, enquanto o orcamento continua referenciando o
registro alterado. A configuracao reaproveita a primeira ativa, que pode ser
uma configuracao criada pelo visitante. O orcamento existente nao tem
itens/evento recriados porque o bloco derivado roda somente quando ele e novo.
Assim, a chamada repetida pode simultaneamente sobrescrever, duplicar e deixar
partes alteradas, dependendo do campo modificado. O teste atual verifica apenas
as contagens raiz de cliente, servicos, orcamento e evento apos duas alocacoes.

`seed_demo_tenant()` tambem nao abre sua propria `transaction.atomic()`. Na
alocacao ele participa da transacao externa e uma falha posterior reverte o
seed. No reset, uma falha parcial deixa o slot bloqueado e um novo reset remove
o schema incompleto, preservando isolamento. Em `demo1`, entretanto, uma falha
do command de preparacao pode deixar seed parcial. A versao futura deve tornar
a criacao/adocao do conjunto seed atomica no schema corrente e validar o
conjunto completo antes de considerar o ambiente pronto.

O desvio de ciclo de vida confirmado e importante: `allocate_demo_lease()`
chama `seed_demo_tenant()` antes de criar o token tanto em alocacao nova quanto
em retomada do mesmo lease. Portanto, logout/retomada pode sobrescrever o
cliente e os servicos seed durante um lease. Exchange e consulta de sessao nao
semeiam, mas o POST de lease/retomada que os antecede semeia. O command manual
`ocupar_tenant_demo` sincroniza o usuario, mas nao semeia; um tenant apenas
provisionado pode ser ocupado manualmente ainda vazio.

Nao existe campo, tag, manager, object permission ou registro externo que
distinga seed de dado posterior. Os valores visiveis usados pelo seed nao sao
uma fronteira de autorizacao aceitavel: podem mudar e podem ser reproduzidos
por um visitante. `Cliente`, `Servico`, `ConfiguracaoFinanceira`, `Orcamento`,
`OrcamentoItem` e `Evento` nao possuem `created_by`/`owner`. Parte dos modelos
financeiros possui `criado_por` e `atualizado_por`, mas o seed roda antes da
criacao do usuario temporario e varios derivados ficam sem autor. Alem disso,
todos os visitantes do slot usam o mesmo username `demo`; autoria isolada nao
separa leases e nao cobre os objetos raiz.

O isolamento entre visitantes, por outro lado, e forte no fluxo normal:
alocacao automatica e manual selecionam apenas status `livre`; expiracao muda
para `expirado`; reset aceita apenas `expirado`/`bloqueado`, faz `DROP SCHEMA
... CASCADE`, recria schema e migrations, recria o seed e so entao marca
`livre`. Qualquer falha mantem o slot `bloqueado`. Nao foi encontrado caminho
de aplicacao que reocupe slot expirado ou bloqueado sem reset. Alterar status
diretamente no banco continua sendo um bypass operacional proibido. Com esse
invariante preservado, nao ha justificativa para adicionar identificador de
lease a todos os objetos.

#### Matriz atual de telas e APIs

| Funcionalidade | Endpoint e metodo | Autorizacao backend | Resultado atual para `Demo Publica` | Bloqueio adicional |
| --- | --- | --- | --- | --- |
| Clientes | `GET/POST /api/clientes/`; `GET/PUT /api/clientes/{id}/` | `view/add/change_cliente` | todos permitidos | nenhum controle por objeto; cliente seed pode ser alterado |
| Servicos | `GET/POST /api/servicos/`; `GET/PUT /api/servicos/{id}/` | `view/add/change_servico` | todos permitidos | nenhum controle por objeto; servicos seed podem ser alterados |
| Configuracoes | `GET/POST /api/configuracoes-financeiras/`; `GET/PUT .../{id}/` | `view/add/change_configuracaofinanceira` | GET permitido; POST/PUT 403 | frontend desabilita criar/editar |
| Orcamentos | `GET/POST /api/orcamentos/`; `GET/PUT .../{id}/` | GET `view`; POST `add_orcamento` + `add_orcamentoitem`; PUT apenas `change_orcamento` | permitidos | PUT apaga e recria itens/custos extras, sem `change_orcamentoitem` nem `delete_*`; status aprovado impede PUT do seed, mas nao e politica de seed |
| Itens de orcamento | embutidos no POST/PUT de orcamento | ver linha anterior | criar/editar permitidos nos orcamentos editaveis | nao existe endpoint proprio; filhos do seed dependem apenas do status do pai |
| Aprovar orcamento | `POST /api/orcamentos/{id}/aprovar/` | `approve_orcamento`, usuario ativo e schema tenant | permitido | nao valida seed, status editavel, ja aprovado nem `change_orcamento` |
| Eventos | `GET /api/eventos/`; `GET/PUT /api/eventos/{id}/` | `view/change_evento` | listar/ver/editar permitidos | nao ha POST; evento seed pode ser alterado |
| Receitas | listagem agregada; `GET/PUT /api/receitas/{id}/` | `view/change_receitaoperacional` | leitura permitida; PUT 403 | nao ha POST de criacao no contrato Next atual |
| Despesas | listagem agregada; `GET/PUT /api/despesas/{id}/` | `view/change_despesaoperacional` | leitura permitida; PUT 403 | nao ha POST de criacao no contrato Next atual |
| Custos fixos | `GET/POST /api/custos-fixos/`; `GET/PUT .../{id}/` | `view/add/change_custofixo` | GET permitido; POST/PUT 403 | frontend fica somente leitura |
| Custos extras | leitura agregada; `POST /api/eventos/custos-extras/` | `view_eventocustoextra`; POST `add_eventocustoextra` | leitura permitida; POST 403 | nao ha PUT dedicado; frontend desabilita criacao |
| Custos de servico | dashboards/obrigacoes | `view/change_eventocustoservico` e permissao de pagamento por operacao | leitura permitida; alteracao/pagamento bloqueados | custos sao derivados do orcamento; nao ha PUT dedicado |
| Pagamentos | fila em `/api/obrigacoes-financeiras/`; POST `/api/obrigacoes-financeiras/liquidar/` | permissao por origem: change de despesa/custo/investimento/financiamento ou `add_pagamento*` | fila e liquidacao 403 | sidebar esconde por `canUsePayments=false` |
| Dashboard | `GET /api/dashboard/financial-overview/` e `/api/custos-por-evento/` | `view_evento` | permitido | somente leitura |
| Fluxo de caixa | `GET /api/mes-financeiro/` | `view_parceladivida` + `view_receitaoperacional` | 403 | sidebar nao oferece rota sem a capacidade |
| Ledger/modelagem | `GET /api/lancamentos-financeiros/`, modelagem e baixas canonicas | `view_lancamentofinanceiro` | 403 | nenhuma exigencia de staff/superuser |
| Obrigacoes | `GET /api/obrigacoes-financeiras/` | geral: `view_lancamentofinanceiro`; consulta por origem pode usar seu `view_*` | tela geral oculta/403; consultas limitadas por origem podem funcionar | liquidacao revalida permissao por origem no service |
| FCI | `GET/POST /api/fci/` | `view_investimento`; POST tambem `add_investimento` | 403 | nao ha endpoint de edicao; liquidacao usa `change_investimento` |
| FCF/credores | `GET/POST /api/fcf/`, `POST /api/fcf/debts/`, `GET/POST /api/fcf/creditors/` | `view_parceladivida`; `add_financiamentomovimentacao`; `add_dividafinanceira`; `view/add_credor` | 403 | nao ha endpoints de edicao desses cadastros; liquidacao usa change/add por origem |
| Exportacao CSV | `GET /api/obrigacoes-financeiras/exportar/` | mesma autorizacao por escopo/origem + throttle | receitas/despesas por origem podem exportar; obrigacoes gerais e pagamentos retornam 403 | nao exige staff; e tenant-scoped |
| Backups | `GET /api/backups/`; `POST /api/backups/criar/` | tenant administrator (`is_superuser` no schema tenant) | 403 | grupo/codename comum nao libera |
| Download de backup | `GET /backups/{arquivo}/download/` | tenant administrator + throttle | negado/redirecionado pelo guard | caminho permanece tenant-scoped |
| Restauracao/importacao | nao existe endpoint HTTP de restore | somente operacao/management command | indisponivel | acesso a command nao e concedido pela allowlist web |
| Django Admin | `/admin/` | `is_staff` e permissoes | indisponivel | `demo` permanece `is_staff=False`, `is_superuser=False` |

No frontend, o sidebar usa os booleans retornados por `/api/auth/session/`.
Hoje aparecem dashboard, receitas, despesas, custos por evento, custos fixos,
custos extras, eventos, orcamentos, servicos, configuracoes e clientes. Ficam
ocultos pagamentos, obrigacoes, FCI, FCF, credores e backups. Clientes,
servicos, orcamentos e eventos habilitam as acoes globais; nao existe flag por
registro que permita deixar apenas o seed em modo leitura. O orcamento seed
parece somente leitura apenas porque foi aprovado.

#### Aprovacao de orcamento

`approve_orcamento` e uma permissao customizada declarada em `Orcamento.Meta`
e criada pela migration `0039_orcamento_approve_permission.py`.
`can_approve_budget()` exige autenticacao, usuario ativo, schema tenant e esse
codename; nao exige `change_orcamento`, `is_staff` ou `is_superuser`. API e
acao do Django Admin chamam `aprovar_orcamento()`, e o model executa status,
evento, receita, despesas, custos e registros canonicos dentro de transacao.

Faltam controles de dominio: o service nao rejeita seed, status nao editavel
ou orcamento ja aprovado, e o model volta a salvar `aprovado` e sincroniza o
evento. A consulta ocorre no schema atual, portanto um ID de outro schema nao
e localizado no host atual; o isolamento por host/schema e a fronteira entre
tenants. A futura correcao deve manter a permissao customizada sem exigir
superusuario, mas adicionar policy de objeto, validacao de status, bloqueio de
reaprovacao e lock da linha no service transacional compartilhado pela API e
pelo Admin.

Existe conflito explicito com a nova regra: o teste
`test_reapproval_is_idempotent_for_event_and_movements` em
`caixa/test_budget_approval_tenant.py` aprova duas vezes e exige HTTP 200 sem
duplicacao. A politica solicitada exige rejeitar a segunda aprovacao. Esse
teste deve ser substituido por rejeicao deterministica e estado inalterado;
nao pode permanecer verde por compatibilidade acidental.

Decisao de escopo posterior ao diagnostico: o replace-all de filhos em
`_salvar_orcamento_from_payload()` e aceito quando o orcamento nao e seed e
esta editavel. A operacao pode apagar e recriar itens/custos extras como parte
da edicao do agregado; isso nao equivale a conceder `delete_*` nem a publicar
endpoint de exclusao autonoma. A policy deve bloquear o orcamento seed antes
do primeiro delete interno e o PUT deve exigir tambem a capacidade de alterar
itens. Exclusoes tecnicas de derivados continuam proibidas quando a raiz for
seed.

#### Estrategias avaliadas para identificar o seed

| Estrategia | Models/migration | Impacto e contorno | Reset/manutencao | Decisao |
| --- | --- | --- | --- | --- |
| `is_demo_seed` booleano | campo em `Cliente`, `Servico`, `ConfiguracaoFinanceira` e `Orcamento`; uma migration | simples e nao gravavel pela API; filhos derivam do orcamento; nao identifica o papel de cada registro e o seed continuaria dependendo de chave visivel para localizar cada raiz | reset recria marcado; baixo custo | segura, mas menos explicita |
| `demo_seed_key` estavel | campo textual interno, nulo e unico por model nos mesmos quatro roots; uma migration | identifica exatamente cada papel do seed, permite idempotencia sem usar nome/CPF/codigo/numero como autorizacao e nao deve ser exposto como writable | reset recria as chaves; manutencao simples e testavel | **recomendada** |
| registro externo | novo model tenant-scoped com content type, object ID e chave; migration | evita quatro campos, mas exige joins/consultas, limpeza de orfaos e disciplina para registrar todo derivado | recriado no reset; maior risco de dessincronizacao | descartada por complexidade |
| lista declarativa de IDs | sem migration apenas se os IDs fossem persistidos em outro lugar | IDs mudam no reset; lista em memoria ou IDs presumidos geram falso positivo/negativo | precisa ser reconstruida e equivale a um registro externo | insegura |
| `created_by` | exigiria campos nos roots e preenchimento uniforme | seed nao possui autor, roots nao possuem campo e o mesmo usuario `demo` atende todos os visitantes | reset reduz risco, mas nao identifica seed e falha em retomadas | insegura |
| identificador de lease nos objetos | migration ampla em roots e propagacao por todas as APIs | separa leases, mas adiciona estado a todo dominio e pode ser esquecido em entradas indiretas | desnecessario porque slot so volta a `livre` apos reset completo | descartada enquanto o invariante atual existir |

A chave recomendada deve existir apenas nos quatro roots. `OrcamentoItem` e
`OrcamentoCustoExtra` herdam a classificacao do orcamento; `Evento`, receitas,
despesas, custos e pagamentos derivados herdam pelo caminho
`evento -> orcamento`. Um objeto novo que apenas referencia cliente, servico
ou configuracao seed nao se torna seed: isso e necessario para o visitante
criar um orcamento editavel usando os catalogos ficticios iniciais. A API deve
expor somente `isSeed`/`isReadOnly`, nunca a chave interna.

O conjunto esperado inicial possui cinco chaves em quatro models: uma
configuracao, um cliente, dois servicos e um orcamento. Os valores devem ficar
em uma especificacao declarativa unica do seed e ser usados por criacao,
validacao de prontidao, backfill controlado e testes. O campo deve ser
`editable=False`, nulo para dados comuns e unico dentro de cada model; payload
que tente enviar a chave deve ser rejeitado ou ignorado sem altera-la.

A policy deve falhar fechada: se o usuario pertencer a `Demo Publica` e o
schema nao possuir todas as cinco chaves/relacoes esperadas, nenhuma escrita
operacional e permitida. O slot tambem nao deve ser entregue. Isso cobre a
janela entre migration e backfill/reset e impede que objetos seed legados sem
marcacao sejam tratados como dados novos mutaveis.

#### Allowlist alvo proposta

A lista abaixo e o alvo minimo para a experiencia operacional solicitada,
depois da policy de objetos e dos contratos de API ausentes. Ela preserva as
22 permissoes atuais e chega a 48 codenames explicitos:

```text
view_cliente, add_cliente, change_cliente
view_servico, add_servico, change_servico
view_configuracaofinanceira, add_configuracaofinanceira, change_configuracaofinanceira
view_orcamento, add_orcamento, change_orcamento
view_orcamentoitem, add_orcamentoitem, change_orcamentoitem
approve_orcamento
view_evento, add_evento, change_evento
view_receitaoperacional, add_receitaoperacional, change_receitaoperacional
view_despesaoperacional, add_despesaoperacional, change_despesaoperacional
view_custofixo, add_custofixo, change_custofixo
view_eventocustoservico, change_eventocustoservico
view_eventocustoextra, add_eventocustoextra, change_eventocustoextra
view_investimento, add_investimento, change_investimento
view_financiamentomovimentacao, add_financiamentomovimentacao, change_financiamentomovimentacao
view_credor, add_credor
view_dividafinanceira, add_dividafinanceira
view_parceladivida
add_pagamentoparceladivida
add_pagamentoeventocustoservico
add_pagamentoeventocustoextra
view_lancamentofinanceiro
```

Decomposicao para evitar concessao prematura:

| Parte | Quantidade | Regra |
| --- | ---: | --- |
| permissoes atuais | 22 | preservadas inicialmente, mas `add_evento` ainda nao possui POST e `view/change_orcamentoitem` nao sao exigidas separadamente |
| adicoes ja correspondentes a contratos atuais | 20 | configuracao, edicao de receita/despesa, custo fixo/extra, FCI/FCF, credor, divida, pagamentos e ledger; so entram depois da policy |
| adicoes condicionais | 6 | `add_receitaoperacional`, `add_despesaoperacional`, `change_eventocustoservico`, `change_eventocustoextra`, `view_financiamentomovimentacao`, `view_dividafinanceira`; exigem endpoint ou autorizacao semantica nova |

As 20 adicoes ligadas a contratos atuais sao:

```text
add_configuracaofinanceira, change_configuracaofinanceira
change_receitaoperacional, change_despesaoperacional
add_custofixo, change_custofixo
add_eventocustoextra
view_investimento, add_investimento, change_investimento
add_financiamentomovimentacao, change_financiamentomovimentacao
view_credor, add_credor
add_dividafinanceira, view_parceladivida
add_pagamentoparceladivida
add_pagamentoeventocustoservico
add_pagamentoeventocustoextra
view_lancamentofinanceiro
```

Essa allowlist nao deve ser copiada do perfil `Financeiro`. Codenames de
modelos canonicos internos, historicos, delete e pagamentos sem endpoint
visivel foram deliberadamente excluidos. `add_receitaoperacional`,
`add_despesaoperacional`, `add_evento` e algumas permissoes `change_*` ainda
nao possuem endpoint Next correspondente; devem ser ativados somente junto do
contrato seguro que os usa. Se esses endpoints ficarem fora do proximo escopo,
os respectivos codenames tambem ficam fora da allowlist implantada.

Antes do deploy da lista, `add_evento` deve ganhar POST seguro ou sair do
perfil, e o PUT de orcamento deve exigir `change_orcamentoitem` quando houver
mutacao de filhos. `view_financiamentomovimentacao` e
`view_dividafinanceira` somente entram se o GET composto de FCF passar a
aplica-las; conceder codename que nenhuma entrada consulta nao melhora a
seguranca nem a funcionalidade.

Continuam proibidos todos os `delete_*`, `auth.*`, `tenancy.*`,
`add/change/delete_historical*`, backup, download, restore, importacao
administrativa, schema `public`, tenant/domain e operacao global. Backups
continuam protegidos por `is_superuser`, independentemente da lista do grupo.

#### Menor patch futuro seguro

1. Adicionar `demo_seed_key` interno aos quatro models raiz e a migration
   `caixa.0042`, pequena, tenant-scoped e sem novo model.
2. Criar uma especificacao canonica com as cinco chaves/relacoes esperadas e
   validacao de prontidao; nao duplicar esses valores em policy, command e
   testes.
3. Tornar `seed_demo_tenant()` atomico, localizar roots pela chave interna e
   executar apenas na preparacao inicial, em `preparar_demo_permanente` e apos
   reset. Remover o seed de `allocate_demo_lease()`.
4. Fazer provisionamento semear/verificar antes de criar um slot `livre` novo.
   Antes de alocar ou ocupar slot existente, validar o seed completo. Slot
   inconsistente deve ser persistido como `bloqueado` sem a marcacao ser
   revertida pela mesma excecao/transacao.
5. Criar um helper/policy central de demo que reconheca membro do grupo,
   classifique roots e descendentes e rejeite mutacao indireta de seed. Aplicar
   o helper nos services canonicos de escrita e settlement, nao apenas nos
   botoes ou views.
6. Preservar o replace-all de filhos nos orcamentos nao-seed editaveis, mas
   validar a policy antes do primeiro delete e exigir
   `change_orcamentoitem` para mutacao dos filhos.
7. Serializar `isSeed` e `isReadOnly`; frontend desabilita edicao/aprovacao com
   mensagem clara, mas o backend permanece autoridade.
8. Endurecer aprovacao com `select_for_update`, status editavel, proibicao de
   reaprovacao e policy de seed, mantendo transacao e tenant scope.
9. Atualizar `PERMISSION_PROFILES['Demo Publica']` na unica fonte canonica,
   validar codenames ausentes e sincronizar exatamente a allowlist.
10. Adicionar contratos de criacao/edicao hoje inexistentes somente onde a UX
   realmente os oferecer; nao conceder permission sem entrada funcional.

Arquivos previstos no backend: `caixa/models.py`, uma nova migration de
`caixa`, `caixa/permissions.py`, um helper central de policy, views/services
de clientes, servicos, configuracoes, orcamentos/aprovacao, eventos, receitas,
despesas, custos fixos/extras e liquidacao, `caixa/views_api_auth.py`,
`tenancy/services_demo_pool.py`, commands de provisionamento/ocupacao e testes
focados. No frontend: contrato de sessao, services/serializadores das entidades,
componentes operacionais, sidebar apenas se novas capacidades forem expostas e
E2E publico. Este documento deve ser atualizado durante a futura execucao.

Migration prevista: um unico arquivo de schema com quatro campos
`demo_seed_key`, provavelmente `caixa/migrations/0042_*.py`, aplicado por
`migrate_schemas`. Nao e recomendado um `RunPython` generico: ele seria
executado em todos os tenants e poderia marcar dado comum que coincidisse com
uma chave visual. A transicao deve usar command explicito com `--dry-run`,
schema demo validado, conjunto e relacoes exatos e confirmacao forte. Esse
command importa a especificacao canonica; nao vira segunda fonte de seed.

Rollout futuro seguro: desligar novas entradas; migrar campos; publicar policy
que nega escrita em schema incompleto; fazer backfill validado de `demo1` e de
slots livres legados; deixar slots ocupados expirarem e serem resetados pelo
ciclo normal; validar as cinco chaves em cada slot; somente entao ampliar a
allowlist e reativar entrada. Se o backfill nao reconhecer exatamente um seed,
nao deve adivinhar por nome/ID: o slot fica bloqueado para reset ou revisao.

Testes futuros obrigatorios: conjunto exato/idempotente de permissoes; ausencia
de delete/admin/backup/historical; provisionamento/reset/reocupacao; flags e
grupo unico do usuario; seed visivel e imutavel por todos os endpoints e
filhos; CRUD permitido para registros do lease; aprovacao valida, transacional,
nao repetivel e tenant-scoped; pagamentos/fluxo de caixa; 403 de backups e
isolamento public/tenant; logout/retomada preservando dados; reset removendo
alteracoes e recriando as chaves originais; tentativa direta de API; E2E de
read-only do seed e edicao de registro novo.

Matriz de cobertura dos 42 cenarios solicitados (`existente` nao significa que
o teste foi executado nesta auditoria; significa apenas que foi localizado no
codigo atual):

| # | Cenario | Estado atual | Ajuste futuro |
| ---: | --- | --- | --- |
| 1 | usuario somente em `Demo Publica` | existente no fluxo de lease | manter e repetir apos sync/backfill |
| 2 | `is_staff=False` | existente | manter |
| 3 | `is_superuser=False` | existente | manter |
| 4 | grupo recebe exatamente a allowlist | ausente | comparar pares app/model/codename, quantidade e igualdade exata |
| 5 | nenhum `delete_*` | parcial: verifica apenas `delete_cliente` | verificar todo o conjunto e a ausencia de exclusao autonoma; o replace-all documentado no cenario 30 permanece permitido |
| 6 | nenhuma permissao administrativa | parcial pelas flags | verificar apps/codenames proibidos e acesso `/admin/` |
| 7 | nenhuma permissao de backup | parcial: `canManageBackups=false` e testes gerais | testar usuario demo nos tres contratos de backup |
| 8 | nenhum historical perigoso | ausente | filtrar todos os codenames historical |
| 9 | sync idempotente | parcial para grupos gerais | executar duas vezes e comparar conjunto exato da demo |
| 10 | provisionamento aplica allowlist | indireto por `post_migrate` | testar schema novo e tenant existente/slot novo |
| 11 | reset reaplica allowlist | parcial: grupo existe apos seed | comparar conjunto exato apos drop/recreate |
| 12 | reocupacao nao amplia permissoes | parcial pelo service | injetar permissao extra/direta e confirmar remocao |
| 13 | seed lista/detalhe | parcial por contagens raiz | testar respostas HTTP e flags read-only de todos os roots/derivados |
| 14 | seed nao pode ser editado | ausente | PUT direto para cada raiz/derivado deve falhar sem mutacao |
| 15 | endpoint alternativo nao altera seed | ausente | cobrir settlement, aprovacao, nested PUT, Admin service e pagamentos |
| 16 | filhos do seed protegidos | ausente | item, custo, evento, receita, despesa, obrigacao e pagamento |
| 17 | criar cliente | API geral existente; nao demo-especifica | testar como demo e banco final |
| 18 | editar cliente criado no lease | API geral existente | distinguir novo de seed |
| 19 | criar servico | API geral existente | testar como demo |
| 20 | editar servico do lease | API geral existente | distinguir novo de seed |
| 21 | criar orcamento | fluxo existente | usar roots seed como referencias sem tornar novo orcamento read-only |
| 22 | editar orcamento permitido | fluxo existente | exigir policy e status |
| 23 | criar/editar item permitido | parcial via replace-all | exigir `change_orcamentoitem`; replace-all e permitido em orcamento nao-seed |
| 24 | nao editar orcamento seed | parcial apenas pelo status aprovado | testar policy independente do status |
| 25 | aprovar orcamento permitido | existente | manter transacao e conferir derivados |
| 26 | nao aprovar seed | ausente | bloquear por policy antes de qualquer save |
| 27 | aprovacao sem superuser | existente | manter depois do endurecimento |
| 28 | aprovacao tenant-scoped | existente | manter host/schema e ID coincidente em outro tenant |
| 29 | registros financeiros necessarios | ausente para demo ampliada | testar cada origem e settlement permitido |
| 30 | nenhuma exclusao autonoma | nao ha DELETE, mas nested PUT reconcilia filhos | confirmar nenhum `delete_*`/endpoint; permitir replace-all apenas em orcamento nao-seed |
| 31 | nao listar backups | teste geral existe | repetir com usuario sincronizado da demo |
| 32 | nao criar backup | teste geral existe | repetir com demo e CSRF valido |
| 33 | nao baixar backup | isolamento/download geral existe | repetir com demo autenticado |
| 34 | nao restaurar backup | nao ha endpoint HTTP | testar ausencia de rota e manter commands fora da superficie web |
| 35 | nao acessar outro tenant | coberturas tenant gerais/aprovacao existem | repetir para objetos demo e IDs coincidentes |
| 36 | nao acessar `public` | aprovacao cobre public parcialmente | cobrir todas as escritas demo relevantes |
| 37 | logout/retomada preserva registros | lease/prazo existente; dados nao testados | criar objeto, logout/resume e conferir mesma PK/valores |
| 38 | reset remove registros do lease | parcial pelo ciclo de manutencao | criar registros em varias raizes e provar ausencia |
| 39 | reset desfaz alteracoes | ausente | alterar somente objetos permitidos e comparar estado recriado |
| 40 | reset recria seed | existente por contagens raiz | validar cinco keys e derivados completos |
| 41 | proximo visitante recebe seed intacto | parcial | completar dois visitantes separados por reset real |
| 42 | API direta nao contorna frontend | ausente | forjar IDs/payloads, inclusive `demoSeedKey`, nested e settlement |

Testes existentes que precisam ser alterados, nao apenas complementados:

- `test_seed_e_ficticio_idempotente_e_isolado` chama alocacao duas vezes e
  hoje codifica seed em retomada; deve preparar o slot antes e provar que
  alocacao/retomada nao chamam o seed;
- `test_falha_no_usuario_reverte_slot_e_seed` espera schema vazio apos falha de
  usuario; no novo ciclo o seed preexistente deve permanecer intacto e apenas
  a ocupacao deve ser revertida;
- fixtures de `DemoPublicFlowTests` e `DemoPublicConcurrencyTests` criam slots
  vazios e dependem da alocacao para semear; devem usar provisionamento que
  entrega slot pronto;
- `test_reapproval_is_idempotent_for_event_and_movements` conflita com a nova
  proibicao de reaprovacao e deve passar a exigir rejeicao sem mutacao.

Riscos restantes antes da implementacao: backfill seguro de `demo1`, garantir
que nenhum service indireto contorne a policy, contratos ausentes para criar
receitas/despesas/eventos e editar alguns cadastros financeiros, e impedir que
uma alteracao operacional manual de status libere slot sem reset. Somam-se a
janela migration/backfill, a persistencia correta de `bloqueado` fora do
rollback da alocacao e a atual ausencia de transacao propria no seed. O
replace-all de itens e risco apenas se a policy de seed for aplicada depois do
primeiro delete; em orcamento permitido ele e comportamento aceito.

Veredito desta etapa: `BLOQUEADO: NAO EXISTE DISTINCAO CONFIAVEL`.

A ampliacao apenas da allowlist nao esta autorizada. O bloqueio pode ser
removido na segunda etapa com a pequena alteracao explicita de
`demo_seed_key`, policy central e correcao do ciclo de seed descritas acima.

#### Implementacao da fundacao de protecao em 2026-07-16

Estado: `[x]` Fase 1 concluida localmente. O escopo implementado identifica e
protege o seed, sem ampliar a allowlist operacional. As 22 permissoes atuais
de `Demo Publica` foram preservadas exatamente e continuam sem qualquer
`delete_*`, permissao de backup ou permissao direta no usuario.

Estado Git confirmado antes da edicao: backend `5f90af4`, branch
`feat/django-tenants-spike`, somente este documento modificado; frontend
`a0ebb69`, branch `main`, limpo. Diagnostico confirmado: o seed atual usa
CPF/codigo/numero visiveis e ainda roda tanto na alocacao nova quanto na
retomada. Nenhuma operacao de producao foi autorizada ou executada.

Fundacao implementada:

- migration tenant-scoped unica `caixa.0042_demo_seed_keys`, sem `RunPython`,
  adiciona `demo_seed_key` textual, `NULL`, unico por model, `blank=True` e
  `editable=False` em `ConfiguracaoFinanceira`, `Cliente`, `Servico` e
  `Orcamento`; payloads e respostas nunca aceitam/expoem a chave;
- especificacao declarativa unica em `caixa/demo_seed.py`, com as chaves
  `demo.configuration.primary`, `demo.client.example`,
  `demo.service.daily`, `demo.service.hourly` e `demo.budget.example`;
- `seed_demo_tenant()` atomico, idempotente pelas chaves e executado somente em
  preparacao, provisionamento e reset; alocacao e retomada apenas validam o
  conjunto pronto e nao reescrevem valores durante o lease;
- prontidao fail-closed valida cinco roots, models, relacoes, dois itens,
  evento e derivados financeiros minimos; slot inconsistente nao e entregue
  e fica `bloqueado` mesmo se uma falha posterior provocar rollback na
  transacao de selecao;
- command `backfill_demo_seed_keys` exige schema explicito, `--dry-run` ou a
  confirmacao forte `MARCAR-SEED demoN`, rejeita `public` e rejeita `rh_teste`
  sem a opcao especifica de teste; correspondencia parcial ou ambigua nao
  grava chaves;
- policy central classifica filhos pelo caminho dirigido ao orcamento/evento
  seed. Um novo orcamento que referencia cliente, configuracao ou servicos
  seed continua comum e editavel. Escritas, nested replace-all, aprovacao,
  pagamentos e liquidacoes do seed falham antes da primeira mutacao;
- aprovacao usa `select_for_update`, aceita somente `rascunho`/`enviado`,
  rejeita seed e reaprovacao de forma deterministica e e compartilhada pela
  API e pela acao do Admin;
- APIs expoem somente `isSeed` e `isReadOnly`; o frontend mantem visualizacao,
  desabilita edicao/aprovacao do seed e mostra `Dados de exemplo - somente
  leitura`, sem impedir cadastro e edicao de objetos comuns;
- sincronizacao de grupos valida previamente todos os codenames e falha
  explicitamente se algum nao existir antes de alterar permissoes.

Validacao final desta fase: 15/15 testes dedicados da fundacao; 49/54 testes
integrados passaram na primeira bateria e os cinco restantes falharam apenas
porque seus fixtures violavam a constraint temporal do lease. A preparacao de
tempo foi corrigida e esses cinco passaram 5/5, incluindo expiracao e reset
real. O frontend passou lint, typecheck, todos os guardrails e build; o E2E
publico passou 22/22. O banco local de desenvolvimento permaneceu sem aplicar
`caixa.0040`, `0041` e `0042`; bancos efemeros de teste aplicaram todas.

Veredito da fundacao: `APROVADO PARA FASE 2`. Isso nao autoriza deploy,
migration, backfill ou reset em producao. Antes de homologar, cada schema demo
legado deve ser migrado e depois reconhecido pelo backfill exato ou recriado
por reset controlado; nunca se deve mudar um slot bloqueado diretamente para
`livre`.

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

### Disponibilidade publica e retomada explicita

Decisao: o status publico apresenta somente total configurado, vagas realmente
`livre` e o lease ativo do proprio cookie. Slots expirados aguardando reset nao
contam como disponiveis. A resposta e `no-store`, possui throttle dedicado e
nao executa operacao mutavel. A acao de continuar envia intencao explicita de
retomada ao endpoint de lease ja existente.

Razao: informar capacidade sem expor a pool, preservar a raiz como landing e
impedir que uma corrida entre status e clique transforme uma retomada expirada
em nova alocacao silenciosa.

## 4. Checklist por fase

- [x] diagnostico;
- [x] reserva permanente de `demo1` e pool publica `demo2...demo10`;
- [x] estabilizacao dos testes existentes relacionados a Fase 1;
- [x] servico de lease;
- [x] endpoint publico;
- [x] concorrencia e rollback;
- [x] autenticacao automatica;
- [x] frontend publico;
- [x] disponibilidade agregada e lease ativo na entrada publica;
- [x] permissoes minimas atuais;
- [ ] ampliacao operacional do grupo, reservada para a Fase 2;
- [x] seed atomico, prontidao fail-closed e reset validado;
- [x] identificacao e protecao read-only do seed no backend e frontend;
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
| Retomada imediata apos logout | `caixa/throttling.py`, `config/settings.py`, `tenancy/demo_visitor.py`, `tenancy/services_demo_pool.py`, `tenancy/views_demo_public.py`, testes, envs e runbook | `manage.py check`; `makemigrations --check --dry-run`; `DemoPublicFlowTests`; `DemoPublicConcurrencyTests`; `corepack pnpm run verify:frontend`; `test:e2e:public-demo` | backend 21/21 + concorrencia 3/3; frontend completo verde; E2E 15/15; mesmo tenant e expiracao, novo exchange, sem segundo slot e sem 429 da cota de novas alocacoes | nenhum commit desta solicitacao | validar Redis e Nginx reais em homologacao; Nginx ainda pode limitar rajadas abusivas antes do Django |
| Aviso transitorio no logout | seis views financeiras com handler de logout, `public-demo.spec.ts` | auditoria global de `logoutFromBackend`; eslint focado; `test:e2e:public-demo`; `verify:frontend`; `git diff --check` | 16 ocorrencias revisadas; consultas posteriores removidas de dashboard, backups, FCF, obrigacoes, FCI e custos extras; demais refetches preservados; E2E publico 16/16 e frontend completo verde | nenhum commit desta solicitacao | repetir smoke test visual depois do deploy frontend |
| Disponibilidade e lease ativo | `services_demo_pool.py`, `views_demo_public.py`, URLs, throttle/settings/envs, `features/demo-public/` e `public-demo.spec.ts` | `manage.py check`; `makemigrations --check --dry-run`; 8 testes focados; 2 testes concorrentes; `pnpm run verify:frontend`; `pnpm run test:e2e:public-demo` | check limpo; nenhuma migration; backend 8/8, concorrencia 2/2; frontend oficial verde; E2E 21/21; status nao muta lease nem revela outros slots e retomada preserva tenant/prazo | nenhum commit desta solicitacao | repetir com Redis, cookies entre hosts, timer e backend reais em homologacao |
| Diagnostico de permissoes e seed read-only, em duas passadas | grupo, seed, ciclo de lease/reset, APIs, frontend e testes existentes relacionados | duas leituras estaticas dirigidas; nenhum teste ou banco executado por restricao da etapa | 22 codenames atuais mapeados; reset garante isolamento; seed roda indevidamente em alocacao/retomada; nao existe marcador seguro; segunda passada registrou replace-all aceito, conflito do teste de reaprovacao, fixtures dependentes da alocacao e fail-closed para schemas sem as cinco chaves | backend `5f90af4`, frontend `a0ebb69`; sem commit | implementacao bloqueada ate `demo_seed_key`, policy central e correcao do ciclo de seed |
| Fundacao de protecao do seed | `caixa/models.py`, `demo_seed.py`, `demo_policy.py`, migration `0042`, views/services de escrita, commands da pool, testes, cinco services/componentes frontend | `compileall`; `manage.py check`; `makemigrations --check --dry-run`; suite dedicada; suites de pool/aprovacao; `verify:frontend`; `test:e2e:public-demo` | 15/15 dedicados; 49 testes integrados aprovados de primeira e 5/5 expiracao/reset aprovados apos corrigir fixtures temporais; lint, tipos, guardrails e build aprovados; E2E publico 22/22; exatamente 22 permissoes preservadas | sem commit; backend base `5f90af4`, frontend base `a0ebb69` | migration/backfill/reset nao executados fora dos bancos efemeros de teste; homologacao real e Fase 2 pendentes |

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
| primeira chamada da suite de retomada com janela curta | o launcher encerrou, mas deixou um runner filho migrando o banco `--keepdb`; a repeticao concorrente encontrou a coluna `origem` ja criada | encerrar somente os PIDs da suite e descartar o banco de teste parcialmente migrado | execucao unica com `--noinput` recriou apenas `test_rhsaas_dev` e passou 21/21; desenvolvimento e producao nao foram tocados |
| primeira suite agregada desta fase | o limite de 10 minutos encerrou o shell e deixou os dois processos Python do teste em execucao | nao interpretar timeout como resultado e nao iniciar runner concorrente | encerrar somente os PIDs com o comando exato, dividir evidencias e recriar apenas `test_rhsaas_dev` |
| repeticao com `--keepdb` apos a interrupcao | `demo1` residual causou `UniqueViolation` no `setUpClass` funcional, embora os tres testes transacionais tenham passado | invalidar somente a classe que nao iniciou e eliminar o banco residual | execucao funcional com `--noinput` recriou o banco e passou 8/8; concorrencia independente passou 2/2 e ambos destruíram o banco ao final |
| primeiros E2E isolados de status | servidor Next manual nao possuia `NEXT_PUBLIC_API_BASE_URL` e a propria tela informou configuracao ausente | nao alterar produto para acomodar servidor invalido | encerrar o servidor manual e deixar Playwright iniciar com o ambiente contratual |
| primeira bateria E2E completa desta fase | 18/21 passaram; duas rotas ainda compilavam alem da expectativa de 10 s e o fixture secundario esperava lease antes de cria-lo | aguardar URL/sessao com limite de compilacao, sem pausa fixa, e restaurar a sequencia real acessar/logout/continuar | tres cenarios passaram isolados e a repeticao completa passou 21/21 em 2,7 min |
| primeira repeticao da suite dedicada da fundacao | `DEBUG=release` persistido no ambiente local foi rejeitado antes de criar o banco | nao alterar `.env` nem enfraquecer a validacao de settings | repetir somente no processo com `DEBUG=True`; suite passou inicialmente 12/12 e, apos ampliar cobertura, 15/15 |
| primeira inicializacao E2E da fundacao | Playwright esgotou 120 s aguardando o webserver; o servidor manual seguinte iniciou sem `NEXT_PUBLIC_API_BASE_URL` e exibiu corretamente configuracao ausente | nao mudar o produto para acomodar ambiente invalido | iniciar o servidor de teste com as mesmas variaveis contratuais do Playwright; caso novo passou isolado e a suite oficial passou 22/22 |
| bateria backend integrada da fundacao | 49/54 passaram; cinco testes tentavam expirar o lease colocando apenas o fim antes do inicio e o PostgreSQL rejeitou a fixture pela constraint `demo_slot_lease_order` | preservar a constraint e corrigir apenas a cronologia artificial dos testes | inicio, fim e validade do exchange foram movidos coerentemente ao passado; os cinco cenarios passaram 5/5, incluindo manutencao, reset e novo seed |

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
| Nginx limita antes da aplicacao | baixa | uma rajada de varias retomadas ainda pode receber 429 HTML antes de o DRF reconhecer o lease | manter burst atual, orientar fluxo normal e validar uma retomada imediata real em homologacao; nao remover protecao de borda | residual deliberado contra abuso | caso observado chegou ao DRF; configuracao versionada usa `3r/m` com burst 2 |
| Status muda entre consulta e clique | baixa | contagem exibida pode ficar desatualizada ou a retomada pode expirar | tratar GET como informativo; POST transacional continua autoridade; retomada explicita retorna 409 e atualiza status sem alocar outro slot | mitigado no codigo | teste de `resume_unavailable` confirma zero exchange e nenhuma nova vaga |
| Ampliar allowlist sem completar a Fase 2 | critica | novos fluxos financeiros podem introduzir pontos de escrita ainda nao cobertos | manter as 22 permissoes nesta fase e auditar cada novo contrato contra a policy antes de ampliar | controlado; Fase 2 nao iniciada | marker e policy existem; teste confirma exatamente 22 codenames e nenhum `delete_*` |
| Seed executado em alocacao e retomada | alta | retomada pode sobrescrever dados durante lease ativo | preparar/resetar previamente e validar prontidao antes da entrega | mitigado no codigo | teste prova que alocacao/retomada nao chamam seed e preservam valor alterado |
| Codenames declarados inexistentes | media | grupo pode ficar incompleto apos deploy/migration divergente | validar todos antes de `group.permissions.set(...)` e falhar fechado | mitigado no codigo | teste injeta codename ausente e recebe `ImproperlyConfigured` antes da sincronizacao |
| Schema demo legado sem as cinco chaves seed | critica | dado seed sem marcador pode ser tratado como comum durante rollout | negar escrita e alocacao; backfill exato ou reset completo antes de liberar | mitigado no codigo, bloqueado operacionalmente ate tratar cada schema | teste nega PUT, bloqueia slot e preserva banco; command dry-run/backfill testado localmente |
| Seed sem transacao propria | alta | falha parcial deixa conjunto incompleto | transacao propria e validacao completa antes de retornar | mitigado no codigo | falha simulada no segundo item reverte todos os roots; suite dedicada 15/15 |
| Reaprovacao de orcamento | alta | segunda aprovacao pode alterar ou duplicar derivados | lock, status aprovavel e rejeicao deterministica antes de mutacao | mitigado no codigo | suites dedicada e de aprovacao confirmam banco inalterado apos rejeicao |

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

### Edicao agregada de orcamento

Decisao considerada durante o diagnostico: tratar qualquer remocao interna de
item ou custo extra durante um PUT de orcamento como exclusao proibida.

Decisao final: preservar o replace-all atual para um orcamento nao-seed e em
estado editavel. O backend pode apagar e recriar seus itens/custos extras como
parte da edicao do agregado, sem conceder `delete_*` e sem disponibilizar um
endpoint de exclusao autonoma. A policy de seed deve ser avaliada antes do
primeiro delete interno, e a mutacao de filhos deve exigir a capacidade
correspondente de alteracao.

Motivo: a exclusao tecnica dos filhos faz parte da forma atual de persistir a
edicao autorizada e nao representa, por si, uma acao destrutiva adicional para
o visitante. O limite de seguranca permanece na raiz seed, no estado editavel,
nas permissoes e na ausencia de operacao de exclusao independente.

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
- status publico: `GET /api/demo/status/` somente no host de entrada, esperando
  `Cache-Control: no-store`, total igual a `DEMO_PUBLIC_POOL_SLOTS` e sem nomes
  de slots quando nao houver lease proprio; monitorar 429 do escopo
  `demo_status` separadamente de lease/exchange;
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
venv/bin/python manage.py backfill_demo_seed_keys --schema=demo1 --dry-run
venv/bin/python manage.py provisionar_pool_demo --slots=10 --dry-run
venv/bin/python manage.py preparar_demo_permanente --dry-run
venv/bin/python manage.py manter_pool_demo --dry-run
```

5. Antes do provisionamento real, classificar todos os schemas demo que ja
   possuem dados. Se o conjunto legado corresponder exatamente, executar o
   backfill com a confirmacao forte individual, por exemplo
   `backfill_demo_seed_keys --schema=demo1 --confirm="MARCAR-SEED demo1"`.
   Se um slot temporario `demo2+` nao corresponder e os dados forem
   descartaveis, aguardar/encerrar o lease de forma controlada e usar
   `resetar_tenant_demo --slot=demoN --confirm="RESETAR demoN"`. Nao resetar
   `demo1` automaticamente; divergencia nele exige revisao manual. Depois de
   todos os existentes estarem prontos, executar
   `provisionar_pool_demo --slots=10` para criar/preparar somente os ausentes.
6. Se o dry-run informar `usuario_pronto=sim`, executar
   `preparar_demo_permanente` sem senha. Se informar `nao`, carregar a senha
   do secret manager em `DEMO_PERMANENT_PASSWORD`, executar com
   `--password-env=DEMO_PERMANENT_PASSWORD` e remover a variavel.
7. Instalar/recarregar as units e o Nginx conforme o runbook; validar timer,
   health, DNS e TLS, ainda com a flag desligada.
8. Homologar `?tenant=demo1`, login permanente, seed e permissoes minimas.
9. Confirmar no schema `public` que nao existe slot `demo1` e que existem
   exatamente nove slots `demo2...demo10`.
10. Ativar a flag, reiniciar a API e executar o E2E real: alocacao em `demo2+`,
   troca de token, isolamento, concorrencia, pool cheia/fallback e um ciclo
   completo de expiracao/reset pelo timer.
11. Desativar novamente a flag se qualquer gate falhar; nao liberar slot
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

## 11. Fase 2 - ampliacao operacional segura

### Diagnostico inicial (2026-07-16)

- backend: `240817c`, branch `feat/django-tenants-spike`, arvore limpa;
- frontend: `5c61344`, branch `main`, arvore limpa;
- a migration tenant-scoped `caixa.0042_demo_seed_keys` existe e a fundacao da
  Fase 1 esta aplicada aos services de configuracao, cadastros, orcamentos,
  custos, dividas, escrita canonica, obrigacoes e pagamentos;
- `PERMISSION_PROFILES["Demo Publica"]` continua sendo a unica fonte canonica
  e possui exatamente as 22 permissoes originais;
- a sincronizacao pre-valida todos os codenames, usa `permissions.set(...)`,
  remove permissoes diretas e mantem somente o grupo `Demo Publica` no usuario
  provisionado;
- existem contratos para configuracao, custos fixos/extras, alteracao de
  receitas/despesas, FCI, FCF, credores, dividas, fluxo de caixa, ledger,
  obrigacoes e liquidacoes nativas;
- `add_evento` nao possui `POST` correspondente e sera mantida somente por
  compatibilidade nesta fase; nao sera criado endpoint artificial;
- nao existe contrato de edicao de movimentacao FCF. Por isso
  `change_financiamentomovimentacao` nao sera concedida;
- a edicao de investimento comum e requisito funcional da fase. Sera criada
  somente a rota de detalhe `PUT /api/fci/<id>/`, com permissao explicita,
  lock, transacao, policy antes da mutacao e sem metodo `DELETE`;
- as seis permissoes condicionais permanecerao fora. Nenhum contrato novo sera
  criado apenas para aumentar a contagem da allowlist.

Contagem decidida: 22 atuais + 19 contratos liberados = 41 permissoes. A
divergencia em relacao as 42 inicialmente esperadas e deliberada e decorre da
ausencia de operacao segura/utilizavel para editar movimentacao FCF.

### Checklist da Fase 2

- [x] diagnostico dos commits, arvores, migration, policy, endpoints e telas;
- [x] allowlist explicita e sincronizacao do usuario demo;
- [x] policy nas novas entradas de escrita FCI/FCF/credor/divida;
- [x] contrato estreito de alteracao de investimento;
- [x] auditoria de lock, atomicidade, duplicidade e rollback de liquidacoes;
- [x] capacidades de sessao e sidebar;
- [x] testes backend dos 52 criterios aplicaveis;
- [x] testes frontend e E2E publico;
- [x] revisao de proibicoes, diff e documentacao operacional;
- [ ] homologacao (fora desta execucao);
- [ ] deploy e validacao pos-deploy (fora desta execucao).

### Matriz inicial dos contratos liberados

| Funcionalidade | Rota/metodo | Permissao de mutacao | Policy antes da escrita | Sucesso | Seed | Sem permissao |
| --- | --- | --- | --- | --- | --- | --- |
| configuracao | `POST /api/configuracoes-financeiras/`, `PUT /api/configuracoes-financeiras/<id>/` | `add/change_configuracaofinanceira` | existente | 201/200 | 403 | 403 |
| custo fixo | `POST /api/custos-fixos/`, `PUT /api/custos-fixos/<id>/` | `add/change_custofixo` | existente | 201/200 | 403 | 403 |
| custo extra | `POST /api/eventos/custos-extras/` | `add_eventocustoextra` | existente no service | 201 | 403 | 403 |
| receita/despesa | `PUT /api/receitas/<id>/`, `PUT /api/despesas/<id>/` | `change_receitaoperacional` / `change_despesaoperacional` | existente | 200 | 403 | 403 |
| FCI | `GET/POST /api/fci/`, `PUT /api/fci/<id>/` | `add/change_investimento` | aplicada ao investimento e ao evento associado antes do `save` | 200/201 | 403 | 403 |
| FCF | `GET/POST /api/fcf/`, `POST /api/fcf/debts/` | `add_financiamentomovimentacao` / `add_dividafinanceira` | aplicada ao evento antes da escrita; criacoes compostas atomicas | 200/201 | 403 | 403 |
| credor | `GET/POST /api/fcf/creditors/` | `add_credor` | prontidao fail-closed antes da criacao | 200/201 | n/a | 403 |
| fluxo/ledger/obrigacoes | rotas `GET` dedicadas | somente leitura | n/a | 200 | leitura | 403 |
| liquidacoes nativas | `POST /api/obrigacoes-financeiras/<origem>/<id>/liquidar/` | permissao explicita por origem | existente nos services | 200 | 403 | 403 |

No schema errado, a resolucao tenant-scoped e os guards existentes devem
impedir a operacao; isso sera novamente comprovado por teste. Nao ha e nao
havera endpoint `DELETE` nesta fase.

### Evidencias parciais da implementacao

- allowlist final: 41 codenames exatos, sincronizados por replace-all. O teste
  injeta permissao extra no grupo, permissao direta e o grupo `Financeiro`,
  sincroniza novamente e comprova a remocao dos tres desvios;
- FCI: criado apenas `PUT /api/fci/<id>/`, sem `DELETE`, usando a mesma
  validacao estreita do `POST`, transacao e policy no investimento e no evento;
- configuracao: a ativacao de uma configuracao comum nao pode mais desativar
  implicitamente uma configuracao seed; todas as configuracoes ativas afetadas
  sao bloqueadas e validadas antes do `update` em lote. Configuracao comum
  inativa continua podendo ser criada e editada;
- despesa derivada de seed: a policy agora e consultada antes do filtro que
  restringe a edicao a despesas manuais, garantindo `403` deterministico em
  vez de `404` quando o visitante possui `change_despesaoperacional`;
- pagamentos: os cinco fluxos nativos auditados mantem `transaction.atomic`,
  `select_for_update`, validacao de duplicidade/valor e policy antes da
  mutacao. Um teste com falha posterior simulada comprova rollback do pagamento
  e do total do custo extra;
- frontend: sessao recebe `canChangeFinancialInvestment`; FCI permite editar
  somente registro comum; obrigacoes e pagamentos ocultam a liquidacao para
  itens `isReadOnly`; sidebar continua derivada de capacidades individuais;
- `pnpm run verify:frontend`: aprovado (lint, typecheck, guardrails, snapshots,
  contratos e build de producao);
- `pnpm run test:e2e:public-demo`: 23 de 23 aprovados em um worker, incluindo
  telas operacionais, seed somente leitura, registro comum editavel, backup
  oculto, isolamento, Admin 404, logout e retomada;
- `python manage.py test tenancy.test_demo_seed_protection.DemoSeedProtectionTests
  tenancy.test_demo_public.DemoPublicFlowTests --verbosity 1`: 48 de 48
  aprovados em runner unico;
- repeticao final dos casos ampliados de configuracao e reset: 2 de 2
  aprovados; o reset removeu evento e pagamento temporarios, recriou o seed e
  liberou somente o slot correto;
- testes focados dos pagamentos nativos: 6 de 6 aprovados para parcela, custo
  de servico, custo extra, investimento, financiamento e escrita manual,
  cobrindo idempotencia/duplicidade; o teste de falha posterior e rollback
  tambem foi aprovado;
- `python manage.py check`: nenhum problema; `python manage.py makemigrations
  --check --dry-run`: nenhuma alteracao detectada;

Cobertura dos criterios obrigatorios:

- 1-12: allowlist exata, quantidade, proibicoes, perfil minimo, idempotencia e
  remocao de desvios na sincronizacao;
- 13-22: configuracao/custos/receitas/despesas comuns e bloqueio dos roots ou
  derivados seed, com verificacao de HTTP e banco;
- 23-32: leitura e escrita FCI/FCF, credor, divida, movimento, fluxo, ledger e
  obrigacoes;
- 33-40: liquidacoes nativas comuns, bloqueio seed, duplicidade e rollback;
- 41-44: escopo tenant, schema publico fail-closed, backup sem permissao e
  Admin indisponivel;
- 45-49: capacidades/sidebar, backup oculto, UI seed somente leitura, registro
  comum utilizavel e API direta protegida;
- 50-52: logout/retomada preserva os dados durante o lease; manutencao remove
  registro e pagamento temporarios; reset recria e valida o seed canonico.

### Tentativas e correcoes registradas

1. A primeira suite detectou que a nova permissao de alterar despesas fazia
   uma despesa automatica seed responder `404` antes da policy. A selecao foi
   reorganizada para identificar o objeto e responder `403` sem mutacao.
2. O primeiro guardrail do frontend recusou o novo hook de atualizacao FCI. A
   allowlist do guardrail foi ampliada somente para esse import canonico; a
   verificacao completa passou na repeticao.
3. O primeiro fixture de rollback foi rejeitado corretamente pela validacao de
   saldo antes de escrever. Foi adicionada receita comum realizada ao fixture
   para alcancar a falha posterior simulada; o teste passou e comprovou rollback
   integral.
4. `next-env.d.ts` foi alterado automaticamente pelo servidor de desenvolvimento
   e nao pertence a esta fase; deve permanecer igual ao conteudo versionado.

### Riscos e limites restantes da Fase 2

| Risco/limite | Severidade | Mitigacao/estado | Evidencia |
| --- | --- | --- | --- |
| `add_evento` continua sem `POST` utilizavel | baixa | aceito por compatibilidade; nao criar endpoint artificial | diagnostico de rotas |
| edicao de movimentacao FCF nao possui contrato | baixa | `change_financiamentomovimentacao` ficou fora | allowlist exata e teste |
| configuracao comum nao pode ser ativada enquanto isso desativaria seed | media | comportamento fail-closed; criar/editar inativa e permitido | teste de mutacao indireta |
| contratos foram validados localmente com APIs mockadas no E2E | media | repetir backend e frontend reais em homologacao | deploy permanece pendente |
| abertura publica ainda depende dos gates operacionais anteriores | alta | manter flag desligada ate homologacao, backup, TLS, pool e timer | secoes 8 a 10 |

### Conclusao da Fase 2

O patch local esta aprovado para homologacao. Nao ha migration nova, permissao
de exclusao, permissao administrativa, backup, acesso cross-tenant ou contrato
de escrita no schema `public`. Homologacao, deploy e validacao pos-deploy
permanecem deliberadamente pendentes e nao foram executados nesta fase.
