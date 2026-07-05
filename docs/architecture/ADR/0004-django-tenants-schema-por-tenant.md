# ADR 0004 - django-tenants com Schema por Tenant

## Status

Aceito.

## Data

2026-07-05

## Contexto

Cada loja precisa de isolamento forte.

## Problema

Evitar vazamento entre empresas e simplificar querysets operacionais.

## Alternativas Consideradas

- Tenant por coluna `tenant_id`.
- Tenant por banco separado.
- Tenant por schema PostgreSQL.

## Decisao

Usar `django-tenants` com um schema PostgreSQL por tenant.

## Consequencias

- Isolamento forte.
- IDs podem repetir entre tenants.
- Querysets operam no schema ativo.
- Migrations precisam usar fluxo de schemas.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Commands e jobs sem schema podem operar errado.
- Muitos schemas exigem monitoramento.

## Criterios de Revisao Futura

- Numero de tenants ou tamanho de dados justificar bancos separados por grupo.

