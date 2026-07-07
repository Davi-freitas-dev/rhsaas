# Operacao manual do pool demo de tenants

Este runbook descreve como operar localmente o pool manual `demo1...demo10`
do RH SaaS. Ele cobre provisionamento, ocupacao, expiracao, reset seguro e
validacoes basicas de isolamento.

O pool demo e uma fase operacional controlada. Ele nao substitui a demo fixa
`rh_teste` e nao implementa cadastro publico automatico.

## Objetivo operacional

Permitir que um operador teste manualmente o ciclo completo de uma vaga demo:

1. criar ou garantir os tenants `demo1...demo10`;
2. ocupar uma vaga com dados de um testador;
3. expirar o lease da vaga;
4. resetar o schema do tenant demo com confirmacao forte;
5. confirmar que a vaga voltou para `livre`;
6. confirmar que `demo1` nao afeta `demo2`.

## Pre-requisitos locais

- Estar na raiz do backend RH SaaS.
- Ter o virtualenv criado e dependencias instaladas.
- Ter banco PostgreSQL local configurado para o projeto.
- Ter migrations aplicadas.
- Usar ambiente local/controlado. Nao executar este runbook diretamente em
  producao sem revisar a secao de riscos.

Comandos base em PowerShell:

```powershell
cd C:\Users\Davif\OneDrive\Desktop\Projetos\rhsaas
$env:Path = "$PWD\venv\Scripts;$env:Path"
$env:DEBUG = "True"
```

## Variaveis necessarias

O comando `ocupar_tenant_demo` cria ou ativa o usuario demo dentro do schema
correto. Para criar usuario novo, a senha inicial deve vir de variavel de
ambiente.

Use uma senha temporaria forte somente no terminal local. Nao grave a senha em
arquivo, commit, print, log ou documentacao.

```powershell
$env:DEMO_TENANT_PASSWORD = "troque-por-uma-senha-temporaria-forte"
```

## Pre-check operacional

Antes de operar o pool demo, confirme o estado do ambiente:

- [ ] `git status` limpo ou contendo apenas alteracoes esperadas.
- [ ] Banco PostgreSQL acessivel.
- [ ] Migrations aplicadas.
- [ ] `python manage.py check` executado com sucesso.
- [ ] `DEBUG=True` configurado para ambiente local.
- [ ] `DEMO_TENANT_PASSWORD` definido no terminal atual.
- [ ] Pool provisionado ou pronto para provisionamento.
- [ ] Nenhum reset em andamento.

Comandos de pre-check:

```powershell
git status --short
python manage.py check
python manage.py showmigrations tenancy
python manage.py provisionar_pool_demo --slots=2 --dry-run
```

## Ordem segura dos comandos

1. `provisionar_pool_demo`
2. `ocupar_tenant_demo`
3. validar status `ocupado`
4. expirar o lease, manualmente em local ou pelo tempo real
5. `expirar_leases_demo`
6. validar status `expirado`
7. `resetar_tenant_demo`
8. validar status `livre`
9. validar isolamento entre `demo1` e `demo2`

## Provisionar demo1...demo10

Dry-run:

```powershell
python manage.py provisionar_pool_demo --slots=10 --dry-run
```

Executar:

```powershell
python manage.py provisionar_pool_demo --slots=10
```

Para teste rapido local, pode provisionar apenas dois slots:

```powershell
python manage.py provisionar_pool_demo --slots=2
```

## Ocupar um slot

Ocupar `demo1`:

```powershell
python manage.py ocupar_tenant_demo `
  --slot=demo1 `
  --nome "Teste Demo 1" `
  --email "demo1.local@example.com" `
  --telefone "11999990000" `
  --username demo-user `
  --password-env DEMO_TENANT_PASSWORD
```

Ocupar `demo2` para validar isolamento:

```powershell
python manage.py ocupar_tenant_demo `
  --slot=demo2 `
  --nome "Teste Demo 2" `
  --email "demo2.local@example.com" `
  --telefone "11999990001" `
  --username demo-user `
  --password-env DEMO_TENANT_PASSWORD
```

O mesmo `username` pode existir nos dois tenants porque cada schema possui sua
propria tabela de usuarios.

## Validar status dos slots

```powershell
@'
from tenancy.models import DemoTenantSlot

for slot in DemoTenantSlot.objects.order_by("slot_code").values(
    "slot_code",
    "status",
    "assigned_email",
    "lease_started_at",
    "lease_expires_at",
    "last_reset_at",
):
    print(slot)
'@ | python manage.py shell
```

Depois de ocupar `demo1` e `demo2`, o esperado e:

- `demo1`: `ocupado`;
- `demo2`: `ocupado`.

## Criar dados sentinela para isolamento

Use dados simples para provar que o reset de `demo1` nao altera `demo2`.

```powershell
@'
from caixa.models import Cliente
from django_tenants.utils import schema_context

with schema_context("demo1"):
    Cliente.objects.get_or_create(
        cpf_cnpj="00.000.000/0001-01",
        defaults={"nome_razao_social": "Cliente Sentinela Demo 1"},
    )

with schema_context("demo2"):
    Cliente.objects.get_or_create(
        cpf_cnpj="00.000.000/0001-02",
        defaults={"nome_razao_social": "Cliente Sentinela Demo 2"},
    )

print("Dados sentinela criados.")
'@ | python manage.py shell
```

Validar contagens:

```powershell
@'
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from caixa.models import Cliente

User = get_user_model()
for schema in ("demo1", "demo2"):
    with schema_context(schema):
        print(
            schema,
            "usuarios=", list(User.objects.values_list("username", flat=True)),
            "clientes=", Cliente.objects.count(),
        )
'@ | python manage.py shell
```

## Expirar um slot

Em uso real, `expirar_leases_demo` atua apenas em leases vencidos. Para teste
local, force a expiracao de `demo1`:

```powershell
@'
from datetime import timedelta
from django.utils import timezone
from tenancy.models import DemoTenantSlot

slot = DemoTenantSlot.objects.get(slot_code="demo1")
slot.lease_expires_at = timezone.now() - timedelta(minutes=1)
slot.save(update_fields=["lease_expires_at", "updated_at"])
print(slot.slot_code, slot.status, slot.lease_expires_at)
'@ | python manage.py shell
```

Dry-run:

```powershell
python manage.py expirar_leases_demo --slot=demo1 --username demo-user --dry-run
```

Executar:

```powershell
python manage.py expirar_leases_demo --slot=demo1 --username demo-user
```

Validar status:

```powershell
@'
from tenancy.models import DemoTenantSlot

print(DemoTenantSlot.objects.get(slot_code="demo1").status)
print(DemoTenantSlot.objects.get(slot_code="demo2").status)
'@ | python manage.py shell
```

Esperado:

- `demo1`: `expirado`;
- `demo2`: `ocupado`.

## Resetar um slot com confirmacao forte

O reset e destrutivo para o schema do tenant demo selecionado. Ele:

- recusa `public`;
- recusa `rh_teste`;
- recusa qualquer schema fora de `demo1...demo10`;
- exige confirmacao literal no formato `RESETAR demoN`;
- recusa slot `ocupado`;
- permite apenas slot `expirado` ou `bloqueado`;
- dropa e recria somente o schema validado;
- limpa artefatos locais tenant-scoped derivados internamente de
  `BASE_DIR/backups/tenants/demoN`;
- nao apaga `Tenant`, `Domain` nem `DemoTenantSlot` publicos.

Dry-run:

```powershell
python manage.py resetar_tenant_demo --slot=demo1 --confirm "RESETAR demo1" --dry-run
```

Executar:

```powershell
python manage.py resetar_tenant_demo --slot=demo1 --confirm "RESETAR demo1"
```

Validar que voltou para livre:

```powershell
@'
from tenancy.models import DemoTenantSlot

slot = DemoTenantSlot.objects.get(slot_code="demo1")
print({
    "slot_code": slot.slot_code,
    "status": slot.status,
    "assigned_email": slot.assigned_email,
    "lease_started_at": slot.lease_started_at,
    "lease_expires_at": slot.lease_expires_at,
    "last_reset_at": slot.last_reset_at,
})
'@ | python manage.py shell
```

Esperado:

- `status`: `livre`;
- dados do testador vazios;
- lease limpo;
- `last_reset_at` preenchido.

## Validar isolamento demo1 x demo2 apos reset

Depois de resetar `demo1`, valide usuarios e dados:

```powershell
@'
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from caixa.models import Cliente

User = get_user_model()
for schema in ("demo1", "demo2"):
    with schema_context(schema):
        print(
            schema,
            "usuarios=", list(User.objects.values_list("username", flat=True)),
            "clientes=", Cliente.objects.count(),
        )
'@ | python manage.py shell
```

Esperado:

- `demo1`: usuario demo removido e `Cliente` zerado;
- `demo2`: usuario demo e dados sentinela preservados.

## Alertas de seguranca sobre resetar_tenant_demo

- Nunca rode reset em `rh_teste`.
- Nunca rode reset em `public`.
- Nunca tente adaptar o comando para aceitar schema livre.
- Nunca use `tenant.delete(force_drop=True)` como operacao manual do pool.
- Nunca remova a confirmacao forte `--confirm "RESETAR demoN"`.
- Nunca passe caminho de arquivo para reset; o comando deve derivar o diretorio
  tenant-scoped somente a partir do schema demo validado.
- Nunca compartilhe senha temporaria em commit, issue, log ou print.
- Nao execute reset enquanto um testador ainda estiver usando o slot.
- Se o reset falhar, o slot deve ficar `bloqueado`; revise antes de liberar.

## O que NAO fazer

- Nao usar `demo1` para dados reais.
- Nao usar o pool demo como ambiente comercial.
- Nao apontar `api-demo-rh.taquiondev.com.br` para outro tenant por engano.
- Nao rodar comandos do pool por tela publica ou endpoint HTTP.
- Nao criar automacao publica antes de validar reset, limites e isolamento.
- Nao commitar secrets, senhas temporarias ou outputs com dados pessoais.
- Nao executar os comandos em producao sem backup e janela operacional definida.

## Riscos restantes antes de producao

- O reset limpa artefatos locais em `BASE_DIR/backups/tenants/demoN`, mas nao
  cobre storage externo, buckets ou anexos futuros fora desse padrao.
- Nao ha rotina agendada oficial para expirar e resetar tenants.
- Nao ha tela publica de cadastro nem distribuicao automatica de vagas.
- Nao ha limite operacional automatizado de 50 MB por tenant.
- DNS wildcard, Nginx wildcard e TLS wildcard ainda precisam ser validados.
- O frontend ainda nao seleciona automaticamente a API tecnica
  `demoN.api-demo-rh.taquiondev.com.br`.
- Logs e monitoramento do fluxo operacional ainda devem ser revisados em
  ambiente de servidor.

## Rollback operacional

Se qualquer etapa falhar, nao improvise liberando vaga manualmente. Primeiro
preserve o estado, revise logs e identifique a causa.

### Se provisionar_pool_demo falhar

- Verifique se o banco esta acessivel.
- Verifique migrations do app `tenancy`.
- Verifique se ja existe `Tenant`, `Domain` ou `DemoTenantSlot` conflitante.
- Rode novamente com `--dry-run` apos entender o conflito.
- Nao apague tenants ou domains manualmente sem confirmar o impacto.

### Se ocupar_tenant_demo falhar

- Verifique o status do `DemoTenantSlot`.
- Confirme se o slot esta `livre`.
- Confirme se o `Domain` tecnico aponta para o tenant correto.
- Confirme se `DEMO_TENANT_PASSWORD` esta definido.
- Nao reutilize senha temporaria em logs ou arquivos.

### Se expirar_leases_demo falhar

- Revise `lease_expires_at` do slot.
- Confirme se o slot esta `ocupado`.
- Confirme se o usuario demo existe no schema correto.
- Rode com `--dry-run` para validar quais leases seriam expirados.
- Nao altere o status para `expirado` manualmente antes de entender a falha.

### Se resetar_tenant_demo falhar

- Nunca marque manualmente o slot como `livre` apos falha.
- Mantenha o slot `bloqueado`.
- Revise logs do comando, banco e aplicacao.
- Confirme `Tenant`, `Domain` e `DemoTenantSlot`.
- Confirme se o schema existe ou se ficou ausente apos tentativa de reset.
- Identifique e corrija a causa antes de repetir a operacao.
- Repita somente com a confirmacao forte correta:
  `--confirm "RESETAR demoN"`.
- Nunca contorne guards, validacoes ou confirmacoes destrutivas.

## Observacoes finais

O comando `resetar_tenant_demo` limpa o schema do tenant demo e remove
artefatos locais em `BASE_DIR/backups/tenants/demoN`. Ele nao recebe caminho de
arquivo do operador; o caminho e derivado internamente do schema demo validado.
Se no futuro houver storage externo, bucket, anexos ou outra arvore de arquivos,
essa limpeza precisara ser expandida e testada em fase separada.

DNS, Nginx e frontend ainda nao fazem distribuicao publica automatica entre
`demo1...demo10`. Nesta fase, a operacao do pool continua manual e restrita a
operador.
