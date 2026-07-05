# Custos e Escalabilidade

Esta visao ajuda a planejar crescimento sem antecipar complexidade desnecessaria.

## Custos Provaveis

- Servidor web/API.
- PostgreSQL.
- Redis.
- Workers.
- Cloudinary.
- Gateway de pagamento.
- Dominio e DNS.
- Certificados/HTTPS.
- Logs e monitoramento.
- Backups.
- CDN.
- E-mail transacional.

## Cloudinary

Custos variam por:

- storage;
- transformacoes;
- bandwidth;
- quantidade de imagens;
- limpeza mal planejada.

Mitigacoes:

- limitar tamanho;
- gerar variantes necessarias;
- limpar imagens removidas;
- usar CDN/cache corretamente.

## PostgreSQL

Pontos de escala:

- conexoes;
- tamanho por tenant;
- indices;
- queries lentas;
- backups;
- restore.

Escalar:

- verticalmente no inicio;
- ajustar indices;
- otimizar querysets;
- separar read replicas apenas quando necessario.

## Redis

Usos:

- cache;
- sessoes;
- throttling;
- locks;
- filas.

Cuidados:

- memoria;
- eviction policy;
- isolamento por tenant;
- seguranca de rede.

## Workers

Adicionar workers quando:

- webhooks demorarem;
- uploads exigirem pos-processamento;
- conciliacao crescer;
- notificacoes aumentarem;
- jobs bloquearem requests.

Jobs devem ser idempotentes e receber schema.

## Cache

Adicionar cache quando:

- catalogo publico tiver alta leitura;
- dashboards forem custosos;
- integracoes externas tiverem limite.

Nao cachear de forma insegura:

- pagamentos;
- sessao;
- carrinho;
- pedidos sensiveis;
- exports.

## Quando Separar Servicos

Separar servicos apenas quando houver motivo real:

- volume de pagamento alto;
- fila dedicada para webhooks;
- processamento de imagem pesado;
- API publica com escala propria;
- time separado mantendo modulo.

Antes disso, monolito Django bem organizado tende a ser mais simples e seguro.

## Otimizacoes Prioritarias

1. Paginacao.
2. Indices.
3. `select_related`.
4. `prefetch_related`.
5. Query count tests.
6. Cache tenant-aware.
7. Workers.
8. CDN/imagens.
9. Separacao de servicos, se necessario.

