# Tenant Lifecycle

Este documento define o ciclo de vida de um tenant/loja na plataforma.

## Estados Canonicos

```text
provisioning
active
trial
past_due
suspended
blocked
reactivating
export_pending
closing
closed
deletion_scheduled
deleted
```

## Criacao

Fluxo:

- criar Tenant no `public`;
- criar Domain/subdominio;
- criar schema PostgreSQL;
- aplicar migrations do tenant;
- criar usuario/admin inicial da loja;
- configurar plano/subscription;
- registrar auditoria;
- validar acesso por Host.

Falha durante provisionamento deve deixar estado claro e recuperavel.

## Trial

Quando existir:

- limites definidos por plano;
- data de expiracao;
- bloqueios progressivos;
- comunicacao ao tenant;
- sem apagar dados automaticamente.

## Inadimplencia

Estados recomendados:

- `past_due`: aviso e restricoes leves;
- `suspended`: operacao limitada;
- `blocked`: acesso operacional bloqueado, mantendo dados preservados.

Regras:

- compradores podem ou nao acessar loja suspensa conforme politica do produto;
- checkout deve ser bloqueado se o tenant nao puder vender;
- webhooks financeiros pendentes ainda podem ser processados para conciliacao;
- exports de dados podem continuar disponiveis por prazo legal/comercial.

## Suspensao e Bloqueio

Motivos:

- inadimplencia;
- abuso;
- risco de fraude;
- solicitacao do cliente;
- decisao operacional.

Exige:

- motivo;
- operador;
- timestamp;
- AuditLog;
- politica de comunicacao.

## Reativacao

Fluxo:

- validar motivo de reativacao;
- validar billing/plano;
- reabilitar Domain;
- reabilitar checkout quando aplicavel;
- registrar auditoria;
- validar smoke check por Host.

## Exportacao

Tenant deve poder exportar dados conforme contrato e LGPD.

Regras:

- export tenant-scoped;
- autorizacao explicita;
- arquivo temporario seguro;
- expiracao;
- AuditLog;
- sem dados de outros tenants.

## Encerramento

Fluxo:

- marcar `closing`;
- bloquear novas vendas;
- permitir conclusao de pedidos pendentes conforme politica;
- permitir export;
- congelar configuracoes criticas;
- definir prazo de retencao;
- registrar auditoria.

## Delecao Segura

Delecao fisica do schema e etapa final e irreversivel.

Antes:

- confirmar tenant alvo;
- confirmar backups/retencao;
- confirmar obrigacoes legais;
- confirmar export entregue quando aplicavel;
- exigir aprovacao forte;
- registrar evidencias.

Depois:

- remover ou arquivar dominios;
- revogar secrets;
- limpar arquivos tenant-scoped conforme politica;
- manter registros minimos de plataforma quando legalmente necessario.

## O Que Nao Fazer

- Nao apagar tenant por inadimplencia automaticamente.
- Nao reutilizar schema_name.
- Nao reutilizar dominio sem validar ownership.
- Nao permitir tenant bloqueado criar checkout.
- Nao deletar dados sem periodo de retencao definido.
