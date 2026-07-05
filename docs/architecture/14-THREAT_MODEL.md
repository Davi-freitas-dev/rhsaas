# Threat Model

Modelo inicial de ameacas para o futuro SaaS.

| Area | Ativo protegido | Possivel ataque | Impacto | Mitigacao | Teste recomendado |
| --- | --- | --- | --- | --- | --- |
| Tenants | Dados da loja | Acessar outro tenant por Host/query string | Vazamento entre empresas | Tenant por Host, sem tenant em query, host desconhecido 404 | Dois tenants com IDs iguais |
| IDOR | Produtos/pedidos | Alterar ID na URL | Acesso indevido | Query no schema ativo e permissao | Detail de pedido de outro tenant retorna 404 |
| Pagamentos | Pedido/pagamento | Frontend marcar pago | Fraude | Paid somente por webhook validado | Pedido nao vira paid sem webhook |
| Pagamentos | Credenciais do gateway | Loja A usar credencial da Loja B | Cobranca indevida ou vazamento | PaymentProviderConfig tenant-scoped e secrets protegidos | Tenant A nao le credencial B |
| Segredos | Gateway secret | Segredo em texto puro ou log/API | Comprometimento financeiro | Secret manager/envelope encryption e `secret_ref` | API/log nao retorna segredo |
| Pagamentos | Metodo de pagamento | Cliente manipular metodo no frontend | Checkout fora da regra da loja | Backend valida metodos ativos no tenant | Metodo desativado retorna erro |
| Pagamento manual | Status financeiro | Funcionario marcar pagamento indevido | Fraude operacional | Permissao especifica, motivo e AuditLog | Confirmacao manual sem permissao falha |
| Estoque | Ultimo item | Dois compradores compram simultaneamente | Overselling | Reserva transacional e lock | Checkout concorrente so permite uma reserva |
| Cancelamento | Pedido/estoque | Cancelar pedido pago como se nao houvesse pagamento | Divergencia financeira | Fluxo separado para cancelamento e reembolso | Cancelamento pago exige refund flow |
| Reembolso | Saldo financeiro | Reembolsar acima do pago | Prejuizo/fraude | Validar saldo reembolsavel | Refund parcial acima do saldo falha |
| Webhook | Status financeiro | Webhook falso | Pedido liberado indevidamente | Assinatura, timestamp, idempotencia | Assinatura invalida rejeitada |
| Webhook | Pedido de outro tenant | Evento da Loja A pagar pedido da Loja B | Vazamento/fraude cross-tenant | Validar tenant, provider, reference, valor e moeda | Webhook A nao altera B |
| Webhook routing | Tenant resolution | Resolver tenant por payload nao autenticado | Tenant spoofing | WebhookIngressRegistry no `public` | Payload adulterado nao troca tenant |
| Replay | WebhookEvent | Reenviar evento | Efeito duplicado | Unique event_id e idempotencia | Mesmo evento duas vezes nao duplica |
| Upload | Imagem/produto | Usar public_id de outro tenant | Vazamento ou defacement | Folder por schema e validacao backend | Tenant A nao associa imagem B |
| Auth | Sessao | Reusar cookie em outro host | Cross-tenant auth | Cookies host-only e sessao tenant-aware | Cookie A nao autentica B |
| Cookies | Sessao/CSRF | Usar `Domain=.meusaas.com` | Cookie compartilhado entre subdominios | Host-Only Cookies | Cookie A nao e enviado para B |
| CSRF | Mutacoes autenticadas | Token de um tenant usado em outro | Cross-Tenant Request Forgery | CSRF por Host e trusted origins restritos | CSRF A falha em B |
| Host | Contexto tenant | Frontend envia tenant por header/body/token | Tenant spoofing | Resolver exclusivamente pelo Host | Parametro/header/payload de tenant ignorado |
| Subdominio | Isolamento | Subdominio comprometido tenta expandir impacto | Sessao/cookie/cache de outros tenants expostos | Host-only cookies, cache por schema e schema isolado | Compromisso A nao autentica B |
| Customer | Dados pessoais do comprador | Loja A consultar cliente da Loja B | Vazamento LGPD e concorrencial | Customer no schema ativo e permissao tenant-scoped | Customer de B retorna 404 em A |
| Customer | Identidade do comprador | Mesmo e-mail virar conta global acidental | Confusao de sessao e vazamento | E-mail unico apenas dentro do tenant | Mesmo e-mail em A/B gera contas independentes |
| Guest checkout | Pedido de convidado | Convidado acessar pedido de outro convidado | Vazamento de dados pessoais | Token seguro, sessao tenant-scoped e validacao por tenant | Token A nao acessa pedido B |
| Reset senha | Conta do comprador | Reset em uma loja afetar outra | Sequestro/alteracao indevida | Token e fluxo tenant-aware por Host | Reset A nao altera B |
| Suporte | Dados pessoais | Plataforma acessar comprador sem auditoria | Exposicao e abuso interno | Menor privilegio, justificativa e audit log | Acesso de suporte exige trilha auditada |
| Dominios | Host/tenant | Dominio customizado apontar para tenant errado | Vazamento ou takeover | Verificacao de propriedade e HTTPS | Dominio nao verificado nao ativa |
| SEO | Catalogo | Sitemap de tenant A listar tenant B | Vazamento e indexacao indevida | Sitemap por Host/schema | Sitemap A nao contem URLs B |
| Uploads | Documentos | Baixar anexo de outro tenant | Vazamento de dados | Paths tenant-scoped e autorizacao | Tenant A nao baixa documento B |
| Logs | PII/secrets | Logar CPF/token/segredo gateway | Exposicao LGPD/seguranca | Scrub, retencao e mascaramento | Snapshot de log sem segredo |
| Soft delete | Historico financeiro | Apagar pedido/pagamento fisicamente | Perda de auditoria | Soft delete/arquivamento | Pedido pago nao pode hard-delete |
| Tenant lifecycle | Tenant suspenso | Loja suspensa continuar vendendo | Risco comercial/operacional | Lifecycle bloqueia checkout conforme estado | Suspenso nao cria checkout |
| Entitlements | Feature access | Feature flag liberar recurso pago | Bypass comercial | Separar Plan/Subscription/Limits/Feature Access/Flags | Backend nega recurso sem entitlement |
| Permissoes | Acoes admin | TenantAdmin agir como plataforma | Escalada | Roles separadas | Admin tenant nao acessa plataforma |
| Cache | Dados sensiveis | Cache sem tenant | Vazamento | Prefixo por schema/host | Cache A nao retorna em B |
| Jobs | Dados operacionais | Task sem schema | Escrita no tenant errado | schema_name obrigatorio | Task sem schema falha |
| Commands | Banco | Command no public | Corrupcao ou erro | Guards e confirmacao | Command tenant-only recusa public |
| Backups | Dados tenant | Baixar backup global | Vazamento | Backup tenant-scoped | Admin tenant nao baixa global |
| Exports | Dados pessoais | Export global | Vazamento LGPD | Export por schema e permissao | Export A nao contem B |
| LGPD | Dados pessoais | Logs com PII/secrets | Exposicao | Scrub e retencao | Snapshot de log sem senha/token |

## Ameacas de Pagamento em Detalhe

### Valor Divergente

- Ativo: pedido e pagamento.
- Ataque: webhook com valor menor.
- Mitigacao: comparar amount/currency com Payment esperado.
- Teste: webhook de valor divergente gera `requires_review`.

### Evento Tardio Conflitante

- Ativo: status financeiro.
- Ataque: evento `failed` depois de `paid`.
- Mitigacao: maquina de estados e alerta.
- Teste: paid nao volta para failed silenciosamente.

### Tenant Divergente

- Ativo: isolamento.
- Ataque: payment reference de outro tenant.
- Mitigacao: referencia local no schema ativo e metadata assinada quando disponivel.
- Teste: webhook de tenant errado rejeitado.

## Revisao do Threat Model

Revisar:

- antes do beta;
- antes de pagamentos reais;
- antes de dominio customizado;
- antes de API publica;
- depois de incidente;
- depois de mudanca de gateway.
