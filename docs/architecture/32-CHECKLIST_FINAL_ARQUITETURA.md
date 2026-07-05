# Checklist Final de Arquitetura

Este checklist consolida decisoes concluidas, pendentes, futuras, riscos conhecidos e itens fora do MVP.

## Decisoes Concluidas

- [x] Backend-first.
- [x] Django/DRF.
- [x] PostgreSQL.
- [x] `django-tenants` com schema por tenant.
- [x] Tenant por Host.
- [x] Cookies e sessoes host-only.
- [x] Cliente final tenant-scoped.
- [x] Checkout e pagamento configuraveis por tenant.
- [x] Gateway/webhook validado e idempotente.
- [x] Cloudinary para imagens de produto.
- [x] Backups tenant-scoped.
- [x] OpenAPI como contrato.
- [x] Estoque com reserva transacional recomendado.
- [x] Suporte da plataforma com menor privilegio e auditoria.
- [x] Soft delete para entidades sensiveis.
- [x] Evolucao arquitetural progressiva, sem complexidade prematura.
- [x] Webhook routing com registry minimo no `public`.
- [x] Secret management para gateways.
- [x] State machines canonicas.
- [x] Tenant lifecycle.
- [x] Dominio canonico por tenant.
- [x] Storage privado para documentos sensiveis.
- [x] Entitlements separados de feature flags.

## Decisoes Pendentes Antes do MVP

- [ ] Gateway inicial de pagamento.
- [ ] Modo de checkout padrao para primeira loja.
- [ ] Politica de expiracao de reserva de estoque.
- [ ] Politica de cancelamento/reembolso da primeira versao.
- [ ] Politica de retencao de logs.
- [ ] Politica de suporte/acesso temporario.
- [ ] Provedor de hospedagem.
- [ ] Estrategia de certificados HTTPS.
- [ ] Provedor de secret manager/envelope encryption.
- [ ] Tempos finais de RPO/RTO.
- [ ] Prazos finais de retencao LGPD.

## Decisoes Futuras

- [ ] Conta global de comprador.
- [ ] Marketplace.
- [ ] Split de pagamento.
- [ ] Fiscal.
- [ ] Multimoeda.
- [ ] Internacionalizacao completa.
- [ ] Dominios customizados em larga escala.
- [ ] Busca dedicada.
- [ ] Microsservicos.
- [ ] Multiplos bancos.

## Riscos Conhecidos

- Estoque concorrente exige teste com transacao/lock.
- Webhook precisa lidar com eventos duplicados, tardios e conflitantes.
- Pagamento manual exige permissao forte e auditoria.
- Suporte da plataforma pode virar acesso excessivo se nao houver fluxo formal.
- Logs podem vazar PII/secrets se nao houver scrub.
- Dominios customizados exigem verificacao e certificado.
- Soft delete sem politica pode virar retencao infinita.
- Restore nao e confiavel sem teste periodico.
- Webhook registry mal configurado pode bloquear pagamento valido.
- Feature flag usada como entitlement pode liberar recurso indevidamente.

## Fora do MVP

- Fiscal completo.
- Conta global de comprador.
- Marketplace.
- Split de pagamento.
- Multimoeda real.
- Internacionalizacao completa.
- Microsservicos.
- Eventos distribuidos complexos.
- Multiplos bancos.
- Busca dedicada.
- Observabilidade avancada completa.

## Gate de Arquitetura Antes de Implementar

- [ ] ADRs principais revisados.
- [ ] Threat model revisado.
- [ ] Checklists revisados.
- [ ] Testes obrigatorios planejados.
- [ ] Fluxos de pagamento revisados.
- [ ] Estoque/concorrencia revisado.
- [ ] Privacidade/LGPD revisada.
- [ ] Backup/restore revisado.
- [ ] Suporte/auditoria revisado.
