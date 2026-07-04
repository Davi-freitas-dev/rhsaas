# Plano PM-30 - Migracao incremental de `GET /api/obrigacoes-financeiras/exportar/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar `GET /api/obrigacoes-financeiras/exportar/` para Django REST
Framework, preservando integralmente o contrato atual consumido pelo frontend
Next.js e pelos downloads CSV.

DRF deve entrar apenas como casca HTTP da view de exportacao de obrigacoes
financeiras, sem alterar regra de negocio, selectors, serializers manuais,
contracts, permissoes, CORS, headers, status HTTP, CSV, filtros, aliases,
encoding, nome de arquivo, colunas, ordenacao, paginacao ignorada ou contrato
do frontend.

## Escopo

- Congelar o contrato atual de exportacao em testes antes da migracao.
- Migrar somente a view `api_exportar_obrigacoes_financeiras`.
- Manter a URL e o nome de rota atuais.
- Usar `@api_view(["GET"])`.
- Usar `Response` apenas para erros JSON, se necessario.
- Preservar `HttpResponse` atual no sucesso CSV se isso for necessario para
  manter headers, encoding, BOM, separador, terminador e download.
- Preservar permissao manual ampla `caixa.view_lancamentofinanceiro`.
- Preservar permissoes parciais por `source`.
- Preservar permissoes de `exportScope=payments`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar headers de sucesso CSV.
- Preservar `exportScope`, `format`, `queueFilter` e filtros atuais.
- Preservar que `limit`, `offset`, `queueLimit` e `queueOffset` sao ignorados
  na exportacao.
- Reaproveitar selectors, serializers manuais, contracts e helpers atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Liquidacao de obrigacoes.
- Listagem de obrigacoes.
- Dashboard financeiro.
- Baixas financeiras.
- Modelagem financeira canonica.
- Mes financeiro.
- Lancamentos financeiros.
- Custos por evento.
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
- Alteracao de contracts.
- Alteracao de models.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, somente a view `api_exportar_obrigacoes_financeiras` deve ser
migrada.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
GETs financeiros antes de mutations financeiras, sempre com paridade congelada
antes da migracao.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar CSV, JSON de erro, status HTTP, headers, permissao, CORS, filtros,
aliases, encoding, nome do arquivo, colunas, separador, terminador, ordenacao,
paginacao ignorada ou comportamento runtime apenas para melhorar a
documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-30.1

Arquivo atual:

- `caixa/views_obrigacoes.py`.

View atual:

- `api_exportar_obrigacoes_financeiras`.

Rota atual:

- `path("api/obrigacoes-financeiras/exportar/", api_exportar_obrigacoes_financeiras, name="api_exportar_obrigacoes_financeiras")`.

Nome da rota:

- `caixa:api_exportar_obrigacoes_financeiras`.

Decoradores atuais:

- `@require_GET`.

Metodo aceito:

- `GET`.

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` observado: `GET`.
- Body observado: vazio.
- `Content-Type` observado: `text/html; charset=utf-8`.
- `Cache-Control` observado: ausente.
- A resposta de `405` Django padrao deve ser preservada.
- Como `@require_GET` esta na view atual, o `405` ocorre antes de
  autenticacao/permissao.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado sem permissao aplicavel:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Comportamento para usuario autenticado com permissao aplicavel:

- Status `200`.
- Resposta CSV.
- `Content-Type: text/csv; charset=utf-8`.
- `Content-Disposition: attachment; filename="<nome>.csv"`.
- `Cache-Control: no-store`.

Permissao ampla:

- `caixa.view_lancamentofinanceiro`.

Permissoes parciais por `source`:

- Reaproveita `_params_obrigacoes_autorizados_por_usuario`.
- Preserva o mesmo mapa de permissoes por origem da listagem de obrigacoes.

Escopo especial de pagamentos:

- `exportScope=payments` aplica:
  - `permissionScope=payments`;
  - `obligationType=pagar`;
  - permissoes de baixa/pagamento nativo;
  - filtros da fila de pagamentos.

Escopos aceitos:

- `obligations`.
- `revenues`.
- `expenses`.
- `payments`.

Default de `exportScope`:

- `obligations`.

Formato aceito:

- `format=csv`, ou ausencia de `format`.

Formato invalido:

- Qualquer valor diferente de `csv` retorna `400` com `{"errors": ...}`.

Filtros canonicos reaproveitados de obrigacoes:

- `period`.
- `quickPeriod`.
- `startDate`.
- `endDate`.
- `contractCode`.
- `eventId`.
- `clientId`.
- `source`.
- `sources`.
- `cashFlowGroup`.
- `nature`.
- `search`.
- `status`.
- `settlementStatus`.
- `dataSource`.
- `obligationType`.
- `realizedAmountBasis`.
- `reconciliationStatus`.
- `reconciliationDiagnosis`.
- `realizedAbovePlanned`.
- `overdueScope`.

Filtros especificos da exportacao:

- `exportScope`.
- `format`.
- `queueFilter`, usado em `payments`.

Valores de `queueFilter` observados:

- `all`, por default.
- `overdue`.
- `next7`.
- `blocked`.

Parametros de paginacao ignorados na exportacao:

- `limit`.
- `offset`.
- `queueLimit`.
- `queueOffset`.

Esses parametros sao removidos antes da montagem da exportacao.

Regras de escopo:

- `exportScope=revenues` forca:
  - `obligationType=receber`;
  - `source=receita_operacional`.
- `exportScope=expenses` forca:
  - `obligationType=pagar`;
  - `cashFlowGroup=fco`.
- `exportScope=expenses` aceita apenas as fontes:
  - `despesa_operacional`;
  - `custo_servico`;
  - `custo_extra`;
  - `custo_fixo`.
- `exportScope=expenses` com `source` invalido retorna `400` com
  `{"errors": ...}`.
- `exportScope=expenses` com `sources` invalidos retorna `400` com
  `{"errors": ...}`.
- `exportScope=payments` forca:
  - `permissionScope=payments`;
  - `obligationType=pagar`.

Formato CSV:

- Encoding HTTP: `text/csv; charset=utf-8`.
- Conteudo inicia com BOM UTF-8 `\ufeff`.
- Separador: `;`.
- Terminador de linha: `\r\n`.

Nome do arquivo:

- Padrao:
  - `{exportScope}-{periodo}-{data_atual}.csv`.
- Quando nao ha `period`:
  - `{exportScope}-{startDate ou inicio}-{endDate ou fim}-{data_atual}.csv`.

Colunas de `exportScope=obligations`:

- `obrigacao`.
- `descricao`.
- `tipo`.
- `origem`.
- `detalhe_origem`.
- `fluxo`.
- `vencimento`.
- `contrato`.
- `evento`.
- `cliente`.
- `previsto`.
- `realizado_origem`.
- `pendente_origem`.
- `realizado_ledger`.
- `pendente_ledger`.
- `acima_previsto_origem`.
- `acima_previsto_ledger`.
- `diferenca_realizada`.
- `status`.
- `status_conciliacao`.
- `diagnostico_conciliacao`.
- `base_realizada`.
- `read_model`.
- `filtros_aplicados`.

Colunas de `exportScope=revenues`:

- `item`.
- `descricao`.
- `origem`.
- `detalhe_origem`.
- `evento`.
- `cliente`.
- `contrato`.
- `vencimento`.
- `status`.
- `previsto`.
- `realizado`.
- `pendente`.
- `fluxo`.
- `filtros_aplicados`.

Colunas de `exportScope=expenses`:

- Mesmas colunas de `exportScope=revenues`.

Colunas de `exportScope=payments`:

- `obrigacao`.
- `descricao`.
- `origem`.
- `detalhe_origem`.
- `evento`.
- `cliente`.
- `contrato`.
- `vencimento`.
- `status`.
- `previsto`.
- `realizado_origem`.
- `pendente_origem`.
- `urgencia`.
- `dias_ate_vencimento`.
- `pronta_para_baixa`.
- `motivo_bloqueio`.
- `suporta_forma_pagamento`.
- `suporta_descricao_pagamento`.
- `suporta_ajustes`.
- `suporta_baixa_saldo`.
- `filtros_aplicados`.

Shape de erros JSON:

```json
{"errors": {...}}
```

Erros conhecidos:

- `exportScope` invalido.
- `format` diferente de `csv`.
- `source` invalido para `expenses`.
- `sources` invalidos para `expenses`.

Dependencias atuais:

- `_params_exportacao_obrigacoes_autorizados`.
- `_aplicar_escopo_exportacao_obrigacoes`.
- `_params_obrigacoes_autorizados_por_usuario`.
- `_params_obrigacoes_pagamentos_autorizados`.
- `montar_exportacao_obrigacoes_financeiras_csv`.
- `normalizar_export_scope_obrigacoes`.
- `normalizar_filtros_obrigacoes`.
- `listar_obrigacoes_com_fonte`.
- `linhas_csv_exportacao_obrigacoes`.
- `linhas_csv_exportacao_pagamentos`.
- `listar_payment_queue_candidates`.
- `filtrar_payment_queue_candidates_exportacao`.
- `renderizar_csv_completo`.
- `nome_arquivo_exportacao_obrigacoes`.
- `serializar_contrato_baixa_obrigacoes_usuario`.
- Selectors/serializers/contracts de obrigacoes financeiras.

Testes existentes identificados:

- `FiltrosHtmlTests.test_exportacao_obrigacoes_financeiras_completa_ignora_paginacao`.
- `FiltrosHtmlTests.test_exportacao_obrigacoes_financeiras_respeita_filtros_receitas_e_despesas`.
- `FiltrosHtmlTests.test_exportacao_receitas_e_despesas_completa_ignora_paginacao_e_teto_300`.
- `FiltrosHtmlTests.test_exportacao_obrigacoes_financeiras_pagamentos_respeita_permissoes`.
- `FiltrosHtmlTests.test_exportacao_obrigacoes_financeiras_falha_explicitamente_para_formato_invalido`.

## Riscos especificos da exportacao de obrigacoes

- Endpoint financeiro sensivel e usado para download de dados operacionais.
- Mudanca acidental de headers pode quebrar download no frontend.
- Mudanca de `Content-Disposition` ou nome de arquivo pode quebrar expectativas
  de usuario/automacao.
- Mudanca de encoding, BOM, separador ou terminador pode quebrar abertura em
  planilhas.
- DRF, se usado sem cuidado, pode transformar sucesso CSV em JSON.
- DRF, se usado sem cuidado, pode transformar `405` Django vazio em JSON padrao.
- DRF, se usar permissao global, pode substituir `401`/`403` atuais.
- A exportacao ignora paginacao de proposito; paginar a exportacao mudaria o
  contrato.
- `exportScope=payments` depende de permissoes e regras da fila de pagamentos.
- OpenAPI tende a representar CSV de forma simplificada, mas runtime tem
  prioridade.

## Guardrails

- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao alterar models.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao alterar contracts.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Nao alterar liquidacao.
- Nao alterar listagem de obrigacoes.
- Nao alterar dashboard financeiro.
- Nao alterar baixas financeiras.
- Nao alterar outros endpoints financeiros.
- Reaproveitar `montar_exportacao_obrigacoes_financeiras_csv`.
- Reaproveitar `_params_exportacao_obrigacoes_autorizados`.
- Reaproveitar helpers atuais de permissao.
- Preservar `@require_GET` por fora da view DRF, ou mecanismo equivalente, para
  manter `405` Django padrao.
- Usar permissao local `AllowAny` se necessario para impedir que a permissao
  global do DRF substitua os `401`/`403` manuais.
- Preservar `HttpResponse` no sucesso CSV se isso for a forma mais segura de
  manter contrato.
- Priorizar paridade runtime sobre OpenAPI.
- Se algum comportamento atual parecer estranho, congelar como esta antes de
  migrar.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `GET` anonimo preserva `401` JSON/no-store.
- `GET` autenticado sem permissao preserva `403` JSON/no-store.
- `GET` autenticado com permissao preserva `200` CSV.
- `POST`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual.
- Headers de sucesso CSV preservados.
- `Content-Disposition` e nome do arquivo preservados.
- Encoding UTF-8 com BOM preservado.
- Separador `;` preservado.
- Terminador `\r\n` preservado.
- Colunas exatas de todos os `exportScope` preservadas.
- Erros de validacao retornam `400` com `{"errors": ...}`.
- `queueFilter` em `payments` preservado.
- `limit`, `offset`, `queueLimit` e `queueOffset` continuam ignorados.
- Permissoes parciais por `source` preservadas.
- Permissoes de `payments` preservadas.
- Filtros reaproveitados de obrigacoes preservados.
- Sucesso CSV nao vira JSON.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora de `api_exportar_obrigacoes_financeiras` e alterado.

## Criterios de bloqueio

Parar imediatamente se:

- Sucesso CSV virar JSON.
- `Content-Type` de sucesso mudar.
- `Content-Disposition` mudar.
- Nome do arquivo mudar.
- BOM UTF-8 sumir.
- Separador ou terminador mudar.
- Alguma coluna mudar.
- Ordem das colunas mudar.
- `405` mudar para JSON DRF padrao.
- `401` ou `403` mudarem.
- Header `Cache-Control` mudar em respostas JSON ou CSV.
- `limit`, `offset`, `queueLimit` ou `queueOffset` passarem a limitar a
  exportacao.
- `exportScope`, `format` ou `queueFilter` mudarem.
- Permissao ampla ou parcial por `source` mudar.
- Permissoes de `payments` mudarem.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario alterar contracts.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar liquidacao, listagem de obrigacoes, dashboard, baixas
  ou outros endpoints financeiros junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_exportar_obrigacoes_financeiras`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em liquidacao, listagem de obrigacoes, dashboard, baixas ou outros
  endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum selector, serializer manual ou contract seja
alterado.

## Fases

### PM-30.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como exportacao financeira sensivel.
- Decisao: migrar sozinho.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-30.1:

- `caixa/urls.py`.
- `caixa/views_obrigacoes.py`.
- `caixa/serializers_obrigacoes.py`.
- `caixa/permissions.py`.
- `caixa/tests.py`.

### PM-30.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `GET` anonimo retorna `401` com JSON/no-store.
- `GET` autenticado sem permissao retorna `403` com JSON/no-store.
- `GET` com permissao retorna CSV.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` com:
  - `Allow: GET`;
  - body vazio;
  - `Content-Type: text/html; charset=utf-8`;
  - sem `Cache-Control`.
- Headers de sucesso CSV:
  - `Content-Type: text/csv; charset=utf-8`;
  - `Content-Disposition: attachment; filename="<nome>.csv"`;
  - `Cache-Control` com `no-store`.
- Nome do arquivo preservado:
  - `{exportScope}-{periodo}-{data_atual}.csv`;
  - fallback com `{startDate ou inicio}-{endDate ou fim}` quando nao houver
    `period`.
- Encoding UTF-8 com BOM `\ufeff`.
- Separador `;`.
- Terminador `\r\n`.
- Colunas exatas para `exportScope=obligations`.
- Colunas exatas para `exportScope=revenues`.
- Colunas exatas para `exportScope=expenses`.
- Colunas exatas para `exportScope=payments`.
- Erro `exportScope` invalido retorna `400` com `{"errors": ...}`.
- Erro `format` diferente de `csv` retorna `400`.
- Erro `source`/`sources` invalidos para `expenses` retorna `400`.
- `queueFilter` em `payments` preservado.
- `limit`, `offset`, `queueLimit` e `queueOffset` continuam ignorados.
- Permissoes parciais por `source` preservadas.
- Permissoes de `payments` preservadas.
- Filtros reaproveitados de obrigacoes preservados.
- CSV nao e transformado em JSON.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de exportacao de obrigacoes>
```

### PM-30.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_exportar_obrigacoes_financeiras` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas para erros JSON, se necessario.
- Preservar `HttpResponse` atual para sucesso CSV se isso for necessario para
  manter headers/encoding.
- Preservar `@require_GET` por fora, ou equivalente, para manter `405` Django
  padrao.
- Usar `AllowAny` local se necessario para preservar `401`/`403` manuais.
- Preservar permissao manual ampla e permissoes parciais por `source`.
- Preservar permissoes de `payments`.
- Preservar `exportScope`, `format`, `queueFilter` e filtros atuais.
- Preservar CSV, BOM, separador, terminador, headers e nome do arquivo.
- Preservar que paginacao e ignorada.
- Reaproveitar selectors, serializers manuais, contracts e helpers atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em liquidacao, listagem de obrigacoes, dashboard, baixas ou outros
  endpoints financeiros.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de exportacao de obrigacoes>
```

### PM-30.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de exportacao de obrigacoes>
python manage.py test <testes relacionados existentes>
python manage.py test
```

Validar:

- Testes focados de exportacao de obrigacoes passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui `GET /api/obrigacoes-financeiras/exportar/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.

### PM-30.5 - Encerramento

Status: concluida.

Atualizar este documento com:

- Arquivos alterados.
- Testes criados.
- Como a view foi migrada.
- Comandos executados.
- Resultados dos testes.
- Resultado do `spectacular`.
- Warnings encontrados.
- Riscos residuais.
- `git status --short`.
- Confirmacao se esta pronto para commit manual.

## Registro de execucao

### PM-30.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- Endpoint permanece Django puro antes da migracao.
- Endpoint classificado como exportacao financeira sensivel.
- Decisao: migrar sozinho, sem agrupar com liquidacao, listagem de obrigacoes,
  dashboard, baixas ou outros endpoints financeiros.
- Nenhuma alteracao de arquivo feita na PM-30.1.

### PM-30.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados/reforcados:

- `FiltrosHtmlTests.test_exportacao_obrigacoes_autenticacao_permissao_405_e_headers_csv`.
- `FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_nome_arquivo_periodo_e_colunas_por_escopo`.
- `FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_colunas_payments_queue_filter_e_paginacao_ignorada`.
- `FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_erros_json_de_validacao`.

Contrato congelado:

- `401` anonimo JSON/no-store.
- `403` sem permissao JSON/no-store.
- Sucesso CSV com `Content-Type`, `Content-Disposition`, nome de arquivo, BOM,
  separador `;`, terminador `\r\n` e `Cache-Control: no-store`.
- `405` Django padrao para metodos nao permitidos.
- Colunas por `exportScope`.
- `format` invalido como `400 {"errors": ...}`.
- `source`/`sources` invalidos em `expenses`.
- `queueFilter` em `payments`.
- Paginacao ignorada na exportacao.
- Permissoes parciais por `source` e permissoes de `payments`.

Comandos executados:

```bash
python manage.py test caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_autenticacao_permissao_405_e_headers_csv caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_nome_arquivo_periodo_e_colunas_por_escopo caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_colunas_payments_queue_filter_e_paginacao_ignorada caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_erros_json_de_validacao
python manage.py check
```

Resultado:

- 4 testes focados OK.
- `check` OK.

### PM-30.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_obrigacoes.py`.

Como a view foi migrada:

- Somente `api_exportar_obrigacoes_financeiras` foi convertida para DRF.
- Foi usado `@api_view(["GET"])`.
- Foi usado `AllowAny` local para preservar `401`/`403` manuais.
- Erros JSON retornam `Response` apenas na borda.
- Sucesso CSV continua retornando `HttpResponse`, preservando headers,
  encoding, BOM, separador, terminador e download.
- `@require_GET` foi preservado por fora, mantendo `405` Django padrao com
  `Allow: GET`, body vazio, `Content-Type: text/html; charset=utf-8` e sem
  `Cache-Control`.
- Selectors, serializers manuais, contracts e helpers atuais foram
  reaproveitados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.

Ajuste tecnico local:

- Foi criada a classe local `_ExportacaoObrigacoesContentNegotiation` somente
  para essa rota.
- Motivo: o DRF usa `?format=` como override de negociacao de conteudo. Esse
  endpoint ja usa `format` como parametro de contrato da exportacao.
- Sem esse ajuste, `format=xlsx` era interceptado pelo DRF antes da view e
  retornava `404`, quebrando o contrato antigo de `400 {"errors": ...}`.
- A desativacao do override foi aplicada apenas nessa view, sem mudar
  `REST_FRAMEWORK` global.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_autenticacao_permissao_405_e_headers_csv caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_nome_arquivo_periodo_e_colunas_por_escopo caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_colunas_payments_queue_filter_e_paginacao_ignorada caixa.tests.FiltrosHtmlTests.test_exportacao_obrigacoes_preserva_erros_json_de_validacao
```

Resultado:

- `check` OK.
- `spectacular --validate` OK.
- 4 testes focados OK.
- OpenAPI passou a incluir `GET /api/obrigacoes-financeiras/exportar/`.
- Nenhum warning do spectacular foi observado.

### PM-30.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Resultado:

- `check` OK.
- `spectacular --validate` OK.
- `FiltrosHtmlTests`: 396 testes OK.
- Suite completa: 765 testes OK.
- Warnings observados durante a suite: apenas logs esperados de testes de CSRF
  e Axes em autenticacao.
- Nenhum warning do spectacular foi observado.
- Nenhum contrato runtime alterado fora da view exportadora.

### PM-30.5 - Encerramento

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.
- `caixa/views_obrigacoes.py`.
- `docs/PLANO_PM30_MIGRACAO_EXPORTACAO_OBRIGACOES_DRF.md`.

Confirmacoes:

- Frontend nao foi alterado.
- Settings nao foram alterados.
- CORS, CSRF global e autenticacao global nao foram alterados.
- Liquidacao nao foi alterada.
- Listagem de obrigacoes nao foi alterada.
- Dashboard financeiro, baixas financeiras e demais endpoints financeiros nao
  foram alterados.
- Sucesso CSV nao virou JSON.
- `Content-Disposition`, BOM, separador, terminador, colunas e nome de arquivo
  foram preservados pelos testes.
- Paginacao continua ignorada na exportacao.
- Permissoes ampla, parciais por `source` e de `payments` foram preservadas.

Riscos residuais:

- O schema OpenAPI ainda representa a resposta CSV de forma simplificada, como
  binario. Isso e aceitavel nesta PM porque a paridade runtime tem prioridade.
- A classe local de content negotiation existe somente para evitar conflito
  entre o parametro de negocio `format` e o override de formato do DRF.

Decisao final:

- PM-30 concluida.
- Pronta para commit local manual.
