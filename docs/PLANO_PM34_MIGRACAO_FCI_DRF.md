# Plano PM-34 - Migracao incremental de `GET/POST /api/fci/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar de forma incremental e controlada o endpoint `GET/POST /api/fci/` para
Django REST Framework, preservando integralmente o contrato atual consumido
pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da view de FCI, sem alterar regra de
negocio, permissao, CSRF, filtros, aliases, status HTTP, payloads, selectors,
serializers manuais, signals, lancamentos financeiros, obrigacoes canonicas,
baixas canonicas ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET/POST /api/fci/` em testes antes da
  migracao.
- Migrar somente a view `api_investimentos`.
- Manter a URL atual `/api/fci/`.
- Manter o nome de rota `caixa:api_investimentos`.
- Manter os metodos `GET` e `POST`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` apenas na borda.
- Preservar `405` manual atual sem promover para `405` padrao Django/DRF.
- Preservar CSRF real no `POST`.
- Preservar permissoes manuais:
  - `GET` exige `caixa.view_investimento`;
  - `POST` exige `caixa.view_investimento` e `caixa.add_investimento`.
- Preservar filtros, aliases, defaults e validacoes atuais.
- Reaproveitar selectors, serializers manuais e helpers atuais.
- Preservar signals e efeitos financeiros atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- FCF.
- Credores FCF.
- Dividas, parcelas ou movimentacoes de financiamento.
- Liquidacao de obrigacoes.
- Listagem/exportacao de obrigacoes.
- Baixas financeiras canonicas.
- Modelagem financeira canonica.
- Dashboard financeiro.
- Mes financeiro.
- Lancamentos financeiros.
- Outros endpoints financeiros.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Serializers DRF.
- ViewSets.
- ModelViewSets.
- Refatoracao de regra de negocio.
- Alteracao de selectors.
- Alteracao de serializers manuais.
- Alteracao de services.
- Alteracao de models.
- Alteracao de signals.
- Criacao de investimento real na etapa de planejamento.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, migrar somente `GET/POST /api/fci/`.

Como o `POST` de FCI cria investimento e aciona efeitos financeiros por
signals, a PM deve manter a regra de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, filtros, aliases,
validacoes, defaults, signals, efeitos financeiros ou comportamento runtime
apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-34.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_investimentos.py`.
- `caixa/permissions.py`.
- `caixa/selectors_investimentos.py`.
- `caixa/serializers_investimentos.py`.
- `caixa/models_fci.py`.
- `caixa/signals.py`.
- `caixa/services_lancamentos.py`.
- `caixa/services_modelagem_canonica.py`.
- `caixa/tests.py`.

View atual:

- `api_investimentos`.

Rota atual:

- `path("api/fci/", api_investimentos, name="api_investimentos")`.

Nome de rota:

- `caixa:api_investimentos`.

Implementacao atual:

- Django puro.
- Usa `JsonResponse` e `api_no_store_json_response`.
- Ainda nao esta migrado para DRF.

Decorador atual:

- `@require_api_permission(FINANCIAL_INVESTMENTS_PERMISSION)`.

Permissoes atuais:

- `FINANCIAL_INVESTMENTS_PERMISSION = caixa.view_investimento`.
- `ADD_FINANCIAL_INVESTMENT_PERMISSION = caixa.add_investimento`.

Metodo `GET`:

- Exige usuario autenticado.
- Exige `caixa.view_investimento`.
- Monta payload via `montar_payload_investimentos_api`.
- Acrescenta `permissions.canCreate` conforme `caixa.add_investimento`.

Metodo `POST`:

- Exige usuario autenticado.
- Exige `caixa.view_investimento` pelo wrapper externo.
- Exige `caixa.add_investimento` dentro de `_api_criar_investimento`.
- Exige `Content-Type: application/json`.
- Cria `Investimento` por `_investment_from_payload`.
- Retorna `201` com `data.investment` e `data.message`.

Metodos nao permitidos:

- Metodos diferentes de `GET` e `POST` retornam `405` manual.
- Payload atual:

```json
{"detail": "Metodo nao permitido."}
```

- Nao ha header `Allow` no contrato manual atual.
- A resposta JSON recebe headers no-store via `require_api_permission`.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado sem `caixa.view_investimento`:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento no `POST` para usuario com `caixa.view_investimento`, mas sem
`caixa.add_investimento`:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

CSRF atual:

- `POST` usa CSRF real do Django.
- Sem token valido, a requisicao deve ser bloqueada antes da view com `403`
  HTML.
- A migracao nao pode alterar CSRF global.

Content-Type no `POST`:

- Aceito: `application/json`.
- Qualquer outro `Content-Type` retorna `415`:

```json
{"detail": "Content-Type deve ser application/json."}
```

JSON invalido:

- JSON invalido, body nao UTF-8 ou body JSON nao-dict retornam `400`:

```json
{"detail": "JSON invalido."}
```

Payload aceito no `POST`:

- `description` / `descricao`.
- `category` / `categoria`.
- `flowType` / `tipo_fluxo`.
- `plannedAmount` / `valor_previsto`.
- `realizedAmount` / `valor_realizado`.
- `plannedDate` / `data_prevista`.
- `realizedDate` / `data_realizacao`.
- `eventId` / `evento` / `evento_id`.
- `notes` / `observacao`.

Defaults e normalizacoes do `POST`:

- `realizedAmount` default: `0.00`.
- Se `realizedAmount > 0` e `realizedDate` nao for informado, usa
  `plannedDate`.
- Valores decimais aceitam virgula ou ponto por conversao com `Decimal`.
- Evento ausente e aceito.
- Evento invalido ou inexistente retorna erro de validacao em `eventId`.

Validacoes principais:

- `plannedAmount` invalido retorna erro em `plannedAmount`.
- `realizedAmount` invalido retorna erro em `realizedAmount`.
- `plannedDate` invalida retorna erro em `plannedDate`.
- Evento invalido retorna erro em `eventId`.
- Evento inexistente retorna erro em `eventId`.
- Validacoes do model `Investimento` continuam valendo:
  - valores nao negativos;
  - valor realizado nao maior que previsto;
  - choices validos de categoria, tipo de fluxo e status;
  - dimensao operacional por evento;
  - caixa suficiente para aumento de saida realizada;
  - status calculado por valor previsto/realizado.

Shape de erro de validacao:

```json
{"errors": {}}
```

Shape top-level do `GET` sucesso:

- `filters` / `filtros`.
- `filterOptions` / `opcoes`.
- `totals` / `totais`.
- `projectedInvestmentFlow`.
- `realizedInvestmentFlow`.
- `dateBasis`.
- `investments` / `investimentos`.
- `categoryGroups` / `grupos_categoria`.
- `permissions`.

`permissions`:

```json
{"canCreate": true}
```

Filtros HTTP canonicos aceitos no `GET`:

- `startDate`.
- `endDate`.
- `category`.
- `flowType`.
- `status`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `period`.
- `quickPeriod`.

Aliases internos no selector:

- `data_inicial`.
- `data_final`.
- `categoria`.
- `tipo_fluxo`.
- `evento`.
- `evento_id`.
- `costCenterId`.
- `cliente`.
- `cliente_id`.
- `contrato_codigo`.

Observacao:

- A PM deve preservar o comportamento atual desses aliases sem promover novos
  contratos HTTP sem decisao explicita.

Totais/agregacoes retornadas:

- `total_previsto_entrada`.
- `total_previsto_saida`.
- `total_realizado_entrada`.
- `total_realizado_saida`.
- `saldo_previsto_fci`.
- `saldo_realizado_fci`.
- `resultado_financeiro_fci_previsto`.
- `resultado_financeiro_fci_projetado`.
- `resultado_financeiro_fci_realizado`.
- `entradas_investimento_projetadas`.
- `saidas_investimento_projetadas`.
- `entradas_investimento_realizadas`.
- `saidas_investimento_realizadas`.
- `resultado_financeiro_investimentos_projetado`.
- `resultado_financeiro_investimentos_realizado`.
- Aliases camelCase em `totals`.

Shape do `POST` sucesso:

```json
{
  "data": {
    "investment": {},
    "message": "Investimento cadastrado com sucesso."
  }
}
```

Shape de `investment`:

- `id`.
- `date`.
- `plannedDate`.
- `realizedDate`.
- `data_prevista`.
- `data_realizacao`.
- `description`.
- `investmentDescription`.
- `descricao`.
- `category`.
- `categoryLabel`.
- `categoria`.
- `categoria_display`.
- `flowType`.
- `flowTypeLabel`.
- `tipo_fluxo`.
- `tipo_fluxo_display`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `pendingRealizationAmount`.
- `valor_previsto`.
- `valor_realizado`.
- `saldo_restante`.
- `valor_pendente_realizacao`.
- `status`.
- `statusLabel`.
- `status_display`.
- `baixado_manualmente`.
- `manuallySettled`.
- Campos de dimensao operacional serializados por
  `serializar_dimensao_operacional`.

Status codes atuais:

- `200` para `GET` sucesso.
- `201` para `POST` sucesso.
- `400` para JSON invalido/body nao-dict e validacoes.
- `401` para anonimo.
- `403` para usuario sem permissao.
- `405` manual para metodo nao permitido.
- `415` para `Content-Type` invalido no `POST`.

Headers relevantes:

- Respostas JSON devem ter `Content-Type: application/json`.
- Respostas JSON controladas pela API devem ter `Cache-Control` com `no-store`.
- `405` manual atual nao deve ganhar header `Allow` sem decisao explicita.

Efeitos colaterais do `POST`:

- Cria `Investimento`.
- Ao salvar `Investimento`, signals executam:
  - `sincronizar_lancamento_investimento`;
  - `sincronizar_obrigacao_investimento_canonica`;
  - `sincronizar_baixa_canonica_por_origem("investimento", instance)`.
- Pode criar/atualizar `LancamentoFinanceiro` quando `valor_realizado > 0` e
  status nao for cancelado.
- Cria/atualiza `ObrigacaoFinanceira` canonica.
- Pode criar/remover `BaixaFinanceira` canonica conforme lancamento.
- Impacta FCI, caixa, dashboard, mes financeiro, obrigacoes e lancamentos por
  meio das sincronizacoes existentes.

Transacoes:

- Nao ha `transaction.atomic` explicito na view.
- Esta PM nao deve alterar esse comportamento.

Testes existentes:

- Rota `/api/fci/`.
- Anonimo `401`.
- Usuario sem permissao `403`.
- `GET` sucesso com `caixa.view_investimento`.
- Contrato JSON do `GET`.
- Filtros `startDate`, `endDate`, `period`, `quickPeriod`, `category`,
  `flowType` e `contractCode`.
- Choices de filtros.
- Query count do contexto de FCI.
- Sincronizacao de investimento com lancamento financeiro.
- Sincronizacao de dimensao operacional no ledger.
- Testes de obrigacoes/liquidacao que usam origem `investimento`.

Lacunas identificadas:

- POST anonimo.
- POST sem `caixa.view_investimento`.
- POST com `caixa.view_investimento`, mas sem `caixa.add_investimento`.
- CSRF real no POST.
- `Content-Type` invalido `415`.
- JSON invalido/body nao-dict `400`.
- Validacoes criticas com `{"errors": ...}`.
- Evento inexistente.
- Shape completo do POST sucesso.
- Shape completo de `investment`.
- 405 manual sem `Allow`.
- Headers JSON/no-store.
- Efeitos colaterais do POST:
  - cria investimento;
  - sincroniza lancamento;
  - sincroniza obrigacao canonica;
  - sincroniza baixa canonica quando aplicavel;
  - nao duplica lancamento/obrigacao/baixa.

## Riscos especificos do FCI

- `POST` cria entidade financeira real.
- Signals sincronizam ledger, obrigacoes e baixas canonicas.
- Alterar parsing de body via DRF pode mudar `Content-Type`, JSON invalido e
  body nao-dict.
- DRF pode trocar o `405` manual atual por `405` padrao com `Allow`.
- Permissao global DRF pode mudar o contrato de `401`/`403`.
- `SessionAuthentication` pode alterar o ponto de bloqueio de CSRF se a ordem
  de decorators nao for controlada.
- Valores realizados podem afetar caixa, status e disponibilidade.
- Validacoes de model e services podem ter efeitos indiretos em totais.
- Schema OpenAPI pode ficar generico, mas isso nao justifica mudar runtime.

## Guardrails

- Nao criar investimento real durante planejamento.
- Em testes de criacao, usar banco de teste e fixtures controladas.
- Nao acessar `request.data` se isso mudar `Content-Type`/JSON invalido.
- Nao trocar o `405` manual por DRF/Django padrao.
- Nao criar serializer DRF.
- Nao criar ViewSet ou ModelViewSet.
- Nao alterar `Investimento`.
- Nao alterar signals.
- Nao alterar services de lancamento, obrigacao ou baixa.
- Nao alterar selectors ou serializers manuais.
- Nao alterar FCF, liquidacao, obrigacoes, dashboard ou outros endpoints.
- Nao alterar frontend, settings, CORS, CSRF global ou auth global.
- Preservar runtime mesmo que o schema OpenAPI fique generico.

## Fases

### PM-34.1 - Diagnostico read-only

Status: concluida.

Objetivo:

- Mapear contrato atual de `GET/POST /api/fci/`.
- Identificar arquivos, permissoes, CSRF, filtros, aliases, payloads, headers,
  efeitos colaterais e lacunas de teste.

Resultado:

- Endpoint permanece Django puro.
- Contrato atual foi mapeado por leitura de codigo e testes existentes.
- Nenhum arquivo foi alterado.
- Nenhum investimento real foi criado.

### PM-34.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.

Cobrir:

- `GET` anonimo `401`.
- `GET` autenticado sem `caixa.view_investimento` `403`.
- `GET` com `caixa.view_investimento` retorna `200`.
- `POST` anonimo `401`.
- `POST` autenticado sem `caixa.view_investimento` `403`.
- `POST` com `caixa.view_investimento`, mas sem `caixa.add_investimento`,
  retorna `403`.
- CSRF real: `POST` sem token valido bloqueia antes da view com `403` HTML.
- `POST` com CSRF valido chega na view.
- `Content-Type` invalido retorna `415`.
- JSON invalido retorna `400`.
- Body JSON nao-dict retorna `400`.
- Validacoes criticas retornam `{"errors": ...}`.
- Evento inexistente retorna erro de validacao em `eventId`.
- Metodos nao permitidos preservam `405` manual:

```json
{"detail": "Metodo nao permitido."}
```

- `405` manual nao deve ganhar header `Allow`, se esse for o contrato atual.
- Headers JSON/no-store em respostas JSON.
- Shape completo do `GET`:
  - `filters` / `filtros`;
  - `filterOptions` / `opcoes`;
  - `totals` / `totais`;
  - `projectedInvestmentFlow`;
  - `realizedInvestmentFlow`;
  - `dateBasis`;
  - `investments` / `investimentos`;
  - `categoryGroups` / `grupos_categoria`;
  - `permissions`.
- Shape completo do `POST` sucesso:
  - `data.investment`;
  - `data.message`.
- Shape completo de `investment`.
- Filtros GET preservados:
  - `startDate`;
  - `endDate`;
  - `category`;
  - `flowType`;
  - `status`;
  - `contractCode`;
  - `eventId`;
  - `clientId`;
  - `period`;
  - `quickPeriod`.
- Aliases internos do selector preservados sem mudar contrato HTTP.
- Aliases POST preservados:
  - `description` / `descricao`;
  - `category` / `categoria`;
  - `flowType` / `tipo_fluxo`;
  - `plannedAmount` / `valor_previsto`;
  - `realizedAmount` / `valor_realizado`;
  - `plannedDate` / `data_prevista`;
  - `realizedDate` / `data_realizacao`;
  - `eventId` / `evento` / `evento_id`;
  - `notes` / `observacao`.
- Default `realizedAmount = 0.00` preservado.
- Regra `realizedAmount > 0` sem `realizedDate` usa `plannedDate`.
- Efeitos colaterais preservados:
  - cria `Investimento`;
  - sincroniza `LancamentoFinanceiro` quando aplicavel;
  - sincroniza `ObrigacaoFinanceira` canonica;
  - sincroniza `BaixaFinanceira` canonica quando aplicavel;
  - nao duplica lancamento/obrigacao/baixa.

Comandos previstos:

```bash
python manage.py check
python manage.py test caixa.tests.FiltrosHtmlTests
```

Critério de aceite da fase:

- Testes focados passam.
- Nenhum arquivo runtime alterado.
- Endpoint ainda nao migrado para DRF.

### PM-34.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Migrar somente `api_investimentos` para DRF, preservando o contrato runtime
  congelado na PM-34.2.

Regras:

- Converter somente `api_investimentos`.
- Usar `@api_view(["GET", "POST"])`.
- Usar `Response` apenas na borda.
- Preservar `405` manual sem `Allow`.
- Preservar CSRF real no `POST`.
- Preservar permissoes manuais:
  - `GET` exige `view_investimento`;
  - `POST` exige `view_investimento` + `add_investimento`.
- Preservar `Content-Type`, JSON invalido e body nao-dict atuais.
- Preservar filtros, aliases, defaults e validacoes.
- Preservar signals/efeitos financeiros atuais.
- Reaproveitar selectors, serializers manuais e helpers atuais.
- Nao criar Serializer, ViewSet ou ModelViewSet.
- Nao mexer em FCF, liquidacao, obrigacoes, dashboard ou outros endpoints
  financeiros.

Comandos previstos:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
```

Critério de aceite da fase:

- Testes focados passam.
- `check` passa.
- `spectacular --validate` passa, mesmo que o schema seja generico.
- OpenAPI inclui `/api/fci/`.
- Nenhum contrato runtime alterado.

### PM-34.4 - Validacao completa

Status: concluida.

Objetivo:

- Validar que a migracao nao causou regressao em FCI, ledger, obrigacoes,
  baixas canonicas e suite geral.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Validar:

- Testes focados de FCI.
- Testes relacionados existentes de investimento/ledger/obrigacao canonica.
- Suite completa.
- Sem mudanca em FCF, liquidacao, obrigacoes, dashboard ou outros endpoints.
- Sem mudanca em settings, CORS, CSRF global ou autenticacao global.

Critério de aceite da fase:

- Todos os comandos passam.
- Sem mudanca de contrato.
- Sem mudanca de efeitos financeiros.

### PM-34.5 - Encerramento

Status: concluida.

Objetivo:

- Atualizar este documento com registro final da execucao.

Registrar:

- Arquivos alterados.
- Testes criados/alterados.
- Comandos executados e resultados.
- Resultado do `check`.
- Resultado do `spectacular --validate`.
- Resultado dos testes focados.
- Resultado da suite completa.
- Warnings, se houver.
- Confirmacao de que FCF, liquidacao, obrigacoes, dashboard e outros endpoints
  financeiros nao foram alterados.
- Confirmacao de que settings, CORS, CSRF global e auth global nao foram
  alterados.
- Confirmacao de pronto ou nao para commit manual.

## Criterios de aceite da PM

- `GET/POST /api/fci/` migrado para DRF.
- URL e nome de rota preservados.
- Metodos `GET` e `POST` preservados.
- `405` manual preservado.
- CSRF real preservado.
- Anonimo recebe `401` atual.
- Usuario sem permissao recebe `403` atual.
- `POST` sem `add_investimento` recebe `403` atual.
- `Content-Type` invalido preservado como `415`.
- JSON invalido/body nao-dict preservado como `400`.
- Shape do `GET` preservado.
- Shape do `POST` preservado.
- Shape de `investment` preservado.
- Filtros e aliases preservados.
- Defaults e validacoes preservados.
- Signals e efeitos financeiros preservados.
- FCF, liquidacao, obrigacoes, dashboard e outros endpoints nao alterados.
- Frontend nao alterado.
- Settings, CORS, CSRF global e auth global nao alterados.
- Sem Serializer DRF, ViewSet ou ModelViewSet.
- `python manage.py check` passa.
- `python manage.py spectacular --validate` passa.
- Testes focados passam.
- Suite completa passa.

## Criterios de bloqueio

Parar imediatamente se:

- CSRF mudar.
- `Content-Type` invalido mudar.
- JSON invalido/body nao-dict mudar.
- `401`, `403`, `405`, `415` ou status de sucesso mudarem.
- `405` manual ganhar/remover caracteristicas fora do contrato atual.
- Shape do `GET` mudar.
- Shape do `POST` mudar.
- Shape de `investment` mudar.
- Algum filtro ou alias mudar.
- Defaults mudarem.
- Validacoes mudarem.
- Lancamento, obrigacao ou baixa canonica duplicar.
- Algum efeito financeiro mudar.
- FCF, liquidacao, obrigacoes, dashboard ou outros endpoints precisarem ser
  alterados.
- For necessario criar Serializer, ViewSet ou ModelViewSet.
- For necessaria decisao arquitetural fora do escopo.

## Estrategia de rollback

Se a migracao causar qualquer divergencia de contrato:

- Reverter apenas as alteracoes da PM-34.3 em `api_investimentos`.
- Manter os testes de paridade da PM-34.2, se eles estiverem corretos e
  representarem o contrato atual.
- Remover somente ajustes de teste que dependam da implementacao migrada.
- Confirmar que `GET/POST /api/fci/` voltou ao comportamento Django puro.
- Rodar testes focados de FCI e `python manage.py check`.

Nao usar rollback destrutivo de git sem aprovacao explicita.

## Registro de execucao

### PM-34.1

Status: concluida.

Resumo:

- Diagnostico read-only realizado.
- Nenhum arquivo alterado.
- Nenhum investimento real criado.
- Contrato atual documentado neste plano.

### PM-34.2

Status: concluida.

Resumo:

- Testes de paridade adicionados em `caixa/tests.py` para congelar o contrato
  runtime de `GET/POST /api/fci/` antes da migracao.
- Foram cobertos auth, permissoes, CSRF real no POST, `Content-Type` invalido,
  JSON invalido/body nao-dict, validacoes, evento inexistente, `405` manual sem
  `Allow`, shape do GET, filtros, aliases, shape do POST, defaults e efeitos
  financeiros principais.
- O endpoint ainda permanecia Django puro nesta fase.

Testes criados:

- `test_api_investimentos_preserva_auth_permissoes_e_headers`.
- `test_api_investimentos_preserva_csrf_real_no_post`.
- `test_api_investimentos_preserva_erros_de_content_type_json_e_validacao`.
- `test_api_investimentos_preserva_405_manual_sem_allow`.
- `test_api_investimentos_preserva_shape_get_filtros_e_aliases`.
- `test_api_investimentos_post_preserva_aliases_defaults_shape_e_efeitos`.

Comandos e resultados:

- `venv\Scripts\python.exe manage.py check`: OK.
- Testes focados dos novos casos de FCI: 6 testes OK.
- `venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests`: 414
  testes OK.

### PM-34.3

Status: concluida.

Resumo:

- `api_investimentos` foi migrada para DRF com `@api_view(["GET", "POST"])`.
- `Response` foi usado apenas na borda do endpoint.
- Foi mantida a permissao manual existente via
  `require_api_permission(FINANCIAL_INVESTMENTS_PERMISSION)`.
- O `POST` continua exigindo `caixa.add_investimento` dentro de
  `_api_criar_investimento`.
- CSRF real foi preservado com o wrapper ja existente
  `csrf_protect_drf_view`.
- Foi adicionado um guard local pequeno para preservar o `405` manual
  `{"detail": "Metodo nao permitido."}` sem header `Allow`.
- Foi adicionado um adaptador local para converter o `JsonResponse` interno do
  POST em `Response` sem alterar payload, status ou headers no-store.
- Selectors, serializers manuais, models, services e signals nao foram
  alterados.
- FCF, liquidacao, obrigacoes, dashboard e outros endpoints financeiros nao
  foram alterados.

Comandos e resultados:

- `venv\Scripts\python.exe manage.py check`: OK.
- `venv\Scripts\python.exe manage.py spectacular --validate`: OK.
- Testes focados dos novos casos de FCI: 6 testes OK.
- `venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests`: 414
  testes OK.

OpenAPI:

- `/api/fci/` passou a aparecer no schema para `GET` e `POST`.
- O schema permanece propositalmente generico; nenhuma mudanca runtime foi feita
  apenas para melhorar documentacao.

### PM-34.4

Status: concluida.

Resumo:

- Validacao completa executada depois da migracao.
- Nenhuma regressao detectada em FCI, ledger, obrigacoes, baixas canonicas ou
  suite geral.
- Nenhum contrato runtime foi alterado fora do escopo da PM.

Comandos e resultados:

- `venv\Scripts\python.exe manage.py check`: OK.
- `venv\Scripts\python.exe manage.py spectacular --validate`: OK.
- `venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests`: 414
  testes OK.
- `venv\Scripts\python.exe manage.py test`: 789 testes OK.

Warnings/logs observados:

- Warnings de CSRF esperados em testes que validam bloqueio sem token.
- Logs esperados de Axes em testes de login invalido.
- Erro simulado de backup manual em teste existente; a suite terminou OK.

### PM-34.5

Status: concluida.

Resumo:

- Documento atualizado com o registro final da PM-34.
- PM-34 pronta para commit manual local.

Arquivos alterados:

- `caixa/tests.py`.
- `caixa/views_investimentos.py`.
- `docs/PLANO_PM34_MIGRACAO_FCI_DRF.md`.

Confirmacoes finais:

- Frontend nao foi alterado.
- Settings, CORS, CSRF global e autenticacao global nao foram alterados.
- FCF, liquidacao, obrigacoes, dashboard e outros endpoints financeiros nao
  foram alterados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- Signals financeiros existentes foram preservados.
- `405` manual sem header `Allow` foi preservado.
- `415` para `Content-Type` invalido foi preservado.
- JSON invalido/body nao-dict como `400` foi preservado.
- Filtros, aliases, defaults, validacoes e shapes de GET/POST foram
  preservados pelos testes.
