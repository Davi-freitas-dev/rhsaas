# Auditoria de Segurança - RH SaaS

Data: 2026-07-04

Escopo desta etapa: auditoria read-only do código e das configurações versionadas, com criação apenas deste documento. Não foram executadas migrations, deploy, push, atualização de dependências ou alteração de lógica de negócio.

## Legenda

- ✅ Existe: controle encontrado e aparentemente ativo.
- ⚠️ Parcial: controle existe, mas depende de configuração, cobre só parte do risco ou precisa de reforço para SaaS.
- ❌ Não existe: controle não encontrado no código auditado.
- ➕ Recomendado para depois: melhoria importante, mas não obrigatória para esta etapa.
- ❓ Não confirmado: exige validação fora do repositório local, como servidor, variáveis reais ou provedor de deploy.

## Evidências consultadas

- Git remoto e estado local.
- `.gitignore`, arquivos versionados e padrões de arquivos sensíveis.
- `config/settings.py`, `config/urls.py`, `caixa/urls.py`.
- Middlewares, permissões, autenticação, backups, serviços auxiliares e testes relacionados.
- Exemplos de ambiente e documentação de deploy.
- Buscas por referências a domínios, paths antigos, PDF, uploads, backups, tenant e secrets óbvios.

## 1. Ambiente e secrets

Status: ⚠️ Parcial

O projeto usa variáveis de ambiente para `SECRET_KEY`, `DATABASE_URL`, e-mail, CORS, CSRF, cookies e configurações de produção. Em produção, `settings.py` bloqueia `SECRET_KEY` ausente ou insegura quando `DEBUG=False`, o que reduz bastante o risco de subir com chave padrão.

Foi encontrada configuração defensiva para `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, cookies seguros e SSL redirect em produção. Também há exemplos `.env.example` e `.env.production.example`.

Pontos de atenção:

- ❓ Não confirmado: os valores reais do servidor/provedor de deploy não foram auditados.
- ⚠️ Parcial: o cache padrão é local em memória se `REDIS_URL` não estiver configurado, o que enfraquece rate limit em produção com múltiplos processos.
- ⚠️ Parcial: há exemplos e documentação com placeholders de segredo; não parecem ser secrets reais, mas uma varredura com ferramenta dedicada de secret scanning ainda é recomendável.
- ➕ Recomendado para depois: adicionar secret scanning no CI antes de abrir o projeto para mais colaboradores.

## 2. Git e arquivos sensíveis

Status: ✅ Existe

O `.gitignore` protege `.env`, bancos SQLite, backups locais, arquivos de backup JSON, `backups/`, `staticfiles/`, `media/`, logs, venvs e caches. A checagem de arquivos versionados não indicou `.env`, banco local, backups ou certificados privados rastreados.

O remoto Git aponta para o novo repositório `rhsaas`, não para o projeto antigo.

Pontos de atenção:

- ⚠️ Parcial: existe arquivo local não versionado `docs/ROADMAP_RH_SAAS.md`, criado antes desta auditoria. Ele não é sensível por si só, mas precisa entrar no commit correto se for desejado.
- ➕ Recomendado para depois: rodar uma auditoria de histórico Git se houver suspeita de que secrets tenham sido commitados no passado.

## 3. Deploy e domínio

Status: ⚠️ Parcial

Não foram encontrados arquivos ativos de Docker, Gunicorn, Nginx, systemd, Procfile, Render, Railway, Fly, Vercel ou Netlify no repositório. A separação principal parece estar concentrada em variáveis de ambiente e documentação.

O novo remoto Git está correto. Os exemplos de ambiente apontam para placeholders próprios do RH SaaS.

Pontos de atenção:

- ❓ Não confirmado: configuração real do servidor, DNS, proxy reverso, PM2/systemd e provedor de deploy.
- ⚠️ Parcial: documentação herdada ainda pode conter comandos ou nomes históricos, como referências de processo/deploy do projeto antigo.
- ➕ Recomendado para depois: criar um documento curto de deploy do RH SaaS com domínios, serviços e variáveis obrigatórias, sem caminhos pessoais.

## 4. Cookies, CSRF e CORS

Status: ✅ Existe

Foram encontrados controles consistentes para cookies, CSRF e CORS:

- `SESSION_COOKIE_HTTPONLY=True`.
- `CSRF_COOKIE_HTTPONLY=True`.
- `SESSION_COOKIE_SAMESITE=Lax`.
- `CSRF_COOKIE_SAMESITE=Lax`.
- cookies seguros por padrão quando `DEBUG=False`.
- `CSRF_TRUSTED_ORIGINS` configurável por ambiente.
- CORS por allowlist exata de origem.
- `CORS_ALLOW_CREDENTIALS=True`.
- middleware customizado adiciona `Vary: Origin` e só responde preflight para origem permitida.
- endpoints de login/logout API preservam proteção CSRF.

Pontos de atenção:

- ❓ Não confirmado: valores reais de `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` e domínios de cookie em produção.
- ➕ Recomendado para depois: validar em staging com domínio final e frontend final.

## 5. Autenticação e reset de senha

Status: ✅ Existe

O projeto usa autenticação Django, validadores de senha, hash Argon2 como primeira opção e `django-axes` para proteção contra tentativas de login. A API de login exige JSON, usa CSRF, aplica throttle específico e retorna erro genérico para credenciais inválidas.

O reset de senha possui rate limit por IP e e-mail via cache, com chave derivada por HMAC.

Pontos de atenção:

- ⚠️ Parcial: o rate limit de reset depende do backend de cache. Em produção SaaS, Redis deve ser obrigatório.
- ❓ Não confirmado: configuração real de e-mail transacional em produção.
- ➕ Recomendado para depois: adicionar alertas para muitos resets, muitos logins inválidos e lockouts.

## 6. Permissões e papéis

Status: ⚠️ Parcial

Existem decorators e helpers de permissão para views HTML e APIs, incluindo respostas 401/403 em JSON. Também existem perfis de permissões como Administrador, Financeiro e Operacional.

O acesso administrativo mais sensível ainda depende de `is_superuser`, especialmente em backups. Isso é correto para a versão atual de usuário único, mas não serve como modelo para clientes SaaS.

Pontos de atenção:

- ⚠️ Parcial: papéis atuais são globais, não vinculados a tenant/organização.
- ⚠️ Parcial: `is_superuser` não deve virar "admin do cliente" no SaaS.
- ➕ Recomendado para depois: criar papéis de aplicação separados de Django staff/superuser.

## 7. Backups e downloads

Status: ⚠️ Parcial

Backups estão protegidos por superuser no fluxo atual. A listagem, criação manual e download exigem superuser. O seletor de backups restringe nomes permitidos, bloqueia path traversal, exige prefixo esperado e valida arquivo dentro do diretório de backups.

O `.gitignore` protege `backups/` e arquivos de backup locais.

Pontos de atenção:

- ⚠️ Parcial: o backup atual é global, do banco inteiro.
- ⚠️ Parcial: o download por view Django direta não recebe throttle específico do DRF.
- ⚠️ Parcial: para SaaS, não é seguro liberar esse backup global para administradores de cliente que não sejam superuser.
- ➕ Recomendado para depois: separar "backup operacional da plataforma" de "exportação de dados do tenant".
- ➕ Recomendado para depois: adicionar rate limit e audit log para downloads/exportações.

## 8. Logs e dados sensíveis

Status: ⚠️ Parcial

Há configuração de logging para console, nível configurável da aplicação e tratamento genérico em pontos sensíveis. Views de autenticação usam decorators para evitar exposição de senha em relatórios de erro.

Pontos de atenção:

- ⚠️ Parcial: não há política central de mascaramento/redação de dados sensíveis em logs.
- ⚠️ Parcial: não foi encontrado audit log específico para downloads, backups, exportações e ações administrativas.
- ❓ Não confirmado: retenção e destino dos logs em produção.
- ➕ Recomendado para depois: registrar eventos de segurança sem gravar senhas, tokens, documentos ou payloads sensíveis.

## 9. Rate limits

Status: ⚠️ Parcial

Existem throttles globais do DRF para usuários anônimos e autenticados, throttle específico para login API, rate limit no reset de senha e proteção por `django-axes`.

Pontos de atenção:

- ⚠️ Parcial: views Django não-DRF, como download de backup, não ficam cobertas automaticamente pelos throttles do DRF.
- ⚠️ Parcial: LocMemCache não é suficiente para rate limit confiável em produção com múltiplos processos.
- ➕ Recomendado para depois: usar Redis em produção e adicionar limites no proxy reverso para login, reset, APIs e downloads.
- ➕ Recomendado para depois: criar limites específicos por tipo de exportação/download.

## 10. Admin Django

Status: ⚠️ Parcial

O `/admin/` está habilitado. Isso é aceitável como painel interno de manutenção, desde que fique restrito a staff/superusers internos. A documentação da API é protegida por `staff_member_required` quando habilitada.

Pontos de atenção:

- ⚠️ Parcial: clientes SaaS não devem acessar o Django Admin.
- ❓ Não confirmado: restrições reais de rede, domínio ou autenticação adicional no servidor.
- ➕ Recomendado para depois: documentar que o Admin Django é apenas interno e criar uma tela de administração SaaS dentro da aplicação.

## 11. APIs

Status: ⚠️ Parcial

As APIs usam DRF com `SessionAuthentication`, `IsAuthenticated` por padrão, throttles globais e documentação OpenAPI protegida para staff quando habilitada. Vários endpoints usam wrappers próprios de permissão e preservam CSRF em operações autenticadas.

Pontos de atenção:

- ⚠️ Parcial: alguns endpoints declaram `AllowAny` e fazem checagem manual internamente. Isso pode estar correto no padrão atual, mas aumenta o risco de regressão se alguém esquecer a checagem manual.
- ⚠️ Parcial: ainda não há modelo de API pública com token, escopo, rotação e auditoria.
- ⚠️ Parcial: endpoints ainda não são tenant-aware.
- ➕ Recomendado para depois: padronizar permissões DRF e criar testes de autorização para endpoints críticos.

## 12. Preparação para multi-tenant

Status: ❌ Não existe

Não foi encontrado modelo de tenant/organização, middleware de tenant, escopo obrigatório por tenant em queries, isolamento de arquivos por tenant ou testes de isolamento. Isso está de acordo com a decisão atual de não implementar multi-tenant nesta etapa.

Pontos de atenção:

- ❌ Não existe: isolamento de dados por cliente.
- ❌ Não existe: backups/exportações por tenant.
- ❌ Não existe: papéis por tenant.
- ❌ Não existe: testes garantindo que um tenant não acessa dados de outro.
- ➕ Recomendado para depois: desenhar o modelo multi-tenant antes de adicionar assinaturas, trial, APIs públicas ou automações.

## Resumo geral

O projeto já tem uma base de segurança melhor que o mínimo para uma aplicação Django autenticada: proteção de secrets por ambiente, cookies seguros em produção, CSRF/CORS controlados, autenticação com Argon2, rate limits em pontos importantes, `django-axes`, permissões internas, proteção de arquivos sensíveis no Git e backups restritos a superuser.

O principal risco para o SaaS não é uma falha isolada de configuração, mas a transição de um sistema de usuário único para múltiplos clientes. Backups, permissões e APIs ainda são globais. Isso é aceitável agora, desde que o sistema continue operando como projeto separado de uso controlado, mas não deve ser exposto como SaaS multi-cliente antes de uma camada de tenant bem definida.

## Riscos altos

- Backup atual é global e não deve ser liberado para administradores de cliente no SaaS.
- Não existe isolamento multi-tenant; não lançar múltiplos clientes no mesmo banco sem redesenho e testes.
- Configuração real de produção não foi confirmada nesta auditoria local.

## Riscos médios

- Downloads e algumas views Django não-DRF precisam de rate limit específico.
- Rate limits dependem de cache compartilhado; Redis deve ser obrigatório em produção.
- Django Admin está ativo e deve ser tratado como área interna, não como painel de cliente.
- Uso de `AllowAny` com checagem manual em APIs exige disciplina e testes para evitar regressões.
- Documentação/deploy herdados ainda podem conter referências operacionais antigas.

## Riscos baixos

- Título OpenAPI foi renomeado para `RH SaaS API`; revisar docs antigas se esse nome reaparecer.
- Existem documentos históricos com exemplos e nomes antigos que não parecem sensíveis, mas podem confundir manutenção.
- Observabilidade e audit log ainda são básicos.
- Há arquivo local não versionado de roadmap que deve ser tratado conscientemente no próximo commit.

## O que corrigir primeiro

1. Confirmar ambiente real de produção: `DEBUG=False`, `SECRET_KEY` única, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, cookies seguros e Redis.
2. Definir política de backup SaaS: backup global só para operador da plataforma; cliente deve ter exportação tenant-scoped.
3. Adicionar rate limits para downloads, exportações e backups, preferencialmente também no proxy reverso.
4. Formalizar que Django Admin é interno e que administradores de cliente usarão telas da aplicação.
5. Criar desenho técnico do multi-tenant antes de trial, cobrança, APIs públicas ou automações.

## O que não vale a pena fazer agora por ainda ser um único usuário

- Implementar multi-tenant imediatamente.
- Criar billing, planos, trial e cobrança antes do isolamento de dados.
- Construir API pública com tokens e escopos antes de definir tenants.
- Liberar backup global para administradores de cliente.
- Implementar exportações por tenant antes de existir o modelo de tenant.
- Adicionar WebSocket/notificações antes de fechar segurança, permissões e auditoria básica.
- Montar observabilidade complexa antes de validar deploy, logs essenciais e alertas mínimos.

## Próxima auditoria recomendada

Rodar uma etapa de verificação controlada com:

- `python manage.py check --deploy` usando variáveis de produção seguras em ambiente local/staging.
- testes focados de autenticação, permissões, backups e APIs.
- secret scanning no repositório e, se necessário, no histórico.
- validação do servidor real: DNS, TLS, proxy, headers, logs, Redis, banco e backups.
