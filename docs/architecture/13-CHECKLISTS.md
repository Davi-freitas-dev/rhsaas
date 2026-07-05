# Checklists

Checklists sao gates operacionais. Nao substituem revisao tecnica.

## Antes de Merge

- [ ] Testes focados verdes.
- [ ] Sem regra sensivel no frontend.
- [ ] Sem secrets no diff.
- [ ] Permissoes revisadas.
- [ ] Querysets tenant-scoped.
- [ ] Logs sem dados sensiveis.
- [ ] Documentacao atualizada quando aplicavel.

## Antes de Criar Migration

- [ ] App correto: public ou tenant.
- [ ] Impacto em dois tenants revisado.
- [ ] Migration testada em banco vazio.
- [ ] Migration testada com dados.
- [ ] Plano de rollback.
- [ ] Backup antes de producao.

## Antes de Deploy

- [ ] `DEBUG=False`.
- [ ] `ALLOWED_HOSTS` correto.
- [ ] HTTPS.
- [ ] CSRF/CORS revisados.
- [ ] Cookies seguros.
- [ ] Checks de seguranca.
- [ ] Testes multi-tenant.
- [ ] Backup recente.
- [ ] Plano de rollback.

## Antes de Liberar Novo Tenant

- [ ] Dominio validado.
- [ ] Schema criado.
- [ ] Migrations aplicadas no schema.
- [ ] Tenant lifecycle definido.
- [ ] Admin inicial criado.
- [ ] Login testado.
- [ ] Isolamento validado.
- [ ] Customer, carrinho e pedido validados apenas no schema do tenant.
- [ ] Mesmo e-mail de Customer em outro tenant nao gera vinculo global.
- [ ] Backup inicial planejado.

## Antes de Liberar Pagamento Real

- [ ] Gateway em modo producao revisado.
- [ ] Secrets rotacionados e protegidos.
- [ ] Secret manager ou envelope encryption definido.
- [ ] WebhookIngressRegistry configurado.
- [ ] Webhook assinado validado.
- [ ] Idempotencia testada.
- [ ] Valor/moeda validados.
- [ ] Eventos conflitantes geram alerta.
- [ ] Conciliacao definida.
- [ ] Pedido nao vira paid sem webhook valido.
- [ ] Reembolso testado.
- [ ] Chargeback documentado.
- [ ] Pagamento manual exige permissao e auditoria.

## Antes de Liberar Estoque Real

- [ ] Reserva transacional implementada.
- [ ] Expiracao de reserva testada.
- [ ] Checkout concorrente testado.
- [ ] Cancelamento antes do pagamento libera reserva.
- [ ] Webhook duplicado nao baixa estoque duas vezes.

## Antes de Ativar Upload Cloudinary

- [ ] Assinatura curta.
- [ ] Folder definido pelo backend.
- [ ] Limite de tamanho.
- [ ] Tipos permitidos.
- [ ] `public_id` validado por schema.
- [ ] Limpeza auditada.
- [ ] Teste tenant A/B.

## Antes de Expor Webhook

- [ ] Webhook routing definido.
- [ ] Tenant resolution nao depende de payload nao autenticado.
- [ ] `secret_ref` configurado.
- [ ] Assinatura.
- [ ] Timestamp.
- [ ] Replay protection.
- [ ] Idempotencia.
- [ ] Rate limit.
- [ ] Logs sanitizados.
- [ ] Alerta para falhas.
- [ ] Teste de duplicidade.

## Antes de Producao

- [ ] Auditoria completa.
- [ ] Restore testado.
- [ ] Observabilidade minima.
- [ ] Hardening HTTP.
- [ ] Dependencias auditadas.
- [ ] Runbook de incidente.
- [ ] Checklist de pagamento aprovado.
- [ ] Privacidade do comprador validada entre dois tenants.
- [ ] Reset de senha tenant-aware testado.
- [ ] Politica de logs/retencao revisada.
- [ ] Politica de soft delete/anonimizacao revisada.
- [ ] Suporte da plataforma auditado.
- [ ] Dominios/HTTPS revisados.
- [ ] State machines canonicas revisadas.
- [ ] Entitlements revisados quando houver billing/planos.

## Antes de Liberar Documentos Privados

- [ ] Storage privado definido.
- [ ] URLs assinadas expiram.
- [ ] Antivirus/scanner definido.
- [ ] Autorizacao de upload/download testada.
- [ ] Retencao definida.
- [ ] AuditLog de download sensivel.

## Antes de Ativar Dominio Customizado

- [ ] Propriedade do dominio validada.
- [ ] Certificado HTTPS emitido.
- [ ] Dominio canonico definido.
- [ ] Alias nao troca tenant.
- [ ] Cookies continuam host-only.

## Antes de Liberar Suporte da Plataforma

- [ ] Menor privilegio definido.
- [ ] Motivo obrigatorio.
- [ ] Acesso temporario.
- [ ] Auditoria completa.
- [ ] Sem acesso a secrets de gateway.

## Antes de Restore

- [ ] Confirmar tenant alvo.
- [ ] Confirmar backup do mesmo tenant.
- [ ] Confirmar ambiente.
- [ ] Criar backup antes do restore.
- [ ] Executar em janela controlada.
- [ ] Validar integridade apos restore.
- [ ] Registrar auditoria.

## Antes de Command Destrutivo

- [ ] Command classificado.
- [ ] Schema explicito.
- [ ] Bloqueia public.
- [ ] Backup valido do mesmo schema.
- [ ] Confirmacao textual.
- [ ] Dry-run quando aplicavel.
- [ ] Auditoria.
