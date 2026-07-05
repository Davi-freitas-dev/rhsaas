# ADR 0020 - Webhook routing e tenant resolution

## Status

Aceito.

## Data

2026-07-05

## Contexto

Webhooks de pagamento chegam sem sessao de usuario e nem sempre chegam pelo Host do tenant.

## Problema

O sistema precisa validar assinatura e resolver tenant sem confiar em payload nao autenticado.

## Alternativas

- Resolver tenant pelo payload do webhook.
- Usar endpoint por tenant/provider.
- Usar metadata assinada enviada ao gateway.
- Usar `WebhookIngressRegistry` no `public`.

## Decisao

Usar `WebhookIngressRegistry` no schema `public` para rotear webhooks.

O registry contem provider, endpoint_key, tenant_schema, environment, status e referencia segura para segredo.

Depois da validacao inicial, o processamento operacional entra no schema do tenant.

## Consequencias

- Menor risco de tenant spoofing.
- Menor ambiguidade entre assinatura e tenant.
- Mais uma entidade de plataforma para administrar.
- Webhook fica independente do Host de loja.

## Trade-offs

- Aumenta complexidade inicial.
- Reduz risco critico em pagamentos.
- Facilita rotacao, desativacao e auditoria.

## Riscos

- Registry desatualizado pode bloquear webhook valido.
- Configuracao incorreta pode apontar evento para tenant errado.
- Precisa auditoria e validacao forte.

## Criterios para revisao futura

- Novo gateway com modelo de assinatura incompativel.
- Marketplace/split de pagamento.
- Alto volume de webhooks.
- Necessidade de endpoint por tenant para provider especifico.
