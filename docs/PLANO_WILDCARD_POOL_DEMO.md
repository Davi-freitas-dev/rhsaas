# Plano de wildcard para o pool demo

> **Nota de escopo atual:** este documento preserva o historico de DNS,
> wildcard e homologacao dos dez tenants. Para alocacao, expiracao e reset,
> prevalece a decisao atual: `demo1` e permanente e `demo2...demo10` formam a
> pool publica automatica. Consulte
> `PLANO_LIBERACAO_DEMO_PUBLICA_AUTOMATICA.md` e
> `deploy/demo-publica/README.md`.

Este documento descreve o plano tecnico para expor os tenants do pool demo em
subdominios proprios:

- `demo1.api-demo-rh.taquiondev.com.br`
- `demo2.api-demo-rh.taquiondev.com.br`
- ...
- `demo10.api-demo-rh.taquiondev.com.br`

Ele comecou como plano local de diagnostico e implantacao futura. Apos a
validacao operacional em producao, tambem registra o estado validado do
wildcard externo. Qualquer nova alteracao de DNS, Nginx, certificado TLS, banco
ou producao continua exigindo revisao operacional propria.

## Objetivo

Permitir que o RH SaaS demonstre multi-tenancy por schema com mais de um
testador ao mesmo tempo, mantendo cada vaga demo isolada por `Host` e schema.

O frontend publico continua sendo:

```text
https://demo-rh.taquiondev.com.br
```

Cada tenant demo deve ser acessado por uma API tecnica propria:

```text
https://demo1.api-demo-rh.taquiondev.com.br/api
https://demo2.api-demo-rh.taquiondev.com.br/api
...
https://demo10.api-demo-rh.taquiondev.com.br/api
```

## Estado validado em producao

Data do registro: 2026-07-07.

O wildcard externo foi implantado e validado para o pool demo:

- DNS wildcard `*.api-demo-rh.taquiondev.com.br` implantado.
- TLS wildcard emitido com sucesso para:
  - `api-demo-rh.taquiondev.com.br`;
  - `*.api-demo-rh.taquiondev.com.br`.
- `openssl` confirmou SAN:
  - `DNS:*.api-demo-rh.taquiondev.com.br`;
  - `DNS:api-demo-rh.taquiondev.com.br`.
- Nginx ajustado com:
  - `server_name api-demo-rh.taquiondev.com.br *.api-demo-rh.taquiondev.com.br;`.
- `proxy_set_header Host $host` deve permanecer preservado.
- `curl -i https://demo1.api-demo-rh.taquiondev.com.br/api/auth/csrf/`
  retornou `HTTP/2 200`.
- `curl -i https://demo2.api-demo-rh.taquiondev.com.br/api/auth/csrf/`
  retornou `HTTP/2 200`.
- Cookies retornaram com:
  - `Secure`;
  - `HttpOnly`;
  - `SameSite=Lax`.

Resultado: DNS, TLS, Nginx e entrada HTTP dos tenants `demo1` e `demo2` estao
validados externamente.

## Arquitetura recomendada

A recomendacao e usar um modelo hibrido:

- DNS wildcard para apontar `*.api-demo-rh.taquiondev.com.br` para a VM Oracle;
- TLS wildcard cobrindo `*.api-demo-rh.taquiondev.com.br`;
- Nginx aceitando o wildcard e encaminhando para o mesmo Gunicorn;
- Django autorizando apenas tenants que existam como `Domain` explicito no
  banco;
- `provisionar_pool_demo` mantendo os `Domain` tecnicos `demo1...demo10`;
- cookies de sessao e CSRF host-only, sem dominio compartilhado.

O wildcard de infraestrutura simplifica DNS, TLS e Nginx. A autorizacao real
de tenant continua no banco, via `tenancy.Domain`.

## Suporte atual do django-tenants

O modelo atual suporta wildcard de infraestrutura sem alteracao no backend,
desde que cada host permitido exista como registro `Domain`.

O fluxo atual e:

1. DNS envia `demo1.api-demo-rh.taquiondev.com.br` para a VM.
2. TLS/Nginx aceitam o host.
3. Nginx preserva `Host $host`.
4. `TenantMainMiddleware` do `django-tenants` resolve o tenant pelo `Host`.
5. O `Domain` `demo1.api-demo-rh.taquiondev.com.br` aponta para o tenant
   `demo1`.
6. O backend usa o schema `demo1`.

Importante: o `django-tenants` nao deve tratar qualquer subdominio wildcard
como tenant valido automaticamente. O wildcard no DNS/Nginx apenas entrega a
requisicao ao backend. Para a aplicacao aceitar o tenant, o host precisa existir
em `tenancy.Domain`.

## O que precisa existir

### DNS

Na Hostinger, manter o registro atual da demo fixa:

```text
A  api-demo-rh  IP_PUBLICO_DA_ORACLE
```

Para o pool, adicionar:

```text
A  *.api-demo-rh  IP_PUBLICO_DA_ORACLE
```

Observacoes:

- `*.api-demo-rh.taquiondev.com.br` cobre `demo1.api-demo-rh...`,
  `demo2.api-demo-rh...` etc.
- O wildcard nao cobre o apex `api-demo-rh.taquiondev.com.br`; por isso o
  registro `api-demo-rh` deve continuar existindo.
- Se quiser reduzir exposicao, a alternativa e criar apenas registros
  explicitos `demo1.api-demo-rh` ate `demo10.api-demo-rh`.

### Certificado TLS

O certificado deve cobrir:

```text
api-demo-rh.taquiondev.com.br
*.api-demo-rh.taquiondev.com.br
```

O certificado atual do apex, se possuir apenas
`api-demo-rh.taquiondev.com.br`, nao cobre `demo1.api-demo-rh...`.

Para wildcard com Let's Encrypt, o caminho normal e desafio DNS-01. O desafio
HTTP-01 comum do Certbot nao emite wildcard. A emissao ja foi validada, mas a
renovacao continua sendo ponto de atencao se depender de TXT manual na
Hostinger.

Antes de ampliar o publico, automatizar a renovacao com plugin/API DNS
compativel ou migrar o DNS para provedor com suporte ACME automatizavel.

### Nginx

O bloco da API deve aceitar o apex e o wildcard:

```nginx
server_name api-demo-rh.taquiondev.com.br *.api-demo-rh.taquiondev.com.br;
```

O ponto critico e preservar o host original:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto https;
```

Nao usar:

```nginx
proxy_set_header Host api-demo-rh.taquiondev.com.br;
```

Isso faria todos os tenants chegarem ao Django como o mesmo host, quebrando a
resolucao por tenant.

Manter tambem:

- `client_max_body_size 1m`;
- `limit_req_zone` no contexto `http`;
- `limit_req` mais rigoroso em login, backup, exportacao e rotas sensiveis;
- proxy para o mesmo Gunicorn `127.0.0.1:8002`;
- redirect HTTP para HTTPS usando `$host`.

### ALLOWED_HOSTS

Em producao, nunca usar `*`.

Com wildcard de infraestrutura, usar um escopo restrito:

```env
ALLOWED_HOSTS=api-demo-rh.taquiondev.com.br,.api-demo-rh.taquiondev.com.br
```

Em Django, o valor com ponto inicial permite o dominio e seus subdominios. Se a
decisao for evitar wildcard na aplicacao, listar explicitamente:

```env
ALLOWED_HOSTS=api-demo-rh.taquiondev.com.br,demo1.api-demo-rh.taquiondev.com.br,demo2.api-demo-rh.taquiondev.com.br
```

e assim por diante ate `demo10`.

### CSRF_TRUSTED_ORIGINS

O frontend roda em outro origin:

```text
https://demo-rh.taquiondev.com.br
```

Para aceitar POSTs autenticados do frontend para as APIs tecnicas, usar:

```env
CSRF_TRUSTED_ORIGINS=https://demo-rh.taquiondev.com.br,https://api-demo-rh.taquiondev.com.br,https://*.api-demo-rh.taquiondev.com.br
```

Se optar por hosts explicitos, substituir o wildcard por `demo1...demo10`.

### CORS

Manter CORS estreito. O browser vem do frontend, nao dos subdominios de API.

```env
CORS_ALLOWED_ORIGINS=https://demo-rh.taquiondev.com.br
CORS_ALLOW_CREDENTIALS=True
```

Nao usar `*` com credenciais.

### Cookies

Manter cookies host-only:

```env
SESSION_COOKIE_DOMAIN=
CSRF_COOKIE_DOMAIN=
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
```

Nao configurar:

```env
SESSION_COOKIE_DOMAIN=.api-demo-rh.taquiondev.com.br
CSRF_COOKIE_DOMAIN=.api-demo-rh.taquiondev.com.br
```

Cookies compartilhados entre subdominios poderiam misturar sessao/CSRF entre
`demo1` e `demo2`. O isolamento desejado e que login em `demo1` nao autentique
automaticamente em `demo2`.

### settings.py

Nao ha indicacao de necessidade de mudanca de codigo em `settings.py` para o
wildcard, porque os valores ja vem de variaveis de ambiente:

- `ALLOWED_HOSTS`;
- `CSRF_TRUSTED_ORIGINS`;
- `CORS_ALLOWED_ORIGINS`;
- `SESSION_COOKIE_DOMAIN`;
- `CSRF_COOKIE_DOMAIN`.

O ajuste deve ser feito no `.env.production` do servidor, seguido de restart do
servico `rhsaas`.

## Riscos e mitigacoes

### Host Header

Risco: aceitar hosts demais e permitir comportamento inesperado.

Mitigacao:

- nao usar `ALLOWED_HOSTS=*`;
- restringir a `.api-demo-rh.taquiondev.com.br`;
- manter apenas `Domain` explicitos `demo1...demo10`;
- validar hosts desconhecidos com `curl`.

### Resolucao incorreta de tenant

Risco: Nginx trocar o `Host` ou algum `Domain` apontar para tenant errado.

Mitigacao:

- manter `proxy_set_header Host $host`;
- validar `Domain.domain -> tenant.schema_name`;
- testar `demo1` e `demo2` com dados sentinela.

### Cookies e sessoes

Risco: cookie compartilhado autenticar o usuario no tenant errado.

Mitigacao:

- manter `SESSION_COOKIE_DOMAIN` e `CSRF_COOKIE_DOMAIN` vazios;
- validar no navegador que cookies ficam presos ao host de cada tenant;
- testar login em `demo1` e ausencia de login em `demo2`.

### CSRF/CORS

Risco: CORS estreito demais bloquear o frontend, ou amplo demais expor
credenciais.

Mitigacao:

- `CORS_ALLOWED_ORIGINS` apenas com `https://demo-rh.taquiondev.com.br`;
- `CSRF_TRUSTED_ORIGINS` com frontend e APIs tecnicas;
- testar `Origin: https://demo-rh.taquiondev.com.br`.

### TLS wildcard

Risco: certificado nao cobrir subdominios ou renovacao falhar.

Mitigacao:

- manter certificado com SAN para apex e wildcard;
- monitorar vencimento;
- criar alerta antes da expiracao;
- automatizar renovacao DNS-01 ou migrar DNS para provedor com plugin ACME;
- validar SNI em `demo1` e `demo2`;
- manter HSTS conservador ate validar todos os hosts.

### Wildcard DNS amplo

Risco: qualquer subdominio de primeiro nivel em `api-demo-rh` apontar para o
servidor, gerando ruido e tentativas indevidas.

Mitigacao:

- Django deve negar hosts sem `Domain`;
- Nginx deve manter rate limit;
- logs devem ser revisados para hosts desconhecidos;
- se isso incomodar, usar hosts explicitos `demo1...demo10`.

### Frontend ainda estatico

Risco: mesmo com wildcard no backend, o frontend continuar chamando apenas
`https://api-demo-rh.taquiondev.com.br/api`.

Mitigacao:

- para fase manual, operador deve orientar qual API tecnica pertence ao lease;
- para experiencia publica completa, criar fase futura para o frontend receber
  ou selecionar a API do tenant reservado;
- nao confundir acesso externo ao backend com distribuicao automatica no
  frontend.

## Wildcard ou hosts explicitos

### Opcao A: wildcard completo

Usar:

```text
*.api-demo-rh.taquiondev.com.br
```

Vantagens:

- menos manutencao de DNS;
- menos manutencao de Nginx;
- facilita crescer de `demo1...demo10` para outros slots controlados.

Cuidados:

- exige TLS wildcard com DNS-01;
- expoe subdominios inexistentes ate o Django negar;
- precisa de logs e rate limits bem acompanhados.

### Opcao B: apenas demo1...demo10

Criar registros e certificado para:

```text
demo1.api-demo-rh.taquiondev.com.br
...
demo10.api-demo-rh.taquiondev.com.br
```

Vantagens:

- superficie menor;
- mais simples de raciocinar em beta controlado;
- pode usar certificado SAN explicito.

Cuidados:

- mais manutencao;
- qualquer novo slot exige DNS/TLS/Nginx.

### Recomendacao

Para este projeto de portfolio/SaaS demonstravel, a melhor opcao pratica e:

1. usar DNS/TLS/Nginx wildcard;
2. manter `Domain` do Django explicito apenas para `demo1...demo10`;
3. manter cookies host-only;
4. manter CORS restrito ao frontend;
5. validar tudo em beta guiado antes de abrir mais.

Assim a infraestrutura fica simples, mas a aplicacao continua permitindo apenas
os tenants realmente provisionados.

## Checklist operacional de implantacao

Estado atual: checklist principal concluido para `demo1` e `demo2`. Manter a
lista como referencia para revalidacoes, renovacao de certificado, troca de
Nginx ou ampliacao para `demo3...demo10`.

### Antes da janela

- [x] Confirmar commit em producao.
- [x] Confirmar backup/snapshot da VM e banco.
- [x] Confirmar Redis `PONG`.
- [x] Confirmar swap ativo.
- [x] Confirmar `python manage.py check`.
- [x] Confirmar `python manage.py check --deploy`.
- [x] Confirmar que `demo1` e `demo2` existem e estao provisionados.
- [x] Confirmar `Domain` tecnico de `demo1` e `demo2`.
- [x] Confirmar plano de rollback do Nginx.
- [x] Confirmar que o certificado wildcard foi emitido.

### DNS

- [x] Manter `api-demo-rh` apontando para a VM.
- [x] Criar `*.api-demo-rh` apontando para a VM.
- [x] Aguardar propagacao.
- [x] Validar `demo1` e `demo2`.
- [x] Validar que apex e wildcard resolvem para o mesmo IP.

### TLS

- [x] Certificado cobre `api-demo-rh.taquiondev.com.br`.
- [x] Certificado cobre `*.api-demo-rh.taquiondev.com.br`.
- [ ] Renovacao automatica revisada.
- [x] SNI testado em `demo1` e `demo2`.

### Nginx

- [x] `server_name` inclui apex e wildcard.
- [x] `proxy_set_header Host $host` preservado.
- [x] `X-Forwarded-Proto https` preservado.
- [x] `client_max_body_size 1m` preservado.
- [x] `limit_req_zone` no contexto correto.
- [x] Login, API e rotas sensiveis com limites.
- [x] `sudo nginx -t` OK.
- [x] `sudo systemctl reload nginx` OK.

### Django/env

- [ ] `ALLOWED_HOSTS` restrito, sem `*`.
- [ ] `CSRF_TRUSTED_ORIGINS` inclui frontend e APIs tecnicas.
- [ ] `CORS_ALLOWED_ORIGINS` inclui apenas o frontend.
- [ ] `SESSION_COOKIE_DOMAIN` vazio.
- [ ] `CSRF_COOKIE_DOMAIN` vazio.
- [ ] `SECURE_PROXY_SSL_HEADER=True`.
- [ ] `SECURE_SSL_REDIRECT=True`.
- [ ] Redis configurado como cache em producao.
- [ ] Servico `rhsaas` reiniciado.

### Frontend

- [ ] Confirmar se a fase ainda sera manual.
- [ ] Confirmar como o testador recebera o host tecnico do tenant.
- [ ] Confirmar que o frontend nao continua preso ao host fixo quando a intencao
  for testar `demo1` ou `demo2`.

## Comandos de validacao

### DNS

PowerShell:

```powershell
Resolve-DnsName api-demo-rh.taquiondev.com.br -Type A
Resolve-DnsName demo1.api-demo-rh.taquiondev.com.br -Type A
Resolve-DnsName demo2.api-demo-rh.taquiondev.com.br -Type A
Resolve-DnsName inexistente.api-demo-rh.taquiondev.com.br -Type A
```

Linux/servidor:

```bash
dig +short api-demo-rh.taquiondev.com.br
dig +short demo1.api-demo-rh.taquiondev.com.br
dig +short demo2.api-demo-rh.taquiondev.com.br
dig +short inexistente.api-demo-rh.taquiondev.com.br
```

### TLS

```bash
echo | openssl s_client \
  -connect demo1.api-demo-rh.taquiondev.com.br:443 \
  -servername demo1.api-demo-rh.taquiondev.com.br 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

Repetir para `demo2`.

### Nginx

```bash
sudo nginx -t
sudo nginx -T | grep -nE "server_name|limit_req|limit_req_zone|client_max_body_size|proxy_set_header Host|8002"
sudo systemctl status nginx --no-pager -l
sudo systemctl status rhsaas --no-pager -l
sudo ss -ltnp | grep -E ":80|:443|:8002"
```

### Django/env

```bash
python manage.py check
python manage.py check --deploy
python manage.py shell --no-imports -c "from django.conf import settings; print('ALLOWED_HOSTS=', settings.ALLOWED_HOSTS); print('CSRF=', settings.CSRF_TRUSTED_ORIGINS); print('CORS=', settings.CORS_ALLOWED_ORIGINS); print('SESSION_COOKIE_DOMAIN=', settings.SESSION_COOKIE_DOMAIN); print('CSRF_COOKIE_DOMAIN=', settings.CSRF_COOKIE_DOMAIN)"
python manage.py shell --no-imports -c "from django.core.cache import cache; cache.set('wildcard_gate', 1, 30); print(cache.get('wildcard_gate'))"
```

### Domain dos tenants

```bash
python manage.py shell --no-imports -c "from tenancy.models import Domain; print(list(Domain.objects.filter(domain__contains='api-demo-rh').values('domain','tenant__schema_name','is_primary').order_by('domain')))"
python manage.py shell --no-imports -c "from tenancy.models import DemoTenantSlot; print(list(DemoTenantSlot.objects.values('slot_code','status','tenant__schema_name').order_by('slot_code')))"
```

### API por tenant

```bash
curl -i https://demo1.api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i https://demo2.api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i -H "Origin: https://demo-rh.taquiondev.com.br" https://demo1.api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i -H "Origin: https://demo-rh.taquiondev.com.br" https://demo2.api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i https://inexistente.api-demo-rh.taquiondev.com.br/api/auth/csrf/
```

Esperado:

- `demo1` e `demo2` retornam endpoint valido se os `Domain` existirem.
- host inexistente nao deve retornar dados de tenant valido.
- resposta com `Origin` do frontend deve permitir fluxo autenticado esperado.

### Isolamento demo1 x demo2

Criar ou confirmar dados sentinela em cada schema:

```bash
python manage.py shell --no-imports <<'PY'
from django_tenants.utils import schema_context
from caixa.models import Cliente

with schema_context("demo1"):
    Cliente.objects.get_or_create(
        cpf_cnpj="00.000.000/0001-01",
        defaults={"nome_razao_social": "Sentinela Demo 1"},
    )

with schema_context("demo2"):
    Cliente.objects.get_or_create(
        cpf_cnpj="00.000.000/0001-02",
        defaults={"nome_razao_social": "Sentinela Demo 2"},
    )

print("sentinelas ok")
PY
```

Validar via API/navegador que o dado de `demo1` nao aparece em `demo2`.

### Login, logout e cookies

No navegador:

- abrir a demo usando o tenant/API `demo1`;
- fazer login;
- confirmar cookie `sessionid` host-only para `demo1.api-demo-rh...`;
- abrir fluxo equivalente para `demo2`;
- confirmar que `demo2` nao herda sessao de `demo1`;
- fazer logout em `demo1`;
- confirmar que `demo2` nao e afetado;
- confirmar que `csrftoken` e `sessionid` usam `Secure`, `HttpOnly` e
  `SameSite=Lax`.

## Testes obrigatorios apos implantacao

- [x] `demo1` resolve DNS.
- [x] `demo2` resolve DNS.
- [ ] host inexistente falha sem vazar tenant valido.
- [x] TLS valido em `demo1`.
- [x] TLS valido em `demo2`.
- [x] `curl /api/auth/csrf/` retorna 200 em `demo1`.
- [x] `curl /api/auth/csrf/` retorna 200 em `demo2`.
- [ ] `Origin: https://demo-rh.taquiondev.com.br` funciona.
- [ ] login funciona em `demo1`.
- [ ] login funciona em `demo2`.
- [ ] logout funciona.
- [ ] cookies nao sao compartilhados entre `demo1` e `demo2`.
- [ ] dados de `demo1` nao aparecem em `demo2`.
- [ ] reset dry-run continua bloqueando slot ocupado.
- [ ] rate limit do Nginx continua ativo.
- [ ] logs nao mostram senha, token, segredo ou session key.

## O que ainda falta

- Validar `Origin: https://demo-rh.taquiondev.com.br` em `demo1` e `demo2`
  depois da implantacao wildcard.
- Validar login/logout no navegador em `demo1` e `demo2`.
- Confirmar que cookies de `demo1` nao autenticam `demo2`.
- Validar isolamento funcional com dados sentinela por tenant.
- Definir fluxo manual para entregar ao testador o tenant/API correto.
- Ajustar futuramente o frontend para selecionar a API tecnica do lease.
- Automatizar renovacao do certificado wildcard DNS-01 ou migrar DNS para
  provedor com plugin ACME.
- Manter rotina de revisao de logs e rate limits para hosts desconhecidos.

## Prontidao apos wildcard

Com wildcard DNS/TLS/Nginx implantado e `demo1`/`demo2` respondendo `200` em
`/api/auth/csrf/`:

- amigos: pronto para beta controlado;
- recrutadores: pronto para demonstracao guiada;
- clientes em demo guiada: aceitavel, com operador acompanhando;
- publico irrestrito: ainda nao recomendado.

Para publico irrestrito ainda faltam, no minimo:

- fluxo de frontend para escolher ou receber o tenant/API do lease;
- monitoramento e alertas mais completos;
- rotina operacional de expiracao/reset mais automatizada ou agendada;
- renovacao automatizada do certificado wildcard;
- teste E2E cobrindo frontend + `demo1` + `demo2`;
- teste de carga leve;
- politica operacional clara para abuso, suporte e indisponibilidade.

## Proximo passo recomendado

O proximo passo mais seguro e executar uma validacao funcional manual no
navegador para `demo1` e `demo2`:

1. ocupar ou confirmar usuario demo em cada slot;
2. acessar o frontend com a API tecnica correta para cada tenant;
3. fazer login e logout em cada tenant;
4. criar dado sentinela simples em `demo1`;
5. criar dado sentinela diferente em `demo2`;
6. confirmar que os dados nao cruzam;
7. revisar cookies no navegador;
8. revisar logs de Nginx/Gunicorn/Django apos o teste.

Depois disso, documentar o procedimento de entrega manual de acesso para
amigos, recrutadores ou clientes em demo guiada.
