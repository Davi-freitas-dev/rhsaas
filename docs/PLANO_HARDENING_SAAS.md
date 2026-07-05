# Plano de Hardening SaaS - RH SaaS

Documento vivo da fase de Hardening do RH SaaS.

Criado em: 2026-07-05

## Painel executivo

### Hardening

- Status geral: 🔴 Em andamento
- Objetivo atual: eliminar riscos conhecidos e adaptar 100% da arquitetura ao modelo SaaS multi-tenant por schema.
- Evolução funcional: bloqueada enquanto o Gate para Evolução do Projeto não for aprovado.

### Progresso geral

| Métrica | Progresso |
| --- | --- |
| Áreas totalmente adaptadas | 8 / 30 |
| Riscos altos concluídos | 3 / 5 |
| Riscos médios concluídos | 0 / 9 |
| Riscos baixos concluídos | 0 / 4 |

Este painel deve ser atualizado a cada implementação, auditoria ou reclassificação de riscos.

## Objetivo

Paralisar a evolução funcional do RH SaaS enquanto existirem riscos conhecidos de isolamento, segurança ou escalabilidade ligados à arquitetura SaaS multi-tenant.

A prioridade absoluta desta fase é eliminar os riscos encontrados nas auditorias de segurança e arquitetura, especialmente qualquer possibilidade de:

- um tenant acessar dados de outro tenant;
- permissões de plataforma se confundirem com permissões de tenant;
- backups, exportações, downloads, cache ou sessões escaparem do schema correto;
- funcionalidades legadas single-tenant continuarem ativas em produção;
- configurações de produção permitirem uso inseguro de Host, cookies, CORS, CSRF ou admin.

O objetivo final não é apenas eliminar riscos isolados. O objetivo final é que todas as áreas da arquitetura sejam consideradas 100% adaptadas ao modelo SaaS multi-tenant por schema.

Nenhuma área poderá permanecer com status "Parcialmente adaptada" ao final da fase de Hardening.

Status permitidos para cada área:

- ❌ Não adaptada
- 🟡 Parcialmente adaptada
- ✅ Totalmente adaptada

Durante esta fase, nenhuma funcionalidade nova deve ser implementada enquanto houver risco alto, risco médio, área parcialmente adaptada, teste obrigatório pendente ou auditoria obrigatória pendente.

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

A fase de Hardening só poderá ser encerrada quando todos os critérios abaixo forem atendidos:

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
| Autenticação | 🟡 Parcialmente adaptada | M-005 | Separar operador da plataforma, usuário de tenant, superuser de tenant e staff sem ambiguidade |
| Sessões | ✅ Totalmente adaptada | - | Manter testes provando que sessão de um tenant não autentica outro tenant |
| Cache | 🟡 Parcialmente adaptada | L-001 | Manter prefixo por schema e revisar cache estático/frontend antes de produção |
| CSRF | 🟡 Parcialmente adaptada | M-002 | Validar política final para subdomínios, trusted origins e produção |
| Cookies | 🟡 Parcialmente adaptada | M-002 | Garantir cookies host-only em produção e checks contra domínio compartilhado |
| CORS | 🟡 Parcialmente adaptada | M-002 | Definir integração final frontend/backend sem wildcard inseguro |
| DRF | 🟡 Parcialmente adaptada | M-001 | Reduzir `AllowAny` e padronizar permissões explícitas por tenant |
| Middleware | ✅ Totalmente adaptada | - | Manter `TenantMainMiddleware` no início e testes de resolução por Host |
| Database Router | ✅ Totalmente adaptada | - | Manter `TenantSyncRouter` e validações de migrations por schema |
| django-tenants | ✅ Totalmente adaptada | - | Manter modelo de um schema por empresa e tenant identificado por Host |
| Commands | 🟡 Parcialmente adaptada | H-004, M-008 | Classificar e proteger todos os comandos operacionais |
| Signals | ✅ Totalmente adaptada | - | Manter signals operacionais bloqueados no `public` e cobertos por testes quando críticos |
| Backups | ✅ Totalmente adaptada | - | Backup/download tenant-scoped por schema, com autorização explícita e auditoria mínima por log |
| Exportações | 🟡 Parcialmente adaptada | H-005 | Padronizar export tenant-scoped, auditado, autorizado e testado com dois tenants |
| Uploads | 🟡 Parcialmente adaptada | L-002 | Definir arquitetura tenant-aware antes de qualquer upload real |
| Media | 🟡 Parcialmente adaptada | L-002 | Definir paths, URLs e limpeza por tenant |
| Logs | 🟡 Parcialmente adaptada | M-003 | Incluir tenant/schema, usuário, IP e ação em eventos relevantes |
| Auditoria | ❌ Não adaptada | M-003, H-005 | Criar trilha para login, logout, backup, export, download e ações administrativas |
| Admin Django | ✅ Totalmente adaptada | - | Manter `/admin/` desativado por teste até existir admin público e tenant separados |
| Services | 🟡 Parcialmente adaptada | H-005, M-006 | Revisar serviços sensíveis para schema ativo, permissões e ausência de globais |
| Selectors | 🟡 Parcialmente adaptada | H-005 | Revisar seletores para garantir queries tenant-scoped e sem leitura global indevida |
| Models | ✅ Totalmente adaptada | - | Separação validada entre models de `public` e models de tenant para a arquitetura atual |
| Managers | 🟡 Parcialmente adaptada | M-006 | Garantir que managers não escondam consultas globais nem dependam de single-tenant |
| QuerySets | 🟡 Parcialmente adaptada | M-001, H-005 | Testar listagem, detalhe, IDs iguais e filtros entre tenants |
| Testes | 🟡 Parcialmente adaptada | H-004, H-005, M-001, M-005, L-004 | Cobrir autenticação, permissões, API, backups, exportações, comandos e produção |
| Configurações de produção | 🟡 Parcialmente adaptada | M-002, M-007 | Adicionar checks para Host, cookies, CSRF, CORS, cache, debug e secrets |
| Deploy | 🟡 Parcialmente adaptada | M-007, M-008 | Documentar e validar deploy separado do projeto antigo, sem comandos legados |
| Observabilidade mínima | ❌ Não adaptada | M-003 | Ter logs, auditoria, alertas mínimos e identificação do tenant em eventos sensíveis |
| Recuperação de desastre | 🟡 Parcialmente adaptada | M-009 | Definir restore e teste de restore por tenant e plataforma |
| Segurança operacional | 🟡 Parcialmente adaptada | H-004, M-007, M-008 | Fechar procedimentos de acesso, comandos, secrets, auditoria e incidentes |

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
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Grande
- Descrição: Comandos operacionais ainda não estão todos classificados e protegidos.
- Motivo: Alguns comandos legados ou de validação podem ler, escrever ou exportar dados no schema errado.
- Arquivos envolvidos: `caixa/management/commands/*.py`.
- Impacto: Execução acidental em `public` ou tenant incorreto.
- Estratégia de correção: Classificar todos como `tenant-only`, `platform-only` ou `read-only`; exigir schema explícito quando aplicável; bloquear `public` para dados operacionais.
- Dependências: H-002 concluído em 2026-07-05.
- Critério de Aceite: Todos os comandos estão inventariados; comandos operacionais recusam schema `public`; comandos tenant-only exigem schema/tenant explícito; testes ou validações provam bloqueio de execução perigosa.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

#### H-005

- ID: H-005
- Domínio: Exportações
- Severidade: Alta
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Exportações e downloads ainda não possuem padrão SaaS completo.
- Motivo: Exportações dependem do schema ativo, mas ainda faltam padrão, auditoria, rate limit e testes de isolamento.
- Arquivos envolvidos: `caixa/views_obrigacoes.py`, comandos de exportação, futuras views de download.
- Impacto: Vazamento de dados por arquivo, cache, path ou permissão incorreta.
- Estratégia de correção: Criar serviço padrão tenant-scoped para export/download; auditar; limitar; testar tenant A vs tenant B.
- Dependências: H-002 concluído em 2026-07-05, M-001, M-003.
- Critério de Aceite: Exportações retornam apenas dados do schema atual; tenant A nunca exporta dados do tenant B; downloads são autenticados, autorizados, auditados e cobertos por testes.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

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
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Logs e auditoria ainda não são suficientes para SaaS.
- Motivo: Não há trilha padrão para login, export, backup, download e negações.
- Arquivos envolvidos: `config/settings.py`, views sensíveis, futuros serviços de auditoria.
- Impacto: Dificulta investigação de incidentes e compliance.
- Estratégia de correção: Incluir `schema_name`, usuário, IP e ação nos logs; criar auditoria para ações sensíveis.
- Dependências: H-001, H-005.
- Critério de Aceite: Eventos sensíveis registram tenant/schema, usuário, IP, Host, ação e resultado; logs/auditoria permitem investigar acesso, exportação, backup e download por tenant.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

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
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Pequeno
- Descrição: `django-axes` precisa teste explícito por tenant.
- Motivo: Lockout deve considerar tenant/schema e não bloquear empresa errada.
- Arquivos envolvidos: `config/settings.py`, testes de autenticação.
- Impacto: Colisão de rate/lockout entre tenants.
- Estratégia de correção: Criar teste de login falho em tenant A sem afetar tenant B; ajustar se necessário.
- Dependências: Suite de testes auth multi-tenant.
- Critério de Aceite: Tentativas inválidas em tenant A não bloqueiam login válido em tenant B; evidência de teste fica registrada.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

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
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado durante auditoria final do H-001.

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
- Status: Não iniciado
- Responsável: Davi
- Estimativa: Médio
- Descrição: Media/uploads ainda não têm arquitetura final.
- Motivo: Não há upload operacional ativo relevante, mas futura funcionalidade precisa isolamento.
- Arquivos envolvidos: Futuras configs `MEDIA_ROOT`, `MEDIA_URL`, models com arquivos.
- Impacto: Risco futuro de path compartilhado.
- Estratégia de correção: Definir `media/tenants/<schema>/...`, URLs protegidas e limpeza por tenant antes de uploads reais.
- Dependências: Implementação futura de uploads.
- Critério de Aceite: Antes de qualquer upload real, arquivos ficam organizados por tenant/schema, URLs são protegidas quando necessário e testes provam isolamento.
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

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
- Evidências: Nenhuma registrada ainda.
- Histórico individual:
  - 2026-07-05: Criado a partir da auditoria arquitetural.

## Visão por Domínio

Esta seção não duplica riscos. Ela apenas mapeia os IDs existentes no backlog principal.

### Autenticação

- H-002
- M-005

### Admin Django

- H-003

### Backups

- H-001

### Cache

- L-001

### Commands

- H-004

### Configurações de produção

- M-002
- M-007

### Deploy

- M-004

### Documentação

- M-008
- L-003

### DRF

- M-001

### Exportações

- H-005

### Media

- L-002

### Observabilidade

- M-003

### Recuperação de desastre

- M-009

### Segurança Operacional

- M-006

### Testes

- L-004

## Ordem obrigatória

A fase de Hardening deve seguir obrigatoriamente esta ordem:

1. Corrigir TODOS os riscos ALTOS.
2. Executar testes.
3. Executar nova auditoria.
4. Corrigir novos riscos ALTOS encontrados.
5. Somente quando não existir nenhum risco ALTO, iniciar riscos MÉDIOS.
6. Repetir o processo de implementação, testes e auditoria.
7. Somente quando não existir nenhum risco MÉDIO, iniciar riscos BAIXOS.
8. Reavaliar a Matriz de Adaptação SaaS após cada ciclo.
9. Antes de encerrar a fase, executar auditoria final completa.
10. Encerrar somente se todas as áreas estiverem "✅ Totalmente adaptada".

Nenhuma funcionalidade nova deve entrar enquanto houver risco alto ou médio conhecido sem decisão registrada.

## Gate para Evolução do Projeto

Nenhuma funcionalidade nova poderá ser iniciada enquanto existir:

- risco alto pendente;
- risco médio pendente;
- área parcialmente adaptada;
- área não adaptada;
- teste obrigatório pendente;
- auditoria obrigatória pendente;
- documentação de Hardening desatualizada;
- evidência obrigatória não registrada.

O Gate para Evolução do Projeto só pode ser aprovado quando:

- todos os itens da Definition of Done aplicáveis estiverem concluídos;
- o Painel executivo estiver atualizado;
- a Matriz de Adaptação SaaS estiver 100% verde;
- uma auditoria read-only final confirmar ausência de riscos altos e médios.

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

O Hardening continua bloqueando novas funcionalidades até ser encerrado pelo Gate para Evolução do Projeto.

### Fase 1 - Spike

- Validar `django-tenants`.
- Criar tenant inicial.
- Confirmar isolamento básico.
- Status: em andamento/concluído parcialmente antes deste plano.

### Fase 2 - Hardening

- Eliminar riscos altos, médios e baixos conforme este plano.
- Adaptar 100% das áreas da Matriz de Adaptação SaaS.
- Preparar produção segura.
- Status: fase atual.

### Fase 3 - Produção SaaS

- Configurar produção definitiva.
- Validar deploy próprio.
- Validar domínio próprio.
- Executar auditoria final pré-produção.

### Fase 4 - Escalabilidade

- Revisar performance por tenant.
- Planejar limites, filas, cache e otimizações.

### Fase 5 - Billing

- Implementar planos, assinaturas, trial e cobrança somente após base SaaS segura.

### Fase 6 - Observabilidade avançada

- Evoluir métricas, dashboards, tracing, analytics e SLOs.

### Fase 7 - Alta disponibilidade

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
