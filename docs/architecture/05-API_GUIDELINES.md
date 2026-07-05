# API Guidelines

As APIs devem ser backend-first, versionadas, documentadas e seguras por padrao.

## Versionamento

Padrao recomendado:

```text
/api/v1/products/
/api/v1/orders/
/api/v1/payments/
```

Regras:

- Mudanca breaking exige nova versao.
- Campo novo opcional pode entrar na mesma versao.
- Campo removido exige deprecacao.
- Contratos publicados devem ter changelog.

## URLs

Usar substantivos no plural:

```text
GET /api/v1/products/
POST /api/v1/products/
GET /api/v1/products/{id}/
PATCH /api/v1/products/{id}/
POST /api/v1/orders/{id}/cancel/
```

Nao incluir tenant na URL. Tenant vem do Host.

Tambem nao aceitar tenant por header customizado, query string ou payload. O backend deve resolver tenant exclusivamente pelo `Host` validado.

## Paginacao

Padrao:

```json
{
  "count": 120,
  "next": "https://loja.meusaas.com/api/v1/products/?page=2",
  "previous": null,
  "results": []
}
```

Definir limite maximo por endpoint.

## Filtros, Ordenacao e Busca

Exemplos:

```text
GET /api/v1/products/?status=active&category=shirts
GET /api/v1/orders/?status=paid&created_after=2026-01-01
GET /api/v1/products/?ordering=-created_at
GET /api/v1/products/?search=camiseta
```

Filtros devem ser whitelistados. Nunca permitir campo arbitrario sem validacao.

## Responses

Padrao simples:

```json
{
  "data": {},
  "meta": {}
}
```

Ou padrao DRF para listas paginadas. O importante e manter consistencia por versao.

## Erros Padronizados

```json
{
  "code": "payment_signature_invalid",
  "message": "Nao foi possivel validar o evento de pagamento.",
  "field_errors": {},
  "meta": {
    "request_id": "req_..."
  }
}
```

Nao expor stack trace, secrets, SQL, payload bruto sensivel ou detalhes do gateway.

## Codigos HTTP

- 200: sucesso.
- 201: criado.
- 202: aceito para processamento.
- 204: sem conteudo.
- 400: payload invalido.
- 401: nao autenticado.
- 403: sem permissao.
- 404: nao encontrado ou nao pertence ao tenant.
- 409: conflito de estado.
- 422: regra de negocio invalida.
- 429: rate limit.
- 500: erro inesperado.

## DTOs e Serializers

- Separar input e output serializers quando necessario.
- Bloquear mass assignment.
- Expor apenas campos permitidos.
- Validar enums e transicoes.
- Normalizar datas e valores monetarios.

## Idempotencia

Obrigatoria para:

- criacao de pagamento;
- webhooks;
- checkout;
- criacao de pedido;
- reembolso;
- operacoes com risco de retry.

Usar:

- `Idempotency-Key` para requests de cliente quando fizer sentido;
- `event_id` do gateway para webhooks;
- unique constraints para reforcar.

## Autenticacao e CSRF

Se usar sessao/cookies:

- `credentials: include` no frontend;
- CSRF em metodos mutaveis;
- cookies Secure, HttpOnly e SameSite;
- host-only por padrao.

Webhooks nao usam CSRF, mas exigem assinatura, timestamp, idempotencia e allowlist quando possivel.

Webhook routing e tenant resolution nao devem depender de tenant enviado pelo frontend ou de payload nao autenticado. A decisao canonica esta em [33 - Webhook Routing e Secret Management](33-WEBHOOK_ROUTING_SECRET_MANAGEMENT.md).

## Cache HTTP

- Dados sensiveis: `Cache-Control: no-store`.
- Catalogo publico: cache controlado por tenant/host.
- Pagamentos, pedidos, sessao, carrinho e exports: sem cache compartilhado.

## Rate Limit

Rate limit por:

- tenant/schema_name;
- usuario;
- IP;
- endpoint.

As chaves de throttling devem incluir `schema_name` para evitar colisao ou bypass entre lojas.

Endpoints criticos:

- login;
- reset de senha;
- checkout;
- pagamento;
- webhook;
- upload;
- export;
- backup/download.

## OpenAPI

Regras:

- OpenAPI desde cedo.
- Documentacao interativa protegida em producao.
- Geracao futura de tipos TypeScript.
- Exemplos sem dados reais.
- Endpoints internos marcados ou omitidos.

## Compatibilidade

- Nao renomear campos sem deprecacao.
- Nao mudar semantica de status sem nova versao.
- Manter aliases apenas com prazo e dono.
- Testar frontend contra contrato.
