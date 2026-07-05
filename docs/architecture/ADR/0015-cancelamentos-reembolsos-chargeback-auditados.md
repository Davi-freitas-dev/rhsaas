# ADR 0015 - Cancelamentos, reembolsos e chargeback auditados

## Status

Aceito.

## Data

2026-07-05

## Contexto

Pedidos podem ser cancelados, reembolsados ou contestados depois de criados.

## Problema

Alteracoes financeiras sem fluxo claro podem causar fraude, divergencia de estoque e conciliacao incorreta.

## Alternativas Consideradas

- Permitir alteracao direta de status.
- Tratar tudo como cancelamento simples.
- Criar fluxos separados para cancelamento, reembolso e chargeback.

## Decisao

Criar fluxos separados, validados por service backend, com permissoes, transacoes, idempotencia e auditoria.

Chargeback nao e cancelamento simples. Reembolso nao e apenas alteracao de pedido.

## Consequencias

- Mais estados internos.
- Mais testes.
- Melhor rastreabilidade financeira.
- Menor risco de alteracao indevida.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Maquina de estados pode ficar complexa.
- Integracao com gateway exige conciliacao.
- Regras de estoque precisam ser explicitas.

## Criterios de Revisao Futura

- Novo gateway.
- Regras de devolucao mais complexas.
- Fiscal integrado.
- Marketplace/split de pagamento.
