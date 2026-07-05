# ADR 0018 - Dominios customizados e HTTPS por tenant

## Status

Aceito.

## Data

2026-07-05

## Contexto

Tenants podem usar subdominios da plataforma ou dominios proprios.

## Problema

Dominios mal verificados podem apontar para tenant errado, expor cookies ou quebrar SEO/HTTPS.

## Alternativas Consideradas

- Apenas subdominios da plataforma.
- Dominios customizados sem verificacao forte.
- Dominios customizados com verificacao, canonico e certificado.

## Decisao

Suportar dominios customizados futuramente com verificacao de propriedade, dominio canonico por tenant e HTTPS obrigatorio.

Cada dominio deve resolver para exatamente um tenant.

## Consequencias

- Melhor SEO e branding.
- Mais complexidade operacional.
- Exige automacao de certificados e alertas.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Certificado expirado.
- Subdomain/domain takeover.
- Aliases duplicados.
- Configuracao incorreta de cookies.

## Criterios de Revisao Futura

- Volume de dominios customizados.
- Provedor de DNS/certificados.
- Necessidade de wildcard.
- Planos enterprise.
