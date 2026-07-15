# Plano do pool de tenants demo

> **Documento historico:** este plano registra uma fase anterior, na qual
> `demo1...demo10` ainda eram considerados uma unica pool. A arquitetura
> vigente mantem `demo1` permanente e usa apenas `demo2...demo10` na pool
> publica automatica. A fonte de acompanhamento atual e
> `PLANO_LIBERACAO_DEMO_PUBLICA_AUTOMATICA.md`.

Este documento descreve a fase futura para criar um pool de tenants de
demonstracao `demo1...demo10` no RH SaaS. Ele e um plano tecnico, nao uma
implementacao.

Este projeto nao sera vendido inicialmente como um SaaS comercial
multi-tenant por assinatura. O objetivo do pool demo e servir como portfolio,
teste controlado e demonstracao tecnica de multi-tenancy por schema.

Uma venda futura mais provavel, se houver, seria a implantacao individual da
aplicacao para um cliente especifico, com ambiente proprio, e nao uma operacao
SaaS multi-tenant aberta para varios clientes pagando assinatura.

## Estado atual

- A demo fixa atual continua usando apenas o tenant `rh_teste`.
- A demo fixa `rh_teste` segue indicada para teste controlado,
  preferencialmente com poucos testadores e ciente de que usuarios simultaneos
  compartilham os mesmos dados.
- O pool `demo1...demo10` sera uma fase nova, separada da demo fixa.
- O pool demo nao muda o posicionamento inicial do projeto: ele existe para
  demonstracao tecnica e teste controlado, nao para venda SaaS comercial.
- O backend usa `django-tenants`.
- O tenant e resolvido pelo `Host` atraves de
  `django_tenants.middleware.main.TenantMainMiddleware`.
- Nao existe `tenancy/middleware.py` no projeto atual.
- O dominio atual `api-demo-rh.taquiondev.com.br` deve continuar apontando para
  `rh_teste` ate a troca planejada.

## Objetivo da fase

Criar uma base segura para oferecer ate 10 vagas de teste isoladas, com um
tenant/schema proprio por testador, usando operacao manual e controlada.

A finalidade principal e demonstrar, em portfolio, que o backend consegue
isolar dados por schema usando `django-tenants`.

A fase deve permitir que um operador:

- provisione previamente `demo1...demo10`;
- associe uma vaga demo a um testador;
- crie ou ative um usuario demo dentro do schema correto;
- acompanhe status e expiracao da vaga;
- bloqueie vaga expirada;
- resete o tenant demo com seguranca;
- libere a vaga para novo testador.

Parametros iniciais sugeridos:

- duracao da vaga: 3 dias;
- limite de armazenamento por tenant: 50 MB;
- tenants do pool: `demo1`, `demo2`, ..., `demo10`;
- dominios tecnicos:
  `demo1.api-demo-rh.taquiondev.com.br` ate
  `demo10.api-demo-rh.taquiondev.com.br`.

## Escopo

- Modelar metadata do pool demo.
- Criar comandos administrativos seguros.
- Proteger comandos destrutivos com guards explicitos.
- Registrar status de vaga: livre, ocupada, expirada e bloqueada.
- Registrar inicio e fim do lease.
- Preparar reset seguro de schemas demo.
- Permitir auditoria basica de tamanho por schema.
- Testar isolamento entre tenants demo.
- Manter limite simples de 50 MB por tenant como protecao operacional da demo.

## Fora de escopo nesta fase

- Tela publica de cadastro/solicitacao da demo.
- Provisionamento automatico disparado por usuario anonimo.
- SaaS comercial multi-tenant por assinatura.
- Pagamentos, planos comerciais, billing ou gestao de assinaturas.
- Autoescala ou arquitetura comercial de alta escala.
- Limites complexos de consumo, quotas comerciais ou planos por faixa.
- Automacao total de reset sem validacao operacional inicial.
- Mudancas no tenant fixo `rh_teste`.
- Migrar usuarios reais ou dados reais para o pool demo.

## Arquitetura proposta

### Resolucao de tenant

O `TenantMainMiddleware` do `django-tenants` escolhe o tenant pelo `Host` da
requisicao. Por isso, cada tenant demo precisa ter um registro em `Domain`:

- `demo1.api-demo-rh.taquiondev.com.br` -> tenant/schema `demo1`;
- `demo2.api-demo-rh.taquiondev.com.br` -> tenant/schema `demo2`;
- ...
- `demo10.api-demo-rh.taquiondev.com.br` -> tenant/schema `demo10`.

O path continua sendo `/api`. O schema nao deve ser decidido por path,
querystring ou payload.

### DNS e proxy

Para a fase do pool, o caminho operacional mais simples e preparar:

- DNS wildcard futuro: `*.api-demo-rh.taquiondev.com.br`;
- Nginx aceitando `*.api-demo-rh.taquiondev.com.br`;
- certificado TLS cobrindo o wildcard ou os subdominios necessarios;
- todos os subdominios apontando para o mesmo Gunicorn/backend.

O isolamento vem do `Host` recebido pelo Django, nao de processos separados.
Nao ha necessidade, nesta fase, de autoescala ou separacao comercial de
infraestrutura por cliente.

### Frontend unico

O frontend publico pode continuar em:

- `https://demo-rh.taquiondev.com.br`

Porem, para varios testadores isolados ao mesmo tempo, o frontend precisara
saber qual API tecnica usar para cada lease, por exemplo:

- testador A chama `https://demo1.api-demo-rh.taquiondev.com.br/api`;
- testador B chama `https://demo2.api-demo-rh.taquiondev.com.br/api`.

Na demo fixa atual, `NEXT_PUBLIC_API_BASE_URL` aponta para um unico backend.
Isso e suficiente para `rh_teste`, mas nao distribui usuarios entre
`demo1...demo10`.

Para a primeira fase do pool, a ocupacao da vaga pode ser manual: o operador
define qual tenant demo sera usado e entrega o acesso correspondente ao
testador. Cadastro publico automatico fica fora de escopo por enquanto.

## Modelagem: DemoTenantSlot

Modelo principal sugerido para ficar no schema publico, junto dos modelos de
tenancy.

Campos sugeridos:

- `tenant`: FK/OneToOne para `Tenant`;
- `slot_code`: identificador curto, exemplo `demo1`;
- `status`: `livre`, `ocupado`, `expirado`, `bloqueado`;
- `assigned_name`: nome informado pelo testador ou operador;
- `assigned_email`: email do testador;
- `assigned_phone`: telefone opcional;
- `lease_started_at`: inicio da ocupacao;
- `lease_expires_at`: fim previsto;
- `last_reset_at`: ultima limpeza/recriacao segura;
- `last_assigned_at`: ultima ocupacao;
- `max_storage_mb`: padrao `50`;
- `notes`: observacao operacional opcional;
- `created_at` e `updated_at`.

Regras sugeridas:

- `slot_code` unico;
- `tenant` unico;
- `slot_code` permitido apenas entre `demo1` e `demo10`;
- status inicial `livre`;
- ao ocupar, preencher lease e dados do testador;
- ao expirar, bloquear acesso antes de resetar;
- ao resetar, voltar para `livre` somente depois de limpar/recriar o schema.

## Modelagem opcional: DemoTenantLease

Se for importante manter historico de ocupacoes, criar um modelo separado:

- `slot`: FK para `DemoTenantSlot`;
- `assigned_name`;
- `assigned_email`;
- `assigned_phone`;
- `started_at`;
- `expires_at`;
- `ended_at`;
- `end_reason`: expirado, reset_manual, cancelado, bloqueado;
- `created_user_id` ou identificador do usuario demo criado;
- `created_at`.

Com esse modelo, `DemoTenantSlot` guarda o estado atual da vaga e
`DemoTenantLease` guarda o historico. Para a primeira implementacao, o lease
pode ficar no proprio `DemoTenantSlot` se o historico nao for necessario.

## Comandos planejados

### provisionar_pool_demo

Responsavel por criar ou ajustar `demo1...demo10`.

Comportamento esperado:

- criar tenants ausentes;
- criar domains tecnicos ausentes;
- garantir metadata `DemoTenantSlot`;
- rodar migracoes de tenant quando apropriado;
- nao alterar `rh_teste`;
- ser idempotente.

### ocupar_tenant_demo

Responsavel por reservar uma vaga para um testador.

Comportamento esperado:

- selecionar uma vaga `livre`;
- aceitar dados do testador;
- definir lease de 3 dias por padrao;
- criar ou ativar usuario demo dentro do schema correto;
- marcar slot como `ocupado`;
- exibir somente informacoes operacionais seguras.

Senhas de usuarios demo nunca devem ser gravadas em arquivo, log ou banco em
texto puro. O banco deve armazenar apenas hash de senha pelo mecanismo padrao do
Django. Se houver senha inicial temporaria, ela deve ser entregue uma unica vez
por canal seguro ou substituida por fluxo de definicao de senha.

### expirar_leases_demo

Responsavel por marcar vagas vencidas.

Comportamento esperado:

- localizar slots `ocupado` com `lease_expires_at` no passado;
- bloquear acesso do usuario demo no schema correspondente;
- marcar slot como `expirado` ou `bloqueado`;
- nao resetar automaticamente ate o reset seguro estar validado.

### resetar_tenant_demo

Responsavel por limpar uma vaga demo expirada/bloqueada e libera-la.

Comportamento esperado:

- aceitar somente `demo1...demo10`;
- bloquear `public`;
- bloquear `rh_teste`;
- bloquear qualquer schema fora do padrao do pool;
- exigir confirmacao explicita;
- derrubar sessoes do tenant quando aplicavel;
- remover dados tenant-specific;
- limpar backups/snapshots temporarios relacionados ao tenant demo;
- recriar ou migrar o schema limpo;
- recriar dados seed minimos se existirem;
- marcar slot como `livre`.

## Guards obrigatorios

Comandos destrutivos precisam de protecoes fortes:

- reset nunca deve aceitar `rh_teste`;
- reset nunca deve aceitar `public`;
- reset nunca deve aceitar schemas fora de `demo1...demo10`;
- reset deve validar o tenant no banco antes de executar;
- reset deve validar o `Domain` esperado;
- reset deve exigir confirmacao textual, como `--confirm demo3`;
- comandos devem falhar fechados quando houver divergencia;
- comandos devem registrar auditoria sem expor senha, token ou segredo;
- comandos devem ser preferencialmente restritos a operador/plataforma.

## Riscos destrutivos

Principais riscos a tratar antes de qualquer automacao publica:

- apagar ou recriar o schema errado;
- resetar `rh_teste` por engano;
- resetar `public` por engano;
- deixar `Domain` apontando para tenant incorreto;
- permitir acesso cruzado entre `demo1` e `demo2`;
- manter sessoes antigas validas apos reset;
- vazar dados de um testador para outro;
- registrar senha temporaria em log;
- manter backups temporarios com dados de testador expirado;
- permitir crescimento ilimitado de arquivos ou tabelas;
- configurar wildcard DNS/Nginx de forma que o Host chegue errado ao Django;
- abrir cadastro publico antes do reset seguro estar testado.

## Ordem incremental de implementacao

1. Criar documentacao e alinhar decisoes da fase.
2. Criar modelagem de metadata no schema publico.
3. Criar migrations da metadata.
4. Criar guards compartilhados para validar schemas demo.
5. Criar comando idempotente para provisionar `demo1...demo10`.
6. Criar comando para ocupar uma vaga manualmente.
7. Criar comando para expirar/bloquear leases vencidos.
8. Criar comando de reset seguro com confirmacao explicita.
9. Testar isolamento entre `demo1` e `demo2`.
10. Medir tamanho por schema e preparar alerta para 50 MB.
11. Ajustar DNS/Nginx wildcard em ambiente controlado, se necessario.
12. Documentar a fase futura de cadastro publico sem implementa-la agora.

## Testes minimos

- Provisionamento idempotente cria `demo1...demo10` sem duplicar registros.
- Cada tenant demo recebe seu `Domain` tecnico correto.
- `TenantMainMiddleware` resolve `demo1` e `demo2` por `Host` diferente.
- Dados criados em `demo1` nao aparecem em `demo2`.
- Ocupar vaga livre muda status para `ocupado`.
- Lease vencido muda status para `expirado` ou `bloqueado`.
- Reset recusa `rh_teste`.
- Reset recusa `public`.
- Reset recusa schema fora de `demo1...demo10`.
- Reset exige confirmacao explicita.
- Reset de `demo1` nao altera `demo2`.
- Usuario demo expirado nao consegue continuar acessando apos bloqueio.
- Logs nao contem senha, token ou segredo.
- Consulta de tamanho por schema identifica quando o tenant se aproxima de
  50 MB.

## Decisao: nao comecar pela tela publica

A tela publica de cadastro automatico fica fora de escopo por enquanto. Antes
dela, o backend precisa provar que consegue:

- manter um pool seguro;
- registrar e controlar lease;
- executar reset seguro;
- bloquear acesso por expiracao;
- validar isolamento entre tenants;
- manter limites auditaveis;
- criar tenants previsiveis;
- ocupar vaga manualmente;
- bloquear expirados;
- resetar sem atingir schemas errados;
- isolar dados entre tenants;
- controlar sessoes e credenciais;
- medir uso de armazenamento.

Abrir cadastro publico antes desses pontos aumenta o risco de acumular dados,
vazar informacoes entre testadores ou perder o controle operacional do pool.

Como o objetivo inicial e portfolio e demonstracao tecnica, nao ha necessidade
de comecar por uma experiencia publica automatizada. O caminho mais seguro e:

1. manter pool manual `demo1...demo10`;
2. manter lease e reset seguro;
3. manter teste de isolamento;
4. manter limite simples de 50 MB por tenant;
5. avaliar cadastro publico somente depois.

## Proteção contra abuso e bypass de limites

Mesmo sendo uma demo de portfolio e demonstracao tecnica, a limitacao de uso
deve ser rigorosa. A demo publica nao deve ser tratada como ambiente livre para
uso indefinido, carga alta, exportacao ampla ou tentativa repetida de acesso.

Os limites devem combinar IP, usuario autenticado e tenant/schema. Nenhum limite
critico deve depender de apenas um identificador, porque isso facilita bypass
por troca de IP, troca de conta, multiplas sessoes ou alternancia de subdominio.

Controles obrigatorios planejados:

- rate limit por IP;
- rate limit por usuario autenticado;
- rate limit por tenant/schema;
- limite especifico para login;
- limite especifico para criacao e edicao em massa;
- limite especifico para APIs sensiveis;
- limite rigoroso para download, exportacao e backup;
- bloqueio temporario apos excesso de tentativas ou volume;
- auditoria de tentativas repetidas;
- protecao contra troca de IP para burlar limite;
- protecao contra criacao de multiplas sessoes para escapar do limite;
- protecao contra uso de varios usuarios no mesmo tenant para escapar do limite;
- protecao contra alterar `Host` ou subdominio para acessar outro tenant;
- limite de tamanho de payload;
- limite de upload;
- paginacao obrigatoria em listas grandes;
- logs sem senha, token ou segredo.

Download, exportacao e backup devem ter limites mais rigorosos que leitura
comum, porque sao operacoes com maior risco de exfiltracao de dados, uso
abusivo de banda e geracao de arquivos. Essas rotas devem ser auditaveis e
podem ter janelas menores, quotas menores e bloqueio mais rapido.

Comandos e rotinas administrativas nao devem ser expostos publicamente. Eles
devem continuar restritos a operador/plataforma e executados por canal
administrativo seguro.

Qualquer violacao repetida deve bloquear temporariamente o acesso a demo. O
bloqueio deve considerar a combinacao de IP, usuario e tenant/schema, para
reduzir bypass por troca de apenas um desses fatores.

## Fase futura opcional: cadastro publico e limites

Se, no futuro, fizer sentido abrir cadastro publico para demonstracao, a fase
publica pode seguir este fluxo:

1. Usuario acessa `https://demo-rh.taquiondev.com.br`.
2. Usuario informa nome, email e telefone.
3. Sistema procura vaga livre entre `demo1...demo10`.
4. Sistema cria lease de 3 dias.
5. Sistema cria ou ativa usuario no schema do tenant reservado.
6. Frontend passa a usar a API tecnica daquele lease.
7. Sistema aplica limite simples de armazenamento e limite basico de
   requisicoes.
8. Ao expirar, acesso e bloqueado.
9. Operacao automatica ou assistida limpa/recria o schema.
10. Vaga volta para `livre`.

Limites sugeridos para essa fase, ainda com foco de demo e nao de SaaS
comercial:

- ate 10 usuarios/testadores simultaneos;
- 3 dias por lease;
- 50 MB por tenant como protecao operacional;
- limite basico de requisicoes por tenant, usuario e IP;
- bloqueio de novos uploads ou registros volumosos ao atingir limite;
- rotina periodica para expirar leases;
- rotina auditavel para resetar e liberar vagas.

Mesmo nessa fase futura, billing, planos comerciais, assinatura recorrente e
autoescala devem continuar fora do escopo ate existir uma decisao explicita de
transformar o projeto em SaaS comercial.
