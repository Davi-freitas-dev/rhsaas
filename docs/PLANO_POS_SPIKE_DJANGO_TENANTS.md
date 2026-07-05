# Plano pos-spike - django-tenants no RH SaaS

Status: planejamento pos-spike.  
Escopo: melhorias pequenas e medias para transformar o spike tecnico em base
segura de desenvolvimento multi-tenant.  
Data: 2026-07-05.

Este documento nao implementa codigo, nao instala bibliotecas e nao executa
migrations. Ele registra as pendencias de seguranca, isolamento e operacao que
devem ser tratadas depois do spike inicial com `django-tenants`.

## Objetivo

Garantir que a evolucao multi-tenant avance com uma regra central:

> Um tenant jamais pode acessar dados de outro tenant, nem por API, sessao,
> ID conhecido, permissao, exportacao, backup, upload, cache ou troca de host.

## Riscos altos que bloqueiam producao

Estes itens devem ser tratados como bloqueadores, nao como melhorias opcionais:

- isolamento entre tenants sem testes automatizados com dois tenants;
- backup global acessivel, direta ou indiretamente, a administrador de cliente;
- exportacao de dados sem prova de escopo pelo schema ativo;
- sessao ou cookie reutilizavel entre tenants por configuracao de dominio
  compartilhado;
- API nova sem permissao explicita ou sem teste de acesso negado;
- `/admin/` exposto com models globais e operacionais no mesmo `admin.site`;
- uploads ou downloads sem caminho/permite de leitura tenant-aware.

Regra de aceite:

- nenhum item acima pode estar aberto antes de producao real;
- backup/export e testes de isolamento tambem bloqueiam qualquer deploy com
  clientes reais;
- endpoint novo que manipule dado operacional precisa nascer com teste de
  isolamento por host/schema.

## Obrigatorio antes de continuar multi-tenant

### 1. Testes automatizados com dois tenants

Criar uma suite minima com dois tenants reais no banco de teste, por exemplo:

- `tenant_a.localhost`.
- `tenant_b.localhost`.

Cobrir:

- isolamento por API;
- isolamento de sessao;
- IDs iguais em tenants diferentes;
- permissoes independentes por tenant;
- exportacoes rodando apenas no schema ativo;
- backups/downloads sem vazamento entre tenants;
- querysets sempre resolvidos no schema ativo;
- usuario autenticado em um tenant nao autenticado automaticamente em outro;
- host conhecido resolve para o schema correto;
- host desconhecido falha fechado;
- `public` nao possui tabelas `caixa_*`;
- `public` nao possui grupos operacionais;
- grupos operacionais existem apenas nos schemas de tenant.

Casos obrigatorios:

- criar Cliente/Evento/Receita/Despesa com mesmo `id` em dois tenants e
  confirmar que a API de um tenant nao retorna dado do outro;
- forcar URL com `pk` existente em outro tenant e confirmar `404` ou resposta
  vazia segura;
- trocar apenas o `Host` da request e confirmar mudanca de schema;
- usar cookie de sessao de um tenant contra outro host e confirmar que nao ha
  autenticacao cruzada.
- solicitar exportacao em um tenant e confirmar que dados do outro tenant nao
  aparecem no arquivo;
- tentar acessar backup global como admin de cliente e confirmar bloqueio;
- criar usuario com mesmo username em tenants diferentes e confirmar que login
  e permissao sao resolvidos no schema correto.

### 2. Metadata do app caixa no schema public

O spike confirmou que `public` nao possui tabelas `caixa_*`, mas Django ainda
pode criar `django_content_type` e `auth_permission` de apps tenant no schema
`public`.

Esse ponto deve ser investigado e decidido antes de endurecer a arquitetura.

Opcoes aceitaveis:

- aceitar como ruido tecnico documentado, desde que nao existam tabelas,
  grupos, usuarios operacionais ou dados do app `caixa` no `public`;
- ou ajustar configuracao/fluxo de migrations para reduzir essa metadata no
  `public`, se houver caminho seguro e suportado pelo `django-tenants`.

Testes obrigatorios:

- `public` sem tabelas `caixa_*`;
- `public` sem grupos `Administrador`, `Financeiro` e `Operacional`;
- nenhuma permissao de `caixa` concedida a usuario/staff de plataforma;
- comandos de provisionamento nao dependem de permissoes operacionais no
  `public`.

### 3. Permissoes DRF

Reduzir a dependencia de `AllowAny` com checagens manuais dentro das views.

Direcao recomendada:

- criar classes de permissao DRF explicitas para autenticacao e permissoes
  Django;
- padronizar respostas `401` e `403`;
- manter compatibilidade de payloads existentes;
- migrar endpoint por endpoint, com testes focados;
- impedir que novas APIs entrem sem permissao declarada.
- criar teste/guardrail que liste APIs com `AllowAny` e exija justificativa ou
  decorator de permissao equivalente;
- revisar endpoints de escrita antes dos endpoints apenas leitura.

Primeiro alvo seguro:

- criar testes de regressao para endpoints existentes antes de alterar as
  decorators;
- depois migrar uma API simples de leitura como prova de padrao.

### 4. Frontend por host/subdominio

Validar o comportamento esperado do frontend com tenants por subdominio.

Pontos obrigatorios:

- chamadas API usando o host do tenant ativo;
- cookies host-only, sem `SESSION_COOKIE_DOMAIN` ou `CSRF_COOKIE_DOMAIN`
  compartilhado;
- `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS` compatibilizados com o
  modelo final;
- respostas de autenticacao e dados sensiveis com cache `no-store`;
- troca de tenant feita por host/subdominio, nao por parametro manipulavel;
- nenhum identificador de tenant confiado ao cliente.
- nenhum token de sessao, CSRF ou dado sensivel em `localStorage`;
- service worker/cache separados por host e sem reaproveitar payload financeiro
  entre tenants;
- logout e reset de senha sempre operando no tenant do host atual.

## Obrigatorio antes de deploy

### 5. Backup/export tenant-scoped

O backup global nao pode ser disponibilizado para administrador de cliente.

Regras:

- backup global continua restrito ao operador da plataforma;
- admin de cliente nao baixa dump global;
- admin de cliente nao ve botao, rota ou permissao de backup global;
- exportacao de cliente deve ser tenant-scoped;
- download precisa registrar auditoria;
- toda exportacao deve rodar no schema ativo;
- qualquer endpoint de backup/export deve ter teste com dois tenants.
- arquivos de exportacao devem ter path ou prefixo por tenant;
- nomes de arquivo nao devem permitir inferir outro tenant;
- falhas de permissao devem ser registradas sem expor caminho interno.

Plano recomendado:

- manter fluxo global atual inacessivel a tenants comuns;
- criar exportacao por tenant como funcionalidade separada;
- registrar usuario, tenant, arquivo, horario, IP e resultado do download;
- aplicar rate limit em listagem, criacao e download.
- expirar arquivos de exportacao temporarios;
- assinar URLs ou servir downloads por view autenticada, nunca por diretorio
  publico.

### 6. Admin Django

Manter `/admin/` desativado por enquanto.

Antes de reativar:

- planejar um admin publico separado para operador da plataforma;
- decidir se existira admin de tenant;
- evitar o mesmo `admin.site` para modelos globais e operacionais sem separacao;
- bloquear exposicao acidental do `admin.site` atual, que registra models
  globais e operacionais;
- garantir que models de `tenancy` nao aparecam no admin do tenant;
- garantir que models de `caixa` nao aparecam no admin publico;
- testar acesso por host publico e host de tenant.

Decisao pendente:

- se o SaaS tera apenas frontend operacional para clientes, provavelmente nao
  vale reativar admin de tenant.

## Obrigatorio antes de producao real

### 7. Media/uploads tenant-aware

Antes de qualquer upload real:

- definir estrutura tenant-aware, como `media/tenants/<schema_name>/...`;
- impedir path traversal;
- evitar nomes de arquivo previsiveis quando houver documento sensivel;
- validar permissao antes de servir arquivo;
- garantir que um tenant nao consiga montar URL de media de outro tenant;
- testar upload, listagem, download e remocao com dois tenants.
- arquivos sensiveis devem ser privados por padrao;
- `MEDIA_URL` publica so deve servir arquivos que possam ser publicos;
- download sensivel deve passar por view autenticada e autorizada.

Se usar storage externo no futuro:

- prefixar objetos por tenant;
- bloquear listagem global;
- assinar URLs com escopo e expiracao;
- auditar downloads sensiveis.

### 8. Limpeza antes de producao

Remover ou atualizar referencias legadas:

- `rhremoto`;
- `dashboardFinanceiro`;
- dominios antigos;
- caminhos pessoais;
- comandos antigos de deploy/validacao;
- evidencias antigas que nao servem ao RH SaaS;
- perfis de ambiente que sugerem cookies/dominos antigos.

Prioridade:

- comandos operacionais primeiro;
- documentos de deploy/configuracao depois;
- testes historicos por ultimo, desde que nao sejam usados no pipeline atual.

## Pode ficar para depois

### 9. Admin de tenant

Pode ficar para depois se o cliente final usar apenas o frontend.

Reavaliar apenas se:

- suporte interno precisar operar dados de cliente dentro do tenant;
- existir fluxo de atendimento com permissao auditada;
- houver necessidade clara de ferramentas administrativas por schema.

### 10. Dominio customizado

Nao precisa entrar no pos-spike imediato.

Antes de implementar:

- manter subdominio padrao funcionando;
- validar SSL e ownership do dominio;
- registrar dominio customizado no `public`;
- testar CORS/CSRF/cookies com dominio customizado.

### 11. Billing, trial e planos

Nao misturar com o endurecimento do isolamento.

Esses itens devem vir depois que:

- isolamento por schema estiver testado;
- autenticacao por tenant estiver confiavel;
- backup/export estiver tenant-scoped;
- frontend estiver validado por host.

## Checklist resumido

Obrigatorio antes de continuar multi-tenant:

- [ ] Suite com dois tenants.
- [ ] Testes de IDOR entre tenants.
- [ ] Testes de sessao/cookie entre hosts.
- [ ] Testes de permissoes por tenant.
- [ ] Testes de exportacao/backup com dois tenants.
- [ ] Decisao sobre metadata de `caixa` no `public`.
- [ ] Padrao de permissoes DRF definido.
- [ ] Frontend validado por subdominio.

Obrigatorio antes de deploy:

- [ ] Backup global bloqueado para admin de cliente.
- [ ] Exportacao tenant-scoped planejada ou implementada.
- [ ] Auditoria de download/export.
- [ ] Rate limit para exportacao/download/backup.
- [ ] `/admin/` mantido desativado ou reativado com separacao formal.

Obrigatorio antes de producao real:

- [ ] Media tenant-aware antes de uploads.
- [ ] Limpeza de referencias legadas operacionais.
- [ ] Testes de isolamento no pipeline.
- [ ] Politica de suporte/acesso a tenant documentada.
- [ ] Nenhuma API operacional sem permissao explicita ou guardrail equivalente.

Pode ficar para depois:

- [ ] Admin de tenant.
- [ ] Dominio customizado.
- [ ] Billing/trial/planos.
- [ ] Automacoes externas.

## Proxima implementacao pequena e segura

A proxima implementacao deve ser uma suite minima de testes automatizados com
dois tenants, sem alterar regra de negocio.

Escopo sugerido:

1. Criar helpers de teste para provisionar dois tenants.
2. Criar um usuario por tenant.
3. Criar dados operacionais com IDs equivalentes nos dois schemas.
4. Validar que a mesma API, chamada com hosts diferentes, retorna apenas dados
   do schema correto.
5. Validar que cookie/sessao de um tenant nao autentica automaticamente no
   outro.
6. Validar que exportacao e tentativa de backup global nao vazam dados entre
   tenants.

Essa etapa e pequena, segura e aumenta muito a confianca antes de qualquer nova
funcionalidade multi-tenant.
