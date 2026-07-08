# Gate operacional da demo publica

Registro operacional da validacao P0 da demo publica do RH SaaS.

Data do gate: 2026-07-07

## Objetivo

Registrar o estado validado da demo publica apos o deploy do commit:

```text
10526c3 chore(security): harden demo pool limits and reset cleanup
```

Este documento cobre a demo como portfolio/SaaS demonstravel, com
multi-tenancy por schema para permitir testadores isolados em fase controlada.

O objetivo deste gate nao e liberar publico irrestrito. O objetivo e confirmar
que a base operacional esta pronta para uso controlado e identificar o que
ainda falta antes de exposicao ampla.

## Escopo validado

- Backend Django na Oracle Cloud.
- Frontend publico em `https://demo-rh.taquiondev.com.br`.
- API publica em `https://api-demo-rh.taquiondev.com.br/api`.
- Demo fixa atual em `rh_teste`.
- Pool manual inicial com `demo1` e `demo2`.
- Wildcard externo para tenants demo:
  - `demo1.api-demo-rh.taquiondev.com.br`;
  - `demo2.api-demo-rh.taquiondev.com.br`;
  - base preparada para `demo1...demo10`.
- Redis para cache/throttle/lockout.
- Nginx com limites P0 de requisicao e payload.
- Gunicorn conservador para VM pequena.

## Estado aprovado no gate

### Codigo e deploy

- Servidor atualizado para `10526c3`.
- `git rev-parse --short HEAD` retornou `10526c3`.
- `pip install -r requirements.txt` sem mudancas relevantes.
- `python manage.py check` sem issues.
- `collectstatic --noinput` executado com sucesso.
- `python manage.py check --deploy` retornou apenas os warnings esperados de
  HSTS conservador:
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS`;
  - `SECURE_HSTS_PRELOAD`.

### Banco e migrations

- Migration `tenancy.0002_demotenantslot` aplicada.
- `public` atualizado.
- `rh_teste` atualizado.
- Schemas `demo1` e `demo2` criados pelo provisionamento do pool.
- Migrations completas rodaram em `demo1` e `demo2`.

### Infraestrutura

- VM com aproximadamente `954 MiB` de RAM.
- Swap de `2 GiB` ativo.
- Disco raiz com aproximadamente `16%` de uso no momento da validacao.
- Servicos ativos:
  - `rhsaas`;
  - `nginx`;
  - `redis-server`;
  - `postgresql`.
- Gunicorn ativo em `127.0.0.1:8002`.
- Configuracao operacional do Gunicorn:
  - `--workers 1`;
  - `--threads 2`;
  - `--timeout 90`;
  - `--max-requests 200`;
  - `--max-requests-jitter 50`.

### Redis

- `redis-cli ping` retornou `PONG`.
- Cache Django validado com `cache.set/get`, retornando `1`.
- Django configurado para usar Redis em producao.

### Nginx

- `sudo nginx -t` aprovado.
- Nginx recarregado com sucesso.
- API demo apontando para upstream em `127.0.0.1:8002`.
- Nginx ajustado para aceitar apex e wildcard:
  - `api-demo-rh.taquiondev.com.br`;
  - `*.api-demo-rh.taquiondev.com.br`.
- `proxy_set_header Host $host` preservado para permitir resolucao por tenant.
- `client_max_body_size 1M` aplicado no bloco da API demo.
- `limit_req_zone` configurado para:
  - login;
  - API geral.
- `limit_req` aplicado em:
  - `/api/auth/login/`;
  - `/api/`.

Observacao operacional:

- O Nginx ainda emite warning de `protocol options redefined for 0.0.0.0:443`.
  A sintaxe esta valida, mas vale limpar a duplicidade de `listen 443` quando
  houver uma janela segura.

### DNS, TLS e wildcard dos tenants demo

- DNS wildcard `*.api-demo-rh.taquiondev.com.br` implantado.
- `demo1.api-demo-rh.taquiondev.com.br` resolve para `137.131.219.81`.
- `demo2.api-demo-rh.taquiondev.com.br` resolve para `137.131.219.81`.
- Certificado TLS wildcard emitido com sucesso para:
  - `api-demo-rh.taquiondev.com.br`;
  - `*.api-demo-rh.taquiondev.com.br`.
- `openssl` confirmou SAN com:
  - `DNS:*.api-demo-rh.taquiondev.com.br`;
  - `DNS:api-demo-rh.taquiondev.com.br`.
- `curl -i https://demo1.api-demo-rh.taquiondev.com.br/api/auth/csrf/`
  retornou `HTTP/2 200`.
- `curl -i https://demo2.api-demo-rh.taquiondev.com.br/api/auth/csrf/`
  retornou `HTTP/2 200`.
- Cookies dos hosts wildcard retornaram com:
  - `Secure`;
  - `HttpOnly`;
  - `SameSite=Lax`.

Risco operacional registrado:

- O certificado wildcard foi emitido por DNS-01. Se a emissao/renovacao ainda
  depende de validacao manual por TXT na Hostinger, existe risco de expiracao
  futura por esquecimento ou falha operacional. Antes de abrir uso mais amplo,
  automatizar a renovacao com plugin/API DNS compativel ou migrar o DNS para
  provedor com suporte ACME automatizavel.

### API, CSRF, CORS e cookies

- GET `/api/auth/csrf/` retornou `200`.
- HEAD `/api/auth/csrf/` retornou `405`, esperado porque o endpoint permite
  `GET` e `OPTIONS`.
- Header `Access-Control-Allow-Origin` validado a partir do frontend publico.
- Cookie `csrftoken` validado com:
  - `Secure`;
  - `HttpOnly`;
  - `SameSite=Lax`.
- HSTS inicial conservador validado com `max-age=300`.

### Pool demo

- `python manage.py provisionar_pool_demo --slots=2 --dry-run` executado com
  sucesso.
- `python manage.py provisionar_pool_demo --slots=2` criou/garantiu:
  - tenant `demo1`;
  - tenant `demo2`;
  - domains tecnicos `demo1.api-demo-rh.taquiondev.com.br` e
    `demo2.api-demo-rh.taquiondev.com.br`;
  - slots `DemoTenantSlot`.
- Estado observado:
  - `demo1`: `ocupado`;
  - `demo2`: `livre`;
  - `demo1` com expiracao em `2026-07-10 22:34:28 UTC`;
  - limite por slot: `50 MB`.
- `resetar_tenant_demo --dry-run` recusou reset de slot ocupado, comportamento
  correto.
- `expirar_leases_demo --dry-run` encontrou `0` leases vencidos, comportamento
  correto para o momento do teste.

## Checklist final do gate operacional

- [x] Commit correto em producao.
- [x] Dependencias instaladas.
- [x] `python manage.py check` sem issues.
- [x] `python manage.py check --deploy` sem bloqueio, apenas HSTS conservador.
- [x] Redis ativo.
- [x] Django usando Redis.
- [x] PostgreSQL ativo.
- [x] Swap de 2 GB ativo.
- [x] Gunicorn ativo em `127.0.0.1:8002`.
- [x] Nginx valido com `nginx -t`.
- [x] Nginx com `client_max_body_size 1M` na API demo.
- [x] Nginx com rate limit para login e API.
- [x] Nginx aceitando apex e wildcard.
- [x] TLS wildcard cobrindo apex e `*.api-demo-rh.taquiondev.com.br`.
- [x] API `/api/auth/csrf/` respondendo.
- [x] API `/api/auth/csrf/` respondendo em `demo1`.
- [x] API `/api/auth/csrf/` respondendo em `demo2`.
- [x] Cookies seguros validados no header.
- [x] Pool demo provisionado com `demo1` e `demo2`.
- [x] Reset destrutivo bloqueia slot ocupado.
- [x] Expiracao dry-run nao altera lease ainda valido.

## Comandos read-only para confirmar estado atual

Executar no servidor:

```bash
cd ~/sites/rhsaas
source venv/bin/activate

git status --short
git rev-parse --short HEAD
git log -1 --oneline

free -h
swapon --show
df -h /

systemctl is-active rhsaas nginx redis-server postgresql
systemctl status rhsaas --no-pager -l
sudo ss -ltnp | grep -E ":(80|443|8002|5432|6379)\b"

redis-cli ping

python manage.py check
python manage.py check --deploy

sudo nginx -t
sudo nginx -T | grep -nE "api-demo-rh|limit_req|limit_req_zone|client_max_body_size|proxy_pass|8002"

curl -i https://api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i -H "Origin: https://demo-rh.taquiondev.com.br" \
  https://api-demo-rh.taquiondev.com.br/api/auth/csrf/

dig +short demo1.api-demo-rh.taquiondev.com.br
dig +short demo2.api-demo-rh.taquiondev.com.br

echo | openssl s_client \
  -connect demo1.api-demo-rh.taquiondev.com.br:443 \
  -servername demo1.api-demo-rh.taquiondev.com.br 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName

curl -i https://demo1.api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i https://demo2.api-demo-rh.taquiondev.com.br/api/auth/csrf/
```

Validar slots sem alterar banco:

```bash
python manage.py shell --no-imports -c "from tenancy.models import DemoTenantSlot; print(list(DemoTenantSlot.objects.order_by('slot_code').values('slot_code','status','lease_expires_at','max_storage_mb')))"
```

Validar domains sem alterar banco:

```bash
python manage.py shell --no-imports -c "from tenancy.models import Domain; print(list(Domain.objects.filter(domain__contains='api-demo-rh').values('domain','tenant__schema_name','is_primary').order_by('domain')))"
```

## P0 restante

Para beta controlado pequeno, nao ha bloqueador P0 tecnico conhecido apos este
gate. O wildcard externo dos tenants demo tambem foi validado para `demo1` e
`demo2`. Antes de convidar pessoas, ainda deve ser feito:

- executar um teste manual completo no navegador com usuario demo:
  - abrir frontend;
  - login;
  - carregar dashboard;
  - navegar por clientes, eventos, servicos, configuracoes financeiras e
    orcamentos;
  - criar um registro simples, se fizer sentido;
  - logout;
  - confirmar console sem erro de CORS, CSRF, mixed content ou cookie.
- registrar qual usuario/tenant sera entregue ao testador.
- evitar entregar `rh_teste` para varios testadores ao mesmo tempo sem aviso de
  dados compartilhados.

## O que ainda falta

- Validar fluxo real no navegador usando `demo1` e `demo2`, incluindo login,
  logout, cookies e isolamento visivel para o testador.
- Definir como o operador vai entregar ao testador a API tecnica correta do
  lease enquanto o frontend ainda nao distribui automaticamente o tenant.
- Automatizar ou operacionalizar lembrete de renovacao do certificado wildcard
  DNS-01.
- Documentar rotina recorrente para expirar leases, resetar slots e revisar
  logs.
- Melhorar monitoramento/alertas antes de aumentar o publico.

## P1 antes de publico irrestrito

Antes de abrir para qualquer pessoa na internet:

- configurar monitoramento externo de disponibilidade;
- configurar alerta para 5xx/502;
- configurar alerta para memoria, swap e disco;
- validar restore em ambiente temporario;
- executar teste de carga leve e documentar limite seguro;
- implementar ou operacionalizar quota real de 50 MB por tenant;
- automatizar renovacao do certificado wildcard DNS-01 ou migrar DNS para
  provedor com plugin ACME confiavel;
- ajustar frontend para selecionar a API tecnica do tenant reservado;
- criar rotina agendada ou runbook periodico para expirar leases;
- decidir se reset automatico sera permitido ou se continuara manual;
- limpar o warning de Nginx sobre `protocol options redefined`;
- criar health endpoint dedicado ou padrao de health check documentado;
- revisar UX publica de entrada da demo e mensagem de uso controlado.

## Melhorias para portfolio e recrutadores

- Preparar dados seed de demonstracao com nomes ficticios.
- Criar roteiro curto de demonstracao:
  - login;
  - dashboard;
  - clientes/eventos;
  - orcamentos;
  - configuracao financeira;
  - prova de isolamento por tenant.
- Criar uma pagina ou texto de boas-vindas explicando que e demo de portfolio.
- Explicar que a fase atual nao e SaaS comercial aberto.
- Para recrutadores, preferir demo guiada ou credencial temporaria com horario
  combinado.

## Decisao de prontidao

- Amigos: aprovado para beta controlado, preferencialmente com poucos
  testadores simultaneos e tenants demo separados.
- Recrutadores: aprovado com demo guiada ou credencial temporaria, apos teste
  manual completo no navegador usando o tenant demo entregue.
- Clientes em demo guiada: aceitavel para conversa exploratoria, sem promessa
  de produto SaaS comercial em producao, e com operador acompanhando.
- Publico irrestrito: nao aprovado. Ainda exige monitoramento, restore
  validado, teste de carga, frontend distribuindo o tenant do lease, renovacao
  automatizada do wildcard e operacao automatizada ou semi-automatizada de
  expiracao/reset.
