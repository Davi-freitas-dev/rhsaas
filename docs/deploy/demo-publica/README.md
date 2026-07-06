# Deploy da demo publica RH SaaS

Este pacote transforma o plano aprovado em templates operacionais para a demo
publica do RH SaaS.

## Dominios

- Frontend: `https://demo-rh.taquiondev.com.br`
- Backend/API: `https://api-demo-rh.taquiondev.com.br/api`
- Tenant fixo: `rh_teste`
- Domain do tenant: `api-demo-rh.taquiondev.com.br`

O `Domain` do `django-tenants` nao recebe `/api`; ele deve conter apenas o host.

## Escopo da demo fixa

A demo publica inicial usa apenas o tenant fixo `rh_teste`. Ela e recomendada
para teste controlado, preferencialmente com 1 testador por vez.

Varios usuarios simultaneos podem acessar a demo, mas eles compartilham os
mesmos dados do tenant `rh_teste`. O isolamento multi-tenant ja existe no
backend, porem esta primeira demo publica aponta para um unico tenant.

Para varios testadores isolados, a fase futura e criar um pool de tenants
`demo1`...`demo10`, com lease temporario e reset automatico de dados.

## DNS na Hostinger

Na zona DNS de `taquiondev.com.br`:

```txt
Tipo   Nome          Valor
A      api-demo-rh   IP_PUBLICO_DA_ORACLE
CNAME  demo-rh       VALOR_EXATO_INFORMADO_PELA_VERCEL
```

O valor do CNAME de `demo-rh` deve ser copiado do painel da Vercel depois que
`demo-rh.taquiondev.com.br` for adicionado ao projeto.

## Backend

Use este arquivo como base do `.env` no servidor:

```bash
cp docs/deploy/demo-publica/.env.production.example .env
```

Antes de iniciar o servico, trocar os placeholders:

- `GERAR_CHAVE_FORTE_UNICA_PARA_A_DEMO`
- `SENHA_FORTE_DO_BANCO`

HSTS comeca conservador para a primeira publicacao:

```env
SECURE_HSTS_SECONDS=300
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
```

Depois de validar HTTPS, DNS, cookies e redirects em producao, aumentar para:

```env
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
```

## Vercel

Configurar no ambiente `Production` do projeto Next.js:

```env
NEXT_PUBLIC_API_BASE_URL=https://api-demo-rh.taquiondev.com.br/api
NEXT_PUBLIC_API_MOCK_FALLBACK=false
NEXT_PUBLIC_API_TIMEOUT_MS=12000
```

## Garantir Domain do tenant

Depois das migrations do schema `public` e depois de confirmar que o tenant
`rh_teste` existe:

```bash
python manage.py shell --no-imports < docs/deploy/demo-publica/garantir_domain_rh_teste.py
```

O script e idempotente. Ele atualiza/cria:

```txt
domain=api-demo-rh.taquiondev.com.br
tenant=rh_teste
is_primary=True
```

Se o dominio ja pertencer a outro tenant, o script falha explicitamente.

## Nginx

Template:

```txt
docs/deploy/demo-publica/nginx-api-demo-rh.conf
```

Destino sugerido no servidor:

```bash
sudo cp docs/deploy/demo-publica/nginx-api-demo-rh.conf /etc/nginx/sites-available/rhsaas-demo
sudo ln -s /etc/nginx/sites-available/rhsaas-demo /etc/nginx/sites-enabled/rhsaas-demo
sudo nginx -t
```

Emitir certificado para:

```bash
sudo certbot --nginx -d api-demo-rh.taquiondev.com.br
```

## systemd/Gunicorn

Template:

```txt
docs/deploy/demo-publica/rhsaas-demo.service
```

Destino sugerido no servidor:

```bash
sudo cp docs/deploy/demo-publica/rhsaas-demo.service /etc/systemd/system/rhsaas-demo.service
sudo systemctl daemon-reload
sudo systemctl enable rhsaas-demo
sudo systemctl restart rhsaas-demo
sudo systemctl status rhsaas-demo
```

## Ordem segura

1. Criar VM Oracle e liberar portas `80` e `443`.
2. Instalar Python, PostgreSQL, Redis, Nginx, Certbot e dependencias do sistema.
3. Criar banco e usuario PostgreSQL.
4. Clonar backend em `/opt/rhsaas`.
5. Criar `venv` e instalar `requirements.txt`.
6. Criar `.env` a partir de `.env.production.example` da demo.
7. Rodar `python manage.py migrate_schemas --shared`.
8. Garantir que o tenant `rh_teste` existe.
9. Rodar `python manage.py shell --no-imports < docs/deploy/demo-publica/garantir_domain_rh_teste.py`.
10. Rodar `python manage.py migrate_schemas --schema=rh_teste`.
11. Criar usuario e dados demo dentro do schema `rh_teste`.
12. Rodar `python manage.py collectstatic --noinput`.
13. Rodar `python manage.py check --deploy`.
14. Instalar e iniciar `rhsaas-demo.service`.
15. Instalar Nginx site e emitir SSL.
16. Apontar DNS `api-demo-rh` para o IP publico da Oracle.
17. Adicionar `demo-rh.taquiondev.com.br` na Vercel.
18. Apontar CNAME `demo-rh` na Hostinger para o valor informado pela Vercel.
19. Configurar variaveis Production na Vercel.
20. Fazer deploy do frontend na Vercel.
21. Executar checklist publico.

## Checklist publico

DNS:

```bash
dig +short api-demo-rh.taquiondev.com.br
dig +short demo-rh.taquiondev.com.br
```

Backend:

```bash
curl -I https://api-demo-rh.taquiondev.com.br/
curl -i https://api-demo-rh.taquiondev.com.br/api/auth/csrf/
curl -i -H "Origin: https://demo-rh.taquiondev.com.br" https://api-demo-rh.taquiondev.com.br/api/auth/csrf/
```

Validacoes no navegador:

- `https://demo-rh.taquiondev.com.br` abre o frontend.
- O frontend chama `https://api-demo-rh.taquiondev.com.br/api`.
- Login demo funciona.
- `/api/auth/session/` retorna usuario autenticado depois do login.
- Cookies de sessao e CSRF aparecem como `Secure`, `HttpOnly` e `SameSite=Lax`.
- Console sem erros de CORS, CSRF, mixed content ou cookie bloqueado.
- API resolve o tenant `rh_teste` pelo host `api-demo-rh.taquiondev.com.br`.
- Logout encerra a sessao.
- `python manage.py check --deploy` passa no servidor.
