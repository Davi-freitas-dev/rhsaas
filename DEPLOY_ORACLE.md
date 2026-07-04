# Deploy no Oracle Cloud

Checklist para publicar depois do `git pull` no servidor.

Para janelas da arquitetura financeira premium/canonical-first, este checklist deve ser usado junto com `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md`, secao `Plano mestre para conclusao da arquitetura premium`. A etapa PM-02 define a baseline versionada, backup e validacoes de ambiente real antes de qualquer ampliacao de origem.

## 1. Preparar o ambiente

```bash
cd /caminho/do/projeto/controledecaixa
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Criar o `.env`

```bash
cp .env.production.example .env
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

Edite o `.env` e ajuste:

```text
SECRET_KEY
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
DATABASE_URL
EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL
```

Para frontend e backend em subdominios do mesmo dominio principal, como
`app.rhremoto.com` e `api.rhremoto.com`, configure tambem:

```text
SESSION_COOKIE_DOMAIN=.rhremoto.com
CSRF_COOKIE_DOMAIN=.rhremoto.com
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

Essas variaveis so funcionam porque o `settings.py` le
`SESSION_COOKIE_DOMAIN` e `CSRF_COOKIE_DOMAIN`. Em desenvolvimento local,
deixe esses campos vazios.

Se ainda nao tiver dominio/HTTPS, use temporariamente:

```text
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_PROXY_SSL_HEADER=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
```

Depois que configurar HTTPS no Nginx, volte esses valores para `True`.

## 2.1. Cache em producao

O `.env.production.example` usa Redis:

```text
CACHE_BACKEND=django.core.cache.backends.redis.RedisCache
CACHE_LOCATION=redis://127.0.0.1:6379/1
```

Esse backend e o Redis nativo do Django. O projeto tambem declara
`django-redis` e `redis` em `requirements.txt`, entao o deploy instala o cliente
Redis junto do restante das dependencias.

Instale e habilite Redis no servidor:

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl restart redis-server
redis-cli ping
```

O retorno esperado do `redis-cli ping` e `PONG`.

Depois de ajustar o `.env`, valide o cache pelo Django:

```bash
python manage.py shell --no-imports -c "from django.core.cache import cache; cache.set('deploy-cache-check', 'ok', 30); print(cache.get('deploy-cache-check'))"
```

O retorno esperado e `ok`.

O `--no-imports` evita mensagens de autoimport do shell sobre models historicos
e deixa o teste de cache mais limpo. Para comandos `manage.py`, use o `python`
do `venv`; nao use `/usr/bin/python` diretamente se o ambiente virtual estiver
ativo.

## 2.2. Snapshot PM-02 antes de ampliar canonical-first

Antes de ampliar qualquer origem em `CANONICAL_FIRST_SETTLEMENT_SOURCES`, gere
um snapshot somente leitura da baseline PM-02:

```bash
python manage.py gerar_snapshot_baseline_financeira --json
```

Esse comando registra commit atual do backend, estado do git, dados do frontend
quando o caminho existir no workspace, canonical-first, cache, cookies, banco
sem senha e a lista dos comandos PM-02 que devem ser repetidos no servidor. Ele
nao substitui backup do banco nem tag/referencia do codigo.
Para guardar o snapshot como evidencia no servidor, use
`--salvar-json=pm02-snapshot.json`; o caminho tambem aparece em
`evidenceFiles.json` no payload salvo.

Se o frontend estiver em outro caminho no servidor, informe explicitamente:

```bash
python manage.py gerar_snapshot_baseline_financeira --json --frontend-path=/caminho/do/frontend
```

Se o frontend estiver apenas na Vercel, registre a referencia do deploy:

```bash
python manage.py gerar_snapshot_baseline_financeira --json --frontend-ref=<commit-ou-deploy-vercel>
python manage.py validar_baseline_pm02 --falhar --json --frontend-ref=<commit-ou-deploy-vercel>
```

Para rodar a baseline PM-02 completa em um unico relatorio, use:

```bash
python manage.py validar_baseline_pm02 --falhar --json
```

`ready=true` nesse comando significa que as validacoes automaticas passaram; o
relatorio humano tambem chama isso de baseline automatica aprovada. A PM-02 so
fecha depois de registrar tambem tag/referencia publicada, backup real do banco,
snapshot das variaveis de ambiente e resultados no plano mestre.
O proprio relatorio inclui comandos sugeridos para essas confirmacoes manuais,
incluindo `python manage.py backup_banco_mensal --force --manter 12`. O JSON
tambem publica `pm02StrictServerCommand` e `strictServerCommand` para evitar
divergencia entre documentacao e comando realmente usado na janela. Use
`manualEvidenceComplete=true` como confirmacao de que release, backup,
referencia do frontend, nome do ambiente e snapshot foram informados no
relatorio; ainda assim, registre o resultado no plano mestre antes de marcar a
PM-02 como concluida.
Quando `--backup-ref` for um caminho de arquivo local, acrescente
`--exigir-backup-arquivo-existente` para reprovar a PM-02 se o arquivo nao
existir. Se o backup for um ID externo ou objeto de storage, mantenha apenas a
referencia textual e registre a evidencia manualmente.
Quando `--release-ref` for tag ou commit presente no checkout do backend,
acrescente `--exigir-release-git-ref-existente` para reprovar a janela se a
referencia nao existir no git local. Se a referencia for um ID externo de
deploy, mantenha apenas `--release-ref` e registre a evidencia manualmente.
Quando a evidencia do frontend for `--frontend-deploy-url`, acrescente
`--exigir-frontend-deploy-url-https` para garantir que a URL publicada seja
HTTPS.
O campo `strictServerCommandResolved` mostra o comando estrito preenchido com os
valores informados, incluindo as expectativas `--esperar-*` quando usadas, e
`executionRecord.markdown` gera um bloco de registro para colar no plano mestre
apos as revisoes. O campo `pm02ClosureReady=true` e o
resumo final de que validacoes automaticas, evidencias manuais e flags estritas
do servidor, incluindo `--falhar`, estao completas; ele ainda precisa ser acompanhado das revisoes
semantica, tecnica e extra previstas no plano mestre. Se
`pm02ClosureReady=false`, consulte `pm02ClosureBlockers` para ver exatamente
qual validacao, evidencia ou flag estrita ainda esta pendente.
Para preservar a evidencia da janela em arquivos no servidor, acrescente
`--salvar-json=pm02-baseline.json --salvar-registro=pm02-registro.md
--salvar-snapshot-json=pm02-snapshot.json` ao
comando estrito executado. Quando essas opcoes forem usadas, elas tambem entram
em `strictServerCommandResolved`, `evidenceFiles` e no
`executionRecord.markdown`.
Como atalho, use `--diretorio-evidencias=<diretorio>` para salvar esses tres
arquivos com nomes padronizados dentro do diretorio informado.
Quando esse atalho for usado, o JSON tambem publica o caminho base em
`evidenceFiles.directory`, e o registro markdown mostra `diretorio=<diretorio>`
na linha `Arquivos salvos`.
O caminho deve ser um diretorio novo ou existente; se apontar para um arquivo, a
baseline reprova antes de gravar os artefatos.
Para reprovar a janela quando os caminhos de evidencia nao forem informados,
adicione `--exigir-arquivos-evidencia`; combine com
`--diretorio-evidencias=<diretorio>` para preencher tudo de uma vez.
Quando `--diretorio-evidencias` for usado, `strictServerCommandResolved`
preserva essa flag e tambem mostra os tres caminhos expandidos de evidencia.
O JSON tambem publica `pm02NextAction`, com a proxima acao recomendada para a
janela antes de tentar fechar PM-02. Quando a acao exigir comando operacional,
consultar tambem `pm02NextAction.suggestedCommand` e
`pm02NextAction.suggestedRhremotoCommand`.

Em producao, quando quiser reprovar explicitamente worktree suja ou `DEBUG`
ativo e exigir referencia do frontend publicado, acrescente:

```bash
python manage.py validar_baseline_pm02 --modo-servidor-estrito --frontend-ref=<commit-ou-deploy-vercel> --ambiente=producao --release-ref=<tag-ou-commit-backend> --backup-ref=<arquivo-ou-id-backup> --json
```

Ou, quando for mais facil registrar a URL publicada do Vercel:

```bash
python manage.py validar_baseline_pm02 --modo-servidor-estrito --frontend-deploy-url=<url-deploy-vercel> --ambiente=producao --release-ref=<tag-ou-commit-backend> --backup-ref=<arquivo-ou-id-backup> --json
```

Para validar tambem os valores esperados do `.env` de producao, acrescente:
`--esperar-session-cookie-domain=.rhremoto.com`,
`--esperar-csrf-cookie-domain=.rhremoto.com` e
`--esperar-cache-backend=django.core.cache.backends.redis.RedisCache`. Quando
quiser travar tambem o banco Redis usado pelo cache, acrescente
`--esperar-cache-location=redis://127.0.0.1:6379/1`.
Quando a janela tambem quiser conferir que os cookies so trafegam por HTTPS,
acrescente `--esperar-session-cookie-secure=true` e
`--esperar-csrf-cookie-secure=true`; esses gates sao opcionais e nao entram no
perfil RHRemoto automaticamente.
Para travar o escopo `SameSite` dos cookies, acrescente
`--esperar-session-cookie-samesite=Lax` e
`--esperar-csrf-cookie-samesite=Lax`, ou o valor esperado da janela.
Como atalho equivalente para a producao RHRemoto em servidor unico com Redis
local, use `--perfil-rhremoto-producao`; ele preenche `--ambiente=producao`,
cookies `.rhremoto.com` e cache Redis local, sem preencher canonical-first ou
banco automaticamente. Valores informados explicitamente no comando prevalecem
sobre os defaults do perfil. Quando usado, o JSON publica
`environmentProfile=rhremoto-producao`, `environmentProfileDefaults`,
`environmentProfileDefaultsApplied` e `environmentProfileOverrides`; o registro
markdown mostra `Perfil de ambiente: rhremoto-producao`,
`Defaults do perfil de ambiente`, `Defaults aplicados do perfil de ambiente` e
`Overrides do perfil de ambiente`; o `strictServerCommandResolved` mantem a flag
do perfil junto dos valores concretos expandidos.
O snapshot e o validador tambem publicam comandos prontos em
`pm02StrictServerCommandRhremotoProduction`,
`pm02StrictServerCommandRhremotoProductionWithDeployUrl`,
`pm02StrictServerCommandRhremotoProductionWithEvidence`,
`pm02StrictServerCommandRhremotoProductionWithDeployUrlAndEvidence`,
`strictServerCommandRhremotoProduction` e
`strictServerCommandRhremotoProductionWithDeployUrl`, incluindo variantes com
`--diretorio-evidencias=<diretorio-evidencias-pm02>` e
`--exigir-arquivos-evidencia`.
O bloco `manualRequirements` tambem inclui `suggestedRhremotoCommand` e
`suggestedRhremotoCommandWithDeployUrl`, alem das variantes com evidencias, para
facilitar a copia do comando correto da janela.
Quando a janela precisar confirmar o estado atual do canonical-first, acrescente
`--esperar-canonical-first-enabled=true` e
`--esperar-canonical-first-sources=custo_fixo` ou a allowlist esperada para a
janela.
Para evitar rodar a baseline contra o banco errado, tambem e possivel informar
`--esperar-database-engine=<engine>`, `--esperar-database-name=<nome>`,
`--esperar-database-host=<host>` e `--esperar-database-port=<porta>` conforme o
ambiente real.
Para conferir configuracao web do backend publicado, use
`--esperar-allowed-hosts=<hosts>`, `--esperar-csrf-trusted-origins=<origens>` e
`--esperar-cors-allowed-origins=<origens>`, com valores separados por virgula.

Use `--ambiente=producao` ou `--ambiente=homologacao` junto de
`--exigir-ambiente` para que o `executionRecord.markdown` registre um nome
humano de ambiente e nao deixe essa evidencia pendente.
O atalho `--modo-servidor-estrito` ativa `--falhar`, `--falhar-se-dirty`,
`--falhar-se-debug`, as exigencias de frontend, release, backup, ambiente e
fechamento PM-02.
Nesse modo, `--frontend-ref` ou `--frontend-deploy-url` precisa apontar para o
deploy publicado do frontend; commit encontrado em checkout local nao fecha a
PM-02 sozinho.

`LocMemCache` continua sendo a opcao mais simples para desenvolvimento ou
servidor unico sem Redis, mas ele e isolado por processo. Com Gunicorn usando
varios workers, cada worker teria seu proprio cache. Para producao com workers
ou mais de um servidor, Redis evita esse isolamento.

## 2.3. Evidencia PM-03.1 da origem canonical-first ativa

A PM-03.1 de `custo_fixo` foi fechada em producao RHRemoto em 2026-05-26 com
`canonicalFirst.count=1`, valor 81.90, `legacyAdapterSynced.count=0`,
auditoria de totais sem divergencia e `validar_fechamento_pm03` aprovado. Os
comandos abaixo ficam como roteiro de repeticao/auditoria dessa evidencia. Essa
etapa nao ativa origem nova; ela apenas comprova que a origem ja publicada
continua escrevendo pela estrutura canonica, sem baixa legada na janela.

Use uma data de ativacao real da janela e grave as evidencias fora do repositorio:

```bash
python manage.py validar_janela_canonical_first \
  --source=custo_fixo \
  --data-ativacao=DATA_DA_ATIVACAO \
  --validar-preflight-operacional \
  --falhar-com-preflight-operacional \
  --exigir-feature-flag-ativa \
  --diretorio-evidencias=~/evidencias_pm03_custo_fixo \
  --exigir-arquivos-evidencia \
  --json \
  --falhar
```

Esse comando gera a evidencia de validacao da janela e tambem retorna um
checklist com os comandos seguintes ja preenchidos com `--diretorio-evidencias`.

```bash
python manage.py monitorar_janela_canonical_first \
  --source=custo_fixo \
  --data-ativacao=DATA_DA_ATIVACAO \
  --exigir-canonical-first \
  --falhar-com-legado-na-janela \
  --exigir-data-ativacao \
  --diretorio-evidencias=~/evidencias_pm03_custo_fixo \
  --exigir-arquivos-evidencia \
  --json \
  --falhar
```

O comando salva `pm03-monitor-canonical-first.json` e
`pm03-monitor-canonical-first.md` quando `--diretorio-evidencias` e usado. O
JSON tambem publica `evidenceFiles` e `executionRecord.markdown`; esse markdown
deve ser copiado para o registro da PM-03.1 no plano mestre apos as revisoes
semantica e tecnica.

Depois do monitor, salve tambem a auditoria da fonte de escrita no mesmo
diretorio de evidencias:

```bash
python manage.py auditar_fonte_escrita_baixas \
  --source=custo_fixo \
  --data-ativacao=DATA_DA_ATIVACAO \
  --write-model-source=canonicalFirst \
  --exigir-canonical-first \
  --exigir-data-ativacao \
  --diretorio-evidencias=~/evidencias_pm03_custo_fixo \
  --exigir-arquivos-evidencia \
  --json
```

A auditoria gera `pm03-auditoria-fonte-escrita.json` e
`pm03-auditoria-fonte-escrita.md`, tambem com `evidenceFiles` e
`executionRecord.markdown`.

Por fim, preserve a auditoria de totais do mesmo recorte operacional:

```bash
python manage.py auditar_totais_negocio \
  --falhar-com-divergencia \
  --validar-valores-editaveis \
  --falhar-com-valores-editaveis \
  --diretorio-evidencias=~/evidencias_pm03_custo_fixo \
  --exigir-arquivos-evidencia \
  --json
```

Ela gera `pm03-auditoria-totais-negocio.json` e
`pm03-auditoria-totais-negocio.md`.

Com os quatro artefatos no diretorio, valide o fechamento documental da PM-03:

```bash
python manage.py validar_fechamento_pm03 \
  --source=custo_fixo \
  --data-ativacao=DATA_DA_ATIVACAO \
  --diretorio-evidencias=~/evidencias_pm03_custo_fixo \
  --json \
  --falhar
```

Esse comando le `pm03-validacao-feature-flag.json`,
`pm03-monitor-canonical-first.json`, `pm03-auditoria-fonte-escrita.json` e
`pm03-auditoria-totais-negocio.json`, salvando
`pm03-fechamento-canonical-first.json` e
`pm03-fechamento-canonical-first.md`.
Para novas origens apos a PM-03.1, quando o canario de pre-window gerar
`pm03-validacao-ativacao-canonical-first.json`, inclua
`--exigir-validacao-ativacao` no fechamento para impedir concluir a janela sem
essa evidencia.

Se houver falha por baixa legada na janela, nao avance para outra origem. Revise
o registro, corrija a causa e rode novamente o monitor. Com PM-03.1 concluida,
o proximo bloco passa a ser preparar PM-03.2 de `despesa_operacional`, mantendo
`custo_fixo` na allowlist aprovada.

Para PM-03.2, antes de ativar `despesa_operacional`, confirme que existe uma
pendencia real/controlada para canario rollback-only e que o ambiente preserva
a origem ja aprovada:

```env
CANONICAL_FIRST_SETTLEMENT_ENABLED=True
CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional
```

Use `validar_ativacao_canonical_first --source=despesa_operacional --json` ou
`validar_janela_canonical_first --source=despesa_operacional --json` para ver
`pendingObligations.canaryCandidates`. Quando houver candidato, use o
`sourceId` retornado no canario rollback-only e inclua
`--exigir-source-id-canario` e `--exigir-data-pagamento-canario` nos
validadores da janela controlada. O payload `canary.sourceIdCheck` confirma se
o ID informado ainda e elegivel, e o artefato registra
`paymentDateRequired`/`paymentDateProvided` quando a data explicita e exigida.
O payload tambem publica `recommendedCommands.canaryRollbackOnly`, com o
primeiro `sourceId` elegivel preenchido quando existir candidato.
Use tambem `nextAction`: `awaitCanaryCandidate` indica que ainda falta
pendencia controlada; `runCanaryRollbackOnly` indica que o canario pode ser
executado; `activateAllowlistWindow` indica que o canario rollback-only ja
passou e a janela pode seguir para allowlist, backup e auditorias.
O mesmo campo aparece em `validar_janela_canonical_first`, inclusive no
markdown de evidencia, para registrar a decisao operacional da janela.
O monitor `monitorar_janela_canonical_first` tambem registra o mesmo resumo no
JSON, relatorio humano e markdown de monitoramento. O titulo do markdown do
monitor e generico (`Registro PM-03 - monitoramento canonical-first`) para que
PM-03.2 e proximas origens nao gerem evidencia presa ao historico PM-03.1 de
`custo_fixo`.
Para o canario de pre-window, prefira
`validar_ativacao_canonical_first --source=despesa_operacional
--username=<usuario> --source-id=<sourceId-de-canaryCandidates>
--payment-date=<DATA> --executar-canario --exigir-canario
--exigir-source-id-canario --exigir-data-pagamento-canario
--diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional>
--exigir-arquivos-evidencia --json --falhar`, pois ele valida readiness,
candidato explicito, data explicita e rollback no mesmo gate e salva
`pm03-validacao-ativacao-canonical-first.json` e `.md`.
No fechamento documental dessa origem, use tambem
`validar_fechamento_pm03 ... --exigir-validacao-ativacao --json --falhar`.
Esse fechamento exige que o artefato de ativacao tenha
`nextAction=activateAllowlistWindow`, confirmando que o canario rollback-only
ja passou antes de concluir a origem. Ele tambem confere se o resultado do
canario registrou `canary=True`, `rollbackOnly=True`, `writesPersisted=False`,
a mesma data explicita, a mesma origem da janela, o mesmo `sourceId` aprovado e
identidade de obrigacao (`obligationId`/`obligationKey`) consistente, alem de
`canonicalSettlement.writeModelSource=canonicalFirst` e obrigacao canonica
igual ao candidato aprovado. O fechamento tambem confere `deltaAmount`
positivo e valores canonicos (`realizedAmount`/`allocatedAmount`) iguais a
`requestedRealizedAmount`, alem de baixa/alocacao canonica registrada e ultima
baixa em `canonicalFirst`, realizada, classificada como saida com fluxo/natureza
e com id/chave, `settlementDate` e `ledgerEntryId`. O fechamento tambem
confere o `canary.result.item` que a API devolveria ao Next.js, exigindo mesma
origem/sourceId, valor realizado, valor realizado no ledger e conciliacao.

Nao promova `despesa_operacional` se o canario nao puder ser executado.

Durante a PM-03.2A, para inventariar origens adapter-only sem abrir PM-04, use
`python manage.py verificar_prontidao_escrita_canonica --json` para consultar
`adapterOnlySources` e `pm04DecisionMatrix`. Esse payload separa origens PM-03
diretas das origens que ainda exigem decisao antes de qualquer allowlist:
`custo_extra`, `custo_servico` e `parcela_divida`.
`validar_ativacao_canonical_first --json` tambem inclui essa matriz em
`writeReadiness`, para explicar por que uma origem adapter-only nao deve ser
promovida pela trilha PM-03 direta.

## 3. PostgreSQL

Instale o PostgreSQL no servidor:

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

Crie usuario e banco:

```bash
sudo -u postgres psql
```

Dentro do `psql`:

```sql
CREATE DATABASE controledecaixa;
CREATE USER controledecaixa WITH PASSWORD 'SENHA_FORTE';
ALTER ROLE controledecaixa SET client_encoding TO 'utf8';
ALTER ROLE controledecaixa SET default_transaction_isolation TO 'read committed';
ALTER ROLE controledecaixa SET timezone TO 'America/Fortaleza';
GRANT ALL PRIVILEGES ON DATABASE controledecaixa TO controledecaixa;
\q
```

No `.env`:

```text
DATABASE_URL=postgres://controledecaixa:SENHA_FORTE@localhost:5432/controledecaixa
```

## 4. Migrar dados atuais do SQLite para PostgreSQL

Nao envie o arquivo de dados pelo GitHub se ele tiver informacoes reais do negocio. Gere um arquivo local e mande direto para o servidor.

No computador local, dentro do projeto:

```powershell
.\venv\Scripts\python.exe manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.Permission --indent 2 --output backup_dados.json
```

Envie para o servidor:

```powershell
scp backup_dados.json ubuntu@IP_DO_SERVIDOR:~/backup_dados.json
```

No servidor, depois de configurar o `.env` com PostgreSQL:

```bash
source venv/bin/activate
python manage.py migrate
python manage.py loaddata ~/backup_dados.json
python manage.py verificar_consistencia_financeira --corrigir
```

Depois confira:

```bash
python manage.py verificar_consistencia_financeira
python manage.py check --deploy
```

## 5. Banco, estaticos e auditoria

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py verificar_consistencia_financeira
python manage.py check --deploy
```

Se a auditoria encontrar divergencias antigas:

```bash
python manage.py verificar_consistencia_financeira --corrigir
```

## 6. Testar com Gunicorn

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

## 7. Exemplo de service systemd

Crie `/etc/systemd/system/controledecaixa.service`:

```ini
[Unit]
Description=Controle de Caixa Django
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/caminho/do/projeto/controledecaixa
Environment="PATH=/caminho/do/projeto/controledecaixa/venv/bin"
ExecStart=/caminho/do/projeto/controledecaixa/venv/bin/gunicorn config.wsgi:application --workers 3 --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable controledecaixa
sudo systemctl restart controledecaixa
sudo systemctl status controledecaixa
```

## 8. Exemplo Nginx

```nginx
server {
    listen 80;
    server_name seu-dominio.com www.seu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Depois configure HTTPS com Certbot ou outro certificado.

## 9. Fluxo de atualizacao

```bash
cd /caminho/do/projeto/controledecaixa
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py validar_preflight_deploy_financeiro --falhar
python manage.py auditar_totais_negocio --falhar-com-divergencia --validar-valores-editaveis --falhar-com-valores-editaveis
python manage.py check --deploy
sudo systemctl restart controledecaixa
```

`validar_preflight_deploy_financeiro --falhar` e a validacao padrao atual antes de reiniciar o servico: ela executa checagens financeiras, valores editaveis, ledger, despesas manuais reservadas, integridade dos credores das dividas FCF, entradas FCF automaticas de dividas e prontidao operacional. Use `verificar_consistencia_financeira` apenas como investigacao legado quando algum diagnostico antigo pedir esse comando.

No JSON do pre-flight, os blocos `debtCreditorIntegrity` e
`debtAutomaticFcfEntryIntegrity` publicam `pendingCount` como contagem
operacional de pendencias, mantendo `totalIssues` por compatibilidade com os
relatorios anteriores.
Parametros `--*-limit` do pre-flight devem ser maiores ou iguais a zero; valores
negativos sao rejeitados antes das auditorias.

Se o pre-flight apontar divergencia entre `credor_cadastro` e o alias textual
`credor` das dividas FCF, revise o relatorio JSON e rode primeiro em dry-run:

```bash
python manage.py sincronizar_credores_dividas_fcf --json
```

No JSON, `pendingCount` mostra quantas pendencias de credor foram encontradas;
`checked` fica preservado por compatibilidade com as primeiras fases do comando.
Use `--limit` apenas com valor maior ou igual a zero.

Depois de revisar, aplique somente se o resultado estiver coerente:

```bash
python manage.py sincronizar_credores_dividas_fcf --aplicar --falhar-com-pendencia
python manage.py validar_preflight_deploy_financeiro --falhar
```

Esse comando corrige apenas `credor_cadastro`/`credor` e nao salva a divida pelo
model, para nao disparar efeitos financeiros indiretos. Se a divida for
`emprestimo` ou `financiamento`, a entrada FCF automatica pode precisar ser
atualizada no passo seguinte pelo comando de entradas FCF.

Se o pre-flight apontar pendencia de entrada FCF automatica de divida, revise
o relatorio e use o comando existente de sincronizacao:

```bash
python manage.py sincronizar_entradas_fcf_dividas --json --falhar-com-pendencia
python manage.py sincronizar_entradas_fcf_dividas --aplicar --json --falhar-com-pendencia
python manage.py validar_preflight_deploy_financeiro --falhar
```

Nos comandos de sincronizacao FCF, `--limit` controla apenas quantos itens
detalhados aparecem no relatorio; valores negativos sao rejeitados.
Use `--limit=0` quando quiser apenas as contagens, sem listar itens detalhados.
O roteiro sugerido pelo proprio pre-flight tambem usa `--falhar-com-pendencia`
nas sincronizacoes FCF para nao declarar sucesso se restar pendencia.

Para validar especificamente as fases recentes de FCI/FCF, credores, filtros e
action hints, rode tambem:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test \
  caixa.tests.DatasTests.test_divida_financeira_prioriza_credor_cadastrado_sobre_texto_legado \
  caixa.tests.FiltrosHtmlTests.test_api_credores_financiamentos_retorna_cadastro_ativo_para_frontend \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_retorna_contrato_json_para_frontend \
  caixa.tests.FiltrosHtmlTests.test_api_fci_e_fcf_filtram_e_expoem_dimensao_operacional \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_por_cliente_frontend \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_por_id_do_credor_cadastrado \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_por_alias_creditor_id \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_creditor_id_invalido_nao_usa_texto_legado \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_preserva_credor_textual_legado_sem_creditor_id \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_por_aliases_start_end_date \
  caixa.tests.FiltrosHtmlTests.test_api_investimentos_filtra_por_aliases_start_end_date \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_movimentacoes_por_source_type \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_descarta_source_type_invalido \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_por_alias_type \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_descarta_tipo_invalido \
  caixa.tests.FiltrosHtmlTests.test_api_financiamentos_descarta_status_invalido \
  caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_legado_publica_contas_a_receber \
  caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_action_hint_fcf_automatico_usa_source_type \
  caixa.tests.FiltrosHtmlTests.test_comando_sincronizar_credores_dividas_fcf_corrige_aliases \
  caixa.tests.FiltrosHtmlTests.test_comando_sincronizar_credores_dividas_fcf_preserva_fluxo_fcf_automatico \
  caixa.tests.FiltrosHtmlTests.test_comando_sincronizar_credores_dividas_fcf_falha_quando_nao_ha_texto_legado \
  caixa.tests.FiltrosHtmlTests.test_comando_validar_preflight_deploy_financeiro_reprova_credor_divida_inconsistente \
  caixa.tests.FiltrosHtmlTests.test_comando_validar_preflight_deploy_financeiro_reprova_entrada_fcf_divida_pendente \
  caixa.tests.FiltrosHtmlTests.test_fcf_filtros_usam_choices_dos_modelos \
  caixa.tests.FiltrosHtmlTests.test_fcf_periodos_rapidos_preservam_credor_textual_legado \
  caixa.tests.PagamentosEventoTests.test_selector_parcelas_fcf_filtra_no_banco_e_mantem_prefetch \
  caixa.tests.PagamentosEventoTests.test_pagina_pagamentos_fcf_lista_parcelas_com_saldo \
  caixa.tests.PagamentosEventoTests.test_pagina_pagamentos_fcf_preserva_filtro_credor_textual_legado \
  caixa.tests.LancamentoFinanceiroDominioTests.test_strategy_entrada_fcf_divida_mapeia_tipos_com_entrada_caixa \
  caixa.tests.LancamentoFinanceiroDominioTests.test_divida_emprestimo_gera_entrada_fcf_no_caixa_e_mes_financeiro \
  caixa.tests.LancamentoFinanceiroDominioTests.test_divida_entrada_fcf_atualiza_valor_data_e_remove_ao_mudar_tipo \
  caixa.tests.LancamentoFinanceiroDominioTests.test_divida_fornecedor_nao_gera_entrada_fcf
```

Esses testes protegem o contrato JSON de FCF, incluindo o espelhamento
`filters`/`filtros`, os filtros canonicos `creditorId`, `startDate`,
`endDate`, `sourceType`, `type`/`tipo`, `status`, `contractId`, `eventId` e
`clientId`, a separacao entre movimentacao FCF manual e entrada automatica por
divida, os links operacionais de FCI/FCF e o filtro visual de origem da
movimentacao na tela Django de FCF. A bateria tambem
protege que valores invalidos de origem, tipo e status sejam descartados sem
sumir com os dados do recorte, inclusive quando `sourceType` invalido vier junto
de `automaticFromDebt=true`; `automaticFromDebt=true/false` permanece apenas
fallback quando nao houver origem textual preenchida. Tambem protege que o credor cadastrado seja a
fonte principal da divida quando houver divergencia com
o texto legado, e que
`creditorId`/`credor_id` sejam ids estritos, sem fallback textual, inclusive na
tela de pagamentos de parcelas FCF. A regra especial de `emprestimo` e
`financiamento` gerando entrada automatica FCF/caixa tambem fica coberta, junto
com a atualizacao/remocao dessa entrada ao editar a divida e o controle de que
tipos comuns, como `fornecedor`, nao geram essa entrada.
Action hints de FCF manual devem continuar sem `creditorId`; action hints de
entradas automaticas por divida podem levar `sourceType=divida_automatica` e
`creditorId` para abrir a tela FCF ja filtrada pelo credor cadastrado.
Links legados com `credor` textual em pagamentos FCF continuam protegidos como
compatibilidade, sem virar filtro estrito por id.
O mesmo vale para a API FCF principal: `credor` textual e compatibilidade,
enquanto `creditorId`/`credor_id` indicam id canonico. A tela FCF tambem
preserva `credor` textual legado nos atalhos de periodo quando nao houver
`creditorId`, para links antigos continuarem navegaveis sem alterar a regra nova.
A bateria tambem cobre o pre-flight de deploy para credores FCF e entradas FCF
automaticas, incluindo casos corrigiveis automaticamente e pendencias manuais
sem texto legado recuperavel.

Se o deploy tambem incluir o frontend Next.js, valide no repositorio do frontend antes de publicar:

```bash
npx --yes pnpm@10.33.4 install --frozen-lockfile
npx --yes pnpm@10.33.4 run lint
npx --yes pnpm@10.33.4 run typecheck
npx --yes pnpm@10.33.4 run build
```

Se o deploy foi feito depois de restaurar um backup antigo ou de importar dados, rode primeiro a sincronizacao operacional:

```bash
python manage.py verificar_integridade_valores_editaveis --corrigir --falhar-com-inconsistencia
python manage.py sincronizar_despesas_eventos
python manage.py sincronizar_lancamentos_financeiros --aplicar
python manage.py sincronizar_modelagem_financeira_canonica --aplicar
python manage.py validar_preflight_deploy_financeiro --falhar
```

## 10. Backup mensal automatico

O projeto tem o comando:

```bash
python manage.py backup_banco_mensal
```

Ele gera arquivos em `backups/db/`, so cria um novo backup quando os dados mudaram desde o ultimo backup e mantem os 3 backups mais recentes.

Para agendar todo dia 1 as 03:00:

```bash
crontab -e
```

Adicione, ajustando o caminho do projeto:

```cron
0 3 1 * * cd /caminho/do/projeto/controledecaixa && /caminho/do/projeto/controledecaixa/venv/bin/python manage.py backup_banco_mensal >> /caminho/do/projeto/controledecaixa/backups/backup.log 2>&1
```

Para criar manualmente mesmo sem alteracao:

```bash
python manage.py backup_banco_mensal --force
```

Para manter outra quantidade:

```bash
python manage.py backup_banco_mensal --manter 6
```

O download fica disponivel para superusuarios em:

```text
/backups/
```

Nessa mesma tela, superusuarios tambem podem usar o botao **Gerar backup manual** para criar um backup imediatamente antes de uma manutencao, deploy ou alteracao importante. O backup manual usa a mesma pasta `backups/db/`, gera o `.json` e o `.meta.json`, e fica disponivel para download na propria lista.
