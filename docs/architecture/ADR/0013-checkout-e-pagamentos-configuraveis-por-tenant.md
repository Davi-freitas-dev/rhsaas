# ADR 0013 - Checkout e pagamentos configuraveis por tenant

## Status

Aceito.

## Data

2026-07-05

## Contexto

Cada loja pode operar com necessidades diferentes de checkout e pagamento.

Algumas lojas exigem login. Outras permitem compra como convidado. Algumas usam gateway online. Outras operam com Pix manual, maquininha fisica ou pagamento na entrega.

## Problema

Uma arquitetura rigida demais limita o produto. Uma arquitetura flexivel sem isolamento pode misturar credenciais, pedidos, webhooks e pagamentos entre tenants.

## Alternativas Consideradas

- Exigir login obrigatorio para todos os compradores.
- Permitir somente compra como convidado.
- Usar um unico gateway global para todas as lojas.
- Permitir configuracao de checkout e pagamento por tenant.

## Decisao

Permitir checkout e pagamento configuraveis por tenant.

O cliente final continua tenant-scoped. Login, sessao, carrinho, pedidos, enderecos e pagamentos pertencem ao Host/schema atual.

Cada tenant podera habilitar modos como login obrigatorio, convidado, cadastro no checkout, pedido manual, Pix manual, pagamento na entrega ou gateway online.

Configuracoes de pagamento serao tenant-scoped por `PaymentProviderConfig` ou armazenamento seguro fortemente vinculado ao tenant.

## Consequencias

- Mais flexibilidade comercial por loja.
- Mais validacoes no backend.
- Testes precisam cobrir provedores diferentes em tenants diferentes.
- Webhooks precisam validar provider, tenant, assinatura, valor, moeda e referencia externa.
- Fluxos manuais exigem permissao e auditoria.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Configuracao incorreta de provider pode bloquear checkout.
- Credenciais precisam protecao forte.
- Compra como convidado exige cuidado com LGPD e tokens de acompanhamento.
- Pagamento manual pode ser abusado sem permissao e AuditLog.

## Criterios de Revisao Futura

- Entrada de novo gateway.
- Necessidade de marketplace.
- Necessidade de split de pagamento.
- Necessidade de conta global de comprador.
- Regras reguladoras sobre armazenamento de credenciais e dados financeiros.
