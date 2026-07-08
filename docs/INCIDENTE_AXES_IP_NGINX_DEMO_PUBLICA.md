# Incidente: lock de login por IP no demo1

Data: 2026-07-08

Status: diagnosticado e destravado manualmente.

Escopo: demo publica do RH SaaS, tenant `demo1`, endpoint
`/api/auth/login/`.

## Resumo

O login pelo frontend publico retornava HTTP 429 com a mensagem:

```text
Account locked: too many login attempts. Please try again later.
```

O usuario `demo` existia no tenant `demo1`, estava ativo e a senha validava
corretamente com `check_password`. O problema nao era senha incorreta nem
tenant ausente.

A causa confirmada foi lock do `django-axes` por IP dentro do schema `demo1`.
Todas as tentativas estavam sendo registradas com `ip_address=127.0.0.1`,
porque a aplicacao Django esta atras do Nginx/Gunicorn e o Axes estava lendo o
IP da conexao interna, nao o IP real do cliente.

## Evidencia observada

O estado do Axes mostrou tentativas somente no schema `demo1`:

```text
schema: demo1
ip_address: 127.0.0.1
failures_since_start total por IP: 8
```

Os schemas `public`, `rh_teste` e `demo2` nao tinham registros equivalentes.

O desbloqueio operacional foi feito com:

```bash
python manage.py tenant_command axes_reset_ip --schema=demo1 127.0.0.1
```

Apos o reset, a consulta a `AccessAttempt.objects.values()` no schema `demo1`
retornou vazia.

## Causa raiz

O `django-axes` usa o endereco de IP da requisicao para aplicar lockouts. Em
ambiente com Nginx na frente do Gunicorn, o `REMOTE_ADDR` visto pelo Django
pode ser `127.0.0.1`, que e o endereco local do proxy para a aplicacao.

Com isso, varias tentativas de usuarios diferentes foram somadas no mesmo IP
interno. Como a configuracao atual inclui `ip_address` nos parametros de
lockout, o IP `127.0.0.1` passou a bloquear novas tentativas no tenant
afetado.

Na pratica, isso cria um falso positivo: o Axes protegeu o login, mas tratou
todos os acessos proxied como se viessem do mesmo cliente.

## Impacto

- Login do tenant `demo1` ficou bloqueado mesmo com usuario e senha corretos.
- Tentativas com usuarios diferentes contribuiram para o mesmo lock por IP.
- O problema afeta a experiencia da demo publica quando muitos acessos passam
  pelo mesmo proxy local.
- O incidente ficou restrito ao schema `demo1` nos dados observados.

## Comandos de diagnostico

Inspecionar tentativas recentes por schema:

```bash
python manage.py shell --no-imports <<'PY'
from datetime import timedelta
from django.db.models import Sum
from django.utils import timezone
from django_tenants.utils import schema_context
from axes.models import AccessAttempt

schemas = ["public", "rh_teste", "demo1", "demo2"]
threshold = timezone.now() - timedelta(hours=2)

for schema in schemas:
    print("\n==", schema, "==")
    with schema_context(schema):
        print("ROWS:", list(
            AccessAttempt.objects
            .filter(attempt_time__gte=threshold)
            .order_by("-attempt_time")
            .values(
                "id",
                "username",
                "ip_address",
                "path_info",
                "failures_since_start",
                "attempt_time",
            )[:30]
        ))
        print("POR IP:", list(
            AccessAttempt.objects
            .filter(attempt_time__gte=threshold)
            .values("ip_address")
            .annotate(total=Sum("failures_since_start"))
            .order_by("-total")[:20]
        ))
PY
```

Confirmar usuario no schema correto:

```bash
python manage.py shell --no-imports <<'PY'
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context

with schema_context("demo1"):
    User = get_user_model()
    print(list(User.objects.values("username", "email", "is_active")))
PY
```

## Plano de correcao definitiva

A correcao recomendada e fazer o Axes identificar o IP real do cliente atras do
Nginx sem confiar cegamente em headers enviados pelo navegador.

1. Garantir no Nginx headers controlados pelo proxy:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
```

2. Criar uma funcao pequena para o `django-axes` obter o IP real somente quando
   `REMOTE_ADDR` for um proxy confiavel, por exemplo `127.0.0.1` ou `::1`.

3. Validar o IP com a biblioteca padrao `ipaddress`.

4. Se o request nao vier de proxy confiavel ou o header for invalido, cair para
   `REMOTE_ADDR`.

5. Configurar o Axes para usar essa funcao via `AXES_CLIENT_IP_CALLABLE`.

6. Reavaliar `AXES_LOCKOUT_PARAMETERS`. Para demo publica, a configuracao mais
   segura contra bloqueio coletivo tende a ser lock por combinacao de usuario e
   IP, por exemplo `[[ "username", "ip_address" ]]`, mantendo rate limits de
   Nginx e DRF para abuso geral por IP.

7. Manter reset schema-scoped para incidentes:

```bash
python manage.py tenant_command axes_reset_ip --schema=demo1 <ip-real>
```

Nao desabilitar o Axes como solucao definitiva.

## Riscos para demos publicas

- Um unico visitante pode causar lock temporario para outros se todos forem
  vistos como `127.0.0.1`.
- Usuarios em uma mesma rede compartilhada podem bloquear uns aos outros se o
  lock continuar amplo demais por IP.
- Se a aplicacao confiar em `X-Forwarded-For` sem validar proxy confiavel, um
  atacante pode forjar IPs e burlar ou poluir os limites.
- Logs de Axes passam a conter IP real do cliente; isso exige cuidado com
  retencao e compartilhamento de logs.
- Rate limit de Nginx, throttle DRF e Axes precisam trabalhar juntos; nenhum
  deles substitui os outros.

## Estrategia de testes

### Testes unitarios

- Request com `REMOTE_ADDR=127.0.0.1` e `X-Real-IP` valido deve retornar o IP
  real.
- Request com `REMOTE_ADDR` nao confiavel deve ignorar `X-Real-IP` forjado.
- Header invalido deve cair para `REMOTE_ADDR`.
- Lista `X-Forwarded-For` com varios valores deve ter comportamento
  deterministico e seguro.

### Testes de integracao

- Uma falha de login em `demo1` deve gravar o IP real, nao `127.0.0.1`.
- Falhas em `demo1` nao devem criar tentativas em `demo2`.
- Falhas de varios usernames no mesmo IP nao devem bloquear todos os usuarios
  se a politica for alterada para combinacao username + IP.
- O mesmo username, no mesmo IP, deve bloquear ao atingir o limite.
- Login correto deve limpar tentativas quando `AXES_RESET_ON_SUCCESS=True`.

### Validacao operacional

1. Aplicar a correcao em ambiente controlado.
2. Fazer uma tentativa errada planejada em `demo1`.
3. Inspecionar `axes_accessattempt` no schema `demo1`.
4. Confirmar que `ip_address` e o IP real esperado.
5. Fazer login correto com o usuario demo.
6. Confirmar ausencia de regressao em CSRF, CORS, cookies e sessoes.

## Criterio de aceite

O incidente so deve ser considerado corrigido definitivamente quando:

- o Axes registrar IP real do cliente atras do Nginx;
- headers forjados pelo cliente nao forem aceitos fora de proxy confiavel;
- `demo1` e `demo2` mantiverem isolamento de tentativas;
- login correto voltar a funcionar apos reset do lock;
- a politica de lock reduzir o risco de bloqueio coletivo em demo publica.

