# Disaster Recovery

Disaster Recovery define como recuperar a plataforma ou um tenant apos falha, erro operacional, corrupcao ou incidente.

Recuperacao, exportacao e delecao devem respeitar o estado do tenant definido em [35 - Tenant Lifecycle](35-TENANT_LIFECYCLE.md).

## Objetivos

- backups confiaveis;
- restore testado;
- RPO definido;
- RTO definido;
- recuperacao por tenant;
- recuperacao da plataforma;
- evidencias periodicas.

## RPO e RTO

Definir por fase:

```text
MVP/Beta:
RPO alvo: ate 24 horas
RTO alvo: ate 8 horas

Producao madura:
RPO alvo: menor, conforme plano contratado
RTO alvo: menor, conforme criticidade
```

Valores finais devem ser decisao operacional e comercial.

## Backups

Tipos:

- backup do schema `public`;
- backup por tenant/schema;
- backup de arquivos tenant-scoped;
- backup de configuracoes;
- backup de secrets via secret manager, quando aplicavel;
- backup de logs/auditoria conforme retencao.

## Restore por Tenant

Regras:

- restaurar apenas o schema alvo;
- validar tenant antes do restore;
- criar backup antes de sobrescrever;
- executar em ambiente temporario primeiro quando possivel;
- validar integridade;
- registrar auditoria;
- garantir que tenant B nao seja alterado ao restaurar tenant A.

## Restore da Plataforma

Afeta:

- tenants;
- dominios;
- planos;
- assinaturas;
- operadores;
- configuracoes globais.

Exige janela controlada, plano de comunicacao e validacao extra.

## Testes de Restore

Obrigatorios:

- restaurar tenant em banco temporario;
- validar pedidos, pagamentos e clientes;
- validar dominios;
- validar arquivos/anexos;
- validar auditoria;
- medir tempo real de restore.

## Runbook Minimo

1. Identificar incidente.
2. Congelar alteracoes sensiveis se necessario.
3. Escolher ponto de restauracao.
4. Confirmar escopo: tenant ou plataforma.
5. Executar restore em ambiente temporario.
6. Validar integridade.
7. Executar restore controlado.
8. Registrar evidencias.
9. Comunicar partes afetadas.
10. Fazer postmortem.

## O Que Nao Fazer

- Nao restaurar tenant sem confirmar schema.
- Nao restaurar direto em producao sem teste quando houver risco.
- Nao sobrescrever outro tenant.
- Nao considerar backup valido sem teste de restore.
