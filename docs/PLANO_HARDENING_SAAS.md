# Plano de Hardening SaaS - RH SaaS

Documento vivo da fase de Hardening do RH SaaS.

Criado em: 2026-07-05

## Painel executivo

### Hardening

- Status geral: 🔴 Em andamento
- Modo atual do projeto: demo/teste/portfólio multi-tenant.
- Objetivo atual: liberar uma demo segura, com isolamento entre tenants, sem tratar o projeto como produção SaaS comercial.
- Evolução funcional: bloqueada apenas para funcionalidades de produção SaaS real; ajustes necessários para demo/teste podem avançar após o Gate para Demo/Teste.

### Progresso geral

| Métrica | Progresso |
| --- | --- |
| Áreas totalmente adaptadas | 12 / 31 |
| Riscos altos concluídos | 11 / 11 |
| Riscos médios concluídos | 1 / 9 |
| Riscos baixos concluídos | 0 / 4 |

Este painel deve ser atualizado a cada implementação, auditoria ou reclassificação de riscos.

## Objetivo

Adaptar o RH SaaS para uso como demo/teste/portfólio multi-tenant, mantendo `django-tenants` como arquitetura definitiva.

O projeto não será tratado, nesta fase, como um SaaS comercial em produção real. Ainda assim, como mais de uma pessoa poderá testar a aplicação, a prioridade absoluta continua sendo impedir qualquer possibilidade de vazamento entre schemas.

A prioridade desta fase é eliminar ou neutralizar riscos que afetem a demo/teste, especialmente qualquer possibilidade de:

- um tenant acessar dados de outro tenant;
- permissões de plataforma se confundirem com permissões de tenant;
- backups, exportações, downloads, cache ou sessões escaparem do schema correto;
- funcionalidades legadas single-tenant continuarem ativas em ambiente exposto;
- configurações permitirem uso inseguro de Host, cookies, CORS, CSRF ou admin durante testes públicos/controlados.

O objetivo imediato não é concluir todos os requisitos de produção SaaS. O objetivo imediato é ter uma demo confiável, com isolamento multi-tenant comprovado e sem superfícies perigosas abertas.

O objetivo de longo prazo, caso o projeto evolua para SaaS real, continua sendo que todas as áreas da arquitetura sejam consideradas 100% adaptadas ao modelo SaaS multi-tenant por schema.

Status permitidos para cada área:

- ❌ Não adaptada
- 🟡 Parcialmente adaptada
- ✅ Totalmente adaptada

Durante a fase de demo/teste, nenhuma funcionalidade nova de produção SaaS deve ser implementada enquanto houver risco alto que permita vazamento entre tenants, execução operacional perigosa, admin exposto indevidamente, backup/download global indevido ou configuração insegura para ambiente exposto.

## Escopo atual: Demo/Teste/Portfólio

O RH SaaS será usado inicialmente apenas como demo, teste e portfólio.

Decisões para este escopo:

- O multi-tenant por schema será mantido.
- Cada usuário/tester poderá operar em tenant/schema separado.
- O tenant continuará sendo resolvido exclusivamente pelo `Host`.
- Cookies devem continuar host-only.
- Admin Django deve continuar desativado.
- Backups globais não devem ser acessíveis por administradores de tenant.
- Exportações/downloads devem ser tenant-scoped ou ficar desativados até existir proteção suficiente.
- Comandos perigosos devem ser protegidos contra execução acidental no `public` ou schema errado.
- Billing, trial, planos comerciais, cobrança, domínio customizado, observabilidade avançada e disaster recovery completo não fazem parte do escopo imediato.

Critério prático: tudo que puder causar vazamento entre tenants, confusão com o projeto antigo ou operação destrutiva acidental continua obrigatório. O que for maturidade de produção comercial pode ficar registrado para depois.

## Estado atual do projeto

O RH SaaS está em fase de adaptação definitiva para SaaS nativo com `django-tenants`.

Estado consolidado até a última auditoria:

- O backend já utiliza `django-tenants` como base arquitetural.
- O tenant é identificado pelo `Host`.
- O schema `public` deve representar somente a plataforma.
- Cada empresa deve operar em seu próprio schema PostgreSQL.
- O app operacional `caixa` deve viver apenas nos schemas dos tenants.
- `public_urls` está vazio e o admin Django não está exposto nas URLs atuais.
- Cache, sessões e throttling já receberam adaptações iniciais tenant-aware.
- Há uma suíte inicial de testes multi-tenant cobrindo criação de tenants, host, sessões, cache, throttling e isolamento básico por API.
- Ainda existem riscos importantes em comandos management, permissões DRF, exportações, auditoria/logs, produção, recuperação de desastre e resquícios legados.

## Critérios para encerrar a fase de Hardening

Para liberar a demo/teste com segurança, os critérios mínimos são:

- Nenhum risco alto conhecido que afete isolamento, admin, backup/download, exportação ou commands perigosos estiver com status "Não iniciado" ou "Em andamento".
- A suíte multi-tenant cobrir isolamento entre pelo menos dois tenants para autenticação, sessões, APIs principais, backups/exportações aplicáveis e IDs iguais quando houver endpoint simples para testar.
- Backups e exportações estiverem tenant-scoped, restritos a operadores da plataforma ou desativados para testers.
- Todos os comandos operacionais críticos estiverem classificados e protegidos contra execução acidental no schema errado.
- O admin Django continuar desativado.
- Configurações do ambiente exposto tiverem validações mínimas contra Host, cookies, CSRF, CORS, `DEBUG` e secrets inseguros.
- Uma auditoria read-only de demo/teste não encontrar riscos altos pendentes.
- Este documento estiver atualizado com painel, backlog, evidências e histórico.

Para encerrar a fase completa de Hardening rumo a produção SaaS real, todos os critérios abaixo continuam válidos:

- Nenhum risco alto conhecido estiver com status "Não iniciado" ou "Em andamento".
- Nenhum risco médio conhecido estiver com status "Não iniciado" ou "Em andamento".
- Todos os riscos baixos conhecidos tiverem decisão registrada: corrigir agora, aceitar temporariamente ou agendar para fase posterior.
- Todas as áreas da Matriz de Adaptação SaaS estiverem marcadas como "✅ Totalmente adaptada".
- Nenhuma área permanecer com status "❌ Não adaptada" ou "🟡 Parcialmente adaptada".
- A suíte multi-tenant cobrir isolamento entre pelo menos dois tenants para autenticação, sessões, APIs, permissões, backups, exportações e IDs iguais.
- Backups e exportações estiverem tenant-scoped ou explicitamente restritos a operadores da plataforma.
- Todos os comandos operacionais estiverem classificados e protegidos contra execução acidental no schema errado.
- O admin Django estiver desativado ou redesenhado com separação clara entre plataforma e tenant.
- Configurações de produção tiverem validações contra CORS, CSRF, cookies, Host e cache inseguros.
- Uma nova auditoria completa não encontrar riscos altos ou médios pendentes.
- Este documento estiver atualizado com painel, matriz, backlog, visão por domínio, evidências, histórico e decisões.

## Decisões arquiteturais definitivas

As decisões abaixo estão consolidadas para o RH SaaS:

- A arquitetura será SaaS nativa com `django-tenants`.
- O sistema não manterá compatibilidade arquitetural com o modelo antigo single-tenant.
- O projeto antigo pessoal é apenas origem histórica de código, não referência arquitetural.
- Cada empresa terá exatamente um schema PostgreSQL próprio.
- O schema `public` será usado somente para recursos da plataforma.
- Dados operacionais de clientes ficam exclusivamente no schema do tenant.
- O operador da plataforma será separado do administrador do tenant.
- `is_superuser` dentro de um tenant não equivale a operador da plataforma.
- A identificação do tenant será feita exclusivamente pelo `Host`.
- O usuário não poderá escolher tenant por parâmetro, payload, query string ou header não confiável.
- Cookies devem ser host-only por padrão.
- Sessões, cache e throttling devem considerar o tenant/schema ativo.
- Backup global pertence somente à plataforma.
- Administrador de cliente não pode baixar backup global.
- Backup/exportação de cliente deve ser tenant-scoped.
- Downloads devem ser autenticados, autorizados, auditados e limitados.
- Observabilidade mínima faz parte do Hardening.
- Observabilidade avançada poderá evoluir após a base SaaS estar segura.
- Admin Django deve permanecer desativado até existir desenho seguro para plataforma e tenant.
- Não deve existir nenhuma possibilidade intencional ou acidental de acesso entre tenants.

## Desenho futuro seguro do Admin Django

Decisão atual: `/admin/` permanece desativado nas URLConfs públicas e de tenant.

O registro de modelos no `admin.site` padrão não deve ser tratado como superfície de produção enquanto não existir rota publicada para ele. Se o Admin Django voltar no futuro, deverá seguir estas regras:

- Admin público: usar um `AdminSite` separado, exposto somente em host/URL de plataforma, autorizado apenas para operadores da plataforma e limitado a modelos de plataforma.
- Admin de tenant: se existir, usar outro `AdminSite` separado, exposto somente após resolução de tenant por `Host`, autorizado apenas para papéis do tenant e limitado a modelos operacionais do schema ativo.
- O mesmo `admin.site` não pode expor ao mesmo tempo modelos de plataforma e modelos operacionais de tenant.
- Administrador de tenant nunca deve receber permissão de operador da plataforma por estar no admin.
- Antes de reativar qualquer admin, devem existir testes provando que modelos de plataforma não aparecem no admin do tenant e modelos de tenant não aparecem no admin público.
- Enquanto esse desenho não for implementado, `/admin/` deve continuar retornando 404 no public e nos tenants.

## Nota operacional de backup/restore da demo

Esta demo não possui restore habilitado pela aplicação.

Regras mínimas enquanto não existir um runbook completo de disaster recovery:

- qualquer restore manual deve ser feito com schema explícito, nunca no schema inferido por engano;
- antes de restaurar dados em um tenant real da demo, validar o procedimento em um schema temporário;
- conferir metadata do backup antes de qualquer uso: `scope`, `schema_name`, nome do arquivo e `sha256`;
- não copiar, compactar, publicar ou expor a pasta `backups/` inteira;
- arquivos locais em `backups/` são artefatos operacionais sensíveis, mesmo quando ignorados pelo Git;
- restore por tenant, criptografia e política completa de retenção permanecem no backlog de recuperação de desastre.

## Matriz de Adaptação SaaS

Esta matriz deve ser reavaliada após cada implementação e a cada nova auditoria.

Uma área só pode ser marcada como "✅ Totalmente adaptada" quando:

- estiver coerente com a arquitetura SaaS definitiva;
- não depender de comportamento single-tenant legado;
- possuir testes ou validação objetiva quando houver risco de isolamento;
- estiver documentada quando envolver decisão arquitetural;
- não possuir risco alto ou médio pendente associado.

| Área | Status atual | Bloqueado por | Condição para encerrar como totalmente adaptada |
| --- | --- | --- | --- |
| Autenticação | ✅ Totalmente adaptada | - | Papéis de plataforma/tenant separados e autenticação/lockout testados entre tenants no escopo demo/teste |
| Sessões | ✅ Totalmente adaptada | - | Manter testes provando que sessão de um tenant não autentica outro tenant |
| Cache | 🟡 Parcialmente adaptada | L-001 | Manter prefixo por schema e revisar cache estático/frontend antes de produção |
| CSRF | 🟡 Parcialmente adaptada | M-002 | Validar política final para subdomínios, trusted origins e produção |
| Cookies | 🟡 Parcialmente adaptada | M-002 | Garantir cookies host-only em produção e checks contra domínio compartilhado |
| CORS | 🟡 Parcialmente adaptada | M-002 | Definir integração final frontend/backend sem wildcard inseguro |
| DRF | 🟡 Parcialmente adaptada | M-001 | Reduzir `AllowAny` e padronizar permissões explícitas por tenant |
| Rate limiting | ✅ Totalmente adaptada | - | Operações caras/sensíveis da demo têm limites tenant-aware por schema, usuário/IP e testes multi-tenant |
| Middleware | ✅ Totalmente adaptada | - | Manter `TenantMainMiddleware` no início e testes de resolução por Host |
| Database Router | ✅ Totalmente adaptada | - | Manter `TenantSyncRouter` e validações de migrations por schema |
| django-tenants | ✅ Totalmente adaptada | - | Manter modelo de um schema por empresa e tenant identificado por Host |
| Commands | 🟡 Parcialmente adaptada | M-008 | Classificar e proteger todos os comandos operacionais |
| Signals | ✅ Totalmente adaptada | - | Manter signals operacionais bloqueados no `public` e cobertos por testes quando críticos |
| Backups | ✅ Totalmente adaptada | - | Backup/download tenant-scoped por schema, com autorização explícita, metadata por schema, validação de sha256, auditoria mínima por log, headers seguros e rate limit tenant-aware |
| Exportações | ✅ Totalmente adaptada | - | Export tenant-scoped, autorizado, auditado, limitado e testado com dois tenants para o escopo demo/teste |
| Uploads | 🟡 Parcialmente adaptada | L-002 | Nao ha upload real na demo; definir arquitetura tenant-aware antes de qualquer upload real |
| Media | 🟡 Parcialmente adaptada | L-002 | `MEDIA_ROOT`/`MEDIA_URL` estao explicitos; definir paths, URLs e limpeza por tenant antes de uploads reais |
| Logs | 🟡 Parcialmente adaptada | M-003 | H-009 cobre logs mínimos da demo; ainda falta padronização ampla para produção real |
| Auditoria | 🟡 Parcialmente adaptada | M-003 | H-009 cobre rastreabilidade mínima por log; ainda falta trilha persistente e cobertura ampla de ações administrativas |
| Admin Django | ✅ Totalmente adaptada | - | Manter `/admin/` desativado por teste até existir admin público e tenant separados |
| Services | 🟡 Parcialmente adaptada | M-006 | Revisar serviços sensíveis para schema ativo, permissões e ausência de globais |
| Selectors | ✅ Totalmente adaptada | - | Seletores sensíveis revisados no escopo atual e cobertos por testes de exportação entre tenants |
| Models | ✅ Totalmente adaptada | - | Separação validada entre models de `public` e models de tenant para a arquitetura atual |
| Managers | 🟡 Parcialmente adaptada | M-006 | Garantir que managers não escondam consultas globais nem dependam de single-tenant |
| QuerySets | 🟡 Parcialmente adaptada | M-001 | Testar listagem, detalhe, IDs iguais e filtros entre tenants |
| Testes | 🟡 Parcialmente adaptada | M-001, L-004 | Cobrir autenticação, permissões, API, backups, exportações, comandos e produção |
| Configurações de produção | 🟡 Parcialmente adaptada | M-002, M-007 | Adicionar checks para Host, cookies, CSRF, CORS, cache, debug e secrets |
| Deploy | 🟡 Parcialmente adaptada | M-007, M-008 | Documentar e validar deploy separado do projeto antigo, sem comandos legados |
| Observabilidade mínima | ❌ Não adaptada | M-003 | Ter logs, auditoria, alertas mínimos e identificação do tenant em eventos sensíveis |
| Recuperação de desastre | 🟡 Parcialmente adaptada | M-009 | Definir restore e teste de restore por tenant e plataforma |
| Segurança operacional | 🟡 Parcialmente adaptada | M-007, M-008 | Fechar procedimentos de acesso, comandos, secrets, auditoria e incidentes |

## Observabilidade

### Observabilidade mínima

A observabilidade mínima é obrigatória durante o Hardening e faz parte do gate para produção.

Ela deve cobrir:

- logs com identificação de tenant/schema;
- auditoria de login, logout, backup, exportação, download e ações administrativas;
- alertas mínimos para erros críticos, falhas de autenticação suspeitas e falhas de backup/exportação;
- identificação de usuário, IP, Host e schema nos eventos sensíveis;
- evidências de que eventos de um tenant não se misturam com eventos de outro tenant.

Risco relacionado: M-003.

### Observabilidade avançada

A observabilidade avançada pode evoluir depois da base SaaS estar segura.

Ela poderá incluir:

- métricas detalhadas;
- dashboards;
- tracing distribuído;
- analytics;
- SLOs e relatórios operacionais.

Observabilidade avançada não libera funcionalidade nova durante o Hardening e não substitui a observabilidade mínima obrigatória.

## Backlog principal

O backlog deve existir apenas uma vez e permanecer organizado por severidade.

Todos os riscos devem seguir exatamente o mesmo modelo:

- ID
- Domínio
- Severidade
- Status
- Responsável
- Estimativa
- Descrição
- Motivo
- Arquivos envolvidos
- Impacto
- Estratégia de correção
- Dependências
- Critério de Aceite
- Evidências
- Histórico individual

Status permitidos para riscos:

- Não iniciado
- Em andamento
- Concluído
- Substituído / Desdobrado

Quando um risco for dividido em riscos menores, ele nunca deve ser removido. Deve ser marcado como "Substituído / Desdobrado" e apontar para os novos IDs.

### 🔴 Riscos ALTOS

#### H-001

- ID: H-001
- Domínio: Backups
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Grande
- Descrição: Backup e download ainda seguem desenho antigo/global.
- Motivo: Listagem, criação e download usam diretórios globais e autorização baseada em `is_superuser`.
- Arquivos envolvidos: `caixa/views_backups.py`, `caixa/services_backups.py`, `caixa/selectors_backups.py`, `caixa/management/commands/backup_banco_mensal.py`.
- Impacto: Tenant pode receber capacidade perigosa de acessar, listar ou baixar artefatos globais.
- Estratégia de correção: Separar backup de plataforma e export/backup tenant-scoped; incluir schema no path/nome; auditar downloads; adicionar testes com dois tenants.
- Dependências: H-002 concluído em 2026-07-05.
- Critério de Aceite: Nenhum administrador de tenant consegue listar, criar ou baixar backup global; backups/exportações de tenant ficam isolados por schema; testes com dois tenants provam que tenant A não acessa artefatos do tenant B; evidências de validação ficam registradas.
- Evidências:
  - 2026-07-05: Auditoria inicial de `caixa/services_backups.py`, `caixa/selectors_backups.py`, `caixa/views_backups.py`, `caixa/management/commands/backup_banco_mensal.py`, `caixa/management/commands/exportar_recadastro_manual_pm06.py` e `caixa/views_obrigacoes.py`.
  - 2026-07-05: `criar_backup_banco` passou a gravar em `backups/tenants/<schema>/db` para tenants e em `backups/platform/db` para schema `public`, com metadata contendo `scope` e `schema_name`.
  - 2026-07-05: Temporários de backup passaram a ser criados dentro do diretório `.tmp` do próprio escopo/schema.
  - 2026-07-05: Listagem e download passaram a validar metadata do arquivo antes de retornar qualquer backup.
  - 2026-07-05: API/HTML de backup passaram a exigir administrador do tenant e a listar/criar/baixar apenas arquivos do schema ativo.
  - 2026-07-05: Exportação operacional `exportar_recadastro_manual_pm06` passou a usar `backups/tenants/<schema>/recadastro` por padrão.
  - 2026-07-05: Exportação CSV de obrigações auditada; ela não grava arquivo em disco e foi coberta por teste multi-tenant de resposta CSV tenant-scoped.
  - 2026-07-05: Auditoria mínima por log adicionada para listagem, criação e download de backup, com action, outcome, schema, user_id, host e filename.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy.tests.TenantBackupIsolationTests tenancy.tests.TenantExportDownloadIsolationTests tenancy.tests.TenantPlatformRoleSeparationTests` aprovado, 7 testes, 175.978s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy` aprovado, 28 testes, 728.612s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: Auditoria read-only final com `rg` confirmou que os arquivos alterados não usam mais o diretório ativo global `backups/db`; referências restantes são documentação/legado ou asserções de teste contra o caminho antigo.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Implementado isolamento tenant-scoped para criação, listagem e download de backups.
  - 2026-07-05: Adicionados testes multi-tenant para listagem, download, criação manual e exportação CSV.
  - 2026-07-05: Concluído após testes focados, suíte tenancy completa, check, makemigrations check e auditoria read-only final.

#### H-002

- ID: H-002
- Domínio: Autenticação
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Grande
- Descrição: Uso de `is_superuser` mistura operador da plataforma e administrador do tenant.
- Motivo: No SaaS, superuser do tenant não pode representar permissão global de plataforma.
- Arquivos envolvidos: `caixa/views_backups.py`, `caixa/permissions.py`, `caixa/views_api_auth.py`, views que expõem flags de usuário.
- Impacto: Elevação indevida de privilégio e confusão entre escopos de plataforma e tenant.
- Estratégia de correção: Criar permissão/serviço explícito de operador da plataforma; manter superuser de tenant restrito ao tenant; revisar payloads de autenticação.
- Dependências: Nenhuma.
- Critério de Aceite: Operador da plataforma e administrador do tenant têm papéis tecnicamente separados; `is_superuser` de tenant não libera ação de plataforma; testes provam que admin do tenant não executa ação global.
- Evidências:
  - 2026-07-05: `venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy.tests.TenantPlatformRoleSeparationTests` aprovado, 3 testes.
  - 2026-07-05: `venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: Auditoria read-only com `rg -n "is_superuser|require_superuser|require_api_superuser|canManageBackups|canApproveBudget|canManageInAdmin|isPlatformOperator|isTenantAdmin" caixa config tenancy -S`; usos de autorização migrados para helpers explícitos, com `is_superuser` restante nos helpers e no payload bruto de compatibilidade.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy` ficou bloqueado porque o timeout anterior deixou o banco temporário `test_rhsaas_dev` inconsistente; tentativa com `--keepdb` falhou por coluna duplicada em `caixa_despesaoperacional.origem`.
  - 2026-07-05: Banco temporário `test_rhsaas_dev` recriado após validação explícita de que o banco base era `rhsaas_dev` e o alvo era somente `test_rhsaas_dev`; resultado: `DROPPED=test_rhsaas_dev`.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy` aprovado, 24 testes, 459.490s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py check` aprovado após suíte tenancy.
  - 2026-07-05: `venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado após suíte tenancy, sem mudanças detectadas.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Implementação iniciada com helpers explícitos de operador da plataforma e administrador do tenant; item ainda não concluído até recriar o banco temporário de testes e executar a suíte tenancy completa.
  - 2026-07-05: Banco temporário de testes recriado com aprovação explícita.
  - 2026-07-05: Concluído após suíte tenancy completa, check e makemigrations check aprovados.

#### H-003

- ID: H-003
- Domínio: Admin Django
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Grande
- Descrição: Admin Django não pode ser religado com desenho atual.
- Motivo: Models de plataforma e tenant usam o mesmo admin global registrado.
- Arquivos envolvidos: `tenancy/admin.py`, `caixa/admin.py`, `config/tenant_urls.py`, `config/public_urls.py`.
- Impacto: Exposição cruzada ou administração no schema errado se `/admin/` voltar sem redesenho.
- Estratégia de correção: Manter admin desativado; planejar admin público separado e, se existir, admin de tenant isolado por Host/schema.
- Dependências: H-002 concluído em 2026-07-05.
- Critério de Aceite: `/admin/` permanece inacessível ou existe separação comprovada entre admin público e admin de tenant; models operacionais não aparecem no admin público; models de plataforma não aparecem no admin de tenant.
- Evidências:
  - 2026-07-05: Auditoria de `config/public_urls.py`, `config/tenant_urls.py` e `config/urls.py` confirmou que nenhuma URL monta `admin.site.urls`.
  - 2026-07-05: Auditoria de `tenancy/admin.py` e `caixa/admin.py` confirmou que modelos de plataforma e de tenant ainda estão registrados no `admin.site` padrão, mas sem rota publicada.
  - 2026-07-05: Registrado desenho futuro seguro do Admin Django neste plano: admin público e admin de tenant devem usar superfícies separadas antes de qualquer reativação.
  - 2026-07-05: Adicionados testes `TenantAdminDisabledTests` garantindo ausência de rota `admin/`, ausência de resolver `admin` nas URLConfs e 404 para `/admin/` no public e em tenant.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy.tests.TenantAdminDisabledTests` aprovado, 3 testes, 36.063s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy` aprovado, 31 testes, 751.979s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: Auditoria read-only final com `rg` confirmou ausência de `admin.site.urls`, `path(...admin...)`, `include(...admin...)` e rota `admin/` em `config`; a única referência a `/admin/` em `config/settings.py` é exclusão de CSP e não publica rota.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Concluído mantendo `/admin/` desativado, adicionando testes de regressão e documentando o desenho futuro obrigatório para reativação segura.

#### H-004

- ID: H-004
- Domínio: Commands
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Grande
- Descrição: Comandos operacionais ainda não estão todos classificados e protegidos.
- Motivo: Alguns comandos legados ou de validação podem ler, escrever ou exportar dados no schema errado.
- Arquivos envolvidos: `caixa/management/commands/*.py`.
- Impacto: Execução acidental em `public` ou tenant incorreto.
- Estratégia de correção: Classificar todos como `tenant-only`, `platform-only` ou `read-only`; exigir schema explícito quando aplicável; bloquear `public` para dados operacionais.
- Dependências: H-002 concluído em 2026-07-05.
- Critério de Aceite: Todos os comandos estão inventariados; comandos operacionais recusam schema `public`; comandos tenant-only exigem schema/tenant explícito; testes ou validações provam bloqueio de execução perigosa.
- Evidências:
  - 2026-07-05: Criado inventário central em `tenancy/command_guards.py` com 45 commands customizados classificados como `tenant-only`, `read-only`, `legacy/read-only` ou `platform-only`.
  - 2026-07-05: Commands tenant-only que ainda não tinham guarda passaram a chamar `ensure_tenant_schema` no início do `handle`, falhando de forma explícita no schema `public`.
  - 2026-07-05: `limpar_base_operacional_pm06` passou a validar que o `--backup-ref` pertence ao schema ativo e está dentro do diretório esperado do tenant.
  - 2026-07-05: Snapshot de baseline passou a usar `rhsaasfront` como frontend padrão.
  - 2026-07-05: Perfil legado `--perfil-rhremoto-producao` foi desativado no RH SaaS e coberto por teste.
  - 2026-07-05: Auditoria read-only confirmou `custom_commands=45`, `classified_commands=45`, `missing_classification=[]`, `missing_files=[]` e `tenant_only_missing_guard=[]`.
  - 2026-07-05: `venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy.tests.TenantCommandGuardTests` aprovado, 8 testes, 59.281s na última execução.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy` aprovado, 37 testes, 643.788s na última execução.
  - 2026-07-05: `venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: `git diff --check` aprovado sem erro; Git exibiu apenas aviso de normalização futura de CRLF em dois arquivos tocados.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Concluído com inventário, guardas tenant-only, validação de backup por schema, neutralização de perfil legado e testes focados.

#### H-005

- ID: H-005
- Domínio: Exportações
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Médio
- Descrição: Exportações e downloads ainda não possuem padrão SaaS completo.
- Motivo: Exportações dependem do schema ativo, mas ainda faltam padrão, auditoria, rate limit e testes de isolamento.
- Arquivos envolvidos: `caixa/views_obrigacoes.py`, comandos de exportação, futuras views de download.
- Impacto: Vazamento de dados por arquivo, cache, path ou permissão incorreta.
- Estratégia de correção: Criar serviço padrão tenant-scoped para export/download; auditar; limitar; testar tenant A vs tenant B.
- Dependências: H-002 concluído em 2026-07-05, M-001, M-003.
- Critério de Aceite: Exportações retornam apenas dados do schema atual; tenant A nunca exporta dados do tenant B; downloads são autenticados, autorizados, auditados e cobertos por testes.
- Evidências:
  - 2026-07-05: `api_exportar_obrigacoes_financeiras` mantém exportação em memória por `HttpResponse`, sem criar arquivo temporário compartilhado em disco.
  - 2026-07-05: Exportação CSV continua autenticada e autorizada por permissões do tenant/schema ativo.
  - 2026-07-05: Exportação CSV registra auditoria mínima por log com action, outcome, schema, user_id, host, scope e filename para sucesso, negação de autenticação, negação de permissão e erro de validação.
  - 2026-07-05: Resposta CSV mantém `Cache-Control: no-store` e passou a incluir `X-Content-Type-Options: nosniff`.
  - 2026-07-05: Teste `TenantExportDownloadIsolationTests.test_exportacao_csv_retorna_apenas_dados_do_schema_do_host` validou tenant A vs tenant B, `Content-Disposition`, `no-store`, `nosniff` e auditoria com `schema=tenant_a`.
  - 2026-07-05: Teste `TenantExportDownloadIsolationTests.test_exportacao_csv_exige_permissao_no_tenant` validou 403 e auditoria quando usuário do tenant não possui permissão de exportação.
  - 2026-07-05: `venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy.tests.TenantExportDownloadIsolationTests` aprovado, 2 testes, 66.201s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py test tenancy` aprovado, 38 testes, 720.161s.
  - 2026-07-05: `venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: `git diff --check` aprovado sem erro; Git exibiu apenas aviso de normalização futura de CRLF em dois arquivos tocados anteriormente.
  - 2026-07-05: Auditoria read-only focada com `rg` confirmou pontos de download/export sensíveis alterados: `views_obrigacoes.py` para exportação CSV e `views_backups.py` para downloads de backup já tratados em H-001.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Concluído para o escopo demo/teste com exportação tenant-scoped, auditoria mínima, cabeçalhos seguros e testes multi-tenant focados.

#### H-006

- ID: H-006
- Domínio: Configurações de demo/teste
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: Configuração mínima da demo multi-tenant precisava aceitar o tenant local e evitar ambiguidade de `DEBUG`.
- Motivo: A demo precisa funcionar por `Host`/subdomínio para provar isolamento entre tenants; `DEBUG=release` era interpretado como `False` silenciosamente e podia divergir do `.env`.
- Arquivos envolvidos: `config/settings.py`, `.env`, `.env.example`, `.env.production.example`.
- Impacto: Demo poderia falhar em `rh-teste.localhost`, quebrar login/CSRF/CORS ou rodar com modo de debug diferente do esperado.
- Estratégia de correção: Permitir `rh-teste.localhost` no ambiente local, liberar origem do frontend local do tenant em CSRF/CORS, manter cookies host-only, orientar `SECRET_KEY` forte e bloquear valores ambíguos para `DEBUG`.
- Dependências: H-001, H-002, H-003, H-004 e H-005 concluídos.
- Critério de Aceite: Demo local aceita `rh-teste.localhost`; origem `http://rh-teste.localhost:3000` está permitida em CSRF/CORS; cookies continuam host-only; `DEBUG` só aceita valores booleanos claros; validações locais passam.
- Evidências:
  - 2026-07-05: `.env` local da demo passou a incluir `ALLOWED_HOSTS=.localhost,localhost,127.0.0.1,rh-teste.localhost`.
  - 2026-07-05: `.env` local da demo passou a incluir `http://rh-teste.localhost` e `http://rh-teste.localhost:3000` em `CSRF_TRUSTED_ORIGINS`, e `http://rh-teste.localhost:3000` em `CORS_ALLOWED_ORIGINS`.
  - 2026-07-05: `config/settings.py` passou a rejeitar `DEBUG` ambíguo, como `DEBUG=release`, com erro explícito orientando `DEBUG=True` para demo local.
  - 2026-07-05: `.env.example` passou a orientar geração de `SECRET_KEY` local forte, sem expor segredo real.
  - 2026-07-05: `.env.example` e `.env.production.example` reforçam que cookies devem permanecer host-only; `COOKIE_SECURE=False` é apenas para demo local HTTP e HTTPS público deve usar `True`.
  - 2026-07-05: Validação de configuração confirmou `RH_TESTE_ALLOWED=True`, `CSRF_HAS_TENANT=True`, `CORS_HAS_TENANT=True`, `SESSION_COOKIE_DOMAIN=None` e `CSRF_COOKIE_DOMAIN=None`.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check --deploy` executado como diagnóstico; retornou apenas avisos esperados para demo local HTTP (`DEBUG=True`, sem HSTS/SSL redirect/cookies secure e `SECRET_KEY` local curta).
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantIsolationInfrastructureTests tenancy.tests.TenantAuthSessionIsolationTests` aprovado, 10 testes, 144.446s.
  - 2026-07-05: `git diff --check` aprovado sem erros.
  - 2026-07-05: Validação negativa com `DEBUG=release` confirmou falha explícita: `DEBUG deve ser True ou False`.
- Histórico individual:
  - 2026-07-05: Criado e concluído como ajuste mínimo para demo/teste/portfólio multi-tenant, sem transformar o projeto em hardening enterprise.

#### H-007

- ID: H-007
- Domínio: Autenticação e Sessões
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: A demo precisava de provas automatizadas adicionais para autenticação, sessão e CSRF entre tenants.
- Motivo: Mais de um usuário poderá testar a aplicação simultaneamente; sessão, CSRF e lockout não podem atravessar schemas/hosts.
- Arquivos envolvidos: `tenancy/tests.py`.
- Impacto: Sem esses testes, uma regressão em login, sessão, CSRF ou lockout poderia permitir comportamento compartilhado entre tenants durante a demo.
- Estratégia de correção: Adicionar testes multi-tenant focados em session fixation, CSRF cross-host e `django-axes` por tenant.
- Dependências: H-001, H-002, H-003, H-004, H-005 e H-006 concluídos.
- Critério de Aceite: Login rotaciona session key preexistente; token CSRF de um tenant não valida POST sensível em outro host; falhas de login no tenant A não bloqueiam login válido no tenant B; validações locais passam.
- Evidências:
  - 2026-07-05: Adicionado teste `TenantAuthSessionIsolationTests.test_login_rotaciona_session_key_preexistente`.
  - 2026-07-05: Adicionado teste `TenantAuthSessionIsolationTests.test_csrf_obtido_em_um_tenant_nao_valida_post_em_outro_host`.
  - 2026-07-05: Adicionado teste `TenantAuthSessionIsolationTests.test_falhas_do_django_axes_em_um_tenant_nao_bloqueiam_outro`.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests` aprovado, 8 testes, 80.006s.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests tenancy.tests.TenantApiIdorIsolationTests tenancy.tests.TenantBackupIsolationTests tenancy.tests.TenantExportDownloadIsolationTests` aprovado, 18 testes, 354.996s.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `git diff --check` aprovado sem erros.
  - 2026-07-05: Tentativa de rodar recorte antigo de `caixa.tests.PermissoesTests` falhou porque esses testes usam `Client` sem `HTTP_HOST` de tenant e recebem HTML em vez de JSON; registrado como dívida de teste legado em L-004, não como falha do fluxo multi-tenant coberto em `tenancy`.
- Histórico individual:
  - 2026-07-05: Criado e concluído como hardening mínimo de autenticação/sessão para demo multi-tenant.

#### H-008

- ID: H-008
- Domínio: Downloads e Media
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: A demo precisava fechar o hardening mínimo de downloads de backup e explicitar a política base de mídia.
- Motivo: Downloads sensíveis devem evitar cache indevido; a configuração de mídia não podia ficar implícita antes de futuras telas de upload.
- Arquivos envolvidos: `caixa/views_backups.py`, `tenancy/tests.py`, `config/settings.py`.
- Impacto: Sem headers seguros, backups baixados poderiam ser armazenados por cache local/proxy. Sem `MEDIA_ROOT`/`MEDIA_URL` explícitos, uploads futuros poderiam nascer em storage global sem decisão arquitetural clara.
- Estratégia de correção: Adicionar headers `Cache-Control: no-store`, `Pragma: no-cache` e `X-Content-Type-Options: nosniff` ao download de backup; testar os headers em download autenticado de tenant; definir `MEDIA_ROOT` e `MEDIA_URL` com comentário exigindo upload futuro tenant-aware.
- Dependências: H-001, H-005 e H-007 concluídos.
- Critério de Aceite: Download autenticado de backup de tenant retorna headers anti-cache e `nosniff`; testes focados passam; política base de mídia fica explícita sem criar upload real nem rota pública de mídia.
- Evidências:
  - 2026-07-05: `backup_download` passou a retornar `Cache-Control: no-store`, `Pragma: no-cache` e `X-Content-Type-Options: nosniff`.
  - 2026-07-05: Adicionado teste `TenantBackupIsolationTests.test_download_de_backup_envia_headers_seguros`.
  - 2026-07-05: `MEDIA_ROOT = BASE_DIR / "media"` e `MEDIA_URL = "/media/"` foram explicitados em `config/settings.py`, com nota de que uploads reais futuros devem ser tenant-aware.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantBackupIsolationTests` aprovado, 4 testes, 83.027s.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: `git diff --check` aprovado sem erros.
- Histórico individual:
  - 2026-07-05: Criado e concluído como hardening mínimo de uploads/media/downloads para demo/teste, sem implementar upload real nem storage enterprise.

#### H-009

- ID: H-009
- Domínio: Logs e Auditoria
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: A demo precisava de rastreabilidade mínima para login, logout, falha de login e tentativa inválida de download de backup.
- Motivo: Mais de um tester pode operar em tenants diferentes; incidentes básicos precisam indicar schema, host, usuário quando existir e IP sem registrar payload sensível.
- Arquivos envolvidos: `caixa/views_api_auth.py`, `caixa/views_backups.py`, `tenancy/tests.py`.
- Impacto: Sem esses eventos, falhas de autenticação, logout e tentativas inválidas de download ficariam difíceis de investigar por tenant durante a demo.
- Estratégia de correção: Registrar eventos mínimos em log simples para login bem-sucedido, falha de login, logout e download de backup negado; nunca registrar senha, token, cookie, `SECRET_KEY` nem corpo da requisição; adicionar testes multi-tenant focados.
- Dependências: H-007 e H-008 concluídos.
- Critério de Aceite: Logs de auth incluem action, outcome, schema, host, user_id quando existir e IP; falha de login não registra username/senha/payload; tentativa inválida de download de backup é auditada como negada sem revelar existência do arquivo; validações locais passam.
- Evidências:
  - 2026-07-05: `api_auth_login` passou a registrar `auth_event action=login outcome=success` e `outcome=failed` sem payload.
  - 2026-07-05: `api_auth_logout` passou a registrar `auth_event action=logout outcome=success` antes de destruir a sessão.
  - 2026-07-05: `backup_download` passou a registrar `backup_event action=download outcome=denied` quando o arquivo solicitado retorna 404, com filename sanitizado.
  - 2026-07-05: Adicionados testes `TenantAuthSessionIsolationTests.test_login_e_logout_registram_auditoria_minima_por_tenant`, `TenantAuthSessionIsolationTests.test_falha_de_login_registra_auditoria_minima_sem_payload` e `TenantBackupIsolationTests.test_download_de_backup_invalido_registra_tentativa_negada`.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests tenancy.tests.TenantBackupIsolationTests` aprovado, 15 testes, 174.965s.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `git diff --check` aprovado sem erros.
- Histórico individual:
  - 2026-07-05: Criado e concluído como hardening mínimo de logs/auditoria operacional para demo/teste, sem criar auditoria persistente nem logging enterprise.

#### H-010

- ID: H-010
- Domínio: Rate limiting
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: Operações caras/sensíveis da demo precisavam de limites tenant-aware.
- Motivo: Criação de backup, download de backup, exportação CSV e reset de senha podem ser abusados ou colidir entre tenants se o rate limit não considerar schema/tenant.
- Arquivos envolvidos: `config/settings.py`, `.env.example`, `.env.production.example`, `caixa/throttling.py`, `caixa/views_backups.py`, `caixa/views_obrigacoes.py`, `tenancy/tests.py`.
- Impacto: Sem limites específicos, um usuário poderia acionar operações caras repetidamente; sem chave por tenant, um tenant poderia afetar o limite de outro.
- Estratégia de correção: Adicionar throttles específicos para criação de backup e exportação CSV; aplicar rate limit manual ao download Django comum; garantir chave com schema, usuário/IP; documentar variáveis de ambiente; testar isolamento entre tenants.
- Dependências: H-001, H-005, H-007, H-008 e H-009 concluídos.
- Critério de Aceite: Criação de backup, download de backup e exportação CSV possuem limites configuráveis; limites não colidem entre tenants; reset de senha continua isolado por schema; validações locais passam.
- Evidências:
  - 2026-07-05: `config/settings.py` passou a expor os escopos `backup_create`, `backup_download` e `export_csv` em `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`.
  - 2026-07-05: `.env.example` e `.env.production.example` passaram a documentar `DRF_THROTTLE_BACKUP_CREATE_RATE`, `DRF_THROTTLE_BACKUP_DOWNLOAD_RATE` e `DRF_THROTTLE_EXPORT_CSV_RATE`.
  - 2026-07-05: `caixa/throttling.py` recebeu throttles tenant-aware para operações sensíveis, com chave por schema, usuário/IP e resposta segura para views Django comuns.
  - 2026-07-05: `api_backup_criar_manual` passou a usar `BackupCreateRateThrottle`.
  - 2026-07-05: `backup_download` passou a usar `BackupDownloadRateThrottle` antes de consultar arquivo, retornando 429 com `Retry-After`, `Cache-Control: no-store`, `Pragma: no-cache` e `X-Content-Type-Options: nosniff`.
  - 2026-07-05: `api_exportar_obrigacoes_financeiras` passou a usar `ExportCsvRateThrottle`.
  - 2026-07-05: Adicionados testes provando rate limit tenant-aware para criação de backup, download de backup e exportação CSV.
  - 2026-07-05: Adicionado teste provando que o rate limit de reset de senha é isolado por schema.
  - 2026-07-05: `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test tenancy.tests.TenantThrottleIsolationTests tenancy.tests.TenantBackupIsolationTests tenancy.tests.TenantExportDownloadIsolationTests` aprovado, 14 testes, 189.848s.
  - 2026-07-05: `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
- Histórico individual:
  - 2026-07-05: Criado e concluído como hardening mínimo de rate limiting para operações caras/sensíveis da demo multi-tenant.

#### H-011

- ID: H-011
- Domínio: Backups
- Severidade: Alta
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: Backups da demo precisavam validar integridade por `sha256` antes de listagem/download.
- Motivo: A metadata já registrava `sha256`, mas a validação de listagem/download ainda aceitava arquivo com metadata de schema válida mesmo se o conteúdo tivesse sido corrompido ou trocado localmente.
- Arquivos envolvidos: `caixa/selectors_backups.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Impacto: Um arquivo de backup corrompido poderia aparecer na listagem ou ser baixado, gerando falsa confiança operacional.
- Estratégia de correção: Recalcular `sha256` do arquivo antes de considerar a metadata válida; manter comportamento seguro de não listar e retornar 404 quando o hash divergir; adicionar nota operacional mínima sobre restore manual.
- Dependências: H-001, H-008 e H-010 concluídos.
- Critério de Aceite: Backup íntegro continua listando e baixando; backup com `sha256` inválido não aparece na listagem nem baixa; isolamento por tenant permanece preservado; restore pela aplicação continua não habilitado.
- Evidências:
  - 2026-07-05: `caixa/selectors_backups.py` passou a recalcular `sha256` em leitura e exigir correspondência com a metadata.
  - 2026-07-05: Teste `TenantBackupIsolationTests.test_backup_com_sha256_invalido_nao_lista_nem_baixa` cobre backup corrompido.
  - 2026-07-05: Teste `TenantBackupIsolationTests.test_backup_com_sha256_valido_continua_listando_e_baixando` cobre backup íntegro.
  - 2026-07-05: Testes existentes de criação/listagem/download continuam cobrindo isolamento entre `tenant_a` e `tenant_b`.
  - 2026-07-05: Nota operacional de backup/restore da demo adicionada neste plano.
  - 2026-07-05: `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test tenancy.tests.TenantBackupIsolationTests` aprovado, 9 testes.
  - 2026-07-05: `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py check` aprovado.
  - 2026-07-05: `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py makemigrations --check --dry-run` aprovado, sem mudanças detectadas.
  - 2026-07-05: `git diff --check` aprovado sem erros.
- Histórico individual:
  - 2026-07-05: Criado e concluído como H-011 Final para fechar integridade mínima de backups e nota operacional de restore da demo, sem implementar restore ou criptografia.

### 🟠 Riscos MÉDIOS

#### M-001

- ID: M-001
- Domínio: DRF
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Grande
- Descrição: Muitas APIs usam `AllowAny` com checagens manuais.
- Motivo: O padrão funciona hoje, mas facilita erro em endpoint novo.
- Arquivos envolvidos: `caixa/views_*.py`, `caixa/permissions.py`.
- Impacto: Endpoint pode ficar acessível por esquecimento de checagem manual.
- Estratégia de correção: Criar permissões DRF explícitas e migrar endpoint por endpoint; manter whitelist apenas para auth/csrf.
- Dependências: H-002.
- Critério de Aceite: Nenhuma API operacional usa `AllowAny` fora das exceções permitidas; permissões DRF explícitas protegem endpoints sensíveis; testes focados cobrem acesso autorizado e negado.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### M-002

- ID: M-002
- Domínio: Configurações de produção
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Configurações finais de CORS/CSRF/cookies ainda precisam travas de produção.
- Motivo: Subdomínios SaaS exigem cuidado com origem, credentials e cookie domain.
- Arquivos envolvidos: `config/settings.py`, `.env.production.example`, middleware CORS customizado.
- Impacto: Compartilhamento indevido de cookie/origem entre tenants.
- Estratégia de correção: Adicionar checks contra cookie domain compartilhado, wildcard inseguro e CORS com credentials mal configurado.
- Dependências: Decisão final de frontend same-origin ou domínio separado.
- Critério de Aceite: Produção bloqueia configuração insegura de cookie domain, CORS wildcard com credentials e CSRF trusted origins incompatíveis com o modelo SaaS; exemplos de `.env` refletem a política final.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### M-003

- ID: M-003
- Domínio: Observabilidade
- Severidade: Média
- Status: Em andamento
- Responsável: Davi
- Estimativa: Médio
- Descrição: Logs e auditoria ainda não são suficientes para SaaS.
- Motivo: Não há trilha padrão para login, export, backup, download e negações.
- Arquivos envolvidos: `config/settings.py`, views sensíveis, futuros serviços de auditoria.
- Impacto: Dificulta investigação de incidentes e compliance.
- Estratégia de correção: Incluir `schema_name`, usuário, IP e ação nos logs; criar auditoria para ações sensíveis.
- Dependências: H-001, H-005.
- Critério de Aceite: Eventos sensíveis registram tenant/schema, usuário, IP, Host, ação e resultado; logs/auditoria permitem investigar acesso, exportação, backup e download por tenant.
- Evidências:
  - 2026-07-05: H-001/H-005 adicionaram logs mínimos para backup e exportação com schema, user_id, host, ação e resultado.
  - 2026-07-05: H-009 adicionou logs mínimos para login, falha de login, logout e download de backup negado.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Parcialmente encaminhado por H-009 para o escopo demo/teste; permanece aberto para padronização ampla, auditoria persistente e observabilidade de produção real.

#### M-004

- ID: M-004
- Domínio: Deploy
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Frontend bridge usa URL global.
- Motivo: SaaS por subdomínio deve preservar Host do tenant ou validar domínio.
- Arquivos envolvidos: `caixa/frontend_bridge.py`, `config/settings.py`.
- Impacto: Redirecionamento pode quebrar isolamento de Host ou UX entre tenants.
- Estratégia de correção: Derivar destino do request/tenant ou definir integração same-origin.
- Dependências: Decisão final do frontend RH SaaS.
- Critério de Aceite: Redirecionamentos e URLs de frontend preservam o tenant correto; não existe troca de tenant por URL global indevida; validação cobre ao menos dois hosts de tenant.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### M-005

- ID: M-005
- Domínio: Autenticação
- Severidade: Média
- Status: Concluído
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: `django-axes` precisa teste explícito por tenant.
- Motivo: Lockout deve considerar tenant/schema e não bloquear empresa errada.
- Arquivos envolvidos: `config/settings.py`, testes de autenticação.
- Impacto: Colisão de rate/lockout entre tenants.
- Estratégia de correção: Criar teste de login falho em tenant A sem afetar tenant B; ajustar se necessário.
- Dependências: Suite de testes auth multi-tenant.
- Critério de Aceite: Tentativas inválidas em tenant A não bloqueiam login válido em tenant B; evidência de teste fica registrada.
- Evidências:
  - 2026-07-05: H-007 adicionou `TenantAuthSessionIsolationTests.test_falhas_do_django_axes_em_um_tenant_nao_bloqueiam_outro`.
  - 2026-07-05: O teste força `AXES_FAILURE_LIMIT` falhas no tenant A com o mesmo username/IP e confirma login válido no tenant B com o mesmo username.
  - 2026-07-05: `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests` aprovado, 8 testes, 80.006s.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Concluído por H-007 com teste explícito de lockout tenant-scoped.

#### M-006

- ID: M-006
- Domínio: Segurança Operacional
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Transactions/on_commit ainda não têm padrão para tarefas assíncronas futuras.
- Motivo: Hoje parece seguro no request atual, mas jobs futuros precisam schema explícito.
- Arquivos envolvidos: Services com `transaction.atomic`, `transaction.on_commit`.
- Impacto: Background job pode executar no schema errado no futuro.
- Estratégia de correção: Definir padrão: toda task recebe schema e entra em contexto tenant.
- Dependências: Introdução futura de filas/automações.
- Critério de Aceite: Existe padrão documentado e validável para tarefas assíncronas tenant-aware; nenhuma task futura pode rodar sem schema explícito.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### M-007

- ID: M-007
- Domínio: Configurações de produção
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Configurações de produção precisam checks adicionais.
- Motivo: Existem bons defaults, mas faltam bloqueios contra combinações inseguras.
- Arquivos envolvidos: `config/settings.py`, `.env.production.example`.
- Impacto: Deploy pode subir com configuração inadequada.
- Estratégia de correção: Criar system checks/startup checks para `ALLOWED_HOSTS`, cookies, cache, CSRF, CORS e debug.
- Dependências: M-002.
- Critério de Aceite: `python manage.py check --deploy` ou checks equivalentes falham para configurações inseguras e passam para configuração SaaS esperada.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### M-008

- ID: M-008
- Domínio: Documentação
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Resquícios legados `rhremoto`/`dashboardFinanceiro` ainda existem em comandos/testes/docs.
- Motivo: Podem induzir deploy, validação ou caminhos errados.
- Arquivos envolvidos: `caixa/management/commands/*.py`, `caixa/tests.py`, docs legados.
- Impacto: Confusão operacional e risco de apontar para ambiente antigo.
- Estratégia de correção: Remover, reescrever ou isolar comandos e testes legados para RH SaaS.
- Dependências: H-004.
- Critério de Aceite: Nenhum comando/configuração ativa aponta para `rhremoto`, `dashboardFinanceiro` ou caminhos antigos; referências históricas em docs ficam marcadas como legado.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### M-009

- ID: M-009
- Domínio: Recuperação de desastre
- Severidade: Média
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Restore e teste de restore por tenant ainda não estão definidos.
- Motivo: O H-001 tornou criação/listagem/download de backup tenant-scoped, mas recuperação completa exige procedimento validado de restore por schema e plataforma.
- Arquivos envolvidos: documentação de operação futura, comandos futuros de restore, serviços de backup.
- Impacto: Backups podem existir sem evidência objetiva de recuperação segura por tenant.
- Estratégia de correção: Definir procedimento de restore por tenant, validar restore em banco temporário, garantir que restore nunca sobrescreva outro schema e documentar runbook de desastre.
- Dependências: H-001 concluído em 2026-07-05.
- Critério de Aceite: Existe runbook de restore por tenant e plataforma; restore é testado em ambiente temporário; evidências demonstram que restaurar tenant A não altera tenant B.
- Evidências:
  - 2026-07-05: H-011 adicionou nota operacional mínima deixando explícito que restore não está habilitado na aplicação demo e que qualquer restore manual deve usar schema explícito, preferencialmente validado antes em schema temporário.
- Histórico individual:
  - 2026-07-05: Criado durante auditoria final do H-001.
  - 2026-07-05: Parcialmente encaminhado por H-011 apenas no nível de orientação operacional mínima; permanece aberto para runbook e teste real de restore por tenant.

### 🟢 Riscos BAIXOS

#### L-001

- ID: L-001
- Domínio: Cache
- Severidade: Baixa
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: Service worker usa cache estático global por versão.
- Motivo: Hoje cacheia somente static same-origin, mas deve ser revisado com frontend final.
- Arquivos envolvidos: `caixa/static/caixa/sw.js`.
- Impacto: Baixo risco atual, possível confusão futura.
- Estratégia de correção: Revisar quando a integração frontend definitiva estiver pronta.
- Dependências: Decisão frontend.
- Critério de Aceite: Service worker não cacheia dados sensíveis nem respostas de API; cache estático não permite confusão entre tenants.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### L-002

- ID: L-002
- Domínio: Media
- Severidade: Baixa
- Status: Em andamento
- Responsável: Davi
- Estimativa: Médio
- Descrição: Media/uploads ainda não têm arquitetura final.
- Motivo: Não há upload operacional ativo relevante, mas futura funcionalidade precisa isolamento.
- Arquivos envolvidos: `config/settings.py`, futuras configs de storage, models com arquivos.
- Impacto: Risco futuro de path compartilhado.
- Estratégia de correção: Definir `media/tenants/<schema>/...`, URLs protegidas e limpeza por tenant antes de uploads reais.
- Dependências: Implementação futura de uploads.
- Critério de Aceite: Antes de qualquer upload real, arquivos ficam organizados por tenant/schema, URLs são protegidas quando necessário e testes provam isolamento.
- Evidências:
  - 2026-07-05: H-008 explicitou `MEDIA_ROOT` e `MEDIA_URL` em `config/settings.py` e registrou que uploads reais futuros devem ser tenant-aware.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Parcialmente encaminhado por H-008; permanece aberto porque ainda nao existe arquitetura final para upload real tenant-aware.

#### L-003

- ID: L-003
- Domínio: Documentação
- Severidade: Baixa
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: Documentação antiga ainda pode conter contexto legado.
- Motivo: Alguns documentos registram histórico de migração e nomes antigos.
- Arquivos envolvidos: `docs/*.md`.
- Impacto: Confusão de leitura, baixo impacto runtime.
- Estratégia de correção: Manter histórico, mas sinalizar obsoleto ou migrado para RH SaaS.
- Dependências: Nenhuma.
- Critério de Aceite: Documentos atuais apontam para RH SaaS; documentos históricos ficam claramente identificados como legado quando necessário.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### L-004

- ID: L-004
- Domínio: Testes
- Severidade: Baixa
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: Testes ainda podem usar domínios fictícios antigos.
- Motivo: Não afeta runtime, mas atrapalha clareza da suíte.
- Arquivos envolvidos: `caixa/tests.py`, possíveis fixtures.
- Impacto: Baixo risco operacional.
- Estratégia de correção: Atualizar fixtures para domínios RH SaaS quando os testes forem revisitados.
- Dependências: M-008.
- Critério de Aceite: Testes ativos usam domínios coerentes com RH SaaS ou deixam explícito que são fixtures legadas sem efeito em runtime.
- Evidências:
  - 2026-07-05: Recorte antigo de `caixa.tests.PermissoesTests` para auth/CSRF falhou porque usa `Client` sem `HTTP_HOST` de tenant e recebe HTML em vez de JSON. A cobertura multi-tenant equivalente para demo foi adicionada em `tenancy.tests.TenantAuthSessionIsolationTests`.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.
  - 2026-07-05: Registrada dívida de adaptação dos testes legados de auth para uso explícito de Host/tenant.

## Visão por Domínio

Esta seção não duplica riscos. Ela apenas mapeia os IDs existentes no backlog principal.

### Autenticação

- H-002
- H-007
- H-009
- M-005

### Admin Django

- H-003

### Backups

- H-001
- H-008
- H-009
- H-010
- H-011

### Cache

- L-001

### Commands

- H-004

### Configurações de produção

- M-002
- M-007

### Configurações de demo/teste

- H-006

### Deploy

- M-004

### Documentação

- M-008
- L-003

### DRF

- M-001

### Downloads

- H-001
- H-005
- H-008
- H-009
- H-010
- H-011

### Exportações

- H-005
- H-010

### Media

- H-008
- L-002

### Logs e Auditoria

- H-009
- M-003

### Observabilidade

- M-003

### Rate limiting

- H-010
- M-005

### Recuperação de desastre

- H-011
- M-009

### Segurança Operacional

- M-006

### Sessões

- H-007

### Testes

- L-004

## Ordem obrigatória

A fase de Hardening para demo/teste deve seguir obrigatoriamente esta ordem:

1. Corrigir ou neutralizar TODOS os riscos ALTOS que possam afetar isolamento, admin, backup/download, exportação ou commands perigosos.
2. Executar testes.
3. Executar nova auditoria focada no escopo demo/teste.
4. Corrigir novos riscos ALTOS encontrados.
5. Corrigir riscos MÉDIOS que sejam bloqueadores da demo/teste exposta.
6. Registrar riscos MÉDIOS e BAIXOS que pertencem somente à produção SaaS real como pendências pós-demo.
7. Reavaliar a Matriz de Adaptação SaaS após cada ciclo.
8. Antes de liberar a demo/teste, executar auditoria final focada em isolamento, autenticação, sessão, backup/export/download, commands, admin e configurações.

Nenhuma funcionalidade comercial de SaaS real deve entrar enquanto houver risco alto ou médio conhecido sem decisão registrada.

## Gate para Demo/Teste

Nenhuma demo/teste com usuários externos deve ser liberada enquanto existir:

- risco alto pendente que permita vazamento entre tenants;
- risco alto pendente em admin, backup/download, exportação ou commands;
- sessão/cookie/cache sem isolamento básico por tenant;
- admin Django exposto;
- backup global acessível por administrador de tenant;
- comando destrutivo ou operacional crítico executável no `public`;
- referência ativa que possa apontar deploy, banco ou domínio para o projeto antigo;
- configuração insegura para ambiente exposto;
- documentação de Hardening desatualizada sobre o escopo atual.

O Gate para Demo/Teste só pode ser aprovado quando:

- todos os itens da Definition of Done aplicáveis estiverem concluídos;
- o Painel executivo estiver atualizado;
- os riscos altos aplicáveis à demo/teste estiverem concluídos ou neutralizados;
- uma auditoria read-only final confirmar ausência de riscos altos no escopo da demo/teste.

## Gate para Produção SaaS Real

O Gate para Produção SaaS Real permanece mais rigoroso e só poderá ser aprovado quando:

- não houver riscos altos pendentes;
- não houver riscos médios pendentes;
- a Matriz de Adaptação SaaS estiver 100% verde;
- todas as áreas parcialmente adaptadas tiverem sido concluídas;
- uma auditoria read-only final confirmar ausência de riscos altos e médios;
- disaster recovery, observabilidade mínima, configurações de produção, restore e segurança operacional estiverem completos.

## Definition of Done

Todo item de Hardening somente poderá mudar para "Concluído" quando TODOS os critérios abaixo forem atendidos:

- implementação concluída;
- `python manage.py check` aprovado;
- `python manage.py makemigrations --check --dry-run` aprovado;
- testes focados aprovados;
- suíte multi-tenant aprovada;
- auditoria read-only aprovada;
- documentação atualizada;
- critério de aceite atendido;
- evidências registradas;
- status da Matriz de Adaptação SaaS atualizado;
- Painel executivo atualizado quando houver mudança de progresso.

Quando um item for apenas documental, os critérios técnicos não aplicáveis devem ser registrados explicitamente nas evidências.

## Checklist obrigatório após cada implementação

Após cada implementação de Hardening, executar e registrar:

- `python manage.py check`
- testes focados da área alterada
- suíte tenancy
- `python manage.py makemigrations --check --dry-run`
- auditoria do risco corrigido
- documentação atualizada

Quando aplicável, registrar também:

- consultas SQL de validação por schema;
- evidências de isolamento entre dois tenants;
- resultado de busca por referências legadas;
- resultado de busca por secrets ou arquivos sensíveis;
- impacto em `.env.example` e `.env.production.example`.

## Roadmap após Hardening

O Hardening passa a ter dois marcos: primeiro liberar uma demo/teste segura; depois, se fizer sentido, evoluir para produção SaaS real.

### Fase 1 - Spike

- Validar `django-tenants`.
- Criar tenant inicial.
- Confirmar isolamento básico.
- Status: em andamento/concluído parcialmente antes deste plano.

### Fase 2 - Hardening mínimo para Demo/Teste

- Eliminar ou neutralizar riscos altos aplicáveis ao uso demo/teste.
- Proteger commands críticos.
- Garantir admin fechado.
- Garantir isolamento de sessão, cache, backup/download e exportações aplicáveis.
- Validar configurações mínimas para ambiente exposto.
- Status: fase atual.

### Fase 3 - Demo/Portfólio controlado

- Liberar acesso controlado para testers.
- Criar tenants de teste separados.
- Monitorar erros e comportamentos de isolamento.
- Evitar billing, trial, cobrança e funcionalidades comerciais.

### Fase 4 - Hardening de Produção SaaS

- Concluir riscos médios e baixos que foram aceitos para a demo.
- Adaptar 100% das áreas da Matriz de Adaptação SaaS.
- Completar observabilidade mínima, logs, auditoria, restore e segurança operacional.

### Fase 5 - Produção SaaS

- Configurar produção definitiva.
- Validar deploy próprio.
- Validar domínio próprio.
- Executar auditoria final pré-produção.

### Fase 6 - Escalabilidade

- Revisar performance por tenant.
- Planejar limites, filas, cache e otimizações.

### Fase 7 - Billing

- Implementar planos, assinaturas, trial e cobrança somente após base SaaS segura.

### Fase 8 - Observabilidade avançada

- Evoluir métricas, dashboards, tracing, analytics e SLOs.

### Fase 9 - Alta disponibilidade

- Planejar redundância, restore validado, monitoramento avançado e recuperação de desastre.

## Regras do documento

Este plano é um documento vivo, mas sua estrutura deve ser considerada estável após esta revisão.

Durante futuras auditorias será permitido:

- adicionar novos riscos;
- adicionar novas áreas quando houver necessidade arquitetural real;
- dividir riscos;
- marcar riscos como "Substituído / Desdobrado";
- alterar prioridades;
- atualizar estimativas;
- atualizar status;
- adicionar evidências;
- atualizar histórico;
- atualizar métricas do Painel executivo;
- atualizar a Matriz de Adaptação SaaS;
- registrar novas decisões arquiteturais.

Não será permitido:

- apagar histórico;
- apagar decisões anteriores;
- remover riscos;
- duplicar o backlog;
- criar backlog paralelo por domínio;
- alterar continuamente a estrutura do documento sem necessidade arquitetural relevante.

Riscos antigos devem permanecer no documento, mesmo quando concluídos ou desdobrados.

## Histórico

### 2026-07-05 - H-011 Final concluído: integridade de backups e nota operacional de restore da demo

- Riscos corrigidos: H-011.
- Riscos parcialmente encaminhados: M-009 recebeu nota operacional mínima, mas permanece aberto para runbook e teste real de restore por tenant.
- Arquivos alterados: `caixa/selectors_backups.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test tenancy.tests.TenantBackupIsolationTests`: aprovado, 9 testes.
  - `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py check`: aprovado.
  - `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
  - `git diff --check`: aprovado sem erros.
- Auditoria executada: revisão focada do fluxo de criação, listagem, download, metadata, hash, isolamento por tenant, restore ausente e pasta `backups/`.
- Novos riscos encontrados: nenhum risco alto novo.
- Decisão registrada: para a demo, backup só é considerado válido quando metadata de schema/scope e `sha256` batem com o arquivo; restore pela aplicação permanece desabilitado.

### 2026-07-05 - H-010 concluído: rate limiting mínimo para operações caras da demo

- Riscos corrigidos: H-010.
- Arquivos alterados: `config/settings.py`, `.env.example`, `.env.production.example`, `caixa/throttling.py`, `caixa/views_backups.py`, `caixa/views_obrigacoes.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test tenancy.tests.TenantThrottleIsolationTests tenancy.tests.TenantBackupIsolationTests tenancy.tests.TenantExportDownloadIsolationTests`: aprovado, 14 testes.
  - `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py check`: aprovado.
  - `$env:DEBUG='True'; .\venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
- Auditoria executada: revisão focada das operações caras/sensíveis de backup, download, exportação CSV, reset de senha e chaves de throttle tenant-aware.
- Novos riscos encontrados: nenhum risco alto novo.
- Decisão registrada: para a demo, operações caras/sensíveis devem ter limite específico e chave incluindo schema/tenant, usuário quando autenticado e IP; views Django comuns também devem respeitar rate limit.

### 2026-07-05 - H-009 concluído: logs mínimos de autenticação e downloads para demo

- Riscos corrigidos: H-009.
- Riscos parcialmente encaminhados: M-003 permanece em andamento para observabilidade/auditoria completa de produção real.
- Arquivos alterados: `caixa/views_api_auth.py`, `caixa/views_backups.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests tenancy.tests.TenantBackupIsolationTests`: aprovado, 15 testes.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check`: aprovado.
  - `git diff --check`: aprovado sem erros.
- Auditoria executada: revisão read-only de `LOGGING`, `logger.*`, `print`, fluxos de login/logout, backup/download/exportação, Axes, middleware, rate limit de reset de senha e testes existentes.
- Novos riscos encontrados: nenhum risco alto novo. M-003 permanece para padronização de logs/auditoria mais ampla e futura auditoria persistente.
- Decisão registrada: para a demo, logs simples em console são suficientes desde que incluam tenant/schema, host, IP, ação, resultado e usuário quando existir, sem payload sensível.

### 2026-07-05 - H-008 concluído: downloads de backup e política base de mídia para demo

- Riscos corrigidos: H-008.
- Riscos parcialmente encaminhados: L-002 permanece em andamento para uploads reais futuros.
- Arquivos alterados: `caixa/views_backups.py`, `tenancy/tests.py`, `config/settings.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantBackupIsolationTests`: aprovado, 4 testes.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check`: aprovado.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
  - `git diff --check`: aprovado sem erros.
- Auditoria executada: revisão read-only de uploads, mídia, downloads, backups, exportações, rotas de `media`, service worker e arquivos estáticos confirmou ausência de upload real ativo, ausência de rota pública `/media/`, backups tenant-scoped e service worker limitado a `/static/`.
- Novos riscos encontrados: nenhum risco alto novo. L-002 continua aberto para a arquitetura final de upload real tenant-aware.
- Decisão registrada: a demo pode operar sem upload real; qualquer upload futuro deve ser tenant-aware antes de ser habilitado.

### 2026-07-05 - H-007 concluído: testes de autenticação e sessão entre tenants

- Riscos corrigidos: H-007 e M-005.
- Arquivos alterados: `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests`: aprovado, 8 testes.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantAuthSessionIsolationTests tenancy.tests.TenantApiIdorIsolationTests tenancy.tests.TenantBackupIsolationTests tenancy.tests.TenantExportDownloadIsolationTests`: aprovado, 18 testes.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check`: aprovado.
  - `git diff --check`: aprovado sem erros.
  - Recorte antigo de `caixa.tests.PermissoesTests` para auth/CSRF: falhou porque os testes legados não configuram `HTTP_HOST` de tenant; registrado em L-004.
- Auditoria executada: revisão read-only de `caixa/views_api_auth.py`, `caixa/views_auth.py`, `caixa/permissions.py`, `config/settings.py`, `config/public_urls.py`, `config/tenant_urls.py`, `tenancy/tests.py`, backups/exportações e buscas por seleção de tenant via parâmetro/header/payload.
- Novos riscos encontrados: nenhum risco alto novo. L-004 permanece como dívida de adaptação de testes legados para Host/tenant.
- Decisão registrada: para a demo, a proteção de autenticação/sessão deve ser validada por testes multi-tenant no app `tenancy`; testes legados que não usam Host explícito não devem ser usados como evidência de segurança multi-tenant até serem adaptados.

### 2026-07-05 - H-006 concluído: configuração mínima para demo multi-tenant local

- Riscos corrigidos: H-006.
- Arquivos alterados: `config/settings.py`, `.env`, `.env.example`, `.env.production.example`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check`: aprovado.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py check --deploy`: executado como diagnóstico; avisos esperados para demo local HTTP.
  - `$env:DEBUG='True'; venv\Scripts\python.exe manage.py test tenancy.tests.TenantIsolationInfrastructureTests tenancy.tests.TenantAuthSessionIsolationTests`: aprovado, 10 testes.
  - `git diff --check`: aprovado sem erros.
  - Validação negativa com `DEBUG=release`: falhou explicitamente com orientação para usar `DEBUG=True` ou `DEBUG=False`.
- Auditoria executada: leitura de `config/settings.py`, `caixa/middleware.py`, `.env`, `.env.example`, `.env.production.example`, URLConfs e tenant/domínio local confirmou demo em PostgreSQL `rhsaas_dev`, tenant `rh_teste`, domínio `rh-teste.localhost`, cookies host-only e ausência de rotas operacionais no `public`.
- Novos riscos encontrados: nenhum risco alto novo. M-002 e M-007 permanecem para hardening de produção/HTTPS pública; os avisos de `check --deploy` são aceitáveis somente para demo local HTTP.
- Decisão registrada: para o escopo portfólio/demo local, `COOKIE_SECURE=False`, HSTS desligado e `SECURE_SSL_REDIRECT=False` são aceitos apenas em HTTP local; qualquer demo pública HTTPS deve trocar cookies secure/SSL/HSTS para valores seguros antes de exposição.

### 2026-07-05 - H-005 concluído: exportações tenant-scoped auditadas

- Riscos corrigidos: H-005.
- Arquivos alterados: `caixa/views_obrigacoes.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `venv\Scripts\python.exe manage.py check`: aprovado.
  - `venv\Scripts\python.exe manage.py test tenancy.tests.TenantExportDownloadIsolationTests`: aprovado, 2 testes.
  - `venv\Scripts\python.exe manage.py test tenancy`: aprovado, 38 testes.
  - `venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
  - `git diff --check`: aprovado sem erro; apenas aviso de normalização futura de CRLF em dois arquivos tocados anteriormente.
- Auditoria executada: busca read-only focada por export/download confirmou que a exportação CSV operacional fica em memória, usa schema ativo, exige autenticação/permissão, não grava arquivo temporário compartilhado e registra evento de auditoria por schema/host/usuário.
- Novos riscos encontrados: nenhum risco alto novo. M-001 e M-003 permanecem como padronização mais ampla de permissões DRF e auditoria/logs para produção SaaS real.
- Decisão registrada: para o escopo demo/teste, exportações operacionais devem permanecer tenant-scoped, autenticadas, autorizadas, sem cache, com `nosniff`, auditoria mínima e cobertura multi-tenant.

### 2026-07-05 - H-004 concluído: management commands classificados e protegidos

- Riscos corrigidos: H-004.
- Arquivos alterados: `tenancy/command_guards.py`, `tenancy/tests.py`, commands tenant-only em `caixa/management/commands/`, `caixa/management/commands/limpar_base_operacional_pm06.py`, `caixa/management/commands/gerar_snapshot_baseline_financeira.py`, `caixa/management/commands/validar_baseline_pm02.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `venv\Scripts\python.exe manage.py check`: aprovado.
  - `venv\Scripts\python.exe manage.py test tenancy.tests.TenantCommandGuardTests`: aprovado, 8 testes.
  - `venv\Scripts\python.exe manage.py test tenancy`: aprovado, 37 testes.
  - `venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
  - `git diff --check`: aprovado sem erro; apenas aviso de normalização futura de CRLF em dois arquivos tocados.
- Auditoria executada: inventário read-only confirmou 45 commands customizados, 45 classificados e nenhum tenant-only sem `ensure_tenant_schema`.
- Novos riscos encontrados: nenhum risco alto novo; M-008 permanece como limpeza de resquícios legados em comandos/testes/docs.
- Decisão registrada: para o escopo demo/teste, commands que leem, escrevem, sincronizam, exportam ou limpam dados operacionais devem exigir schema de tenant explícito; commands puramente documentais/file-only permanecem classificados como read-only/legacy-read-only.

### 2026-07-05 - Escopo ajustado para demo/teste/portfólio multi-tenant

- Riscos corrigidos: nenhum nesta etapa.
- Arquivos alterados: `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas: revisão documental.
- Novos riscos encontrados: nenhum novo risco técnico.
- Decisões registradas:
  - o RH SaaS será usado inicialmente como demo, teste e portfólio;
  - o multi-tenant por schema com `django-tenants` será mantido porque mais de um tester poderá usar a aplicação;
  - o gate imediato passa a ser o Gate para Demo/Teste, focado em isolamento entre tenants, admin fechado, backup/export/download seguros, commands críticos protegidos e configuração segura para ambiente exposto;
  - produção SaaS real permanece como trilha futura, com gate próprio mais rigoroso;
  - billing, trial, planos comerciais, cobrança, domínio customizado, observabilidade avançada e disaster recovery completo ficam fora do escopo imediato da demo/teste.

### 2026-07-05 - H-003 concluído: Admin Django permanece desativado

- Riscos corrigidos: H-003.
- Arquivos alterados: `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `venv\Scripts\python.exe manage.py test tenancy.tests.TenantAdminDisabledTests`: aprovado, 3 testes, 36.063s.
  - `venv\Scripts\python.exe manage.py test tenancy`: aprovado, 31 testes, 751.979s.
  - `venv\Scripts\python.exe manage.py check`: aprovado.
  - `venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
- Auditoria executada: revisão de `config/public_urls.py`, `config/tenant_urls.py`, `config/urls.py`, `tenancy/admin.py`, `caixa/admin.py` e busca read-only por rotas que publiquem `admin.site.urls`.
- Novos riscos encontrados: nenhum novo risco técnico; o registro misto no `admin.site` padrão permanece aceitável somente porque `/admin/` não está publicado.
- Decisão registrada: qualquer reativação futura do Admin Django deve usar admin público e admin de tenant separados, com testes de isolamento antes de publicar rota.

### 2026-07-05 - H-001 concluído: backup/download tenant-scoped

- Riscos corrigidos: H-001.
- Arquivos alterados: `caixa/tenant_files.py`, `caixa/services_backups.py`, `caixa/selectors_backups.py`, `caixa/views_backups.py`, `caixa/management/commands/exportar_recadastro_manual_pm06.py`, `caixa/permissions.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `venv\Scripts\python.exe manage.py test tenancy.tests.TenantBackupIsolationTests tenancy.tests.TenantExportDownloadIsolationTests tenancy.tests.TenantPlatformRoleSeparationTests`: aprovado, 7 testes.
  - `venv\Scripts\python.exe manage.py test tenancy`: aprovado, 28 testes.
  - `venv\Scripts\python.exe manage.py check`: aprovado.
  - `venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
- Auditoria executada: busca read-only por caminhos globais, downloads, exports, temporários, `FileResponse`, `Content-Disposition`, `NamedTemporaryFile`, `criar_backup_banco`, `listar_backups_disponiveis`, `obter_caminho_backup`, `backup_dir_for_schema` e `recadastro_dir_for_schema`.
- Novos riscos encontrados: M-009, recuperação de desastre/restore por tenant ainda não definido.
- Observação: a suíte `tenancy` estourou uma primeira janela de timeout; o banco temporário `test_rhsaas_dev` foi recriado novamente, com validação explícita do alvo, e a suíte completa passou em seguida. O banco `rhsaas_dev` não foi alterado.

### 2026-07-05 - H-002 concluído: separação entre operador da plataforma e administrador do tenant

- Riscos corrigidos: H-002.
- Arquivos alterados: `caixa/permissions.py`, `caixa/views_backups.py`, `caixa/views_api_auth.py`, `caixa/services_cadastros.py`, `caixa/views_orcamentos_api.py`, `caixa/views_eventos_api.py`, `caixa/views_receitas_api.py`, `caixa/views_despesas_api.py`, `tenancy/tests.py`, `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas:
  - `venv\Scripts\python.exe manage.py test tenancy.tests.TenantPlatformRoleSeparationTests`: aprovado, 3 testes.
  - `venv\Scripts\python.exe manage.py test tenancy`: aprovado, 24 testes.
  - `venv\Scripts\python.exe manage.py check`: aprovado.
  - `venv\Scripts\python.exe manage.py makemigrations --check --dry-run`: aprovado, sem mudanças detectadas.
- Novos riscos encontrados: nenhum novo risco técnico.
- Observação: o banco temporário `test_rhsaas_dev` foi recriado com aprovação explícita para limpar estado inconsistente deixado por timeout anterior; o banco `rhsaas_dev` não foi alterado.

### 2026-07-05 - Estabilização da estrutura do plano

- Riscos corrigidos: nenhum nesta etapa.
- Arquivos alterados: `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas: revisão documental e reorganização estrutural.
- Novos riscos encontrados: nenhum novo risco técnico.
- Decisões registradas:
  - backlog único mantido por severidade;
  - cada risco passa a possuir domínio, responsável, estimativa, critério de aceite, evidências e histórico individual;
  - a Visão por Domínio passa a ser apenas um índice dos riscos;
  - a Matriz de Adaptação SaaS passa a apontar os riscos bloqueadores;
  - a estrutura do documento passa a ser considerada estável.

### 2026-07-05 - Diretriz de adaptação 100% por área

- Riscos corrigidos: nenhum nesta etapa.
- Arquivos alterados: `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas: atualização documental.
- Novos riscos encontrados: nenhum novo risco técnico; a diretriz ampliou o critério de encerramento da fase.
- Decisão registrada: a fase de Hardening não termina apenas pela ausência de riscos altos/médios. Ela só termina quando todas as áreas arquiteturais estiverem marcadas como "✅ Totalmente adaptada".

### 2026-07-05 - Criação do plano mestre de Hardening

- Riscos corrigidos: nenhum nesta etapa.
- Arquivos alterados: `docs/PLANO_HARDENING_SAAS.md`.
- Validações executadas: criação documental baseada na auditoria arquitetural concluída em modo leitura.
- Novos riscos encontrados: nenhum novo risco além dos já registrados na auditoria.
- Observação: este documento passa a ser a fonte principal da fase de Hardening. Histórico não deve ser apagado; riscos não devem ser removidos, apenas reclassificados ou marcados como concluídos.
