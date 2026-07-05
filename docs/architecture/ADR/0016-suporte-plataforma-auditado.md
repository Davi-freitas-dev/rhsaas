# ADR 0016 - Suporte da plataforma com menor privilegio

## Status

Aceito.

## Data

2026-07-05

## Contexto

Operadores da plataforma podem precisar ajudar tenants em problemas operacionais.

## Problema

Acesso irrestrito aos dados dos tenants cria risco de privacidade, abuso interno e vazamento.

## Alternativas Consideradas

- Operador com acesso total a todos os tenants.
- Impersonation livre.
- Acesso temporario, justificado e auditado.

## Decisao

Suporte da plataforma deve usar menor privilegio, motivo obrigatorio, acesso temporario, escopo claro e auditoria completa.

Operador da plataforma nao vira administrador automatico dos tenants.

## Consequencias

- Fluxos de suporte ficam mais seguros.
- Implementacao exige ferramentas proprias.
- Toda acao sensivel precisa trilha.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Mais friccao para suporte.
- Emergencias precisam procedimento claro.
- Auditoria deve ser protegida contra alteracao.

## Criterios de Revisao Futura

- Suporte 24/7.
- Planos enterprise.
- Impersonation controlado.
- Requisitos legais adicionais.
