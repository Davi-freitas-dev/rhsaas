# Soft Delete e Retencao

Este capitulo define a estrategia de exclusao logica e fisica.

## Principio

Dados com impacto financeiro, fiscal, juridico, auditoria ou historico de cliente nao devem ser apagados fisicamente por padrao.

## Exclusao Logica Recomendada

Entidades que devem usar exclusao logica ou arquivamento:

- Customer;
- CustomerAddress;
- Product;
- Category;
- Coupon;
- Cart, quando associado a pedido;
- Order;
- OrderItem;
- Payment;
- PaymentAttempt;
- PaymentWebhookEvent;
- Refund;
- Chargeback;
- AuditLog;
- FiscalDocument futuro;
- anexos sensiveis ligados a pedido/pagamento.

Justificativa:

- auditoria;
- suporte;
- conciliacao;
- obrigacoes legais;
- historico de pedidos;
- LGPD com retencao controlada.

## Exclusao Fisica Possivel

Pode ser fisica quando nao houver obrigacao de retencao:

- carrinho anonimo expirado sem pedido;
- arquivo temporario;
- upload rejeitado;
- cache;
- token expirado;
- sessao expirada;
- artefato de job temporario;
- imagem de produto nao vinculada e dentro da janela segura.

## LGPD

Soft delete nao substitui privacidade.

Para dados pessoais:

- definir retencao;
- anonimizar quando aplicavel;
- bloquear reidentificacao desnecessaria;
- preservar dados obrigatorios por lei;
- registrar solicitacoes de exclusao/anonimizacao.

## Campos Comuns

Campos possiveis:

```text
deleted_at
deleted_by
delete_reason
archived_at
anonymized_at
```

## Regras

- querysets publicos nao retornam deletados por padrao;
- relatorios financeiros podem incluir arquivados quando necessario;
- auditoria nao deve ser apagada sem politica formal;
- exclusao fisica em massa exige command protegido;
- tenant A nunca apaga dados do tenant B.

## O Que Nao Fazer

- Nao apagar pedido pago fisicamente.
- Nao apagar pagamento/webhook usado em conciliacao.
- Nao apagar AuditLog por conveniencia.
- Nao confundir anonimizar com deletar.
