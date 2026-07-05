# Roadmap Tecnico

Este roadmap orienta a implementacao futura sem prometer escopo fechado.

## Fase 0 - Planejamento

- Definir dominio.
- Definir gateway.
- Definir modelo de tenancy.
- Criar ADRs iniciais.
- Definir Definition of Done.

## Fase 1 - Primeiro Commit

- Criar repo backend.
- Criar repo frontend.
- Configurar lint/testes.
- Configurar ambiente local.
- Criar OpenAPI inicial.

## Fase 2 - Base Multi-Tenant

- Django.
- PostgreSQL.
- `django-tenants`.
- Tenant e Domain.
- Host-based tenancy.
- Tenant lifecycle inicial.
- Testes com dois tenants.

## Fase 3 - Auth

- Login/logout/session.
- CSRF.
- roles e permissions.
- operador da plataforma separado.
- testes de sessao entre tenants.

## Fase 4 - Catalogo

- produtos.
- categorias.
- imagens conceituais.
- estoque inicial.
- SEO basico.
- slugs.
- API paginada.

## Fase 5 - Cloudinary

- upload assinado.
- folder por tenant.
- ProductImage.
- limpeza auditada.
- testes de isolamento.

## Fase 6 - Carrinho

- cart.
- cart item.
- expiracao.
- recalculo backend.
- cache seguro.

## Fase 7 - Pedidos

- order.
- order item.
- maquina de estado.
- reserva transacional de estoque.
- cancelamento.
- reembolso.
- chargeback conceitual.

## Fase 8 - Pagamentos/Webhooks

- Payment.
- PaymentAttempt.
- PaymentWebhookEvent.
- WebhookIngressRegistry.
- assinatura.
- idempotencia.
- secret management.
- conciliacao.
- testes de conflito.

## Fase 9 - Dashboard Tenant

- vendas.
- pedidos.
- estoque.
- pagamentos.
- alertas.

## Fase 10 - Plataforma/Admin

- gestao de tenants.
- dominios.
- operadores.
- planos.
- entitlements.
- suporte.
- suporte auditado com menor privilegio.

## Fase 11 - Observabilidade

- logs estruturados.
- auditoria.
- metricas.
- alertas.
- request_id.

## Fase 12 - Beta

- tenants piloto.
- pagamentos em ambiente controlado.
- restore testado.
- hardening.

## Fase 13 - Producao

- deploy.
- HTTPS.
- backups.
- restore testado.
- monitoramento.
- runbooks.
- auditoria final.

## Fase 14 - Escalabilidade

- workers.
- cache.
- indices.
- query optimization.
- CDN.
- filas.
- busca dedicada somente quando necessaria.

## Fase 14.5 - Operacao Avancada

- dominios customizados em escala.
- feature flags.
- disaster recovery maduro.
- logs com retencao formal.
- uploads de documentos sensiveis.
- storage privado.

## Fase 15 - Marketplace Futuro

- apps/integracoes.
- temas.
- extensoes.
- controle de permissoes.

## Fase 16 - API Publica Futura

- OAuth ou estrategia equivalente.
- rate limit por app.
- docs publicas.
- chaves por tenant.
- auditoria.

## Fase Futura - Fiscal e Internacionalizacao

- nota fiscal.
- documentos fiscais.
- CPF/CNPJ e dados fiscais.
- idiomas.
- moedas.
- fuso horario.
- formatacao regional.
