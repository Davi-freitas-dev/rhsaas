# ADR 0003 - PostgreSQL

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS usara schemas por tenant e dados transacionais.

## Problema

Escolher banco com suporte robusto a schemas, transacoes, indices e integridade.

## Alternativas Consideradas

- PostgreSQL.
- MySQL.
- SQLite.

## Decisao

Usar PostgreSQL.

## Consequencias

- Suporte nativo a schemas.
- Transacoes fortes.
- Indices e constraints robustos.
- Compatibilidade com `django-tenants`.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Operacao de muitos schemas exige disciplina.
- Backups/restores por tenant precisam ser desenhados.

## Criterios de Revisao Futura

- Escala extrema exigir particionamento, replicas ou estrategia dedicada.

