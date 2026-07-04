# Arquitetura do projeto

Este projeto passa a seguir arquitetura frontend separado + backend API:
Next.js e a interface operacional dos usuarios, enquanto Django e a fonte da
verdade de dados, regras, permissoes, APIs, comandos e administracao tecnica.
O HTML Django operacional foi removido da linha principal; Django preserva
apenas Admin, API, autenticacao, erro/suporte e downloads tecnicos.

## Camadas

- `config/`: configuracoes globais, rotas raiz e seguranca.
- `caixa/models*.py`: modelos e regras ligadas diretamente aos dados.
- `caixa/selectors_*.py`: consultas, agregacoes e read-models para APIs e regras.
- `caixa/selectors_opcoes_filtros.py`: opcoes reutilizaveis de filtros compartilhados entre telas.
- `caixa/serializers_*.py`: montagem de payloads JSON para contratos de API.
- `caixa/services_*.py`: casos de uso e operacoes de escrita.
- `caixa/views_*.py`: entrada HTTP fina para APIs, autenticacao, Admin/suporte e
  redirects legados para links antigos.
- `caixa/templates/caixa/layouts/`: layouts preservados apenas para
  autenticacao, erro e suporte enquanto necessarios.
- `caixa/templates/caixa/`: sem templates operacionais Django; permanecem
  `login.html`, `password_reset_*`, `403.html`, `layouts/auth.html` e includes
  PWA usados por autenticacao/suporte.
- `caixa/static/caixa/js/` e `caixa/static/caixa/css/`: assets operacionais
  Django foram removidos; permanecem apenas recursos de auth/Admin/suporte,
  PWA, logos e apoio tecnico.
- `caixa/permissions.py`: guards reutilizaveis de acesso.

## Migracao gradual para Next.js

Este nao e um rewrite. A aplicacao atual continua sendo a fonte de verdade e deve permanecer funcional durante toda a migracao.

Responsabilidades preservadas no Django:

- regras de negocio e financeiras;
- banco de dados;
- autenticacao, sessoes, permissoes e admin;
- validacoes, recalculos, sinais e servicos de escrita;
- selectors de leitura, agregacoes e montagem de contexto;
- camada de API;
- configuracoes de seguranca.

Responsabilidades do Next.js:

- renderizacao da interface;
- dashboards, graficos e UX responsiva;
- consumo dos contratos JSON expostos pelo Django;
- composicao visual sem duplicar regra financeira.

Nao criar ou reativar tela HTML Django operacional. Com a base operacional
vazia, templates, rotas, aliases e fluxos que existirem apenas para
compatibilidade historica devem ser removidos quando nao sustentarem Admin,
auth, API, auditoria, comando ou download tecnico.

O documento `INTEGRACAO_NEXT_DJANGO.md` complementa esta secao com o contrato intermediario entre o dashboard Next.js e o backend Django, incluindo endpoint inicial, variaveis do frontend, regra de consumo via services/hooks e criterio de pronto.

### PM-06 - Base vazia premium e contrato visual

A linha atual da PM-06 trata a base operacional como vazia/premium. Dados
historicos nao sao requisito de migracao e serao recadastrados manualmente apos
a atualizacao. Por isso, compatibilidade historica deixa de ser padrao:
aliases, adapters, models, campos e fluxos temporarios so permanecem quando
agregam valor real para a arquitetura final ou para auditoria tecnica
essencial.

`ContratoOperacional` nao participa mais do contrato tecnico do backend: o
caminho principal e `Cliente -> Orcamento -> Evento`, com `Evento` como
dimensao operacional/contabil e `contractCode` como numero visual de
contrato/orcamento/evento.

Em PM-06-I local, a migration `0035_remove_contrato_operacional` foi aplicada
com backup SQLite previo. O schema local ficou sem tabela fisica de
`ContratoOperacional` e sem colunas `contrato_operacional*`; referencias
restantes so devem existir em migrations historicas, testes negativos,
documentacao historica ou compatibilidade explicitamente justificada.

Regras atuais:

- nao publicar `contractId`, `contratoId`, `contrato_operacional` ou `contrato_operacional_id` em novos serializers/selectors;
- nao resolver filtros novos por ID de contrato operacional removido;
- manter o filtro visual chamado "Contrato" usando `contractCode`;
- usar URLs Next.js canonicas; aliases historicos como `costCenterId`,
  `contrato_codigo`, `evento_id`, `cliente_id`, `periodo_rapido`,
  `data_inicial` e `data_final` nao pertencem ao contrato novo;
- preservar encoding seguro para `contractCode` em links HTML que ainda forem
  mantidos; `contrato_codigo` e apenas excecao de template legado, nao contrato
  novo do Next.js;
- centralizar regra financeira, permissao, aprovacao, baixa, conciliacao e auditoria no Django;
- tratar qualquer retorno desses aliases removidos como regressao, exceto em migrations historicas ou testes explicitamente pulados de legado.

No frontend, a bateria agregada da PM-06 e `corepack pnpm run verify:pm06`,
que roda lint, typecheck, guardrails, build e E2E de filtros por contrato. Para
publicacao sem E2E local, usar `verify:publish`.

Para evolucao da arquitetura financeira premium, o roteiro executivo fica em `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md`, secao `Plano mestre para conclusao da arquitetura premium`. Ao retomar esse assunto, usar o plano mestre como lista principal de proximos passos; o historico em `Fases` serve como evidencia do que ja foi feito.

O roadmap ativo PM-06 premium fica dentro desse Plano Mestre. Estados atuais:

- concluida: decisao de base limpa, backend-first, Next.js como UI operacional
  e `ContratoOperacional` fora do caminho principal;
- concluida: retirada de HTML Django operacional e do shell visual antigo;
- concluida em desenvolvimento local: limpeza de schema
  `0035_remove_contrato_operacional` com backup previo e validacoes verdes;
- concluida em desenvolvimento local: auditoria final pos-limpeza PM-06-J,
  suite completa, auditoria de totais, frontend e E2E verdes;
- proximo passo: PM-07 apenas com riscos residuais aceitos; ambiente alvo ainda
  exige backup/rollback/janela propria quando aplicavel;
- descartada: migracao historica como requisito, preservacao longa de aliases
  ate `financeiro-v3` e HTML Django como fallback operacional permanente.

### Padrao para APIs

1. Novos contratos da migracao devem nascer sob `/api/dashboard/`.
2. Endpoints JSON existentes, como `/api/mes-financeiro/`, `/api/fci/` e `/api/fcf/`, continuam validos enquanto forem usados por testes ou frontend atual/futuro.
3. Views de API devem ser finas: validar entrada, chamar selectors/services e devolver JSON.
4. Calculos financeiros devem continuar em models, selectors e services existentes.
5. Serializers devem ficar separados por dominio, por exemplo:
   - resumo do dashboard;
   - receitas;
   - despesas;
   - fluxo de caixa;
   - clientes;
   - contratos/eventos;
   - contas a pagar;
   - contas a receber;
   - despesas por categoria;
   - receitas por servico;
   - indicadores financeiros;
   - metricas operacionais.
6. Valores monetarios devem ser serializados de forma previsivel, preferencialmente como string decimal.
7. Datas devem sair em ISO (`YYYY-MM-DD`) para facilitar consumo no Next.js.
8. Listagens maiores devem prever paginacao e filtros antes de crescerem.
9. Contratos devem incluir estrutura estavel, com blocos como `filtros`, `opcoes`, `totais`, `resultados` e, quando aplicavel, `paginacao`.

### DRF, CORS e seguranca

A introducao de Django REST Framework e `django-cors-headers` deve ser incremental e conservadora:

- adicionar dependencias e apps sem remover views HTML existentes;
- inserir middleware de CORS na posicao recomendada pelo pacote, sem enfraquecer middleware de seguranca atual;
- configurar origens permitidas por variavel de ambiente para o dominio Next.js;
- manter `CSRF_TRUSTED_ORIGINS`, cookies seguros, HTTPS, headers atuais e CSP sem alteracoes desnecessarias;
- comecar com autenticacao de sessao quando o Next.js estiver no mesmo ecossistema confiavel;
- proteger APIs com usuario autenticado e permissoes equivalentes as telas Django atuais;
- adicionar testes de permissao para cada endpoint.

### Performance e reutilizacao

Antes de criar um endpoint novo, procure primeiro por selectors existentes. O padrao esperado e reaproveitar:

- `selectors_dashboard*.py` para resumo, movimentacoes, alertas, custos por evento e totais;
- `selectors_mes_financeiro.py` para fluxo mensal, contas a pagar/receber e acumulados;
- `selectors_cadastros.py` para clientes, eventos, receitas, despesas e orcamentos;
- `selectors_custos_fixos.py`, `selectors_investimentos.py`, `selectors_financiamentos.py` e `selectors_pagamentos.py` para dominios financeiros especificos;
- `services_*.py` para qualquer escrita, pagamento, baixa, aprovacao ou sincronizacao.

Use `select_related`, `prefetch_related`, `annotate` e `aggregate` sempre que o endpoint puder crescer em volume. Endpoints novos devem ter teste de contrato, teste de permissao e, quando exibirem colecoes financeiras, teste de query count para evitar N+1.

### Regra de leitura centralizada para o frontend

Quando existir um ponto central de leitura ou read-model sincronizado, ele deve
ser a primeira fonte usada para telas Next.js e APIs de exibicao. O frontend nao
deve buscar valores em models fisicos paralelos apenas porque eles tambem
possuem o dado bruto. Se uma informacao visual importante nao estiver no ponto
central, a primeira opcao deve ser enriquecer esse read-model/API central no
backend; so depois disso considerar uma fonte secundaria, sempre documentada e
coberta por teste contra dupla contagem.

Prioridade atual de leitura para exibicao:

- valores realizados, caixa, FCO, FCI e FCF consolidados: `LancamentoFinanceiro`
  e selectors/APIs que agregam esse ledger central;
- contas a pagar/receber, saldo pendente, status de conciliacao e capacidade de
  baixa: `ObrigacaoFinanceira`, `BaixaFinanceira` e `BaixaFinanceiraAlocacao`,
  via leitura canonica quando disponivel;
- detalhes operacionais de despesas de evento: `DespesaOperacional` separada por
  `origem`, preservando vinculos como `origem_custo_extra`;
- cadastros e configuracoes operacionais: endpoints/selectors do dominio
  responsavel (`Cliente`, `Orcamento`, `Evento`, `Servico`, credores e demais
  cadastros). Na PM-06, `ContratoOperacional` deixou de ser entidade fisica do
  caminho principal; o contrato visual e o numero do orcamento/evento publicado
  como `contractCode`;
- FCI/FCF e telas especializadas: usar primeiro o endpoint/read-model do dominio
  (`/api/fci/`, `/api/fcf/`) e os campos consolidados publicados por ele; para
  realizado/caixa, preferir o ledger central quando o selector ja publicar esse
  recorte.

O codigo anti-duplicacao continua obrigatorio, mas ele deve proteger a leitura
centralizada, nao justificar coleta espalhada. Qualquer excecao precisa explicar
por que o dado ainda nao pertence ao ponto central e qual teste impede soma
duplicada ou divergencia visual.

Em obrigacoes financeiras, o selector tambem deve respeitar a dimensao central:
evento, contrato visual, cliente, parcelas FCF e financiamentos nao devem ser
lidos por relacoes Django diretas durante a montagem do JSON. Use
`serializar_dimensao_operacional_financeira`, `dados_parcela_divida_sem_lazy` e
`relacao_carregada`, com `select_related` explicito no queryset.

`dados_dimensao_operacional` e helper de escrita/sincronizacao. Ele nao deve ser
usado em selectors, serializers ou views JSON consumidas pelo Next.js, porque
esses caminhos precisam da versao sem lazy load e com contrato publico
normalizado.

Na PM-06 base vazia, services dedicados do Next.js so podem atuar como borda de
compatibilidade para aliases financeiros gerais quando o Django ainda publicar
esse contrato por necessidade atual documentada. A regra preferencial e remover
aliases sem uso operacional novo. Quando a excecao existir, a leitura deve ficar
centralizada em mapas/helpers locais e componentes/hooks consomem apenas campos
canonicos normalizados. Essa regra nao vale para a entidade removida
`ContratoOperacional`: `contractId`, `contratoId`, `contrato_operacional` e
`contrato_operacional_id` nao devem voltar ao contrato novo. O guardrail
`check:financial-canonical` deve continuar bloqueando aliases financeiros
diretamente na UI.

APIs com periodo rapido precisam tratar filtros personalizados como recortes
autonomos quando o operador nao enviou periodo ou datas explicitamente. Busca,
entidade, categoria, status ou tipo sem `data_inicial`/`data_final` e sem
`periodo_rapido`/`quickPeriod` nao podem cair em mes atual herdado da sessao. O
efeito do recorte e todos os periodos; o valor publicado em `periodo_rapido` ou
`quickPeriod` pode ficar vazio ou `todos`, conforme o contrato da superficie. A
combinacao com periodo continua permitida quando o periodo vier explicitamente
na requisicao.
FCI e FCF tambem devem publicar essa decisao nos aliases canonicos de filtro
quando o contrato da API exigir. Eventos segue a mesma regra no resolver central
de lista/API: busca, cliente ou status sem datas/periodo nao herda mes atual.
No Next.js, a decisao interativa equivalente fica centralizada em
`dashboard-filters.ts`: filtros de entidade, status ou servico sem datas deixam
de herdar o periodo rapido anterior, mas periodo escolhido explicitamente depois
continua sendo uma combinacao valida.
Campos descritivos legados, como `descricao`, devem ser resolvidos na borda de
normalizacao do service. Telas FCI/FCF consomem apenas
`description`/`investmentDescription` ou `description`/`debtDescription`,
mantendo aliases somente como espelho legado auditavel. O guardrail canonico do
frontend bloqueia acesso/propriedade `descricao` em UI/hooks financeiros.
O mesmo vale para categoria, tipo, tipo de fluxo, descricao de divida e
quantidade de parcelas: aliases como `categoria`, `categoria_display`,
`tipo_fluxo_display`, `descricao_divida`, `quantidade_parcelas` e
`status_display` pertencem a normalizadores/services, nao a componentes.
Em FCI, datas, valores e baixa manual seguem a mesma fronteira:
`data_prevista`, `data_realizacao`, `valor_previsto`, `valor_realizado`,
`saldo_restante`, `valor_pendente_realizacao` e `baixado_manualmente` ficam na
borda de normalizacao; UI/hooks consomem apenas campos canonicos.
Filtros FCI seguem o mesmo padrao: novas chamadas usam `startDate`, `endDate`,
`category`, `flowType`, `contractCode`, `eventId`, `clientId` e `quickPeriod`.
Aliases como `data_inicial`, `data_final`, `categoria`, `tipo_fluxo`,
`contrato_codigo`, `evento`, `cliente` e `periodo_rapido` so podem existir em
borda de service se a API ainda publicar essa compatibilidade de forma
documentada. Para contrato visual, `contractCode` e o unico campo funcional;
`contractId` nao deve ser publicado nem consumido.
Relatorios CSV gerados pelo Next.js contam como superficie visual e devem ser
incluidos nos guardrails canonicos sempre que exibirem dados financeiros.
O contrato TypeScript deve explicitar esses filtros, evitando `Record` generico
quando a API ja possui campos canonicos conhecidos.
Totais, fluxos, subtotais e estatisticas financeiras seguem a mesma fronteira,
incluindo FCI e FCF: a UI deve receber `*Amount`/contadores canonicos ja
preenchidos pelo service, sem fazer fallback visual para aliases de transicao.
Campos genéricos como `description` so devem ser consumidos diretamente quando
forem canonicos daquele contrato. Em contas a pagar do dashboard, a UI deve
usar `obligationDescription`/`payableDescription`; `description` permanece como
espelho de compatibilidade.
Componentes compartilhados de filtro, como o header do dashboard, devem receber
opcoes de contrato/evento/cliente ja normalizadas. Aliases operacionais em
portugues ou snake_case pertencem aos services/normalizadores.
Telas Next.js filtraveis devem passar os filtros ativos ao layout em todos os
estados visuais relevantes: sucesso, loading, erro, login e forbidden. Filtro
vindo da URL ou do estado local nao deve sumir do header enquanto o backend
resolve sessao, permissao ou leitura da API. No frontend, o guardrail
`check:dashboard-filter-layout` deve proteger essa regra nas telas financeiras
filtraveis.
Quando o filtro for usado por operador humano, o contrato deve preferir
`contractCode`/numero do contrato na UI. O backend resolve esse valor pelo
`Evento` e pelo `Orcamento.numero`, sem tabela intermediaria de contrato
operacional. `contractId` nao deve ser ecoado nem usado como chave funcional
dessa dimensao.
Essa regra vale para todas as telas Next.js que exibem filtros operacionais por
contrato, incluindo Dashboard, Custos por Evento, Obrigacoes, Pagamentos, FCI,
FCF, Receitas, Despesas e recortes derivados de Mes Financeiro. Testes Django
devem cobrir a resolucao `contractCode -> evento/orcamento`, e testes E2E do
frontend devem garantir que o numero digitado nao seja enviado como
`contractId`.
Quando a dimensao vier de evento legado, `eventNumber` preserva o numero tecnico
do evento, inclusive prefixos como `EVT-`, mas `contractCode` deve ser o numero
de contrato visivel ao operador. Essa normalizacao fica no servico central de
dimensao operacional financeira e deve ser reaproveitada pelos serializers de
opcoes e payloads financeiros.
Serializers de dimensao operacional/financeira nao devem completar contrato por
lazy load. Se a resposta precisa do contrato visual, o selector correspondente
deve carregar `evento__orcamento` com `select_related`; caso contrario, o
serializer deve preservar os campos conhecidos sem disparar consultas ocultas.
A mesma regra se
aplica a parcela FCF: divida, rótulo derivado da dívida e credor cadastrado
devem vir carregados pelo selector quando forem necessários no payload.
Serializers financeiros tambem nao devem acessar relacoes encadeadas direto,
como `obj.evento.campo`, `obj.divida.campo`, `obj.cliente.campo` ou
`obj.credor_cadastro.campo`. Para publicar campos de relacoes, use
`relacao_carregada` no serializer e `select_related` no selector que define o
payload.
Montadores centrais que transformam listas financeiras em payload visual seguem
a mesma regra. Referencias de receita/despesa, descricao de divida e rotulo de
parcela devem usar relacoes ja carregadas ou fallback neutro; o montador nao
deve consultar o banco para completar texto de exibicao.
Serializers de baixas canonicas, alocacoes e lancamentos financeiros tambem
seguem essa fronteira. Eles podem publicar IDs tecnicos diretamente, mas nomes,
codigos, rotulos e colecoes reversas dependem de relacoes ja carregadas pelo
selector com `select_related`/`prefetch_related`.
Views/APIs financeiras que montam JSON direto seguem a mesma regra: a view pode
ler IDs tecnicos, mas texto relacional e colecoes dependem de
`relacao_carregada`/`relacoes_multiplas_carregadas` e de querysets preparados.
APIs operacionais de eventos e orcamentos tambem devem publicar contrato,
evento e cliente pelo serializer central de dimensao operacional. Quando um
orcamento ainda nao tiver evento aprovado, o numero do orcamento e o contrato
visivel ao operador; depois da aprovacao, o evento gerado passa a ser a
dimensao operacional publicada, mantendo `contractCode` igual ao numero do
orcamento/evento.
Read-models centrais, como obrigacoes financeiras canonicas, devem seguir a
mesma regra e consumir a dimensao operacional financeira pronta, em vez de
recompor cliente, contrato e evento por acessos relacionais diretos.

Na linha PM-06 de base limpa, endpoints JSON consumidos pelo Next.js devem
aceitar entrada publica somente com nomes canonicos. Para Dashboard, Mes
Financeiro, FCI, FCF, Obrigacoes, Ledger e Baixas Canonicas, aliases como
`periodo_rapido`, `data_inicial`, `data_final`, `costCenterId`, `evento`,
`cliente`, `contrato_codigo`, `contractId`, `fonteEscrita`, `origem`,
`situacao`, `busca`, `tipoObrigacao` e `tipo_obrigacao` nao podem comandar
query nova. Se um selector legado ainda usa nomes antigos internamente, a view
ou serializer da API deve fazer uma ponte explicita a partir de entrada
canonica e manter essa ponte documentada como temporaria.

### Padrao de modelagem de dados

O banco deve proteger as invariantes centrais do dominio, nao apenas as telas. Regras financeiras basicas devem existir em tres camadas quando fizer sentido:

- `models.clean()` para mensagens claras no admin, forms e services.
- `save()`/services para recalculos, sincronizacoes e transicoes de status.
- `CheckConstraint`, `UniqueConstraint` e indices compostos para preservar integridade e performance no banco.

Campos derivados ou snapshots financeiros sao permitidos quando evitam recalculos caros ou preservam o estado historico de uma operacao, mas precisam ter fonte de verdade clara. Exemplos atuais:

- totais de `Orcamento` sao recalculados a partir dos itens;
- totais realizados de `Evento` sao recalculados a partir de receitas e despesas;
- despesas derivadas de custos de servico ou custos extras sao sincronizadas por services/signals e marcadas em `DespesaOperacional.origem`;
- saldos antigos como `saldo_em_aberto` sao candidatos a remocao quando a API
  ja expoe o nome canonico `valor_pendente_pagamento`; se ficarem, precisam ser
  excecao temporaria documentada.

`DespesaOperacional` tem origem explicita:

- `manual`: criada diretamente no admin/telas de despesas e paga como despesa operacional;
- `custo_servico`: gerada ou sincronizada a partir dos custos de servico do evento;
- `custo_extra`: gerada ou sincronizada a partir dos custos extras do evento.

Nao use descricao/categoria para decidir origem de pagamento. Descricoes como `Mao de obra prevista` ou `Custo extra: ...` sao apenas labels historicos; a regra deve consultar `origem`, `origem_custo_servico_tipo` e `origem_custo_extra`.

Para a tela premium de custos por evento, o contrato segue esta separacao:

- os totais principais continuam vindo das fontes estruturadas do evento (`EventoCustoServico`, `EventoCustoExtra` e despesas manuais), evitando dupla contagem;
- o detalhamento visual por categoria usa `DespesaOperacional` como read-model central sincronizado, separando por `origem`;
- `origem=custo_servico` detalha mao de obra/diarias, alimentacao e transporte;
- `origem=custo_extra` detalha os custos extras sincronizados, preservando a categoria original de `EventoCustoExtra` quando ela existir;
- `origem=manual` detalha apenas despesas operacionais criadas manualmente.

Assim, `DespesaOperacional` vira o read-model operacional central do card. O card nao deve buscar detalhe visual direto em `EventoCustoExtra` quando a despesa sincronizada existir; `EventoCustoExtra` e `EventoCustoServico` continuam como fontes estruturadas de cadastro, sincronizacao e totais. Essa regra e parte da arquitetura premium PM-06 para manter rastreabilidade, legibilidade de UI e paridade financeira sem duplicar valores.

Para novos models financeiros:

1. Use nomes de dominio claros: `contrato`, `resultado_financeiro`, `contas_pendentes`, `deficit_caixa`, `valor_pendente_pagamento` e `valor_pendente_recebimento`.
2. Evite criar novos campos com nomes genericos como `numero`, `saldo`, `aberto` ou `falta_cobrir`, salvo quando forem aliases temporarios documentados.
3. Crie indices compostos para filtros reais: status + data, categoria + data, entidade pai + status/data.
4. Adicione constraints para valores monetarios nao negativos, quantidades positivas, datas coerentes e unicidade de configuracoes globais.
5. Preserve compatibilidade externa apenas quando houver consumidor ativo
   documentado; em base vazia premium, aliases sem uso operacional novo devem
   ser removidos ou isolados em borda temporaria com guardrail.

### Superficie de interface

A arquitetura premium PM-06 nao usa mais HTML Django como superficie
operacional nova. A separacao oficial passa a ser:

- Next.js: interface operacional, telas de trabalho, filtros, exportacao,
  interacao e experiencia do usuario.
- Django: regras de negocio, models, services, selectors, serializers, APIs,
  permissoes, comandos, auditorias e integridade de dados.
- Django Admin: superficie HTML administrativa para suporte controlado.
- Auth/erro/suporte: templates Django minimos para login, reset de senha,
  erro 403 e includes PWA necessarios.

Templates HTML Django operacionais foram removidos. Rotas antigas podem
permanecer apenas como redirects legados para o Next.js; novas superficies
devem nascer como API Django + tela Next.js.

PM-06.1313 adicionou o comando read-only
`python manage.py inventariar_html_django_pm06 --json` como gate de limpeza de
HTML Django operacional. O inventario separa superficies removidas, redirects
legados, suporte preservado de auth/download e forms compartilhados com
API/Admin/services. Depois da PM-06.1327, o gate esperado e
`operationalHtmlCount=0`.

PM-06.1314 removeu as rotas/views POST HTML operacionais avulsas
`aprovar_orcamento` e `backup_criar_manual`. As escritas correspondentes
permanecem apenas nas APIs JSON `api_aprovar_orcamento` e
`api_backup_criar_manual`; nao recriar formularios POST HTML Django para
essas acoes. PM-06.1315 bloqueou os POSTs HTML embutidos em
`orcamento_adicionar`, `custo_extra_adicionar`,
`pagamentos_custos_servico`, `pagamentos_custos_extras` e `pagar_parcela`;
essas views sao `GET`/`HEAD`-only, os templates ficaram sem controles de
escrita operacional, e as baixas/cadastros correspondentes devem continuar
API/service-only.

PM-06.1316 removeu fisicamente o HTML operacional GET de `clientes_lista`,
`orcamentos_lista`, `orcamento_adicionar` e `eventos_lista`. Essas rotas Django
permanecem apenas como legacy redirect-only para o Next.js; os templates foram
apagados. A remocao nao autoriza perder regra de negocio: filtros, totais,
permissoes, validacoes, agregacoes e performance que existiam nas telas devem
continuar no backend e ser reaproveitados pelas APIs, selectors, serializers ou
services consumidos pelo Next.js.

PM-06.1317 aplicou o mesmo padrao em `backups_lista`: a tela HTML foi removida
e a rota `/backups/` virou redirect-only para o Next.js. A API de listagem,
geracao manual e o download tecnico (`backup_download`) continuam preservados
no Django.

PM-06.1318 removeu o HTML operacional GET de `receitas_lista` e
`despesas_lista`. As rotas `/receitas/` e `/despesas/` ficaram
redirect-only para o Next.js; os templates foram apagados, mas os selectors de
filtro/total (`filtrar_receitas`, `totais_receitas`, `filtrar_despesas`,
`totais_despesas`) permanecem como patrimonio backend. A leitura operacional
principal deve seguir pela API canonica de obrigacoes, e a edicao por APIs
dedicadas de receita/despesa quando houver permissao.

PM-06.1319 removeu o HTML operacional GET de `custo_extra_adicionar`. A rota
`/eventos/custos-extras/adicionar/` ficou redirect-only para `/custos-extras`
no Next.js. O template foi apagado, mas a regra util permanece no backend:
`api_criar_custo_extra_evento`, `criar_custo_extra()`,
`EventoCustoExtraForm` e `listar_custos_extras_recentes()` continuam
preservados enquanto a API usar essa validacao/consulta.

PM-06.1320 removeu o HTML operacional GET de `custos_fixos_lista`. A rota
`/custos-fixos/` ficou redirect-only para `/custos-fixos` no Next.js. A API de
custos fixos e os selectors `montar_contexto_custos_fixos()`,
`filtrar_custos_fixos()` e `totais_custos_fixos()` continuam sendo a camada
backend para filtros, totais, agrupamentos e performance.

PM-06.1321 removeu o HTML operacional GET de `custos_por_evento`. A rota
`/custos-por-evento/` ficou redirect-only para `/custos-por-evento` no Next.js.
A API `api_custos_por_evento`, o serializer de payload e os selectors
`montar_contexto_custos_por_evento()` e
`montar_custos_por_evento_dashboard()` continuam sendo a camada backend para
filtros, agrupamento por evento, detalhamento de custos de servico/custos
extras/despesas manuais, totais e performance.

PM-06.1322 removeu o HTML operacional GET de `lista_investimentos`. A rota
`/fci/` ficou redirect-only para `/fci` no Next.js. A API
`api_investimentos`, o serializer de payload e `montar_contexto_investimentos()`
continuam sendo a camada backend para filtros canonicos, grupos por categoria,
totais FCI, opcoes de filtro e performance.

PM-06.1323 removeu o HTML operacional GET de `lista_financiamentos`. A rota
`/fcf/` ficou redirect-only para `/fcf` no Next.js. A API
`api_financiamentos`, o serializer de payload e
`montar_contexto_financiamentos()` continuam sendo a camada backend para
parcelas, movimentacoes FCF, filtros canonicos, grupos por credor/divida,
totais, opcoes de filtro e performance.

PM-06.1324 removeu o HTML operacional GET de `pagamentos`,
`pagamentos_custos_servico`, `pagamentos_custos_extras`, `pagamentos_fcf` e
`pagar_parcela`. Essas rotas ficaram redirect-only para `/pagamentos` no
Next.js, preservando `source` e `sourceId` quando aplicavel. A baixa oficial
continua API/service-only por `api_liquidar_obrigacao_financeira`,
`services_obrigacoes.py` e selectors de obrigacoes/pagamentos; filtros,
permissoes, saldos, query count e regras de liquidacao nao pertencem mais a
templates Django.

PM-06.1325 removeu o HTML operacional GET de `dashboard_financeiro`. A rota
raiz Django (`/`) ficou redirect-only para o dashboard Next.js (`/`). A API
`api_dashboard_financial_overview`, `api_custos_por_evento`, serializers e
selectors de dashboard continuam sendo a fonte backend para filtros, totais,
alertas, links operacionais, FCO/FCI/FCF, performance e permissoes. O Next.js
mostra a experiencia; o Django calcula e valida.

PM-06.1326 removeu o HTML operacional GET de `mes_financeiro`. A rota
`/mes-financeiro/` ficou redirect-only para `/obrigacoes-financeiras` no
Next.js. A API `api_mes_financeiro`, `serializers_mes_financeiro.py` e
`montar_contexto_mes_financeiro()` permanecem como read-model backend para
filtros, totais, contas a pagar/receber, FCO/FCI/FCF, caixa disponivel,
performance e auditoria.

PM-06.1327 removeu o shell operacional Django remanescente (`base.html`,
`shared/_app_header.html`, `shared/_app_nav.html`, aviso de migracao, tabela
vazia, titulo de pagina e mensagens do shell). Permanecem apenas templates de
auth/erro/suporte (`login.html`, `password_reset_*`, `403.html`,
`layouts/auth.html`) e includes PWA usados por auth. Regras de negocio,
filtros, permissoes, performance e calculos seguem no backend/API.

PM-06.1328 removeu `forms_orcamentos.py`, pois ele era usado apenas pela tela
HTML antiga de orcamentos. O fluxo operacional de orcamentos permanece no
Next.js consumindo APIs JSON; validacoes e regras uteis ficam em serializers,
services, models e testes backend.

PM-06.1329 removeu assets estaticos exclusivos do shell/telas operacionais
Django (`caixa/css/base.css`, `caixa/css/dashboard.css` e
`caixa/js/menu.js`). Permanecem `login.css`, PWA/manifest/icones e JS usado
pelo Admin, pois sustentam auth/suporte/administracao tecnica.

### Sequencia recomendada

1. Documentar contratos e limites de responsabilidade.
2. Criar ou ajustar endpoints JSON com serializers canonicos.
3. Colocar consultas em `selectors_*.py`.
4. Colocar gravacoes/regras de negocio em `services_*.py`.
5. Cobrir cada contrato com testes antes de conectar o Next.js.
6. Implementar a experiencia operacional no Next.js.
7. Remover ou aposentar template Django legado quando houver rota Next.js
   equivalente, contrato estavel e plano de rollback.
8. Para escrita operacional, preferir sempre API JSON + service backend; HTML
   Django legado pode ficar no maximo como GET tecnico/readonly durante a
   retirada.
9. Ao remover HTML, migrar cobertura de filtros/performance/permissoes para
   API/selector/service em vez de simplesmente apagar o teste.

## Regra para novas telas

1. Nao criar nova tela HTML Django operacional.
2. Crie ou reutilize uma view fina de API em `views_*.py`.
3. Coloque consultas em `selectors_*.py`.
4. Coloque gravacoes/regras de negocio em `services_*.py`.
5. Para endpoints JSON, monte o contrato em `serializers_*.py` reaproveitando selectors existentes.
6. Reutilize selectors compartilhados de opcoes antes de montar listas de filtros na view.
7. Proteja a API com `require_permission`, `require_any_permission` ou `require_superuser`.
8. Adicione teste cobrindo rota, permissao e caso financeiro principal.
9. Crie ou ajuste a tela operacional no Next.js.

## Paralelo com Angular

- Layouts Django equivalem a shells/layout components.
- Includes em `shared/` equivalem a shared components.
- Selectors equivalem a uma camada de facades/read services.
- Services equivalem a use cases/write services.
- Guards equivalem a decorators de permissao em `caixa/permissions.py`.
- Templates de feature continuam perto do dominio da tela.

Evite colocar regra de negocio em template. Template deve renderizar dados prontos.
