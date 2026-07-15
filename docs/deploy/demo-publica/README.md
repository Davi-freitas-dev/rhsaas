# Operacao da demo publica automatica do RH SaaS

Este e o runbook de deploy e operacao. Decisoes, progresso, riscos e evidencias
ficam em `docs/PLANO_LIBERACAO_DEMO_PUBLICA_AUTOMATICA.md`. Os documentos de
gate e pool manual anteriores permanecem historicos; em divergencia, o plano
de liberacao automatica e este runbook prevalecem.

Nunca registrar aqui, em logs ou em evidencias senhas, tokens, hashes,
enderecos IP completos ou dados pessoais de visitantes.

## Arquitetura em operacao

- frontend: `https://demo-rh.taquiondev.com.br`;
- API de entrada: `https://api-demo-rh.taquiondev.com.br/api`;
- schema de entrada legado/compativel: `rh_teste`;
- metadata e autoridade de leases: schema `public`;
- vagas isoladas: `demo1...demo10`;
- APIs das vagas: `https://demoN.api-demo-rh.taquiondev.com.br/api`;
- autenticacao: token de troca de uso unico; somente o digest HMAC fica no
  banco; a sessao Django e criada pelo host `demoN`;
- expiracao padrao: 60 minutos;
- manutencao: `manter_pool_demo`, disparado por systemd timer;
- Gunicorn recomendado para a VM de aproximadamente 1 GB: 1 worker e 2
  threads em `127.0.0.1:8002`.

O apex continua apontando para `rh_teste`, por compatibilidade. A rota de lease
e publicada nesse URLconf, mas muda imediatamente para `public` antes de ler ou
travar `DemoTenantSlot`. Hosts `demoN` recusam essa rota. A troca de token e
publicada somente no URLconf de tenant e valida que token, slot e schema
coincidem.

## Arquivos deste pacote

- `.env.production.example`: variaveis sem valores secretos;
- `nginx-api-demo-rh.conf`: apex + wildcard, limites e proxy;
- `rhsaas-demo.service`: Gunicorn;
- `rhsaas-demo-pool-maintenance.service`: manutencao oneshot;
- `rhsaas-demo-pool-maintenance.timer`: execucao a cada dois minutos;
- `garantir_domain_rh_teste.py`: compatibilidade idempotente do apex.

## Pre-condicoes obrigatorias

Antes de qualquer deploy:

1. backup recente do PostgreSQL existente e restauracao testada em ambiente
   separado;
2. certificado valido para o apex e `*.api-demo-rh.taquiondev.com.br`, com
   renovacao automatica comprovada;
3. Redis e PostgreSQL saudaveis;
4. no minimo 10 vagas aprovadas no planejamento de capacidade;
5. migrations e testes relacionados verdes;
6. `DEMO_PUBLIC_LEASE_ENABLED=False`;
7. nenhuma vaga deve ser liberada manualmente sem reset comprovado.

Diagnostico inicial no servidor:

```bash
sudo systemctl status rhsaas-demo postgresql redis-server --no-pager
sudo journalctl -u rhsaas-demo -n 100 --no-pager
df -h
free -h
sudo ss -ltnp | grep -E ":(80|443|8002|5432|6379)\b"
```

## Variaveis de ambiente

```bash
cp docs/deploy/demo-publica/.env.production.example .env
chmod 600 .env
```

Substituir os placeholders fora do Git. Manter cookies de sessao e CSRF
host-only:

```env
SESSION_COOKIE_DOMAIN=
CSRF_COOKIE_DOMAIN=
```

Isso impede que uma sessao de `demo1` seja enviada a `demo2`. A origem do
frontend deve ser a unica origem CORS permitida. O wildcard e necessario em
`CSRF_TRUSTED_ORIGINS` porque a troca ocorre no host alocado.

Na Vercel:

```env
NEXT_PUBLIC_API_BASE_URL=https://api-demo-rh.taquiondev.com.br/api
NEXT_PUBLIC_API_MOCK_FALLBACK=false
NEXT_PUBLIC_API_TIMEOUT_MS=12000
```

## Sequencia segura de deploy

Os comandos abaixo sao um roteiro; esta preparacao local nao os executa no
servidor.

1. Publicar backend com a entrada ainda desligada.
2. Instalar dependencias no venv e executar checks.
3. Aplicar migration compartilhada e migrations de todos os tenants.
4. Provisionar/validar dez slots.
5. Instalar Gunicorn, Nginx e timer.
6. Publicar o frontend.
7. Fazer smoke test com entrada desligada.
8. Ativar a entrada e repetir o smoke ponta a ponta.

Checks e migrations:

```bash
cd /opt/rhsaas
/opt/rhsaas/venv/bin/python manage.py check --deploy
/opt/rhsaas/venv/bin/python manage.py makemigrations --check --dry-run
/opt/rhsaas/venv/bin/python manage.py migrate_schemas --plan
/opt/rhsaas/venv/bin/python manage.py migrate_schemas --shared
/opt/rhsaas/venv/bin/python manage.py migrate_schemas
```

Validar o plano antes de aplicar. Nao usar `--fake` para contornar falhas.

Compatibilidade do dominio apex:

```bash
/opt/rhsaas/venv/bin/python manage.py shell --no-imports \
  < docs/deploy/demo-publica/garantir_domain_rh_teste.py
```

Pool, primeiro em dry-run:

```bash
/opt/rhsaas/venv/bin/python manage.py provisionar_pool_demo --slots=10 --dry-run
/opt/rhsaas/venv/bin/python manage.py provisionar_pool_demo --slots=10
/opt/rhsaas/venv/bin/python manage.py manter_pool_demo --dry-run
```

O provisionamento cria somente tenants, domains e slots ausentes. O seed e
recriado pelo reset e confirmado novamente na alocacao antes de ativar o
usuario temporario.

## systemd

```bash
sudo cp docs/deploy/demo-publica/rhsaas-demo.service \
  /etc/systemd/system/rhsaas-demo.service
sudo cp docs/deploy/demo-publica/rhsaas-demo-pool-maintenance.service \
  /etc/systemd/system/rhsaas-demo-pool-maintenance.service
sudo cp docs/deploy/demo-publica/rhsaas-demo-pool-maintenance.timer \
  /etc/systemd/system/rhsaas-demo-pool-maintenance.timer
sudo systemctl daemon-reload
sudo systemctl enable --now rhsaas-demo.service
sudo systemctl enable --now rhsaas-demo-pool-maintenance.timer
sudo systemctl list-timers rhsaas-demo-pool-maintenance.timer
```

Validacao manual, sem alterar vaga valida:

```bash
sudo -u ubuntu /opt/rhsaas/venv/bin/python \
  /opt/rhsaas/manage.py manter_pool_demo --dry-run
sudo systemctl start rhsaas-demo-pool-maintenance.service
sudo systemctl status rhsaas-demo-pool-maintenance.service --no-pager
```

## Nginx e TLS

```bash
sudo cp docs/deploy/demo-publica/nginx-api-demo-rh.conf \
  /etc/nginx/sites-available/rhsaas-demo
sudo ln -s /etc/nginx/sites-available/rhsaas-demo \
  /etc/nginx/sites-enabled/rhsaas-demo
sudo nginx -t
sudo systemctl reload nginx
```

O certificado precisa conter os dois SANs:

```text
api-demo-rh.taquiondev.com.br
*.api-demo-rh.taquiondev.com.br
```

DNS/TLS read-only:

```bash
dig +short api-demo-rh.taquiondev.com.br
dig +short demo1.api-demo-rh.taquiondev.com.br
openssl s_client -connect demo1.api-demo-rh.taquiondev.com.br:443 \
  -servername demo1.api-demo-rh.taquiondev.com.br </dev/null 2>/dev/null \
  | openssl x509 -noout -dates -ext subjectAltName
sudo certbot renew --dry-run
```

## Ativacao e desativacao rapida

Ativar apenas depois do checklist de homologacao:

```env
DEMO_PUBLIC_LEASE_ENABLED=True
```

```bash
sudo systemctl restart rhsaas-demo
curl -fsS https://api-demo-rh.taquiondev.com.br/api/health/
```

Para desativar novas entradas, mudar imediatamente a flag para `False` e
reiniciar Gunicorn. Isso nao apaga nem libera slots. Sessoes existentes expiram
normalmente e o timer continua limpando-as. Se a manutencao for a causa do
incidente, parar tambem o timer:

```bash
sudo systemctl stop rhsaas-demo-pool-maintenance.timer
```

## Operacao rotineira

### Expiracao e reset

```bash
sudo -u ubuntu /opt/rhsaas/venv/bin/python \
  /opt/rhsaas/manage.py manter_pool_demo --dry-run
sudo -u ubuntu /opt/rhsaas/venv/bin/python \
  /opt/rhsaas/manage.py manter_pool_demo
```

O ciclo esperado e:

1. lease vencido e travado no schema `public`;
2. usuario desativado, sessoes/Axes/cache removidos;
3. slot marcado `expirado`;
4. reset com advisory lock;
5. schema recriado, migrations aplicadas, seed ficticio criado;
6. arquivos tenant-scoped removidos;
7. metadata anonima apagada e slot marcado `livre`.

Falha em qualquer parte do reset deixa a vaga `bloqueado`. Nunca trocar esse
estado diretamente para `livre`.

### Recuperacao de slot preso

```bash
sudo -u ubuntu /opt/rhsaas/venv/bin/python \
  /opt/rhsaas/manage.py expirar_leases_demo --slot=demoN --dry-run
sudo -u ubuntu /opt/rhsaas/venv/bin/python \
  /opt/rhsaas/manage.py resetar_tenant_demo \
  --slot=demoN --confirm="RESETAR demoN" --dry-run
```

Se o lease ja venceu, executar primeiro `manter_pool_demo --slot=demoN`. Para
um slot bloqueado, revisar banco, domain, schema, logs e artefatos; depois usar
o reset com confirmacao forte. Se a causa nao estiver entendida, manter
bloqueado e reduzir a capacidade anunciada.

### Pool cheia

A API responde `503` com `code=pool_full`, sem lista de slots. Confirmar apenas
contagens agregadas no shell administrativo e revisar se ha leases vencidos.
Nao prolongar leases nem liberar vaga ocupada para mascarar capacidade.

### Logs e health check

```bash
curl -fsS https://api-demo-rh.taquiondev.com.br/api/health/
curl -fsS https://demo1.api-demo-rh.taquiondev.com.br/api/health/
sudo journalctl -u rhsaas-demo --since "30 min ago" --no-pager
sudo journalctl -u rhsaas-demo-pool-maintenance.service \
  --since "24 hours ago" --no-pager
```

Eventos esperados: `demo_lease`, `demo_exchange`, expiracao e reset. O codigo
nao registra token de troca, senha, hash anonimo ou IP no fluxo publico.

Monitorar na VM pequena:

```bash
free -h
df -h
ps -eo pid,ppid,%mem,rss,cmd --sort=-rss | head
sudo systemctl show rhsaas-demo -p MemoryCurrent -p TasksCurrent
```

## Rollback

1. definir `DEMO_PUBLIC_LEASE_ENABLED=False`;
2. reiniciar Gunicorn;
3. parar o timer se ele estiver falhando;
4. preservar slots `bloqueado` e logs para diagnostico;
5. voltar para o artefato/release anterior aprovado;
6. somente reverter migration com plano especifico, backup e teste de restore;
7. validar health, Nginx e a demo fixa antes de reabrir.

O rollback de codigo nao autoriza apagar schemas nem restaurar toda a base
sobre outros tenants.

## Checklist de homologacao e pos-deploy

- [ ] `check --deploy` sem issues;
- [ ] migrations aplicadas em `public`, `rh_teste` e `demo1...demo10`;
- [ ] dez domains tecnicos respondendo por HTTPS;
- [ ] cookie de visitante `Secure`, `HttpOnly`, `SameSite=Lax`;
- [ ] cookies de sessao/CSRF host-only;
- [ ] pagina publica sem formulario de senha;
- [ ] clique aloca e autentica automaticamente;
- [ ] usuario nao e staff/superuser e nao acessa backups/admin/exclusoes;
- [ ] duas requisicoes concorrentes nao compartilham indevidamente um slot;
- [ ] pool cheia retorna 503 generico;
- [ ] lease expira, sessao para de funcionar e timer devolve vaga limpa;
- [ ] dado criado em `demo1` nao aparece em `demo2`;
- [ ] seed reaparece depois do reset;
- [ ] timer executa duas vezes sem erro/idempotencia;
- [ ] logs nao contem token, senha, hash, IP completo ou PII;
- [ ] RAM, swap e disco permanecem dentro do limite aprovado;
- [ ] frontend sem erros de CORS, CSRF, CSP, mixed content ou cookies;
- [ ] rollback e desativacao rapida ensaiados.
