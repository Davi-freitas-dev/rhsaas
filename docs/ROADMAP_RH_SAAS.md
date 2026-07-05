# Roadmap RH SaaS

Este documento organiza os proximos passos do RH SaaS depois da separacao do
projeto, banco, dominio e deploy proprios.

## Status atual

- Separacao do projeto: concluida.
- Banco de dados proprio: concluido.
- Dominio proprio: concluido.
- Deploy proprio: concluido.

## Ordem recomendada

### 1. Auditoria completa de seguranca

Objetivo: garantir que a base esta segura antes de expor o SaaS para clientes,
trials, APIs publicas ou cobranca.

Checklist inicial:

- revisar `.env`, secrets, chaves e variaveis de producao;
- validar `DEBUG=False`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`
  e `CORS_ALLOWED_ORIGINS`;
- revisar cookies de sessao e CSRF;
- revisar reset de senha, e-mails e rate limits;
- revisar permissoes, grupos, admin e endpoints sensiveis;
- confirmar que backups, banco local, uploads e arquivos temporarios nao entram
  no Git;
- revisar logs para evitar vazamento de dados sensiveis;
- validar headers de seguranca;
- revisar deploy, systemd, Nginx, HTTPS e acesso ao banco;
- rodar `manage.py check --deploy` em ambiente configurado para producao;
- registrar pendencias antes de abrir trial/demo.

Pronto quando:

- nao houver secrets versionados;
- configuracoes criticas estiverem documentadas;
- deploy estiver reproduzivel;
- backups e restore tiverem procedimento claro;
- riscos encontrados tiverem correcao ou aceite documentado.

### 2. Monitoramento e observabilidade basicos

Objetivo: enxergar erros, indisponibilidade e comportamento do sistema antes de
colocar usuarios reais.

Checklist inicial:

- healthcheck simples da aplicacao;
- logs de aplicacao e servidor organizados;
- alertas basicos para erro 5xx, queda do servico e uso anormal;
- monitoramento de disco, memoria e CPU;
- monitoramento de banco;
- verificacao periodica de backup;
- pagina ou procedimento simples de incidente.

Pronto quando:

- uma falha de app, banco ou disco gerar sinal claro;
- houver caminho rapido para consultar logs;
- houver procedimento de rollback/restart documentado.

### 3. Multi-tenant

Objetivo: isolar dados e operacoes por organizacao/cliente.

Checklist inicial:

- definir modelo de tenant/organizacao;
- decidir estrategia de isolamento: campo por tenant, schema por tenant ou banco
  por tenant;
- mapear todos os models que precisam de escopo por tenant;
- garantir que queries, selectors, serializers e services filtram por tenant;
- revisar permissoes por usuario e organizacao;
- revisar admin;
- criar guardrails para impedir acesso cruzado;
- criar testes de isolamento entre tenants;
- revisar backups e restore considerando tenants.

Pronto quando:

- um usuario de um tenant nao consegue ler, alterar ou listar dados de outro;
- endpoints principais tem testes de isolamento;
- fluxos administrativos estao seguros;
- criacao de novo tenant esta documentada.

### 4. Trial e demo

Objetivo: permitir experimentacao controlada sem comprometer dados reais.

Checklist inicial:

- definir tipo de trial: tempo limitado, tenant demo ou ambiente demo;
- criar fluxo de criacao de tenant trial;
- definir expiracao, bloqueio e reativacao;
- criar dados iniciais seguros, sem dados reais do projeto antigo;
- limitar acoes sensiveis no demo, se necessario;
- registrar origem do trial e aceite de termos;
- criar rotina de limpeza ou arquivamento de trials expirados.

Pronto quando:

- um novo usuario consegue testar sem intervencao manual critica;
- dados demo nao se misturam com producao real;
- expiracao e bloqueio funcionam;
- suporte consegue identificar e encerrar trials.

### 5. Assinaturas, planos e cobranca

Objetivo: transformar uso em receita com regras claras de plano, acesso e
cobranca.

Checklist inicial:

- definir planos e limites;
- mapear recursos pagos e gratuitos;
- definir status de assinatura: trial, ativa, vencida, cancelada e bloqueada;
- integrar provedor de pagamento;
- implementar webhooks de pagamento;
- registrar historico de cobranca;
- criar regras de bloqueio e periodo de tolerancia;
- revisar e-mails transacionais;
- revisar seguranca de webhooks.

Pronto quando:

- mudancas de status no provedor refletem no sistema;
- acesso muda conforme plano/status;
- falhas de pagamento tem tratamento claro;
- webhooks sao autenticados e auditaveis.

### 6. APIs publicas

Objetivo: permitir integracoes externas com seguranca, limites e rastreabilidade.

Checklist inicial:

- definir casos de uso reais da API;
- criar autenticacao por token/chave;
- escopar tokens por tenant;
- aplicar rate limit;
- versionar endpoints;
- documentar contratos;
- registrar auditoria de chamadas sensiveis;
- criar politica de revogacao de tokens.

Pronto quando:

- API nao permite acesso entre tenants;
- tokens podem ser criados, rotacionados e revogados;
- limites por plano estao definidos;
- documentacao basica esta disponivel.

### 7. Automacoes com n8n

Objetivo: conectar o RH SaaS a fluxos operacionais externos sem acoplamento
excessivo.

Checklist inicial:

- definir eventos uteis para automacao;
- criar webhooks internos ou endpoints seguros;
- validar autenticacao e assinatura de payload;
- criar exemplos de fluxos n8n;
- limitar repeticoes e reprocessamentos;
- registrar logs de automacao.

Pronto quando:

- automacoes nao dependem de acesso direto ao banco;
- falhas podem ser reprocessadas;
- payloads nao expõem dados desnecessarios.

### 8. WebSocket e notificacoes

Objetivo: entregar atualizacoes em tempo real quando houver dor clara de produto.

Checklist inicial:

- definir quais eventos precisam ser em tempo real;
- avaliar se notificacao simples por e-mail/in-app resolve primeiro;
- escolher stack para WebSocket/canais;
- escopar mensagens por tenant e usuario;
- criar fallback para conexao perdida;
- monitorar conexoes abertas.

Pronto quando:

- notificacoes respeitam tenant/permissao;
- conexoes nao degradam o servidor;
- eventos importantes tem fallback.

## Principios para o roadmap

- Nao abrir trial antes de seguranca e monitoramento basico.
- Nao implementar cobranca antes de multi-tenant.
- Nao expor API publica antes de isolamento, rate limit e auditoria.
- Nao automatizar via n8n com acesso direto ao banco.
- Nao tratar WebSocket como obrigatorio ate existir necessidade clara.

## Proxima acao recomendada

Iniciar a auditoria completa de seguranca com foco em configuracao, deploy,
permissoes, arquivos sensiveis, backups, logs e headers. Depois disso, criar o
plano tecnico do multi-tenant com decisao explicita de estrategia de isolamento.
