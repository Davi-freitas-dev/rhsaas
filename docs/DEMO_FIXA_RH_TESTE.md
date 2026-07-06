# Demo fixa com tenant rh_teste

Este roteiro prepara a demo local simples antes do pool de tenants demo.
O pool `demo1...demo10` fica para uma fase posterior.

## Backend

Tenant esperado:

```txt
schema: rh_teste
domain principal local: localhost
domain tecnico opcional: rh-teste.localhost
api: http://localhost:8000/api
```

Variaveis locais esperadas:

```env
DEBUG=True
ALLOWED_HOSTS=.localhost,localhost,127.0.0.1,rh-teste.localhost
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://localhost:3000,http://127.0.0.1:3000,http://rh-teste.localhost,http://rh-teste.localhost:3000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://rh-teste.localhost:3000
CORS_ALLOW_CREDENTIALS=True
SESSION_COOKIE_DOMAIN=
CSRF_COOKIE_DOMAIN=
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False
```

Se o terminal ou o sistema tiver `DEBUG=release`, o Django recusara iniciar.
Para a demo local, remova essa variavel do ambiente ou sobrescreva apenas na
sessao atual:

```powershell
$env:DEBUG = "True"
```

## Frontend

No projeto `rhsaasfront`, configure `.env.local` sem versionar secrets:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_API_TIMEOUT_MS=12000
NEXT_PUBLIC_API_MOCK_FALLBACK=false
```

O frontend deve continuar em:

```txt
http://localhost:3000
```

Para a demo fixa, o dominio `localhost` deve estar cadastrado no `public` como
um `Domain` apontando para o tenant `rh_teste`. Assim o usuario testa frontend e
backend em localhost, enquanto o isolamento por schema continua sendo resolvido
pelo `Host` do django-tenants.

## Usuario demo

O usuario demo deve existir apenas localmente dentro do schema `rh_teste`.
A senha nao deve ser gravada em arquivo versionado.

## Validacao minima

```powershell
$env:DEBUG = "True"
.\venv\Scripts\python.exe manage.py check
```

No frontend:

```powershell
cd ..\rhsaasfront
corepack pnpm run lint
corepack pnpm run typecheck
corepack pnpm test:e2e tests/e2e/rh-teste-demo.spec.ts
```
