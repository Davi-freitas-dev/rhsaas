# Seguranca

Seguranca deve ser padrao inicial do projeto, nao etapa posterior.

## Autenticacao

- Login por tenant.
- Sessao host-only.
- Reset de senha tenant-aware.
- Argon2 como hasher preferencial.
- Protecao contra brute force.
- MFA para operadores da plataforma quando possivel.

Cliente final/comprador autentica dentro da loja atual. Login em `loja-a.meusaas.com` nao autentica automaticamente em `loja-b.meusaas.com`.

Mesmo e-mail em duas lojas nao significa mesma conta tecnica.

## Autorizacao

Hierarquia:

```text
PlatformOperator
  -> Tenant
      -> Roles
          -> Permissions
              -> Users / Customers
```

Roles sugeridas:

- PlatformOperator.
- TenantAdmin.
- Manager.
- StockManager.
- FinancialManager.
- OrderManager.
- Support.
- Customer.

`is_superuser` de tenant nao e operador global.

Customer final nao e operador da plataforma, nao e usuario interno da loja e nao deve receber permissao administrativa.

Operador da plataforma so deve acessar dados pessoais de compradores por fluxo explicito, menor privilegio e auditoria.

## OWASP e Riscos

### IDOR

Mitigacao:

- tenant por Host;
- querysets no schema ativo;
- 404 seguro;
- testes com IDs iguais em tenants diferentes.

### Privacidade do Comprador

Mitigacao:

- Customer no schema do tenant;
- sem perfil global de comprador por padrao;
- reset de senha tenant-aware;
- suporte auditado;
- logs sem dados pessoais desnecessarios;
- uma loja nao infere compras ou cadastro do comprador em outra loja.

### Mass Assignment

Mitigacao:

- serializers de input dedicados;
- campos readonly;
- whitelist de campos mutaveis.

### SQL Injection

Mitigacao:

- ORM;
- queries parametrizadas;
- raw SQL com revisao e teste.

### XSS

Mitigacao:

- escapar output;
- CSP;
- sanitizacao de HTML, se existir conteudo rico;
- nao renderizar payload externo sem tratamento.

### SSRF

Mitigacao:

- nao buscar URLs arbitrarias enviadas pelo usuario;
- allowlist de hosts para integracoes;
- timeouts;
- bloqueio de IPs privados quando aplicavel.

### Clickjacking

Mitigacao:

- `X-Frame-Options: DENY`;
- `frame-ancestors 'none'`.

## CSRF, CORS e Cookies

- Cookies `Secure` em producao.
- Cookies `HttpOnly` para sessao.
- `SameSite` explicito.
- Cookies de sessao e CSRF devem ser host-only.
- Nao configurar `Domain=.meusaas.com` para cookies de sessao ou CSRF.
- CORS sem wildcard com credenciais.
- CSRF trusted origins controlados.
- CSRF e sessao de um subdominio nao devem autenticar nem autorizar outro subdominio.

Cada subdominio deve ter autenticacao, sessao, CSRF, cache, carrinho, pedidos e pagamentos independentes.

Tenant deve ser resolvido exclusivamente pelo `Host`; nunca por query string, header customizado ou payload.

Ver a decisao completa em [17 - Isolamento por Host e Autenticacao](17-ISOLAMENTO_HOST_AUTH.md).

## Webhooks

Requisitos:

- assinatura;
- timestamp;
- idempotencia;
- validacao de valor/moeda;
- tenant e referencia confiaveis;
- transacao;
- auditoria;
- rate limit;
- alerta em conflito.

Quando houver provedores configuraveis por loja, o webhook tambem deve validar `PaymentProviderConfig` do tenant, provider, external_reference, valor, moeda e idempotencia no schema correto.

Segredos de gateways pertencem ao tenant e nunca devem aparecer em frontend, API responses ou logs.

Fluxos manuais de pagamento exigem permissao especifica e AuditLog. Ver [18 - Checkout e Pagamentos por Tenant](18-CHECKOUT_PAGAMENTOS_POR_TENANT.md).

## Upload Seguro

- tamanho maximo;
- tipo permitido;
- moderacao quando necessario;
- assinatura curta;
- folder definido pelo backend;
- public_id validado;
- antivirus/moderacao se o produto exigir.

## Dependencias

Dependencias uteis:

- Django;
- DRF;
- `django-tenants`;
- `argon2-cffi`;
- `django-axes`;
- `django-environ`;
- `django-redis`;
- `django-simple-history`;
- `drf-spectacular`;
- `psycopg`;
- `requests` com timeout.

Ferramentas recomendadas:

- `pip-audit`;
- `bandit`;
- `pytest-django`;
- `coverage`;
- `sentry-sdk` ou equivalente;
- `django-csp` ou CSP equivalente.

## Headers

- HSTS.
- CSP.
- X-Frame-Options.
- X-Content-Type-Options.
- Referrer-Policy.
- Permissions-Policy.

## LGPD

- minimizacao de dados;
- retencao definida;
- export seguro;
- anonimizar quando aplicavel;
- trilha de auditoria para dados pessoais;
- nao logar dados sensiveis.

## Anti-Padroes

- webhook sem assinatura;
- upload livre;
- CORS wildcard com credenciais;
- cookie compartilhado entre tenants;
- `Domain=.meusaas.com` em cookie de sessao ou CSRF;
- tenant selecionado por query string, header customizado ou payload;
- secrets no Git;
- logs com token/senha/cartao;
- OpenAPI interativa publica sem protecao;
- dependencia vulneravel sem plano.
- Customer final no `public` sem decisao explicita;
- login global de comprador por padrao;
- reset de senha global para conta tenant-scoped;
- historico de compras cruzado entre lojas.
- credencial de gateway compartilhada entre tenants;
- segredo de pagamento em texto puro;
- pagamento manual sem permissao e auditoria;
- metodo de pagamento aceito apenas porque veio do frontend.
