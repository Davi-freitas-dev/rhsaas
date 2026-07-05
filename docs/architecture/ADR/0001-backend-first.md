# ADR 0001 - Backend-first

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS tera pagamentos, webhooks, permissao, multi-tenancy, estoque e dados pessoais.

## Problema

Regras sensiveis no frontend geram risco de fraude, inconsistencias e bypass.

## Alternativas Consideradas

- Frontend-driven com regras no cliente.
- Backend-first com frontend como consumidor de API.

## Decisao

Adotar backend-first.

## Consequencias

- Backend e fonte da verdade.
- Frontend apenas inicia fluxos e exibe estado.
- Testes de regra ficam majoritariamente no backend.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Backend pode crescer demais se nao houver camadas.
- Frontend depende de APIs bem desenhadas.

## Criterios de Revisao Futura

- API publica exigir BFF separado.
- Mobile app exigir adaptacoes de contrato.

