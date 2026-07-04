# Plano Vivo Para Correcao De Query Count Do Financial Overview

Atualizado em: 2026-06-10

## Objetivo

Planejar, de forma incremental e segura, a correcao da regressao de queries do
endpoint `/api/dashboard/financial-overview/`, mantendo o contrato JSON usado
pelo frontend Next.js, as regras financeiras existentes, permissoes, filtros e
valores publicados.

Este documento e um plano tecnico vivo. Ele pode ganhar novas subfases se, no
meio da execucao, aparecer risco nao previsto. Nenhuma fase deve avancar sem
revisao final e sem o campo de liberacao marcado.

## Regras Obrigatorias

- Nao implementar a correcao diretamente sem diagnostico de queries duplicadas.
- Nao resolver aumentando o limite do teste de query count.
- Nao remover campos, listas, aliases ou secoes do payload para reduzir queries.
- Nao alterar regra financeira, status, saldos, filtros ou arredondamento.
- Nao alterar models, migrations ou schema de banco na primeira tentativa.
- Nao criar cache como solucao primaria; cache pode esconder N+1 e divergencia.
- Nao trocar a fonte canonica/legada de dados sem teste que prove equivalencia.
- Nao mexer no frontend enquanto o contrato atual puder ser mantido no backend.
- Se uma validacao falhar, a fase deve parar e registrar o motivo.
- Priorizar estabilidade do dashboard, FCO, FCI, FCF, obrigacoes, ledger,
  filtros por data, cliente, evento, contrato e status.
- Aproveitar ao maximo selectors, serializers, helpers e testes existentes.
- Criar novos arquivos, dependencias, scripts ou abstracoes somente quando forem
  realmente necessarios para a fase em execucao.

## Principio De Mudanca Minima

- Preferir ajustes pequenos em querysets ja existentes antes de criar selector
  novo.
- Reusar `querysets_dashboard_filtrados` como ponto principal de preparo dos
  dados do dashboard.
- Reusar `serializar_dimensao_operacional_financeira`, `relacao_carregada` e
  `dados_parcela_divida_sem_lazy` para evitar lazy load em serializers.
- Reusar selectors especializados quando ja estiverem mais preparados, como
  `selectors_financiamentos.filtrar_movimentacoes_financiamento`.
- Reusar `select_related`, `prefetch_related`, `Prefetch`, `annotate` e
  `aggregate` antes de materializar listas grandes em Python.
- Reusar testes existentes em `caixa.tests.FiltrosHtmlTests` como guardrail de
  performance.
- Criar helper novo somente se houver duplicacao real entre montagem do
  dashboard, obrigacoes, FCI, FCF ou mes financeiro.
- Nao duplicar logica de calculo financeiro em serializer se ela ja existir em
  selector ou service consolidado.

## Regra Obrigatoria De Versionamento E Publicacao

- Cada fase concluida deve gerar um commit local, quando houver alteracao de
  codigo.
- O commit local e permitido apenas apos as validacoes da fase.
- O Codex nao deve executar `git push`.
- O Codex nao deve executar `git merge`.
- O Codex nao deve acionar deploy de producao.
- Qualquer push sera manual, feito pelo responsavel do projeto.
- Qualquer merge para `main` sera manual, apos validacao final.
- Em caso de falha, retornar ao ultimo commit local estavel.

## Estado Atual Conhecido

- Backend: Django, app `caixa`.
- Endpoint afetado: `/api/dashboard/financial-overview/`.
- View afetada: `caixa/views_dashboard.py`, funcao
  `api_dashboard_financial_overview`.
- Serializer principal: `caixa/serializers_dashboard.py`, funcao
  `montar_payload_dashboard_financial_overview_api`.
- Querysets base do dashboard: `caixa/selectors_dashboard_filtros.py`, funcao
  `querysets_dashboard_filtrados`.
- Teste de performance afetado:
  `caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_mantem_queries_constantes`.
- Baseline local em 2026-06-10:
  - Com 1 lote de registros: 111 queries.
  - Com 9 lotes de registros: 420 queries.
  - Falha: `AssertionError: 420 != 111`.
- O teste do contexto base do dashboard passa com queries constantes e limite
  menor ou igual a 25, entao a regressao parece estar na montagem extra do
  payload da API `financial-overview`, nao no contexto basico do dashboard.
- Existem outros testes de query count para custos por evento, mes financeiro,
  FCI/FCF, APIs de cadastro e pagamentos.
- A arquitetura do projeto ja orienta uso de `select_related`,
  `prefetch_related`, `annotate`, `aggregate` e testes de query count para
  colecoes financeiras.

## Mapa Atual Do Fluxo

Fluxo principal da API:

1. `api_dashboard_financial_overview` normaliza filtros da request.
2. `montar_payload_dashboard_financial_overview_api` chama
   `montar_dados_dashboard`.
3. `montar_dados_dashboard` usa `querysets_dashboard_filtrados`, calcula totais
   e monta movimentacoes.
4. A API enriquece o payload com comparativo, contas a pagar, contas vencidas
   all-time, contas a receber, receitas por servico, despesas por categoria,
   fluxo de caixa, disponibilidade de caixa, filtros e metadados.

Blocos extras da API que nao fazem parte do teste do contexto base:

- `montar_realized_cash_flow_dashboard`
- `montar_comparativo_dashboard`
- `montar_contas_vencidas_all_time_dashboard`
- `montar_contas_a_receber_dashboard`
- `montar_resumo_receitas_servico`
- `montar_despesas_por_categoria`
- `montar_disponibilidade_caixa_dashboard`
- `montar_opcoes_filtros_dashboard_api`

## Contrato Que Nao Pode Mudar

O frontend Next.js consome o payload em:

- `features/financial-dashboard/services/financial-dashboard-service.ts`
- `features/financial-dashboard/components/financial-dashboard-view.tsx`
- `features/financial-dashboard/utils/dashboard-export.ts`
- `lib/types/dashboard.ts`

Campos e secoes que devem permanecer compativeis:

- `kpis`
- `resultadoFinanceiro`
- `cashFlow`
- `cashAvailability`
- `cashBasisRealizedFlow`
- `competenceBasisRealizedFlow`
- `realizedCashFlow`
- `realizedCashFlowComparison`
- `revenueExpense`
- `operationalRevenueExpense`
- `expenseCategories`
- `serviceRevenue`
- `accountsPayable`
- `overduePayablesAllTime`
- `accountsReceivable`
- `contractSummary`
- `financialIndicators`
- `financialGoals`
- `cashEvolution`
- `summary`
- `filterOptions`
- `meta`
- aliases legados ainda consumidos ou normalizados, como `deficitCaixa`,
  `contasPendentesTotal`, `totalDespesaPrevista`, `entradas`, `saidas`,
  `saldoInicial`, `saldoFinal`, `fluxosCaixa`, `caixaDisponivel` e
  `saldoCaixaDisponivel`.

Qualquer otimizacao deve preservar tambem:

- formato numerico publicado ao frontend;
- ordenacao das listas visiveis;
- limite atual de exibicao de contas a pagar e contas a receber;
- filtros de navegacao usados nos links de detalhes;
- metadados de fonte de leitura canonica/legada quando publicados.

## Evidencias Obrigatorias Da Correcao

Cada execucao real deste plano deve registrar:

- query count inicial e final do teste afetado;
- bloco responsavel pelo crescimento;
- SQL ou familia de SQLs que crescia com o volume;
- decisao tomada e alternativas descartadas;
- campos do payload comparados antes e depois;
- testes rodados e resultado;
- motivo para qualquer arquivo novo, helper novo, indice novo ou mudanca de
  fonte canonica/legada.

Sem essas evidencias, a fase nao deve ser considerada pronta, mesmo que o teste
passe localmente.

## Hipoteses Tecnicas Iniciais

Estas hipoteses nao devem ser tratadas como conclusao antes da Fase 0.

- Alguma etapa extra de `montar_payload_dashboard_financial_overview_api` pode
  estar iterando colecoes e acionando lazy load ou agregacao por item.
- Funcoes candidatas a diagnostico:
  - `montar_contas_vencidas_all_time_dashboard`
  - `montar_contas_a_receber_dashboard`
  - `montar_resumo_receitas_servico`
  - `montar_realized_cash_flow_dashboard`
  - `montar_disponibilidade_caixa_dashboard`
- `querysets_dashboard_filtrados` ja prepara varias relacoes, mas o queryset de
  `financiamentos` e mais simples que o selector especializado de FCF.
- Properties de custos de servico e custos extras usam pagamentos prefetchados
  quando disponiveis; se algum caminho perder o prefetch, pode gerar agregacoes
  repetidas.
- A leitura de obrigacoes pode carregar varias origens financeiras; ela deve ser
  medida separadamente para nao misturar custo necessario com N+1.
- Hipotese forte a medir: `montar_contas_vencidas_all_time_dashboard` chama
  `listar_obrigacoes_com_fonte` com `dataSource=canonical`. Antes de retornar a
  leitura canonica ou legada, esse caminho avalia prontidao canonica. A prontidao
  chama verificacao de paridade e reconciliacao legada; se a leitura canonica nao
  estiver pronta, o legado pode ser percorrido para diagnostico e depois
  percorrido novamente para a resposta.
- Hipotese forte a medir: `verificar_paridade_modelagem_financeira_canonica`
  foi desenhada como auditoria de integridade e usa comparacoes por
  `chave_origem`. Se essa auditoria completa roda dentro da request do dashboard,
  ela pode gerar queries proporcionais ao volume mesmo que o payload final so
  precise de um resumo de vencidos.
- Hipotese forte a medir: o card `overduePayablesAllTime` publica apenas resumo
  (`count`, `amount`, `pendingAmount`, filtros e read model). Se ele estiver
  montando a lista completa de obrigacoes apenas para resumir, pode haver uma
  oportunidade de reaproveitar ou criar um selector de resumo, desde que a
  semantica canonica/legada seja preservada.

## Fase 0 - Diagnostico De Queries

### Objetivo

Criar uma baseline confiavel e identificar quais SQLs crescem com a quantidade
de registros antes de alterar codigo.

### Diagnostico Necessario Antes De Alterar

- Confirmar novamente o teste falhando.
- Capturar as queries repetidas do caso com 1 lote e com 9 lotes.
- Agrupar SQLs normalizados por tabela/fonte.
- Separar queries constantes de queries proporcionais ao volume.
- Identificar qual funcao do payload dispara o crescimento.
- Medir o custo isolado de cada bloco extra do payload.
- Confirmar se a avaliacao de prontidao canonica esta rodando dentro da request.
- Confirmar se `overduePayablesAllTime` precisa montar itens completos ou se
  apenas um resumo seria suficiente.
- Capturar um snapshot leve das chaves do payload antes da correcao para
  comparar depois.

### Arquivos Apenas Para Leitura

- `caixa/tests.py`
- `caixa/serializers_dashboard.py`
- `caixa/selectors_dashboard.py`
- `caixa/selectors_dashboard_filtros.py`
- `caixa/selectors_dashboard_movimentacoes.py`
- `caixa/selectors_dashboard_totais.py`
- `caixa/selectors_obrigacoes.py`
- `caixa/serializers_obrigacoes.py`
- `caixa/models*.py`

### Subfases Numeradas

1. Rodar apenas o teste afetado.
2. Capturar `connection.queries` em cenario com 1 lote.
3. Capturar `connection.queries` em cenario com 9 lotes.
4. Normalizar SQL removendo literais para agrupar repeticoes.
5. Mapear as tabelas mais repetidas.
6. Medir isoladamente as secoes do payload:
   `realizedCashFlow`, comparativo, vencidos all-time, contas a receber,
   receitas por servico, categorias, disponibilidade de caixa e opcoes de
   filtros.
7. Medir `listar_obrigacoes_com_fonte` separando:
   avaliacao de prontidao canonica, leitura canonica, fallback legado,
   reconciliacao e resumo.
8. Registrar se ha leitura duplicada de obrigacoes no mesmo request.
9. Registrar qual secao causa crescimento proporcional.
10. Liberar a fase seguinte apenas com causa provavel documentada.

### Tecnica Recomendada De Medicao

- Usar `CaptureQueriesContext` como os testes existentes.
- Medir primeiro o payload inteiro.
- Medir depois blocos internos com wrappers temporarios em teste local ou
  shell, sem commitar instrumentacao.
- Normalizar SQLs para agrupar repeticoes por forma, nao por valores literais.
- Separar query count de tempo total: a correcao primaria e query count
  constante, mas queries constantes muito caras tambem devem ser registradas.
- Ao comparar payload antes/depois, ignorar campos naturalmente volateis como
  `generatedAt`.
- Registrar no plano a tabela e a funcao responsavel pela maior repeticao.

### Comandos De Validacao

```powershell
$env:SECRET_KEY='local-validation-secret'; $env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_mantem_queries_constantes --verbosity 1
rg -n "montar_payload_dashboard_financial_overview_api|montar_contas_vencidas_all_time_dashboard|listar_obrigacoes_com_fonte|avaliar_prontidao_canonica_obrigacoes|verificar_paridade_modelagem_financeira_canonica" caixa
```

### Criterios De Aceite

- Teste afetado reproduzido localmente.
- Quantidade de queries atual registrada.
- SQLs repetidos agrupados.
- Funcao ou bloco responsavel pelo crescimento identificado.
- Nenhuma alteracao de codigo feita nesta fase.

### Criterios De Rollback

Nao ha rollback tecnico nesta fase, pois nao deve haver alteracao. Se algum
arquivo for alterado por engano, reverter antes de liberar a proxima fase.

### Campo Final De Liberacao Da Proxima Fase

[ ] Fase concluida e proxima fase liberada

---

## Matriz De Decisao Apos O Diagnostico

| Sinal medido | Causa provavel | Primeira acao | Evitar |
| --- | --- | --- | --- |
| Queries repetidas para relacoes simples | `select_related` ausente | Ajustar queryset de origem | Acessar relacao direto no serializer |
| Queries repetidas para relacoes multiplas | `prefetch_related` ausente ou perdido | Prefetch controlado ou `Prefetch` especifico | Prefetch global sem medir memoria |
| Agregacao por item | Property ou serializer chama `aggregate` em loop | Agregar em lote e aplicar mapa | Cache como primeira solucao |
| Auditoria canonica por item na request | Readiness pesada dentro do dashboard | Criar caminho leve de leitura ou batching | Rodar paridade completa em toda request |
| Lista completa usada so para resumo | Selector retorna itens demais para o card | Criar/reusar selector de resumo equivalente | Remover campos do payload |
| Query count constante, mas lenta | Plano SQL ou indice insuficiente | Usar `EXPLAIN` e avaliar indice | Criar indice antes de resolver N+1 |
| Divergencia de valor apos otimizacao | Regra financeira mudou sem querer | Parar fase e comparar payload antigo/novo | Ajustar teste para aceitar valor novo |

Esta matriz nao substitui o diagnostico. Ela apenas define a primeira resposta
segura depois que a causa for medida.

---

## Fase 1 - Corrigir Preparo De Querysets Existentes

### Objetivo

Eliminar lazy loads e relacoes faltantes usando a estrutura atual de selectors,
sem alterar contrato JSON nem regra financeira.

### Ordem Preferencial De Correcao

1. Ajustar `select_related` em `querysets_dashboard_filtrados` quando a relacao
   faltante for simples e ja usada por serializers.
2. Ajustar `prefetch_related` ou `Prefetch` quando o problema vier de relacao
   multipla, como pagamentos.
3. Reaproveitar selector especializado existente se ele ja publicar a colecao
   com preparo melhor.
4. Usar `annotate` para totais por item quando o prefetch nao for adequado.
5. Criar helper novo somente se as opcoes anteriores gerarem duplicacao ou
   deixarem a regra espalhada.

### Trilhas Prioritarias De Correcao

1. Se o crescimento vier de relacoes faltantes em querysets do dashboard,
   corrigir o queryset de origem e manter os serializers sem lazy load.
2. Se o crescimento vier de `overduePayablesAllTime`, avaliar primeiro se o
   endpoint precisa de itens completos ou apenas de resumo.
3. Se o crescimento vier de prontidao canonica, separar auditoria completa de
   leitura de tela:
   - auditoria completa deve continuar disponivel em comando, admin ou endpoint
     tecnico apropriado;
   - request do dashboard deve usar caminho barato e previsivel;
   - qualquer decisao de ler canonico ou legado deve continuar documentada no
     payload quando esse status for publicado.
4. Se o crescimento vier de reconciliacao legado/ledger, reaproveitar mapas
   agregados por origem em vez de consultar por item.
5. Se o crescimento vier de filtros do dashboard, preferir opcoes agregadas ou
   querysets preparados ja existentes.

### Correcoes Aceitaveis Para Prontidao Canonica

- Reusar o resultado de uma leitura legada ja feita dentro da mesma chamada,
  evitando percorrer as mesmas obrigacoes duas vezes.
- Trocar verificacoes por item por carregamento em lote quando a comparacao for
  indispensavel na request.
- Criar um caminho leve de readiness para leitura, mantendo a auditoria completa
  em rotina separada.
- Criar um selector de resumo para vencidos all-time se a UI nao precisar dos
  itens completos nessa chamada.

### Correcoes Que Exigem Justificativa Extra

- Forcar `dataSource=legacy` no dashboard sem preservar a decisao canonica
  existente.
- Introduzir cache de readiness sem regra clara de invalidacao.
- Criar model, migration ou indice novo antes de provar que o problema e query
  count, e nao plano SQL.
- Mover calculo financeiro para o frontend.
- Remover aliases ou campos que hoje sao normalizados pelo Next.

### Cuidados Para Nao Quebrar A Aplicacao

- Nao trocar nomes de chaves no payload.
- Nao alterar filtros de data, evento, cliente, contrato ou status.
- Nao mudar ordenacao visual sem teste que prove equivalencia.
- Nao mudar `periodo_rapido=todos`, `vencidos` ou filtros personalizados.
- Nao trocar leitura canonica de obrigacoes por legada, nem o contrario, sem
  validar prontidao canonica.
- Nao remover aliases que o frontend ainda consome.
- Nao usar `.only()` se houver risco de adiar campo usado pelo serializer.
- Nao usar `.values()` em caminho que hoje precisa de metodo de model, display
  label, property ou serializer de dimensao.
- Nao materializar o mesmo queryset mais de uma vez dentro da mesma request sem
  motivo medido.
- Nao transformar auditoria de paridade em dependencia obrigatoria de cada
  chamada visual do dashboard.
- Nao substituir `relacao_carregada` por acesso direto a relacoes em serializers
  de resposta JSON.

### Arquivos Possivelmente Afetados

- `caixa/selectors_dashboard_filtros.py`
- `caixa/serializers_dashboard.py`
- `caixa/selectors_dashboard_movimentacoes.py`
- `caixa/selectors_dashboard_totais.py`
- `caixa/selectors_obrigacoes.py`
- `caixa/serializers_obrigacoes.py`
- `caixa/tests.py`

### Criterios De Aceite

- O teste afetado passa com queries constantes.
- O limite de queries continua menor ou igual a 40.
- Nenhum campo financeiro do payload muda sem intencao documentada.
- Os testes de contrato do `financial-overview` continuam passando.
- O bloco responsavel pela regressao fica coberto por teste ou por comentario
  claro no teste existente.
- O caminho escolhido fica alinhado com a regra de leitura centralizada descrita
  em `ARQUITETURA.md`.

### Campo Final De Liberacao Da Proxima Fase

[ ] Fase concluida e proxima fase liberada

---

## Fase 2 - Agregacoes Em Lote Quando Necessario

### Objetivo

Se a Fase 1 nao for suficiente, substituir agregacoes por item por agregacoes em
lote, preservando os mesmos valores financeiros.

### Regras Da Fase

- Preferir `annotate` ou mapas agregados por `id`/`evento_id`/`source_id`.
- Manter arredondamento com os mesmos helpers financeiros existentes.
- Comparar totais antes e depois para receitas, despesas, custos, FCI, FCF,
  obrigacoes e caixa disponivel.
- Evitar duplicar calculos que ja existam em `selectors_dashboard_totais`,
  `selectors_lancamentos`, `selectors_obrigacoes` ou services canonicos.
- Quando a tela consumir apenas resumo, nao montar lista completa apenas para
  contar e somar, salvo se a semantica depender de campos calculados por item.
- Quando o resumo depender de reconciliacao ledger/origem, agregar os
  lancamentos em lote e aplicar o mapa ao conjunto de itens, como ja acontece em
  partes de `selectors_obrigacoes`.
- Se o caminho canonico estiver pronto, preferir agregacoes no read-model
  canonico quando ele ja possuir os campos necessarios.

### Cenarios Que Justificam A Fase

- SQL repetido por custo de servico.
- SQL repetido por custo extra.
- SQL repetido por parcela, baixa, obrigacao ou lancamento.
- SQL repetido por dimensao operacional que nao possa ser resolvida apenas com
  `select_related`.
- Card de vencidos all-time montando itens completos quando o payload final so
  usa `count`, `amount`, `pendingAmount`, filtros e read model.
- Readiness canonica fazendo auditoria completa em request de dashboard.

### Ordem Preferencial Para Resumos

1. Usar agregacao direta no read-model canonico se a leitura canonica estiver
   pronta e os filtros forem equivalentes.
2. Usar selector legado existente com agregacoes em lote se o fallback atual for
   legado.
3. Reusar itens ja materializados na mesma request se eles ja foram carregados
   por outro bloco e representam o mesmo recorte.
4. Criar selector de resumo novo apenas quando as opcoes anteriores misturarem
   responsabilidades ou preservarem N+1.

### Criterios De Aceite

- Query count constante para 1, 9 e volume maior definido no teste.
- Valores financeiros iguais aos valores anteriores nos testes funcionais.
- Sem nova dependencia e sem cache.
- Resumo de vencidos all-time continua usando a mesma data de referencia e os
  mesmos filtros operacionais.

### Campo Final De Liberacao Da Proxima Fase

[ ] Fase concluida e proxima fase liberada

---

## Fase 3 - Plano SQL E Indices Somente Se Necessario

### Objetivo

Depois que o query count estiver constante, verificar se alguma query restante
continua lenta por falta de indice ou por plano SQL ruim.

### Regras Da Fase

- Nao criar indice para corrigir N+1.
- Nao criar migration enquanto o teste de query count ainda estiver falhando.
- Usar `EXPLAIN` apenas nas queries constantes mais caras.
- Priorizar campos ja usados nos filtros reais: data, status, evento, cliente,
  contrato visual via evento/orcamento, origem, fluxo e natureza.
- Qualquer indice novo precisa de justificativa com query, filtro e endpoint
  afetado.

### Criterios De Aceite

- Nenhum indice novo se o problema for resolvido apenas com batching/preload.
- Se indice for necessario, documentar a query alvo e validar migracao.
- Testes funcionais e de query count continuam passando.

### Campo Final De Liberacao Da Proxima Fase

[ ] Fase concluida e proxima fase liberada

---

## Fase 4 - Guardrails De Teste

### Objetivo

Garantir que a correcao nao volte a regredir e que nenhum contrato financeiro
tenha sido quebrado.

### Testes Obrigatorios

```powershell
$env:SECRET_KEY='local-validation-secret'; $env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_mantem_queries_constantes --verbosity 1
$env:SECRET_KEY='local-validation-secret'; $env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_dashboard_mantem_queries_constantes_com_mais_registros caixa.tests.FiltrosHtmlTests.test_custos_por_evento_mantem_queries_constantes_com_mais_registros caixa.tests.FiltrosHtmlTests.test_mes_financeiro_mantem_queries_constantes_com_mais_registros caixa.tests.FiltrosHtmlTests.test_listas_financeiras_mantem_queries_constantes_com_mais_registros caixa.tests.FiltrosHtmlTests.test_apis_cadastros_mantem_queries_constantes_com_mais_registros --verbosity 1
```

### Testes Funcionais Recomendados

```powershell
$env:SECRET_KEY='local-validation-secret'; $env:DEBUG='True'; .\venv\Scripts\python.exe manage.py test caixa.tests.DatasTests.test_filtros_dashboard_financial_overview_normalizam_params_do_frontend caixa.tests.PermissoesTests.test_api_dashboard_financial_overview_exige_permissao_da_tela caixa.tests.PermissoesTests.test_api_dashboard_financial_overview_nao_autenticada_retorna_json_401 caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_usa_mesma_regra_saldo_inicial caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_retorna_arrays_vazios_sem_dados --verbosity 1
```

Se alguma classe tiver sido renomeada no momento da execucao, localizar os
testes atuais do endpoint com:

```powershell
rg -n "api_dashboard_financial_overview|financial-overview|financial_overview" caixa\tests.py
```

### Guardrails Adicionais Recomendados

- Se a causa for `overduePayablesAllTime`, adicionar ou ajustar teste que
  confirme query count constante para esse bloco ou para o endpoint com esse
  bloco ativo.
- Se a causa for readiness canonica, adicionar teste que prove que a request do
  dashboard nao executa auditoria completa por item.
- Se for criado selector de resumo, testar equivalencia entre resumo antigo e
  resumo novo para um cenario com FCO, FCI, FCF, parcelas e financiamentos.
- Comparar as chaves de topo do payload antes e depois, ignorando `generatedAt`.
- Comparar campos numericos principais:
  `cashDeficitAmount`, `pendingAccountsAmount`, `cashFlow`,
  `cashAvailability`, `summary`, `overduePayablesAllTime`,
  `accountsReceivable`, `accountsPayable`, `serviceRevenue` e
  `resultadoFinanceiro`.

### Criterios De Aceite

- Teste de query count do `financial-overview` passa.
- Testes de query count relacionados continuam passando.
- Testes de permissao e autenticacao do endpoint continuam passando.
- Testes de payload vazio e filtros continuam passando.
- Payload mantem compatibilidade com `FinancialDashboardData` no frontend.
- Nenhum alias legado consumido pelo frontend e removido sem plano proprio.

### Campo Final De Liberacao Da Proxima Fase

[ ] Fase concluida e proxima fase liberada

---

## Fase 5 - Validacao Manual Do Contrato E Do Frontend

### Objetivo

Confirmar que a otimizacao nao quebrou o consumo pelo frontend Next.js nem a
leitura administrativa do backend.

### Validacoes Manuais

- Abrir o dashboard financeiro no frontend.
- Testar periodo `todos`.
- Testar periodo customizado com `startDate` e `endDate`.
- Testar filtros por cliente, evento e contrato.
- Testar status pendente, realizado/recebido/pago e vencidos quando aplicavel.
- Conferir cards de resumo, contas a receber, contas a pagar, vencidos,
  receitas por servico, FCO, FCI, FCF e caixa disponivel.
- Exportar CSV do dashboard financeiro e confirmar que campos de fluxo de caixa,
  contas pendentes, contas a receber e receitas por servico continuam
  preenchidos.
- Abrir links de detalhes de contas a pagar e contas a receber a partir do
  dashboard.
- Conferir que `overduePayablesAllTime.readModel.actual` continua coerente com
  a fonte usada.
- Conferir que o admin Django continua abrindo models financeiros relacionados.

### Criterios De Aceite

- Payload da API mantem campos esperados pelo frontend.
- Valores principais batem com a versao anterior ou com a regra de negocio.
- Nenhum erro 500 no endpoint.
- Nenhum erro de contrato no frontend.
- Exportacao CSV continua gerando linhas esperadas.
- Admin continua navegavel.

### Campo Final De Liberacao Da Proxima Fase

[ ] Fase concluida e proxima fase liberada

---

## Fase 6 - Liberacao Segura

### Objetivo

Publicar a correcao somente depois de validada localmente e, se houver ambiente
de homologacao/preview, validada fora da maquina local.

### Checklist De Liberacao

- Testes locais obrigatorios passaram.
- Query count final registrado.
- Mudancas revisadas para garantir que nao houve alteracao de regra financeira.
- Sem migrations novas, salvo decisao explicitamente documentada.
- Sem dependencia nova.
- Sem alteracao no frontend, salvo necessidade documentada.
- Commit local criado depois das validacoes.
- Deploy/push feito manualmente pelo responsavel do projeto.

### Criterios De Rollback

- Se o endpoint retornar 500, voltar ao ultimo commit estavel.
- Se valores financeiros divergirem sem explicacao, voltar ao ultimo commit
  estavel.
- Se o frontend perder campos do payload, voltar ao ultimo commit estavel.
- Se a leitura canonica/legada de obrigacoes mudar resultado, voltar ao ultimo
  commit estavel.

### Campo Final De Liberacao

[ ] Plano executado e correcao liberada

---

## Criterios Globais De Aceite

A correcao so deve ser considerada pronta quando todos os itens abaixo forem
verdadeiros:

- `test_api_dashboard_financial_overview_mantem_queries_constantes` passa com
  query count igual entre o cenario pequeno e o cenario maior.
- Query count final fica menor ou igual a 40, salvo decisao tecnica futura
  explicitamente documentada e aprovada.
- Testes funcionais do endpoint passam.
- Testes de query count relacionados continuam passando.
- Payload permanece compativel com o frontend Next.js.
- Valores financeiros principais permanecem equivalentes ao comportamento
  anterior ou a divergencia esta justificada por correcao de regra.
- Nenhuma auditoria completa de paridade canonica roda obrigatoriamente em cada
  request visual do dashboard.
- Nenhuma dependencia nova, migration, indice ou cache foi adicionado sem
  evidencia registrada.
- Rollback e ultimo commit estavel estao claros antes de publicar.

## Criterios De Bloqueio

A execucao deve parar se qualquer um destes pontos ocorrer:

- query count continua crescendo com o volume;
- payload perde chave consumida pelo frontend;
- valores de caixa, FCO, FCI, FCF, contas vencidas, contas a receber ou
  resultado financeiro divergem sem explicacao;
- fallback canonico/legado muda a fonte dos dados sem teste de equivalencia;
- a solucao exige cache ou migration antes de diagnosticar a causa real;
- a correcao depende de alterar o frontend para compensar mudanca evitavel no
  backend.

---

## Registro De Execucao - 2026-06-10

- Teste reproduzido localmente:
  `caixa.tests.FiltrosHtmlTests.test_api_dashboard_financial_overview_mantem_queries_constantes`.
- Resultado atual:
  `AssertionError: 420 != 111`.
- Interpretacao:
  o endpoint `financial-overview` cresce em quantidade de queries conforme o
  volume de registros aumenta, indicando N+1 ou agregacao repetida.
- Nenhuma correcao de codigo foi implementada neste registro.

## Registro De Revisao Ampla - 2026-06-10

- Plano revisado contra backend Django e frontend Next.js.
- Adicionado mapa do fluxo atual do endpoint.
- Adicionada secao de contrato que nao pode mudar, incluindo campos usados pelo
  frontend e aliases legados ainda normalizados.
- Adicionadas hipoteses tecnicas mais especificas sobre:
  - `montar_contas_vencidas_all_time_dashboard`;
  - `listar_obrigacoes_com_fonte`;
  - `avaliar_prontidao_canonica_obrigacoes`;
  - `verificar_paridade_modelagem_financeira_canonica`;
  - montagem de resumo all-time a partir de lista completa.
- Fase 0 fortalecida com medicao por bloco e separacao de readiness canonica,
  fallback legado, reconciliacao e resumo.
- Fase 1 ampliada com trilhas prioritarias e regras para nao transformar
  auditoria de paridade em dependencia obrigatoria da request visual.
- Fase 2 ampliada com criterios para resumos em lote.
- Adicionada fase de plano SQL para tratar indices somente depois que o
  query count estiver constante.
- Fase de guardrails ampliada com payload e testes especificos por bloco.
- Fase de validacao manual ampliada com exportacao CSV, links de detalhe e status do
  read model.
- Nenhuma correcao de codigo foi implementada nesta revisao.

## Registro De Segunda Revisao Ampla - 2026-06-10

- Adicionada secao de evidencias obrigatorias da correcao.
- Adicionada matriz de decisao apos diagnostico, ligando sinais medidos a
  acoes seguras.
- Renumeradas as fases para remover `Fase 2.5` e manter sequencia linear.
- Adicionados criterios globais de aceite.
- Adicionados criterios de bloqueio para impedir que uma solucao arriscada
  avance.
- Mantida a regra de nao implementar codigo da aplicacao durante a revisao do
  plano.

## Registro De Execucao Da Fase 1 - 2026-06-10

- Escopo executado:
  corrigir exclusivamente o crescimento de queries causado por
  `overduePayablesAllTime`.
- Arquivos alterados:
  - `caixa/serializers_obrigacoes.py`
  - `caixa/serializers_dashboard.py`
  - `caixa/tests.py`
- Mudanca aplicada:
  - mantido `listar_obrigacoes_com_fonte` com auditoria completa para os fluxos
    tecnicos e para o endpoint completo de obrigacoes;
  - criado `listar_obrigacoes_com_fonte_leitura_visual` para leitura visual do
    dashboard;
  - criado `avaliar_prontidao_canonica_visual_obrigacoes`, caminho leve que nao
    chama `verificar_paridade_modelagem_financeira_canonica`;
  - `montar_contas_vencidas_all_time_dashboard` passou a usar a leitura visual;
  - adicionado teste
    `test_dashboard_overdue_payables_all_time_nao_executa_auditoria_canonica`.
- Query count antes da correcao:
  - cenario pequeno: 111 queries;
  - cenario maior: 420 queries;
  - crescimento: +309 queries.
- Query count depois da correcao:
  - cenario pequeno: 36 queries;
  - cenario maior: 36 queries;
  - crescimento: 0 queries.
- Valores conferidos para `overduePayablesAllTime` no cenario medido:
  - `count`: 72;
  - `amount`: 4050.0;
  - `pendingAmount`: 4050.0;
  - `readModel`: `{"requested": "canonical", "actual": "canonical"}`.
- Os valores de `overduePayablesAllTime` bateram com o resumo canonico e com o
  resumo legado no cenario medido.
- Regra financeira preservada:
  a alteracao nao muda filtros, status, datas, saldos, arredondamento, aliases
  ou serializacao financeira; ela apenas impede que a auditoria completa de
  paridade canonica rode dentro da request visual do dashboard.
- Nao foram criados cache, migracao, indice, dependencia nova ou alteracao no
  frontend.

## Registro De Validacao Ampliada - 2026-06-10

- Testes de query count relacionados executados com sucesso:
  - `test_api_dashboard_financial_overview_mantem_queries_constantes`;
  - `test_dashboard_mantem_queries_constantes_com_mais_registros`;
  - `test_custos_por_evento_mantem_queries_constantes_com_mais_registros`;
  - `test_mes_financeiro_mantem_queries_constantes_com_mais_registros`;
  - `test_listas_financeiras_mantem_queries_constantes_com_mais_registros`;
  - `test_apis_cadastros_mantem_queries_constantes_com_mais_registros`;
  - `test_dashboard_overdue_payables_all_time_nao_executa_auditoria_canonica`.
- Resultado dos testes de query count: 7 testes executados, 7 passaram.
- Testes funcionais do `financial-overview` executados com sucesso:
  - `test_filtros_dashboard_financial_overview_normalizam_params_do_frontend`;
  - `test_api_dashboard_financial_overview_exige_permissao_da_tela`;
  - `test_api_dashboard_financial_overview_nao_autenticada_retorna_json_401`;
  - `test_api_dashboard_financial_overview_usa_mesma_regra_saldo_inicial`;
  - `test_api_dashboard_financial_overview_retorna_arrays_vazios_sem_dados`.
- Resultado dos testes funcionais: 5 testes executados, 5 passaram.
- Comparacao de payload antes/depois:
  - queries antes: 420;
  - queries depois: 36;
  - chaves de topo preservadas;
  - `overduePayablesAllTime`: igual;
  - `cashFlow`: igual;
  - `cashAvailability`: igual;
  - `summary`: igual;
  - `accountsReceivable`: igual;
  - `accountsPayable`: igual;
  - `serviceRevenue`: igual;
  - `resultadoFinanceiro`: igual.
- Validacao concluida sem novas mudancas alem da Fase 1.
- Nao foi feito push, merge ou deploy.

## Registro De Validacao Final E Conclusao - 2026-06-10

- Ponto de partida confirmado:
  - commit local base: `7e784dd Otimiza query count do financial overview`;
  - backend sem alteracoes pendentes antes da validacao final;
  - frontend sem alteracoes pendentes antes da validacao final.
- Fases revisadas:
  - Fase 0 concluida previamente com diagnostico do crescimento de queries;
  - Fase 1 concluida no commit `7e784dd`;
  - Fase 2 nao exigiu nova implementacao, pois a Fase 1 deixou o query count
    constante e abaixo do limite definido;
  - Fase 3 nao exigiu migration, indice ou plano SQL adicional, pois nao
    restou evidencia de gargalo SQL com query count crescente;
  - Fase 4 permaneceu coberta pelos testes de guardrail de query count e
    contrato;
  - Fase 5 foi executada no limite possivel localmente, com validacao de
    contrato consumido pelo frontend e sem alteracao no frontend;
  - Fase 6 ficou pronta para liberacao manual, sem push, merge ou deploy nesta
    execucao.
- Validacao local do frontend:
  - `corepack pnpm run typecheck`: passou;
  - `corepack pnpm run check:dashboard`: passou;
  - checks cobertos: uso canonico financeiro, expenses overview, grids
    responsivos, layout de filtros, separacao contrato/evento, fronteira de
    servico e acessibilidade do dashboard;
  - unico aviso observado: `MODULE_TYPELESS_PACKAGE_JSON` do Node ao ler modulo
    TypeScript/ESM existente; nao bloqueia a validacao e nao foi tratado por
    exigir mudanca de configuracao fora do escopo.
- Validacao final do backend:
  - testes de query count relacionados: 7 executados, 7 passaram;
  - testes funcionais do `financial-overview`: 5 executados, 5 passaram;
  - `python manage.py check`: passou, sem issues;
  - `python manage.py makemigrations --check --dry-run`: passou, sem mudancas
    detectadas.
- Comparacao final de payload nos campos principais:
  - caminho atual: 36 queries;
  - caminho legado simulado: 420 queries;
  - `overduePayablesAllTime`: igual;
  - `cashFlow`: igual;
  - `cashAvailability`: igual;
  - `summary`: igual;
  - `accountsReceivable`: igual;
  - `accountsPayable`: igual;
  - `serviceRevenue`: igual;
  - `resultadoFinanceiro`: igual;
  - resultado geral: payload compativel e valores financeiros preservados.
- Valor conferido de `overduePayablesAllTime` no cenario final:
  - `count`: 72;
  - `amount`: 4050.0;
  - `pendingAmount`: 4050.0;
  - `readModel`: `{"requested": "canonical", "actual": "canonical"}`.
- Confirmacoes de seguranca:
  - sem alteracao de frontend;
  - sem alteracao de regra financeira, filtros, status, saldos, aliases ou
    contrato JSON;
  - sem cache;
  - sem migration;
  - sem indice;
  - sem dependencia nova;
  - sem push, merge ou deploy.
- Riscos remanescentes:
  - validacao manual em navegador, CSV e admin depende de ambiente interativo e
    deve ser repetida pelo responsavel antes/depois do deploy manual;
  - smoke test em homologacao/producao deve ocorrer somente apos push/deploy
    manual autorizado.
- Recomendacao final:
  - plano concluido localmente e pronto para push/deploy manual pelo
    responsavel do projeto.

## Registro De Revisao Geral E Robustez - 2026-06-10

- Revisao executada apos validacao conceitual da correcao de query count do
  `financial-overview`.
- Problema encontrado:
  - a prontidao visual canonica de `overduePayablesAllTime` estava barata e
    mantinha a auditoria completa fora da request, mas considerava a leitura
    canonica pronta quando existia qualquer registro em `ObrigacaoFinanceira`;
  - em uma base parcialmente migrada, isso poderia indicar leitura canonica
    mesmo quando nao houvesse obrigacao canonica compativel com os filtros
    visuais aplicados, como vencidos all-time, cliente, evento ou contrato.
- Risco evitado:
  - falso positivo de `readModel.actual = canonical` em filtro sem registro
    canonico correspondente;
  - diferenca visual em `overduePayablesAllTime` durante janela de migracao ou
    base parcialmente sincronizada;
  - reintroducao da auditoria completa dentro da request normal para resolver
    esse cenario.
- Melhoria aplicada:
  - criada contagem canonica filtrada e barata para leitura visual;
  - `avaliar_prontidao_canonica_visual_obrigacoes` passou a receber os filtros
    normalizados e decidir a prontidao com base nos registros canonicos
    compativeis com a consulta visual;
  - mantido fallback legado quando nao ha registro canonico filtrado;
  - mantida a auditoria completa disponivel fora da request visual.
- Arquivos alterados:
  - `caixa/selectors_obrigacoes_canonicas.py`;
  - `caixa/serializers_obrigacoes.py`;
  - `caixa/tests.py`;
  - `docs/PLANO_CORRECAO_QUERY_COUNT_FINANCIAL_OVERVIEW.md`.
- Teste novo criado:
  - `test_dashboard_overdue_payables_all_time_faz_fallback_visual_sem_canonico_filtrado`;
  - cobre o cenario em que existe registro canonico no banco, mas nao para o
    filtro visual de vencidos all-time, garantindo fallback legado sem chamar
    `verificar_paridade_modelagem_financeira_canonica`.
- Validacoes executadas:
  - testes focados do bloco `overduePayablesAllTime`: passaram;
  - testes de query count relacionados: 8 executados, 8 passaram;
  - testes funcionais do `financial-overview`: 5 executados, 5 passaram;
  - `python manage.py check`: passou, sem issues;
  - `python manage.py makemigrations --check --dry-run`: passou, sem mudancas
    detectadas;
  - `git diff --check`: passou.
- Comparacao de payload e queries:
  - caminho atual: 36 queries;
  - caminho legado simulado: 420 queries;
  - `overduePayablesAllTime`, `cashFlow`, `cashAvailability`, `summary`,
    `accountsReceivable`, `accountsPayable`, `serviceRevenue` e
    `resultadoFinanceiro` permaneceram equivalentes no cenario medido.
- Confirmacoes de seguranca:
  - sem alteracao de frontend;
  - sem migration;
  - sem cache;
  - sem dependencia nova;
  - sem alteracao de regra financeira, filtros, status, saldos, aliases ou
    contrato JSON;
  - sem push, merge ou deploy.
