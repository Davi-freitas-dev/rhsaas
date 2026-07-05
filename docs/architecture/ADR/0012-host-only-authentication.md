# ADR 0012 - Host-only authentication e contexto de seguranca por tenant

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS tera um dominio principal da plataforma e subdominios exclusivos por tenant.

Exemplos:

- `meusaas.com`;
- `loja-a.meusaas.com`;
- `loja-b.meusaas.com`.

O tenant sera identificado exclusivamente pelo `Host`.

## Problema

Autenticacao, sessao, cookies e CSRF compartilhados entre subdominios aumentam o risco de vazamento entre tenants, confusao de sessao e propagacao de impacto caso um subdominio seja comprometido.

Tambem seria perigoso permitir que o frontend escolha tenant por query string, header, payload ou token.

## Alternativas Consideradas

### Cookies Compartilhados

Usar `Domain=.meusaas.com` para cookies de sessao ou CSRF.

Rejeitado porque aumenta a superficie de ataque e permite que cookies circulem entre subdominios.

### Login Global

Uma autenticacao para todos os tenants.

Rejeitado inicialmente porque reduz isolamento, complica privacidade e pode misturar contexto de clientes finais entre lojas.

### Sessao Global

Uma sessao valida em qualquer subdominio.

Rejeitado porque cria risco de session confusion e acesso indevido entre tenants.

### Host-Only

Cada Host possui autenticacao, sessao, cookies, CSRF, cache e contexto de seguranca independentes.

Aprovado.

## Decisao

Adotar Host-only authentication e contexto de seguranca independente por tenant.

Regras:

- tenant resolvido exclusivamente pelo `Host`;
- sem tenant por query string, parametro de URL, body, header customizado ou token do frontend;
- cookies de sessao e CSRF host-only;
- nao usar `Domain=.meusaas.com` para cookies de sessao ou CSRF;
- sessao de um tenant nao autentica outro tenant;
- logout afeta apenas o Host atual;
- CSRF pertence ao Host;
- cache, throttling, logs, jobs e arquivos ligados a tenant incluem `schema_name`;
- cliente final e tenant-scoped.

## Consequencias

- Maior isolamento entre lojas.
- Menor superficie de ataque.
- Menor impacto em caso de subdominio comprometido.
- Testes de autenticacao e sessao precisam cobrir multiplos Hosts.
- Experiencia de login nao e automaticamente compartilhada entre lojas.

## Trade-offs

- Implementacao mais complexa.
- Mais casos de teste.
- Fluxos de suporte e plataforma precisam de desenho proprio.
- Futuro marketplace com conta global exigira nova decisao arquitetural.

## Beneficios de Seguranca

- Evita cookie confusion.
- Evita session confusion.
- Reduz risco de Cross-Tenant Request Forgery.
- Reduz chance de vazamento por cache.
- Evita tenant spoofing pelo frontend.
- Protege privacidade do cliente final entre lojas.

## Riscos Evitados

- Cookie compartilhado entre tenants.
- Login global acidental.
- Reset de senha afetando outro tenant.
- Carrinho/pedido/pagamento aparecendo em outra loja.
- Cache contaminado entre subdominios.
- Tenant escolhido por parametro manipulavel.

## Criterios de Revisao Futura

- Introducao de marketplace global.
- Necessidade real de conta global de comprador.
- Aplicativos mobile ou API publica com modelo de autenticacao proprio.
- Dominios customizados em larga escala.
- Mudanca regulatoria de privacidade/LGPD.
