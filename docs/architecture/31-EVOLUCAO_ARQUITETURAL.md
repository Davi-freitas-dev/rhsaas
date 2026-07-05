# Evolucao Arquitetural

Este capitulo define quando faz sentido evoluir a arquitetura sem adotar complexidade prematuramente.

## Principio

Comecar com monolito modular Django/DRF, PostgreSQL, Redis quando necessario e jobs controlados.

Nao adotar microsservicos, eventos distribuidos ou multiplos bancos antes de haver necessidade concreta.

## Filas Distribuidas

Adotar quando:

- checkout ou pagamento tiver tarefas lentas;
- webhooks precisarem processamento resiliente;
- envio de e-mail/notificacao crescer;
- conciliacao precisar rodar fora do request.

Toda task deve receber `schema_name`.

## Microsservicos

Considerar apenas quando:

- um dominio tiver escala ou equipe propria;
- deploy independente trouxer ganho real;
- contratos de API/eventos estiverem maduros;
- observabilidade e tracing estiverem prontos.

Nao extrair servico so por organizacao.

## Eventos

Considerar para:

- pagamento confirmado;
- pedido criado;
- estoque reservado;
- fiscal emitido;
- chargeback recebido.

Regras:

- eventos devem carregar tenant/schema;
- idempotencia obrigatoria;
- consumidores nao podem assumir tenant global;
- DLQ e replay planejados.

## Multiplos Bancos

Considerar quando:

- numero de tenants crescer muito;
- isolamento fisico for exigido;
- performance de um grupo afetar demais os outros;
- requisitos comerciais pedirem plano enterprise isolado.

Antes disso, schema por tenant em PostgreSQL e suficiente.

## CDN

Usar para:

- assets estaticos;
- imagens publicas de catalogo;
- arquivos publicos nao sensiveis.

Nao usar CDN para dados pessoais, pedidos, pagamentos ou documentos sensiveis sem desenho proprio.

## Cache Distribuido

Usar quando:

- query repetida pesar;
- catalogo publico tiver alto trafego;
- rate limit precisar estado compartilhado;
- locks distribuidos forem necessarios.

Chaves devem incluir `schema_name` e Host quando ligadas a tenant.

## Busca Dedicada

Considerar quando:

- busca por catalogo no banco ficar lenta;
- filtros e relevancia ficarem complexos;
- volume de produtos crescer.

Indice de busca deve ser tenant-scoped.

## O Que Nao Fazer

- Nao criar microsservicos antes de estabilizar dominio.
- Nao usar eventos para esconder transacao mal modelada.
- Nao usar cache para corrigir query sem indice.
- Nao separar banco sem runbook de backup/restore.
