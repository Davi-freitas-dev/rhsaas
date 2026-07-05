# Integracao Frontend Next.js + Backend Django

## Objetivo

Integrar o frontend Next.js do RH SaaS ao backend Django existente sem recriar
regras de negocio e sem quebrar o sistema atual em producao.

## Principio principal

O Django continua sendo a fonte da verdade.

O Next.js e responsavel apenas por:

- interface visual;
- dashboard;
- graficos;
- experiencia do usuario;
- consumo das APIs.

O Next.js nao deve duplicar regras financeiras, calculos sensiveis, permissoes ou validacoes de negocio.

## Workspace e Projetos Relacionados

Este backend Django trabalha junto com o frontend Next.js no mesmo workspace/local de desenvolvimento:

- Backend Django: `<workspace>/rhsaas`
- Frontend Next.js: `<workspace>/rh-saas-frontend`

Relacao de caminhos:

- a partir do backend, confirmar o caminho real do frontend RH SaaS;
- a partir do frontend, confirmar o caminho real deste backend.

Ao retomar uma tarefa, confirmar primeiro a raiz do terminal. Alteracoes de regra financeira, banco, admin, selectors, serializers, APIs, migrations, comandos, auditoria e testes de negocio ficam neste backend. Templates Django operacionais foram removidos da linha principal; permanecem apenas Admin, APIs, auth/erro/suporte, downloads tecnicos e redirects legados. Alteracoes de UI operacional, tipos TypeScript, mocks, services/hooks e documentacao visual ficam no frontend.

## PM-06 - Telas operacionais no Next.js

Durante a PM-06, as telas Django operacionais devem ser substituidas por
experiencias Next.js apenas quando a operacao ja estiver coberta por API
canonica ou por endpoint JSON seguro do Django. Com a nova premissa de base
operacional vazia, remocoes de alias, model obsoleto ou fluxo temporario ficam
permitidas quando simplificarem a arquitetura final e tiverem migration,
guardrail e validacao local.

Decisao atual: Django nao tera mais interface operacional HTML. O unico HTML
Django preservado como superficie aceita e o Django Admin, alem de telas de
autenticacao/suporte enquanto forem necessarias para Admin/API. Views,
templates, forms e rotas HTML operacionais antigas sao divida tecnica e devem
ser removidos quando houver API/Next equivalente ou quando a operacao nao for
mais necessaria.

### Linha atual para conclusao da PM-06

A linha escolhida para concluir a PM-06 a partir de 2026-06-02 e a virada com
base operacional limpa e recadastro manual controlado. Essa e a rota oficial
agora: aproveitar o codigo ja entregue, preservar backup/evidencias, limpar os
dados operacionais antigos e recriar manualmente apenas o conjunto pequeno que
precisa existir no sistema novo.

No backend, essa linha significa:

- Django continua sendo a fonte da verdade de banco, permissao, CSRF, validacao
  de negocio, calculos financeiros, aprovacao de orcamento, geracao de evento,
  obrigacoes, baixas e auditoria;
- usuarios, grupos, permissoes, sessoes, servicos e configuracao financeira
  devem ser preservados na base limpa;
- clientes, orcamentos, eventos, custos por evento, custos extras, custos fixos
  e FCF podem ser recriados manualmente pelo fluxo novo;
- `ContratoOperacional` nao faz mais parte do caminho principal da PM-06:
  `Cliente -> Orcamento -> Evento` e a cadeia operacional/contabil. O filtro
  visual "Contrato" usa o numero do orcamento/evento (`contractCode`), porque o
  evento e a dimensao que entra nas contabilizacoes de fato;
- obrigacoes, lancamentos, baixas e totais derivados devem ser recalculados ou
  auditados depois do recadastro, em vez de digitados como legado bruto;
- backup bruto, pacote PM-06 e relatorio financeiro completo continuam sendo a
  fonte de rollback/auditoria caso o recadastro precise ser conferido.

No frontend, a mesma linha significa operar pelo Next.js e enviar os nomes
canonicos/novos nos fluxos principais. O backend so deve manter aliases legados
em bordas de API quando eles ainda forem contrato publicado necessario para uma
tela ativa ou integrarem uma remocao temporaria com dono, motivo, prazo e
guardrail. Compatibilidade historica por dados antigos deixou de ser requisito.
Aliases ligados a `ContratoOperacional` saem do contrato novo: o backend nao
deve publicar nem depender de `contractId`, `contratoId`,
`contrato_operacional` ou `contrato_operacional_id`. O filtro visual
"Contrato" continua permitido, mas sempre por `contractCode`.

PM-06-I foi aplicada em desenvolvimento local com backup SQLite previo e
`0035_remove_contrato_operacional`. Depois da migration, o schema local nao
tem tabela `ContratoOperacional` nem colunas `contrato_operacional*`; qualquer
referencia restante deve ser historica, teste negativo, auditoria PM-06 ou
compatibilidade explicitamente justificada.

Roadmap ativo PM-06 premium:

- `concluida`: decisao de base limpa, Next.js como UI operacional,
  backend-first, retirada de `ContratoOperacional` do caminho principal e
  remocao do HTML operacional Django.
- `concluida localmente`: limpeza de schema PM-06-I com
  `0035_remove_contrato_operacional`, backup previo e validacoes verdes.
- `concluida localmente`: auditoria final pos-limpeza PM-06-J, suite completa,
  auditoria de totais, frontend e E2E verdes.
- `proximo passo`: PM-07 apenas com riscos residuais aceitos; ambiente alvo
  ainda exige backup/rollback/janela propria quando aplicavel.
- `descartada`: preservacao de aliases ate um grande corte `financeiro-v3`,
  migracao/restauracao automatica de dados antigos como requisito principal e
  HTML Django como fallback operacional permanente.

Proxima prioridade tecnica: iniciar PM-07 somente pelo Plano Mestre, mantendo
`inventariar_html_django_pm06` como gate contra regressao de HTML operacional e
respeitando os riscos residuais aceitos na PM-06-J.

PM-06.1314 removeu os POSTs HTML Django avulsos `aprovar_orcamento` e
`backup_criar_manual`. Aprovacao de orcamento e geracao manual de backup por
essas acoes sao API-only para operacao: `api_aprovar_orcamento` e
`api_backup_criar_manual`. O service de aprovacao permanece no backend para
Admin/API; o download tecnico de backup permanece preservado.
PM-06.1315 tambem bloqueou os POSTs HTML embutidos em `orcamento_adicionar`,
`custo_extra_adicionar`, `pagamentos_custos_servico`,
`pagamentos_custos_extras` e `pagar_parcela`: as views legadas ficaram
`GET`/`HEAD`-only, os templates nao exibem controles de escrita operacional e
as escritas correspondentes devem continuar por APIs JSON/services.
PM-06.1316 removeu o HTML operacional GET de clientes, orcamentos, cadastro de
orcamento e eventos. As rotas Django antigas permanecem apenas como
redirect-only para `/clientes`, `/orcamentos` e `/eventos` no Next.js. Ao
remover uma tela Django, nao remover junto as regras uteis que ela usava:
filtros, totais, permissoes, validacoes, performance, paginacao, agregacoes e
regras financeiras devem continuar no backend e ser expostos por API/selector/
serializer/service para o Next.js.
PM-06.1317 removeu tambem o HTML operacional GET de backups. A rota
`/backups/` ficou redirect-only para `/backups` no Next.js; `GET
/api/backups/`, `POST /api/backups/criar/` e o download tecnico Django
permanecem como fontes oficiais para listagem, geracao manual e recuperacao de
arquivos.

PM-06.1318 removeu tambem o HTML operacional GET de receitas e despesas. As
rotas `/receitas/` e `/despesas/` ficaram redirect-only para `/receitas` e
`/despesas` no Next.js. Para leitura operacional, o frontend deve priorizar a
API canonica de obrigacoes; para detalhe/edicao, usar as APIs dedicadas de
receitas/despesas. Os selectors legados uteis de filtro e totais continuam no
backend para reaproveitamento por APIs/testes e nao devem ser duplicados no
frontend.

PM-06.1319 removeu tambem o HTML operacional GET de cadastro/listagem de custo
extra. A rota `/eventos/custos-extras/adicionar/` ficou redirect-only para
`/custos-extras`; a tela Next.js deve usar `POST /api/eventos/custos-extras/`
para cadastro. `EventoCustoExtraForm`, `criar_custo_extra()` e
`listar_custos_extras_recentes()` continuam no backend enquanto forem usados
pela API/validacao/testes.

PM-06.1320 removeu tambem o HTML operacional GET de custos fixos. A rota
`/custos-fixos/` ficou redirect-only para `/custos-fixos`; a tela Next.js deve
usar a API JSON de custos fixos. Filtros, totais e agrupamentos seguem no
Django via `montar_contexto_custos_fixos()`, `filtrar_custos_fixos()` e
`totais_custos_fixos()`.

PM-06.1321 removeu tambem o HTML operacional GET de custos por evento. A rota
`/custos-por-evento/` ficou redirect-only para `/custos-por-evento`; a tela
Next.js deve usar `GET /api/custos-por-evento/`. Filtros, agrupamentos,
breakdown de custos de servico/custos extras/despesas manuais, totais e
performance seguem no Django via `montar_contexto_custos_por_evento()`,
`montar_custos_por_evento_dashboard()` e serializers da API.

PM-06.1322 removeu tambem o HTML operacional GET de FCI/investimentos. A rota
`/fci/` ficou redirect-only para `/fci`; a tela Next.js deve usar
`GET /api/fci/`. Filtros canonicos, grupos por categoria, totais FCI, opcoes de
filtro e performance seguem no Django via `montar_contexto_investimentos()` e
serializers da API.

PM-06.1323 removeu tambem o HTML operacional GET de FCF/financiamentos. A rota
`/fcf/` ficou redirect-only para `/fcf`; a tela Next.js deve usar
`GET /api/fcf/`. Parcelas, movimentacoes FCF, filtros canonicos, grupos por
credor/divida, totais, opcoes de filtro e performance seguem no Django via
`montar_contexto_financiamentos()` e serializers da API.

PM-06.1324 removeu tambem o HTML operacional GET da familia de pagamentos:
`/pagamentos/`, `/eventos/custos-servico/pagamentos/`,
`/eventos/custos-extras/pagamentos/`, `/fcf/pagamentos/` e
`/fcf/parcelas/<id>/pagar/` ficam somente redirect-only para `/pagamentos` no
Next.js, com `source`/`sourceId` preservados quando aplicavel. A leitura da
fila deve continuar em `GET /api/obrigacoes-financeiras/` com
`obligationType=pagar`, e a escrita em
`POST /api/obrigacoes-financeiras/liquidar/`. Regras de saldo, permissao,
baixa, write-off, FCF, custo de servico e custo extra permanecem no backend em
selectors/services/API canonica, nao no frontend nem em template Django.

PM-06.1325 removeu tambem o HTML operacional GET do dashboard Django. A rota
`/` do backend agora e somente redirect para `/` no Next.js. A tela Next.js
deve continuar consumindo `GET /api/dashboard/financial-overview/` e
`GET /api/custos-por-evento/`; filtros, totais, alertas, links operacionais,
FCO/FCI/FCF, permissoes e performance permanecem implementados no backend via
selectors/serializers/APIs. O frontend nao deve recalcular essas regras.

PM-06.1326 removeu tambem o HTML operacional GET de `mes_financeiro`. A rota
`/mes-financeiro/` do backend agora e somente redirect para
`/obrigacoes-financeiras` no Next.js. O read-model mensal continua no Django
por `GET /api/mes-financeiro/`, `montar_contexto_mes_financeiro()` e
`serializers_mes_financeiro.py`; filtros, totais, contas a pagar/receber,
FCO/FCI/FCF, caixa disponivel, performance e auditoria nao devem ser
recriados no frontend.

PM-06.1327 removeu o shell operacional HTML Django remanescente (`base.html`
e includes de cabecalho/menu/listagem). Permanecem apenas templates de
autenticacao, erro/suporte e includes PWA usados por auth. Qualquer nova
experiencia operacional deve nascer no Next.js, chamando API/selector/service
do backend.

PM-06.1328 removeu `forms_orcamentos.py`, que era dependencia apenas da tela
HTML antiga de orcamentos. O Next.js deve continuar usando APIs JSON de
orcamentos; validacao/regra util fica em serializers, services, models e
testes backend.

PM-06.1329 removeu assets exclusivos do shell/telas operacionais Django:
`caixa/css/base.css`, `caixa/css/dashboard.css` e `caixa/js/menu.js`.
Permanecem assets de login, PWA, icones e Admin.

No fluxo de orcamentos, o numero do orcamento e o contrato visivel desta linha:
cadastrar e editar no Next.js antes da aprovacao; aceitar edicao de servico,
horas, dias, pessoas, diaria, alimentacao, transporte, margem, imposto, regra
especial e custos extras; tratar margem/imposto como taxa (`0.30` ou `30%` para
30%); bloquear edicao visual de orcamentos aprovados, recusados ou cancelados;
manter geracao de evento, sincronizacao de custos/receita e permissoes no
Django.

Regra geral de edicao na integracao Next.js + Django: toda API de cadastro,
edicao, aprovacao ou baixa deve responder com o registro atualizado e com os
totais derivados ja recalculados quando essa informacao aparecer na tela. O
frontend deve usar essa resposta para substituir imediatamente o registro antigo
no estado local e depois fazer nova leitura do backend como confirmacao. O
usuario nao deve precisar recarregar a pagina para ver venda, lucro, saldo,
status ou qualquer resumo alterado por uma edicao. Quando um valor foi editado
por erro de cadastro, o valor antigo nao deve permanecer em dado ativo, lista,
resumo, card, grafico ou calculo operacional; ele so pode continuar em backup,
auditoria ou historico tecnico.

Regra de filtros PM-06: filtros especializados do Next.js sem datas explicitas
devem ser tratados como recortes autonomos de todos os periodos. Antes de chamar
o Django, a tela nao deve herdar nem criar periodo artificial quando buscar por
contrato, evento, cliente, categoria, origem, credor, fluxo, situacao,
conciliacao, diagnostico ou fonte de pagamento. O Django resolve o recorte
efetivo sem limitar ao mes atual; periodo + filtro continua permitido quando o
operador escolhe o periodo explicitamente depois do filtro.

Decisao operacional PM-06.1202: quando a quantidade de dados reais for pequena,
fica permitido usar uma base limpa para acelerar a virada, desde que exista
backup bruto completo e um pacote de recadastro manual gerado por
`python manage.py exportar_recadastro_manual_pm06`, validado por
`python manage.py validar_recadastro_manual_pm06 --comparar-base-atual`. Esse
caminho aproveita todo o codigo ja atualizado e recria manualmente apenas as
fontes operacionais necessarias no sistema novo, incluindo orcamentos com itens
e custos extras; obrigacoes, lancamentos, baixas e totais derivados devem ser
recalculados depois do recadastro. Se essa estrategia for usada, a prontidao
operacional deve ser validada por `validar_prontidao_base_limpa_pm06`; o gate
de migration/limpeza continua restrito a remocao fisica e nao autoriza limpeza
automatica de producao.

PM-06.1203 operacionalizou essa decisao com
`python manage.py limpar_base_operacional_pm06`. O comando exige backup bruto
com metadata, `pm06-prontidao-base-limpa-manual.json`,
`pm06-validacao-recadastro-manual.json`, `dry-run` revisado e token explicito
para execucao. A limpeza remove dados operacionais e derivados em transacao,
preservando usuarios, grupos, permissoes, sessoes, servicos e configuracao
financeira; com `--limpar-historico`, tambem remove historicos Simple History
dos modelos operacionais, mantendo o backup bruto como fonte de auditoria.

Rotas Next.js registradas na superficie PM-06:

- `/custos-por-evento` e alias `/centro-de-custos`: leitura por
  `GET /api/custos-por-evento/`, com a mesma permissao Django da tela de
  eventos (`caixa.view_evento`) e agrupamento de custos por evento.
- `/receitas`: leitura canonica de obrigacoes com `obligationType=receber` e
  `source=receita_operacional`; edicao de valor previsto e recebido/nao
  recebido por `PUT /api/receitas/<id>/`, restrita a
  `caixa.change_receitaoperacional`.
- `/despesas`: leitura canonica de obrigacoes com `obligationType=pagar`,
  `cashFlowGroup=fco`, `source=despesa_operacional` e graficos derivados
  apenas das despesas operacionais carregadas; edicao de despesas operacionais
  manuais por `PUT /api/despesas/<id>/`, restrita a
  `caixa.change_despesaoperacional`.
- `/custos-fixos`: leitura de custos fixos por `GET /api/custos-fixos/`,
  preservando cadastro/edicao administrativa no Django quando necessario.
- `/custos-extras`: cadastro por `POST /api/eventos/custos-extras/`, com
  sessao Django, CSRF e permissao de adicionar custo extra.
- `/orcamentos`: listagem/cadastro/edicao pre-aprovacao por
  `GET/POST /api/orcamentos/` e `GET/PUT /api/orcamentos/<id>/`, com
  aprovacao por `POST /api/orcamentos/<id>/aprovar/`. O Next.js nao edita
  orcamentos aprovados, recusados ou cancelados.
- `/pagamentos`: fila de contas a pagar com saldo pendente para baixa por
  `POST /api/obrigacoes-financeiras/liquidar/`, respeitando
  `meta.settlementCapabilities`. Itens liquidados/cancelados permanecem em
  `Obrigacoes`, nao na fila operacional de pagamentos.
- `/fcf`: superficie operacional de financiamentos/parcelas, consumindo
  `GET /api/fcf/` e mantendo cadastro/edicao administrativa no Django Admin.
- `/fci`: superficie operacional de investimentos, consumindo
  `GET /api/fci/` e mantendo cadastro/edicao administrativa no Django Admin.
- `/backups`: superficie operacional de backup, consumindo
  `GET /api/backups/` e `POST /api/backups/criar/`, restrita a superusuario.
- `Admin`: link externo para `/admin/`, que permanece como o unico acesso
  visual direto permitido ao backend e so deve aparecer para superusuario no
  menu Next.js.

As telas Django correspondentes existem apenas como legado transitorio ate
classificacao formal para remocao, redirect/readonly temporario ou excecao de
suporte. Nao devem receber novas features operacionais.

Classificacao documental atual:

- Migradas para superficie Next.js, com Django preservado como fallback legado:
  custos por evento, receitas, despesas, cadastro de custo extra, central de
  pagamentos, orcamentos, custos fixos, FCF, FCI e backups.
- Pagamentos especializados de custos de servico, custos extras e parcela FCF
  foram classificados como migrados para `/pagamentos` com filtro `source`;
  a rota `pagar_parcela` tambem inclui `sourceId` derivado da parcela.
- Excecao operacional temporaria: Mes Financeiro permanece `partial`, pois o
  fluxo principal esta coberto por Obrigacoes/Fluxo de Caixa/relatorios, mas a
  aposentadoria total exige aceite fora desta conclusao local.

Ponte visual PM-06.1101:

- As telas Django migradas publicam `frontend_migration` no contexto e exibem
  aviso no template base com link para a rota Next.js equivalente.
- `NEXT_FRONTEND_URL` define a origem do frontend usada nesses links; em
  desenvolvimento o padrao e `http://localhost:3000`. Fora de `DEBUG`, se
  `NEXT_FRONTEND_URL` nao estiver configurado, o aviso nao e renderizado.
- A ponte e informativa e nao faz redirect automatico. Django segue como
  fallback legado ate decisao explicita de redirect controlado ou somente
  leitura.
- Pagamentos de custos de servico/extras e parcelas FCF usam status
  `migrated`, apontando para `/pagamentos?source=...`. A baixa continua
  protegida pelo backend e os redirects permanecem desligados por padrao.

Redirect controlado PM-06.1102:

- `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED` liga/desliga redirects de telas
  Django migradas para Next.js.
- `NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES` define a allowlist de rotas
  liberadas, usando as chaves de superficie documentadas no backend, como
  `receitas_lista` ou `custos_por_evento`.
- Redirect preserva query string e so roda para metodos seguros `GET`/`HEAD`.
  Requisicoes `POST` continuam no Django.
- O padrao e seguro: flag desligada e allowlist vazia. Producoes/homologacoes
  devem ativar uma tela por vez e manter rollback via variaveis de ambiente.

Validador PM-06.1103:

- Antes de ativar uma tela, rodar
  `python manage.py validar_redirects_next_legado --surface=<surface> --exigir-unitario --falhar`.
- Para validar a configuracao efetiva do ambiente, rodar
  `python manage.py validar_redirects_next_legado --falhar --json`.
- O comando reprova superficies desconhecidas, `partial`, sem rota Django ou
  sem `NEXT_FRONTEND_URL`.
- A ativacao continua operacional: o comando nao altera variaveis, nao liga
  redirect e nao remove fallback Django.

Registro PM-06.1104:

- O JSON de `validar_redirects_next_legado` inclui `executionRecord.markdown`
  para colar no plano mestre.
- `activation.recommendedEnvironment` mostra os valores de ambiente para uma
  janela aprovada.
- `activation.rollbackEnvironment` mostra o rollback minimo:
  `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False` e allowlist vazia.
- `activation.commands` publica os comandos de validar candidato, validar
  ambiente efetivo e validar rollback.

Evidencias PM-06.1105:

- `validar_redirects_next_legado` aceita `--salvar-json`, `--salvar-registro`
  e `--diretorio-evidencias`.
- Com `--diretorio-evidencias`, os arquivos padrao sao
  `pm06-redirect-next-legado.json` e `pm06-redirect-next-legado.md`.
- `--exigir-arquivos-evidencia` deve ser usado em homologacao/producao para
  garantir que a validacao gere evidencia persistida.
- Persistir evidencia nao ativa redirects; a mudanca operacional continua nas
  variaveis de ambiente da janela.

Reconciliacao PM-06.1106 a PM-06.1108:

- Mudancas operacionais feitas fora da ordem foram reconciliadas no plano
  mestre em PM-06.1106: FCI em Next.js, Backups em Next.js, permissao
  `canManageBackups`, Admin como unico acesso visual direto ao backend e
  conversao de links/action hints legados para rotas Next.js.
- PM-06.1107 inventariou os acessos visuais restantes: o frontend deve manter
  apenas Admin, download/API tecnica ou rotas Next.js para operacao.
- PM-06.1108 atualizou a ponte Django -> Next.js para FCI, FCF, Backups e
  pagamentos especializados.
- PM-06.1109 concluiu o canario unitario por superficie com `backups_lista`,
  validando candidato, allowlist local, permissao de superusuario, query string
  e rollback. Na sequencia, `lista_investimentos`, `lista_financiamentos` e
  `pagamentos_custos_extras` foram validadas no mesmo padrao. O canario de
  `pagamentos_custos_extras` tambem confirmou POST invalido sem redirect e sem
  erro 500. Em seguida, `pagamentos_custos_servico` foi validada com candidato,
  allowlist local, permissao, query string, POST invalido sem redirect e
  rollback. `pagamentos_fcf` tambem foi validada para
  `/pagamentos?source=parcela_divida`, preservando filtros FCF e rollback. A
  surface `pagar_parcela` foi validada com `sourceId` derivado da rota da
  parcela, POST invalido sem redirect/500 e rollback. `receitas_lista` foi
  validada para `/receitas`, com permissao, query string, POST legado sem
  redirect e rollback. `despesas_lista` foi validada para `/despesas` no mesmo
  padrao. Em seguida, `custos_fixos_lista`, `custos_por_evento`,
  `custo_extra_adicionar` e `pagamentos` foram validadas com evidencia,
  allowlist local, permissao, query string, POST legado sem redirect e
  rollback.
- PM-06.1110 classificou a politica local: superficies migradas usam redirect
  controlado por flag/allowlist para `GET`/`HEAD`, formularios `POST`
  permanecem fallback explicito, `mes_financeiro` fica `partial`, e Admin,
  downloads/API tecnica ficam fora da politica readonly de telas publicas.
  Registro historico superado por PM-06.1326/PM-06.1327, quando
  `mes_financeiro` e o shell operacional Django foram removidos.
- PM-06.1111 validou backend/frontend em desenvolvimento local:
  `manage.py check`, `makemigrations --check --dry-run`, suite `caixa` com 528
  testes, `corepack pnpm lint`, `typecheck`, `build` e `git diff --check`.
- PM-06.1112 fechou a revisao local. Nenhuma tela/template Django deve ser
  removida fisicamente antes de repetir as evidencias com URL real do Next.js
  em homologacao/producao e obter aceite operacional de rollback.
- PM-06.1115 validou os dominios reais de producao informados pelo operador do
  projeto antigo. No RH SaaS, substituir por `<frontend-rh-saas>` e
  `<backend-rh-saas>`.
  As rotas Next.js migradas responderam HTTP 200; o backend base respondeu HTTP
  200 e API protegida sem sessao respondeu HTTP 401 esperado. O management
  command foi executado com `NEXT_FRONTEND_URL=<frontend-rh-saas>`, 13
  superficies unitarias, agregado e rollback, salvando evidencias em
  `evidencias/pm06-1115-prod-url-real-2026-05-31/`. A ativacao em producao
  ainda depende de persistir flag/allowlist no runtime e manter rollback por
  `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False` ou allowlist vazia.
- PM-06.1116 confirmou o runtime efetivo em producao: o operador executou
  `python manage.py validar_redirects_next_legado --falhar --json` no servidor
  e o resultado retornou `ready=True`, `issues=[]`, `redirectsEnabled=True`,
  `frontendBaseUrl=<frontend-rh-saas>` e as 13 superficies migradas na
  allowlist configurada. O registro local ficou em
  `evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31/`.
- PM-06.1117 confirmou smoke autenticado de producao por relato do operador:
  receitas, despesas, pagamentos, obrigacoes, FCI, FCF, backups, clientes,
  custos por evento, custos extras e admin abriram suas respectivas paginas
  normalmente. O servidor tambem salvou JSON/Markdown do validador em
  `evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31/`.
- Checagem externa anonima das rotas antigas em `<backend-rh-saas>`
  retornou `/login/?next=...`, pois a autenticacao Django intercepta antes da
  view. O smoke autenticado foi confirmado em PM-06.1117.
- PM-06.1119 alinhou as permissoes do Next.js ao Django para as telas
  operacionais: o payload de sessao publica permissoes granulares, o menu filtra
  links por permissao, `Admin` e `PM-03 Evidencias` ficam restritos a
  superusuario, links sem rota implementada foram retirados do menu, e
  `/custos-por-evento` passou a usar API dedicada com permissao
  `caixa.view_evento`. O endpoint de obrigacoes tambem aceita leitura
  source-scoped e `permissionScope=payments` para seguir permissoes nativas de
  baixa sem exigir ledger geral.
- PM-06.1120 atualizou o guardrail frontend
  `npm run check:financial-canonical` para reconhecer as telas PM-06 novas,
  documentar boundaries de compatibilidade/allowlist de services, hooks, app
  routes, auth e navegacao, e voltar a aprovar o recorte canônico sem remover
  aliases publicados.

- PM-06.1121 ajustou o logout do header compartilhado do Next.js: depois do
  `POST /api/auth/logout/`, a rota atual e recarregada pelo frontend e a tela
  cai no estado de login Next.js, sem depender de rota `/login` separada.
- PM-06.1122 revisou a tela `/pagamentos` como fila de pendencias: ela mostra
  apenas contas a pagar com saldo em aberto e passou a exibir estado vazio
  explicito quando custos extras ou outras origens existem em `Obrigacoes`, mas
  ja estao liquidados/cancelados ou sem saldo. A regressao backend confirmou
  `custo_extra` em `permissionScope=payments` com
  `caixa.add_pagamentoeventocustoextra`.
- PM-06.1139/PM-06.1140 adicionaram o gate final
  `python manage.py validar_fechamento_pm06`. O comando e read-only, bloqueia
  PM-07 por padrao e exige evidencias finais com identidade estrita:
  preparacao PM-06.2 (`source=pm06_backup_rollback_preparation`,
  `step=PM-06.2`, `readOnly=True`), redirects com superficies e plano de
  ativacao/rollback, validacao frontend, aceite operacional, revisoes finais,
  evidencias atualizadas e liberacao explicita. Com `--diretorio-evidencias`,
  ele procura `pm06-validacao-backup-rollback.json` e
  `pm06-redirect-next-legado.json`, salvando `pm06-fechamento.json/md`.
  O payload tambem inclui `financeiroV3Policy`, derivado de `meta.nomenclature`,
  para registrar versao atual, versao futura de remocao, campos fisicos
  pendentes e renomes planejados antes de qualquer corte.
- PM-06.1142 adicionou
  `python manage.py validar_prontidao_congelamento_pm06`, outro comando
  read-only. Ele diagnostica se congelamento de escrita legada pode ser
  iniciado, bloqueando quando ainda houver escrita `legacyAdapterSynced`,
  origens adapter-only, campos fisicos pendentes ou falta de evidencias finais.
  O resultado nunca libera migration de limpeza: `mayCreateCleanupMigrations`
  permanece falso e exige gate proprio futuro.
  A partir de PM-06.1143, o fechamento final tambem exige o JSON
  `pm06-prontidao-congelamento-legado.json`; com `--diretorio-evidencias`, o
  gate final procura esse arquivo junto com os JSONs de backup/rollback e
  redirects.
- PM-06.1144 adicionou
  `python manage.py validar_prontidao_migracao_limpeza_pm06`, comando
  read-only posterior ao fechamento. Ele exige fechamento PM-06 aprovado,
  congelamento legado aprovado, backup, homologacao sem divergencias, auditoria
  sem divergencias, aceite operacional, rollback, conciliacao, plano de
  migration pequena, revisoes finais e liberacao explicita. Mesmo aprovado, so
  permite criar migrations; aplicar migrations continua bloqueado por janela
  propria.
- PM-06.1145 adicionou
  `python manage.py validar_rollback_conciliacao_pm06`, comando read-only para
  validar backup, janela, rollback, conciliacao, politica de dados criados entre
  backup e janela, responsavel, homologacao, aceite e revisoes. Com
  `--exigir-arquivos-plano`, rollback, conciliacao e politica de dados delta
  precisam existir como arquivos locais. O comando nao executa rollback nem
  conciliacao; ele gera `pm06-rollback-conciliacao-janela.json/md`, evidencia
  exigida pelo gate de migration de limpeza.
- PM-06.1146 passou a exigir essa mesma evidencia no fechamento final
  `validar_fechamento_pm06`. O fechamento aceita o JSON somente quando ele
  libera uso como evidencia, mas mantem `mayExecuteRollback=False` e
  `mayExecuteConciliation=False`.
- PM-06.1147 confirmou por regressao que `validar_fechamento_pm06`, quando
  recebe `--diretorio-evidencias`, resolve automaticamente os quatro JSONs
  finais: `pm06-validacao-backup-rollback.json`,
  `pm06-redirect-next-legado.json`,
  `pm06-prontidao-congelamento-legado.json` e
  `pm06-rollback-conciliacao-janela.json`.
- PM-06.1148 endureceu a validacao do JSON de redirects: alem de `ready=True`,
  o fechamento exige `activation.rollbackEnvironment` com
  `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False`.
- PM-06.1149 confirmou por regressao que
  `validar_prontidao_migracao_limpeza_pm06`, quando recebe
  `--diretorio-evidencias`, resolve automaticamente `pm06-fechamento.json`,
  `pm06-prontidao-congelamento-legado.json` e
  `pm06-rollback-conciliacao-janela.json`.
- PM-06.1150 confirmou por regressao que
  `validar_rollback_conciliacao_pm06` bloqueia janela invertida
  (`--janela-inicio` maior que `--janela-fim`) mesmo com as demais referencias
  operacionais preenchidas, mantendo a evidencia fora do gate de migration de
  limpeza.
- PM-06.1151 confirmou por regressao que o modo
  `--exigir-arquivos-plano` rejeita caminhos inexistentes para rollback,
  conciliacao e politica de dados delta, evitando evidencia estrita baseada
  apenas em texto livre.
- PM-06.1152 confirmou por regressao que
  `--exigir-arquivos-evidencia` tambem reprova o rollback/conciliacao quando
  nao houver destino de JSON e markdown, mantendo os gates finais dependentes
  de artefatos persistidos.
- PM-06.1153 confirmou por regressao que
  `validar_prontidao_migracao_limpeza_pm06` rejeita evidencia de
  rollback/conciliacao que permita executar rollback ou conciliacao; o gate de
  limpeza so aceita evidencia read-only.
- PM-06.1154 confirmou por regressao que
  `validar_prontidao_congelamento_pm06` bloqueia congelamento legado quando a
  politica de remocao de aliases nao aponta para `financeiro-v3`.
- PM-06.1155 confirmou por regressao que
  `validar_prontidao_congelamento_pm06 --exigir-arquivos-evidencia` reprova
  execucao sem destino de JSON e markdown, impedindo prontidao sem artefatos
  persistidos.
- PM-06.1156 confirmou por regressao que
  `validar_prontidao_migracao_limpeza_pm06 --exigir-arquivos-evidencia`
  tambem reprova execucao sem destino de JSON e markdown.
- PM-06.1157 confirmou por regressao que
  `validar_fechamento_pm06 --exigir-arquivos-evidencia` bloqueia PM-07 quando
  o proprio fechamento nao tem destino de JSON e markdown, mesmo com as
  evidencias finais validas.
- PM-06.1158 passou os quatro gates finais a rejeitar `--salvar-json` ou
  `--salvar-registro` apontando para diretorio/pai invalido, retornando
  pendencia em `outputEvidenceFiles` sem tentar sobrescrever o destino errado.
- PM-06.1159 cobriu por regressao o caso em que o diretorio pai da evidencia
  ja existe como arquivo comum, mantendo rollback/conciliacao bloqueado sem
  tentar criar diretorio sobre esse arquivo.
- PM-06.1160 passou os quatro gates finais a rejeitar `--salvar-json` e
  `--salvar-registro` apontando para o mesmo caminho, evitando sobrescrita de
  JSON por markdown ou vice-versa.
- PM-06.1161 passou os quatro gates finais a exigir extensoes coerentes para
  evidencia persistida: `.json` para JSON e `.md`/`.markdown` para registro.
- PM-06.1162 passou `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` a rejeitar saida de evidencia que
  sobrescreva JSON de entrada carregado pelo proprio gate.
- PM-06.1163 adicionou `inputEvidenceFiles` nos mesmos gates para rejeitar
  pacote em que duas evidencias de entrada apontam para o mesmo arquivo.
- PM-06.1164 ampliou `inputEvidenceFiles` para exigir extensao `.json` nas
  evidencias de entrada, mesmo quando o conteudo carregaria como JSON valido.
- PM-06.1165 endureceu as evidencias finais: fechamento, congelamento legado
  e rollback/conciliacao precisam trazer decisao `status=approved`, nao apenas
  `ready=True` e flags booleanas liberadas.
- PM-06.1166 passou fechamento final e migration de limpeza a rejeitar
  evidencia contraditoria com `ready=True`, mas `checksSummary` ainda pendente
  ou `pendingCount` diferente de zero.
- PM-06.1167 passou os mesmos validadores a exigir `issues` como lista nos
  JSONs de entrada, bloqueando payload manual/inconsistente com pendencia em
  texto livre.
- PM-06.1168 endureceu `checksSummary`: quando presente, ele precisa declarar
  `ready=True`, `pending` como lista vazia e contadores de pendencia/issues
  zerados.
- PM-06.1169 passou os mesmos validadores a checar a lista `checks`, recusando
  item malformado ou check interno com `ok` diferente de `True`.
- PM-06.1170 completou a validacao de `checks`: item com `issues` preenchido
  ou `issues` em formato invalido tambem bloqueia o artefato de entrada.
- PM-06.1171 passou `checksSummary.total` e `checksSummary.okCount` a serem
  comparados com a lista real de `checks` quando ambos existem no artefato.
- PM-06.1172 passou as decisoes de fechamento, congelamento e
  rollback/conciliacao a rejeitar `blockedBy` preenchido ou malformado mesmo
  quando `status=approved`.
- PM-06.1173 passou os mesmos validadores a bloquear decisoes malformadas que
  nao sejam objetos JSON, retornando pendencia controlada em vez de erro de
  execucao.
- PM-06.1174 passou decisoes finais com `step` explicito diferente de `PM-06`
  a bloquear fechamento e migration de limpeza.
- PM-06.1175 passou o gate de migration de limpeza a rejeitar fechamento PM-06
  cujo `closureDecision.nextStep` explicito nao aponte para `PM-07`.
- PM-06.1176 passou o mesmo gate a rejeitar fechamento que declare
  `mayMarkCurrentStepDone=False`, mantendo compatibilidade quando o campo esta
  ausente.
- PM-06.1177 passou o gate de migration de limpeza a rejeitar
  `closureNextAction.nextStep` explicito diferente de `PM-07`.
- PM-06.1178 completou a checagem de `closureNextAction`: quando presente, a
  acao precisa estar pronta para `advanceToPm07` e liberar sequencia/proxima
  etapa.
- PM-06.1179 passou fechamento e gate de migration de limpeza a rejeitar
  evidencia de rollback/conciliacao cujo bloco `window` exista sem
  `ordered=True`; artefatos antigos sem `window` seguem aceitos por
  compatibilidade.
- PM-06.1180 completou a validacao desse bloco `window`: quando presente, ele
  tambem precisa declarar `startValid=True` e `endValid=True`.
- PM-06.1181 completou o contrato downstream do `window`: quando presente, ele
  tambem precisa trazer `ref`, `start` e `end` preenchidos.
- PM-06.1182 passou o fechamento final a rejeitar evidencia de redirects com
  `surfaces=[]`, evitando pacote `ready=True` sem superficie migrada declarada.
- PM-06.1183 passou o fechamento final a rejeitar item malformado em
  `surfaces`; cada superficie precisa ser objeto com chave `surface`.
- PM-06.1184 passou o fechamento final a rejeitar evidencia de redirects com
  `activation.readyToActivate=False` explicito.
- PM-06.1185 passou o fechamento final a rejeitar
  `activation.recommendedSurfacesValue` vazio quando esse campo vier declarado.
- PM-06.1186 passou o fechamento final a validar
  `activation.recommendedEnvironment` quando presente, exigindo frontend URL,
  redirects ligados e allowlist recomendada nao vazia.
- PM-06.1187 formalizou a decisao segura original para o Next.js na PM-06:
  campos canonicos seguem como preferenciais nos fluxos principais, enquanto
  aliases legados permaneciam apenas em bordas de compatibilidade ate o corte
  `financeiro-v3`. PM-06.1305/PM-06.1306 substituem essa politica para a linha
  de base vazia premium: aliases sem valor operacional novo podem ser removidos
  antes do corte, desde que haja guardrail, teste e documentacao.
- PM-06.1188 amarrou essa politica aos gates finais: fechamento PM-06 e
  prontidao de congelamento legado rejeitam `frontend-validacao-ref` generico
  que nao comprove `verify:publish` ou `check:financial-canonical`.
- PM-06.1189 propagou a mesma regra para o gate de migration de limpeza quando
  o JSON de fechamento PM-06 trouxer `references.frontendValidationRef`.
- PM-06.1190 tornou a politica antiga explicita nos JSONs/registros de
  fechamento, congelamento legado e migration de limpeza; PM-06.1305/PM-06.1306
  passam a tratar esses campos como evidencia historica, nao como regra final
  para a base vazia premium.
- PM-06.1191 passou fechamento e migration de limpeza a validar tambem a
  evidencia de congelamento legado quando ela trouxer
  `references.frontendValidationRef` ou `frontendCanonicalValidationPolicy`,
  bloqueando congelamento com validacao frontend generica declarada.
- PM-06.1192/PM-06.1193 registraram gates antigos de `financeiro-v3` para corte
  de aliases. Na linha atual de base vazia, esses gates devem ser revisados ou
  substituidos por evidencias de remocao canonica direta quando a remocao nao
  depender de historico de dados.
- PM-06.1194 passou fechamento e migration de limpeza a recalcular datas da
  janela de rollback/conciliacao quando `window` estiver presente, bloqueando
  datas ISO invalidas ou intervalo invertido mesmo que o JSON declare
  `startValid/endValid/ordered=True`.
- PM-06.1195 corrigiu o proprio gerador `validar_rollback_conciliacao_pm06`
  para tratar datas ISO impossiveis como pendencia controlada, marcando
  `startValid/endValid=False` em vez de interromper a execucao.
- PM-06.1196 passou o mesmo comando a publicar `planFiles` e bloquear saida de
  evidencia que sobrescreva arquivos de rollback, conciliacao ou politica de
  dados delta usados como entrada.
- PM-06.1197 passou fechamento e migration de limpeza a validar `planFiles`
  quando esse bloco existir na evidencia de rollback/conciliacao, recusando
  plano de rollback, conciliacao ou politica de dados delta vazios.
- PM-06.1198 passou os mesmos consumidores a validar `references` da evidencia
  de rollback/conciliacao quando presente, recusando backup, janela, planos,
  responsavel, homologacao, aceite ou revisoes finais ausentes.
- PM-06.1199 passou fechamento e migration de limpeza a comparar `planFiles`
  com `references` quando ambos existem na evidencia de rollback/conciliacao,
  bloqueando divergencia entre rollback, conciliacao ou politica de dados delta.
- PM-06.1200 passou os mesmos consumidores a exigir
  `references.windowStart/windowEnd` quando `references` existir e a comparar
  `window` com `references`, bloqueando divergencia de referencia, inicio ou
  fim da janela de rollback/conciliacao.
- PM-06.1201 passou fechamento e migration de limpeza a validar
  `references.windowStart/windowEnd` como datas ISO reais e ordenadas mesmo
  quando `window` nao estiver presente.
- PM-06.1210 a PM-06.1213 alinharam a fronteira de compatibilidade dos
  services dedicados do Next.js para Eventos, Custos Fixos, Clientes,
  Orcamentos, Receitas e Despesas. Aliases legados de resposta/filtro ficam
  restritos aos mapas/helpers desses services; componentes e hooks seguem
  consumindo campos canonicos normalizados, com
  `check:financial-canonical` vigiando a excecao.
- PM-06.1214 reforcou filtros de Eventos: busca, cliente ou status sem datas
  nem periodo explicito deixam de herdar mes atual ou periodo rapido anterior.
  O Next.js omite periodo artificial e o Django resolve o recorte efetivo.
- PM-06.1215 aplicou a mesma protecao ao overview compartilhado de Receitas,
  Despesas e Custos Extras no Next.js: contrato, evento, cliente ou status sem
  datas omitem periodo artificial, preservando combinacao quando o periodo for
  alterado explicitamente.
- PM-06.1216 centralizou a decisao interativa de filtros personalizados em
  `dashboard-filters.ts` no Next.js e aplicou o helper ao Dashboard, Custos por
  Evento, Obrigacoes, Pagamentos, Investimentos, Financiamentos e overview
  operacional. O backend deve continuar interpretando filtro personalizado sem
  datas/periodo como `todos`, e periodo enviado explicitamente continua sendo
  uma combinacao valida.
- PM-06.1217 removeu fallback visual direto de `descricao` nas telas FCI/FCF
  do Next.js. FCI normaliza `description`/`investmentDescription` no service
  central antes da UI; FCF consome `description`/`debtDescription` ja
  normalizados. Aliases permanecem apenas como borda/espelho legado ate
  `financeiro-v3`, e o guardrail canonico passa a bloquear acesso/propriedade
  `descricao` em UI/hooks financeiros.
- PM-06.1218 estendeu a mesma fronteira para categoria, tipo, tipo de fluxo,
  descricao de divida e quantidade de parcelas em FCI/FCF. Componentes consomem
  `category`, `categoryLabel`, `flowType`, `flowTypeLabel`, `debtDescription`,
  `type`, `typeLabel` e `installmentsCount`; aliases como `categoria`,
  `categoria_display`, `tipo_fluxo_display`, `descricao_divida` e
  `quantidade_parcelas` ficam bloqueados em UI/hooks.
- PM-06.1219 normalizou opcoes de filtro e status dos itens FCI no service
  central do Next.js. `categories`, `flowTypes`, `statuses`, `contracts` e
  `events` passam a ser preenchidos a partir de aliases quando necessario, e
  `status_display` deixa de ser lido em UI/hooks.
- PM-06.1220 completou a normalizacao dos itens FCI para datas, valores e baixa
  manual. Componentes consomem `plannedDate`, `realizedDate`, `plannedAmount`,
  `realizedAmount`, `pendingRealizationAmount`, `pendingAmount` e
  `manuallySettled`; aliases como `data_prevista`, `valor_realizado`,
  `saldo_restante` e `baixado_manualmente` ficam restritos ao service.
- PM-06.1221 normalizou tambem os filtros FCI no service central do Next.js.
  O view model publica `startDate`, `endDate`, `category`, `flowType`,
  `contractCode`, `eventId`, `clientId`, `quickPeriod` e `status`; a exportacao
  CSV do FCI consome apenas esses campos e os labels canonicos ja normalizados.
- PM-06.1222 incluiu o exportador CSV financeiro do Next.js no guardrail
  canonico. Relatorios gerados no frontend contam como superficie visual e nao
  podem ler aliases legados de membros fora dos services/normalizadores.
- PM-06.1223 adicionou `FinancialInvestmentFiltersApi` no contrato TypeScript
  do Next.js. FCI deixa de representar filtros como `Record<string,string>`
  generico e passa a explicitar campos canonicos e aliases de borda.
- PM-06.1224 normalizou totais, fluxos e subtotais de grupos FCI no service
  central do Next.js. Tela e CSV passam a consumir campos `*Amount` canonicos
  ja preenchidos, sem fallback visual para aliases de transicao.
- PM-06.1225 ampliou o guardrail canonico do Next.js para aliases de
  totais/subtotais FCI, impedindo regressao em UI/hooks/CSV.
- PM-06.1226 aplicou a mesma trava preventiva a aliases de totais e
  estatisticas FCF no guardrail canonico do Next.js, mantendo esses nomes
  restritos aos services/normalizadores.
- PM-06.1227 removeu `AccountPayable.description` como fallback visual da
  tabela de contas a pagar, auditoria de reconciliacao do dashboard e CSV. O
  Next.js passa a consumir `obligationDescription`/`payableDescription` ja
  normalizados para esse contrato.
- PM-06.1228 removeu aliases operacionais do header compartilhado do Next.js e
  ampliou o guardrail para aliases especificos de contrato/evento/cliente em
  UI/hooks/CSV. O header deve receber opcoes ja normalizadas pelo service.
- PM-06.1229 alinhou FCI e FCF ao filtro operacional por numero de contrato:
  `/api/fci/` e `/api/fcf/` aceitam `contractCode`/`contrato_codigo` e resolvem
  esse codigo visual por `Evento`/`Orcamento.numero`, sem `contractId`. No
  Next.js, essas telas usam o modo visual de contrato por codigo.
- PM-06.1230 completou `/api/fci/` com filtro operacional por cliente:
  `clientId`, `cliente_id` e `cliente` sao tratados como IDs, cobrem
  investimentos por contrato, evento e contrato do evento, e o payload publica
  `filterOptions.clients`/`clientes` para o header Next.js.
- PM-06.1231 alinhou a exportacao CSV de FCI ao mesmo contrato visual de FCF:
  o relatorio resolve contrato por `contractCode`, inclui o cliente filtrado nas
  linhas de resumo/agrupamento e mantem aliases gerais apenas na borda de
  normalizacao do service.
- PM-06.1232 fechou a hidratacao de links por numero de contrato no helper
  compartilhado de filtros do Next.js. Telas em modo `contractCode` aceitam
  `contractCode` e `contrato_codigo` na query string, mas entregam para a UI
  apenas o filtro normalizado conforme o modo da tela.
- PM-06.1233 alinhou os hooks FCI/FCF ao mesmo modo de contrato por codigo
  usado pelas telas e services, impedindo que numeros como `03685/25` sejam
  descartados como IDs invalidos antes da chamada ao backend.
- PM-06.1234 alinhou o CSV de Custos por Evento aos cards operacionais,
  incluindo despesas operacionais manuais calculadas pela leitura canonica de
  obrigacoes sem misturar com custos extras.
- PM-06.1235 adicionou regressao Playwright no frontend para o filtro por
  numero de contrato nas telas principais e regressao Django para o endpoint de
  Mes Financeiro. Dashboard, Custos por Evento, Receitas, Despesas, Obrigacoes,
  Pagamentos, FCF e FCI devem preservar `contractCode=03685/25` na request
  visual e no chip de filtro ativo, inclusive em loading/erro quando o backend
  estiver indisponivel. A regressao tambem confirma que esse filtro nao herda
  periodo rapido anterior nem cria `period=all`, `quickPeriod=todos` ou
  `periodo_rapido=todos` artificiais. O teste observa
  `NEXT_PUBLIC_API_BASE_URL` quando configurada; quando nao estiver, o
  `playwright.config.ts` injeta
  `http://127.0.0.1:8000/api` para o servidor E2E. O Django resolve esse numero
  por `contractCode` nos selectors/APIs, sem exigir que o operador conheca ID
  interno.
- PM-06.1236 padronizou a preservacao visual de filtros ativos em estados
  excepcionais do Next.js. Custos por Evento, FCF e FCI passam os mesmos
  `layoutFilterProps` ao `DashboardLayout` tambem em login/forbidden, mantendo
  filtro vindo da URL ou do estado local visivel enquanto o Django resolve
  sessao, permissao ou leitura da API.
- PM-06.1237 adicionou o guardrail frontend
  `check:dashboard-filter-layout`, agora integrado ao `check:dashboard`. Ele
  descobre telas financeiras filtraveis pelos padroes `layoutFilterProps`,
  `fallbackLayoutFilterProps`, `filters={filters}`, `onFiltersChange=` ou
  `contractFilterValueMode` e bloqueia `DashboardLayout` sem props de filtro
  ativo, protegendo filtros em sucesso, loading, erro, login e forbidden.
- PM-06.1238 padronizou a evidencia E2E opcional dessa integracao no frontend:
  `corepack pnpm run verify:e2e:contract-filters`. O comando executa a mesma
  regressao Playwright de contrato por numero e deve ser usado quando for
  necessario comprovar chip visual e request real em navegador. O alias
  `verify:pm06:e2e` continua aceito por compatibilidade, enquanto
  `verify:publish` permanece reservado para lockfile, lint, typecheck,
  guardrails e build sem depender de backend local.
- PM-06.1239 alinhou a API de criacao de custo extra ao serializer central de
  dimensao operacional. `eventNumber` continua expondo o numero tecnico do
  evento, enquanto `contractCode`, `contractLabel`, `clientId` e `clientName`
  saem da mesma dimensao normalizada, removendo prefixos `EVT-` de eventos
  legados quando o valor representar contrato visivel ao operador.
- PM-06.1240 moveu `codigo_contrato_visivel_evento` para o servico central de
  dimensao operacional financeira. Com isso, opcoes operacionais, payloads de
  FCI/FCF, Mes Financeiro e demais leituras financeiras compartilham a mesma
  regra: `contractCode` e contrato visivel, `eventNumber` e numero tecnico do
  evento.
- PM-06.1241 alinhou a tela Next.js de Custos por Evento a essa regra: o campo
  Contrato nao usa `eventNumber` como fallback. Se `contractLabel`/`contractCode`
  nao vierem preenchidos, a UI mostra contrato nao informado em vez de exibir o
  numero tecnico do evento.
- PM-06.1242 adicionou o guardrail frontend `check:dashboard-contract-event`,
  integrado ao `check:dashboard`, para bloquear componentes que tentem montar
  texto de contrato usando `eventNumber`.
- PM-06.1243 adicionou guardrail Django em testes para bloquear
  `evento.contrato_codigo` direto em serializers/selectors/views de
  API/services financeiros. A publicacao visual de `contractCode` deve passar
  por `codigo_contrato_visivel_evento`.
- PM-06.1244 reforcou a regra de performance da dimensao operacional e
  financeira: serializers usam apenas relacoes ja carregadas, e selectors devem
  aplicar `select_related` quando o payload precisar publicar contrato completo.
  O serializer nao faz lazy load para preencher `contractCode`, divida ou credor
  cadastrado.
- PM-06.1245 adicionou guardrail Django contra acesso encadeado direto a
  relacoes em `serializers_*.py`, como `obj.evento.campo`,
  `obj.contrato_operacional.campo`, `obj.divida.campo`, `obj.cliente.campo` ou
  `obj.credor_cadastro.campo`. Relacoes publicadas para o Next.js devem passar
  por `relacao_carregada` e por selectors com `select_related`.
- PM-06.1246 estendeu essa regra aos montadores centrais do Dashboard e Mes
  Financeiro. Referencias de receita/despesa e parcelas FCF usam
  `relacao_carregada`/dados de parcela sem lazy load; selector incompleto gera
  fallback neutro, nao consulta escondida durante a montagem do payload.
- PM-06.1247 alinhou o service Next.js a separacao contrato/evento: `contractCode`
  nao e derivado de `eventNumber`, e `eventNumber` nao e derivado de
  `contractCode`. O guardrail frontend agora varre components e services para
  impedir essa regressao.
- PM-06.1248 adicionou guardrail Django nos montadores centrais do Dashboard e
  Mes Financeiro, bloqueando acesso direto a `receita.evento`,
  `despesa.evento`, `parcela.divida` e `parcela.rotulo_parcela`.
- PM-06.1249 estendeu a regra aos serializers de baixas canonicas, alocacoes e
  lancamentos financeiros. IDs tecnicos continuam publicados sem consulta; nomes
  e colecoes reversas dependem de `select_related`/`prefetch_related`.
- PM-06.1250 ampliou o guardrail dos serializers para bloquear relacoes de
  origem financeira e `alocacoes` reversas sem prefetch, preservando `*_id`
  como leitura tecnica permitida.
- PM-06.1251 aplicou a mesma fronteira às views/APIs financeiras de orcamento,
  evento, receita, despesa, custo extra e FCF legado. Views que serializam JSON
  usam `relacao_carregada`/`relacoes_multiplas_carregadas` e guardrail dedicado.
- PM-06.1252 adicionou guardrail Next.js para fronteira HTTP/service:
  componentes, hooks e rotas nao podem chamar `fetch`, `apiFetch` ou CSRF
  diretamente; chamadas ao Django ficam no client central e em services.
- PM-06.1253 ampliou o guardrail Next.js para imports diretos de `apiFetch` e
  `requestBackendCsrfToken`, mantendo tipos/estado de auth permitidos em UI.
- PM-06.1254 centralizou a dimensao operacional das APIs de eventos e
  orcamentos no serializer compartilhado. Eventos passam a publicar cliente e
  contrato visivel pela mesma regra usada em custos extras/financeiro, e
  orcamentos em rascunho usam o proprio numero como `contractCode` quando
  ainda nao ha contrato operacional/evento aprovado.
- PM-06.1255 alinhou o selector de obrigacoes financeiras canonicas ao helper
  `serializar_dimensao_operacional_financeira`. O read-model central de
  obrigacoes deixa de montar cliente/contrato/evento por relacao direta, e o
  guardrail de montadores passa a cobrir `selectors_obrigacoes_canonicas.py`.
- PM-06.1256 removeu montagem local de dimensao no payload do Dashboard.
  Contas a receber usam `serializar_dimensao_operacional_financeira`, e o
  enriquecimento de eventos dos cards de custos por evento usa
  `serializar_dimensao_operacional`.
- PM-06.1257 centralizou referencias textuais de receita nos montadores do
  Dashboard e Mes Financeiro. O texto `cliente / evento` passa a usar
  `clientDisplayName` e `eventName` publicados pela dimensao financeira central,
  sem acesso relacional direto nos montadores.
- PM-06.1258 centralizou opcoes e receitas do Mes Financeiro nos serializers de
  dimensao operacional. Contratos, eventos, clientes e `receita.evento` seguem
  o mesmo contrato visual de `contractCode`/`eventNumber`, mantendo aliases
  publicados apenas como espelhos de compatibilidade.
- PM-06.1259 alinhou `serializers_lancamentos.py` ao helper
  `serializar_dimensao_operacional_financeira`. O ledger deixa de recompor
  cliente/contrato/evento manualmente e passa a usar a mesma dimensao central
  dos demais payloads financeiros.
- PM-06.1260 alinhou baixas financeiras canonicas e alocacoes ao mesmo helper
  de dimensao operacional financeira. A modelagem canonica preserva IDs
  tecnicos como fallback, mas nomes/codigos/rotulos passam pela dimensao
  central.
- PM-06.1261 alinhou os rotulos dimensionais aplicados dos filtros de
  Obrigacoes aos serializers centrais de contrato, cliente e dimensao de
  evento, preservando o formato publico ja validado pelos testes.
- PM-06.1262 alinhou a referencia de evento das despesas operacionais em
  Custos por Evento ao helper de dimensao operacional financeira. O card segue
  usando `DespesaOperacional` como read-model central e reaproveita `eventName`
  normalizado.
- PM-06.1263 removeu acesso direto a `divida_financeira` no serializer de
  movimentacoes FCF. `serializers_financiamentos.py` passa a usar
  `relacao_carregada`, e o guardrail de serializers bloqueia `.divida_financeira`
  como regressao de lazy load. A regressao de zero queries cobre movimento FCF
  automatico com e sem a divida carregada.
- PM-06.1264 ampliou o guardrail dos serializers financeiros para bloquear
  tambem `getattr(obj, "relacao")` em relacoes de dominio. IDs tecnicos seguem
  permitidos, mas objetos relacionais devem passar por `relacao_carregada` e
  querysets preparados.
- PM-06.1265 aplicou a mesma protecao as views/APIs financeiras que montam JSON
  direto, bloqueando `getattr(obj, "relacao")` alem de acesso por ponto.
- PM-06.1266 incluiu `selectors_obrigacoes.py` na mesma fronteira de
  performance e contrato: referencias de evento, parcelas FCF e filtros de
  navegacao de financiamentos passam por `serializar_dimensao_operacional_financeira`,
  `dados_parcela_divida_sem_lazy` e `relacao_carregada`. O guardrail de
  montadores agora bloqueia `receita.evento`, `despesa.evento`, `custo.evento`,
  `parcela.divida` e `financiamento.divida_financeira` nesse selector.
- PM-06.1267 estendeu a regra ao selector especializado de financiamentos:
  agrupamento de parcelas por credor e listagem de dividas de parcelas passam a
  usar `relacao_carregada(parcela, "divida")`. A varredura ampla de
  selectors/serializers/views financeiras ficou sem acessos relacionais diretos.
- PM-06.1268 centralizou no Next.js a construcao de URLs para
  `/obrigacoes-financeiras` a partir de filtros do Dashboard. Dashboard, Custos
  por Evento e overviews operacionais passam a usar
  `getFinancialObligationsFrontendUrl`, e os guardrails canonico/service-boundary
  impedem que `toDashboardQuery` volte para componentes/hooks.
- PM-06.1269 completou a centralizacao de query strings de navegacao financeira
  no Next.js: o link Eventos -> Custos por Evento passou a usar `getFrontendUrl`
  e `check:dashboard-service-boundary` bloqueia `new URLSearchParams` fora de
  `navigation-urls.ts` na superficie financeira.
- PM-06.1270 formalizou a separacao entre helper de escrita e leitura de
  dimensao operacional no Django. `dados_dimensao_operacional` fica restrito a
  services de escrita/sincronizacao; selectors, serializers e views JSON devem
  usar `serializar_dimensao_operacional_financeira`, `relacao_carregada` ou
  helpers sem lazy load. O guardrail backend bloqueia regressao nessa fronteira.
- PM-06.1271 centralizou no Next.js a navegacao para `/pagamentos` em
  `getFinancialPaymentsFrontendUrl`. Obrigacoes, FCF e Custos Extras deixam de
  chamar `getFrontendUrl('/pagamentos', ...)` diretamente, e
  `check:dashboard-service-boundary` bloqueia regressao desse destino.
- PM-06.1272 centralizou o mapeamento source -> rota operacional em
  `getFinancialObligationSourceListFrontendUrl`. A tela de Obrigacoes nao
  conhece mais diretamente os caminhos `/receitas`, `/despesas`, `/custos-fixos`,
  `/fci` e `/fcf`; o guardrail bloqueia `getFrontendUrl` direto para esses
  destinos na superficie financeira.
- PM-06.1273 centralizou tambem a navegacao Admin financeira no Next.js.
  Eventos, FCI, Obrigacoes e Backups passam a usar helpers `getFinancialAdmin*`
  para `/admin/...`; `getBackendUrl` direto continua permitido apenas para
  downloads/caminhos tecnicos vindos do backend e action hints genericos.
- PM-06.1274 refinou Eventos -> Custos por Evento: o Next.js passou a usar
  `getFinancialEventCostsFrontendUrl`, que abre `/custos-por-evento` com
  `eventId` sem periodo artificial, evitando que filtros rapidos escondam
  eventos antigos ao navegar pela ficha do evento.
- PM-06.1275 reforcou `check:dashboard-service-boundary` para bloquear
  chamadas diretas a rotas financeiras operacionais em `getFrontendUrl` fora de
  `navigation-urls.ts`. Obrigacoes, Pagamentos, Custos por Evento e rotas de
  origem financeira devem usar helpers especificos.
- PM-06.1276 removeu a excecao da sidebar do Next.js que ainda chamava
  `getBackendUrl` para abrir o Django Admin. O item Admin agora usa
  `getFinancialAdminRootUrl`, mantendo links backend genericos fora de
  componentes de navegacao.
- PM-06.1277 centralizou no Next.js a limpeza de periodo herdado para filtros
  personalizados sem datas. Eventos e Custos Fixos deixam de duplicar regra de
  periodo rapido antigo; a request omite periodo artificial para o Django
  resolver.
- PM-06.1278 centralizou downloads tecnicos de backup em
  `getFinancialBackupDownloadUrl`. Componentes financeiros deixam de importar
  `getBackendUrl`; novos caminhos backend devem ganhar helper nomeado no
  boundary de navegacao do Next.js.
- PM-06.1279 endureceu helpers de origem financeira no Next.js. Origem vazia ou
  desconhecida em Admin/lista operacional nao monta URL com `undefined`; o link
  fica ausente ate o frontend mapear explicitamente a nova origem.
- PM-06.1280 endureceu helpers Admin por model no Next.js. Model vazio em
  lista, cadastro ou detalhe retorna sem link, evitando `/admin/caixa//...`.
- PM-06.1281 removeu fallback visual `href="#"` da navegacao financeira/Admin.
  Eventos e sidebar deixam de renderizar links externos quando o helper nao
  consegue montar URL real para o backend.
- PM-06.1282 adicionou guardrail no Next.js contra links mortos:
  `check:dashboard-service-boundary` bloqueia `href="#"` e fallbacks
  equivalentes nas superficies do dashboard.
- PM-06.1283 removeu botoes inertes das tabelas compactas de contas do
  dashboard. Sem `detailsHref`, contas a pagar/receber exibem texto
  informativo em vez de botao sem acao.
- PM-06.1284 reforcou guardrail no Next.js contra botao com aparencia de link
  sem destino/acao: `Button variant="link"` precisa ter `asChild` ou `onClick`.
- PM-06.1285 corrigiu o widget de resumo de contratos no dashboard. O texto
  `Ver todos os contratos` deixou de ser botao inerte ate haver rota
  operacional real para esse destino.
- PM-06.1286 centralizou Eventos -> Orcamentos no Next.js por
  `getFinancialBudgetsFrontendUrl`; a rota literal `/orcamentos` permanece
  restrita ao item da sidebar.
- PM-06.1287 consolidou a regra operacional backend-first: regras de negocio,
  filtros, permissoes, validacoes e calculos devem ficar no Django sempre que o
  backend tiver contexto para decidir. O filtro do dashboard por
  `contractCode=03685/25` tambem passa a resolver eventos `EVT-03685/25`
  criados a partir de orcamento sem `ContratoOperacional`.
- PM-06.1288 removeu do Next.js a criacao artificial de `period=all` para
  filtros operacionais sem datas. Quando contrato/evento/cliente/status vier
  sem periodo explicitamente escolhido, o frontend deve omitir o periodo e o
  Django resolve o recorte efetivo nos selectors/views.
- PM-06.1289 ampliou a resolucao backend-first de contrato/orcamento para os
  centralizadores financeiros. Mesmo em base zerada, um orcamento aprovado pode
  gerar evento `EVT-03685/25` sem `ContratoOperacional` separado; por isso o
  Django resolve `contractCode=03685/25` contra `Evento.numero` e
  `Evento.orcamento.numero`. O frontend continua enviando o numero visivel em
  `contractCode`, sem duplicar essa regra. O fluxo premium atual e
  `Cliente -> Orcamento -> Evento`, com `Orcamento.numero` como contrato
  visivel; `ContratoOperacional` nao deve ser criado nem usado em cadastros
  novos.
- PM-06.1290 removeu das bordas Next.js a conversao `period=all` para
  `quickPeriod=todos`. FCI/FCF, Investimentos, Eventos e Custos Fixos agora
  omitem periodo artificial quando o filtro personalizado sem datas deve ser
  resolvido pelo Django; o guardrail do dashboard bloqueia a volta desse padrao.
- PM-06.1291 fechou a borda de URL inicial no Next.js: Eventos e Custos Fixos
  com busca, cliente, status, categoria ou datas sem `quickPeriod` explicito
  preservam `quickPeriod` vazio na query tecnica. O select pode exibir o
  padrao visual, mas o Django segue como fonte da verdade para resolver o
  periodo efetivo. O E2E de filtros canonicos cobre essa entrada direta.
- PM-06.1292 reforcou no Next.js o guardrail de separacao contrato/evento:
  components, hooks, services, utils e `lib` nao podem usar `contractId`,
  `contratoId`, `contrato_operacional`, `contrato_operacional_id` ou
  `operationalContract`. O filtro visual continua por `contractCode`, e o
  vinculo operacional/contabil por `eventId`. Validacao backend focada:
  `makemigrations --check --dry-run` sem mudancas e 10 testes de
  `contractCode` sem `ContratoOperacional` verdes.
- PM-06.1293 alinhou os templates Django legados de Dashboard, FCI, FCF e Mes
  Financeiro ao mesmo contrato visual: o select "Contrato" usa
  `contrato_codigo` e `contrato.codigo` como value, sem `contrato.id` nem
  `contrato_operacional`. Guardrail backend bloqueia a volta desses termos nos
  templates financeiros.
- PM-06.1294 adicionou guardrail backend para codigo runtime: arquivos Python
  fora de migrations, testes e nomenclatura nao podem conter `contractId`,
  `contratoId`, `contrato_operacional`, `contrato_operacional_id` ou
  `ContratoOperacional`. O caminho novo fica limitado a `contractCode` visual e
  `eventId` operacional.
- PM-06.1295 ajustou nomenclatura interna do helper de contrato visual:
  `resolver_codigo_contrato_visual_parametros` passa por helper local de
  codigo visual, deixando claro que o backend nao resolve ID tecnico de
  contrato removido.
- PM-06.1296 ampliou o guardrail frontend de separacao contrato/evento para
  incluir `app`, impedindo que pages e rotas do Next.js hidratem ou repassem
  aliases tecnicos como `contractId` ou `contrato_operacional`.
- PM-06.1297 endureceu a regressao Playwright de filtros: requests observadas
  com `contractId`, `contratoId`, `contrato_operacional`,
  `contrato_operacional_id` ou `operationalContract` passam a reprovar o E2E.
- PM-06.1298 validou a estabilizacao apos esses guardrails: suite Django
  completa `manage.py test caixa` passou com 654 testes OK e 24 pulados.
- PM-06.1299 limpou guias atuais do frontend para remover qualquer orientacao
  de preferencia por `contractId`. Mes Financeiro, FCI e FCF ficam descritos
  com `contractCode`/`contrato_codigo` como filtro visual de contrato; aliases
  tecnicos de contrato operacional permanecem apenas como memoria historica ou
  compatibilidade backend, nao como estado/query nova do Next.js.
- PM-06.1300 protegeu links Django legados de periodo rapido: Dashboard, FCI e
  FCF agora usam `{{ filtros.contrato_codigo|urlencode }}` ao preservar o filtro
  "Contrato" em links, evitando quebrar codigos visuais com espaco, `&` ou
  outros caracteres de query. Guardrail de templates bloqueia
  `contrato_codigo={{ filtros.contrato_codigo }}` sem encoding e teste HTML
  cobre `CTR A&B` renderizado como `CTR%20A%26B`.
- PM-06.1301 validou o caminho basico de publicacao: `corepack pnpm run build`
  concluiu com sucesso no Next.js e `manage.py check` do Django nao reportou
  issues.
- PM-06.1302 adicionou `corepack pnpm run verify:pm06` no frontend, encadeando
  `verify:frontend` e o E2E de filtros por contrato. `verify:publish` permanece
  sem E2E para publicacao. O comando passou com lint, typecheck, guardrails,
  build e E2E Playwright de filtros por contrato.
- PM-06.1303 adicionou regressao Playwright para o uso manual do dashboard:
  abrir filtros, digitar `03685/25` em "Contrato" e aplicar deve chamar
  `/api/dashboard/financial-overview/` com `contractCode`, sem `contractId`,
  sem aliases de `ContratoOperacional` e sem `period=all` artificial. O teste
  focado passou localmente.
- PM-06.1304 concluiu a regra de `contractCode` sem periodo artificial nas
  telas principais: Dashboard, Custos por Evento, Receitas, Despesas,
  Obrigacoes, Pagamentos, FCF e FCI nao enviam `period`, `quickPeriod` nem
  `periodo_rapido` quando a request ja possui `contractCode` e nao possui datas
  manuais. O E2E bloqueia esse vazamento e `verify:pm06` passou com 12 testes
  Playwright.
- PM-06.1305 registrou a nova premissa de base operacional vazia/premium e
  iniciou a remocao de compatibilidade historica no Next.js: a hidratacao
  inicial compartilhada aceita apenas `period`, `startDate`, `endDate`,
  `contractCode`, `eventId`, `clientId`, `service` e `status`. Aliases antigos
  de URL como `costCenterId`, `contrato_codigo`, `evento_id`, `cliente_id`,
  `periodo_rapido`, `data_inicial` e `data_final` deixam de ser contrato novo.
- PM-06.1306 estendeu a limpeza para a hidratacao inicial das telas
  operacionais e para entradas FCI/FCF: orcamentos, clientes, eventos, custos
  fixos e FCI usam somente nomes canonicos; FCI aceita `category`, `flowType` e
  `quickPeriod`; FCF aceita `creditorId`, `type`, `sourceType` e `quickPeriod`.
  Aliases de query como `busca`, `categoria`, `tipo_fluxo`, `credor_id`,
  `tipo`, `origem_movimentacao`, `automaticFromDebt` e `periodo_rapido` nao
  fazem parte do caminho premium.

## Arquitetura

Backend Django:

- banco de dados;
- autenticacao;
- permissoes;
- regras financeiras;
- selectors;
- services;
- validacoes;
- APIs JSON/DRF;
- admin;
- seguranca.

Frontend Next.js:

- UI;
- sidebar;
- cards;
- graficos;
- tabelas;
- filtros;
- loading states;
- empty states;
- consumo via services/hooks.

Diretriz de arquitetura principal/prime:

- O roteiro oficial para concluir a arquitetura financeira premium fica em
  `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md`, secao `Plano mestre para conclusao
  da arquitetura premium`. Ao retomar, seguir a proxima subetapa marcada no
  plano mestre; apos PM-03.1 concluida, o proximo bloco e PM-03.2 de
  `despesa_operacional`. O historico em `Fases` e evidencia, nao lista
  principal de proximos passos.
- O Django continua sendo a fonte da verdade para regras financeiras, banco,
  admin, validacoes, baixas, credores e comportamento especial de FCF/caixa.
- Quando uma decisao puder ser resolvida no backend, a regra deve ficar no
  Django. O Next.js pode normalizar entrada visual, chamar services, exibir
  estado e reforcar seguranca/UX, mas nao deve virar fonte primaria de regra de
  negocio, filtro, permissao, validacao ou calculo financeiro.
- Filtros operacionais sem `startDate`/`endDate` e sem periodo explicitamente
  escolhido nao devem receber `period=all` artificial do Next.js. O backend
  decide se o recorte efetivo e `todos`, `mes_atual` ou outro comportamento da
  superficie.
- A camada canonica deve ser promovida por origem via canonical-first, nunca por
  troca total imediata de todos os fluxos.
- A ativacao operacional usa `CANONICAL_FIRST_SETTLEMENT_ENABLED=True` somente
  no ambiente validado e `CANONICAL_FIRST_SETTLEMENT_SOURCES` com origens
  especificas ja suportadas.
- Evidencia operacional informada em 2026-05-25: `custo_fixo` ja foi usado em
  pagamento pelo frontend com canonical-first ativo. Tratar essa origem como
  validada quando a API/metadata do backend indicarem, sem transformar isso em
  ativacao automatica de outras origens.
- Antes de ampliar uma origem, executar backup do banco, registrar a versao do
  codigo, aplicar migrations, rodar pre-flight, canario rollback-only,
  auditoria de fonte de escrita, monitoramento da janela e auditoria de totais.
- PM-03.1 de `custo_fixo` foi fechada em producao do projeto antigo em
  2026-05-26 com
  monitor `ready=True`, `canonicalFirst.count=1`, valor 81.90,
  `legacyAdapterSynced.count=0`, auditoria de totais sem divergencia e
  `validar_fechamento_pm03` com todos os checks OK.
- Para repetir ou auditar a PM-03.1, o comando operacional e
  `python manage.py monitorar_janela_canonical_first --source=custo_fixo --data-ativacao=<DATA> --exigir-canonical-first --falhar-com-legado-na-janela --exigir-data-ativacao --diretorio-evidencias=<diretorio-evidencias-pm03-custo-fixo> --exigir-arquivos-evidencia --json --falhar`.
  Quando `--diretorio-evidencias` for usado, o backend salva JSON/markdown de
  monitoramento e publica `evidenceFiles` e `executionRecord.markdown`.
- A validacao da janela tambem salva evidencia:
  `python manage.py validar_janela_canonical_first --source=custo_fixo --data-ativacao=<DATA> --validar-preflight-operacional --falhar-com-preflight-operacional --exigir-feature-flag-ativa --diretorio-evidencias=<diretorio-evidencias-pm03-custo-fixo> --exigir-arquivos-evidencia --json --falhar`.
- A auditoria de fonte de escrita da mesma janela tambem pode salvar evidencia:
  `python manage.py auditar_fonte_escrita_baixas --source=custo_fixo --data-ativacao=<DATA> --write-model-source=canonicalFirst --exigir-canonical-first --exigir-data-ativacao --diretorio-evidencias=<diretorio-evidencias-pm03-custo-fixo> --exigir-arquivos-evidencia --json`.
- A auditoria de totais tambem pode salvar evidencia:
  `python manage.py auditar_totais_negocio --falhar-com-divergencia --validar-valores-editaveis --falhar-com-valores-editaveis --diretorio-evidencias=<diretorio-evidencias-pm03-custo-fixo> --exigir-arquivos-evidencia --json`.
- O fechamento documental da PM-03 confere esses artefatos antes de marcar a
  origem como concluida:
  `python manage.py validar_fechamento_pm03 --source=custo_fixo --data-ativacao=<DATA> --diretorio-evidencias=<diretorio-evidencias-pm03-custo-fixo> --json --falhar`.
  Para novas origens apos a PM-03.1, usar tambem
  `--exigir-validacao-ativacao` para validar o artefato de pre-window
  `pm03-validacao-ativacao-canonical-first.json`.
- A proxima etapa arquitetural e preparar PM-03.2 de `despesa_operacional`, sem
  hardcode no Next.js e sem ativar nova origem antes dos gates de pre-window.
- A preparacao local PM-03.2 ja confirmou paridade e pre-flight read-only, mas
  a base local nao tinha pendencia elegivel para canario. A ativacao real deve
  aguardar canario rollback-only no servidor/homologacao e preservar
  `CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional`.
- Os validadores de PM-03 retornam `pendingObligations.canaryCandidates` quando
  houver obrigacoes a pagar pendentes, para escolher o `sourceId` do canario sem
  consulta manual no banco; em janela controlada, usar tambem
  `--exigir-source-id-canario` e `--exigir-data-pagamento-canario`. Quando o
  `sourceId` for informado, o backend retorna `canary.sourceIdCheck` para
  confirmar elegibilidade; quando a data for exigida, o artefato registra
  `paymentDateRequired` e `paymentDateProvided`.
  O fechamento PM-03 tambem confere `canary=True`, `rollbackOnly=True`,
  `writesPersisted=False`, data explicita consistente, origem consistente e
  `sourceId`, `obligationId` e `obligationKey` iguais ao candidato aprovado no resultado do canario, alem de
  `canonicalSettlement.writeModelSource=canonicalFirst` e obrigacao canonica
  igual ao candidato aprovado. Tambem confere `deltaAmount` positivo e valores
  canonicos iguais a `requestedRealizedAmount`, com baixa/alocacao canonica
  registrada e ultima baixa em `canonicalFirst`, realizada, classificada como
  saida com fluxo/natureza, id/chave, `settlementDate` e `ledgerEntryId`.
  Tambem confere `canary.result.item`, exigindo mesma origem/sourceId, valor
  realizado, valor realizado no ledger e conciliacao do item atualizado que a
  API devolveria ao Next.js.
  O payload tambem publica `recommendedCommands.canaryRollbackOnly` para o
  operador executar o canario com menos risco de montar parametro errado.
  O campo `nextAction` resume se a operacao deve aguardar/criar pendencia,
  rodar canario, corrigir `sourceId` ou seguir para allowlist da janela.
  `validar_janela_canonical_first` tambem propaga esse resumo para o JSON e o
  markdown de evidencia da janela, e `monitorar_janela_canonical_first` faz o
  mesmo no monitoramento. O titulo do markdown do monitor e generico
  (`Registro PM-03 - monitoramento canonical-first`), mantendo PM-03.1 apenas
  como historico concluido de `custo_fixo`.
  O fechamento PM-03 de novas origens com `--exigir-validacao-ativacao`
  tambem confere `nextAction=activateAllowlistWindow` no artefato de ativacao.
- Como inventario PM-03.2A preparatorio, sem abrir PM-04,
  `verificar_prontidao_escrita_canonica --json` expoe
  `adapterOnlySources` e `pm04DecisionMatrix`, separando origens diretas de
  PM-03 das origens que ainda exigem decisao arquitetural:
  `custo_extra`, `custo_servico` e `parcela_divida`. O payload de
  `validar_ativacao_canonical_first --json` tambem inclui essa matriz em
  `writeReadiness` quando uma origem adapter-only for avaliada.
- Para a baseline PM-02, o backend publica o comando agregado
  `python manage.py validar_baseline_pm02 --falhar --json`, que nao substitui
  backup/tag, mas reduz erro manual ao reunir snapshot, checks e auditorias.
  Na janela estrita, usar `--modo-servidor-estrito` com
  `--frontend-ref=<commit-ou-deploy-vercel>` ou `--frontend-deploy-url=<url>`,
  e registrar tambem `--ambiente=producao` ou `--ambiente=homologacao`, para
  que o fechamento da PM-02 nao dependa de inferencia manual posterior.
  Quando a janela salvar artefatos com `--diretorio-evidencias=<diretorio>`, o
  backend publica `evidenceFiles.directory` para o frontend/documentacao
  conferirem o diretorio base da evidencia.
- O Next.js deve consumir contratos canonicos publicados pelo backend, sem
  recriar calculos nem assumir que uma origem virou canonical-first antes da API
  e da metadata operacional indicarem isso.
- Em producao com subdominios do RH SaaS, o backend deve ler
  `SESSION_COOKIE_DOMAIN=<dominio-cookie-rh-saas>` e
  `CSRF_COOKIE_DOMAIN=<dominio-cookie-rh-saas>` do `.env`.
- Em producao, usar Redis para cache compartilhado entre workers/processos:
  `CACHE_BACKEND=django.core.cache.backends.redis.RedisCache` e
  `CACHE_LOCATION=redis://127.0.0.1:6379/1`.
- Na producao RH SaaS, informar explicitamente ambiente, dominios de cookie,
  cache Redis, hosts, origins, release e backup esperados no validador. Evitar
  atalhos de perfil herdados do projeto antigo.
  Se a janela tambem precisar validar cookies seguros por HTTPS, adicionar
  `--esperar-session-cookie-secure=true` e
  `--esperar-csrf-cookie-secure=true`; essas travas sao opcionais e nao sao
  preenchidas automaticamente.
  Para validar o escopo `SameSite`, adicionar
  `--esperar-session-cookie-samesite=Lax` e
  `--esperar-csrf-cookie-samesite=Lax`, ou o valor esperado da janela.
  O snapshot/validador tambem publicam comandos prontos genericos, com
  variantes que ja incluem `--diretorio-evidencias` e
  `--exigir-arquivos-evidencia`.
  Quando `--diretorio-evidencias` for usado, o comando resolvido preserva essa
  flag e mostra os tres caminhos expandidos.
  Conferir tambem `pm02NextAction` para saber a proxima acao operacional antes
  de tentar fechar a etapa; quando houver comando sugerido, usar
  `pm02NextAction.suggestedCommand`.
- `LocMemCache` fica como fallback simples para desenvolvimento ou servidor
  unico sem Redis, mas e isolado por processo.

## Contrato inicial recomendado

Endpoint principal:

```http
GET /api/dashboard/financial-overview/
```

Esse endpoint deve fornecer os dados necessarios para a primeira tela do dashboard financeiro.

Status atual: o endpoint inicial ja esta disponivel no Django, protegido pela
mesma permissao da tela atual do dashboard (`caixa.view_evento`) e retornando
envelope `{ "data": ... }` compativel com o service do Next.js.

Campo financeiro canonico para despesas previstas no dashboard:
`total_despesa_prevista`. Novos payloads da API nao devem expor
`custo_total_previsto`; esse nome continua reservado para o custo previsto de
eventos no modelo Django e para compatibilidade interna temporaria quando
necessario.

Campos canonicos recomendados para o frontend:

- `totalDespesaPrevista`: alias camelCase de `total_despesa_prevista`;
- `resultadoFinanceiro`: bloco canonico para resultado projetado, realizado,
  consolidado, operacional, deficit de caixa e contas pendentes;
- `deficitCaixa`: falta de caixa/cobertura do recorte filtrado;
- `contasPendentesTotal`: total ainda nao liquidado no recorte.

Chaves antigas como `saldoCaixa`, `saldoFinal`, `saldo_previsto`,
`saldo_realizado`, `falta_cobrir`, `aberto` e `numero` nao fazem parte do
contrato premium novo. Se ainda forem emitidas por alguma API durante a
transicao tecnica, devem ficar tratadas como espelho temporario de service e
removidas quando o serializer canonico cobrir a superficie.

Enquanto existir, `meta.nomenclature.version` deve ser usado apenas como
inventario tecnico de transicao, nao como autorizacao para novas telas
consumirem aliases. Na arquitetura premium final, o payload deve priorizar:

- `canonicalFields`: nomes de dominio que o Next.js deve preferir;
- guardrails de aliases removidos;
- lista minima de campos fisicos ainda pendentes, quando houver motivo atual.

Metadados `legacyAliases`, `legacyAliasUsage` e `physicalFieldsPendingMigration`
devem ser reduzidos ou removidos quando servirem apenas a compatibilidade
historica. `costCenterId` nao deve ser publicado nem usado em chamadas novas;
o filtro operacional e `eventId`.

Filtros aceitos pelo endpoint para o Next.js:

- `period`: `current-month`, `previous-month`, `quarter`, `semester`, `year`;
- `quickPeriod`: `hoje`, `mes_atual`, `30_dias`, `todos`, `vencidos` quando a
  superficie operacional publicar esse filtro rapido;
- `startDate` e `endDate`: periodo manual em `YYYY-MM-DD`;
- `eventId`: filtro de evento/dimensao operacional;
- `contractCode`: filtro visual Contrato, derivado de orcamento/evento;
- `clientId`: filtro de cliente;
- `status`: `pendente`, `parcial`, `recebido`, `pago`, `vencido`,
  `cancelado`, `planejado`, `realizado`.

Quando datas manuais forem enviadas, elas prevalecem sobre o periodo rapido.
A view de API deve apenas normalizar esses parametros e delegar os calculos aos selectors.

O endpoint `/api/mes-financeiro/`, quando consumido por fluxo novo, deve usar
`period`, `startDate`, `endDate`, `eventId`, `clientId` e `contractCode`.
Aliases como `mes`, `periodo_rapido`, `data_inicial`, `data_final`,
`costCenterId`, `evento_id`, `evento`, `cliente_id`, `cliente` e
`contrato_codigo` nao sao contrato premium; se ainda existirem no backend,
devem ter motivo de transicao e remocao planejada. `contractId`,
`contrato_operacional_id` e `contrato_operacional` nao fazem parte do contrato
novo.

O endpoint `/api/lancamentos-financeiros/` aceita entrada canonica:
`period`, `quickPeriod`, `startDate`, `endDate`, `contractCode`, `eventId`,
`clientId`, `cashFlowGroup`, `type`, `nature`, `origin`, `source`,
`sourceId`, `sourceDetail`, `status`, `search`, `limit` e `offset`. Para filtro
de evento, o contrato novo usa somente `eventId`; aliases antigos como
`costCenterId`, `evento`, `evento_id`, `cliente`, `contrato_codigo`,
`data_inicial`, `data_final`, `busca`, `fluxo`, `tipo`, `natureza`,
`origem_obrigacao`, `source_id`, `originId` e `origin_id` devem ficar fora de
novas chamadas.

O endpoint `/api/obrigacoes-financeiras/` aceita entrada canonica:
`period`, `quickPeriod`, `startDate`, `endDate`, `contractCode`, `eventId`,
`clientId`, `source`, `sources`, `cashFlowGroup`, `nature`,
`settlementStatus`, `status`, `search`, `dataSource`, `obligationType`,
`realizedAmountBasis`, `reconciliationStatus`, `reconciliationDiagnosis`,
`realizedAbovePlanned`, `permissionScope`, `limit` e `offset`. O backend
converte periodo para a janela de vencimento antes dos selectors. Para filtro
de evento, obrigacoes usam `eventId` como nome canonico. Aliases antigos como
`periodo_rapido`, `data_inicial`, `data_final`, `costCenterId`, `evento`,
`cliente`, `contrato_codigo`, `origem`, `fluxo`, `situacao`, `busca`,
`tipoObrigacao` e `tipo_obrigacao` nao devem ser enviados por telas novas.

O endpoint `/api/baixas-financeiras-canonicas/` aceita entrada canonica:
`period`, `quickPeriod`, `startDate`, `endDate`, `contractCode`, `eventId`,
`clientId`, `source`, `type`, `cashFlowGroup`, `nature`, `status`,
`writeModelSource`, `search`, `limit` e `offset`. Aliases como
`fonteEscrita`, `write_model_source`, `costCenterId`, `evento`,
`contrato_codigo`, `tipo`, `fluxo`, `natureza`, `origem`, `busca`,
`data_inicial` e `data_final` nao sao entrada nova dessas APIs.

Normalizacao obrigatoria:

- o front envia apenas query canonica pela camada de service;
- `eventId` e o nome canonico para recorte operacional;
- datas invalidas, IDs nao numericos e status fora do contrato devem ser descartados;
- intervalo manual invertido deve ser ordenado antes dos selectors;
- calculos financeiros permanecem nos selectors/serializers do Django.
- filtros por `eventId` ou `clientId` representam um recorte de entidade; custos
  globais sem vinculo com esse recorte nao devem contaminar os totais filtrados.
Para endpoints com status proprio, como `/api/fcf/`, o Next.js pode preservar
os valores publicados em `filterOptions.installmentStatuses` por meio de
`allowedStatuses` ou `allowUnknownStatus`, sem duplicar no frontend a lista de
status de `ParcelaDivida`.

Endpoints de autenticacao para o Next.js:

- `GET /api/auth/csrf/`: retorna token CSRF e define o cookie CSRF HttpOnly;
- `POST /api/auth/login/`: recebe JSON `{ "username": "...", "password": "..." }`, exige `X-CSRFToken`, autentica no Django e cria sessao HttpOnly;
- `POST /api/auth/logout/`: encerra a sessao atual, tambem com CSRF;
- `GET /api/auth/session/`: retorna estado autenticado e usuario minimo quando houver sessao; no Next.js, pode ser usado pelo painel de login para reaproveitar sessao ativa antes de pedir senha.

O payload publico de usuario da autenticacao expoe `canViewDashboard`,
`canPayFinancialDebtInstallment` e o espelho `permissions` com esses mesmos
booleans. A permissao de pagamento FCF no payload de sessao serve para futuras
telas e controles gerais; a permissao por linha continua vindo de
`installments[].actionHints.primary` em `/api/fcf/`.

No Next.js, `features/auth/services/backend-auth-service.ts` deve ser a fronteira unica para CSRF, login, consulta de sessao e logout. Componentes visuais nao devem chamar `fetch` diretamente para endpoints de autenticacao.
O frontend nao deve armazenar senha, token de sessao ou token CSRF em `localStorage`. A sessao continua em cookie HttpOnly do Django, com CORS por allowlist e `CSRF_TRUSTED_ORIGINS` configurado para a origem do Next.js.
As chamadas de autenticacao do service Next.js devem usar `cache: "no-store"` para acompanhar as respostas nao cacheaveis do Django.
Services financeiros do Next.js tambem devem usar `cache: "no-store"` nas chamadas reais ao Django para evitar saldos, baixas ou conciliacoes defasadas no cliente.
O client HTTP do Next.js deve aplicar `Content-Type: application/json` automaticamente apenas para body JSON serializado, preservando futuros `FormData`/uploads sem header JSON indevido.
O client HTTP deve tolerar resposta vazia/204 retornando `null`, sem tentar parsear JSON inexistente.
Quando uma API Django retornar erro JSON com `errors`, `detail`, `non_field_errors`, `field_errors`, `message` ou erros de campo no topo, o client HTTP do Next.js deve expor a primeira mensagem estruturada em `ApiError.message` e manter o payload original em `ApiError.details`.
Hooks do Next.js que consomem APIs protegidas devem usar a classificacao central do client HTTP para distinguir `unauthorized`, `forbidden` e `unknown`.
Quando capturarem `unknown`, hooks do Next.js devem normalizar com o helper central do client HTTP antes de salvar o erro no estado.
Em producao, preferir frontend e backend em subdominios do mesmo dominio para manter `SameSite=Lax`. Se ficarem em sites diferentes, configurar `SESSION_COOKIE_SAMESITE=None`, `CSRF_COOKIE_SAMESITE=None`, `SESSION_COOKIE_SECURE=True` e `CSRF_COOKIE_SECURE=True`.
As respostas de autenticacao devem usar headers de nao-cache e o login deve aceitar JSON: `Content-Type: application/json` ou `Content-Type: application/json; charset=utf-8`.

## Variaveis do frontend

Desenvolvimento:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_API_TIMEOUT_MS=12000
NEXT_PUBLIC_API_MOCK_FALLBACK=true
NEXT_PUBLIC_AUTH_LOGIN_URL=http://localhost:8000/login/
```

Producao:

```env
NEXT_PUBLIC_API_BASE_URL=https://seudominio.com/api
NEXT_PUBLIC_API_MOCK_FALLBACK=false
NEXT_PUBLIC_AUTH_LOGIN_URL=https://seudominio.com/login/
```

## Regra de consumo no frontend

Componentes visuais nao devem chamar `fetch` diretamente.

Fluxo obrigatorio:

```text
componentes -> hooks -> services -> lib/api/http-client -> Django API
```

Erros `401` e `403` sao estados de autenticacao/autorizacao. O frontend deve
mostrar login ou acesso restrito nesses casos e nao deve trocar a resposta por
mock fallback.
Essa regra tambem vale para chamadas auxiliares usadas para enriquecer uma tela:
se a falha for auth/permissao, o service deve propagar o erro em vez de exibir
dados parciais como se fosse apenas indisponibilidade.

As APIs financeiras consumidas pelo Next.js devem manter esse boundary em JSON.
No ciclo atual isso vale para `/api/dashboard/financial-overview/`,
`/api/fci/`, `/api/fcf/`, `/api/fcf/creditors/` e
`/api/mes-financeiro/`, `/api/lancamentos-financeiros/`,
`/api/obrigacoes-financeiras/`, `/api/modelagem-financeira-canonica/` e
`/api/baixas-financeiras-canonicas/`, alem da mutation
`/api/obrigacoes-financeiras/liquidar/`.

## Regra de negocio

Calculos financeiros devem ficar no Django.

Exemplos:

- receita total;
- despesas totais;
- lucro liquido;
- margem;
- resultado financeiro;
- contas a pagar;
- contas a receber;
- fluxo de caixa;
- despesas por categoria;
- receitas por servico.

O frontend apenas exibe os valores recebidos.

Os KPIs principais devem usar a mesma base filtrada:

- `receitaTotal`: receitas operacionais previstas;
- `despesasTotais`: saidas previstas;
- `lucroLiquido`: `receitaTotal - despesasTotais`;
- `margemLiquida`: `lucroLiquido / receitaTotal`;
- `resultadoFinanceiro`: resultado final do fluxo de caixa, podendo incluir
  entradas nao operacionais.
- `saldoCaixa`: alias legado de `resultadoFinanceiro` durante a transicao.

## Compatibilidade com o Django atual

A migracao deve ser gradual.

Nao remover:

- templates atuais;
- views HTML atuais;
- rotas atuais;
- regras existentes;
- permissoes existentes.

As APIs devem ser criadas em paralelo.

## Seguranca

As APIs devem respeitar:

- autenticacao;
- permissoes equivalentes as telas atuais;
- CSRF/cookies ou token, conforme estrategia escolhida;
- CORS liberado somente para dominios autorizados;
- HTTPS em producao;
- settings de seguranca existentes.

## CORS

Liberar apenas:

- `http://localhost:3000`;
- dominio de producao do frontend Next.js na Vercel;
- dominio proprio futuro, se houver.

Nao usar `CORS_ALLOW_ALL_ORIGINS=True` em producao.

No backend atual, as origens permitidas sao controladas por
`CORS_ALLOWED_ORIGINS` e `CORS_ALLOW_CREDENTIALS`, mantendo credenciais de
sessao para o frontend Next.js sem liberar origens indiscriminadas.

## Ordem segura de migracao

1. Criar base DRF/CORS no Django.
2. Criar endpoint `/api/dashboard/financial-overview/`.
3. Testar contrato JSON.
4. Testar permissoes.
5. Testar query count quando houver listas/agregacoes.
6. Configurar `NEXT_PUBLIC_API_BASE_URL` no frontend.
7. Trocar mock pelo service real.
8. Manter fallback mockado apenas em desenvolvimento.
9. Validar dashboard local.
10. Publicar frontend.
11. So depois substituir telas HTML antigas.

## Responsabilidade dos mocks

Mocks ficam somente no frontend, em `lib/data`.

Mocks sao temporarios.

Em producao, o frontend deve consumir dados reais do Django.
No Next.js, `NEXT_PUBLIC_API_MOCK_FALLBACK` so deve ficar habilitado em
desenvolvimento. Quando a variavel nao for definida, o fallback mockado deve
ser considerado ativo apenas fora de `NODE_ENV=production`.

Aliases semanticos tambem devem ser preferidos nas APIs auxiliares:

- FCF: `total_contas_pendentes`, `total_contas_vencidas`,
  `valor_pendente_pagamento`, `contas_pendentes` e
  `subtotal_contas_pendentes`;
- FCI: `resultado_financeiro_fci_previsto` e
  `subtotal_resultado_financeiro_previsto`;
- mes financeiro: `resultado_financeiro_previsto`,
  `valor_pendente_pagamento`, `contas_pendentes` e `deficit_caixa`.

Em FCI e FCF, novos consumidores devem enviar filtros de periodo como
`period` para atalhos rapidos ou `startDate`/`endDate` para intervalo manual.
O backend ainda aceita `data_inicial` e `data_final` como aliases de transicao
e ecoa os dois formatos em `filters`. Datas manuais continuam prevalecendo
sobre `period`.

Em FCI, `contractCode`/`contrato_codigo` filtra pelo numero visual do contrato
resolvido por evento/orcamento; `eventId`/`costCenterId`/`evento_id`/`evento`
filtra por evento.

No Mes Financeiro, `contractCode`/`contrato_codigo`, `eventId`/`evento_id`/
`evento` e `clientId`/`cliente_id`/`cliente` sao os recortes operacionais.
`costCenterId` permanece aceito apenas como compatibilidade de evento. Novos
consumidores devem preferir `contractCode`, `eventId` e `clientId`.

`actionHints` de obrigacoes financeiras que apontam para FCI e FCF tambem devem
preferir `startDate`/`endDate`. Para movimentacoes FCF, o backend pode incluir
`sourceType` para abrir a tela ja separando movimentacao manual de entrada
automatica de divida. `creditorId` so deve acompanhar action hints de entradas
automaticas quando houver credor cadastrado; action hints FCF manuais devem
ficar sem `creditorId`.

Action hints `legacyPayment` em obrigacoes financeiras devem respeitar a
permissao de pagamento da origem (`add_pagamentoeventocustoservico`,
`add_pagamentoeventocustoextra` ou `add_pagamentoparceladivida`). Quando
`actionHints` existir e `primary=null`, o Next.js deve tratar isso como decisao
explicita do backend e nao reconstruir URL de pagamento por convencao local.
Mesmo com permissao, `legacyPayment` so deve ser publicado quando a obrigacao
ainda tiver valor pendente; itens liquidados ou cancelados devem manter
`primary=null`.
Action hints `adminChange` tambem devem respeitar `view_*` ou `change_*` do
model de origem. Quando `actionHints.admin=null`, o frontend nao deve
reconstruir URL de admin por fallback local.
Fallbacks locais de transicao no Next.js, usados somente quando `actionHints`
estiver ausente, tambem devem respeitar saldo pendente e status de liquidacao
antes de montar link de pagamento.
O item retornado por `/api/obrigacoes-financeiras/liquidar/` deve seguir a
mesma politica de `actionHints` da listagem, usando o usuario autenticado da
mutation para publicar ou ocultar `legacyPayment` e `adminChange`.
`meta.settlementCapabilities.sources[*]` tambem publica `canSettle` e
`canUseNativeSettlement` por usuario autenticado. O Next.js deve usar esses
campos para exibir ou ocultar a baixa nativa, mantendo fallback permissivo
apenas para payload legado sem esses campos.

## Origem das despesas operacionais

`DespesaOperacional` possui origem explicita para evitar ambiguidades entre
despesa manual e despesas sincronizadas:

- `manual`: criada diretamente como despesa operacional;
- `custo_servico`: criada/sincronizada a partir de `EventoCustoServico`;
- `custo_extra`: criada/sincronizada a partir de `EventoCustoExtra`.

O Next.js e novas APIs nao devem inferir origem por texto de `descricao`.
Quando uma despesa for `custo_servico`, `origem_custo_servico_tipo` indica o
bucket (`diarias`, `alimentacao` ou `transporte`). Quando for `custo_extra`,
`origem_custo_extra_id` aponta para o custo extra original quando ele ainda
existir.

## Credores de Dividas FCF

Enquanto o cadastro de dividas estiver no Django admin, o backend e a fonte da
verdade para credores.

- `Credor` e o cadastro mestre de credores.
- `DividaFinanceira.credor_cadastro` referencia um credor cadastrado.
- `DividaFinanceira.credor` permanece como alias textual legado para filtros e
  integracoes antigas.
- O admin de dividas usa autocomplete de credores cadastrados; novas dividas no
  admin nao devem receber credor como texto livre.
- Novas dividas no admin selecionam apenas credores ativos. Credores inativos
  ja vinculados a dividas antigas continuam preservados na edicao.
- A validacao de dominio tambem rejeita novas dividas com `credor_cadastro`
  inativo, inclusive em futuras APIs ou criacoes programaticas.
- O perfil `Financeiro` possui permissao para visualizar, adicionar e alterar
  credores no admin; o perfil `Operacional` nao acessa esse cadastro.
- O backend normaliza espacos e bloqueia nomes duplicados ignorando diferencas
  de maiusculas/minusculas. Salvamentos legados por texto reaproveitam um
  credor existente antes de criar novo cadastro.
- `/api/fcf/` publica `creditorId`, `creditorName`, `credor_id`,
  `credor_nome`, `creditor` e `credor` em dividas, parcelas e grupos.
- Parcelas FCF publicam `availableForPayment` como decisao calculada pelo
  backend para exibir acao de pagamento; `disponivel_para_pagamento` fica
  apenas como alias de transicao.
- Enquanto o pagamento FCF continuar no Django, a tela Next.js `/fcf` pode
  apontar parcelas com `availableForPayment=true` para
  `/fcf/parcelas/<id>/pagar/`; isso nao muda a regra de baixa nem transforma o
  Next.js em escritor financeiro.
- `/api/fcf/` deve publicar `installments[].actionHints.primary` para parcelas
  pagaveis quando o usuario tambem possuir `caixa.add_pagamentoparceladivida`,
  usando `type=legacyPayment`, `target=backend` e `path` da tela Django; o
  Next.js deve preferir esse hint para URL e texto da acao, mantendo caminho
  direto apenas como fallback de transicao quando `actionHints` estiver ausente
  em payload legado.
- O objeto `installments[].actionHints` de FCF deve manter a forma
  `{ primary, admin, actions }`; enquanto nao houver acao administrativa
  propria nesse contrato, `admin` deve ser `null`.
- `/api/fcf/creditors/` exige `caixa.view_credor`, responde erros de
  autenticacao/autorizacao em JSON e publica somente os credores ativos
  cadastrados para o select da futura tela Next.js.
- `/api/fcf/` deve ser consumida por novas telas com filtro de credor por
  `creditorId`; aliases de credor, quando ainda aceitos pela API, ficam como
  compatibilidade de borda e nao como query nova do Next.js.
- `/api/fcf/` aceita filtro de cliente por `clientId`, `cliente_id` ou
  `cliente`; novas telas devem preferir `clientId`. O filtro vale para
  parcelas e movimentacoes FCF vinculadas por contrato, evento ou dimensao da
  divida.
- `clientId`, `cliente_id` e `cliente` em FCF sao tratados como filtros por ID;
  valores nao numericos retornam recorte vazio em vez de busca textual.
- Componentes FCF no Next.js devem ler `filterOptions.clients` depois do
  adapter; `filterOptions.clientes` fica restrito ao boundary de compatibilidade
  do service.
- O adapter FCF do Next.js tambem deve normalizar
  `filterOptions.contracts`/`contratos` e `filterOptions.events`/`eventos`,
  preservando `contracts` e `events` para o header global e exportacoes.
- Exportacoes FCF no Next.js devem resolver labels de contrato, evento e cliente
  a partir de `filterOptions.contracts`, `filterOptions.events` e
  `filterOptions.clients` ja normalizados pelo service.
- `contractId`/`contrato_operacional_id`/`contrato_operacional` e
  `eventId`/`costCenterId`/`evento_id`/`evento` em FCF tambem sao filtros por
  ID; valores nao numericos retornam recorte vazio.
- O filtro FCF por evento tambem cobre movimentacoes vinculadas pela
  `divida_financeira` de origem, alem de movimentacoes com evento direto.
- No Next.js, a leitura completa de FCF deve passar por
  `getFinancialFinancingData()`, que consome apenas `GET /api/fcf/`, normaliza
  opcoes de credores, opcoes de escolha e listas principais. Escritas de
  dividas continuam fora dessa etapa.
- A normalizacao frontend de `creditorId`, `type` e `sourceType` deve
  ficar em `features/financial-dashboard/utils/financial-financing-filters.ts`,
  compartilhada pela tela, hook e service.
- O hook e o service FCF do Next.js devem enviar entradas novas apenas por
  `creditorId`, `type`, `sourceType` e `quickPeriod`.
- O adapter de resposta FCF do Next.js tambem deve espelhar aliases de filtros
  operacionais para `contractId`, `eventId` e `clientId`, mantendo
  `contrato_operacional_id`, `costCenterId`, `evento_id`, `cliente_id` e demais
  aliases apenas como compatibilidade de transicao.
- O mesmo adapter deve espelhar `startDate`/`data_inicial` e
  `endDate`/`data_final`; exportacoes e componentes novos devem ler os nomes
  canonicos.
- `FinancialFinancingFiltersApi` deve marcar aliases legados com `@deprecated`;
  novos consumidores devem preferir `startDate`, `endDate`, `period`, `type`,
  `creditorId`, `sourceType`, `contractId`, `eventId` e `clientId`.
- `FinancialFinancingQueryOverrides` deve expor apenas entradas canonicas para
  novas chamadas de service/hook: `creditorId`, `type`, `sourceType`,
  `quickPeriod` e os filtros globais `period`/`startDate`/`endDate`.
- Consumidores da resposta FCF no Next.js devem ler
  `filterOptions.financingMovementSourceTypes` depois do adapter;
  `movementSourceTypes` permanece apenas como alias legado de entrada/resposta
  dentro do service.
- A rota Next.js `/fcf` e somente leitura nesta fase: KPIs, dividas, parcelas,
  credores agrupados, movimentacoes e exportacao CSV local. Cadastro, edicao e
  pagamento de dividas continuam no Django/admin ou nos fluxos Django
  existentes.
- Os filtros locais da rota `/fcf` usam `creditorId`, `type` e
  `sourceType`, junto do filtro global `clientId`, parametros ja aceitos por
  `GET /api/fcf/`.
- `GET /api/fci/` e `GET /api/fcf/` aceitam `period` do Next.js. O backend
  converte `current-month` para `periodo_rapido=mes_atual` e converte
  `previous-month`, `quarter`, `semester` e `year` para `startDate`/`endDate`
  antes de aplicar os selectors de leitura.
- `GET /api/canonical-settlements/` e o alias
  `/api/baixas-financeiras-canonicas/` tambem aceitam `period`. O backend
  converte o periodo para `startDate`/`endDate` quando datas manuais nao forem
  enviadas e filtra por `data_baixa`, preservando o endpoint como read-only.
  Para evento, aceita `eventId`, `costCenterId`, `evento_id` e `evento`,
  mantendo `eventId` como nome preferencial.
- O filtro de status da rota `/fcf` deve preferir
  `filterOptions.installmentStatuses` publicado pelo backend.
- A normalizacao de filtros da rota `/fcf` deve preservar esses status no hook,
  na query enviada e na query key, mesmo quando nao fizerem parte do conjunto
  generico do dashboard.
- Valores de `status` fora das choices de parcelas FCF e movimentacoes FCF devem
  ser descartados por `/api/fcf/` e ecoados como `filters.status` vazio. O
  Next.js deve limpar o status local invalido usando `filterOptions` da resposta,
  sem duplicar choices dos models.
- A rota `/fcf` pode exibir contadores de movimentacoes automaticas/manuais
  usando `statistics.automaticFinancingMovementsCount` e
  `statistics.manualFinancingMovementsCount`.
- Parcelas FCF podem exibir `overdueDays`, mas status de atraso,
  disponibilidade de pagamento e saldos continuam sendo decisao do backend.
- Dividas, parcelas e movimentacoes FCF podem exibir contrato/evento usando
  apenas `contractLabel`/`contractCode` e
  `eventLabel`/`eventName`/`eventNumber` recebidos da API.
- Movimentacoes FCF automaticas ou legadas podem publicar contrato/evento/cliente
  herdados da `divida_financeira` quando esses campos nao estiverem duplicados
  diretamente na movimentacao.
- O service do Next.js deve enviar `type`, `creditorId` e `sourceType` no
  caminho novo de FCF. `creditor` textual pode existir apenas como label ou
  fallback visual de resposta, nao como filtro novo de query.
- `/api/fcf/` aceita tipo de divida somente quando o valor pertence aos tipos
  publicados pelo contrato FCF. Valores invalidos devem ser descartados e
  ecoados como `filters.type` vazio, para nao exibir filtro ativo sem efeito.
  Quando `filters.type` vier vazio, a rota Next.js `/fcf` deve limpar o filtro
  local de tipo.
- O Next.js nao deve duplicar a lista de `DividaFinanceira.TIPO_CHOICES`; ele
  deve enviar `type` e deixar o backend validar e normalizar a resposta.
- `creditorId` filtra estritamente pelo id do credor cadastrado.
- O Next.js deve enviar `creditorId` somente como inteiro positivo.
  Valores invalidos vindos da URL devem abrir como "Todos" no filtro local, sem
  cair para busca textual no caminho canonico.
- `useFinancialFinancing()` deve usar esse mesmo ID normalizado na query key e
  na request, para evitar cache/refetch divergentes de uma query que o service
  descartaria.
- Quando a resposta trouxer `creditor` textual, o frontend deve tratar como
  label/fallback visual, nao como id de filtro.
- A tela Django FCF tambem usa `creditorId` no filtro visual de credor, com
  opcoes vindas do cadastro mestre de credores.
- A tela Django de pagamentos de parcelas FCF tambem usa `creditorId` no
  filtro de credor, preservando `credor` apenas como alias de compatibilidade.
- `/api/fcf/` aceita filtro de movimentacoes por `sourceType=manual` ou
  `sourceType=divida_automatica`; no Next.js, aliases como
  `movementSourceType`, `origem_movimentacao` e `automaticFromDebt` ficam
  restritos a espelhos de resposta normalizados pelo service quando a API ainda
  publicar esses campos.
- O adapter de resposta FCF do Next.js pode derivar `filters.sourceType` de
  `automaticFromDebt` quando a API ecoar somente esse alias legado, mas esse
  fallback nao deve ser usado como query inicial ou override novo.
- Valores fora de `manual` e `divida_automatica` em `sourceType` devem ser
  descartados e ecoados vazios no payload `filters`, para nao exibir filtro
  ativo sem efeito.
  Quando a origem vier vazia no payload, a rota Next.js `/fcf` deve limpar o
  `sourceType` local.
- Movimentacoes FCF automaticas originadas de dividas publicam
  `debtCreditorId`, `debtCreditorName` e `debtCreditor`.
- `filterOptions.creditors` deve vir dos credores ativos cadastrados. Para
  selects de UI, `value` e o id serializado; novas telas devem enviar
  `creditorId` numerico no payload de escrita.

Quando o Next.js ganhar cadastro proprio de dividas, ele deve carregar os
credores via API, converter o `value` do select quando necessario e enviar o
identificador numerico do credor cadastrado. No frontend, essa conversao deve
passar por `buildCreateFinancialDebtRequestPayload()` ou
`buildUpdateFinancialDebtRequestPayload()` antes de chamar o Django. Nao criar
novas telas aceitando credor digitado livremente. Para acoes de pagamento de parcelas FCF, usar
`availableForPayment` junto com as permissoes da sessao, sem recalcular
status/saldo no frontend.

Contrato do endpoint dedicado de credores:

```json
{
  "creditors": [
    {
      "id": "1",
      "value": "1",
      "label": "Banco Exemplo",
      "name": "Banco Exemplo",
      "credor_id": 1,
      "creditorId": 1,
      "credor_nome": "Banco Exemplo",
      "creditorName": "Banco Exemplo",
      "document": "00.000.000/0001-00",
      "isActive": true
    }
  ],
  "credores": ["Banco Exemplo"],
  "meta": {
    "count": 1,
    "onlyActive": true,
    "source": "cadastro_credor"
  }
}
```

## Regra para IA/Codex

Antes de alterar qualquer codigo, ler:

- documentacao do backend Django;
- documentacao do frontend Next.js;
- este documento de integracao.

Ao mexer no backend:

- nao alterar regras financeiras sem necessidade;
- reutilizar selectors/services existentes;
- nao criar novas telas HTML Django operacionais;
- manter `python manage.py inventariar_html_django_pm06 --json` como canario
  de `operationalHtmlCount=0`;
- preservar apenas Admin, APIs, auth/erro/suporte, comandos, auditoria e
  downloads tecnicos;
- manter o Django Admin como superficie HTML administrativa; auth/erro/suporte
  permanecem apenas para acesso e suporte tecnico.

Ao mexer no frontend:

- nao duplicar calculo financeiro;
- consumir services;
- preservar arquitetura modular;
- preservar visual premium SaaS.
- validar com `npx --yes pnpm@10.33.4 install --frozen-lockfile`,
  `npx --yes pnpm@10.33.4 run lint`,
  `npx --yes pnpm@10.33.4 run typecheck` e
  `npx --yes pnpm@10.33.4 run build` antes de publicar.

## Criterio de pronto

A integracao inicial estara pronta quando:

- Django responder `/api/dashboard/financial-overview/`;
- endpoint exigir autenticacao/permissao adequada;
- testes Django passarem;
- frontend consumir o endpoint via service/hook;
- dashboard exibir dados reais;
- mock fallback funcionar apenas em desenvolvimento;
- producao nao depender de mock.
- listas sem dados sairem como arrays vazios na API, sem itens artificiais
  como "Sem receitas" ou "Sem contas a pagar".
