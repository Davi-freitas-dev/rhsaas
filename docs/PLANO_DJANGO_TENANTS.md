# Plano tecnico - django-tenants no RH SaaS

Status: planejamento.  
Escopo: analise tecnica e ordem de implementacao futura.  
Data: 2026-07-04.

Este documento nao implementa multi-tenant. Ele define a arquitetura futura para
o RH SaaS usando PostgreSQL schemas com `django-tenants`.

Contexto atualizado: o RH SaaS e um projeto novo, com base zerada. Ainda nao ha
banco PostgreSQL de producao nem dados reais de clientes neste projeto. O
projeto antigo pessoal permanece separado e nao sera migrado para o RH SaaS
nesta fase.

Nota de status do spike inicial em 2026-07-05: a primeira validacao tecnica ja
instalou `django-tenants`, criou o app `tenancy`, separou URLs publicas e de
tenant, configurou `TenantMainMiddleware`, `TenantSyncRouter`,
`SHARED_APPS`/`TENANT_APPS` e criou o tenant local `rh_teste` em um PostgreSQL
descartavel. O restante deste plano continua como referencia de arquitetura e
ordem de implementacao; trechos que descrevem o estado anterior ao spike devem
ser lidos como historico, nao como estado atual.

## Decisao de arquitetura

O RH SaaS usara multi-tenancy por schema PostgreSQL com `django-tenants`.

Cada cliente tera um schema proprio no mesmo banco PostgreSQL. O schema `public`
guardara dados globais da plataforma. Os dados operacionais da empresa ficarao
no schema do tenant.

Tenants serao identificados por host/subdominio:

- `empresa.rhsaas.com` identifica o tenant `empresa`.
- A tabela de dominios no schema `public` fara o mapeamento entre dominio e
  tenant.
- O desenho deve deixar espaco para dominios personalizados no futuro, como
  `app.empresa.com.br`, tambem cadastrados na tabela de dominios.

## Fontes consultadas

- Documentacao oficial de instalacao:
  https://django-tenants.readthedocs.io/en/latest/install.html
- Documentacao oficial de uso, comandos, contextos e migracoes:
  https://django-tenants.readthedocs.io/en/latest/use.html
- Documentacao oficial de arquivos tenant-aware:
  https://django-tenants.readthedocs.io/en/latest/files.html
- Documentacao oficial de testes:
  https://django-tenants.readthedocs.io/en/latest/test.html
- PyPI do pacote `django-tenants`:
  https://pypi.org/project/django-tenants/

## Estado atual do projeto

O projeto atual e uma aplicacao Django classica, ainda single-tenant.

O banco alvo da implementacao multi-tenant sera um PostgreSQL novo e vazio. O
primeiro tenant sera criado do zero, com bootstrap inicial de usuario, grupos,
permissoes e configuracoes, sem carga de dados do projeto antigo.

Fatos observados:

- `settings.py` usa `INSTALLED_APPS` unico, sem `SHARED_APPS` e `TENANT_APPS`.
- `settings.py` usa `DATABASE_URL`, com fallback local para SQLite.
- O projeto ja tem `psycopg[binary]` em `requirements.txt`.
- `django-tenants` ainda nao esta instalado.
- O projeto usa `Django==6.0.6`; o PyPI atual do `django-tenants` declara
  suporte a Django 6.0.
- `MIDDLEWARE` ainda nao tem `TenantMainMiddleware`.
- `config.urls` concentra admin, docs API e `caixa.urls`.
- O app operacional principal e `caixa`.
- Os dados operacionais ficam majoritariamente no app `caixa`.
- Muitos models operacionais possuem FK para `auth.User` em campos como
  `criado_por` e `atualizado_por`.
- O projeto usa DRF com `SessionAuthentication`, CSRF e permissao padrao
  autenticada.
- O frontend Next.js nao esta versionado neste repositorio.
- Backups atuais usam `dumpdata` global e filesystem local em
  `BASE_DIR/backups/db`.
- Nao foram encontrados `FileField`, `ImageField` ou `upload_to` ativos no app,
  mas `media/` ja e protegido no `.gitignore`.

## Compatibilidade com django-tenants

Status: compativel com ressalvas.

O projeto e conceitualmente compativel porque os dados operacionais estao
concentrados no app `caixa`. Isso facilita mover o app inteiro para
`TENANT_APPS`.

As principais ressalvas sao:

- O banco local SQLite nao serve para a arquitetura final. `django-tenants`
  exige PostgreSQL.
- A autenticacao precisa ser redesenhada para separar usuarios da plataforma e
  usuarios dos tenants.
- Os campos `criado_por` e `atualizado_por` apontam para `auth.User`; isso
  favorece colocar usuarios operacionais dentro do schema do tenant, evitando
  FK cruzada entre schemas.
- O backup atual e global e nao pode ser reaproveitado como backup de tenant sem
  adaptacao.
- Rate limits, cache, logs, permissoes e sessoes precisam incluir tenant/schema
  na estrategia.
- A configuracao de CORS atual usa allowlist exata e precisara considerar
  subdominios dinamicos com seguranca.

Nao se aplica agora:

- migracao de dados single-tenant existentes para o primeiro tenant;
- backup/restore de dados reais atuais;
- validacao de totais financeiros migrados;
- invalidacao de sessoes antigas de usuarios reais;
- janela de manutencao motivada por preservacao de dados reais existentes.

## Arquitetura recomendada

### Schemas

`public`:

- Tenant/empresa.
- Dominios.
- Usuarios da plataforma, como staff/superuser internos.
- Planos.
- Assinaturas.
- Billing.
- Configuracoes globais.
- Auditoria global da plataforma.
- Logs de provisionamento de tenants.
- Eventos de billing/webhooks.

Schema de cada tenant:

- Usuarios operacionais daquele tenant.
- Grupos e permissoes daquele tenant.
- Sessoes daquele tenant.
- Clientes.
- Eventos.
- Orcamentos.
- Receitas.
- Despesas.
- Pagamentos.
- Custos fixos.
- Custos por evento.
- Custos extras.
- Servicos.
- Credores.
- Dividas.
- Investimentos.
- Financiamentos.
- Lancamentos financeiros.
- Obrigacoes financeiras.
- Baixas financeiras.
- Configuracao financeira da empresa.
- Historicos do `simple_history` relativos aos dados operacionais.
- Demais dados operacionais do app `caixa`.

### Usuarios

Recomendacao inicial:

- Usuarios da plataforma ficam no schema `public`.
- Usuarios de clientes ficam no schema do tenant.
- Nao usar `auth.User` do schema `public` como FK direta nos dados operacionais
  do tenant.
- Nao transformar `is_superuser` do Django em "admin do cliente".
- O "admin do cliente" deve ser um papel/perfil de aplicacao dentro do tenant.
- O Django Admin deve permanecer area interna da plataforma, nao painel de
  cliente.

Essa estrategia evita FK cruzada entre schemas e combina melhor com os campos
atuais `criado_por` e `atualizado_por`.

No futuro, se for necessario que um mesmo login acesse varias empresas, criar
uma camada de identidade global e memberships por tenant, ou avaliar uma etapa
separada para `django-tenant-users`. Isso nao deve entrar na primeira migracao.

### Apps

Criar um app novo, por exemplo `tenancy`, para os models publicos:

- Tenant.
- Domain.
- Plan.
- Subscription.
- BillingCustomer.
- BillingEvent.
- GlobalSetting.
- PlatformAuditLog.

Separacao conceitual:

`SHARED_APPS`:

- `django_tenants`.
- `tenancy`.
- `django.contrib.contenttypes`.
- `django.contrib.auth`.
- `django.contrib.sessions`.
- `django.contrib.messages`.
- `django.contrib.admin`.
- `django.contrib.staticfiles`.
- apps sem tabelas que precisam estar disponiveis globalmente, como DRF e
  drf-spectacular.
- `axes`, preferencialmente com estrategia global de lockout por tenant/host.

`TENANT_APPS`:

- `django.contrib.contenttypes`.
- `django.contrib.auth`.
- `django.contrib.sessions`.
- `django.contrib.messages`.
- `django.contrib.staticfiles`.
- `caixa`.
- `simple_history`.
- apps sem tabelas usados pelas views/API do tenant, como DRF e
  drf-spectacular.

Ponto a validar em spike:

- Se `django.contrib.admin` deve entrar tambem em `TENANT_APPS`. A recomendacao
  inicial e nao expor admin para clientes, mas pode ser util em staging para
  suporte interno. Essa decisao precisa ser tomada antes da migracao.

## Mudancas por camada

### `settings.py`

Mudancas necessarias:

- Adicionar `django-tenants` em dependencias, em etapa futura.
- Trocar o backend de banco para `django_tenants.postgresql_backend`.
- Remover o fallback SQLite para ambientes multi-tenant.
- Exigir PostgreSQL em desenvolvimento, staging e producao.
- Definir `SHARED_APPS`.
- Definir `TENANT_APPS`.
- Montar `INSTALLED_APPS` a partir de `SHARED_APPS` e `TENANT_APPS`, evitando
  duplicidade.
- Definir `TENANT_MODEL`, provavelmente `tenancy.Tenant`.
- Definir `TENANT_DOMAIN_MODEL`, provavelmente `tenancy.Domain`.
- Definir `DATABASE_ROUTERS` com `TenantSyncRouter`.
- Definir `PUBLIC_SCHEMA_NAME` como `public`.
- Definir `PUBLIC_SCHEMA_URLCONF` para URLs publicas da plataforma.
- Manter `ROOT_URLCONF` para URLs de tenant ou criar URLConf tenant dedicada.
- Colocar `TenantMainMiddleware` no topo do `MIDDLEWARE`.
- Ajustar `ALLOWED_HOSTS` para aceitar o dominio raiz e subdominios do SaaS.
- Ajustar `CSRF_TRUSTED_ORIGINS` para subdominios do SaaS.
- Ajustar CORS para o modelo final de frontend.
- Definir estrategia de cookie domain, provavelmente `.rhsaas.com` nos
  subdominios oficiais.
- Definir cache Redis obrigatorio em producao.
- Revisar chaves de cache/rate limit para incluir tenant/schema.
- Adicionar filtro de logging com schema/domain do tenant.
- Planejar storage tenant-aware para media antes de qualquer upload real.

### `urls.py`

Mudancas necessarias:

- Separar URLs publicas das URLs de tenant.
- Publico:
  - Django Admin da plataforma.
  - Login/staff da plataforma, se existir.
  - Signup/trial, quando for implementado.
  - Billing/webhooks, quando for implementado.
  - Healthcheck publico.
  - Paginas institucionais, se ficarem no Django.
- Tenant:
  - Rotas atuais do app `caixa`.
  - Auth do tenant.
  - APIs operacionais.
  - Password reset tenant-aware.
  - Exportacoes tenant-aware.
- Decidir se docs OpenAPI ficam no public, no tenant, ou ambos com protecao
  staff. Recomendacao: manter docs operacionais apenas para staff interno.

### Middleware

Mudancas necessarias:

- Inserir `TenantMainMiddleware` antes de qualquer middleware que possa tocar no
  banco.
- Revisar `ConfiguredCorsMiddleware` para subdominios dinamicos.
- Garantir que CORS nao aceite qualquer origem com final parecido por erro de
  string.
- Garantir que o tenant esteja disponivel em `request.tenant`.
- Garantir que unknown host retorne 404 ou public controlado, nunca caia em um
  tenant padrao por acidente.
- Adicionar tenant/schema em logs.

### Apps

Mudancas necessarias:

- Criar app `tenancy`.
- Registrar models publicos no `tenancy`.
- Mover o app `caixa` para `TENANT_APPS`.
- Garantir que `caixa` nao seja migrado no schema `public`.
- Garantir que apps globais como billing nao sejam migrados dentro dos tenants.
- Revisar `AppConfig.ready()` e signals para evitar execucao indevida no schema
  errado.

### Models

Mudancas necessarias:

- Criar `Tenant` herdando de `TenantMixin`.
- Criar `Domain` herdando de `DomainMixin`.
- Adicionar campos de status ao tenant:
  - nome.
  - slug.
  - status: provisioning, active, suspended, deleting, deleted.
  - trial flags.
  - plano atual.
  - datas de criacao/ativacao/suspensao.
  - billing IDs.
  - limites basicos.
- Definir validacao forte para `schema_name`.
- Separar `schema_name` de `domain`. Schema pode usar underscore; dominio nao.
- Manter todos os models operacionais do `caixa` no schema do tenant.
- Nao adicionar `tenant_id` em todos os models operacionais nesta arquitetura;
  o isolamento primario sera por schema.

### Autenticacao

Mudancas necessarias:

- Separar login publico/plataforma de login de tenant.
- Login de tenant deve ocorrer no dominio do tenant.
- Password reset precisa gerar links no dominio do tenant.
- E-mails de reset devem carregar contexto de tenant.
- Sessoes devem ser tenant-local ou ter chave que inclua tenant.
- Nao permitir que sessao valida de um tenant autentique outro tenant.
- Definir claramente como staff da plataforma acessa suporte:
  - criar usuario de suporte dentro do tenant; ou
  - fluxo de impersonation auditado, apenas depois.

### Permissoes

Mudancas necessarias:

- Rodar sincronizacao de grupos/permissoes por tenant.
- Criar perfis padrao dentro de cada novo tenant.
- Separar permissoes de plataforma de permissoes operacionais.
- Trocar usos funcionais de `is_superuser` por permissoes de aplicacao quando a
  acao for do cliente.
- Manter `is_superuser` apenas para operadores internos da plataforma.
- Revisar `canManageBackups`: backup global nao deve aparecer para admin de
  cliente.
- Criar permissao futura para exportacao tenant-scoped, se necessario.

### APIs DRF

Mudancas necessarias:

- Todas as APIs operacionais devem depender do tenant resolvido por host.
- Nenhuma API deve confiar em `tenant_id`, `schema_name` ou slug vindo do corpo
  da requisicao.
- Endpoints `AllowAny` com checagem manual precisam de revisao extra para
  garantir que rodam no schema correto.
- Throttles devem incluir tenant/schema na chave de cache.
- Logs de 401/403/429 devem incluir tenant/schema.
- OpenAPI deve documentar que as rotas operacionais sao tenant-scoped por host.
- Testes de API devem usar `TenantClient` ou cliente equivalente.

### Frontend Next.js

O frontend nao esta neste repositorio, mas precisara seguir estas regras:

- O tenant deve ser identificado pelo host.
- O frontend deve rodar em `empresa.rhsaas.com` ou fazer proxy/API no mesmo
  host do tenant.
- A aplicacao nao deve enviar tenant como dado confiavel no body/query.
- Links de login, logout e reset devem preservar o dominio do tenant.
- Troca de tenant deve ser troca de host, nao apenas troca de estado em memoria.
- Para dominio personalizado futuro, o frontend deve funcionar com host
  arbitrario cadastrado em `Domain`.
- Preferir chamadas same-origin para reduzir complexidade de CORS e cookies.
- Se houver frontend separado em `app.rhsaas.com`, sera preciso desenhar uma
  estrategia explicita para encaminhar a chamada ao backend do tenant correto.

## Dados por schema

### Public

Devem permanecer no schema `public`:

- Tenant/empresa.
- Dominios.
- Usuarios da plataforma, staff e superuser internos.
- Planos.
- Assinaturas.
- Billing.
- Configuracoes globais.
- Auditoria global.
- Eventos de webhook.
- Logs de provisionamento.
- Feature flags globais.
- Integracoes globais de pagamento/e-mail.

### Tenant

Devem ficar dentro do schema de cada tenant:

- Usuarios operacionais do tenant.
- Grupos e permissoes do tenant.
- Clientes.
- Eventos.
- Orcamentos.
- OrcamentoItem.
- Receitas.
- Despesas.
- Pagamentos.
- Custos fixos.
- Custos de servico.
- Custos extras.
- Servicos.
- Credores.
- Dividas.
- Parcelas.
- Investimentos.
- Financiamentos.
- Lancamentos financeiros.
- Obrigacoes financeiras.
- Baixas financeiras.
- Configuracoes financeiras da empresa.
- Historicos de alteracao.
- Sessoes do tenant.
- Qualquer dado operacional visivel pelo cliente.

## Fluxos operacionais

### Criacao de novo tenant

Fluxo recomendado:

1. Operador ou fluxo de trial cria registro `Tenant` no schema `public`.
2. Validar nome, slug, schema_name e dominio.
3. Criar tenant com status `provisioning`.
4. Criar dominio primario, como `empresa.rhsaas.com`.
5. Criar schema PostgreSQL do tenant.
6. Aplicar migrations de `TENANT_APPS` no schema criado.
7. Entrar no contexto do tenant.
8. Criar grupos/perfis padrao.
9. Criar usuario admin inicial do tenant.
10. Criar configuracoes financeiras iniciais.
11. Executar healthcheck interno do tenant.
12. Marcar tenant como `active`.
13. Enviar e-mail de boas-vindas ou convite.

Sobre `auto_create_schema`:

- A biblioteca permite criar/sincronizar schema ao salvar o tenant.
- Para producao SaaS, o mais seguro e controlar o provisionamento em um servico
  transacional/assinado por status.
- A criacao pode ser "automatica" do ponto de vista do produto, mas nao deve ser
  um efeito colateral invisivel sem logs, lock e tratamento de erro.

### Aplicacao de migrations no novo schema

Regras:

- Usar comandos/fluxos do `django-tenants`, nao `manage.py migrate` comum sem
  entender o impacto.
- Migracoes publicas rodam somente para `SHARED_APPS`.
- Migracoes tenant rodam somente para `TENANT_APPS`.
- O provisionamento deve falhar de forma limpa se qualquer migration falhar.
- O tenant nao deve ficar `active` antes das migrations e bootstrap terminarem.
- Registrar versao de codigo e migration state usada no provisionamento.

### Exclusao de tenant

Fluxo recomendado:

1. Suspender tenant primeiro.
2. Bloquear login e APIs.
3. Gerar backup/exportacao final.
4. Desativar dominios.
5. Aguardar periodo de retencao.
6. Executar exclusao destrutiva do schema apenas com confirmacao explicita.
7. Manter registro publico minimo para auditoria/billing.

Importante:

- O comando de exclusao de tenant pode apagar schema PostgreSQL de forma
  irreversivel.
- Nao criar exclusao self-service na primeira fase.
- Preferir soft delete operacional antes de qualquer drop schema.

### Backups por tenant

Politica:

- Backup global da plataforma continua restrito ao operador interno.
- Admin de cliente nao baixa backup global.
- Backup/exportacao de cliente deve ser tenant-scoped.

Opcoes tecnicas:

- Backup por schema com `pg_dump` limitado ao schema do tenant.
- Exportacao por `dumpdata` executada dentro de `tenant_context`.
- Exportacao funcional por endpoints especificos, quando o produto pedir.

Recomendacao inicial:

- Para recuperacao operacional, usar backup por schema PostgreSQL.
- Para cliente, oferecer exportacoes controladas de dados, nao dump completo do
  banco.
- Salvar arquivos em `backups/tenants/<schema_name>/`.
- Incluir metadata com tenant, schema, dominio, data, versao do codigo e hash.
- Criar rate limit e audit log para downloads/exportacoes.

## Identificacao do tenant

### Subdominio

Modelo principal:

- `empresa.rhsaas.com` aponta para o mesmo backend.
- `Domain.domain` guarda `empresa.rhsaas.com`.
- Middleware resolve o tenant pelo host.
- O schema ativo passa a ser o schema do tenant.

Cuidados:

- `schema_name` e dominio nao devem ser tratados como a mesma string.
- Slug publico, dominio e schema_name precisam de validacoes separadas.
- Unknown host deve resultar em 404 ou public controlado.

### Dominio personalizado futuro

Preparar desde o comeco:

- `Domain` deve aceitar mais de um dominio por tenant.
- `Domain` deve ter `is_primary`.
- Adicionar status de verificacao, como pending, verified, disabled.
- Adicionar campos futuros para certificado/TLS se necessario.
- O tenant deve continuar sendo resolvido por tabela, nao por parse fixo de
  subdominio.

Nao implementar automacao de dominio personalizado na primeira fase.

## Adaptacoes especificas

### Permissoes

- Perfis atuais `Administrador`, `Financeiro` e `Operacional` devem ser criados
  dentro de cada tenant.
- Permissoes devem ser tenant-local.
- Acoes de plataforma exigem usuario do public.
- Acoes operacionais exigem usuario do tenant.
- Remover dependencia funcional de `is_superuser` para recursos de cliente.

### Autenticacao

- Login da plataforma: public.
- Login do cliente: tenant.
- Reset de senha: tenant-aware.
- Sessao: tenant-local.
- Rate limit de auth: chave deve incluir tenant/domain.

### Backup

- Backup global: plataforma.
- Backup por tenant: schema especifico.
- Exportacao de cliente: dados do tenant, com auditoria.
- Download: rate limit especifico e permissao explicita.

### Exportacoes

- Todas as exportacoes atuais devem rodar no schema ativo do tenant.
- Nome de arquivo deve incluir tenant/schema.
- Exportacoes nao devem aceitar tenant vindo do request body.
- Exportacoes administrativas globais devem ficar no public e separadas.

### Uploads/media

- Hoje nao ha `FileField`/`ImageField` operacional detectado.
- Antes de adicionar uploads reais, configurar storage tenant-aware.
- Estrutura recomendada: `media/tenants/<schema_name>/...`.
- Custom domains nao devem alterar o path fisico dos arquivos.
- Validar permissao de leitura por tenant antes de servir qualquer media
  privada.

### APIs

- Host resolve tenant.
- Querysets continuam sem `tenant_id`, porque o schema isola os dados.
- Cache keys, throttle keys e logs devem incluir schema.
- APIs publicas futuras devem ter token/scopes por tenant.
- Webhooks de billing ficam no public.

## Riscos da migracao

### Alto

- Rodar `migrate` comum em vez de `migrate_schemas` depois da conversao.
- Colocar `caixa` em `SHARED_APPS` por engano e criar dados operacionais no
  `public`.
- Manter backup global acessivel a admin de cliente.
- Misturar usuario public com dados operacionais tenant por FK cruzada.
- Sessao/cookie autenticar usuario no tenant errado.
- Rate limit por user id colidir entre tenants.

### Medio

- Provisionamento de tenant ficar parcialmente criado apos erro de migration.
- Testes locais dependerem de SQLite e deixarem de representar producao.
- CORS/CSRF quebrar em subdominios dinamicos.
- Password reset gerar link para dominio errado.
- Comandos de manutencao rodarem em todos os tenants sem querer.
- `django-axes` bloquear usuarios de tenants diferentes se a chave nao incluir
  tenant/domain.
- Migrations do app `caixa` ficarem lentas para muitos tenants.

### Baixo

- OpenAPI mostrar nome/host generico.
- Logs sem tenant dificultarem suporte.
- `collectstatic` e assets tenant-aware serem mais complexos do que o necessario
  se nao houver customizacao visual por tenant.

## Testes obrigatorios

### Resolucao de tenant

- Host `empresa-a.rhsaas.com` ativa schema A.
- Host `empresa-b.rhsaas.com` ativa schema B.
- Host desconhecido retorna 404 ou public controlado.
- Dominio primario resolve corretamente.
- Dominio customizado futuro pode ser testado com fixture, mesmo sem automacao
  TLS.

### Isolamento de dados

- Criar Cliente com mesmo nome em dois tenants e garantir que cada API lista
  apenas o seu.
- Repetir para Eventos, Orcamentos, Receitas, Despesas, Pagamentos, Custos,
  Servicos e Lancamentos.
- Criar registros com mesmo PK em tenants diferentes e garantir que detalhe por
  ID nao cruza dados.
- Dashboard financeiro nao soma dados de outro tenant.
- Mes financeiro nao le obrigacoes de outro tenant.

### Autenticacao

- Usuario do tenant A nao autentica no tenant B.
- Mesmo username pode existir em tenants diferentes sem conflito.
- Sessao criada no tenant A nao autentica tenant B.
- Password reset no tenant A gera link do dominio A.
- Usuario public staff nao acessa dados de tenant sem fluxo explicito.

### Permissoes

- Perfis padrao existem em tenant novo.
- Admin de cliente tem permissoes operacionais esperadas.
- Admin de cliente nao acessa backup global.
- Usuario financeiro nao acessa telas fora do perfil.
- Permissoes de um tenant nao alteram permissoes de outro.

### APIs DRF

- Cada endpoint operacional principal deve ter teste de isolamento entre dois
  tenants.
- Endpoints `AllowAny` com checagem manual devem respeitar tenant.
- Throttle de login/API deve separar tenant A e tenant B.
- API sem tenant valido nao deve responder dados operacionais.

### Backups e exportacoes

- Backup por tenant gera arquivo apenas com dados do tenant.
- Download de backup/exportacao exige permissao correta.
- Tenant A nao baixa arquivo do tenant B.
- Nome e path de backup bloqueiam path traversal.
- Backup global nao aparece em tenant.

### Media/uploads

- Arquivo do tenant A salva em path do tenant A.
- Tenant B nao acessa arquivo do tenant A.
- Path nao depende do dominio customizado.

### Migrations/provisionamento

- Criar tenant novo cria schema.
- Migrations do tenant rodam no schema criado.
- Bootstrap cria usuario admin inicial e grupos.
- Falha de bootstrap deixa tenant em `provisioning_failed` ou status
  equivalente.
- Exclusao suspende antes de apagar.

### Comandos de manutencao

- Comando tenant-specific roda apenas no schema indicado.
- Comando all-tenants registra cada schema processado.
- Comando de backup nao roda global por acidente.

## Ordem de implementacao

### Etapa 0 - Preparacao obrigatoria

Objetivo: reduzir risco antes da primeira migration.

Tarefas:

- Garantir que o codigo atual esteja versionado antes da branch multi-tenant.
- Evitar mudancas funcionais paralelas durante a implementacao da arquitetura.
- Criar banco PostgreSQL novo e vazio para desenvolvimento/staging.
- Confirmar versao exata do `django-tenants`.
- Confirmar compatibilidade com `Django==6.0.6`.
- Definir dominio base do SaaS.
- Definir o primeiro tenant a ser criado do zero.
- Definir schema_name do primeiro tenant.
- Definir estrategia de usuarios: public staff e tenant users separados.
- Definir o app `tenancy`.
- Fechar matriz `SHARED_APPS`/`TENANT_APPS`.
- Fechar plano de rollback.
- Confirmar explicitamente que o projeto antigo pessoal fica fora do escopo e
  nao sera migrado nesta fase.

Risco: baixo se for apenas preparacao em banco novo e vazio; medio se houver
mudancas funcionais concorrentes.

### Etapa 1 - Spike tecnico em branch

Objetivo: provar o esqueleto com banco vazio.

Tarefas:

- Instalar `django-tenants` na branch.
- Criar app `tenancy`.
- Configurar settings multi-tenant.
- Criar Tenant e Domain.
- Subir PostgreSQL local/staging.
- Rodar migrations em banco vazio.
- Criar public tenant.
- Criar um tenant de teste.
- Acessar rota simples tenant.

Risco: medio. Pode revelar incompatibilidades de settings, middleware e app
split.

### Etapa 2 - Separar public URLs e tenant URLs

Objetivo: impedir mistura de plataforma e app operacional.

Tarefas:

- Criar URLConf public.
- Criar ou adaptar URLConf tenant.
- Manter admin no public.
- Manter rotas operacionais no tenant.
- Definir comportamento para host desconhecido.

Risco: medio. Quebras de login, admin e docs API sao provaveis.

### Etapa 3 - Autenticacao tenant-local

Objetivo: fazer login e permissao funcionarem por schema.

Tarefas:

- Confirmar `auth`, `contenttypes` e `sessions` nos tenants.
- Criar usuario admin inicial do tenant.
- Criar grupos/perfis por tenant.
- Adaptar reset de senha para dominio do tenant.
- Testar mesma credencial/nome em tenants diferentes.

Risco: alto. Autenticacao e permissoes sao o ponto mais delicado.

### Etapa 4 - Rodar app `caixa` como tenant app

Objetivo: fazer operacao atual funcionar dentro de um schema tenant.

Tarefas:

- Garantir que `caixa` nao migra no public.
- Migrar `caixa` no tenant.
- Rodar testes principais dentro de um tenant.
- Corrigir acessos que assumem schema global.
- Validar dashboard, cadastros, financeiro e pagamentos.

Risco: alto. O app e grande e tem muitas migrations.

### Etapa 5 - Bootstrap do primeiro tenant zerado

Objetivo: criar o primeiro tenant do RH SaaS do zero, sem migrar dados do
projeto antigo.

Tarefas:

- Criar tenant inicial no schema `public`.
- Criar dominio/subdominio do tenant.
- Criar schema PostgreSQL do tenant.
- Aplicar migrations do tenant em banco vazio.
- Criar usuario admin inicial do tenant.
- Criar grupos/perfis padrao.
- Criar configuracoes iniciais minimas.
- Validar login, dashboard vazio, cadastros vazios e APIs principais sem dados.
- Confirmar que nenhum dado do projeto antigo foi carregado.

Risco: medio. O risco principal nao e perda de dados, e sim bootstrap incompleto
ou schema/app split incorreto.

### Etapa 6 - Backups, exportacoes e media

Objetivo: impedir vazamento operacional entre tenants.

Tarefas:

- Substituir backup global exposto por backup/exportacao tenant-scoped.
- Criar paths por schema.
- Adicionar audit log.
- Adicionar rate limit por tenant.
- Preparar storage de media tenant-aware antes de uploads reais.

Risco: medio/alto. Backup errado e vazamento de dados.

### Etapa 7 - Testes de isolamento

Objetivo: travar regressao antes de qualquer deploy.

Tarefas:

- Criar base de testes com dois tenants.
- Cobrir endpoints principais.
- Cobrir auth, permissoes, backup/exportacao e media.
- Cobrir comandos de manutencao.
- Rodar suite em PostgreSQL.

Risco: medio. Testes podem ficar lentos; usar estrategia de fixture/fast tenant
com cuidado.

### Etapa 8 - Staging completo

Objetivo: simular producao.

Tarefas:

- DNS/subdominios reais de staging.
- HTTPS.
- Redis.
- PostgreSQL.
- Background jobs, se existirem.
- Backups.
- Logs com tenant.
- Testes manuais por tenant.

Risco: medio. Problemas de dominio, CORS, CSRF e cookies aparecem aqui.

### Etapa 9 - Producao controlada

Objetivo: ativar com um tenant inicial.

Tarefas:

- Confirmar codigo versionado e rollback de deploy.
- Usar banco PostgreSQL de producao novo e vazio.
- Deploy sem migrations automaticas destrutivas.
- Migracoes controladas.
- Criacao do primeiro tenant do zero.
- Validacao do tenant inicial sem dados legados.
- Monitoramento.
- Plano de rollback.

Risco: medio/alto. Nao ha janela de manutencao por dados reais existentes, mas
a ativacao ainda exige rollback de codigo/configuracao e validacao cuidadosa de
migrations.

## Arquivos provavelmente alterados

Arquivos de configuracao:

- `requirements.txt`.
- `.env.example`.
- `.env.production.example`.
- `config/settings.py`.
- `config/urls.py`.
- novo `config/public_urls.py`.
- possivel novo `config/tenant_urls.py`.
- `config/wsgi.py`.
- `config/asgi.py`.

Novo app:

- `tenancy/apps.py`.
- `tenancy/models.py`.
- `tenancy/admin.py`.
- `tenancy/services.py`.
- `tenancy/permissions.py`, se necessario.
- `tenancy/tests.py`.
- `tenancy/migrations/*`.

App operacional:

- `caixa/permissions.py`.
- `caixa/views_api_auth.py`.
- `caixa/views_auth.py`.
- `caixa/views_backups.py`.
- `caixa/services_backups.py`.
- `caixa/selectors_backups.py`.
- `caixa/throttling.py`.
- `caixa/middleware.py`.
- `caixa/tests.py`.
- management commands em `caixa/management/commands/*`.

Documentacao:

- `README.md`.
- `docs/MAPA_SEGURANCA.md`.
- `docs/AUDITORIA_SEGURANCA_RH_SAAS.md`.
- este plano.
- futuro runbook de provisionamento tenant.
- futuro runbook de backup/restore tenant.

Frontend, em repositorio separado:

- config de dominios/subdominios.
- camada de API client.
- fluxo de login/logout/reset.
- leitura do host atual.
- links entre public e tenant.
- telas de admin de cliente.

## Checklist tecnico completo

### Antes de codar

- [ ] Confirmar banco PostgreSQL para dev/staging/prod.
- [ ] Confirmar pacote `django-tenants` e versao.
- [ ] Confirmar dominio base do SaaS.
- [ ] Definir schema_name do primeiro tenant.
- [ ] Definir separacao public/tenant de auth.
- [ ] Definir `SHARED_APPS`.
- [ ] Definir `TENANT_APPS`.
- [ ] Definir URLConf public.
- [ ] Definir URLConf tenant.
- [ ] Definir estrategia de backup.
- [ ] Definir estrategia de rollback.

### Configuracao

- [ ] Backend PostgreSQL do `django-tenants`.
- [ ] `TenantMainMiddleware` no topo.
- [ ] `TenantSyncRouter`.
- [ ] `TENANT_MODEL`.
- [ ] `TENANT_DOMAIN_MODEL`.
- [ ] `PUBLIC_SCHEMA_URLCONF`.
- [ ] Redis obrigatorio em producao.
- [ ] Cookies subdominio.
- [ ] CSRF trusted origins para subdominios.
- [ ] CORS seguro para frontend.
- [ ] Logs com tenant/schema.

### Public schema

- [ ] Tenant model.
- [ ] Domain model.
- [ ] Plans.
- [ ] Subscriptions.
- [ ] Billing.
- [ ] Platform users.
- [ ] Platform admin.
- [ ] Global settings.
- [ ] Provisioning logs.

### Tenant schema

- [ ] `caixa`.
- [ ] Tenant users.
- [ ] Tenant groups.
- [ ] Tenant permissions.
- [ ] Tenant sessions.
- [ ] Operational data.
- [ ] Historical data.
- [ ] Tenant bootstrap.

### Seguranca

- [ ] Admin Django apenas public/internal.
- [ ] Admin de cliente via app, nao Django Admin.
- [ ] Backup global bloqueado para cliente.
- [ ] Exportacao tenant-scoped.
- [ ] Rate limit por tenant.
- [ ] Logs sem dados sensiveis.
- [ ] Auditoria para export/download.
- [ ] Password reset tenant-aware.

### Testes

- [ ] Tenant resolution.
- [ ] Auth isolation.
- [ ] Data isolation.
- [ ] Permission isolation.
- [ ] API isolation.
- [ ] Backup/export isolation.
- [ ] Media isolation.
- [ ] Provisioning.
- [ ] Delete/suspend tenant.
- [ ] Management commands.

## O que preparar antes da primeira migration django-tenants

Obrigatorio:

- Codigo atual versionado antes da branch.
- Banco PostgreSQL novo e vazio para experimento.
- Branch exclusiva para multi-tenant.
- Versao exata do `django-tenants` escolhida.
- Confirmacao de compatibilidade com Django 6.0.6.
- Matriz final `SHARED_APPS`/`TENANT_APPS`.
- Decisao final sobre auth public vs tenant.
- Nome do app public `tenancy`.
- Nome do primeiro tenant.
- `schema_name` do primeiro tenant.
- Dominio/subdominio do primeiro tenant.
- Runbook de comandos permitidos.
- Regra clara: apos conversao, usar `migrate_schemas` nos fluxos de tenant.
- Plano de bootstrap do primeiro tenant zerado.
- Plano para bloquear backup global no tenant.
- Confirmacao explicita de que o projeto antigo pessoal fica separado e nao
  sera migrado nesta fase.

Nao iniciar migration sem isso.

Nao aplicavel agora:

- backup de dados reais atuais;
- restore de dados reais atuais;
- migracao de dados single-tenant;
- carga de dados operacionais existentes;
- validacao de totais financeiros migrados;
- invalidacao de sessoes antigas;
- janela de manutencao por dados reais existentes.

## O que NAO deve ser implementado ainda

- Billing completo.
- Trial self-service.
- Planos com enforcement automatico.
- Dominio personalizado automatico.
- Impersonation de suporte.
- API publica com tokens.
- WebSocket/notificacoes.
- Automacoes n8n.
- Uploads reais de usuario.
- Tenant marketplace.
- Exclusao self-service de tenant.
- Migracao para `django-tenant-users`.
- Otimizacoes prematuras para centenas de tenants.
- Customizacao visual por tenant.
- Multi-regiao.

## Conclusao

A melhor rota e migrar em fases, primeiro provando `django-tenants` com banco
PostgreSQL vazio, depois separando public/tenant, depois autenticação e somente
entao criando o primeiro tenant do zero.

O maior cuidado tecnico sera separar corretamente usuarios da plataforma e
usuarios de tenant. O segundo maior sera garantir que backups, exportacoes,
rate limits e testes de API nunca cruzem dados entre schemas.

O projeto atual esta bem posicionado para essa mudanca porque o app operacional
esta concentrado em `caixa`, mas a migracao deve ser tratada como mudanca de
arquitetura central, nao como simples instalacao de biblioteca.

Como o RH SaaS nasce com base zerada, a primeira implementacao nao precisa
preservar ou migrar dados do projeto antigo. O foco passa a ser criar uma
fundacao multi-tenant correta desde o primeiro schema.
