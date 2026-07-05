# Arquitetura Futura - SaaS de Vendas/E-commerce

Este arquivo e o indice da documentacao futura do SaaS multi-tenant de vendas/e-commerce.

O conteudo detalhado foi reorganizado em `docs/architecture/` para ficar mais profissional, navegavel e reutilizavel. Esta documentacao nao altera o RH SaaS atual, nao promete implementacao e nao deve ser lida como codigo pronto.

## Objetivo

Desenhar uma arquitetura segura para um SaaS de vendas/e-commerce criado do zero, com:

- backend Django/DRF;
- frontend Next.js com TypeScript;
- PostgreSQL;
- multi-tenancy por schema com `django-tenants`;
- identificacao do tenant exclusivamente por `Host`;
- checkout e pagamentos validados pelo backend;
- webhooks assinados e idempotentes;
- imagens via Cloudinary com assinatura gerada pelo backend;
- backups, exports, jobs, cache e arquivos sempre tenant-scoped;
- seguranca, testes, observabilidade e operacao desde a primeira fase.

## Regra de seguranca da documentacao

Todo fluxo documentado deve nascer seguro.

Fluxos simples, provisorios ou inseguros nao devem ser usados como caminho de implementacao. Quando forem mencionados, devem aparecer apenas como anti-padroes em secoes de "O que nao fazer".

## Navegacao Principal

- [00 - Visao Geral](architecture/00-VISAO_GERAL.md)
- [01 - Backend](architecture/01-BACKEND.md)
- [02 - Frontend Next.js](architecture/02-FRONTEND_NEXTJS.md)
- [03 - Multi-Tenant](architecture/03-MULTI_TENANT.md)
- [04 - Database](architecture/04-DATABASE.md)
- [05 - API Guidelines](architecture/05-API_GUIDELINES.md)
- [06 - Pagamentos e Webhooks](architecture/06-PAGAMENTOS_WEBHOOKS.md)
- [07 - Cloudinary e Imagens](architecture/07-CLOUDINARY_IMAGENS.md)
- [08 - Seguranca](architecture/08-SEGURANCA.md)
- [09 - Testes](architecture/09-TESTES.md)
- [10 - Deploy e Infra](architecture/10-DEPLOY_INFRA.md)
- [11 - Observabilidade](architecture/11-OBSERVABILIDADE.md)
- [12 - Roadmap](architecture/12-ROADMAP.md)
- [13 - Checklists](architecture/13-CHECKLISTS.md)
- [14 - Threat Model](architecture/14-THREAT_MODEL.md)
- [15 - Custos e Escalabilidade](architecture/15-CUSTOS_ESCALABILIDADE.md)
- [16 - Atores, Clientes e Identidades](architecture/16-ATORES_CLIENTES.md)
- [17 - Isolamento por Host e Autenticacao](architecture/17-ISOLAMENTO_HOST_AUTH.md)
- [18 - Checkout e Pagamentos por Tenant](architecture/18-CHECKOUT_PAGAMENTOS_POR_TENANT.md)
- [19 - Estoque e Concorrencia](architecture/19-ESTOQUE_CONCORRENCIA.md)
- [20 - Cancelamentos, Reembolsos e Chargeback](architecture/20-CANCELAMENTOS_REEMBOLSOS_CHARGEBACK.md)
- [21 - Fiscal](architecture/21-FISCAL.md)
- [22 - Suporte da Plataforma](architecture/22-SUPORTE_PLATAFORMA.md)
- [23 - SEO e Catalogo](architecture/23-SEO_CATALOGO.md)
- [24 - Dominios](architecture/24-DOMINIOS.md)
- [25 - Internacionalizacao](architecture/25-INTERNACIONALIZACAO.md)
- [26 - Soft Delete e Retencao](architecture/26-SOFT_DELETE_RETENCAO.md)
- [27 - Disaster Recovery](architecture/27-DISASTER_RECOVERY.md)
- [28 - Logs, Auditoria e Retencao](architecture/28-LOGS_AUDITORIA_RETENCAO.md)
- [29 - Uploads, Anexos e Documentos](architecture/29-UPLOADS_DOCUMENTOS.md)
- [30 - Feature Flags](architecture/30-FEATURE_FLAGS.md)
- [31 - Evolucao Arquitetural](architecture/31-EVOLUCAO_ARQUITETURAL.md)
- [32 - Checklist Final de Arquitetura](architecture/32-CHECKLIST_FINAL_ARQUITETURA.md)
- [33 - Webhook Routing e Secret Management](architecture/33-WEBHOOK_ROUTING_SECRET_MANAGEMENT.md)
- [34 - State Machines Canonicas](architecture/34-STATE_MACHINES_CANONICAS.md)
- [35 - Tenant Lifecycle](architecture/35-TENANT_LIFECYCLE.md)
- [36 - Entitlements, Planos e Limites](architecture/36-ENTITLEMENTS_PLANOS_LIMITES.md)

## ADRs

- [ADR 0001 - Backend-first](architecture/ADR/0001-backend-first.md)
- [ADR 0002 - Django/DRF](architecture/ADR/0002-django-drf.md)
- [ADR 0003 - PostgreSQL](architecture/ADR/0003-postgresql.md)
- [ADR 0004 - django-tenants com schema por tenant](architecture/ADR/0004-django-tenants-schema-por-tenant.md)
- [ADR 0005 - Tenant por Host](architecture/ADR/0005-tenant-por-host.md)
- [ADR 0006 - Next.js com TypeScript](architecture/ADR/0006-nextjs-typescript.md)
- [ADR 0007 - Cloudinary para imagens](architecture/ADR/0007-cloudinary-para-imagens.md)
- [ADR 0008 - Gateway externo com webhooks idempotentes](architecture/ADR/0008-gateway-externo-webhooks-idempotentes.md)
- [ADR 0009 - Backups tenant-scoped](architecture/ADR/0009-backups-tenant-scoped.md)
- [ADR 0010 - OpenAPI como contrato](architecture/ADR/0010-openapi-como-contrato.md)
- [ADR 0011 - Cliente final tenant-scoped](architecture/ADR/0011-cliente-final-tenant-scoped.md)
- [ADR 0012 - Host-only authentication](architecture/ADR/0012-host-only-authentication.md)
- [ADR 0013 - Checkout e pagamentos configuraveis por tenant](architecture/ADR/0013-checkout-e-pagamentos-configuraveis-por-tenant.md)
- [ADR 0014 - Estoque com reserva transacional](architecture/ADR/0014-estoque-com-reserva-transacional.md)
- [ADR 0015 - Cancelamentos, reembolsos e chargeback auditados](architecture/ADR/0015-cancelamentos-reembolsos-chargeback-auditados.md)
- [ADR 0016 - Suporte da plataforma auditado](architecture/ADR/0016-suporte-plataforma-auditado.md)
- [ADR 0017 - Soft delete e retencao](architecture/ADR/0017-soft-delete-e-retencao.md)
- [ADR 0018 - Dominios customizados e HTTPS](architecture/ADR/0018-dominios-customizados-e-https.md)
- [ADR 0019 - Evolucao arquitetural progressiva](architecture/ADR/0019-evolucao-arquitetural-progressiva.md)
- [ADR 0020 - Webhook routing e tenant resolution](architecture/ADR/0020-webhook-routing-e-tenant-resolution.md)
- [ADR 0021 - Secret management para gateways](architecture/ADR/0021-secret-management-gateways.md)
- [ADR 0022 - State machines canonicas](architecture/ADR/0022-state-machines-canonicas.md)
- [ADR 0023 - Tenant lifecycle](architecture/ADR/0023-tenant-lifecycle.md)
- [ADR 0024 - Dominio canonico e aliases](architecture/ADR/0024-canonical-domain-aliases.md)
- [ADR 0025 - Storage privado para documentos sensiveis](architecture/ADR/0025-storage-privado-documentos-sensiveis.md)
- [ADR 0026 - Entitlements, planos e limites](architecture/ADR/0026-entitlements-planos-limites.md)

## Decisoes Arquiteturais Consolidadas

- O backend e a fonte da verdade para regras de negocio, precos, estoque, permissao e pagamento.
- O frontend e responsavel por experiencia, validacao de interface e consumo seguro da API, mas nao confirma pagamento nem autoriza operacao critica.
- Cada loja/empresa deve ter um schema PostgreSQL proprio.
- O schema `public` deve conter apenas dados globais da plataforma.
- Produtos, pedidos, carrinhos, clientes finais, pagamentos de loja e estoque pertencem ao schema do tenant.
- Cliente da plataforma/loja e cliente final/comprador sao conceitos diferentes.
- Customer e tenant-scoped; nao existe conta global de comprador por padrao.
- O tenant deve ser resolvido pelo `Host`, nunca por parametro controlado pelo usuario.
- Nenhum tenant pode ser selecionado por query string, header customizado ou payload.
- Cookies de sessao e CSRF devem ser host-only, sem `Domain=.meusaas.com`.
- Cada subdominio possui autenticacao, sessao, cookies, CSRF, cache e contexto de seguranca independentes.
- Cache, throttling, logs, jobs e arquivos ligados a tenant devem incluir `schema_name`.
- Autenticacao do cliente final e modos de compra podem ser configurados por tenant, mas sempre validados pelo backend.
- Configuracoes de pagamento e credenciais sao tenant-scoped.
- Webhooks precisam validar assinatura, idempotencia, valor, moeda, tenant e referencia externa antes de alterar pedido.
- Webhook routing usa registry minimo no `public`; segredos de gateway usam secret manager ou envelope encryption.
- Estados de pedido, pagamento, reembolso, chargeback e estoque seguem state machines canonicas.
- Estoque deve usar reserva temporaria transacional para evitar overselling.
- Cancelamentos, reembolsos e chargebacks devem ser auditados e passar por services backend.
- Tenant lifecycle controla criacao, suspensao, inadimplencia, reativacao, exportacao, encerramento e delecao segura.
- Suporte da plataforma deve seguir menor privilegio, motivo obrigatorio e auditoria.
- Dominios customizados futuros exigem verificacao, dominio canonico e HTTPS.
- Soft delete/retencao deve proteger entidades financeiras, pessoais e auditaveis.
- Entitlements separam Plan, Subscription, Limits, Feature Access e Feature Flags.
- Uploads de imagem devem usar assinatura gerada pelo backend e metadados tenant-scoped.
- Jobs e commands operacionais devem exigir schema explicito.
- Backups, exports e restores devem ser tenant-scoped e auditados.
- OpenAPI deve ser tratado como contrato entre backend e frontend.
- A evolucao para filas, eventos, microsservicos, busca dedicada, CDN e multiplos bancos nao deve ser prematura.

## Como Usar Este Conjunto de Docs

1. Leia a visao geral.
2. Consulte os ADRs antes de iniciar implementacao.
3. Use os checklists antes de merge, migration, deploy, pagamentos reais, uploads e restores.
4. Atualize os ADRs quando uma decisao arquitetural mudar.
5. Atualize o threat model sempre que surgir novo fluxo sensivel.

## Fora de Escopo Nesta Documentacao

- Implementar codigo.
- Copiar regra de negocio de outro produto.
- Definir layout final de telas.
- Escolher fornecedor final de pagamento.
- Prometer deploy, prazos ou escopo comercial fechado.
