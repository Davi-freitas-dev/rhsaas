# Logs, Auditoria e Retencao

Este capitulo complementa observabilidade com regras de retencao, anonimizacao, LGPD e exportacao.

## Tipos de Registro

- logs tecnicos;
- logs de seguranca;
- logs de auditoria;
- eventos de pagamento;
- eventos de webhook;
- logs de suporte;
- logs de jobs/commands;
- trilhas de export/download.

## Campos Minimos

- timestamp;
- request_id;
- schema_name;
- host;
- user_id;
- role;
- ip;
- action;
- object_type;
- object_id;
- status;
- error_code;
- duration_ms;

## Retencao

Definir por categoria:

- logs tecnicos: prazo curto/medio;
- auditoria: prazo maior;
- eventos financeiros: conforme necessidade legal/operacional;
- payloads sanitizados de webhook: prazo controlado;
- logs de suporte: prazo conforme politica de privacidade.

Prazos finais dependem de decisao juridica e comercial.

## Anonimizacao

Quando aplicavel:

- remover ou mascarar dados pessoais;
- preservar referencias tecnicas necessarias;
- manter trilha de auditoria sem expor segredo;
- separar anonimizacao de exclusao fisica.

## Exportacao

Exports de logs/auditoria devem:

- ser tenant-scoped quando ligados a tenant;
- exigir permissao;
- gerar AuditLog;
- usar arquivo temporario seguro;
- expirar;
- nao conter secrets.

## LGPD

Regras:

- minimizacao;
- finalidade;
- retencao definida;
- acesso controlado;
- rastreabilidade;
- mascaramento de dados sensiveis;
- resposta a solicitacoes de titular quando aplicavel.

## Operacoes LGPD

### Exportacao

- exportacao de dados pessoais deve ser tenant-scoped;
- arquivo deve expirar;
- download exige autenticacao e autorizacao;
- export gera AuditLog;
- export nao inclui dados de outros tenants.

### Anonimizacao

- anonimizar quando nao houver obrigacao legal de manter dado identificavel;
- preservar referencias financeiras/fiscais quando necessario;
- registrar motivo e executor;
- evitar reidentificacao desnecessaria.

### Exclusao

- exclusao fisica so quando nao houver obrigacao de retencao;
- pedidos, pagamentos e auditoria tendem a exigir retencao/anonimizacao, nao hard delete;
- solicitacao do titular deve ser conciliada com obrigacoes legais.

### Consentimento

- consentimento deve ter finalidade, origem, timestamp e versao do texto;
- retirada de consentimento nao deve apagar automaticamente dado legalmente necessario;
- marketing deve ser separado de transacao operacional.

### Minimizacao

- coletar CPF/CNPJ apenas quando necessario;
- coletar data de nascimento apenas se houver finalidade clara;
- evitar armazenar dados de cartao;
- logs e analytics devem usar mascaramento.

## O Que Nao Logar

- senha;
- token;
- cookie;
- authorization header;
- segredo de gateway;
- payload bruto de cartao;
- chave privada;
- documento pessoal sem necessidade.
