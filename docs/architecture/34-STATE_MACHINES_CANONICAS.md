# State Machines Canonicas

Este documento e a fonte canonica para estados de `Order`, `Payment`, `Refund`, `Chargeback` e estoque.

Outros documentos podem mostrar fluxos simplificados, mas em caso de divergencia este documento prevalece.

## Principios

- Estados mudam apenas por services backend.
- Transicoes sensiveis geram AuditLog.
- Webhooks e jobs devem ser idempotentes.
- Transicoes conflitantes geram revisao.
- Status externo de gateway nao substitui status interno.
- Estados vivem no schema do tenant.

## Order

Estados canonicos:

```text
draft
pending
awaiting_payment
awaiting_manual_payment
paid
preparing
ready_for_pickup
out_for_delivery
delivered
cancellation_requested
canceled
refund_requested
partially_refunded
refunded
chargeback_under_review
expired
failed
```

Transicoes principais:

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> awaiting_payment
    pending --> awaiting_manual_payment
    awaiting_payment --> paid
    awaiting_manual_payment --> paid
    awaiting_payment --> expired
    awaiting_manual_payment --> expired
    paid --> preparing
    preparing --> ready_for_pickup
    preparing --> out_for_delivery
    ready_for_pickup --> delivered
    out_for_delivery --> delivered
    paid --> cancellation_requested
    cancellation_requested --> canceled
    paid --> refund_requested
    refund_requested --> partially_refunded
    refund_requested --> refunded
    paid --> chargeback_under_review
```

Regras:

- `paid` so acontece por webhook valido, conciliacao confiavel ou confirmacao manual auditada.
- `delivered` nao volta para `pending`.
- `canceled` nao volta para `paid` sem reabertura auditada.
- cancelamento apos pagamento passa por reembolso ou decisao auditada.

## Payment

Estados canonicos:

```text
awaiting_payment
processing
paid
failed
canceled
expired
awaiting_manual_confirmation
manually_confirmed
refund_pending
partially_refunded
refunded
chargeback
chargeback_under_review
chargeback_lost
chargeback_won
requires_review
```

Transicoes principais:

```mermaid
stateDiagram-v2
    [*] --> awaiting_payment
    awaiting_payment --> processing
    processing --> paid
    awaiting_payment --> failed
    processing --> failed
    awaiting_payment --> expired
    awaiting_payment --> canceled
    awaiting_payment --> awaiting_manual_confirmation
    awaiting_manual_confirmation --> manually_confirmed
    manually_confirmed --> paid
    paid --> refund_pending
    refund_pending --> partially_refunded
    refund_pending --> refunded
    paid --> chargeback_under_review
    chargeback_under_review --> chargeback_lost
    chargeback_under_review --> chargeback_won
    paid --> requires_review
    processing --> requires_review
```

Regras:

- `manually_confirmed` e evidencia operacional; `paid` e estado financeiro final interno.
- `failed -> paid` exige nova tentativa ou evento confiavel auditado.
- `paid -> failed` nao ocorre por evento tardio; deve gerar `requires_review`.
- reembolso nao remove pagamento original.

## Refund

Estados canonicos:

```text
requested
approved
processing
succeeded
failed
canceled
requires_review
```

Regras:

- soma de refunds bem-sucedidos nao pode exceder valor pago.
- refund parcial deve indicar item/valor/motivo quando aplicavel.
- refund automatico e manual compartilham a mesma trilha de auditoria.

## Chargeback

Estados canonicos:

```text
received
under_review
evidence_required
evidence_submitted
won
lost
accepted
reversed
closed
```

Regras:

- chargeback nao e cancelamento simples.
- chargeback pode bloquear reembolso duplicado.
- evidencias/anexos sao tenant-scoped e privados.
- resultado final impacta relatorios financeiros.

## Estoque

Estados canonicos de reserva:

```text
available
reserved
confirmed
released
expired
adjusted
```

Transicoes:

```mermaid
stateDiagram-v2
    [*] --> available
    available --> reserved
    reserved --> confirmed
    reserved --> released
    reserved --> expired
    confirmed --> adjusted
```

Regras:

- reserva deve ter expiracao.
- confirmacao e idempotente.
- webhook duplicado nao confirma duas vezes.
- cancelamento antes do pagamento libera reserva.
- ajuste manual exige motivo e AuditLog.

## Transicoes Proibidas

- pedido cancelado virar pago sem service de reabertura auditada.
- pagamento pago virar falho por evento tardio.
- refund exceder saldo pago.
- chargeback encerrado ser alterado sem nova evidencia/evento.
- reserva expirada ser confirmada sem revisao.

## Responsabilidade

Cada dominio pode ter services especificos, mas a validacao de transicao deve ser centralizada ou reutilizavel.

O frontend nunca decide estado financeiro ou operacional final.
