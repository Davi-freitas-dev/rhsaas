# ADR 0022 - State machines canonicas

## Status

Aceito.

## Data

2026-07-05

## Contexto

Pedidos, pagamentos, reembolsos, chargebacks e estoque aparecem em varios fluxos.

## Problema

Estados duplicados ou contraditorios geram bugs financeiros e regras ambiguas.

## Alternativas

- Cada modulo definir seus proprios estados.
- Documentar estados apenas nos models futuros.
- Criar documento canonico de state machines.

## Decisao

Criar documento canonico para `Order`, `Payment`, `Refund`, `Chargeback` e estoque.

Outros documentos podem resumir fluxos, mas devem referenciar a fonte canonica.

## Consequencias

- Menos ambiguidade.
- Mais facil validar transicoes.
- Mais disciplina ao alterar estados.

## Trade-offs

- Exige manutencao central.
- Pode parecer burocratico no MVP.
- Reduz muito risco financeiro.

## Riscos

- Documento canonico ficar desatualizado.
- Implementacao ignorar state machine.

## Criterios para revisao futura

- Novo gateway.
- Novo fluxo logistico.
- Fiscal integrado.
- Marketplace ou split de pagamento.
