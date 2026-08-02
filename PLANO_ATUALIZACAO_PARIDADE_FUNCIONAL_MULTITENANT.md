# Plano de atualização para paridade funcional multi-tenant

## 0. Status, finalidade e regra de uso

- Criado em: 29/07/2026.
- Revisado criticamente em: 29/07/2026.
- Estado: `[EM IMPLEMENTAÇÃO]`.
- Escopo atual: implementação local controlada, testes e registro de evidências.
- Código e migrations locais foram criados; migrations não foram aplicadas aos
  bancos persistentes, e nenhum deploy, dado operacional ou dependência foi alterado.
- Repositórios abrangidos: backend SaaS atual e frontend SaaS atual.

Este documento é o roteiro autocontido para atualizar a aplicação SaaS até que,
dentro de um tenant comum, a experiência, as regras de negócio, os cálculos e os
fluxos operacionais sejam equivalentes à implementação funcional auditada em
28/07/2026.

Um usuário habituado à aplicação de referência deve conseguir entrar em um tenant,
usar as mesmas telas e concluir os mesmos fluxos sem perceber diferença funcional.
As únicas diferenças aceitas são as necessárias à arquitetura SaaS:

- resolução do tenant exclusivamente pelo `Host`;
- isolamento por schema PostgreSQL;
- autenticação, sessão, CSRF, cache e throttling isolados por host/schema;
- comandos e jobs executados com tenant explícito;
- arquivos, exports e backups separados por tenant;
- políticas especiais da demonstração pública;
- controles de segurança adicionais que não removam comportamento de negócio.

Estados permitidos neste plano:

- `[PLANEJADO]`: ainda não iniciado;
- `[EM IMPLEMENTAÇÃO]`: código em desenvolvimento, sem gate completo;
- `[IMPLEMENTADO SEM EVIDÊNCIA]`: código existe, mas os critérios ainda não passaram;
- `[COMPROVADO]`: comportamento e segurança validados;
- `[BLOQUEADO]`: impedimento objetivo registrado.

Uma fase só pode ser marcada `[COMPROVADO]` após registrar evidências no próprio
documento. Código existente, teste isolado ou validação apenas no SQLite não bastam
para afirmar concorrência, locks ou isolamento multi-tenant.

Rótulos de proveniência usados nesta revisão:

- `[CÓDIGO COMPROVADO]`: comportamento localizado na implementação executável e,
  quando disponível, nos testes da aplicação funcional auditada;
- `[INVARIANTE SaaS]`: requisito derivado da implementação multi-tenant atual e que
  prevalece sobre qualquer adaptação de código single-tenant;
- `[HARDENING OBRIGATÓRIO]`: requisito de segurança, operabilidade ou qualidade que
  precisa ser entregue, embora não seja necessário para reproduzir a interface;
- `[NECESSITA CONFIRMAÇÃO ANTES DA IMPLEMENTAÇÃO]`: hipótese encontrada apenas em
  documentação, decisão operacional sem equivalente executável ou escolha nova da
  versão SaaS. Não pode ser convertida silenciosamente em regra de negócio.

Em caso de conflito, a precedência é: isolamento e segurança SaaS, integridade
financeira, comportamento comprovado em código, contrato HTTP comprovado, testes e,
por último, documentação histórica. Um conflito não autoriza remover funcionalidade:
deve ser registrado e resolvido antes da escrita afetada.

## 1. Resultado obrigatório

A atualização estará concluída quando um tenant comum oferecer:

1. cadastro completo de servidores diaristas e mensalistas;
2. múltiplos serviços por servidor;
3. dados sensíveis e salário protegidos por permissões distintas;
4. histórico salarial por vigência;
5. participação de servidores nos serviços dos eventos;
6. rateio exato das diárias entre diaristas;
7. mensalistas identificados e fora do rateio de diárias;
8. custos por servidor e detalhamento por servidor nos custos do evento;
9. planos de custos recorrentes separados de ocorrências físicas;
10. projeção, materialização e recuperação idempotentes;
11. salários mensalistas materializados pelo fluxo financeiro canônico;
12. escala por datas trabalhadas, inclusive dias não consecutivos;
13. indicação visual opcional de “Sócio”, sem criar novo vínculo operacional;
14. mesma responsividade, estados visuais, permissões e comportamento de formulários;
15. backup tenant-scoped em UTF-8 restaurável;
16. OpenAPI, testes, CI e E2E cobrindo os novos contratos;
17. isolamento comprovado entre pelo menos dois tenants com IDs coincidentes.

Não faz parte desta atualização:

- folha de pagamento completa;
- encargos, benefícios, férias, décimo terceiro, rescisão ou descontos;
- rateio proporcional automático de salário;
- apropriação gerencial inventada para mensalistas;
- criação de um segundo ledger, obrigação ou despesa paralela;
- migração automática de recorrências legadas;
- backfill de datas trabalhadas;
- seleção de tenant por query string, header, body, cookie ou token do frontend;
- dados operacionais no schema `public`;
- deploy ou migração em produção sem autorização posterior.

### 1.1 Classificação obrigatória do escopo

#### Paridade Funcional Obrigatória

- cadastro, serviços, vínculo, histórico e apresentação visual dos servidores;
- participações, snapshots, rateio, valor manual, restauração e recálculo;
- escala diária e compatibilidade das participações históricas;
- custos por servidor e detalhamento aditivo por servidor nos custos do evento;
- planos, projeções, materialização e recuperação de custos recorrentes;
- automação salarial explicitamente autorizada e integrada ao fluxo financeiro
  canônico;
- totais financeiros, telas, mensagens, filtros, estados, responsividade e
  comportamento de formulários;
- fechamento do painel de evento apenas depois de sucesso;
- backup UTF-8 restaurável.

#### Segurança Multi-Tenant Obrigatória

- schema, `Host`, sessão, CSRF, CORS, cache, throttle, arquivos, comandos, jobs,
  idempotência e auditoria isolados por tenant;
- nenhum dado operacional novo no `public` e nenhum seletor de tenant aceito do
  cliente;
- permissões aplicadas no backend antes de consulta a objeto sensível;
- política salarial fail-closed em todas as superfícies e agregações;
- Demo Pública sem novas capacidades sensíveis por herança acidental e com proteção
  transitiva de seeds;
- migrations aplicadas e verificadas em todos os schemas, inclusive na criação e no
  reset de tenants.

#### Hardening Obrigatório

- constraints finais, transações, ordem global de locks e testes PostgreSQL com
  conexões independentes;
- idempotência persistente, retry seletivo, auditoria segura e erros sistêmicos sem
  vazamento;
- OpenAPI concreto, sem warnings e sem colisões de `operation_id`, inclusive onde a
  implementação funcional auditada ainda usa `OBJECT` genérico;
- compatibilidade de deploy N/N-1, rollback não destrutivo, observabilidade
  tenant-aware, CI reproduzível e E2E integrado;
- orçamento de queries e proibição de lazy load nos serializers.

#### Evoluções Futuras Não Bloqueantes

Estas evoluções não podem bloquear a paridade descrita acima nem ser implementadas
por inferência durante as fases obrigatórias:

- retenção automática de registros de idempotência com janela inicialmente sugerida
  de 24 horas;
- paginação ou streaming de projeções;
- apropriação gerencial não nula de mensalistas;
- folha de pagamento, encargos, benefícios, férias, décimo terceiro, rescisões e
  descontos;
- proporcionalidade automática para salário ou contrato parcial;
- novos perfis de permissão além dos já existentes;
- conversão automática de recorrências legadas ou backfill de datas trabalhadas.

### 1.2 Pontos que necessitam confirmação antes da implementação

| Ponto | Evidência atual | Tratamento obrigatório |
|---|---|---|
| Exposição dos módulos novos na Demo Pública | escolha exclusiva do SaaS; não existe equivalente multi-tenant na implementação funcional auditada | manter oculto e sem permissões novas; confirmar seed, quota e matriz antes de qualquer liberação |
| Apropriação gerencial não nula de mensalista | citada como possibilidade documental, mas não implementada | manter “não calculada” e não inventar fórmula |
| Folha ou proporcionalidade salarial | descrita apenas como evolução fora do escopo; não implementada | não criar; exigir decisão de negócio e novo plano |
| Retenção de idempotência em 24 horas | recomendação documental adiada, sem expurgo implementado | manter como evolução futura; não confundir com a retenção obrigatória da auditoria |
| Paginação/streaming e gatilho aproximado de 10 mil projeções | recomendação documental adiada, não contrato executável | medir; abrir evolução somente se o gatilho operacional for confirmado |
| Fan-out do agendador entre tenants e política continuar/abortar | necessidade nova da arquitetura SaaS, sem implementação equivalente auditada | o command tenant-only é obrigatório; confirmar orquestrador, fonte de tenants, exclusão mútua e política antes de ativar o agendamento |
| Consistência do backup durante escritas concorrentes | o ciclo UTF-8 é comprovado, mas não há garantia executável de snapshot consistente sob mutação simultânea | definir janela de quiescência ou estratégia transacional antes do rollout |
| Perfis adicionais e permissões da Demo | não há regra funcional comprovada além da matriz mínima descrita | preservar perfis atuais e decidir explicitamente qualquer concessão adicional |

Os pontos acima não tornam opcionais as salvaguardas. Enquanto não houver
confirmação, vale o comportamento mais restritivo indicado na última coluna.

## 2. Lacunas verificadas no estado atual

| Área | Estado atual auditado | Resultado necessário |
|---|---|---|
| Servidores | módulo inexistente | cadastro, serviços, salário, permissões e auditoria |
| Participações | módulo inexistente | servidor por evento/serviço e rateio explicativo |
| Custos por servidor | tela/API inexistentes | relatório completo com filtros e sigilo |
| Custos recorrentes | recorrência física legada | plano, projeção e ocorrência materializada |
| Automação salarial | inexistente | contrato, corte explícito, histórico e materialização |
| Idempotência recorrente | inexistente | chave UUID, hash de payload, replay e conflito |
| Auditoria recorrente | inexistente | eventos agregados, correlation ID e expurgo seguro |
| Escala diária | somente totais agregados | datas distintas e horas opcionais por data |
| Sócio | inexistente | opção apenas visual, preservando diarista/mensalista |
| Custos do evento | sem distribuição por servidor | detalhe aditivo sem alterar totais |
| Responsividade | anterior à revisão mais recente | grids e seletores equivalentes ao comportamento esperado |
| Edição de evento | painel permanece aberto | fechar somente depois de salvamento confirmado |
| Backup | temporário binário | fixture UTF-8 explícita e restaurável |
| CI | sem workflow versionado | PostgreSQL, OpenAPI, frontend, guardrails e E2E |

### 2.1 Conflitos e ambiguidades resolvidos por este plano

| Conflito ou ambiguidade | Resolução vinculante |
|---|---|
| “Mesmas permissões” versus restrições da Demo Pública | paridade integral vale para tenant comum; Demo é um perfil excepcional, fail-closed e sem acesso salarial |
| Participação implementada antes da escala diária | modelar participação e datas trabalhadas no estado final e fechar seus contratos backend na mesma etapa; só então criar a UI |
| Migration de escala posterior à API de participação | incluir o model diário na primeira entrega estrutural; migrations podem ser revisáveis, mas o endpoint não nasce com contrato transitório |
| OpenAPI genérico na implementação auditada versus schema concreto exigido aqui | tratar schemas concretos como hardening obrigatório sem alterar o JSON funcional |
| “Mutações recorrentes” sem escopo exato | exigir `Idempotency-Key` somente nas quatro operações listadas na seção 5.3; demais mutações mantêm contrato atual |
| Erros “consistentes” versus envelopes históricos diferentes | não unificar envelopes por conveniência; documentar e testar `detail`, `errors` e `data` por endpoint/status |
| Próxima migration fixada em número | determinar a folha real no início da implementação e depender dela; nenhum número é reservado por este plano |
| Rollback de frontend “primeiro” em qualquer cenário | a ordem depende da matriz de compatibilidade N/N-1; somente versões comprovadamente aditivas podem ser alternadas sem janela de bloqueio |

## 3. Invariantes da arquitetura SaaS que não podem regredir

### 3.1 Isolamento de dados

- `caixa` permanece em `TENANT_APPS`.
- Todos os novos models operacionais ficam no schema do tenant ativo.
- O schema `public` não pode ganhar tabela `caixa_*`.
- Não adicionar `tenant_id` aos models operacionais apenas para compensar consultas
  incorretas; o isolamento principal continua sendo o schema ativo.
- Querysets não recebem tenant informado pelo cliente.
- IDs podem coincidir entre tenants.
- Documento de servidor pode se repetir entre tenants, mas permanece único dentro de
  cada tenant.
- FK, constraint, idempotência e auditoria são resolvidas apenas no schema ativo.

### 3.2 Resolução, autenticação e frontend

- O tenant continua sendo resolvido pelo `Host`.
- Sessão e CSRF permanecem host-only.
- CORS continua com allowlist exata e credenciais; não usar wildcard.
- O frontend continua obtendo a API pelo runtime atual, inclusive leases da demo.
- Nenhuma service nova aceita ou envia `tenant`, `schema` ou equivalente.
- Hooks novos devem usar a infraestrutura financeira atual, cuja chave inclui o
  runtime da API, para impedir resposta/cache de outro tenant.
- Troca de runtime deve cancelar requisições antigas e invalidar estado financeiro.

### 3.3 Segurança e demonstração pública

- Throttling e cache continuam incluindo o schema.
- A quota de armazenamento da demo continua bloqueando mutações quando aplicável.
- Dados de seed permanecem imutáveis para o usuário público.
- A demo pública não recebe automaticamente permissões salariais, de auditoria ou
  administração dos novos módulos.
- Qualquer liberação dos módulos na demo exige decisão explícita, seed compatível,
  matriz exata de permissões e testes de proteção dos objetos relacionados ao evento.
- A proteção de seed deve percorrer as novas relações:
  participação -> evento, data trabalhada -> participação -> evento e custo
  distribuído -> participação/evento. Não basta bloquear apenas o endpoint direto do
  evento.
- Toda mutação nova exposta à demo deve permanecer dentro da transação observada pela
  quota; falha de quota precisa desfazer participação, escala, rateio e histórico
  como uma unidade.
- Reset/recriação da demo deve aplicar as migrations novas, sincronizar permissões e
  produzir novamente um schema sem dados salariais reais.
- Nenhuma proteção SaaS existente deve ser substituída por código da implementação de
  referência.

### 3.4 Arquivos e comandos

- Backups e artefatos continuam em diretório tenant-scoped.
- Commands operacionais recusam `public`.
- Jobs recebem o schema explicitamente e nunca inferem tenant pelo primeiro registro.
- Logs operacionais devem incluir `schema_name`, sem salário, documento, token, payload
  sensível ou mensagem bruta de exceção.
- OpenAPI, URLs e payloads não publicam `schema_name`; o schema é contexto interno de
  execução, observabilidade e diagnóstico.
- Qualquer command novo deve entrar no registro fail-closed de commands tenant-only e
  possuir teste explícito no `public` e em dois tenants.

## 4. Regras funcionais que são fonte de verdade

### 4.1 Cadastro de servidores

Criar `Servidor` com:

- nome;
- tipo de documento: `CPF`, `CNPJ`, `RG` ou `OUTRO`;
- documento normalizado, case-insensitive e único dentro do tenant;
- telefone, e-mail, nascimento, endereço e observações;
- ativo/inativo;
- vínculo operacional `DIARISTA` ou `MENSALISTA`;
- `exibir_como_socio`, exclusivamente visual;
- salário mensal opcional e permitido somente para mensalista;
- início e fim de contrato;
- dia de pagamento salarial entre 1 e 31;
- data explícita de autorização da automação salarial;
- autoria, timestamps e histórico.

Regras:

- diarista não possui salário mensal nem campos contratuais salariais;
- mensalista exige salário maior que zero;
- data final não pode anteceder a inicial;
- nascimento não pode estar no futuro;
- alterar `exibir_como_socio` não muda vínculo, salário, participação ou custo;
- editar outros campos sem permissão salarial preserva os dados salariais atuais no
  backend;
- busca sem permissão sensível consulta apenas nome, impedindo inferência por
  documento, telefone ou e-mail;
- sem permissão sensível, documento é mascarado e os demais dados pessoais são
  omitidos;
- sem permissão salarial, salário e dados contratuais salariais são omitidos.

Criar `ServidorServico` como relação M:N explícita:

- uma linha por servidor/serviço;
- serviço protegido contra exclusão;
- vínculo ativo/inativo;
- serviço inativo não pode ser adicionado em novo vínculo;
- autoria, timestamps e histórico.

Criar `HistoricoSalarialServidor`:

- snapshot do nome e ID do servidor;
- valor positivo;
- data inicial e data final opcional;
- vigências não sobrepostas;
- autoria, timestamps e histórico;
- histórico preservado quando o servidor for excluído.

### 4.2 Participação e rateio de diaristas

Criar `ParticipacaoServidorEvento` para servidor + evento + serviço.

Regras obrigatórias:

- unicidade por servidor, evento e serviço enquanto o servidor existir;
- servidor e serviço precisam estar ativos e vinculados para nova participação;
- evento precisa possuir `EventoCustoServico` para o serviço;
- eventos `concluido` e `cancelado` são somente leitura;
- exclusão de servidor usa `SET_NULL` na participação e preserva snapshots;
- serviço usa `PROTECT`;
- documento completo não entra no snapshot; guardar somente identificador parcial;
- alimentação e transporte não participam do rateio;
- o total distribuível é exclusivamente `EventoCustoServico.valor_diarias`;
- a participação explica a distribuição e não cria novo custo, despesa, obrigação,
  lançamento ou pagamento.

Rateio:

- somente diaristas entram no rateio;
- mensalista sempre tem `valor_calculado = 0` e `valor_final = 0`;
- o peso usa horas positivas; sem horas, usa
  `dias × horas_base_diaria_snapshot`;
- distribuição em centavos usa maior resto e desempate estável pelo ID;
- a soma final precisa coincidir exatamente com o total distribuível;
- valor manual exige permissão e motivo;
- valores manuais são preservados e o saldo é redistribuído entre automáticos;
- soma manual acima do total é rejeitada com rollback;
- restaurar cálculo remove a trava manual e recalcula;
- recálculo explícito é permitido somente em evento editável;
- alterações cadastrais posteriores não modificam snapshots históricos.
- toda escrita e todo recálculo usam o mesmo serviço de domínio; serializers, views,
  commands e Admin não podem duplicar fórmula, validação ou redistribuição;
- qualquer mudança em escala, horas, servidor, serviço ou valor manual que afete o
  rateio deve chamar esse serviço dentro da mesma transação.

Ordem única de locks:

`Evento -> Servidor -> ParticipacaoServidorEvento -> EventoCustoServico`

Quando houver várias linhas, bloquear por chave crescente. Relações anuláveis devem
ser carregadas separadamente ou com `select_for_update(of=("self",))`, sem `FOR
UPDATE` sobre o lado anulável de `LEFT OUTER JOIN`.

Operações que envolvam evento, participação, escala e rateio devem obedecer a essa
mesma ordem, inclusive exclusão de servidor concorrente com criação de participação,
troca de serviço concorrente com recálculo e redução do período do evento concorrente
com substituição de datas. Se uma operação não precisar de todas as entidades, ela
mantém a ordem relativa das que usar.

### 4.3 Custos por servidor

Criar relatório com:

- grupos por servidor ou snapshot de servidor excluído;
- serviços;
- participações por evento;
- custo real das participações de diaristas;
- salário por competência, quando autorizado;
- totais por servidor e período;
- indicação de mensalista, inativo e excluído;
- apropriação gerencial explicitamente “não calculada”, com valor nulo/zero conforme
  o contrato e permissão.

Filtros:

- período;
- servidor;
- existente/excluído;
- ativo/inativo;
- diarista/mensalista;
- serviço;
- evento;
- valor manual/automático.

Sem permissão salarial:

- remover linhas salariais antes de totalizar;
- não revelar quantidade, descrição, existência ou diferença de total;
- recalcular os totais visíveis apenas com participações permitidas.

Sem permissão de apropriação:

- omitir a apropriação de cada item;
- omitir o total de apropriação.

### 4.4 Planos de custos recorrentes e salários

Criar `PlanoCustoRecorrente` separado de `CustoFixo`.

O plano contém:

- descrição e categoria;
- origem `comum` ou `salario`;
- periodicidade mensal;
- valor previsto apenas para origem comum;
- início, fim opcional e dia de vencimento;
- data explícita de autorização da materialização;
- ativo/inativo;
- servidor protegido para plano salarial;
- referência opcional a custo legado ou plano renovado;
- autoria, timestamps e histórico.

Regras:

- novo custo recorrente cria um plano, não todos os custos físicos futuros;
- novo custo avulso continua criando `CustoFixo`;
- competência futura é projeção de leitura, não obrigação;
- competência elegível gera um `CustoFixo` físico;
- a ocorrência física reutiliza obrigação, liquidação e FCO canônicos;
- não criar `DespesaOperacional` ou obrigação paralela;
- `(plano, competência)` é único;
- edição do plano afeta apenas projeções futuras não materializadas;
- ocorrências materializadas preservam snapshots;
- dia inexistente no mês usa o último dia;
- plano sem fim respeita horizonte máximo configurável, inicialmente 24 meses;
- não gerar retroativo anterior à criação/corte autorizado;
- recuperação percorre todas as competências ausentes até o limite;
- repetição não duplica custo nem obrigação;
- renovação não pode sobrepor plano nem série física legada;
- erros inesperados retornam 5xx seguro com correlation ID;
- conflito concorrente esgotado retorna 409;
- bloqueios de domínio podem ser resultados por item, sem expor erro interno.

Salários:

- `HistoricoSalarialServidor` é a fonte temporal do valor;
- contrato limita competências;
- mês parcial por contratação, encerramento ou reajuste é bloqueado;
- não inventar proporcionalidade;
- ocorrência salarial física prevalece sobre representação virtual;
- servidor existente só entra na automação após corte e confirmação explícitos;
- nenhuma data de contrato, pagamento ou autorização pode ser inferida silenciosamente;
- mensalista no evento continua fora do rateio, mesmo com salário materializado.

Totais de custos fixos:

- `realizedAmount`: valor efetivamente pago;
- `materializedPlannedAmount`: previsto das ocorrências físicas;
- `pendingPaymentAmount`: saldo físico ainda pendente;
- `projectedAmount`: projeções futuras válidas;
- `forecastAmount = pendingPaymentAmount + projectedAmount`;
- valores realizados não entram novamente na previsão;
- manter aliases existentes apenas quando o contrato atual ainda os exigir.

### 4.5 Idempotência, concorrência e auditoria recorrente

Criar idempotência persistente com:

- escopo;
- UUID enviado em `Idempotency-Key`;
- hash canônico do payload;
- ator;
- status HTTP;
- resposta segura;
- unicidade por escopo + chave;
- replay para mesma chave, mesmo ator e mesmo payload;
- erro 400 para reutilização incompatível;
- header `Idempotency-Replayed`.

Aplicar em:

- criação de plano;
- atualização de plano;
- materialização;
- criação de custo recorrente pelo endpoint de custos fixos.

Não aplicar implicitamente a DELETE, pagamento, baixa ou atualização de custo fixo
avulso. Ampliar esse escopo exige novo contrato HTTP e teste de compatibilidade.

Concorrência:

- ocorrência protegida por constraint, transação e tratamento de `IntegrityError`;
- retry somente para deadlock/serialization failure;
- quatro tentativas totais;
- backoff de 50/150/450 ms com jitter limitado;
- operação inteira precisa ser idempotente antes de receber retry.

Criar auditoria operacional tenant-scoped:

- tipo, origem, plano, competência, status e código de motivo;
- correlation ID;
- chave de agregação;
- primeira/última ocorrência e contador;
- eventos equivalentes agregados em janela de uma hora;
- sem valor, salário, nome, documento, payload, exceção ou traceback;
- Admin somente leitura e permissão investigativa própria;
- retenção inicial de 400 dias para eventos de auditoria.

Itens deliberadamente futuros:

- retenção de registros de idempotência: implementar quando houver retry HTTP,
  integração com reentrega, fila offline, volume relevante ou garantia formal de
  “exactly once”; janela inicial sugerida de 24 horas;
- paginação/streaming de projeções: antecipar quando houver centenas altas de planos,
  mais de aproximadamente 10 mil itens, p95 fora do SLO, pressão de memória ou
  horizonte acima de 24 meses.

### 4.6 Escala por datas trabalhadas

Criar `ServidorEventoDiaTrabalhado`:

- FK `CASCADE` para participação;
- data civil;
- horas decimais opcionais;
- timestamps;
- unicidade por participação/data;
- check de horas nulas ou maiores que zero.

Regras:

- todo novo POST de participação exige `workedDays` não vazio;
- datas precisam estar no intervalo inclusivo do evento;
- payload não aceita data duplicada;
- pessoas distintas podem trabalhar no mesmo dia;
- uma pessoa pode ter escalas distintas por serviço;
- horas por dia são opcionais e, quando informadas, precisam ser positivas;
- não inventar teto diário;
- `quantidade_dias` é a quantidade de datas distintas;
- `quantidade_horas` é a soma das horas não nulas;
- backend deriva e persiste os totais;
- substituição da escala é atômica;
- a substituição bloqueia a participação antes de apagar/inserir datas e recalcula
  uma única vez, no commit lógico da operação;
- não permitir remover todas as datas depois da conversão para escala;
- evento não pode ter o período reduzido se excluir data persistida;
- participações antigas permanecem sem datas inventadas;
- editar participação histórica sem `workedDays` preserva totais;
- primeiro envio explícito de `workedDays` converte o registro para escala diária;
- mensalistas usam a mesma escala operacional, mas continuam financeiramente em zero;
- nenhuma fórmula de rateio é alterada.

Em concorrência, “última requisição confirmada vence” somente é aceitável para a
lista integral de `workedDays`; misturas parciais de duas requisições são proibidas.
Se o período do evento mudar em paralelo, ou a combinação inteira é válida e
confirmada, ou uma das operações falha sem persistência parcial.

Contrato aditivo:

```json
{
  "workedDays": [
    {"date": "2026-08-10", "hours": "8.00"},
    {"date": "2026-08-12", "hours": null}
  ],
  "days": 2,
  "hours": "8.00",
  "workDatesProvided": true
}
```

Registros legados retornam `workedDays: []` e `workDatesProvided: false`.

### 4.7 Ajustes de interface que também fazem parte da paridade

- Rotas novas `/servidores` e `/custos-por-servidor`.
- Sidebar condicionada às permissões publicadas na sessão.
- Cadastro com métricas, busca, filtros, múltiplos serviços, salário condicionado,
  confirmação de exclusão e estados loading/erro/vazio/forbidden.
- Checkbox “Exibir como Sócio”; muda apenas o texto da coluna Vínculo.
- Participações dentro do detalhe do evento.
- Seletor de todas as datas inclusivas do evento, dias não consecutivos, horas por
  dia, rolagem em eventos longos e navegação por teclado.
- Detalhes expansíveis da escala em evento, custos por servidor e custos por evento.
- Texto histórico: “Datas não informadas — registro anterior à escala diária.”
- Mensalista exibido como “Custo fixo (fora do rateio)” e sem colunas de valor
  calculado/final de diária.
- Painel de edição de evento fecha após sucesso da API, atualiza a linha antes do
  fechamento e permanece aberto com os dados quando houver erro.
- Planos recorrentes com lista, criação, edição, materialização do mês e recuperação
  de competências ausentes.
- Projeções são somente leitura e não oferecem editar/pagar.
- Dashboard sinaliza período recorrente incompleto e totais potencialmente
  subestimados.
- Aplicar a revisão responsiva aos cards, filtros e seletores das telas financeiras,
  incluindo dashboard, backups, orçamentos, clientes, eventos, custos fixos, custos
  por evento, custos por servidor, servidores, serviços, credores, pagamentos,
  financiamentos, investimentos, configurações e obrigações.
- Reutilizar grids responsivos compartilhados e manter teste contra overflow em
  viewports mobile.

### 4.8 Backup UTF-8

No serviço atual de backup:

- preservar o diretório tenant-scoped;
- criar o arquivo temporário em modo texto com `encoding="utf-8"`;
- passar o handle como `stdout` de `dumpdata`;
- calcular hash sobre os bytes UTF-8;
- gravar metadados com `ensure_ascii=False`;
- limpar temporário no `finally`;
- preservar schema/scope nos metadados e no retorno;
- provar que não há BOM e que caracteres como `ç`, `á`, `é` e `ã` sobrevivem ao
  ciclo dump/restore;
- provar que backup e restore de um tenant não leem nem alteram outro tenant.

## 5. Contratos HTTP

Todos os caminhos abaixo permanecem sob `/api` no backend. No frontend, services
continuam usando os caminhos relativos esperados pela configuração atual da API.

| Método | Endpoint | Entrada principal | Sucesso | Idempotência |
|---|---|---|---|---|
| GET | `/api/servidores/` | `search`, `active`, `linkType`, `serviceId` | 200, `{data:{servers,summary,filters,filterOptions,permissions,meta}}` | não |
| POST | `/api/servidores/` | `ServidorPayload` | 201, `{data:{server,message}}` | não |
| GET | `/api/servidores/<id>/` | path ID | 200, `{data:{server,permissions,filterOptions,meta}}` | não |
| PUT | `/api/servidores/<id>/` | `ServidorPayload` completo | 200, `{data:{server,message}}` | não |
| DELETE | `/api/servidores/<id>/` | path ID | 204, corpo vazio | não |
| GET | `/api/eventos/<id>/servidores/` | path ID | 200, `{data:{event,participations,serverOptions,permissions,meta}}` | não |
| POST | `/api/eventos/<id>/servidores/` | `ParticipacaoCreatePayload` | 201, `{data:{participation}}` | não |
| GET | `/api/participacoes-servidores/<id>/` | path ID | 200, `{data:{participation,permissions}}` | não |
| PUT | `/api/participacoes-servidores/<id>/` | `ParticipacaoUpdatePayload` | 200, `{data:{participation}}` | não |
| DELETE | `/api/participacoes-servidores/<id>/` | path ID | 204, corpo vazio | não |
| POST | `/api/participacoes-servidores/<id>/restaurar-calculo/` | sem corpo | 200, `{data:{participation}}` | não |
| POST | `/api/eventos/<id>/servidores/recalcular/` | sem corpo | 200, `{data:{recalculatedGroups}}` | não |
| GET | `/api/custos-por-servidor/` | filtros da seção 5.1 | 200, `{data:{servers,summary,filters,filterOptions,permissions,meta}}` | não |
| GET | `/api/custos-por-evento/` | contrato atual + campos aditivos | 200, envelope atual preservado | não |
| GET | `/api/planos-custos-recorrentes/` | `active` opcional | 200, `{data:{recurringPlans,total,permissions,meta}}` | não |
| POST | `/api/planos-custos-recorrentes/` | `RecurringPlanCreate` | 201, `{data:{recurringPlan,materialization?,message}}` | obrigatória |
| GET | `/api/planos-custos-recorrentes/<id>/` | path ID | 200, `{data:{recurringPlan}}` | não |
| PUT | `/api/planos-custos-recorrentes/<id>/` | `RecurringPlanUpdate` | 200, `{data:{recurringPlan,message}}` | obrigatória |
| GET | `/api/projecoes-custos-recorrentes/` | `startDate`, `endDate` obrigatórios | 200, `{data:{items,summary,period}}` | não |
| POST | `/api/materializacoes-custos-recorrentes/` | modo único ou recuperação | 200/409/500, `{data:{status,correlationId,summary,failure?}}` | obrigatória |
| GET, POST | `/api/custos-fixos/` | contrato atual aditivo | contrato atual preservado | obrigatória apenas ao criar recorrente |

Requisitos transversais:

- autenticação de sessão e CSRF atuais;
- `application/json` em POST/PUT com corpo; DELETE e ações explicitamente sem corpo
  preservam o contrato comprovado;
- IDs são inteiros positivos e datas civis usam `AAAA-MM-DD`; valores monetários e
  horas saem como strings decimais com duas casas, nunca `float`;
- 401 usa `detail` de autenticação, 403 usa `detail` de permissão, validação de domínio
  usa `errors`, e respostas em lote de materialização usam `data`; preservar esses
  envelopes comprovados em vez de normalizá-los sem migração de contrato;
- 400, 401, 403, 404, 405, 409, 415 e 500 devem estar documentados somente onde
  aplicáveis e cobertos por teste de contrato;
- permissão verificada antes da busca do objeto sensível para evitar IDOR;
- 404 não revela objeto de outro tenant;
- objetos relacionados inexistentes ou não permitidos no tenant ativo não podem ser
  distinguidos de objetos inexistentes por meio do status, corpo ou opções de filtro;
- CORS deve permitir `Idempotency-Key` e expor `Idempotency-Replayed`;
- OpenAPI com request/response concretos, códigos e `operation_id` único;
- schemas genéricos `OBJECT` para participação e custos por servidor são dívida da
  implementação auditada e devem ser substituídos por serializers de contrato sem
  mudar o JSON;
- nenhum contrato recebe tenant/schema.

### 5.1 Payloads e filtros canônicos

`ServidorPayload` usa os nomes:

`name`, `documentType`, `document`, `phone`, `email`, `birthDate`, `address`,
`notes`, `active`, `linkType`, `displayAsPartner`, `monthlySalary`,
`salaryEffectiveDate`, `contractStartDate`, `contractEndDate`,
`salaryPaymentDay`, `salaryAutomationFromDate`,
`confirmSalaryAutomationActivation` e `serviceIds`.

- POST exige os campos funcionais obrigatórios definidos pelo serializer; PUT mantém
  o contrato completo comprovado, não deve ser tratado como PATCH;
- `serviceIds` é lista não vazia de inteiros positivos e é deduplicada preservando a
  primeira ordem;
- campos salariais enviados sem a permissão específica são ignorados/preservados no
  backend, nunca zerados pelo frontend;
- a resposta `server` mantém todos os campos canônicos, mas aplica máscara/omissão
  antes da serialização conforme as permissões.

`ParticipacaoCreatePayload`:

```json
{
  "serverId": 1,
  "serviceId": 2,
  "workedDays": [{"date": "2026-08-10", "hours": "8.00"}],
  "days": 1,
  "hours": "8.00"
}
```

- `workedDays` é obrigatório e não vazio no POST novo;
- `days` e `hours` de entrada são aceitos para compatibilidade, mas o backend deriva
  e devolve os totais da lista.

`ParticipacaoUpdatePayload` exige `serviceId` e segue dois modos:

- registro convertido: `workedDays` não vazio substitui integralmente a escala;
- registro histórico: ausência de `workedDays` exige `days` e `hours`, preservando o
  modo legado;
- `finalAmount` exige `editReason` não vazio e a permissão específica.

A resposta `participation` preserva, no mínimo, identidade e snapshots de servidor,
serviço e evento; vínculo; `days`, `hours`, `workedDays`, `workDatesProvided`;
valores calculado/final/manual; referências salarial e de apropriação redigidas;
regra/total/quantidade do rateio; custo real; `readOnly`; timestamps.

Filtros de `/api/custos-por-servidor/`:

- `startDate` e `endDate` com defaults atuais, intervalo inclusivo e erro 400 quando
  inválido;
- `serverId`, `existence`, `active`, `linkType`, `serviceId`, `eventId` e
  `manuallyEdited`;
- a resposta repete filtros efetivos e opções obtidas somente do tenant ativo.

`RecurringPlanCreate` usa `description`, `category`, `origin="comum"`,
`plannedAmount`, `startDate`, `endDate`, `dueDay`,
`authorizedMaterializationDate`, `isActive`, `notes`, `legacyFixedCostId` e
`renewedPlanId`. Criação salarial ocorre pelo fluxo do servidor, não por forçar
`origin="salario"` nesse endpoint. `RecurringPlanUpdate` é parcial conforme o
serializer comprovado e não permite editar plano salarial por essa rota.

Materialização aceita exatamente um modo:

```json
{"competence": "2026-08-01", "dryRun": false}
```

ou:

```json
{
  "recoverMissing": true,
  "throughCompetence": "2026-08-01",
  "dryRun": false
}
```

`competence` com `recoverMissing=true`, ausência de `throughCompetence` na
recuperação ou ausência de `competence` no modo único retorna 400 sem escrita.

### 5.2 Matriz de erros, conteúdo e compatibilidade

| Situação | Status/envelope obrigatório |
|---|---|
| JSON/domínio inválido, chave ausente/malformada/reutilizada com payload ou ator incompatível | 400 com `errors`; nenhuma escrita parcial |
| sessão ausente | 401 com `detail` |
| permissão ausente | 403 com `detail`, antes de buscar objeto sensível |
| recurso não encontrado no schema ativo | 404 sem pista sobre outro tenant |
| método não permitido | 405 |
| mutação com media type diferente de JSON | 415 onde o endpoint exige JSON |
| materialização concluída, inclusive com bloqueios de domínio por item | 200 com `data.status` e resumo consistente |
| conflito transacional esgotado na materialização | 409 com `data.status="conflict"` e correlation ID |
| falha sistêmica | 500 com código seguro/correlation ID, sem mensagem bruta, salário ou payload |

Qualquer campo aditivo em custos fixos, dashboard e custos por evento deve ser
tolerado pelo frontend N-1. Nenhum campo antigo pode mudar de tipo, significado,
opcionalidade ou nulabilidade sem uma fase de transição explicitamente registrada.

### 5.3 Idempotência HTTP

`Idempotency-Key`:

- é UUID válido e obrigatório na criação/atualização de plano, materialização e
  criação de custo fixo quando `isRecurring=true`;
- é escopado por operação e schema; a mesma UUID pode existir em tenants diferentes;
- mesma chave + escopo + ator + hash canônico reproduz corpo e status sem novo efeito;
- reutilização incompatível retorna 400;
- toda resposta de operação idempotente, original ou replay, retorna
  `Idempotency-Replayed: false|true`;
- clientes geram uma chave por intenção do usuário e a preservam nos retries; nova
  intenção gera nova chave.

### 5.4 Campos de sessão que o frontend precisa receber

Adicionar, sem remover os atuais:

- `canViewServers`;
- `canViewServerParticipations`;
- `canAddServer`;
- `canChangeServer`;
- `canDeleteServer`;
- `canViewServerSalary`;
- `canChangeServerSalary`;
- `canViewServerSensitiveData`;
- `canViewServerCosts`;
- `canManageServerParticipation`;
- `canChangeServerDistributedValue`;
- `canRecalculateServerCosts`;
- `canViewServerAppropriation`.

As capacidades de plano recorrente também precisam estar disponíveis no payload da
própria listagem de planos: criar, alterar e materializar.

## 6. Permissões

Criar/preservar os codenames:

- `view/add/change/delete_servidor`;
- `view_salario_servidor`;
- `change_salario_servidor`;
- `view_dados_sensiveis_servidor`;
- `view_participacaoservidorevento`;
- `view_custos_servidor`;
- `manage_participacao_servidor`;
- `change_valor_distribuido_servidor`;
- `recalculate_custos_servidor`;
- `view_apropriacao_servidor`;
- `view/add/change_planocustorecorrente`;
- `materialize_planocustorecorrente`;
- `view_auditoria_custos_recorrentes`.

As formas abreviadas com barras representam codenames Django distintos; migrations,
sincronização e testes devem usar cada codename completo. Permissões de salário,
dados sensíveis, valor distribuído, recálculo e auditoria nunca podem ser deduzidas
apenas da permissão CRUD do model.

Matriz mínima:

| Perfil | Servidores | Participações | Salário/sensíveis | Planos recorrentes | Auditoria |
|---|---|---|---|---|---|
| Administrador | integral | integral | integral | integral | conforme superusuário/permissão |
| Financeiro | ver/criar/alterar | ver/gerir/valor/recalcular | ver/alterar | ver/criar/alterar/materializar | somente se concedida explicitamente |
| Operacional | ver/criar/alterar | ver/gerir/recalcular | não | não por padrão | não |
| Demo Pública | decisão explícita futura | decisão explícita futura | nunca por padrão | nunca por padrão | não |

`sincronizar_grupos_permissoes()` deve continuar fail-closed quando um codename
declarado não existir. A sincronização é executada dentro de cada tenant.

Regras adicionais:

- exclusão de servidor fica restrita ao Administrador na matriz mínima;
- Financeiro e Operacional recebem somente os codenames comprovados na matriz; não
  conceder por wildcard ou por nome aproximado;
- o backend é a autoridade. Capacidades publicadas à sessão ou à listagem de planos
  apenas dirigem a UI e não substituem `has_perm`;
- mudanças de perfil durante sessão ativa devem valer na requisição seguinte e não
  permanecer autorizadas por cache de capacidade;
- a criação das permissões e a sincronização de grupos são verificadas em cada
  schema, inclusive tenant novo, tenant migrado e reset da Demo;
- qualquer futuro módulo que consuma salário reutiliza a política central antes de
  filtrar, agregar, contar, exportar, registrar ou serializar.

## 7. Modelos, migrations e compatibilidade

### 7.1 Regra de numeração

Não copiar migrations antigas pela numeração. O backend SaaS já possui migrations
`0037` a `0042` com finalidade diferente. A cadeia nova deve ser gerada sobre o
estado atual.

No estado auditado, a primeira migration disponível é posterior à `0042`; se novas
migrations entrarem antes da implementação, usar a próxima numeração real.

### 7.2 Sequência lógica sugerida

1. **M1 — servidores no estado final**
   - `Servidor`, `ServidorServico` e `HistoricoSalarialServidor`;
   - incluir contrato salarial, autorização, horas não negativas,
     `exibir_como_socio`, constraints, índices, permissões e históricos desde o
     início;
   - nenhuma API de participação é publicada nesta etapa.
2. **M2 — planos, ocorrências, idempotência e auditoria**
   - `PlanoCustoRecorrente`;
   - campos aditivos em `CustoFixo`;
   - `RequisicaoIdempotenteRecorrencia`;
   - `AuditoriaCustoRecorrente` e estado de agregação;
   - constraints finais de servidor salarial obrigatório, `PROTECT`, renovação e
      plano/competência.
3. **M3 — participação e escala diária no estado final**
   - `ParticipacaoServidorEvento` e `ServidorEventoDiaTrabalhado`;
   - constraints, índices, permissões e históricos;
   - FK, `SET_NULL`/`PROTECT`, snapshots, unicidades, horas positivas e índices de
     leitura;
   - o contrato de participação já nasce com `workedDays`; não liberar uma versão
     intermediária baseada somente em agregados.

A implementação pode separar essas migrations para facilitar revisão, mas não deve
reproduzir etapas intermediárias já superadas. Se M3 for fisicamente dividida, suas
partes formam uma única unidade de deploy e rollback: a API/frontend de participação
só pode ser liberada depois de ambas. O schema novo deve nascer diretamente com as
invariantes finais.

Cada migration deve:

- depender da folha real encontrada na Fase 0, com nomes de constraint/índice
  exclusivos e compatíveis com o limite de identificadores do PostgreSQL;
- ser validada para instalação do zero, upgrade, reversão estrutural sem dados e
  reexecução segura do processo de deploy;
- não consultar `public` para preencher dado operacional nem copiar linhas entre
  schemas;
- separar operação de schema de backfill; este plano não autoriza backfill funcional;
- prever o custo de lock e o tempo por tenant, sem migrar vários schemas em paralelo
  antes de prova controlada;
- garantir que migrations históricas não importem código mutável da aplicação;
- ter estado compatível com `makemigrations --check --dry-run` após toda a cadeia.

### 7.3 Dados existentes

- Não alterar custos físicos antigos.
- Não transformar recorrências antigas em planos.
- Não criar datas trabalhadas por inferência.
- Não recalcular evento concluído/cancelado.
- Não ativar automação salarial sem confirmação.
- Não fazer importação cruzada entre tenants.
- Models novos e seus históricos existem apenas nos schemas de tenant.
- Mesmo banco PostgreSQL deve permitir constraints e índices homônimos em schemas
  diferentes.

### 7.4 Aplicação multi-tenant

- Validar `migrate_schemas --plan`.
- Aplicar primeiro o schema compartilhado, sem tabela operacional nova no `public`.
- Aplicar a cadeia em cada schema de tenant.
- Criar um tenant novo após as migrations e provar que ele nasce no mesmo estado.
- Executar preflight em tenant representativo antes de qualquer rollout amplo.
- Verificar todos os schemas e bloquear o rollout se um ficar com migration pendente.
- Executar `showmigrations`/introspecção por schema e comparar tabela, coluna,
  constraint, índice e permissão esperados, não apenas a linha de histórico.
- Confirmar que uma falha em um tenant não marca os demais como concluídos e que a
  retomada é determinística.
- Aplicar a cadeia também ao template/processo real usado para provisionar e resetar
  tenants.

### 7.5 Compatibilidade com módulos futuros

Todo módulo futuro que referencie servidor, participação, escala, plano ou ocorrência
deve declarar:

- schema de execução e proibição de acesso ao `public`;
- política de permissão/redaction antes de agregação;
- relação com o ledger e confirmação de que não cria obrigação paralela;
- ordem de locks e chave de idempotência quando houver escrita repetível;
- contrato OpenAPI concreto e estratégia N/N-1;
- impacto no grafo de proteção da Demo, quota, seed, backup e restore;
- impacto em selectors/query count e inexistência de lazy load;
- migration aditiva sobre a folha real e rollback de dados;
- novos registros no comando tenant-only, CI e matriz deste plano.

## 8. Arquivos previstos

### 8.1 Backend — novos

- `caixa/models_servidores.py`;
- `caixa/selectors_servidores.py`;
- `caixa/selectors_participacoes_servidores.py`;
- `caixa/selectors_custos_servidores.py`;
- `caixa/serializers_servidores.py`;
- `caixa/serializers_participacoes_servidores.py`;
- `caixa/serializers_custos_servidores.py`;
- `caixa/serializers_custos_recorrentes.py`;
- `caixa/services_servidores.py`;
- `caixa/services_participacoes_servidores.py`;
- `caixa/services_custos_recorrentes.py`;
- `caixa/services_idempotencia.py`;
- `caixa/services_auditoria_recorrencias.py`;
- `caixa/services_ativacao_mensalistas.py`;
- `caixa/security_salarios.py`;
- `caixa/views_servidores_api.py`;
- `caixa/views_participacoes_servidores_api.py`;
- `caixa/views_custos_servidores_api.py`;
- `caixa/views_planos_custos_recorrentes_api.py`;
- commands de materialização, ativação e expurgo;
- migrations novas geradas sobre a cadeia SaaS;
- testes dedicados tenant-aware.

### 8.2 Backend — alterações

- `.env.example` e `.env.production.example`;
- `.gitignore`, removendo a regra que oculta `caixa/test_*.py`, sem remover ignores
  SaaS necessários;
- `caixa/admin.py`;
- `caixa/demo_policy.py`, se algum fluxo for exposto à demo;
- `caixa/middleware.py`;
- `caixa/models.py`;
- `caixa/models_custo_fixo.py`;
- `caixa/permissions.py`;
- `caixa/selectors_custos_fixos.py`;
- selectors, serializers, services e views financeiros afetados pelo sigilo salarial;
- `caixa/serializers_dashboard.py`;
- `caixa/services_backups.py`;
- `caixa/signals.py`;
- `caixa/urls.py`;
- `caixa/views_api_auth.py`;
- `config/settings.py`;
- `tenancy/command_guards.py`;
- `tenancy/test_helpers.py`, apenas se for necessário um harness transacional;
- documentação operacional e workflow de qualidade.

### 8.3 Frontend — novos

- `app/servidores/page.tsx`;
- `app/custos-por-servidor/page.tsx`;
- `lib/types/servers.ts`;
- `lib/utils/local-date.ts`;
- componentes de servidores, custos por servidor, participações e planos recorrentes;
- hooks e services dos novos domínios;
- grid responsivo compartilhado;
- E2E de servidores, recorrências e integração real.

### 8.4 Frontend — alterações

- `components/dashboard/sidebar.tsx`;
- service e tipos de autenticação;
- barrel de `features/financial-dashboard`;
- telas de dashboard, eventos, custos por evento e custos fixos;
- service de dashboard e custos fixos;
- tipos do dashboard;
- scripts de guardrail;
- `package.json`, preservando os checks de demo, parsing horário e snapshots já
  existentes;
- workflow de qualidade.

Não substituir arquivos completos entre implementações. Cada alteração deve ser
fundida semanticamente com o runtime de demo, cache, CSP, guardrails e contratos
canônicos atuais.

## 9. Fases de execução

Princípio de ordenação:

```text
F0 baseline
 └─ F1 Servidores (fundação)
     ├─ F2 Recorrência e salário (backend)
     │   └─ F3 APIs e frontend de Servidores/Recorrência
     └─ F4 Participação + Escala Diária (backend final)
         └─ F5 UI de Participação/Escala + Custos por Servidor
F3 + F5 └─ F6 paridade transversal
F0..F6 └─ F7 qualidade e prontidão operacional
```

A dependência funcional entre os três domínios solicitados é
`Servidor -> Participação -> Dias Trabalhados`, mas participação e dias trabalhados
devem ser implementados como um único contrato backend final. A ramificação de
recorrência depende de Servidor por causa do histórico e da automação salarial, mas
não é pré-requisito para desenvolver rateio/escala. Isso permite trabalho isolado sem
acoplar regras financeiras diferentes e evita refazer payload, migration, formulário
e testes de participação.

### Fase 0 — baseline e contrato

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Confirmar worktrees e alterações preexistentes.
2. Registrar a migration terminal real.
3. Executar baseline backend, frontend, OpenAPI e E2E atuais.
4. Congelar os shapes atuais que não podem regredir.
5. Inventariar todas as superfícies que agregam `CustoFixo`, obrigação, baixa ou
   lançamento para aplicar sigilo salarial antes da agregação.
6. Capturar OpenAPI atual e fixtures de contrato dos endpoints afetados.
7. Registrar versões de PostgreSQL, Python, Node, gerenciador de pacotes e browsers
   usadas no baseline.
8. Resolver ou marcar formalmente cada item da seção 1.2; decisão não comprovada não
   pode virar default permissivo.

Gate:

- baseline e comandos/resultados registrados;
- nenhum arquivo do usuário descartado;
- plano de migrations, compatibilidade N/N-1 e ordem de locks aprovados;
- contratos de erro e redaction congelados;
- nenhuma implementação iniciada com item bloqueante sem confirmação.

### Fase 1 — domínio de servidores no tenant

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Criar os models M1 finais, constraints, históricos e Admin seguro.
2. Importar os models pelo mecanismo atual do app.
3. Criar selectors e services como única escrita sensível.
4. Adaptar testes para `TenantAppTestCase`.
5. Adicionar testes com dois tenants.
6. Criar permissões finais de servidor e validar sincronização por schema.
7. Fixar o contrato de snapshots que será consumido por participação e salário.

Gate:

- models não existem no `public`;
- mesmo documento é aceito em tenants distintos;
- dados e IDs iguais não atravessam hosts;
- constraints, vigências, exclusão e preservação histórica passam no PostgreSQL;
- migration do zero, upgrade, tenant novo e reversão estrutural sem dados passam;
- services impedem escrita salarial sem permissão e não duplicam regra no Admin.

### Fase 2 — recorrência e salário no backend

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Criar os models M2 e constraints finais.
2. Implementar plano, projeção, materialização, recuperação e ocorrência física.
3. Integrar alteração salarial, contrato, corte e ativação ao histórico do servidor.
4. Implementar idempotência, auditoria e retry seletivo.
5. Integrar sigilo salarial antes de todas as agregações financeiras inventariadas.
6. Criar commands tenant-only e testes em `public`/dois tenants, sem ativar agenda.

Gate:

- projeção não escreve; materialização usa `CustoFixo`/obrigação/baixa/FCO canônicos;
- mesma chave/payload reproduz resposta e chave incompatível falha sem efeito;
- duas conexões criam uma ocorrência e deadlock real recebe apenas o retry previsto;
- erro sistêmico é 500 seguro e bloqueio de domínio permanece resultado por item;
- usuário sem permissão não infere salário em linha, contagem, total, log ou command;
- migration e commands são tenant-safe e recusam `public`.

### Fase 3 — APIs e frontend de servidores e recorrência

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Criar serializers, respostas e erros concretos conforme a seção 5.
2. Aplicar permissões antes da busca de objeto e publicar capacidades.
3. Criar rotas, services, hooks, telas e sidebar de servidores.
4. Implementar “Exibir como Sócio” apenas na apresentação.
5. Criar UI de planos, projeções, materialização e recuperação.
6. Atualizar custos fixos/dashboard e validar CORS real dos headers idempotentes.
7. Preservar runtime da API, chave de cache e cancelamento de requests.

Gate:

- CRUD, filtros, automação salarial e recorrência equivalentes;
- redaction e busca não inferencial comprovadas;
- tenant cruzado retorna 404/403 seguro;
- schemas OpenAPI concretos e contratos N/N-1 aprovados;
- reenvio de UI preserva a chave por intenção e mostra resultado sem duplicar;
- lint, typecheck, build e E2E dos fluxos verdes.

### Fase 4 — participação e escala diária no backend

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Criar M3 com participação e dias trabalhados no estado final.
2. Implementar snapshots, serviço único de rateio e ordem global de locks.
3. Implementar criação/edição atômica com `workedDays`, inclusive compatibilidade
   histórica sem backfill.
4. Implementar restauração, recálculo e bloqueio de alteração inválida do evento.
5. Criar selectors e serializers concretos sem lazy load.
6. Cobrir exclusão de servidor, troca de serviço e escritas concorrentes de escala.

Gate:

- rateio igual, proporcional, manual e com centavos comprovado;
- mensalista em zero e sem valor manual;
- escala integral, datas não consecutivas, horas opcionais e legado comprovados;
- concorrência não mistura listas de datas nem deixa rateio parcial;
- exclusão preserva histórico e nenhuma obrigação/despesa/saída nova é criada;
- endpoints de participação já nascem com `workedDays` e OpenAPI concreto;
- query count sem N+1.

### Fase 5 — UI de participação/escala e custos por servidor

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Integrar participações e seletor de datas no detalhe do evento.
2. Criar custos por servidor com filtros, totais e redaction.
3. Enriquecer custos por evento sem modificar seus totais.
4. Exibir detalhes de escala e texto histórico nas superfícies definidas.
5. Preservar data civil local, navegação por teclado e rolagem em evento longo.
6. Testar troca rápida de evento/runtime sem resposta obsoleta.

Gate:

- fluxos criar/editar/excluir/restaurar/recalcular aprovados ponta a ponta;
- rateio e totais coincidem com o backend em todas as telas;
- usuário sem salário não infere linha, contagem ou diferença de total;
- evento histórico permanece editável pelo modo de compatibilidade previsto;
- cache e resposta de outro runtime não aparecem na tela;
- desktop, mobile, teclado e overflow aprovados.

### Fase 6 — ajustes transversais de paridade

Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`

1. Portar a correção de backup UTF-8 preservando paths tenant-scoped.
2. Aplicar grids responsivos compartilhados e revisão dos seletores.
3. Fechar painel de evento apenas após sucesso.
4. Diferenciar mensalistas nas telas financeiras.
5. Atualizar guardrails sem remover os checks SaaS.

Gate:

- backup/restore UTF-8 por tenant;
- nenhuma colisão de artefatos entre tenants;
- política de consistência do backup durante escrita definida para rollout;
- nenhuma tela com overflow global nas viewports definidas;
- painel fica aberto em erro e fecha em sucesso;
- guardrails SaaS preexistentes continuam presentes.

### Fase 7 — qualidade, CI e preparação operacional

Estado: `[PLANEJADO]`

1. Gerar OpenAPI sem warnings.
2. Executar suíte completa no PostgreSQL.
3. Executar testes de concorrência com conexões independentes.
4. Executar testes multi-tenant e demo.
5. Executar frontend completo e E2E.
6. Executar integração navegador -> frontend -> backend -> PostgreSQL.
7. Criar workflows reproduzíveis.
8. Documentar rollout e rollback, sem executar produção.
9. Executar ensaio de compatibilidade backend N com frontend N-1 e frontend N com
   backend N-1 nos pontos declarados compatíveis.
10. Auditar Demo Pública, tenant novo, tenant migrado e retomada de migration falha.

Gate:

- todos os testes descobertos aprovados;
- CI remota aprovada;
- OpenAPI sem warnings, colisões ou schemas genéricos nos endpoints novos;
- matriz N/N-1 e ensaio de rollback aprovados;
- todos os schemas de teste apresentam estrutura e permissões idênticas;
- worktrees revisados;
- nenhuma credencial, banco, dump, log ou artefato temporário versionado.

### 9.1 Matriz de dependências

“Pode ser implementada isoladamente” significa independência de desenvolvimento
depois das dependências listadas; não autoriza deploy parcial nem dispensa o gate
final.

| Fase | Depende de | Pode ser implementada isoladamente? | Exige backend | Exige frontend | Exige migrations | Exige atualização de OpenAPI |
|---|---|---:|---:|---:|---:|---:|
| F0 — baseline/contratos | nenhuma | sim | leitura/testes | leitura/testes | não | snapshot/validação |
| F1 — Servidores | F0 | sim | sim | não | sim (M1) | não, apenas contrato planejado |
| F2 — Recorrência/Salário backend | F0, F1 | sim, independente de participação | sim | não | sim (M2) | não, apenas contrato planejado |
| F3 — APIs/UI Servidores/Recorrência | F1, F2 | sim, independente de rateio | sim | sim | não, salvo correção comprovada | sim |
| F4 — Participação + Escala backend | F0, F1 | sim, independente de recorrência | sim | não | sim (M3) | sim |
| F5 — UI Participação/Escala + Custos | F3, F4 | não | sim | sim | não, salvo correção comprovada | sim |
| F6 — Paridade transversal | F3, F5 | não | sim | sim | não | se contrato afetado |
| F7 — Qualidade/prontidão | F0 a F6 | não | sim | sim | valida todas | valida todas |

Regras da matriz:

- uma fase não começa com a dependência em `[BLOQUEADO]`;
- migrations são criadas apenas na fase indicada; drift detectado depois exige
  decisão registrada, não migration improvisada em fase de UI;
- mudança de payload/status durante F5 ou F6 reabre o gate OpenAPI da fase produtora;
- F3 e F4 podem avançar em paralelo depois de F1, desde que não alterem o mesmo
  contrato sem decisão registrada;
- nenhuma fase é publicável isoladamente: o rollout só ocorre após F7.

## 10. Adaptação dos commands e agendamento

Adicionar à lista de commands tenant-only:

- `materializar_custos_recorrentes`;
- `ativar_mensalistas_existentes`;
- `expurgar_auditoria_custos_recorrentes`.

Cada command deve chamar `ensure_tenant_schema()` antes de consultar ou escrever.

Comportamento:

- `materializar_custos_recorrentes --competencia AAAA-MM`;
- sem competência, recuperar todas as ausentes até o mês local;
- `--dry-run` sem escrita;
- `ativar_mensalistas_existentes --data-corte AAAA-MM-DD --dry-run`;
- escrita de ativação exige confirmação forte;
- expurgo possui `--dry-run`;
- stdout nunca mostra salário.

Execução operacional ocorre via `tenant_command --schema=<schema>`. O agendador deve:

1. listar tenants ativos por fonte confiável no `public`;
2. executar uma transação/command por schema;
3. registrar schema, resultado e correlation ID;
4. continuar ou abortar conforme política explícita, sem trocar tenant dentro de uma
   transação operacional aberta;
5. alertar ausência de execução, erro e crescimento anormal de bloqueios;
6. nunca executar a rotina operacional no `public`.

`[NECESSITA CONFIRMAÇÃO ANTES DA IMPLEMENTAÇÃO]`: os seis itens acima são o contrato
mínimo do futuro orquestrador SaaS, mas fonte de tenants, mecanismo de exclusão
mútua, política continuar/abortar e ferramenta de agendamento ainda não estão
comprovados em código. Até essa decisão:

- implementar e testar somente o command tenant-only;
- não criar loop ad hoc de schemas dentro do command de domínio;
- não ativar cron/timer;
- usar a timezone configurada da aplicação, sem hardcode;
- exigir lock/exclusão mútua por tenant e competência no desenho operacional;
- tratar reexecução, atraso e duas instâncias simultâneas como cenários normais e
  idempotentes.

## 11. Testes obrigatórios

### 11.1 Domínio e banco

- validações de todos os models;
- constraints via `bulk_create`/SQL onde aplicável;
- documento normalizado;
- servidor/serviço ativo, vínculo existente e `EventoCustoServico` obrigatório;
- evento concluído/cancelado somente leitura;
- vigências salariais;
- snapshots e exclusão;
- rateio igual/proporcional, maior resto, desempate por ID, zero distribuível, horas
  versus dias, valor manual, restauração e soma manual acima do total;
- plano salarial sem servidor rejeitado pelo banco;
- renovação sobreposta rejeitada;
- uma ocorrência por plano/competência;
- contrato parcial, mês futuro, corte, vigência e dia inexistente no mês;
- escala diária única e horas positivas;
- migration do zero, upgrade, reversão estrutural vazia e tenant existente com dados.

### 11.2 Concorrência PostgreSQL

- materialização simultânea;
- criação de plano com mesma chave;
- renovação simultânea;
- alteração salarial simultânea;
- ativação simultânea;
- atualização simultânea da escala;
- criação de participação versus exclusão do servidor;
- troca de serviço/valor manual versus recálculo do evento;
- redução do período do evento versus substituição da escala;
- alteração salarial versus materialização;
- alteração/desativação/renovação do plano versus materialização e recuperação;
- duas instâncias do command no mesmo tenant/competência;
- mesma chave idempotente em atores diferentes e em tenants diferentes;
- agregação de auditoria concorrente na primeira ocorrência da janela;
- deadlock real e retry;
- confirmação de que erros não elegíveis não recebem retry;
- rollback quando obrigação, escala, rateio, quota ou etapa intermediária falhar.

### 11.3 Isolamento multi-tenant

Criar tenants A e B com:

- mesmos IDs;
- mesmo documento de servidor;
- mesma chave idempotente;
- planos e competências iguais;
- eventos e participações equivalentes.

Provar:

- host A retorna somente A;
- host B retorna somente B;
- ID de A no host B não revela A;
- usuário/sessão/CSRF de A não autoriza B;
- idempotência de A não bloqueia B;
- auditoria de A não aparece em B;
- cache e throttling não colidem;
- command em `public` falha;
- tentativa de enviar tenant/schema por query, header ou body não altera o contexto;
- backup de A não contém B;
- `public` não possui tabelas operacionais;
- tenant novo, tenant migrado e tenant da demo possuem mesma estrutura, mas dados e
  permissões próprios.

### 11.4 Segurança salarial

Testar com e sem permissões em:

- servidor/lista/detalhe/busca;
- planos e projeções;
- custos fixos;
- custos por servidor;
- dashboard;
- mês financeiro;
- obrigações e detalhes;
- baixas/pagamentos;
- ledger;
- Admin;
- commands;
- exports e backups autorizados.

O teste deve procurar também um salário-sentinela no corpo, stdout, arquivo e logs.
Deve procurar o sentinela em respostas de erro, correlation/auditoria, contagens,
resumos, filtros/opções e diferenças de total, não apenas em campos de salário.

### 11.5 API e OpenAPI

- sucesso e todos os códigos esperados;
- CSRF, content type e métodos;
- IDOR e ordem da verificação de permissão;
- headers de idempotência;
- lote com bloqueio, conflito e falha sistêmica;
- contratos concretos;
- tipos, nulabilidade, obrigatoriedade, formatos decimais/datas e exemplos válidos;
- envelopes diferentes por status preservados;
- `Idempotency-Replayed` em resposta original e replay;
- ausência total de tenant/schema nos schemas públicos;
- zero colisão de `operation_id`;
- zero warning no validador do schema;
- diff do OpenAPI revisado e limitado aos contratos pretendidos.

### 11.6 Frontend

- cadastro diarista/mensalista;
- múltiplos serviços;
- sócio apenas visual;
- salário oculto;
- ativação salarial confirmada;
- participação, valor manual, restauração e recálculo;
- troca rápida de evento sem resposta antiga sobrescrever a nova;
- escala diária, data civil local e evento longo;
- custos por servidor e custos por evento;
- planos, projeções, materialização e recuperação;
- dashboard incompleto;
- painel de evento fechando em sucesso;
- desktop e mobile;
- tenant/runtime da API trocado durante a sessão;
- demo sem permissão sensível;
- frontend N contra backend N-1 e frontend N-1 contra backend N nos contratos
  declarados compatíveis;
- resposta 400/401/403/404/409/415/500, retry/replay e dupla submissão;
- acessibilidade: foco, rótulos, erro associado ao campo, teclado e contraste nos
  componentes novos.

### 11.7 Demo Pública

- módulos novos ausentes da navegação enquanto não houver decisão de exposição;
- usuário demo não recebe salário, sensíveis, auditoria ou administração;
- participação não altera indiretamente evento de seed;
- data trabalhada não altera indiretamente participação/evento protegido;
- quota excedida reverte a transação inteira;
- reset recria schema, aplica todas as migrations, sincroniza a matriz decidida e
  mantém os seeds imutáveis;
- dois leases/sessões não compartilham cache, dados ou permissão.

### 11.8 Migrations, rollout e rollback

- `migrate_schemas --plan` e aplicação em `public`, tenant vazio, tenant populado e
  múltiplos tenants;
- introspecção confirma ausência de tabela operacional no `public`;
- tenant criado depois da mudança recebe todas as constraints/permissões;
- falha induzida em um tenant, retomada e relatório de schema pendente;
- frontend N-1 opera durante backend aditivo N;
- frontend N não chama contrato indisponível antes do backend N;
- rollback de aplicação preserva ocorrências, obrigações, baixas, FCO, snapshots,
  escala e auditoria;
- restore UTF-8 de A não altera B e falha de restore não deixa estado parcial;
- estratégia confirmada para backup enquanto há escrita concorrente.

### 11.9 Commands e observabilidade

- `--dry-run` não escreve em nenhuma tabela;
- confirmação forte é obrigatória na ativação salarial;
- command sem schema/contra `public` falha antes da primeira consulta operacional;
- stdout e logs contêm schema/correlation ID, mas nenhum sentinela sensível;
- repetição, atraso e execução simultânea mantêm um único efeito;
- expurgo respeita exatamente a retenção de auditoria e não remove idempotência;
- alerta/metricas distinguem bloqueio de domínio, conflito e falha sistêmica sem
  cardinalidade baseada em identidade.

## 12. Performance e observabilidade

Orçamentos mínimos:

- projeção de 100 planos × 24 meses: no máximo três `SELECTs`;
- repetir benchmark com 1, 100 e 1.000 planos no PostgreSQL;
- selectors de participação usam `select_related` e `prefetch_related`;
- serializers não podem disparar lazy load oculto;
- listas com 1 e 100 servidores/participações devem manter query count constante
  dentro do orçamento registrado na Fase 0; qualquer variação por item bloqueia o
  gate;
- filtros salariais usam subquery/relação SQL, não lista ilimitada de IDs em Python;
- medir p50/p95, tempo total, memória, quantidade de queries e tamanho do payload por
  tenant representativo;
- registrar `schema_name`, endpoint/command, status e correlation ID;
- nunca registrar valor ou identidade salarial;
- métricas não usam schema, usuário, servidor, documento ou correlation ID como
  label de alta cardinalidade; o schema pode permanecer em log estruturado com
  acesso controlado;
- alertar falhas de migrations por schema, commands ausentes, conflitos/retries,
  materialização atrasada, quota da Demo e backup/restore sem sucesso.

## 13. CI

O backend SaaS exige PostgreSQL por causa de `django-tenants`. Não criar um gate
SQLite artificial que contorne a configuração real.

Workflow backend:

1. instalar dependências congeladas;
2. iniciar PostgreSQL compatível;
3. aplicar migrations de `public` e tenants de teste;
4. executar `check` e `check --deploy` com configuração segura;
5. executar `makemigrations --check --dry-run`;
6. gerar e validar OpenAPI;
7. executar suíte completa;
8. executar concorrência e isolamento multi-tenant;
9. executar testes de migrations, tenant novo, Demo e rollback lógico;
10. executar `git diff --check`.

Testes backend não podem presumir que o repositório frontend exista como diretório
irmão no runner. Qualquer evidência de frontend exigida por um command deve receber
fixture ou referência explícita; o cenário sem referência precisa continuar
fail-closed.

Workflow frontend:

1. instalação com lockfile congelado;
2. lint;
3. typecheck;
4. todos os guardrails atuais, inclusive demo runtime, parsing de serviços por hora,
   snapshots, contratos canônicos, cache, listas, filtros e responsividade;
5. novos guardrails de servidores/recorrências, se necessários;
6. build de produção;
7. Playwright;
8. E2E integrado obrigatório em stack efêmera frontend -> backend -> PostgreSQL.

Se um runner não puder executar o E2E integrado, o job deve falhar ou permanecer
explicitamente bloqueado; não pode ficar verde por `continue-on-error`, ausência de
secret, detecção silenciosa de ambiente ou fallback para mock. Separar testes rápidos
e lentos é permitido, mas F7 exige ambos.

Não adicionar `"type": "module"` ou substituir scripts do `package.json` sem provar
compatibilidade com os scripts atuais. Manter o runtime de demo e os testes já
existentes.

Gates de CI adicionais:

- lockfiles sem alteração implícita e versões de serviços fixadas;
- cache de CI não pode reutilizar banco, schema ou artefato de outro job/tenant;
- OpenAPI gerado é comparado com o artefato aprovado e validado antes do build do
  cliente;
- coleta de cobertura/artefatos remove dados sensíveis e sempre roda no `finally`;
- nenhuma suíte obrigatória pode ser excluída por padrão de descoberta ou pelo
  ignore atual de `caixa/test_*.py`.

## 14. Rollout planejado

Sem autorização para executar nesta etapa.

Ordem futura:

1. aprovar F7, janela, responsáveis, comunicação, critérios go/no-go e tempo máximo
   por tenant;
2. produzir artefatos imutáveis de backend/frontend/OpenAPI com versão e checksum;
3. homologar tudo em PostgreSQL descartável com cópia/fixtures representativas;
4. definir quiescência ou snapshot consistente e gerar backup UTF-8 tenant-scoped;
5. provar restore do backup antes da primeira migration;
6. validar plano, lock/timeouts e duração das migrations em cópia representativa;
7. garantir que backend/frontend N-1 toleram o schema expandido;
8. migrar tenant canário e introspectar estrutura/permissões;
9. publicar backend N compatível com frontend N-1;
10. sincronizar permissões no tenant canário;
11. publicar frontend N somente após health/contratos do backend N;
12. executar materialização em `--dry-run`;
13. validar cadastro, rateio, plano, salário, escala, OpenAPI e backup;
14. ampliar migrations tenant a tenant, com checkpoint e relatório por schema;
15. sincronizar permissões e repetir smoke por lote;
16. ativar agendamento somente após materialização manual aprovada e confirmação dos
    itens operacionais da seção 10;
17. monitorar primeira virada mensal e manter a janela de rollback de aplicação.

O rollout para se um schema falhar, se a estrutura divergir, se o backup não puder
ser restaurado, se houver vazamento de permissão ou se p95/retries excederem o limite
aprovado. Tenant parcialmente migrado não pode receber frontend N até ser reconciliado.

Para tenants da demo:

- reset/recriação precisa aplicar a cadeia nova;
- conferir quota e seed;
- sincronizar matriz exata da Demo Pública;
- não semear salário real nem conceder permissão salarial;
- validar que um seed de evento não pode ser alterado indiretamente por participação;
- manter navegação e endpoints novos indisponíveis enquanto a decisão da seção 1.2
  não estiver registrada;
- testar lease novo e reset depois do deploy antes de liberar tráfego público.

## 15. Rollback planejado

- interromper agendamento antes do rollback;
- impedir novas escritas durante reversão;
- selecionar a ordem pela matriz N/N-1 comprovada: reverter frontend primeiro somente
  quando backend N suporta frontend N-1; nunca executar frontend N contra backend N-1
  sem teste explícito;
- rollback de aplicação não implica rollback de schema nem exclusão de dados;
- preservar ocorrências, obrigações, baixas e FCO já criados;
- não apagar planos, auditoria, escala ou históricos com dados reais;
- preferir migration corretiva/aditiva;
- exportar escala diária antes de remover qualquer tabela;
- manter agregados de dias/horas para preservar rateio;
- restaurar tenant individual sem atingir os demais;
- não usar rollback destrutivo de schema como procedimento normal;
- preservar registros de idempotência para que retries durante a troca de versão não
  dupliquem efeitos;
- registrar quais tenants receberam cada migration/versão e bloquear tráfego somente
  dos incompatíveis;
- depois da reversão, executar smoke de sessão, permissões, leitura financeira,
  rateio, materialização em `--dry-run`, Demo e isolamento;
- definir antes do rollout RTO, RPO, responsável pela decisão e critérios objetivos
  de retorno.

Migrations destrutivas ou reversão física com dados tornam o rollback
`[BLOQUEADO]`; nesse caso, manter o schema expandido e reverter apenas aplicação, ou
criar migration corretiva. A reversão física só é aceitável em ambiente sem dados,
com prova de reversibilidade.

## 16. Critérios finais de aceite

### Paridade funcional

- [ ] Usuário de tenant comum encontra as mesmas rotas e ações.
- [ ] Cadastros, mensagens, filtros, estados e permissões são equivalentes.
- [ ] Contratos de servidor, participação/escala, custos e recorrência coincidem em
      campos, tipos, nulabilidade, status e envelopes.
- [ ] Rateios e totais coincidem centavo a centavo.
- [ ] Mensalistas nunca entram no rateio de diárias.
- [ ] Projeção não cria obrigação.
- [ ] Materialização usa o fluxo canônico.
- [ ] Datas trabalhadas não alteram a fórmula financeira.
- [ ] Participações históricas continuam utilizáveis sem backfill inventado.
- [ ] Sócio é apenas apresentação.
- [ ] Painel de evento fecha somente após sucesso.
- [ ] Responsividade e acessibilidade foram testadas em desktop/mobile/teclado.
- [ ] Backup/restore UTF-8 mantém caracteres e isolamento.

### Segurança SaaS

- [ ] Nenhuma tabela operacional no `public`.
- [ ] Nenhum tenant informado pelo cliente.
- [ ] Dois tenants com IDs iguais permanecem isolados.
- [ ] Sessão e CSRF não atravessam hosts.
- [ ] Cache, throttle, idempotência, auditoria e arquivos são tenant-scoped.
- [ ] Commands recusam `public`.
- [ ] Sigilo salarial é fail-closed.
- [ ] Demo Pública não ganha acesso sensível.
- [ ] Seeds da Demo não podem ser alterados por relações indiretas.
- [ ] Tenant novo, migrado e resetado recebem estrutura correta sem dados cruzados.

### Hardening obrigatório

- [ ] Migrations limpas e aplicáveis a todos os schemas.
- [ ] Suíte completa PostgreSQL aprovada.
- [ ] Concorrência real aprovada.
- [ ] Ordem de locks, retry seletivo, rollback transacional e idempotência aprovados.
- [ ] OpenAPI concreto, sem warnings, sem `operation_id` duplicado e sem tenant/schema.
- [ ] Backend/frontend N/N-1 e rollback de aplicação ensaiados.
- [ ] Logs, métricas e erros não contêm sentinela sensível.
- [ ] Query count e benchmarks respeitam os orçamentos.
- [ ] Demo, commands, backup e retomada de migration falha foram testados.

### Qualidade e prontidão

- [ ] Lint, typecheck, guardrails e build aprovados.
- [ ] E2E mockado e integrado aprovados.
- [ ] Backup/restore UTF-8 aprovado em dois tenants.
- [ ] CI remota aprovada.
- [ ] Nenhuma credencial ou artefato temporário versionado.
- [ ] Evidências, desvios e decisões de todas as fases estão registrados.
- [ ] Todos os itens “necessita confirmação” que afetem rollout foram resolvidos.

### Evoluções futuras não bloqueantes

- [ ] Retenção de idempotência permanece registrada, sem ser confundida com gate atual.
- [ ] Paginação/streaming permanece registrada com métricas/gatilhos.
- [ ] Apropriação não nula, folha e proporcionalidade continuam fora da implementação
      até decisão e plano próprios.
- [ ] Nenhuma evolução futura foi usada para dispensar requisito obrigatório.

## 17. Registro desta etapa

- [COMPROVADO] Projetos e documentos funcionais foram auditados em modo somente
  leitura.
- [COMPROVADO] Foram identificadas as diferenças de backend, frontend, arquitetura,
  migrations e segurança multi-tenant.
- [COMPROVADO] A colisão de numeração de migrations foi registrada.
- [COMPROVADO] O plano preserva resolução por Host, schema por tenant, comandos
  tenant-only, paths tenant-scoped, runtime de demo e permissões especiais.
- [COMPROVADO] Participação e custos por servidor ainda possuem documentação OpenAPI
  genérica na implementação funcional auditada; schemas concretos foram classificados
  aqui como hardening obrigatório, não como paridade já comprovada.
- [COMPROVADO] As hipóteses sem implementação executável foram marcadas como
  `[NECESSITA CONFIRMAÇÃO ANTES DA IMPLEMENTAÇÃO]`.
- [COMPROVADO] A ordem foi corrigida para que Participação e Escala Diária nasçam no
  mesmo contrato backend final, depois da fundação de Servidores.
- [COMPROVADO] Nenhum código, migration, banco, configuração ou documento preexistente
  foi alterado nesta etapa.
- [PLANEJADO] Todas as fases de implementação permanecem pendentes de execução futura.

### 17.1 Política obrigatória de atualização deste plano

Este arquivo é um artefato vivo e faz parte do gate. Cada fase implementada deve
atualizá-lo na mesma mudança que pretende encerrar a fase. Não é permitido marcar
`[COMPROVADO]` apenas por existência de código ou por relato externo.

Para cada fase:

1. atualizar estado e datas de início/fim;
2. registrar escopo realmente implementado e arquivos relativos afetados;
3. registrar evidências reproduzíveis;
4. registrar todos os testes executados, inclusive falhas e skips;
5. registrar desvios encontrados entre plano, código atual e comportamento esperado;
6. registrar a decisão técnica adotada, alternativas rejeitadas e impacto;
7. atualizar dependências, contratos, migrations, riscos, rollout e rollback quando
   o desvio afetar seções anteriores;
8. deixar itens não comprovados desmarcados e explicar o bloqueio;
9. confirmar revisão do diff e ausência de alteração fora do escopo da fase.

Evidência aceitável:

- comando exato, ambiente/versões, banco PostgreSQL e resultado;
- teste automatizado identificado por nome e resultado;
- diff de OpenAPI e validação do schema;
- plano/introspecção de migration por schema;
- contagem de queries, benchmark ou log sanitizado;
- evidência de E2E/CI com identificador estável;
- arquivos e linhas por caminho relativo, sem credenciais, dumps, dados pessoais ou
  caminhos de outra aplicação.

Não é evidência suficiente:

- “funcionou localmente” sem comando/resultado;
- teste apenas em SQLite para lock, constraint ou concorrência;
- screenshot sem estado/backend verificável;
- teste mockado como substituto do E2E integrado;
- CI verde com job obrigatório pulado;
- documentação histórica sem correspondência no código.

### 17.2 Modelo de registro por fase

```text
Fase:
Estado:
Início/fim:
Escopo entregue:
Arquivos relativos afetados:
Migrations e schemas validados:
Contratos/OpenAPI alterados:
Evidências:
Testes executados (comando, ambiente, resultado):
Testes falhos/pulados e motivo:
Desvios encontrados:
Decisão técnica e alternativas:
Impacto multi-tenant/Demo/permissões:
Impacto N/N-1/rollback:
Riscos residuais:
Próximo gate:
Revisor/data:
```

### 17.3 Controle de desvios e mudança de requisito

- Desvio funcional comprovado no código auditado atualiza a seção funcional
  correspondente e recebe teste de paridade.
- Regra encontrada somente em documentação recebe o rótulo
  `[NECESSITA CONFIRMAÇÃO ANTES DA IMPLEMENTAÇÃO]`; não pode ser promovida por
  conveniência.
- Invariante SaaS não é removida para atingir paridade. O conflito é resolvido com
  adaptação tenant-aware e teste.
- Decisão que reduza proteção, altere contrato ou torne requisito obrigatório
  opcional exige justificativa técnica explícita e aprovação antes da implementação.
- Falha descoberta reabre a fase produtora e todas as fases dependentes relevantes.
- Registros antigos não são apagados; correções são anexadas com data para manter a
  trilha de decisão.

### 17.4 Registro F0 — baseline anterior à implementação

Fase: F0 — baseline e contrato
Estado: `[IMPLEMENTADO SEM EVIDÊNCIA]`
Início: 29/07/2026
Escopo entregue: worktrees, migration terminal, ambiente, checks de backend,
OpenAPI e frontend inventariados antes da primeira alteração de código.
Migration terminal: `caixa.0042_demo_seed_keys`.
Banco: PostgreSQL 18.4 com backend `django_tenants.postgresql_backend`.
Ambiente: Python 3.13.1; Django instalado 6.0.6; requirements fixa 6.0.7;
Node 24.15.0; pnpm 11.17.0.

Evidências:

- `DEBUG=True python manage.py check`: OK, zero issues;
- `DEBUG=True python manage.py makemigrations --check --dry-run`: OK, nenhuma
  mudança;
- `DEBUG=True python manage.py spectacular --validate --fail-on-warn`: OK;
- `pnpm run verify:frontend`: lint, typecheck e todos os guardrails executados antes
  do build: OK;
- `pnpm run build`, repetido isoladamente: OK em 57,2 s, 22 páginas geradas;
- `python manage.py test --verbosity 1`: não concluiu no limite de 3.604,1 s e foi
  encerrado após o timeout; não houve saída de falha antes do limite.

Desvios encontrados:

- o valor preexistente de `DEBUG` no ambiente não é booleano e é rejeitado pelo
  settings; os comandos de baseline usaram override efêmero, sem alterar `.env`;
- a versão Django instalada está uma revisão abaixo do requirements;
- o cliente `psql` não está no PATH, embora a conexão Django com PostgreSQL funcione;
- a primeira execução paralela deixou um build concorrente; a repetição isolada
  passou e o arquivo gerado `next-env.d.ts` foi restaurado ao conteúdo rastreado;
- a suíte backend monolítica excede uma hora e precisa ser segmentada para diagnóstico
  e mantida como gate completo final.

Decisão técnica:

- F0 não será marcada `[COMPROVADO]` enquanto a suíte backend completa não terminar;
- fases seguintes podem usar testes focados PostgreSQL, `check`, migrations e
  OpenAPI, mas F7 continua bloqueada até a suíte integral ou segmentada equivalente
  passar;
- nenhum desvio de ambiente será corrigido implicitamente dentro das fases
  funcionais.

Impacto multi-tenant/Demo/permissões: nenhum; somente leitura e testes.
Impacto N/N-1/rollback: contratos atuais capturados sem alteração.
Próximo gate: F1 — domínio de Servidores.

### 17.5 Registro de implementação F1 a F6 — 29/07/2026

Estado geral: `[EM IMPLEMENTAÇÃO]`. As fases possuem implementação local e
evidências focadas, mas permanecem em `[IMPLEMENTADO SEM EVIDÊNCIA]` até que todos
os gates, inclusive rollback estrutural, integração real N/N-1, backup/restore e
suíte regressiva segmentada completa, sejam concluídos.

Escopo entregue:

- F1: models, constraints, snapshots, histórico, services, selectors, permissões,
  Admin somente leitura e isolamento por schema do domínio de Servidores;
- F2: planos recorrentes, projeção, materialização, recuperação, salário derivado,
  idempotência, auditoria agregada, retry transacional, commands tenant-only e
  sigilo salarial antes das agregações financeiras;
- F3: contratos HTTP, capacidades de sessão, rotas, telas, hooks e services de
  Servidores e planos recorrentes, inclusive “Exibir como Sócio” apenas visual;
- F4: participação e escala diária em estado final, datas trabalhadas, snapshots,
  rateio, restauração, recálculo, locks e bloqueio de intervalo inválido de evento;
- F5: painel de participação no evento, custos por servidor, detalhes de escala,
  distinção de mensalista e preservação de data civil local;
- F6: backup UTF-8 mantendo paths por tenant, grids responsivos compartilhados,
  fechamento do painel somente após sucesso e guardrails SaaS preservados.

Migrations criadas, sem aplicação em banco persistente:

- `caixa.0043_servidores`;
- `caixa.0044_recorrencias_salariais`;
- `caixa.0045_participacoes_escala_diaria`.

Validações de migrations e schemas:

- `python manage.py makemigrations --check --dry-run`: OK, sem drift;
- `python manage.py migrate_schemas --plan`: plano tenant reconheceu M1, M2 e M3;
- criação dos bancos/schemas temporários pelas suítes PostgreSQL: OK;
- tenant adicional criado durante teste aceitou o mesmo documento de outro tenant
  sem vazamento por host;
- migrations não foram executadas em schemas persistentes;
- reversão estrutural explícita e retomada após migration interrompida ainda
  pendentes.

Contratos/OpenAPI:

- respostas de Servidores, Participações, Escala e Custos por Servidor receberam
  serializers concretos;
- planos recorrentes, projeções e materialização mantêm requests/responses
  concretos e headers idempotentes;
- `python manage.py spectacular --validate --fail-on-warn --file NUL`: OK;
- CORS permite `Idempotency-Key` e expõe `Idempotency-Replayed`;
- ensaios backend N/frontend N-1 e frontend N/backend N-1 ainda pendentes.

Evidências backend PostgreSQL:

- `python manage.py check`: OK;
- `python manage.py test caixa.test_custos_recorrentes --verbosity 1 --noinput`:
  97 testes, OK em 339,302 s;
- `python manage.py test caixa.test_servidores --verbosity 1 --noinput`:
  67 testes, OK em 310,602 s;
- teste adicional `CommandsRecorrentesEscopoTenantTests`: OK; os três commands
  recusam execução em `public`;
- teste `ServidoresIsolamentoMultiTenantTests`: OK; documento repetido por schema,
  listagem isolada e 404 para ID exclusivo de outro tenant;
- teste focado da Demo Pública: OK; usuário demo permanece sem capacidades de
  Servidores, Participações, Custos por Servidor, salário, plano ou materialização;
- `python manage.py test tenancy.tests.TenantBackupIsolationTests --verbosity 1
  --noinput`: 9 testes, OK em 84,643 s; listagem, download, SHA-256, rate limit,
  criação e colisão de nomes permaneceram isolados por schema;
- testes reais `SegurancaTests.test_superusuario_cria_backup_manual_pela_api` e
  `SegurancaTests.test_comando_backup_mensal_continua_criando_e_evitando_duplicado`:
  2 testes, OK em 43,535 s; criação, metadados, hash e deduplicação aprovados;
- concorrência PostgreSQL comprovada para salário, ativação, escala, materialização,
  chave idempotente, deadlock/retry e auditoria agregada.

Evidências frontend:

- `corepack pnpm run typecheck`: OK;
- `corepack pnpm run lint`: OK;
- guardrails de uso canônico, responsividade, contratos de lista, paridade, serviços
  por hora, snapshots de orçamento, layout, separação contrato/evento, boundary,
  acessibilidade e runtime da Demo: OK;
- `corepack pnpm run build`: OK no estado final em 63,2 s, 24 rotas;
- E2E mockado de Servidores e Recorrência: 11 testes passaram no ciclo conjunto; o
  único clique flutuante em `<details>` passou ao ser repetido isoladamente,
  totalizando 12 cenários aprovados;
- E2E integrado com backend real de recorrência e escala ainda pendente.

Desvios encontrados e decisões técnicas:

- `TenantTestCase` mantém atomic externo e não permite concorrência real entre
  conexões; foi criada base transacional tenant específica para esses testes, com
  schema efêmero por caso e remoção ao final;
- a auditoria podia receber timestamps em ordem inversa enquanto aguardava lock e
  criar dois agregados; a janela passou a usar distância temporal absoluta,
  preservando o menor `first_occurred_at` e o maior `last_occurred_at`;
- a UI original gerava nova chave em cada retry; o frontend SaaS mantém a mesma
  chave para a mesma intenção/payload e cria nova chave quando a intenção muda;
- a Demo não recebeu permissões novas. A ausência de capacidade é deliberada e foi
  testada, mantendo comportamento fail-closed;
- dados salariais são filtrados antes de queryset, serialização, totais, dashboard,
  posição de caixa, Admin, diagnóstico e exportação;
- um guardrail preexistente de cache executado diretamente pelo Node não resolve o
  alias TypeScript `@/` nesse modo. O código não foi enfraquecido para contornar o
  runner; typecheck, build e os demais guardrails passaram. O runner deve ser
  corrigido antes de F7.

Impacto em rollback:

- nenhuma migration foi aplicada fora dos bancos temporários;
- rollback de código requer frontend e backend como uma única unidade por causa dos
  contratos aditivos de participação/escala;
- ocorrências materializadas continuam canônicas e não podem ser apagadas por
  rollback de plano;
- ensaio de reversão M3 -> M2 -> M1 sem dados e política para schema com dados
  materializados permanecem no próximo gate.

Riscos residuais e próximo gate:

- executar restore real do backup UTF-8 em banco descartável e comparar dados;
- executar E2E navegador -> frontend -> backend -> PostgreSQL;
- validar permissões em tenant novo e tenant migrado após aplicação controlada;
- executar reversão estrutural e retomada de migration falha em banco descartável;
- corrigir o runner do guardrail de cache e executar a regressão segmentada restante;
- concluir matriz N/N-1, rollout/rollback e somente então promover F1 a F6 para
  `[COMPROVADO]`.

### 17.6 Auditoria técnica final F1–F6 — 29/07/2026

Estado: `[AUDITORIA BLOQUEADA]`
Veredito: **BLOQUEADO para iniciar F7, criar commits ou aplicar migrations**.
Natureza da revisão: somente leitura de backend, frontend, migrations, testes,
OpenAPI e estado dos schemas persistentes. Nenhuma correção de código foi feita.

#### 17.6.1 Escopo efetivamente auditado

- o inventário solicitado como “108 arquivos” não corresponde ao worktree atual;
- foram encontrados 112 registros reais em `git status --short`: 68 no backend
  (38 rastreados modificados e 30 não rastreados) e 44 no frontend
  (27 rastreados modificados e 17 não rastreados);
- o diff rastreado do backend contém 38 arquivos, 1.840 adições e 93 remoções;
- o diff rastreado do frontend contém 27 arquivos, 1.142 adições e 242 remoções;
- todos os 112 registros foram incluídos no inventário e na revisão semântica;
- os arquivos de maior superfície e risco são `caixa/admin.py`,
  `caixa/models_custo_fixo.py`, `caixa/views_custos_fixos_api.py`,
  `features/financial-dashboard/components/financial-fixed-costs-view.tsx`,
  `features/financial-dashboard/services/financial-fixed-costs-service.ts` e
  `features/financial-dashboard/components/financial-event-costs-view.tsx`;
- não foi encontrada substituição integral de arquivo rastreado que apagasse
  deliberadamente uma implementação anterior; as mudanças amplas concentram fusão
  de recorrência, sigilo salarial, participação e responsividade, mas exigem os
  bloqueios abaixo antes de serem aceitas;
- os dois arquivos de teste não rastreados anteriores a F1–F6 permaneceram
  inalterados e foram apenas inventariados.

#### 17.6.2 Achados bloqueantes

**B-01 — inferência de salário no relatório de custos por servidor**

- Arquivos/linhas: `caixa/views_custos_servidores_api.py:56-65`,
  `caixa/selectors_custos_servidores.py:193-256` e
  `features/financial-dashboard/components/financial-server-costs-view.tsx:450-468`.
- Esperado: remover salários antes da consulta/agregação e não revelar existência,
  quantidade, nome ou diferença de total a quem não possui
  `view_salario_servidor`.
- Encontrado: o selector cria grupos exclusivamente a partir do histórico salarial
  e calcula `serverCount`; somente depois a view esvazia `salaryCosts` e troca os
  totais. O nome, vínculo mensalista, existência do grupo e contagem permanecem na
  resposta e são apresentados na UI.
- Impacto: usuário Operacional com `view_custos_servidor`, mas sem permissão salarial,
  consegue inferir a existência e a identidade de mensalistas com custo salarial,
  violando o sigilo obrigatório e o desenho fail-closed.
- Correção recomendada: aplicar a autorização antes de carregar qualquer fonte
  salarial e construir grupos/resumo somente com linhas visíveis; adicionar teste
  com servidor-sentinela que possua salário e nenhuma participação.
- Fases reabertas: F2, F3 e F5.

**B-02 — exclusão de participação pelo Admin ignora o serviço único de domínio**

- Arquivo/linhas: `caixa/admin.py:2050-2086` e
  `caixa/services_participacoes_servidores.py:456-468`.
- Esperado: Admin somente leitura para participação ou exclusão delegada ao serviço
  que bloqueia o evento e redistribui o grupo.
- Encontrado: os campos são somente leitura e a inclusão é negada, mas
  `ParticipacaoServidorEventoAdmin` não nega nem sobrescreve a exclusão. Superusuário
  ou grupo Administrador recebe a permissão de exclusão e o fluxo padrão do Admin
  apaga a linha sem chamar `excluir_participacao`.
- Impacto: `valor_final`, snapshots do rateio e soma distribuída das linhas restantes
  ficam inconsistentes; Demo policy, autoria e validação de evento concluído também
  podem ser contornadas.
- Correção recomendada: tornar o Admin explicitamente não mutável ou encaminhar a
  operação para o serviço de domínio com todas as validações e locks; testar GET/POST
  da URL de exclusão do Admin.
- Fases reabertas: F1 e F4.

**B-03 — alteração do custo distribuível não recalcula as participações**

- Arquivos/linhas: `caixa/signals.py:61-75` e
  `caixa/services_participacoes_servidores.py:79-169`.
- Esperado: qualquer alteração de `EventoCustoServico.valor_diarias`, ou remoção do
  custo estruturado, deve preservar a soma exata do rateio na mesma transação e pelo
  mesmo serviço de domínio.
- Encontrado: os handlers de `EventoCustoServico` sincronizam evento e obrigações,
  mas nunca recalculam participações. O recálculo do rateio é chamado somente pelos
  fluxos de participação; existem outros fluxos que salvam ou removem custos de
  serviço.
- Impacto: editar orçamento/custo após cadastrar participantes deixa
  `valor_calculado`, `valor_final` e snapshots com o total anterior; remover o custo
  pode deixar participações que não podem mais ser recalculadas.
- Correção recomendada: criar uma orquestração transacional única para mutação do
  custo e rateio, obedecendo `Evento -> Servidor -> Participação ->
  EventoCustoServico`; bloquear remoção enquanto houver participação ou definir
  migração funcional explícita.
- Fases reabertas: F4 e F5.

**B-04 — redução concorrente do período do evento pode aceitar escala fora do intervalo**

- Arquivos/linhas: `caixa/models.py:940-951`,
  `caixa/views_eventos_api.py:333-350` e
  `caixa/services_participacoes_servidores.py:343-382`.
- Esperado: redução do intervalo e criação/substituição da escala serializadas sob o
  mesmo lock de Evento, sem estado impossível após commit.
- Encontrado: a escrita de participação bloqueia Evento; a atualização do evento faz
  `full_clean()` antes de salvar, mas não abre transação nem executa
  `select_for_update()`. Uma participação pode ser inserida após a validação e antes
  do `UPDATE` do evento, que então conclui com uma data trabalhada fora do novo
  intervalo.
- Impacto: invariante de escala é violada por corrida PostgreSQL real; o banco não
  possui constraint capaz de validar a data contra outra tabela.
- Correção recomendada: mover a alteração do período para serviço transacional com
  lock do Evento antes da validação e testar a corrida obrigatória em duas conexões
  PostgreSQL.
- Fases reabertas: F4 e F5.

**B-05 — deploy desacoplado N/N-1 está comprovadamente incompatível**

- Arquivos/linhas: `caixa/views_custos_fixos_api.py:645-703`,
  `features/financial-dashboard/services/financial-fixed-costs-service.ts:685-698`
  e `features/financial-dashboard/components/financial-recurring-cost-plans-panel.tsx`.
- Esperado: backend N tolerar frontend N-1 nos contratos declarados aditivos, e
  frontend N degradar de forma segura com backend N-1.
- Encontrado: backend N exige `authorizedMaterializationDate` e
  `Idempotency-Key` quando o endpoint legado recebe `isRecurring=true`; frontend N-1
  não enviava esses valores. No sentido inverso, o painel novo consulta rotas
  inexistentes no backend N-1 e o backend antigo materializa toda a série física em
  vez de criar plano/projeção.
- Impacto: criação recorrente retorna 400 no primeiro sentido; no segundo, a UI
  apresenta erro e a semântica financeira muda. Rollback para backend antigo após
  criar ocorrências novas também permite tratar linhas derivadas como custos legados
  editáveis.
- Correção recomendada: escolher e documentar janela de compatibilidade, defaults
  seguros/versionamento ou deploy atômico com bloqueio de tráfego; executar ensaios
  reais nos dois sentidos antes de F7.
- Fases reabertas: F2, F3, F6 e F7.

#### 17.6.3 Achados altos

**A-01 — fonte salarial do relatório ignora autorização, mês parcial e ocorrência
física**

- Arquivo/linhas: `caixa/selectors_custos_servidores.py:105-130` e `:191-230`.
- Esperado: histórico é fonte temporal, contrato e corte limitam a competência,
  meses parciais são bloqueados e ocorrência física materializada prevalece.
- Encontrado: o relatório lê apenas `HistoricoSalarialServidor`, escolhe qualquer
  vigência que toque a competência e lança o salário integral. Não consulta
  `CustoFixo`, plano, contrato nem data de autorização.
- Impacto: pode exibir salário antes do corte, fora do contrato, em mês parcial ou
  diferente do snapshot físico preservado.
- Correção recomendada: reutilizar uma regra temporal única da projeção/materialização
  e priorizar a ocorrência física; cobrir os quatro cenários em teste.
- Fases reabertas: F2 e F5.

**A-02 — edição de participação sobrescreve snapshots históricos**

- Arquivo/linhas: `caixa/services_participacoes_servidores.py:211-220` e `:408-420`.
- Esperado: alterações cadastrais posteriores não alteram snapshots históricos.
- Encontrado: toda atualização chama `_preencher_snapshots` e copia novamente nome,
  identificador, vínculo, salário de referência e parâmetros do serviço atuais.
- Impacto: uma edição de escala ou troca de serviço reescreve o passado após mudança
  de nome, salário, vínculo ou configuração do cadastro.
- Correção recomendada: separar snapshots imutáveis de criação dos snapshots que
  legitimamente mudam numa troca explícita de serviço; adicionar teste “alterar
  cadastro, editar escala, comparar snapshots”.
- Fases reabertas: F1 e F4.

**A-03 — observações sensíveis aparecem no Admin**

- Arquivos/linhas: `caixa/admin.py:1955-1983` e
  `caixa/serializers_servidores.py:93-105`.
- Esperado: sem `view_dados_sensiveis_servidor`, observações e demais dados pessoais
  devem ser omitidos em API e Admin.
- Encontrado: a API oculta `notes`, mas `ServidorAdmin.get_fields()` não remove
  `observacoes`.
- Impacto: usuário `is_staff` com permissão de visualização do servidor, mas sem a
  permissão sensível, lê anotações confidenciais.
- Correção recomendada: aplicar a mesma classificação de campos em API, Admin,
  histórico e busca; ampliar o teste Admin com uma observação-sentinela.
- Fases reabertas: F1 e F3.

**A-04 — contratos de media type e idempotência estão incompletos**

- Arquivos/linhas: `caixa/views_planos_custos_recorrentes_api.py:343-403`,
  `:461-525`, `:596-699` e `caixa/views_clientes_api.py:34-49`.
- Esperado: POST/PUT com corpo recusam media type diferente de JSON com 415, e toda
  resposta de operação idempotente contém `Idempotency-Replayed`.
- Encontrado: as views recorrentes não usam `_is_json`, `JSONParser` exclusivo nem
  `parser_classes`; os parsers DRF padrão aceitam formulário/multipart. Respostas
  400 e 500 retornadas antes/depois da operação não recebem o header.
- Impacto: contrato HTTP diverge do plano e clientes/retries não conseguem distinguir
  execução original de replay em todos os resultados.
- Correção recomendada: centralizar parser/validação e construção da resposta
  idempotente; testar 400/415/500 e headers.
- Fases reabertas: F2 e F3.

**A-05 — OpenAPI válido, porém funcionalmente incompleto**

- Arquivos/linhas: `caixa/views_servidores_api.py:180-265`,
  `caixa/views_participacoes_servidores_api.py:114-200`,
  `caixa/views_custos_servidores_api.py:28-32` e
  `caixa/views_custos_fixos_api.py:868-875`.
- Esperado: schemas concretos, todos os status aplicáveis e headers de resposta.
- Encontrado: Servidores, Participações e Custos por Servidor publicam apenas
  respostas de sucesso; Custos Fixos continua com `OpenApiTypes.OBJECT`; nenhuma
  operação idempotente documenta `Idempotency-Replayed` na resposta. A inspeção do
  schema confirmou, por exemplo, somente 200/201/204 nos primeiros endpoints.
- Impacto: geração de clientes e teste de contrato não representam 400, 401, 403,
  404, 405, 415 ou headers reais, embora o validador não emita warning.
- Correção recomendada: declarar erros e headers concretos, gerar diff do OpenAPI e
  testá-lo como artefato versionado.
- Fases reabertas: F3, F5 e F7.

**A-06 — troca de runtime não invalida diretamente o estado dos hooks financeiros**

- Arquivos/linhas:
  `lib/config/use-api-runtime-sync.ts:15-54`,
  `components/dashboard/layout.tsx:51-57` e
  `features/financial-dashboard/hooks/financial-hook-state.ts:147-199`.
- Esperado: todo hook assina a troca, aborta imediatamente a requisição antiga,
  limpa o dado renderizado e inicia a consulta no runtime novo.
- Encontrado: somente um filho sem UI do layout assina o evento e limpa o cache. Os
  hooks chamam `getApiRuntimeKey()` durante render, mas não assinam o evento; a
  atualização do filho não força rerender dos irmãos que contêm os hooks.
- Impacto: em troca de runtime sem navegação/remount completo, dados ou resposta do
  tenant anterior podem permanecer na tela até outro rerender.
- Correção recomendada: fornecer runtime reativo por contexto/external store e
  incluí-lo na dependência de todos os recursos; testar troca sem reload com resposta
  antiga atrasada.
- Fases reabertas: F3, F5 e F6.

**A-07 — agregação de auditoria mistura atores**

- Arquivo/linhas: `caixa/services_auditoria_recorrencias.py:20-43` e `:79-116`.
- Esperado: o ator registrado identifica as ocorrências agregadas ou a agregação é
  separada por ator.
- Encontrado: ator não participa da chave; eventos equivalentes de usuários
  diferentes incrementam a mesma linha. O ator original permanece, enquanto o
  correlation ID é substituído pelo mais recente.
- Impacto: atribuição investigativa incorreta e trilha de auditoria ambígua.
- Correção recomendada: incluir identidade segura do ator na chave ou representar
  explicitamente agregação multiator sem atribuição falsa; testar dois atores.
- Fases reabertas: F2 e F7.

**A-08 — testes obrigatórios de concorrência, isolamento, integração e regressão
continuam ausentes**

- Arquivos/linhas: `caixa/test_servidores.py:152-279`, `:981-1048`,
  `caixa/test_custos_recorrentes.py:182-427`,
  `tests/e2e/live-backend-recurring.spec.ts:1-8` e
  `tests/e2e/live-backend-scale.spec.ts:1-57`.
- Esperado: toda a matriz das seções 11.2–11.8, E2E real e regressão completa.
- Encontrado: há concorrência real para alguns casos, mas faltam servidor versus
  participação, período versus escala, custo/serviço/valor manual versus recálculo,
  salário/plano versus materialização, duas instâncias do command, mesma UUID em
  atores e tenants distintos e rollback de falhas intermediárias. Os dois E2E reais
  estão condicionados a variáveis e não foram executados; a regressão de 1.258 testes
  continua sem término.
- Impacto: os bloqueios B-03/B-04 e o isolamento completo não são detectados pelo
  conjunto atual.
- Correção recomendada: completar a matriz e segmentar a suíte em CI sem substituir o
  gate integral.
- Fases reabertas: F1–F7.

#### 17.6.4 Achados médios e observações

**M-01 — constraint de Servidor não cobre todos os campos exclusivos de mensalista**

- `caixa/models_servidores.py:99-129` restringe salário/vínculo, período e dia, mas
  não impede no banco um diarista com datas contratuais, dia de pagamento ou
  autorização; `save()` em `:199-203` não chama `full_clean()`.
- O serviço atual valida corretamente, mas escrita ORM futura, fixture ou bulk pode
  criar estado inválido. Completar constraints e testes SQL antes do rollout. F1.

**M-02 — tabela de idempotência cresce sem retenção**

- `caixa/services_idempotencia.py` preserva uma linha por chave concluída e a
  migration cria índice por `criado_em`, mas não existe expurgo da tabela.
- É evolução futura não bloqueante funcionalmente, porém precisa de política,
  métrica, limite e command tenant-only antes de volume de produção. F2/F7.

**M-03 — validação do reset da Demo não comprova as estruturas novas**

- `tenancy/management/commands/resetar_tenant_demo.py:260-288` verifica somente
  tabelas essenciais de auth/sessão. `create_schema()` deve aplicar a cadeia atual e
  o `post_migrate` deve sincronizar permissões, mas o gate não confirma tabelas,
  constraints e codenames F1–F6.
- Adicionar introspecção e teste real do reset com models/permissões novos. F6/F7.

**M-04 — migrations são reversíveis apenas estruturalmente e podem manter locks**

- 0043–0045 têm dependências lineares corretas, não importam código mutável, não
  executam backfill nem acessam outros schemas. Nomes inspecionados são compatíveis
  com o limite do PostgreSQL.
- 0044 adiciona colunas com default e depois constraints/índices normais em tabelas
  existentes de custos e histórico. Isso pode reescrever/validar tabelas e manter
  lock por tenant. Reversão com dados apaga planos, auditoria, idempotência e
  metadados de ocorrências; somente a reversão vazia é aceitável.
- Exigir estimativa, canário, timeout, retomada e rollback lógico antes de aplicar.
  F2/F7.

**M-05 — flutuação do `<details>` é mais compatível com fragilidade de E2E do que
com race funcional comprovada**

- `tests/e2e/servers.spec.ts:1321-1325` clica imediatamente num texto de `<summary>`
  após uma carga mockada. O cenário passou isolado e não há atualização concorrente
  do item depois de carregado.
- Não foi reproduzida uma race de estado da aplicação, mas um único passe isolado
  não fecha o diagnóstico. Usar locator específico, esperar estabilidade e executar
  repetição/trace no ciclo conjunto. F5/F7.

**M-06 — causa exata da suíte superior a uma hora permanece inconclusiva**

- a descoberta atual contém 1.258 testes; as duas suítes novas somam 165 testes e,
  nas evidências anteriores, consumiram cerca de 650 segundos;
- bases multi-tenant criam schemas por classe, e
  `TenantTransactionTestCase` cria/migra/remove schema por teste concorrente;
- isso explica pressão de tempo, mas não há relatório por teste ou stack do timeout
  que permita afirmar ausência de deadlock. Instrumentar duração, dividir jobs e
  manter um job integral com timeout compatível. F7.

Observações comprovadas:

- `caixa` permanece somente em `TENANT_APPS`; as novas tabelas não existem no
  `public` nem nos tenants persistentes porque 0043–0045 não foram aplicadas;
- nenhum endpoint/service/frontend novo localizado aceita `tenant`, `schema` ou
  equivalente informado pelo cliente;
- cache, throttle, sessão, CSRF e paths de backup continuam tenant-aware;
- os três commands novos estão no registro tenant-only, chamam o guard e possuem
  teste de recusa em `public`;
- a Demo não recebeu permissões novas e a proteção transitiva inclui participação e
  dia trabalhado;
- projeção recorrente é somente leitura; materialização reutiliza `CustoFixo` e os
  fluxos canônicos, sem segundo ledger;
- idempotência usa hash canônico, ator e tabela no schema ativo; retry está limitado
  aos SQLSTATE `40001` e `40P01`;
- rateio de diaristas, maior resto, mensalista zero, escala derivada e compatibilidade
  de registros sem `workedDays` possuem implementação e testes focados, mas não
  superam os bloqueios de mutação externa e concorrência;
- os projetos de referência permaneceram limpos e somente leitura.

#### 17.6.5 Matriz de cobertura após a auditoria

| Requisito do plano | Código localizado | Testes localizados | Estado |
|---|---|---|---|
| models operacionais apenas no tenant | `config/settings.py`, migrations 0043–0045 | criação de tenant em testes | comprovado |
| nenhum tenant/schema vindo do cliente | URLs, serializers e services novos | cobertura explícita incompleta | parcial |
| commands recusam `public` | `tenancy/command_guards.py` e três commands | `CommandsRecorrentesEscopoTenantTests` | comprovado |
| Demo sem novas capacidades | perfis, sessão e demo policy | teste focado da Demo | comprovado |
| reset/tenant novo recebe tabelas e permissões | `create_schema`, `post_migrate` | sem asserção específica F1–F6 | parcial |
| cadastro, vínculo e histórico de servidor | models/services de servidores | suíte focada | parcial por M-01 |
| sigilo pessoal no Admin | serializers e Admin | teste não usa observação-sentinela | ausente por A-03 |
| sigilo salarial antes de agregações | filtros financeiros centrais | vários endpoints, não o relatório por servidor | ausente por B-01 |
| participação + escala em contrato final | migration 0045, serializers e views | domínio/API/E2E mockado | comprovado no fluxo principal |
| snapshots históricos imutáveis | model e service de participação | somente exclusão, não edição após mudança cadastral | ausente por A-02 |
| rateio reage a toda mudança do total | service de participação | sem alteração externa do custo | ausente por B-03 |
| redução de evento versus escala | model/event view/service | apenas cenários seriais | ausente por B-04 |
| plano/projeção/ocorrência canônicos | models e service recorrente | 98 testes descobertos | comprovado no fluxo focado |
| salário parcial/autorizado no relatório por servidor | selector do relatório | sem teste de corte/parcial/físico | ausente por A-01 |
| idempotência e replay | service e endpoints recorrentes | original/replay feliz | parcial por A-04/M-02 |
| auditoria agregada e atribuível | service de auditoria | mesmo ator/concorrência | parcial por A-07 |
| OpenAPI concreto e completo | decorators e serializers | geração sem warnings | parcial por A-05 |
| runtime reativo e cancelamento | runtime sync e hooks | troca de evento, não troca de runtime sem remount | ausente por A-06 |
| UI loading/vazio/erro/forbidden/read-only | views e componentes novos | E2E mockado parcial | parcial |
| desktop/mobile/teclado/overflow | componentes responsivos | guardrail e E2E real não executado | parcial |
| backup e restore UTF-8 em dois tenants | backup tenant-scoped UTF-8 | criação real; restore real pendente | parcial |
| migrations zero/upgrade/reverse/retomada | 0043–0045 | bancos temporários no caminho feliz | parcial |
| backend N/frontend N-1 e inverso | contratos atuais | nenhum ensaio concluído | ausente por B-05 |
| regressão integral e CI | 1.258 testes descobertos | execução integral expirou; guardrail de cache falha | ausente |

#### 17.6.6 Testes, comandos e evidências desta auditoria

Executados em modo de leitura:

- `git status --short`, `git diff --name-status`, `git diff --stat`,
  `git diff --numstat` e `git diff --check` nos dois projetos atuais;
- `venv\Scripts\python.exe manage.py check`: OK;
- `venv\Scripts\python.exe manage.py spectacular --validate --fail-on-warn
  --file NUL`: OK, sem warnings;
- inspeção programática do OpenAPI: confirmou status e headers incompletos;
- `manage.py makemigrations --check --dry-run`: OK, sem drift;
- `manage.py showmigrations caixa`, `tenant_command showmigrations` para os dois
  schemas persistentes e `migrate_schemas --plan`: somente leitura;
- consulta a `information_schema.tables`: nenhuma tabela F1–F6 em schema persistente;
- descoberta por `unittest.TestLoader`: 67 testes em `caixa.test_servidores`, 98 em
  `caixa.test_custos_recorrentes` e 1.258 na descoberta total;
- busca por `skip`, `expectedFailure` e `xfail`: três `skipTest` condicionais a
  PostgreSQL; nenhum expected failure/xfail localizado;
- `playwright test ... --list`: 14 testes nos quatro arquivos novos, sendo 12
  mockados e dois integrados condicionais;
- `pnpm exec eslint .`: OK;
- `pnpm exec tsc --noEmit`: OK;
- guardrails Demo runtime, responsividade e uso financeiro canônico: OK;
- guardrail de cache financeiro: falhou porque o runner Node não resolve o alias
  TypeScript `@/`; o problema já registrado permanece aberto;
- `git status --short` nos dois projetos de referência: limpo.

Ocorrências durante os comandos:

- a primeira tentativa de `manage.py check` usou o Python global sem Django e falhou;
  a execução correta com o interpretador do `venv` passou;
- nenhum teste Django ou Playwright foi reexecutado nesta auditoria. Foram auditados
  descoberta, código, condições de skip e as evidências de execução já registradas
  em 17.5; execução isolada anterior não foi aceita como substituta da regressão.
- a contagem anterior de 97 recorrentes está desatualizada: o código atual descobre
  98. A contagem de 67 testes de servidores permanece correta.

Estado persistente observado, sem escrita:

- `demo1` e `rh_teste` estão em `caixa.0040`; 0041–0045 aparecem não aplicadas;
- `public` não contém nenhuma das tabelas operacionais novas;
- nenhuma migration foi aplicada, revertida ou marcada durante esta auditoria;
- nenhum banco persistente foi acessado para escrita;
- nenhum commit, reset, descarte, deploy ou alteração de configuração foi realizado;
- o único arquivo alterado por esta auditoria é este registro técnico no plano.

Próximo gate:

1. corrigir e testar B-01 a B-05;
2. corrigir A-01 a A-07 e completar A-08;
3. executar migrations somente em banco descartável para upgrade, tenant novo,
   reset da Demo, reversão vazia, falha induzida e retomada;
4. executar E2E real, N/N-1, restore UTF-8 e regressão segmentada + integral;
5. repetir esta auditoria e somente então decidir se F7 pode iniciar.

### 17.7 Correções pré-F7 dos achados da auditoria 17.6 — 29/07/2026

Estado: `[PRONTO COM PENDÊNCIAS DE COMPROVAÇÃO NA F7]`.

Esta subseção substitui o estado operacional de bloqueio de 17.6, mas preserva
aquele registro histórico. As correções foram feitas somente nos worktrees SaaS.
Não houve migration aplicada, escrita em `demo1` ou `rh_teste`, deploy, commit,
reset ou modificação dos projetos de referência.

#### 17.7.1 Critério de status e política de atualização deste plano

- **corrigido**: regra implementada e com teste automatizado no banco temporário
  do runner ou no ambiente mockado do frontend;
- **parcialmente corrigido**: segurança e consistência preservadas, mas a prova de
  compatibilidade ou integração depende da F7;
- **pendente de comprovação na F7**: código e teste preparados, porém a evidência
  exige PostgreSQL descartável com migrations reais, Demo reset ou E2E real.

Ao encerrar cada fase, acrescentar: data, artefato avaliado, comandos exatos,
contagem de testes, resultado, evidências, desvios, risco residual e decisão
técnica. Um desvio não pode ser ocultado por skip, `xfail`, redução de assert ou
reclassificação de requisito obrigatório.

#### 17.7.2 Matriz dos 19 achados

| ID | Severidade | Causa raiz e correção | Arquivos principais | Teste/evidência | Status e risco residual |
| --- | --- | --- | --- | --- | --- |
| B-01 | Bloqueador | Autorização era posterior à agregação; política agora filtra ocorrência física antes de grupo e total. | `security_salarios.py`, `selectors_custos_servidores.py`, `views_custos_servidores_api.py` | `test_custos_sem_permissao_salarial_nao_revelam_ocorrencia_ou_total` | **corrigido**; repetir perfis e dados migrados na F7. |
| B-02 | Bloqueador | Admin podia excluir por caminho direto; participação é somente leitura, sem add/change/delete nem ação em massa. | `admin.py`, `test_servidores.py` | GET/POST de delete retornam 403 e `delete_selected` está ausente. | **corrigido**; Admin não é canal de mutação. |
| B-03 | Bloqueador | Custo distribuível não recalculava o grupo; save/delete bloqueiam e acionam o serviço de rateio na mesma transação. | `models_servico.py`, `services_participacoes_servidores.py`, `services_orcamentos.py`, `admin.py` | alteração, exclusão bloqueada e lote atômico. | **corrigido**; `QuerySet.update()` é proibido para esses campos. |
| B-04 | Bloqueador | Período e escala não tinham o mesmo lock; serviço de período bloqueia Evento antes de validar/salvar. | `services_participacoes_servidores.py`, `views_eventos_api.py`, testes | duas conexões PostgreSQL temporárias. | **corrigido**; repetir sob carga e schema migrado. |
| B-05 | Bloqueador | Contratos novos não eram mutuamente tolerantes; FE N trata 404/405 como indisponível e incompatibilidade insegura foi declarada. | serviço/hook de recorrência, E2E | Playwright mockado FE N/BE N-1. | **parcialmente corrigido**; FE N deve preceder BE N. |
| A-01 | Alto | Relatório usava histórico bruto; agora usa somente `CustoFixo` salarial materializado na competência. | `selectors_custos_servidores.py`, testes | ocorrência autorizada, ausente e sigilo. | **corrigido**; comprovar mês parcial pós-migration. |
| A-02 | Alto | Edição reaplicava snapshots; servidor é capturado na criação e serviço só muda em troca explícita. | `services_participacoes_servidores.py`, testes | imutabilidade e troca explícita. | **corrigido**; correção histórica futura requer fluxo auditado. |
| A-03 | Alto | Admin aplicava classificação sensível incompleta; campos, busca e histórico foram restringidos. | `admin.py`, testes | Admin restrito não recebe documento, observação, salário ou histórico. | **corrigido**; validar papéis reais por tenant. |
| A-04 | Alto | Parser aceitava formatos implícitos e erro não tinha header; parser/resposta idempotente foram centralizados. | `views_planos_custos_recorrentes_api.py`, testes | JSON inválido/vazio, texto, formulário, multipart e headers. | **corrigido**; validar CORS real na F7. |
| A-05 | Alto | Schema descrevia só sucesso/genérico; entradas, saídas, erros, parâmetros e header foram concretizados. | serializers e views API | Spectacular com `--validate --fail-on-warn`. | **corrigido**; anexar diff do OpenAPI na F7. |
| A-06 | Alto | Hook lia runtime sem reatividade; revisão de runtime/sessão, chave de cache e descarte de resposta obsoleta. | `api-runtime-events.ts`, `use-api-runtime-sync.ts`, `financial-hook-state.ts` | typecheck e Playwright A→B mockado. | **corrigido**; E2E real pendente. |
| A-07 | Alto | Chave de auditoria não incluía ator; identidade compõe a chave de agregação. | `services_auditoria_recorrencias.py`, testes | dois atores na mesma janela. | **corrigido**; validar em tenant migrado. |
| A-08 | Alto | Matriz não cobria limites reais; B-01..B-04, idempotência, auditoria, N/N-1 e runtime receberam testes. | testes backend e `tests/e2e/*.spec.ts` | grupos focados aprovados. | **pendente de comprovação na F7**; integral e E2E real obrigatórios. |
| M-01 | Médio | Constraint de mensalista aceitava combinações incompletas; model e `0043` exigem nulo integral para diarista. | `models_servidores.py`, `0043_servidores.py` | `makemigrations --check --dry-run`. | **pendente de comprovação na F7**; constraint não foi aplicada. |
| M-02 | Médio | Idempotência não tinha retenção; expurgo tenant-only, idempotente e dry-run foi criado. | `services_idempotencia.py`, command, testes | limites e validação do command. | **corrigido**; agendamento é decisão operacional futura. |
| M-03 | Médio | Reset Demo não validava F1–F6 completo; command valida tabelas, constraints e codenames. | `resetar_tenant_demo.py`, testes | teste preparado, execução excedeu janela local. | **pendente de comprovação na F7**; reset real é gate. |
| M-04 | Médio | Faltava protocolo de lock/rollback; `0043` foi corrigida ainda não aplicada e `0044/0045` revisadas. | `0043_servidores.py`, plano | revisão estática e check sem drift. | **pendente de comprovação na F7**; canary, locks, rollback e retomada. |
| M-05 | Médio | E2E tinha clique frágil em `<details>`; teste abre `summary` e afirma `open`. | `tests/e2e/servers.spec.ts` | Playwright isolado. | **corrigido**; E2E real é separado. |
| M-06 | Médio | Duração/estabilidade integral desconhecidas; CI deve segmentar sem substituir gate integral. | plano/CI futura | descoberta e grupos focados. | **pendente de comprovação na F7**; medir e concluir integral. |

#### 17.7.3 Correções detalhadas dos bloqueadores

**B-01 e A-01 — sigilo e semântica salarial.** A decisão foi centralizada em
`usuario_pode_acessar_custos_salariais()`. Sem permissão, o queryset fica vazio
antes de criar grupo, contador ou total. Com permissão, o relatório usa somente
ocorrência salarial física `CustoFixo`, na data de vencimento, e declara a origem
`MATERIALIZED_SALARY_OCCURRENCE`; histórico contratual não é apresentado como custo
realizado. A F7 deve repetir Administrador, Financeiro e Operacional; mensalista e
diarista; competência integral/parcial; consulta individual e agregada.

**B-02.** `ParticipacaoServidorEventoAdmin` declara read-only e remove
`delete_selected`; API e serviços de domínio são os únicos caminhos de criação,
edição, escala, valor manual e restauração. O teste usa usuário com a permissão de
delete do model e prova que GET e POST do endpoint de exclusão retornam 403.

**B-03.** Ordem global aplicada: **Evento → Servidor(es) por PK → Participação →
EventoCustoServico**. Save de custo bloqueia o Evento, impede troca da identidade
evento/serviço e recalcula o grupo; delete bloqueia a fonte se houver participação.
O Admin em lote processa os itens em `transaction.atomic()`: uma fonte protegida
reverte exclusões anteriores. Valores manuais são preservados pelo serviço.

**B-04.** `atualizar_evento_com_periodo()` bloqueia o Evento antes de validar o
novo intervalo. A view de eventos usa o serviço e a troca de escala usa o mesmo
primeiro lock. O teste concorrente usa conexões independentes do banco temporário e
afirma que nenhum dia persistido fica fora do período final.

**B-05 — N/N-1 e rollback.** Compatibilidade completa nos dois sentidos não é
segura: **BE N + FE N-1** pode omitir `authorizedMaterializationDate` e
`Idempotency-Key`; aceitar defaults reabriria materialização não autorizada e retry
sem idempotência. Essa combinação é expressamente proibida. **FE N + BE N-1** é
tolerado: 404/405 das rotas de planos torna somente o painel recorrente
indisponível, mantendo custos fixos legados. Ordem obrigatória: frontend N, validar
degradação, backend N. Não é necessária janela se essa ordem for seguida. Após BE
N, rollback para BE N-1 é proibido se houver planos/ocorrências novas; recuperar por
correção adiante ou janela controlada, sem tratar ocorrência materializada como
custo legado editável. F7 deve ensaiar ambos os sentidos.

#### 17.7.4 Hardening, Demo Pública, migrations e módulos futuros

Hardening obrigatório concluído: parser JSON estrito e respostas com
`Idempotency-Replayed`/`Access-Control-Expose-Headers`; retenção tenant-only de
idempotência; ator na auditoria; OpenAPI concreto; runtime reativo; e loader `@/`
do guardrail de cache. Nenhuma regra cria tabela operacional no schema `public` ou
chave global entre tenants.

O reset da Demo passou a exigir tabelas, constraints e permissões F1–F6. A Demo
continua fail-closed quando não possui capacidade salarial/operacional. Executar o
reset completo, incluindo dados sentinela, é pendência F7 e não foi compensado por
skip.

Somente `0043_servidores.py` foi alterada, pois está não aplicada e deve espelhar a
constraint do model; é seguro antes da primeira aplicação. `0044` e `0045` foram
revisadas sem mutação estrutural. Na F7: tenant canário em PostgreSQL descartável,
`lock_timeout`, `statement_timeout`, inspeção de locks, tenant novo, upgrade de
existente, reversão estrutural sem dados, falha induzida e retomada. Não usar
rollback de schema para apagar dados materializados. Novos escritores de custo devem
usar o serviço transacional, nunca `QuerySet.update()` nos campos distribuíveis.

#### 17.7.5 Evidências de execução pré-F7

Os comandos Django usaram somente o banco automaticamente criado/reutilizado pelo
runner (`test_rhsaas_dev`), nunca `demo1` ou `rh_teste`:

- `DEBUG=true venv\\Scripts\\python.exe manage.py check`: aprovado;
- `DEBUG=true venv\\Scripts\\python.exe manage.py makemigrations --check --dry-run`:
  aprovado, sem drift;
- `DEBUG=true venv\\Scripts\\python.exe manage.py spectacular --file NUL --validate --fail-on-warn`:
  aprovado;
- grupo focado anterior de servidores/participações, inclusive corrida período/escala:
  4 aprovados em 34,068 s; reexecução final isolada da corrida período/escala: 1
  aprovado em 44,211 s;
- segurança salarial, Admin e custo estruturado: 5 aprovados em 3,134 s; o lote
  atômico do Admin também foi aprovado isoladamente em 1,028 s;
- media type, auditoria e retenção de idempotência: 4 aprovados em 1,252 s;
- `corepack pnpm run check:financial-cache-guardrails`, `corepack pnpm run lint` e
  `corepack pnpm run typecheck`: aprovados no estado final;
- `corepack pnpm run build`: aprovado no estado final em 56,6 s (24 rotas);
- Playwright mockado de `<details>`, recorrência FE N/BE N-1 e troca Demo A→B passou
  isoladamente.

Desvios mantidos: a classe completa `caixa.test_servidores`, reset Demo focado e
regressão Django integral excederam a janela local; não são sucesso. Uma execução
composta de seis testes de servidor excedeu o limite externo de 64 s sem resultado
aproveitável; a corrida foi então reexecutada isoladamente e aprovada. Uma primeira
invocação de teste recorrente usou nome de classe inexistente e falhou antes de
executar aquele caso; a invocação corrigida acima aprovou os quatro testes. Não
foram criados skips/xfails; só existem skips condicionais preexistentes de
PostgreSQL.

#### 17.7.6 Gates antes de aprovar F7

1. repetir check, Spectacular, makemigrations check, lint, typecheck, guardrails e
   build no artefato candidato;
2. executar suites segmentadas completas e regressão Django integral, registrando
   coletados/aprovados/falhos/skips/duração;
3. aplicar migrations somente em PostgreSQL descartável, validar upgrade, tenant
   novo, Demo reset, rollback vazio, falha/retomada e locks;
4. executar E2E navegador→frontend→backend→PostgreSQL, incluindo runtime A→B,
   permissões, CORS/idempotência e N/N-1;
5. atualizar esta seção com as evidências e a decisão. Até lá, a implementação está
   pronta para aplicar migrations localmente em ambiente descartável e iniciar F7,
   mas F7 não está aprovada.

### 17.8 Registro F7 — validação operacional interrompida — 29/07/2026

Estado: `[REPROVADO — GATE DE REGRESSÃO INTEGRAL NÃO CONCLUÍDO]`.

#### Ambiente e pré-check

- banco exclusivamente descartável: `rhsaas_f7_20260729`, PostgreSQL 18.4 local;
- Python 3.13.1, Django 6.0.6, Node 24.15.0 e pnpm 11.17.0;
- backend no commit `c2c3fb0`, branch `feat/django-tenants-spike`, sem commit criado
  nesta etapa; worktree já continha 42 arquivos rastreados modificados e 33 não
  rastreados;
- `psql` não está no PATH, porém a conexão direta, sanitizada e isolada ao
  PostgreSQL local foi comprovada;
- os projetos de referência permanecem limpos; nenhum deploy, produção, `demo1` ou
  `rh_teste` persistente foi acessado para escrita.

#### Migrations, schemas e rollback estrutural

- `migrate_schemas --shared --noinput`: aprovado em 33,4 s. Embora o histórico de
  `caixa` seja marcado no `public` pelo router, a introspecção confirmou zero tabela
  `caixa_*` no schema público;
- tenant novo `f7_novo`: criado com domínio próprio e terminal `caixa.0045`;
- tenant migrado `f7_migrado`: reversão estrutural vazia 0045 → 0042 aprovada;
  as tabelas F1–F6 desapareceram, e a reaplicação 0043 → 0045 foi aprovada;
- `migrate_schemas --tenant --noinput` repetido: sem migrations pendentes;
- `makemigrations --check --dry-run`: aprovado, sem drift;
- `showmigrations caixa`, `tenant_command showmigrations --schema=f7_novo caixa` e
  `--schema=f7_migrado`: terminais 0043, 0044 e 0045 aplicados;
- nos dois schemas, tabelas, colunas, índices, permissões e todas as constraints
  obrigatórias foram verificadas. As cinco unicidades condicionais são índices
  parciais PostgreSQL, não linhas de `pg_constraint`.

#### Correção objetiva encontrada durante F7

Gate afetado: **Demo Pública / reset e recriação**.

O validador `resetar_tenant_demo` procurava todas as invariantes somente em
`pg_constraint`. Isso rejeitaria schemas corretos, porque as unicidades condicionais
`uq_servidor_documento_ci`, `uq_hist_salario_inicio`,
`uq_custo_fixo_plano_comp`, `uq_plano_salario_servidor` e
`uq_part_servidor_evento_serv` são índices parciais. A correção mínima passou a
aceitar constraint convencional ou índice nomeado, sem remover nenhuma validação.

- arquivos: `tenancy/management/commands/resetar_tenant_demo.py` e
  `tenancy/tests.py`;
- teste novo: `ResetarTenantDemoCommandTests.test_validacao_do_reset_aceita_unicidades_parciais_postgresql`;
- primeira execução revelou alias SQL reservado; corrigido para `pgc` e repetido;
- execução corrigida: 1 teste aprovado em 94,868 s;
- ciclo real F7: provisionamento descartável de `demo1`/`demo2`, ocupação de
  `demo2`, expiração com intervalo válido e `resetar_tenant_demo`: aprovado em
  94,9 s. Schema recriado, migrations/seeds validados e slot voltou a `livre`.

#### Gates aprovados antes da interrupção

- `manage.py check`: aprovado;
- `manage.py spectacular --file NUL --validate --fail-on-warn`: aprovado;
- OpenAPI continua sem warnings; nenhum artefato persistente foi gerado;
- Demo reset/recriação, sincronização das permissões requeridas e validação de seed:
  aprovados no banco F7;
- novo tenant, tenant migrado, repetição de migrations e reversão estrutural vazia:
  aprovados.

#### Gate reprovado e motivo de interrupção

O comando obrigatório

```text
DEBUG=true DATABASE_URL=<banco-F7> python manage.py test --noinput -v 1
```

foi executado integralmente no banco de teste derivado do F7. Após mais de 66
minutos, sem saída de sucesso, falha ou progresso, foi encerrado. O comportamento
repete o baseline F0, que também não concluiu a suíte monolítica em 3.604,1 s.
Não há causa de código isolada comprovada por essa execução; portanto nenhuma
refatoração ou alteração funcional foi feita para contornar a duração.

Conforme a ordem obrigatória da F7, os gates posteriores não foram promovidos:
Playwright completo com backend real, validação integrada multi-tenant/backup/restore,
matriz N/N-1 real e homologação permanecem **não executados nesta F7**. Testes
focados e mockados anteriores não substituem esses gates.

Próximo gate: diagnosticar e tornar observável a regressão integral sem reduzir
cobertura; executar novamente até resultado explícito e só então reiniciar a F7 a
partir do gate de backend.

### 17.9 Diagnóstico e retomada da regressão Django — 29–30/07/2026

Estado: `[PENDENTE — CAIXA APROVADO; TENANCY INTERROMPIDO; REGRESSÃO INTEGRAL PENDENTE]`.

Esta subseção preserva 17.8 como registro histórico e recupera o estado deixado
pelo diagnóstico antes do reinício do notebook. A recuperação foi concluída em
01/08/2026. Não houve commit, deploy, migration em banco persistente nem escrita
em `demo1`, `rh_teste` ou produção. O frontend SaaS confirmado para este plano é
o worktree irmão `rhsaasfront`; nenhum arquivo desse worktree foi alterado pelo
diagnóstico da regressão Django.

#### Descoberta, falso diagnóstico de travamento e falhas reais

- a descoberta registrou 1.270 testes: 1.095 em `caixa` e 175 em `tenancy`;
- `-v 1` ocultava tanto a preparação inicial do banco/schema quanto o progresso
  individual. Com `-v 2`, nomes de testes, CPU acumulada e SQL continuaram
  avançando; o setup podia consumir cerca de dois minutos antes do primeiro teste;
- as fotografias de processos e PostgreSQL registraram zero locks aguardados. Não
  foi encontrado deadlock do runner, espera por Redis/Celery, HTTP externo ou outro
  serviço; testes de concorrência, migrations, reset e semeadura de schemas explicam
  parte relevante da duração;
- falhas determinísticas reais foram reproduzidas antes de qualquer correção: duas
  consultas lazy no contrato de dimensão financeira; relatório salarial de teste
  sem ocorrência física/contrato/autorização; contratos HTTP, permissões, Demo,
  recorrência, distribuição e CSV desatualizados; expectativas conflitantes de
  reaprovacão; e a ausência de classificação tenant-only de um command mutável;
- o primeiro `caixa` completo depois da triagem terminou com 1.095 testes em
  2.094,592 s, 49 falhas e 11 erros. Esse resultado foi usado apenas para agrupar e
  corrigir causas; não foi promovido como aprovação.

#### Alterações do diagnóstico que sobreviveram

O histórico local da sessão e o diff atual comprovam alterações em:

- `caixa/demo_policy.py`: `allow_lazy` permite impedir carregamento implícito de
  relações sem alterar a verificação completa nos fluxos de escrita da Demo;
- `caixa/serializers_financiamentos.py`: parcelas e movimentações publicam flags da
  Demo somente a partir de relações já carregadas;
- `caixa/test_servidores.py`: o cenário salarial passou a criar contrato,
  autorização e ocorrência física canônica;
- `caixa/tests.py`: contratos passaram a validar flags da Demo, capacidades,
  completude financeira, recorrência/idempotência, distribuição por servidor,
  imutabilidade após aprovação e CSV com parser real e filtros rastreáveis;
- `caixa/serializers_custos_fixos_api.py`: o schema OpenAPI passou a declarar
  `isSeed` e `isReadOnly` opcionais nas ocorrências materializadas;
- `caixa/tests_event_number_tenant.py`: a reaprovacão passou a ser comprovadamente
  rejeitada sem duplicar evento ou movimentações;
- `tenancy/command_guards.py`: o command
  `expurgar_requisicoes_idempotentes_recorrencia` foi classificado como tenant-only.

As alterações experimentais que aceitavam reaprovacão em `caixa/models.py` e
`caixa/services_cadastros.py` foram revertidas durante o próprio diagnóstico. O
segundo arquivo está limpo; o diff ainda existente em `caixa/models.py` é anterior
ao diagnóstico e não deve ser atribuído a ele.

#### Testes focados e segmentados recuperados

- o caso de lazy loading falhou isoladamente antes da correção e depois passou; a
  classe `DatasTests` passou com 52 testes em 58,622 s;
- 21 contratos focados de Eventos/Despesas passaram em 67,088 s;
- o cenário salarial passou isoladamente, `ServidoresDominioTests` passou com 33
  testes em 105,494 s e `caixa.test_servidores` passou com 74 testes em 453,593 s;
- `FiltrosHtmlTests` primeiro terminou com 440 testes em 540,132 s e 10 falhas;
  depois das correções localizadas, repetiu os 440 em 556,584 s com `OK`;
- o conjunto relacionado de orçamento, receita e numeração passou com 112 testes em
  239,751 s; os quatro cenários finais de imutabilidade/reaprovacão passaram em
  246,093 s; a expectativa final de mensagem passou isoladamente em 46,559 s.

#### Evidência terminal de `caixa`

O registro local da sessão preservou a saída terminal e o código do processo:

```text
Ran 1095 tests in 2138.781s

OK
Destroying test database for alias 'default' ('test_rhsaas_diag_isolado_f7_20260729')...
Exit code: 0
```

Portanto, o gate segmentado do aplicativo `caixa` está aprovado. Isso não equivale
à regressão Django integral nem aprova a F7.

#### Estado comprovado de `tenancy`

Classificação: **B — tenancy foi interrompido**.

- a execução descobriu 175 testes e progrediu com `-v 2`;
- houve uma falha real em
  `TenantCommandGuardTests.test_todos_commands_customizados_estao_classificados`,
  com `unclassified=expurgar_requisicoes_idempotentes_recorrencia`;
- a correção mínima foi aplicada em `tenancy/command_guards.py` enquanto a execução
  já reprovada continuava, mas o caso corrigido ainda não foi reexecutado;
- o último snapshot preservado contava 152 linhas de teste. O último caso iniciado
  era
  `OcuparTenantDemoCommandTests.test_permite_ocupar_slot_especifico`, sem resultado
  `ok`/falha registrado para ele;
- não existe resumo `Ran 175 tests`, duração final, `OK` nem código de saída. O
  reinício interrompeu o runner antes da validação isolada e da repetição completa
  de `tenancy`.

Os diretórios temporários `rhsaas_diag_caixa_gate_f7_20260729`,
`rhsaas_diag_tenancy_gate_f7_20260729` e
`rhsaas_diag_caixa_final_pass_f7_20260729`, bem como seus `stdout.log`,
`stderr.log` e `exitcode.txt`, não sobreviveram. As evidências acima foram
recuperadas do registro local da sessão Codex
`sessions/2026/07/29/rollout-2026-07-29T12-49-13-019fae90-cbd0-7f03-af89-bd613a8f6ad3.jsonl`;
nenhum resultado terminal ausente foi inferido.

#### Bancos descartáveis e limpeza

A consulta inicial encontrou somente:

```text
rhsaas_diag_isolado_f7_20260729  size_bytes=8102415  active_sessions=0
```

Não restavam `test_rhsaas_diag_*`, `rhsaas_f7_20260729` ou outros bancos com os
prefixos F7/diagnóstico consultados. Depois da identificação e da confirmação de
zero sessões, `rhsaas_diag_isolado_f7_20260729` foi removido. A verificação posterior
retornou zero bancos `^(test_)?rhsaas_(diag|f7)`. O banco era descartável e não é
recuperável; pode ser recriado para a retomada. Nenhum banco persistente da
aplicação foi removido ou alterado.

#### Estado do Git recuperado

Backend `rhsaas`, branch `feat/django-tenants-spike`, commit `c2c3fb0`:

- `git status --short`: 79 entradas, sendo 46 arquivos rastreados modificados e 33
  não rastreados; o próprio plano permanece não rastreado;
- `git diff --stat`: 46 arquivos rastreados, 2.491 inserções e 168 remoções;
- `git diff --check`: código de saída zero, sem erro de whitespace; somente avisos
  de futura normalização CRLF→LF em sete arquivos rastreados.

Frontend `rhsaasfront`, branch `main`, commit `8a19e77`:

- `git status --short`: 51 entradas, sendo 32 arquivos rastreados modificados e 19
  não rastreados;
- `git diff --stat`: 32 arquivos rastreados, 1.177 inserções e 256 remoções;
- `git diff --check`: código de saída zero.

Nenhuma dessas alterações foi commitada ou descartada. Os 51 registros do frontend
são implementação F1–F6 anterior e não foram tocados por este diagnóstico.

#### Veredito e próximo comando

Veredito permitido: **Caixa aprovado; tenancy interrompido e regressão integral
pendente**.

F7, E2E integrado, matriz N/N-1 real, homologação, commit e produção continuam
pendentes. A retomada deve validar primeiro a correção que não chegou a ser
reexecutada e só então repetir o aplicativo `tenancy`, com saída detalhada e logs.
No PowerShell, a partir da raiz do backend, o próximo comando exato é:

```powershell
$diagDir = Join-Path $env:LOCALAPPDATA 'Temp\rhsaas_diag_tenancy_resume_f7_20260730'
New-Item -ItemType Directory -Force -Path $diagDir | Out-Null
$env:DEBUG = 'true'
& .\venv\Scripts\python.exe -u manage.py test tenancy.tests.TenantCommandGuardTests.test_todos_commands_customizados_estao_classificados --noinput -v 2 2>&1 |
    Tee-Object -FilePath (Join-Path $diagDir 'isolated.stdout.log')
$isolatedExitCode = $LASTEXITCODE
Set-Content -LiteralPath (Join-Path $diagDir 'isolated.exitcode.txt') -Value $isolatedExitCode
if ($isolatedExitCode -eq 0) {
    & .\venv\Scripts\python.exe -u manage.py test tenancy --noinput -v 2 2>&1 |
        Tee-Object -FilePath (Join-Path $diagDir 'stdout.log')
    $tenancyExitCode = $LASTEXITCODE
    Set-Content -LiteralPath (Join-Path $diagDir 'exitcode.txt') -Value $tenancyExitCode
    exit $tenancyExitCode
}
exit $isolatedExitCode
```

O `.env` atual aponta para `rhsaas_dev`; o runner Django cria e destrói somente o
banco derivado `test_rhsaas_dev`. Não executar a regressão integral antes de obter
para `tenancy` resumo terminal, 175 testes, duração, `OK` e código zero.

### 17.10 Retomada e aprovação do gate segmentado `tenancy` — 01/08/2026

Estado: `[TENANCY APROVADO — REGRESSÃO DJANGO INTEGRAL PRONTA, MAS NÃO EXECUTADA]`.

Esta retomada partiu exatamente do estado de 17.9. O módulo `caixa` não foi
reexecutado, a regressão Django integral não foi iniciada e nenhum gate de
frontend, Playwright, E2E ou deploy foi executado. A F7 permanece **não aprovada**.
Não houve commit nem escrita em `demo1`, `rh_teste`, produção ou banco persistente.

#### PostgreSQL descartável e isolamento

- banco-base exclusivo: `rhsaas_diag_tenancy_resume_f7_20260801_run01`;
- banco derivado criado e destruído pelo Django em cada runner:
  `test_rhsaas_diag_tenancy_resume_f7_20260801_run01`;
- PostgreSQL 18.4 estritamente local, host `localhost`, porta `5433`, resolvido
  somente para `127.0.0.1` e `::1`; nenhuma senha foi registrada;
- o nome não corresponde a `rhsaas_dev`, `demo1`, `rh_teste`, `postgres` ou outro
  destino persistente. A validação prévia confirmou zero sessões no banco-base,
  ausência de conexão de produção e possibilidade de remoção integral ao final;
- o `.env` persistente continuou apontando para `rhsaas_dev`; cada processo de
  teste recebeu `DATABASE_URL` sobrescrita somente no ambiente do runner.

#### Guardrail isolado obrigatório

Comando executado antes do módulo:

```powershell
$env:DEBUG = 'true'
.\venv\Scripts\python.exe -u manage.py test tenancy.tests.TenantCommandGuardTests.test_todos_commands_customizados_estao_classificados --noinput -v 2
```

Resultado: 1 teste executado em 71,746 s, `OK`, código de saída 0. Início em
`2026-08-01T15:39:33.9644975-03:00` e término em
`2026-08-01T15:41:28.0764075-03:00`. A correção já existente em
`tenancy/command_guards.py`, que classifica
`expurgar_requisicoes_idempotentes_recorrencia` como tenant-only, foi validada sem
nova alteração de aplicação.

#### Primeira execução completa e falhas reais

A primeira execução de `manage.py test tenancy --noinput -v 2` descobriu e
executou 175 testes em 3.833,321 s. Resultado terminal:

```text
Ran 175 tests in 3833.321s

FAILED (failures=2)
Exit code: 1
```

Foram 173 aprovados, 2 falhas, 0 erros e 0 skips. As duas falhas ficaram na classe
`ResetarTenantDemoCommandTests`:

- `test_dry_run_nao_altera_banco`: `Cliente.objects.count()` retornou 2, enquanto
  o teste esperava 1;
- `test_reset_de_demo2_nao_altera_demo3`: a mesma divergência `2 != 1` no schema
  `demo3`.

Ambas foram reproduzidas isoladamente antes da correção, sem dependência de ordem:

- `test_dry_run_nao_altera_banco`: 1 teste em 81,998 s, `FAILED`, saída 1;
- `test_reset_de_demo2_nao_altera_demo3`: 1 teste em 152,791 s, `FAILED`, saída 1.

A causa foi classificada como **teste desatualizado em relação ao contrato já
aprovado de seed protegido**, não defeito da aplicação, ambiente ou limpeza entre
tenants. `provisionar_pool_demo` cria exatamente um `Cliente` com
`demo_seed_key`; o helper do próprio teste cria mais um `Cliente` comum. Esse
contrato foi introduzido pelo commit histórico `240817c`, posterior aos asserts
que ainda esperavam um único registro.

#### Correção mínima e retestes

Somente `tenancy/tests.py` foi ajustado nos dois cenários: a expectativa passou a
exigir exatamente 2 clientes e, adicionalmente, exatamente 1 cliente seed e 1
cliente comum. Nenhum assert foi removido ou reduzido e nenhum código de aplicação,
timeout, skip ou xfail foi alterado.

Retestes pós-correção:

- `test_dry_run_nao_altera_banco`: 1 teste em 76,567 s, `OK`, saída 0;
- `test_reset_de_demo2_nao_altera_demo3`: 1 teste em 148,638 s, `OK`, saída 0;
- classe `ResetarTenantDemoCommandTests`: 12 testes em 989,575 s, `OK`, saída 0;
- módulo `tenancy`: 175 testes em 3.801,045 s, `OK`, saída 0.

Na execução final foram descobertos 175, executados 175, aprovados 175, falhas 0,
erros 0 e skips 0. O último teste iniciado e concluído foi
`ResetarTenantDemoCommandTests.test_validacao_do_reset_aceita_unicidades_parciais_postgresql`.
A execução começou em `2026-08-01T17:20:30.3941405-03:00` e terminou em
`2026-08-01T18:24:30.1243098-03:00`; duração interna Django de 3.801,045 s e
duração de parede, incluindo criação/destruição do banco, de aproximadamente
3.839,730 s.

#### Monitoramento e logs persistentes

Os logs ficaram fora do banco e fora do repositório em
`C:\Users\Davif\.codex\diagnostics\rhsaas_f7_tenancy_resume_20260801_run01`.
Foram preservados stdout, stderr, código de saída, início, término e PID para cada
runner. Arquivos principais:

- guardrail: `isolated.stdout.log`, `isolated.stderr.log`,
  `isolated.exitcode.txt`;
- primeira execução completa: `stdout.log`, `stderr.log`, `exitcode.txt`;
- reproduções e retestes: prefixos `failure_dryrun_isolated_*` e
  `failure_isolation_isolated_*`;
- classe corrigida: prefixo `resetar_class_afterfix`;
- execução final aprovada: `tenancy_afterfix.stdout.log` (14.834 bytes,
  SHA-256 `3BB9B94C4E8A3572DF97B14B3C59638739B0A9CA0A662EAFCA7B7DE1A86E63F1`),
  `tenancy_afterfix.stderr.log` (88.296 bytes, SHA-256
  `C1C36F8E096A3A353000275BD313D56A86E6247B79807B9F4E10BE81AFA717EC`),
  `tenancy_afterfix.exitcode.txt`, `tenancy_afterfix.started_at.txt` e
  `tenancy_afterfix.finished_at.txt`.

O PowerShell marcou linhas nativas de stderr com metadados `NativeCommandError`,
mas os logs preservam integralmente os nomes dos testes e o resumo Django. Durante
as execuções, o log progrediu, a CPU acumulada cresceu continuamente e consultas
periódicas a `pg_stat_activity`/`pg_locks` mostraram somente conexão local ao banco
derivado, SQL de migrations/setup e zero locks não concedidos. Nenhuma execução
foi interrompida por duração.

#### Limpeza, arquivos e Git

Ao final, o banco de teste derivado já havia sido destruído pelo Django. A consulta
encontrou somente o banco-base descartável, com zero sessões. Foram emitidos drops
por nome exato para o derivado e para o base; a verificação posterior retornou zero
bancos residuais contendo o prefixo desta retomada. `rhsaas_dev` permaneceu
presente e intocado. Os bancos descartáveis removidos não são recuperáveis.

Arquivos alterados nesta retomada:

- `tenancy/tests.py`, somente nos dois contratos de contagem seed/comum;
- `PLANO_ATUALIZACAO_PARIDADE_FUNCIONAL_MULTITENANT.md`, com esta seção 17.10.

`tenancy/command_guards.py` já estava corrigido antes da retomada e apenas foi
validado. O frontend irmão `rhsaasfront` não foi alterado. O estado final do Git
continua sem commit; o plano permanece não rastreado. No backend, branch
`feat/django-tenants-spike`, commit `c2c3fb0`, `git status --short` registra 79
entradas: 46 rastreadas modificadas e 33 não rastreadas. `git diff --stat` registra
46 arquivos rastreados, 2.509 inserções e 170 remoções; o plano não rastreado não
entra nessa estatística. `git diff --check` termina com código zero e sem erro de
whitespace, mantendo apenas sete avisos preexistentes de futura normalização
CRLF→LF.

No frontend, branch `main`, commit `8a19e77`, o estado permaneceu idêntico ao
pré-check: 51 entradas (32 rastreadas modificadas e 19 não rastreadas), 32 arquivos
no `diff --stat`, 1.177 inserções, 256 remoções e `git diff --check` com código zero.

#### Veredito e próximo gate

Veredito permitido: **Tenancy aprovado; regressão integral pronta para execução**.

Próximo gate: regressão Django integral, que ficou deliberadamente **não executada**
nesta etapa. A aprovação segmentada de `caixa` e `tenancy` ainda não aprova a F7;
frontend, Playwright e demais gates posteriores também permanecem pendentes.

### 17.11 Regressão Django integral — 01/08/2026

Estado: `[REGRESSÃO DJANGO INTEGRAL APROVADA — F7 AINDA NÃO CONCLUÍDA]`.

Esta etapa partiu do estado aprovado de 17.10 e executou exclusivamente a regressão
Django integral. Não foram executados frontend, Playwright, E2E ou gates posteriores;
não houve commit, deploy, acesso a produção nem escrita em banco persistente. A F7
permanece não concluída até a execução dos gates posteriores previstos.

#### PostgreSQL descartável e comando

- banco-base exclusivo: `rhsaas_f7_full_regression_20260801_run01`;
- banco derivado do runner: `test_rhsaas_f7_full_regression_20260801_run01`;
- PostgreSQL 18.4 local, host `localhost` resolvido somente para `127.0.0.1` e
  `::1`, porta `5433`; nenhuma senha foi registrada;
- o nome foi validado previamente como descartável e distinto de `rhsaas_dev`,
  `demo1`, `rh_teste`, `postgres` e produção, e sua remoção final era possível;
- o `.env` persistente permaneceu apontando para `rhsaas_dev`; a sobrescrita de
  `DATABASE_URL` ocorreu somente no ambiente dos runners.

Comando integral, sem labels de aplicativo:

```powershell
$env:DEBUG = 'true'
.\venv\Scripts\python.exe -u manage.py test --noinput -v 2
```

#### Primeira execução integral e diagnóstico

A primeira execução começou em `2026-08-01T18:34:33.7596538-03:00` e terminou
em `2026-08-01T20:15:20.7043309-03:00`. Foram descobertos e executados 1.270
testes em 6.023,328 s internos e aproximadamente 6.046,945 s de parede. Resultado
terminal: `FAILED (failures=6)`, com 1.264 aprovados, 6 falhas, 0 erros e 0 skips.
O wrapper criou `exitcode.txt` vazio; portanto, o código bruto dessa primeira
execução não foi capturado, embora o terminal `FAILED` seja inequívoco.

As seis falhas foram:

1. `AtivacaoMensalistasCommandTests.test_execucao_e_repeticao_sao_idempotentes_e_auditadas`;
2. `ServidoresApiTests.test_custos_sem_permissao_salarial_nao_revelam_ocorrencia_ou_total`;
3. `ServidoresApiTests.test_salario_aparece_em_custo_fixo_sem_linha_editavel_duplicada`;
4. `ServidoresDominioTests.test_relatorio_separa_salario_e_participacao`;
5. `TenantIsolationInfrastructureTests.test_cria_dois_tenants_e_dominios`;
6. `ConcorrenciaSalarialPostgreSQLTests.test_ativacao_simultanea_cria_um_plano_e_uma_ocorrencia`.

Cada falha foi reproduzida isoladamente. As cinco falhas salariais continuaram
falhando em banco limpo e foram classificadas como **defeito da aplicação exposto
pela virada de julho para agosto**: a competência explícita de julho era descartada
em favor de `timezone.localdate()`, e a proteção `beforePlanCreation` impedia a
materialização retroativa do histórico salarial. A falha de infraestrutura passou
isoladamente em banco derivado limpo (1 teste em 48,705 s, `OK`, saída 0) e foi
classificada como **dependência de ordem/limpeza do teste**: `FastTenantTestCase`
preserva intencionalmente `tenant_app_tests`, mas o teste comparava os conjuntos
globais completos de tenants e domínios.

#### Correções mínimas e retestes

Foram aplicadas somente as correções necessárias:

- `caixa/services_custos_recorrentes.py`: aceita e respeita competência explícita
  de materialização; mantém `beforePlanCreation` para planos manuais, mas não
  bloqueia a origem salarial, inclusive na recuperação de competências ausentes;
- `caixa/services_servidores.py`: propaga a data de vigência salarial;
- `caixa/services_ativacao_mensalistas.py`: propaga a data de corte da ativação;
- `tenancy/tests.py`: restringe a asserção aos dois schemas/domínios criados pelo
  cenário, sem presumir que tabelas globais estejam vazias.

Não foram removidos testes ou asserts, nem usados skip, xfail ou aumento de timeout.
Após a correção final, os cinco testes salariais isolados passaram, respectivamente,
em 0,791 s, 1,291 s, 0,944 s, 0,829 s e 37,441 s, todos com saída 0. Em seguida,
passaram as cinco classes afetadas:

- `AtivacaoMensalistasCommandTests`: 4 testes em 1,588 s;
- `ServidoresApiTests`: 23 testes em 29,316 s;
- `ServidoresDominioTests`: 33 testes em 39,614 s;
- `TenantIsolationInfrastructureTests`: 5 testes em 70,087 s;
- `ConcorrenciaSalarialPostgreSQLTests`: 2 testes em 77,672 s.

Todas terminaram com `OK` e código 0 antes da repetição integral.

#### Regressão integral final

A repetição integral começou em `2026-08-01T20:41:38.9294910-03:00` e
terminou em `2026-08-01T22:21:49.2416877-03:00`. Resultado final:

```text
Found 1270 test(s).
Ran 1270 tests in 5979.140s

OK
```

Foram 1.270 descobertos, 1.270 executados, 1.270 aprovados, 0 falhas, 0 erros e
0 skips. A duração interna foi 5.979,140 s e a duração de parede, incluindo
criação e destruição do banco, aproximadamente 6.010,312 s. O último teste
iniciado e concluído foi
`ResetarTenantDemoCommandTests.test_validacao_do_reset_aceita_unicidades_parciais_postgresql`.

O wrapper voltou a criar `exitcode.txt` vazio. Assim, o **código bruto não foi
capturado**; não se atribui valor observado ao arquivo. O terminal completo `OK`,
a conclusão de todos os testes, a destruição normal do banco e a ausência de
traceback posterior comprovam o encerramento aprovado do runner.

#### Monitoramento, logs e limpeza

As evidências persistentes ficaram fora do banco e do repositório em
`C:\Users\Davif\.codex\diagnostics\rhsaas_f7_full_regression_20260801_run01`.
Arquivos principais:

- primeira integral: `stdout.log`, `stderr.log`, `started_at.txt`,
  `finished_at.txt`, `command.txt`, `monitor.log` e `exitcode.txt` vazio;
- reproduções: subdiretório `isolated`;
- isolados corrigidos: `postfix_isolated_round2`;
- classes corrigidas: `postfix_classes`;
- integral final: subdiretório `full_rerun_after_fix`, com `stdout.log`,
  `stderr.log`, timestamps, comando, PIDs, monitor e `exitcode.txt` vazio;
- limpeza: `database_cleanup.txt`.

SHA-256 dos logs da integral final: `stdout.log`
`3E999448646D44798262568BC9B8D4AF617F43122BC38503C18252B48D9A1A9F` e
`stderr.log` `A60DF836834BEFB767F3D8C6D6611577A0D5B7D4F76D481853741B746FE8F626`.
Durante a execução houve progresso contínuo de log e CPU; as amostras do
PostgreSQL mostraram uma conexão exclusiva ao banco derivado, SQL ativo e zero
locks não concedidos. Não houve interrupção por duração.

O Django destruiu o banco derivado ao final. A limpeza por nomes exatos confirmou
zero conexões restantes, removeu o banco-base e terminou com código 0. A consulta
posterior retornou zero bancos residuais do prefixo; `rhsaas_dev` permaneceu
presente e intocado. Nenhum banco persistente foi removido.

#### Arquivos, Git e próximo gate

Arquivos alterados nesta etapa: `caixa/services_custos_recorrentes.py`,
`caixa/services_servidores.py`, `caixa/services_ativacao_mensalistas.py`,
`tenancy/tests.py` e este plano. O frontend irmão `rhsaasfront` não foi alterado.
O estado Git permaneceu sem commit; a fotografia final de `git status --short`,
`git diff --stat` e `git diff --check` está preservada junto aos diagnósticos.
Na branch `feat/django-tenants-spike`, commit `c2c3fb0`, `git status --short`
registra 79 entradas: 46 arquivos rastreados modificados e 33 não rastreados.
`git diff --stat` registra 46 arquivos rastreados, 2.521 inserções e 173
remoções; arquivos não rastreados, inclusive este plano e três serviços
ajustados, não entram nessa estatística. `git diff --check` terminou com código
zero e sem erro de whitespace, mantendo somente sete avisos preexistentes de
futura normalização CRLF→LF.

Veredito permitido: **Regressão Django integral aprovada; F7 pronta para os gates
posteriores**.

Próximo gate: os gates posteriores da F7 previstos no plano. Eles não foram
executados automaticamente nesta etapa, e a regressão aprovada isoladamente não
declara a F7 completa.

### 17.12 Encerramento da F7 — 02/08/2026

Estado: `[F7 APROVADA — PRONTA PARA CRIAÇÃO DOS COMMITS E HOMOLOGAÇÃO]`.

Esta etapa retomou exclusivamente os gates posteriores deixados pendentes em
17.11. Não foram repetidos migrations, rollback, `caixa`, `tenancy` ou a regressão
Django integral de 1.270 testes, pois nenhuma correção desta etapa alterou backend,
migrations, tenancy ou modelos. Não houve implementação funcional nova,
refatoração, commit, deploy, acesso a produção ou escrita em `demo1`, `rh_teste` ou
banco persistente.

Todas as evidências foram preservadas fora dos repositórios em
`C:\Users\Davif\.codex\diagnostics\rhsaas_f7_remaining_gates_20260801_run01`.

#### Ambiente local descartável

- stack N: PostgreSQL 18.4 local em `localhost`/`::1`, porta `5433`, banco
  `rhsaas_f7_remaining_20260801_run01`, backend `127.0.0.1:8000` e frontends
  locais; tenants de validação `f7a`, `f7b`, `f7restorea` e `f7restoreb`;
- stack N-1: banco separado `rhsaas_f7_nminus1_20260802_run01`, backend N-1 em
  `127.0.0.1:8001` e tenant `f7n1`;
- os dois nomes foram previamente confirmados como não persistentes, não
  produtivos e removíveis. A senha não foi gravada em logs ou no plano;
- `demo1` e `rh_teste` não foram usados. Todos os requests de escrita foram
  direcionados aos tenants descartáveis acima;
- a preparação da stack N terminou com código 0 em 45,425 s. A criação/migração
  do tenant N-1 terminou com código 0 em 17,492 s, após migrations shared em
  15,358 s.

#### Gate 1 — frontend

O gate final executou 17 comandos: ESLint, TypeScript, runtime da Demo, filtros
globais, uso financeiro canônico, cache, overview, contratos de listas e paridade,
responsividade, serviços por hora, snapshots de orçamento, layout/filtro/contrato/
boundary/acessibilidade do Dashboard e build de produção.

Resultado final: 17/17 comandos aprovados, código 0, 112,064 s, todos os arquivos
`stderr` vazios. O build gerou 24 rotas sem warning crítico, erro de hidratação,
React ou Next.js. Evidências principais: `gate1_frontend_final/results.tsv`,
`gate1_frontend_final/exitcode.txt`, `gate1_frontend_final/duration_seconds.txt` e
os pares `*.stdout.log`/`*.stderr.log` de cada comando.

Dois guardrails estavam desatualizados em relação ao contrato já aprovado e foram
ajustados sem enfraquecimento: o sincronizador aninhado do runtime deve observar a
URL e resetar estado, enquanto o hook de URL continua sem `useSearchParams`; e o
service recorrente pode importar `ApiError` exclusivamente para reconhecer a
degradação 404/405 do backend N-1.

#### Gate 2 — Playwright completo com backend real

Foram descobertos 54 testes em sete arquivos. A primeira tentativa não iniciou
testes porque o webserver não ficou saudável no endereço configurado; terminou em
122,273 s, código 1, e foi preservada em `attempt1_webserver_timeout`. A primeira
execução efetiva terminou com 33 aprovados e 21 falhas em 677,037 s. As causas
foram reproduzidas e classificadas: origem frontend/backend incompatível com CSRF,
mock público com CORS fixo em outra origem, período de escala preso a julho após a
virada para agosto, expectativa antiga de Dashboard protegido na raiz que agora é
landing pública e sincronização insuficiente do logout; tentativas repetidas ainda
atingiram o throttle de backup em memória.

Foram corrigidos somente os contratos de teste/ambiente. Retestes isolados finais:

- recorrência real: 1/1, 11,094 s, código 0;
- escala real: 1/1, 27,670 s, código 0;
- Demo Pública: 26/26, 113,890 s, código 0;
- tenant local descartável: 1/1, 19,580 s, código 0.

A repetição completa final executou 54/54 testes, com 54 aprovados, zero falhas,
zero erros, zero skips, zero retries e código 0. Duração do reporter: 335,774 s;
duração de parede: 337,277 s. Os logs finais são
`gate2_playwright/full_stdout.log`, `full_stderr.log`, `full_exitcode.txt` e
`results.json`. Screenshots das 21 falhas iniciais foram preservados em
`attempt2_21_failures/artifacts`; a execução final não gerou screenshot de falha.
Não existem traces porque a configuração usa `trace: on-first-retry` com retries
zero, nem vídeos porque `video` está desativado. As duas capturas deliberadas da
escala real também foram preservadas.

#### Gate 3 — integração real

Frontend, backend e PostgreSQL locais foram validados em conjunto. O ciclo real
cobriu login, sessão Django, CSRF, logout confirmado pelo endpoint de sessão,
troca de tenant, criação/edição, desativação lógica e guard de exclusão física,
custos fixos e por evento, servidores, escala diária, participações, planos e
materializações recorrentes, idempotência, exportação, backup/download, restore,
auditoria, permissões e OpenAPI.

- navegador multitenant: código 0 em 8,288 s; cliente criado/editado/desativado em
  `f7a` sem aparecer em `f7b`, exclusão física corretamente recusada com 405,
  CSRF cruzado recusado com 403, replay idempotente estável em `f7a`, mesma chave
  independente em `f7b`, logout de `f7a` sem encerrar a sessão de `f7b`, cookies
  separados por host e zero hosts externos;
- auditoria/setup: código 0 em 1,341 s, com histórico e ator em planos e
  participações e zero vazamento de cliente para `f7b`;
- usuário sem grupos/permissões: backups, clientes e planos recusados com 403 e
  logout permitido com 200; código 0 em 3,578 s;
- OpenAPI: `manage.py spectacular --validate`, código 0 em 2,119 s, schema válido
  de 114.528 bytes e `stderr` vazio.

Evidências: `gate3_multitenant_browser`, `gate3_audit_permissions`,
`gate3_openapi` e os testes reais de recorrência/escala no resultado Playwright.

#### Gate 4 — compatibilidade N/N-1

Os snapshots N-1 foram extraídos dos HEADs limpos dos repositórios para diretórios
diagnósticos; as mudanças F7 não commitadas representam N. A matriz real terminou
verde:

- FE N → BE N: criação, edição, materialização, replay idempotente e confirmação
  salarial passaram no Playwright real;
- FE N → BE N-1: código 0 em 23,047 s; endpoint recorrente respondeu 404, somente o
  painel recorrente degradou e a lista legada de custos fixos continuou visível,
  sem erro de página ou servidor;
- FE N-1 → BE N: código 0 em 3,913 s; payload recorrente legado sem
  `authorizedMaterializationDate`/`Idempotency-Key` foi recusado com 400 e nenhum
  registro foi criado.

Estratégia obrigatória de deploy: publicar FE N primeiro, confirmar a degradação
controlada contra BE N-1 e somente então publicar BE N. Depois que BE N criar
planos/ocorrências, rollback para BE N-1 permanece proibido. Riscos residuais
operacionais: durante a janela N/N-1 o painel recorrente fica indisponível; um FE
N-1 remanescente não consegue criar recorrência no BE N e deve ser atualizado,
sem flexibilizar o guard de autorização.

Evidências: `gate4_n_nminus1/fe_n_to_be_nminus1`,
`fe_nminus1_to_be_n_attempt3`, snapshots e logs dos servidores N-1.

#### Gate 5 — multi-tenant

O gate terminou aprovado combinando o navegador real, auditoria, backup/restore e
os 26 testes da Demo Pública. Foram confirmados isolamento de schemas, cache por
runtime/tenant, sessões e cookies independentes, CSRF por origem, auditoria com
ator, backups e restores por diretório/schema, idempotência por tenant, quotas de
escrita/leitura da Demo e ausência de links/admin não autorizados. Não houve
vazamento entre `f7a`, `f7b`, `f7restorea`, `f7restoreb` ou `f7n1`; zero requests
externos foram emitidos. O gate previamente aprovado da Demo Pública não foi
repetido contra `demo1`, conforme a restrição desta retomada; seu contrato atual
foi coberto no Playwright sem escrever em tenant persistente.

#### Gate 6 — responsividade e paridade visual

A referência original foi identificada no repositório
`dashboardFinanceiro/v0-dashboard-financeiro-rhremoto`, HEAD `8fede544`, limpo.
Foram usadas cópias diagnósticas isoladas da referência e do frontend atual,
ambas lendo o mesmo backend/tenant `f7a`. Na cópia atual, somente o harness expôs
diretamente o componente do Dashboard, porque a raiz oficial agora é a landing
pública; nenhum arquivo da referência ou essa rota no repositório atual foi
alterado.

Foram comparadas Dashboard, Eventos, Custos por Evento, Custos Fixos, Custos por
Servidor, Servidores, Obrigações Financeiras e Backups em 375×812, 768×1024,
1024×768 e 1440×900: 64 cenários e 64 screenshots em 271,288 s, código 0. Resultado:
zero overflow documental, recorte inseguro, sobreposição, erro de página/console,
warning crítico ou host externo. As tabelas mantêm controles acessíveis em
contêineres próprios de rolagem sem ampliar a página. O Dashboard foi recapturado
após aguardar o KPI real, em oito cenários, 64,025 s, código 0. Formulário lateral
de custo fixo e seletor de período foram abertos, sem submissão, nas oito
combinações original/atual e largura: 16 screenshots em 64,556 s, zero falhas,
overflow ou divergência de paridade.

As tentativas que detectaram CSP da referência, skeleton ainda carregando,
classificação indevida de tabela rolável/Fast Refresh e medição durante a animação
do painel foram preservadas como diagnóstico do harness; os rechecks sincronizados
terminaram verdes. Evidências finais: `gate6_responsiveness/report.json`,
`dashboard_report.json`, `interactive_report.json`, `screenshots` e
`interactive_screenshots`.

#### Gate 7 — backup e restore

Foram gerados backups reais e separados:

- `f7a`: `backup_banco_2026-08_20260802_002241_732722.json`, 323.911 bytes,
  559 objetos, SHA-256
  `4b2f479403686416d1d1f27905df17223bdac6ede73d59edcdc4c8ab0fecded0`,
  código 0 em 1,816 s;
- `f7b`: `backup_banco_2026-08_20260802_002243_555469.json`, 140.794 bytes,
  371 objetos, SHA-256
  `74f917d04cd3a67420cb355b777ed27b63461da4dcc57fec613956326ec676f6`,
  código 0 em 1,975 s.

Os schemas de restore foram criados em 44,910 s. `loaddata` instalou 559 objetos em
`f7restorea` (2,396 s) e 371 em `f7restoreb` (1,879 s), ambos com código 0. Os
marcadores `Árvore São João – Tenant A` e `Órbita Açúcar – Tenant B` foram
confirmados por codepoints UTF-8; contagens por modelo coincidiram integralmente e
o marcador do outro tenant foi zero. Um fixture inválido falhou como esperado em
1,674 s e a verificação posterior confirmou rollback atômico, marcador preservado
e zero corrupção. Nomes, metadados, hashes e diretórios por tenant foram validados.
Evidências: `gate7_backup_restore`, incluindo as cópias dos dumps e metadados.

#### Gate 8 — Git, limpeza e recomendação

Backend `rhsaas`, branch `feat/django-tenants-spike`, HEAD `c2c3fb0`: 79 entradas
em `git status --short` (46 rastreadas modificadas e 33 não rastreadas), nenhuma
remoção. `git diff --stat`: 46 arquivos, 2.521 inserções e 173 remoções.
`git diff --check`: código 0, sem erro de whitespace; somente os sete avisos
preexistentes de futura normalização CRLF→LF.

Frontend `rhsaasfront`, branch `main`, HEAD `8a19e77`: 54 entradas em
`git status --short` (35 rastreadas modificadas e 19 não rastreadas), nenhuma
remoção. `git diff --stat`: 35 arquivos, 1.203 inserções e 268 remoções.
`git diff --check`: código 0, sem saída.

Os manifestos exatos estão em `backend_git_status_final.txt` e
`frontend_git_status_final.txt`; os stats e checks correspondentes também estão na
raiz dos diagnósticos. O backend já estava sujo pela implementação F1–F7 e pelas
correções de 17.10/17.11; nenhum código backend foi alterado nesta etapa. Arquivos
deliberadamente alterados nesta etapa:

- `rhsaasfront/scripts/check-global-financial-filters.mjs`;
- `rhsaasfront/scripts/check-financial-canonical-usage.mjs`;
- `rhsaasfront/tests/e2e/public-demo.spec.ts`;
- `rhsaasfront/tests/e2e/live-backend-scale.spec.ts`;
- `rhsaasfront/tests/e2e/rh-teste-demo.spec.ts`;
- este plano, com a seção 17.12.

Não houve arquivo removido, teste removido, skip, xfail, redução de assert ou
aumento de timeout. Os dois bancos descartáveis foram removidos após terminar
conexões; a consulta final retornou zero bancos residuais. As portas 8000, 8001,
3100–3104 foram encerradas. Os diretórios de backup `f7a` e `f7b` foram retirados
do repositório e preservados de forma recuperável nos diagnósticos; zero diretório
temporário `f7*` permaneceu em `backups/tenants`. A credencial efêmera foi excluída.

Riscos residuais: respeitar estritamente a ordem FE N antes de BE N; não reverter
BE para N-1 depois de criar dados recorrentes; manter monitoramento de 404/405 do
painel durante a janela de rollout e executar homologação com a mesma matriz antes
da produção. São riscos operacionais documentados, não falhas dos gates locais.

Recomendação e veredito final: **F7 aprovada; pronta para criação dos commits e
homologação.**

### 17.13 Revisão final e commits da paridade SaaS — 02/08/2026

Esta revisão foi feita depois da aprovação integral da F7 em 17.12 e antes de
homologação. A auditoria persistente está fora dos repositórios em
`C:\Users\Davif\.codex\diagnostics\rhsaas_commit_audit_20260802`; nenhum log,
backup, banco, cache, `.env`, `node_modules`, `.next`, diagnóstico ou artefato
local foi incluído em staging.

O backend partiu de `feat/django-tenants-spike` / `c2c3fb0` com 46 modificações
rastreadas e 33 arquivos novos; o frontend partiu de `main` / `8a19e77` com 35
modificações rastreadas e 19 arquivos novos. Não havia remoções. Todos os
arquivos foram revisados individualmente por diff, declarações e varredura de
segredos. Os únicos matches de credencial foram fixtures de teste de senha/CSRF;
não há credencial real, chave privada ou URL de conexão com senha nos commits.

As migrations `0043_servidores`, `0044_recorrencias_salariais` e
`0045_participacoes_escala_diaria` foram conferidas integralmente. Mantêm a cadeia
`0042 -> 0043 -> 0044 -> 0045`, usam somente operações declarativas compatíveis
com PostgreSQL, constraints e índices; não contêm credenciais, SQL mutável ou
operações sobre schema público. `makemigrations --check --dry-run` e
`manage.py check`, ambos com `DEBUG=true`, passaram sem criar migration ou escrever
em banco persistente. A primeira tentativa sem sobrescrever o ambiente local foi
registrada como bloqueada por `DEBUG=release` inválido; não chegou a executar
migration nem alterou dados.

Commits funcionais criados no backend:

- `8790b00` `feat(caixa): add server and salary domain`;
- `5329f6e` `feat(caixa): add recurring cost plans and materialization`;
- `c81880a` `feat(caixa): add event staff participation and allocation`;
- `e6699d4` `feat(caixa): integrate parity flows with financial dashboard`;
- `6d3067b` `feat(tenancy): guard recurring operations and demo reset`.

Commits funcionais criados no frontend:

- `86e8cc8` `feat(finance): add server management and cost views`;
- `a7a3cf8` `feat(finance): support recurring cost plans`;
- `9eab315` `feat(finance): show server participation in event costs`;
- `0ebe2a7` `refactor(finance): harden responsive dashboard state`;
- `f5d1a40` `test(finance): add parity guardrails and E2E coverage`.

Em cada commit, foram revisados `git diff --cached --stat`, o diff completo salvo
nos diagnósticos e `git diff --cached --check` antes da gravação. A importação
duplicada de `hashlib` no comando de reset da Demo foi removida durante a revisão;
não houve outra correção funcional, remoção de teste, skip, xfail, redução de
assert ou aumento de timeout.

Validação pós-commit aprovada: backend com `manage.py check`,
`makemigrations --check --dry-run` e `spectacular --file NUL --validate
--fail-on-warn`; frontend com lint, typecheck, guardrail de cache e build de
produção. O build gerou 24 rotas sem erro. Não foram repetidos Django integral ou
Playwright, pois os gates F7 de 17.12 já estavam aprovados e esta etapa não alterou
o código após a validação funcional.

O commit documental desta seção é criado em seguida; seu hash não é escrito
aqui para evitar um ciclo de autoatualização. Não houve push, deploy, produção,
uso de `demo1`/`rh_teste` ou criação de migration persistente nesta revisão.


### 17.14 Homologação exploratória final SaaS multi-tenant — 02/08/2026

Esta rodada ocorreu depois da F7 aprovada em 17.12 e dos commits de 17.13. Não repetiu a regressão Django integral, Playwright ou os gates F7: foi exploração manual assistida por navegador contra frontend, backend e PostgreSQL locais.

#### Ambiente, escopo e isolamento

Foi criado exclusivamente o PostgreSQL descartável `rhsaas_explore_20260802_r1`, em `localhost:5433`. A pré-validação confirmou host local, ausência de conexão de produção, nome diferente de banco persistente, zero escrita em `demo1` e `rh_teste`, e remoção segura ao final. Foram criados somente os tenants descartáveis `explorea`, `exploreb` e `explorerestore` dentro desse banco. Não houve acesso a produção, deploy, push ou commit.

#### Fluxos explorados

O navegador concluiu a execução final em `101,0 s` (11:35:03–11:36:44, código 0), além da confirmação posterior do clique real da barra lateral. Foram exercitados autenticação CSRF/sessão, aba adicional e refresh de sessão, logout, permissão limitada, CRUD de cliente, isolamento entre tenants e rejeição CSRF cruzada, eventos e detalhe com escala diária, participação mensal e custo, CRUD de servidor, custo fixo, plano recorrente, idempotência/materialização, dashboard, relatórios, obrigações, links profundos, refresh, voltar/avançar e telas de erro/autorização.

As 15 combinações responsivas de Dashboard, Eventos, Custos fixos, Servidores e Custos de servidores (desktop, tablet e celular) não apresentaram overflow horizontal. A telemetria final não encontrou erro React/página, falha de request ou HTTP inesperado. Os 401/403 eram respostas intencionalmente provocadas por logout, CSRF cruzado e permissão limitada. Uma extensão local de segurança injetou tentativa de recurso externo; ela foi bloqueada no contexto do navegador antes de sair da máquina e não houve host externo efetivo. Indicadores locais: `DOMContentLoaded` 1.925 ms, `load` 6.930 ms e transferência de 76.254 bytes; não são benchmark de produção.

O backup real de `explorea`, `backup_banco_2026-08_20260802_112155_553606.json`, foi restaurado em `explorerestore`: `loaddata` instalou 645 objetos com código 0. O marcador UTF-8 `Árvore São João — Tenant A` foi confirmado por codepoints e o marcador do tenant B foi zero. A cópia recuperável do dump e metadado ficou somente nos diagnósticos externos.

A Demo pública não foi provisionada nem mutada nesta rodada, pois criar ou usar o seed público contrariaria a proibição explícita de escrita em `demo1` e `rh_teste`. O banco temporário confirmou zero schema reservado; a proteção de não escrita foi respeitada. O fluxo público completo, inclusive seed/reset/isolamento, permanece coberto pela evidência F7 aprovada em 17.12.

#### Problema encontrado e correção mínima

O item **Dashboard** da sidebar apontava para `/`, rota de entrada da Demo pública, em vez do dashboard privado do tenant. A correção foi restrita ao frontend:

- `rhsaasfront/components/dashboard/sidebar.tsx`: destino alterado de `/` para `/dashboard`;
- `rhsaasfront/app/dashboard/page.tsx`: rota privada que renderiza `FinancialDashboardView`.

Após o hot reload, o clique real em **Dashboard** chegou a `/dashboard`, exibiu o título esperado e terminou com código 0. Não houve alteração de backend, remoção de teste, skip, xfail, redução de assert ou aumento de timeout.

#### Evidências, limpeza e estado Git

Os logs persistentes externos estão em `C:\Users\Davif\.codex\diagnostics\rhsaas_exploratory_homologation_20260802_run01`: `environment_preflight.log`, `fixture_setup.log`, `migrate_shared.log`, `browser_exploration.log`, `backup_restore.log`, `public_demo_protection.log` e `cleanup.log`. O backup criado sob `backups/tenants/explorea` foi removido do repositório após a cópia diagnóstica. As portas 8010 e 3110 foram encerradas, todas as conexões remanescentes do alvo foram terminadas e a consulta final retornou zero bancos com o prefixo `rhsaas_explore_20260802_`.

Estado Git ao finalizar: backend em `feat/django-tenants-spike` / `13ab56b`, com somente `M PLANO_ATUALIZACAO_PARIDADE_FUNCIONAL_MULTITENANT.md`; frontend em `main` / `f5d1a40`, com `M components/dashboard/sidebar.tsx` e a nova rota não rastreada `app/dashboard/page.tsx`. Não deve ser criado commit nesta etapa.

Veredito: **Homologação exploratória aprovada com observações documentadas.**
