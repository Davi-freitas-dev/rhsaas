# Cancelamentos, Reembolsos e Chargeback

Este capitulo define os fluxos financeiros e operacionais posteriores a criacao do pedido.

Estados canonicos ficam em [34 - State Machines Canonicas](34-STATE_MACHINES_CANONICAS.md). Os fluxos abaixo explicam comportamento esperado, mas a fonte final para nomes e transicoes de estados e o documento canonico.

## Principios

- Toda alteracao de status deve passar por service backend.
- Toda alteracao sensivel deve gerar auditoria.
- Pedido, pagamento, estoque e entrega devem ser atualizados de forma consistente.
- Fluxos automaticos e manuais devem ser separados.
- Eventos conflitantes devem gerar revisao, nao correcao silenciosa.

## Cancelamentos

### Antes do Pagamento

Fluxo:

- pedido esta `pending`, `awaiting_payment` ou `awaiting_manual_payment`;
- pagamento ainda nao foi confirmado;
- cancelar pedido;
- cancelar ou expirar tentativa de pagamento quando aplicavel;
- liberar reserva de estoque;
- registrar auditoria.

Impacto:

- Order: `canceled`;
- Payment: `canceled` ou `expired`;
- StockReservation: liberada;
- AuditLog: usuario/sistema, motivo, origem e data.

### Apos Pagamento

Fluxo:

- pedido esta `paid`;
- gateway ou fluxo manual ja confirmou pagamento;
- cancelamento passa a exigir reembolso total ou parcial;
- estoque pode ou nao retornar, conforme regra operacional;
- registrar auditoria e conciliacao.

Impacto:

- Order: pode ir para `canceled` ou `refund_requested`;
- Payment: `refund_pending`, `refunded` ou `partially_refunded`;
- estoque: retorno manual ou automatico conforme regra;
- AuditLog obrigatorio.

### Antes da Expedicao

Pedido pago, mas ainda nao enviado.

Recomendacao:

- permitir cancelamento com reembolso seguindo regras da loja;
- travar separacao/expedicao;
- registrar motivo;
- reavaliar estoque.

### Apos Envio

Pedido ja enviado.

Recomendacao:

- cancelamento vira fluxo de devolucao/reembolso;
- nao simplesmente cancelar como se nada tivesse sido enviado;
- registrar tracking, status logistico e motivo;
- exigir revisao quando necessario.

### Cancelamento Manual

Usado por operador da loja com permissao especifica.

Exige:

- permissao;
- motivo obrigatorio;
- AuditLog;
- registro de usuario, IP e data;
- validacao do estado atual;
- quando houver pagamento, decisao explicita sobre reembolso.

### Cancelamento Automatico

Usado por jobs ou eventos externos.

Exemplos:

- pagamento expirado;
- reserva expirada;
- pedido sem pagamento apos prazo;
- gateway confirma cancelamento.

Exige:

- idempotencia;
- schema_name explicito;
- auditoria tecnica;
- alerta em falha.

## Reembolsos

### Total

Devolve o valor integral pago.

Regras:

- validar pedido e pagamento;
- validar permissao ou evento confiavel;
- chamar gateway quando aplicavel;
- registrar `Refund`;
- atualizar `Payment`;
- registrar auditoria.

### Parcial

Devolve parte do valor.

Casos:

- item indisponivel;
- desconto posterior;
- devolucao parcial;
- acordo de suporte.

Regras:

- valor parcial nunca pode exceder saldo reembolsavel;
- motivo obrigatorio;
- item/quantidade devem ser rastreaveis quando aplicavel;
- auditoria obrigatoria.

### Automatico

Executado por service ou gateway.

Exige:

- evento assinado ou job tenant-aware;
- idempotencia;
- validacao de valor/moeda;
- transacao;
- reconciliacao posterior.

### Manual

Executado por operador autorizado.

Exige:

- permissao especifica;
- motivo;
- evidencia quando aplicavel;
- AuditLog;
- revisao para valores altos.

## Chargeback

Chargeback e contestacao iniciada pelo cliente final ou emissor/cartao.

## Recebimento

O sistema pode receber chargeback por webhook ou conciliacao.

Requisitos:

- validar assinatura do provider;
- identificar tenant/provider/pagamento;
- validar valor, moeda e referencia;
- registrar evento bruto sanitizado;
- criar ou atualizar registro de chargeback.

## Processamento

Estados conceituais:

```text
received
under_review
won
lost
accepted
reversed
```

Regras:

- nao alterar pedido silenciosamente sem registrar impacto financeiro;
- bloquear reembolso duplicado quando chargeback esta em andamento;
- alertar equipe da loja/plataforma quando aplicavel;
- anexos/evidencias devem ser tenant-scoped.

## Auditoria e Revisao

Registrar:

- provider;
- payment;
- order;
- valor;
- moeda;
- status;
- prazos;
- usuario/operador quando houver acao manual;
- evidencias enviadas;
- resultado final.

## Impacto Financeiro

Um chargeback pode:

- reduzir receita liquida;
- gerar taxa;
- reabrir conciliacao;
- afetar relatorios financeiros;
- bloquear captura/reembolso;
- exigir revisao de risco.

## Estados

Usar a fonte canonica em [34 - State Machines Canonicas](34-STATE_MACHINES_CANONICAS.md).

## Testes Obrigatorios

- cancelamento antes de pagamento libera reserva.
- cancelamento apos pagamento exige fluxo de reembolso.
- reembolso parcial nao excede valor pago.
- webhook duplicado de reembolso e idempotente.
- chargeback de tenant A nao altera pagamento de tenant B.
- cancelamento manual exige permissao e motivo.
- eventos conflitantes geram revisao.

## O Que Nao Fazer

- Nao apagar pedido cancelado.
- Nao reembolsar sem registrar motivo e auditoria.
- Nao tratar chargeback como cancelamento simples.
- Nao repor estoque automaticamente sem regra clara.
- Nao permitir que frontend altere status financeiro.
