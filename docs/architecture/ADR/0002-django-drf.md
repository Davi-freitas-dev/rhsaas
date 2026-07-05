# ADR 0002 - Django + Django REST Framework

## Status

Aceito.

## Data

2026-07-05

## Contexto

O produto precisa de backend seguro, admin/plataforma, ORM, autenticacao, permissoes e APIs.

## Problema

Escolher framework que permita velocidade sem sacrificar seguranca.

## Alternativas Consideradas

- Django + DRF.
- FastAPI.
- Node.js/NestJS.

## Decisao

Usar Django + DRF.

## Consequencias

- ORM maduro.
- Ecossistema forte.
- Suporte a CSRF, sessoes e permissoes.
- DRF para APIs.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Views podem crescer sem padrao de services/selectors.
- Performance exige cuidado com querysets.

## Criterios de Revisao Futura

- Necessidade real de servicos separados.
- Gargalos que nao sejam resolvidos com otimizacao e workers.

