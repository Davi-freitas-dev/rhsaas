# ADR 0014 - Estoque com reserva transacional

## Status

Aceito.

## Data

2026-07-05

## Contexto

Varios compradores podem disputar o ultimo item ao mesmo tempo.

## Problema

Sem controle de concorrencia, o sistema pode vender estoque inexistente ou confirmar dois pedidos para o mesmo item.

## Alternativas Consideradas

- Baixar estoque apenas apos pagamento.
- Reservar estoque temporariamente.
- Usar fila/eventual consistency para todo checkout.
- Usar reserva temporaria com transacao e lock.

## Decisao

Adotar reserva temporaria de estoque com transacao e lock nos itens afetados.

Reservas devem expirar, ser idempotentes e viver no schema do tenant.

## Consequencias

- Reduz overselling.
- Exige job de expiracao.
- Exige testes concorrentes.
- Mantem banco como fonte da verdade.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Locks longos podem gerar contencao.
- Reservas abandonadas precisam limpeza confiavel.
- Regras de reembolso/reposicao devem ser explicitas.

## Criterios de Revisao Futura

- Alto volume de checkout.
- Necessidade de fila distribuida.
- Produtos digitais/sem estoque.
- Modelo marketplace.
