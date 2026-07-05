# Estrategia de Testes

Testes devem provar isolamento, seguranca e comportamento financeiro.

## Tipos de Teste

### Unit

Validam funcoes puras, validators, mapeamentos e maquinas de estado.

### Integration

Validam services com banco e transacoes.

### API

Validam endpoints, permissao, serializacao, erros e codigos HTTP.

### Tenant Isolation

Obrigatorio desde o inicio.

Casos:

- dois tenants;
- IDs iguais;
- host correto;
- host desconhecido;
- sessao isolada;
- cache isolado.
- mesmo e-mail de comprador em dois tenants;
- carrinho anonimo isolado por tenant;
- reset de senha tenant-aware.

### Payments

Casos:

- pagamento inicia pending/processing;
- pedido nao vira paid sem webhook;
- webhook invalido e rejeitado;
- webhook duplicado e idempotente;
- valor divergente gera alerta;
- evento conflitante nao corrige silenciosamente.
- tenant A usa provider diferente do tenant B;
- credenciais de pagamento nao vazam entre tenants;
- pagamento manual exige permissao e auditoria.

### Security

Casos:

- IDOR;
- permissao;
- brute force;
- CSRF;
- CORS;
- upload invalido;
- rate limit;
- command bloqueando public.

### E2E

Playwright ou equivalente para fluxos:

- login;
- catalogo;
- carrinho;
- checkout aguardando pagamento;
- painel tenant;
- produto com imagem.

### Performance

Validar:

- query count;
- paginacao;
- indices;
- endpoints com lista;
- checkout sob concorrencia.

### Mutation Testing

Opcional, util para regras criticas de pagamento e permissao.

## Testes Obrigatorios

- Tenant A nao acessa produto de tenant B.
- Tenant A nao acessa pedido de tenant B.
- Usuario de tenant A nao autentica no tenant B.
- Comprador de tenant A nao autentica no tenant B.
- Mesmo e-mail cadastrado como Customer em dois tenants cria contas independentes.
- Customer com mesmo e-mail em tenants diferentes tem IDs e dados independentes.
- Carrinho anonimo do tenant A nao aparece no tenant B.
- Pedido do comprador no tenant A nao aparece no tenant B.
- Reset de senha do tenant A nao afeta tenant B.
- Mesmo navegador autenticado em `loja-a` e `loja-b` mantem cookies diferentes.
- Mesmo navegador autenticado em `loja-a` e `loja-b` mantem sessoes diferentes.
- Token CSRF de `loja-a` nao valida request mutavel em `loja-b`.
- Logout de `loja-a` nao afeta sessao de `loja-b`.
- Cache e throttling usam `schema_name` e Host.
- Tenant nao pode ser selecionado por query string, header customizado, body ou token do frontend.
- Operador da loja nao acessa clientes finais de outro tenant.
- Operador da plataforma so acessa dados de comprador por fluxo auditado, se existir.
- Mesmo ID em tenants diferentes retorna dado correto.
- Public nao possui dados operacionais.
- Command tenant-only recusa public.
- Backup/export tenant-scoped.
- Upload Cloudinary rejeita public_id de outro tenant.
- Webhook sem assinatura falha.
- Webhook duplicado nao duplica efeitos.
- Webhook com payload adulterado nao troca tenant.
- WebhookIngressRegistry inativo nao processa pagamento.
- Tenant A usa provider diferente do tenant B.
- Tenant A nao acessa credencial do tenant B.
- Webhook do tenant A nao paga pedido do tenant B.
- Metodo de pagamento desativado nao pode ser usado.
- Compra como convidado gera pedido apenas no tenant atual.
- Pagamento manual exige permissao.
- Confirmacao manual gera auditoria.
- Segredo do gateway nao aparece em logs/API/frontend.
- Token de acompanhamento de convidado do tenant A nao consulta pedido do tenant B.
- Tenant suspenso nao cria novo checkout.
- Feature flag nao libera recurso sem entitlement.
- Documento privado do tenant A nao pode ser baixado pelo tenant B.

## Gate de Producao

Antes de producao:

- unit verdes;
- API verdes;
- multi-tenant verdes;
- pagamentos/webhooks verdes;
- security tests verdes;
- E2E minimo verde;
- coverage minimo definido;
- auditoria manual registrada.
