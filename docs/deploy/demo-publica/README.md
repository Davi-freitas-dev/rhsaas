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
- tenant permanente: `demo1`, sem `DemoTenantSlot`, lease, expiracao ou reset
  automatico;
- vagas isoladas temporarias: `demo2...demo10`;
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
4. nove vagas temporarias (`demo2...demo10`) e o tenant permanente `demo1`
   aprovados no planejamento de capacidade;
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

Manter a cota anonima por rede explicita:

```env
DEMO_MAX_ACTIVE_LEASES_PER_NETWORK=2
DRF_THROTTLE_DEMO_LEASE_RATE=3/hour
DRF_THROTTLE_DEMO_LEASE_RESUME_RATE=10/hour
```

O cookie assinado reutiliza o lease no mesmo navegador. Visitantes distintos
da mesma rede recebem tenants distintos ate a cota; o terceiro recebe
`code=network_limit`. O banco armazena somente HMAC de visitante/rede, nunca IP
puro. O hash deixa de contar assim que o lease expira e e removido no reset.
Novas alocacoes usam a cota por IP/rede; retomadas reconhecidas pelo cookie e
por um lease ainda ativo usam a cota separada por HMAC do visitante.

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
4. Validar `demo1` permanente e provisionar nove slots (`demo2...demo10`).
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
/opt/rhsaas/venv/bin/python manage.py preparar_demo_permanente --dry-run
/opt/rhsaas/venv/bin/python manage.py manter_pool_demo --dry-run
/opt/rhsaas/venv/bin/python manage.py shell -c \
  "from tenancy.models import DemoTenantSlot; print(list(DemoTenantSlot.objects.order_by('slot_code').values_list('slot_code', flat=True)))"
```

O provisionamento cria Tenant/Domain para `demo1...demo10`, mas cria
`DemoTenantSlot` somente para `demo2...demo10`. A migration `tenancy.0004`
remove apenas a linha de pool antiga de `demo1`, sem apagar schema, Domain,
dados ou usuario. A ultima consulta deve listar exatamente `demo2` ate
`demo10`, sem `demo1`.

`preparar_demo_permanente` preserva a senha utilizavel do usuario existente,
reaplica flags/grupo minimos e garante o seed idempotente. Se o dry-run
informar `usuario_pronto=sim`, concluir com:

```bash
/opt/rhsaas/venv/bin/python manage.py preparar_demo_permanente
```

Se o dry-run informar `usuario_pronto=nao`, carregar a credencial a partir do
secret manager em uma variavel de ambiente temporaria e concluir com:

```bash
/opt/rhsaas/venv/bin/python manage.py preparar_demo_permanente \
  --password-env=DEMO_PERMANENT_PASSWORD
unset DEMO_PERMANENT_PASSWORD
```

Nunca colocar o valor da senha na linha de comando, no Git, no historico do
shell ou no runbook.

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

Todo o ciclo acima e restrito por configuracao a `demo2...demo10`. `demo1` nao
possui slot, nao e varrido e `manter_pool_demo --slot=demo1` apenas informa que
o tenant permanente foi ignorado.

Falha em qualquer parte do reset deixa a vaga `bloqueado`. Nunca trocar esse
estado diretamente para `livre`.

### Recuperacao de slot preso

Esta rotina aceita somente vagas temporarias `demo2...demo10`; para `demo1`,
usar `preparar_demo_permanente` e nunca os comandos de lease/reset da pool.

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

A API responde `503` com `code=pool_full`, sem lista de slots. O frontend passa
a oferecer `Experimentar demo permanente`, que navega para `?tenant=demo1` sem
novo lease. Confirmar apenas contagens agregadas da pool `demo2...demo10` no
shell administrativo e revisar se ha leases vencidos. Nao prolongar leases nem
liberar vaga ocupada para mascarar capacidade.

### Retomada depois do logout

O logout encerra a sessao do tenant e remove o lease do armazenamento local,
mas nao libera a vaga nem apaga o cookie `HttpOnly` do host publico. Um novo
clique em `Acessar demo` chama o mesmo endpoint e deve retornar `reused=true`,
o mesmo `apiBaseUrl` e o mesmo `expiresAt`, emitindo somente outro token de
exchange para recriar a sessao.

O DRF separa a cota de nova alocacao (`demo_lease`) da cota de retomada
(`demo_lease_resume`). Nao limpar Redis, prolongar o lease ou aumentar o limite
global para corrigir uma retomada. Se o detalhe 429 contiver tempo de espera,
confirmar a configuracao implantada e distinguir o `Retry-After` do DRF de um
429 HTML do Nginx. O Nginx continua protegendo a rota antes da aplicacao.

### Limite de rede

A API responde `429` com `code=network_limit` quando a rede ja possui a
quantidade configurada de leases ativos. Isso e diferente de pool cheia: nao
resetar nem liberar slots. Orientar o visitante a reutilizar o navegador
original ou aguardar a expiracao. Para diagnostico, consultar somente contagens
agregadas por `network_key_hash`; nao imprimir hash, IP, cookie ou token.

### Logs e health check

```bash
curl -fsS https://api-demo-rh.taquiondev.com.br/api/health/
curl -fsS https://demo1.api-demo-rh.taquiondev.com.br/api/health/
sudo journalctl -u rhsaas-demo --since "30 min ago" --no-pager
sudo journalctl -u rhsaas-demo-pool-maintenance.service \
  --since "24 hours ago" --no-pager
```

Eventos esperados: `demo_lease` (`granted` com `reused=true/false`,
`resume_unavailable`, `network_limit` ou `pool_full`),
`demo_exchange`, expiracao e reset. O codigo
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

Nao recriar `DemoTenantSlot` para `demo1` durante rollback. Um release antigo
que volte a assumir `demo1...demo10` deve permanecer com a entrada publica
desligada ate receber a mesma exclusao central ou ser substituido pelo release
corrigido.

O rollback de codigo nao autoriza apagar schemas nem restaurar toda a base
sobre outros tenants.

## Checklist de homologacao e pos-deploy

- [ ] `check --deploy` sem issues;
- [ ] migrations aplicadas em `public`, `rh_teste` e `demo1...demo10`;
- [ ] `tenancy.0004` removeu somente o `DemoTenantSlot` de `demo1`;
- [ ] `demo1` preserva schema, Domain, dados, usuario e grupo minimo;
- [ ] `demo1` nao aparece entre slots livres/ocupados/expirados;
- [ ] pool publica contem somente `demo2...demo10`;
- [ ] dez domains tecnicos respondendo por HTTPS;
- [ ] cookie de visitante `Secure`, `HttpOnly`, `SameSite=Lax`;
- [ ] cookies de sessao/CSRF host-only;
- [ ] pagina publica sem formulario de senha;
- [ ] clique aloca e autentica automaticamente;
- [ ] usuario nao e staff/superuser e nao acessa backups/admin/exclusoes;
- [ ] duas requisicoes concorrentes nao compartilham indevidamente um slot;
- [ ] mesmo cookie reutiliza o slot; dois cookies da mesma rede ficam isolados;
- [ ] logout seguido de entrada imediata retorna o mesmo tenant e `expiresAt`;
- [ ] retomada imediata nao e bloqueada pela cota de novas alocacoes;
- [ ] visitante novo continua sujeito a `demo_lease` e retomadas abusivas a `demo_lease_resume`;
- [ ] terceiro visitante da mesma rede recebe 429 `network_limit` sem novo slot;
- [ ] pool cheia retorna 503 generico;
- [ ] lease expira, sessao para de funcionar e timer devolve vaga limpa;
- [ ] dado permanente de `demo1` nao aparece em `demo2` e vice-versa;
- [ ] pool cheia oferece fallback `?tenant=demo1` sem chamar novo lease;
- [ ] seed reaparece depois do reset;
- [ ] timer executa duas vezes sem erro/idempotencia;
- [ ] logs nao contem token, senha, hash, IP completo ou PII;
- [ ] RAM, swap e disco permanecem dentro do limite aprovado;
- [ ] frontend sem erros de CORS, CSRF, CSP, mixed content ou cookies;
- [ ] rollback e desativacao rapida ensaiados.
