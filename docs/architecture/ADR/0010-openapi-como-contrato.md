# ADR 0010 - OpenAPI como Contrato

## Status

Aceito.

## Data

2026-07-05

## Contexto

Backend Django/DRF e frontend Next.js precisam evoluir juntos.

## Problema

Evitar divergencia entre APIs e services/types do frontend.

## Alternativas Consideradas

- Documentacao manual apenas.
- OpenAPI gerada e revisada.
- Contrato informal.

## Decisao

Usar OpenAPI como contrato de API.

## Consequencias

- Tipos TypeScript podem ser gerados no futuro.
- Mudancas breaking ficam visiveis.
- Documentacao interativa pode ser protegida.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Schema incorreto se serializers/views forem mal anotados.
- Expor endpoint interno na documentacao publica.

## Criterios de Revisao Futura

- API publica exigir portal/documentacao separado.

