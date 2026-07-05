# ADR 0009 - Backups Tenant-Scoped

## Status

Aceito.

## Data

2026-07-05

## Contexto

Cada loja tem dados isolados por schema.

## Problema

Permitir backup e restore sem vazar ou afetar outros tenants.

## Alternativas Consideradas

- Backup global unico.
- Backup por tenant.
- Backup por banco separado.

## Decisao

Usar backup tenant-scoped para dados operacionais e backup separado da plataforma.

## Consequencias

- Restore de tenant pode ser planejado isoladamente.
- Admin de tenant nao acessa backup global.
- Metadata deve registrar schema.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Usar backup de tenant errado.
- Restore sem teste.

## Criterios de Revisao Futura

- Escala exigir estrategia incremental ou storage dedicado.

