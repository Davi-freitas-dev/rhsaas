# Database Architecture

Banco recomendado: PostgreSQL.

Multi-tenancy recomendado: schema por tenant com `django-tenants`.

## Principios

- Dados operacionais ficam no schema do tenant.
- Dados da plataforma ficam no `public`.
- Constraints e indices devem proteger invariantes.
- Transacoes devem envolver fluxos criticos.
- Migrations devem ser planejadas para `public` e tenants.

## Modelagem Inicial

### Public

- `Tenant`
- `Domain`
- `PlatformOperator`
- `Plan`
- `Subscription`
- `LimitDefinition`
- `FeatureAccessDefinition`
- `WebhookIngressRegistry`
- `PlatformBillingEvent`
- `GlobalConfig`
- `PlatformAuditLog`

### Tenant

- `StoreUser`
- `Role`
- `Permission`
- `Product`
- `ProductImage`
- `Category`
- `StockMovement`
- `StockReservation`
- `Cart`
- `CartItem`
- `Order`
- `OrderItem`
- `Payment`
- `PaymentAttempt`
- `PaymentWebhookEvent`
- `Refund`
- `Chargeback`
- `PaymentProviderConfig`
- `ManualPaymentConfirmation`
- `StoreCheckoutSettings`
- `Customer`
- `GuestCustomer`, se a modelagem separar convidados de clientes cadastrados
- `CustomerAddress`
- `Coupon`
- `AuditLog`

`Customer` e o cliente final/comprador dentro do tenant. Ele nao e o cliente da plataforma.

Cliente da plataforma e representado por `Tenant`, `Subscription` e billing no `public`.

Mesmo e-mail, CPF ou telefone pode existir em tenants diferentes como registros independentes, conforme regra de negocio e LGPD.

`PaymentProviderConfig` pertence ao tenant ou deve ser fortemente vinculada ao tenant em armazenamento seguro. Credenciais nunca devem ser compartilhadas de forma insegura entre schemas.

`WebhookIngressRegistry` vive no `public` e contem apenas metadados minimos para roteamento seguro de webhooks, conforme [33 - Webhook Routing e Secret Management](33-WEBHOOK_ROUTING_SECRET_MANAGEMENT.md).

Planos, assinaturas, limites e acesso a funcionalidades seguem [36 - Entitlements, Planos e Limites](36-ENTITLEMENTS_PLANOS_LIMITES.md).

Estoque deve usar reserva transacional conforme [19 - Estoque e Concorrencia](19-ESTOQUE_CONCORRENCIA.md).

Cancelamentos, reembolsos e chargebacks seguem [20 - Cancelamentos, Reembolsos e Chargeback](20-CANCELAMENTOS_REEMBOLSOS_CHARGEBACK.md).

Entidades financeiras, pessoais e auditaveis devem seguir a estrategia de [26 - Soft Delete e Retencao](26-SOFT_DELETE_RETENCAO.md).

## Constraints Recomendadas

- `Product.slug` unico por tenant.
- `Category.slug` unico por tenant.
- `Order.number` unico por tenant.
- `Payment.provider_payment_id` unico por provider no tenant.
- `PaymentWebhookEvent.event_id` unico por provider no tenant.
- `Coupon.code` unico por tenant.
- `ProductImage.cloudinary_public_id` unico por tenant.
- `StockReservation(order_id, product_id)` coerente por tenant quando aplicavel.
- `Refund(provider_refund_id)` unico por provider no tenant quando aplicavel.
- `Chargeback(provider_chargeback_id)` unico por provider no tenant quando aplicavel.

## Indices Recomendados

- `Order(status, created_at)`.
- `Payment(internal_status, created_at)`.
- `Payment(provider, provider_payment_id)`.
- `PaymentWebhookEvent(provider, event_id)`.
- `PaymentProviderConfig(provider, environment)` unico por tenant quando aplicavel.
- `Product(status, category_id)`.
- `StockMovement(product_id, created_at)`.
- `StockReservation(product_id, expires_at)`.
- `AuditLog(action, created_at)`.
- `Customer(email)`.
- `Customer(cpf)` ou `Customer(phone)` apenas se esses campos existirem e forem usados para busca no tenant.

## Transacoes

Usar `transaction.atomic` para:

- criar pedido;
- reservar estoque;
- expirar reserva de estoque;
- iniciar pagamento local;
- confirmar pagamento manual;
- processar webhook;
- cancelar pedido;
- reembolsar;
- registrar chargeback;
- restaurar backup;
- executar command destrutivo.

## Locks

Usar lock quando houver concorrencia:

- pagamento duplicado;
- webhook duplicado;
- confirmacao manual de pagamento;
- estoque;
- cupom com limite;
- mudanca de status de pedido.
- reembolso/chargeback concorrente.

## Migrations

Regras:

- Separar `SHARED_APPS` e `TENANT_APPS`.
- Nao criar tabela operacional no `public`.
- Testar migration em banco vazio.
- Testar migration em dois tenants.
- Antes de migration em producao, ter backup e plano de rollback.
- Migration de dados deve ser tenant-aware.

## Anti-Padroes

- Usar SQLite em producao.
- Criar coluna `tenant_id` para compensar schema isolado sem necessidade.
- Usar raw SQL sem schema claro.
- Rodar migration sem `migrate_schemas`.
- Criar dados operacionais no `public`.
- Criar Customer final no `public` sem ADR, base legal e necessidade real.
- Usar e-mail de Customer como identificador global entre tenants.
- Compartilhar `PaymentProviderConfig` ou segredo de gateway entre tenants.
- Salvar segredo de pagamento em texto puro.
- Apagar dados sem backup e confirmacao.
