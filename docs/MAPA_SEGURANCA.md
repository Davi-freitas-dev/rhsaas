# Mapa de seguranca

## Superficies

- Autenticacao web: `caixa.views_auth.LoginSeguroView`, `LogoutSeguroView` e fluxo de reset de senha.
- Autenticacao API: `caixa.views_api_auth` com sessao Django, CSRF explicito e respostas JSON para o frontend.
- APIs operacionais: rotas `/api/...` em `caixa.urls`, com `SessionAuthentication`, permissoes por dominio e respostas 401/403 padronizadas.
- Backups: tela e APIs restritas a superusuario.
- Admin Django: mantido fora do CSP customizado para preservar scripts internos do admin.

## Controles ativos

- Cookies de sessao e CSRF `HttpOnly`, `SameSite` e `Secure` em producao.
- `django-axes` para bloqueio por falhas de login.
- Limite de reset de senha por IP/e-mail em `caixa.services_auth`.
- CSRF real preservado em escritas DRF sensiveis.
- CORS por allowlist em `caixa.middleware.ConfiguredCorsMiddleware`.
- Headers de seguranca em `caixa.middleware.SecurityHeadersMiddleware`: CSP, Permissions-Policy, COOP, CORP e X-Permitted-Cross-Domain-Policies.
- DRF throttling global para usuarios anonimos/autenticados e throttle especifico para `/api/auth/login/`.

## Limites de requisicao

Configuracao via `.env`:

- `DRF_THROTTLE_ANON_RATE`: limite global para requisicoes anonimas. Padrao de producao: `120/minute`.
- `DRF_THROTTLE_USER_RATE`: limite global para usuarios autenticados. Padrao de producao: `1200/minute`.
- `DRF_THROTTLE_AUTH_LOGIN_RATE`: limite especifico do login JSON. Padrao de producao: `20/minute`.

Em producao com mais de um worker/processo, use Redis em `CACHE_BACKEND`/`CACHE_LOCATION`, senao cada processo tera contadores locais de throttle.

## Politica de backup no SaaS

- Backup global do banco e artefatos operacionais e exclusivo do operador da
  plataforma.
- Administrador de cliente nao pode baixar backup global, mesmo quando tiver
  permissoes administrativas dentro da aplicacao.
- Backup/exportacao por tenant fica para a fase multi-tenant, depois de existir
  isolamento formal de organizacao, permissoes por tenant e testes de acesso
  cruzado.

## Comandos uteis

- `python manage.py check`
- `python manage.py check --deploy`
- `python manage.py gerar_snapshot_baseline_financeira --json`
- `python manage.py validar_preflight_deploy_financeiro --validar-deploy-django --falhar --json`
- `python -m pip check`
- `python -m pip_audit -r requirements.txt` quando `pip-audit` estiver instalado.

## Proximos endurecimentos recomendados

- Adicionar rate limit no proxy reverso para `/api/auth/login/`, `/password-reset/` e `/api/`.
- Rodar auditoria de dependencias no CI antes de publicar.
- Registrar alertas de 401/403/429 em logs ou observabilidade.
- Revisar periodicamente `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` e `ALLOWED_HOSTS`.
