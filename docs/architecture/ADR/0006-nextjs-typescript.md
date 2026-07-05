# ADR 0006 - Next.js + TypeScript

## Status

Aceito.

## Data

2026-07-05

## Contexto

O produto precisa de storefront, painel tenant e experiencia moderna.

## Problema

Escolher frontend produtivo, tipado e adequado para consumo de API.

## Alternativas Consideradas

- Next.js + TypeScript.
- React SPA.
- Templates Django.

## Decisao

Usar Next.js + TypeScript.

## Consequencias

- App Router.
- Tipos compartilhaveis via OpenAPI.
- Melhor experiencia de UI.
- Backend segue como fonte da verdade.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Duplicar regra de negocio no frontend.
- Cache client-side sem tenant.

## Criterios de Revisao Futura

- Necessidade de mobile app nativo.
- Necessidade de BFF dedicado.

