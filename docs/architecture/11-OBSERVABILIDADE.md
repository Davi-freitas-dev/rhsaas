# Observabilidade

Observabilidade minima faz parte do hardening.

Regras de retencao, anonimizacao, LGPD, exportacao e trilha de auditoria detalhada estao em [28 - Logs, Auditoria e Retencao](28-LOGS_AUDITORIA_RETENCAO.md).

## Logs Estruturados

Campos recomendados:

- `timestamp`;
- `level`;
- `request_id`;
- `schema_name`;
- `host`;
- `user_id`;
- `ip`;
- `action`;
- `object_type`;
- `object_id`;
- `status`;
- `duration_ms`;
- `error_code`.

Logs, metricas, traces, jobs, arquivos temporarios, exports e backups devem carregar `schema_name` quando estiverem ligados a um tenant.

Nao registrar tenant apenas por nome visual, query string, header customizado ou payload. Para requisicoes web, o tenant observado deve ser o tenant resolvido pelo `Host`.

## Eventos Auditaveis

- login/logout;
- reset de senha;
- criacao/alteracao de produto;
- alteracao de preco;
- movimento de estoque;
- criacao/cancelamento de pedido;
- inicio de pagamento;
- webhook recebido;
- status de pagamento alterado;
- upload/exclusao de imagem;
- export/download;
- command destrutivo;
- restore.

## Metricas

- latencia por endpoint;
- taxa de erro;
- requests por tenant;
- login failures;
- webhooks invalidos;
- webhooks duplicados;
- pagamentos pendentes;
- fila de workers;
- uso de banco;
- cache hit/miss;
- upload failures.
- throttling por schema/usuario/IP.

## Alertas

Alertar para:

- erro 5xx elevado;
- webhook invalido recorrente;
- divergencia de pagamento;
- command destrutivo;
- falha de backup;
- falha de restore;
- fila travada;
- alto numero de login failures.

## Tracing Futuro

Tracing pode ser adicionado para:

- checkout;
- pagamento;
- webhook;
- jobs;
- integracoes externas.

## Retencao

Definir retencao por tipo:

- logs tecnicos;
- auditoria;
- eventos de pagamento;
- payloads de webhook sanitizados;
- exports.

## Dados Sensiveis

Nao logar:

- senha;
- token;
- secret;
- payload bruto de cartao;
- authorization header;
- cookies;
- dados pessoais sem necessidade.
