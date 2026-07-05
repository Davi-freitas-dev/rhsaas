# ADR 0008 - Gateway Externo com Webhooks Idempotentes

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS precisa aceitar Pix e cartao.

## Problema

Confirmar pagamentos sem confiar no frontend.

## Alternativas Consideradas

- Confirmacao pelo frontend.
- Consulta manual periodica apenas.
- Webhook assinado e idempotente.

## Decisao

Usar gateway externo com webhook assinado, validado e idempotente.

## Consequencias

- Pedido so vira paid apos confirmacao confiavel.
- Eventos duplicados nao duplicam efeitos.
- Conciliacao periodica complementa seguranca.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Configuracao incorreta de secret.
- Evento conflitante exigir revisao.

## Criterios de Revisao Futura

- Troca de gateway.
- Suporte a multiplos gateways por tenant.

