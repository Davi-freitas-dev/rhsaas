# ADR 0023 - Tenant lifecycle

## Status

Aceito.

## Data

2026-07-05

## Contexto

Tenant passa por criacao, ativacao, suspensao, inadimplencia, reativacao, encerramento e delecao.

## Problema

Sem lifecycle explicito, tenants podem continuar vendendo quando bloqueados ou ter dados apagados incorretamente.

## Alternativas

- Usar apenas booleano `is_active`.
- Controlar estados apenas no billing.
- Criar lifecycle canonico do tenant.

## Decisao

Criar lifecycle canonico para tenants, com estados e regras operacionais.

Checkout, dominios, exports, suporte, webhooks e delecao devem respeitar esse estado.

## Consequencias

- Mais clareza operacional.
- Melhor seguranca para suspensao/bloqueio.
- Billing futuro fica mais facil.

## Trade-offs

- Mais estados para gerenciar.
- Exige cuidado para nao bloquear exports obrigatorios.

## Riscos

- Estado incorreto pode bloquear loja indevidamente.
- Delecao sem retencao pode violar contrato/LGPD.

## Criterios para revisao futura

- Billing automatizado.
- Trial publico.
- Planos enterprise.
- Politica juridica de retencao.
