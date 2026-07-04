# Plano PM-27 - Migracao incremental de `GET /api/modelagem-financeira-canonica/` e `GET /api/canonical-financial-model/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar conjuntamente `GET /api/modelagem-financeira-canonica/` e
`GET /api/canonical-financial-model/` para Django REST Framework,
preservando integralmente o contrato atual consumido pelo frontend Next.js.

As duas rotas podem ser tratadas na mesma PM porque apontam para a mesma view
`api_modelagem_financeira_canonica`.

DRF deve entrar apenas como casca HTTP da view de leitura da modelagem
financeira canonica, sem alterar regra de negocio, services, selectors,
serializers manuais, permissoes, CORS, headers, status HTTP, JSON, filtros,
aliases, comportamento read-only/dry-run, queries ou contrato do frontend.

## Escopo

- Congelar o contrato atual das duas rotas em testes antes da migracao.
- Migrar somente a view `api_modelagem_financeira_canonica`.
- Manter as duas rotas existentes apontando para a mesma view.
- Usar `@api_view(["GET"])`.
- Usar `Response` somente na borda do endpoint.
- Preservar permissao manual `caixa.view_lancamentofinanceiro`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar Content-Type, Cache-Control/no-store, status HTTP e shape atual das
  respostas JSON.
- Preservar filtros `limit` e `issueLimit`.
- Preservar limites de issues:
  - padrao `20`;
  - minimo `1`;
  - maximo `200`.
- Preservar comportamento read-only/dry-run.
- Reaproveitar services, selectors e serializers manuais atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Baixas financeiras canonicas.
- Obrigacoes financeiras.
- Dashboard financeiro.
- Mes financeiro.
- Lancamentos financeiros.
- Custos por evento.
- Outros endpoints financeiros.
- Mutations financeiras.
- Comandos de sincronizacao.
- Comandos de verificacao de paridade.
- Frontend.
- Settings.
- CORS.
- CSRF global.
- Autenticacao global.
- Serializers DRF.
- ViewSets.
- ModelViewSets.
- Refatoracao de regra de negocio.
- Alteracao de services.
- Alteracao de selectors.
- Alteracao de serializers manuais.
- Alteracao de models.
- Alteracao de signals.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, somente a view `api_modelagem_financeira_canonica` deve ser migrada,
preservando as duas URLs atuais.

Endpoints financeiros sensiveis devem continuar respeitando a ordem definida:
GETs financeiros antes de mutations financeiras, sempre com paridade congelada
antes da migracao.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissao, CORS, filtros, aliases,
efeitos de dominio, queries ou comportamento runtime apenas para melhorar a
documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-27.1

Arquivo atual:

- `caixa/views_modelagem_canonica.py`

View atual:

- `api_modelagem_financeira_canonica`

Rotas atuais:

- `path("api/modelagem-financeira-canonica/", api_modelagem_financeira_canonica, name="api_modelagem_financeira_canonica")`
- `path("api/canonical-financial-model/", api_modelagem_financeira_canonica, name="api_canonical_financial_model")`

Nomes das rotas:

- `caixa:api_modelagem_financeira_canonica`.
- `caixa:api_canonical_financial_model`.

As duas rotas apontam para a mesma view.

Decoradores atuais:

- `@require_GET`
- `@require_api_permission(FINANCIAL_LEDGER_PERMISSION)`

Metodo aceito:

- `GET`

Metodos nao permitidos:

- `POST`, `PUT`, `PATCH`, `DELETE` e outros retornam `405`.
- Header `Allow` observado: `GET`.
- Body observado: vazio.
- `Content-Type` observado: `text/html; charset=utf-8`.
- `Cache-Control` observado: ausente.
- A resposta de `405` Django padrao deve ser preservada.
- Como `@require_GET` esta por fora do decorator de permissao, o `405` ocorre
  antes de autenticacao/permissao.

Permissao atual:

- `FINANCIAL_LEDGER_PERMISSION`, que resolve para
  `caixa.view_lancamentofinanceiro`.

Nao usar `DjangoModelPermissions`, `IsAuthenticated` global ou permissao DRF
generica se isso mudar contrato.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`.

Comportamento para usuario autenticado sem `caixa.view_lancamentofinanceiro`:

```json
{"detail": "Permission denied."}
```

com status `403`.

Comportamento para usuario autenticado com `caixa.view_lancamentofinanceiro`:

- Status `200`.
- Resposta JSON com top-level `data`.
- Header `Content-Type` JSON.
- Header `Cache-Control` com `no-store`.

Filtros aceitos:

- `limit`.
- `issueLimit`.

Regras atuais de limite:

- `limit` tem precedencia sobre `issueLimit` quando ambos sao enviados.
- Padrao: `20`.
- Minimo: `1`.
- Maximo: `200`.
- Valores invalidos usam o padrao.

Diferencas entre rota PT-BR e rota EN:

- Nao ha diferenca funcional esperada.
- As duas rotas usam a mesma view, mesmas permissoes, mesmos filtros e mesmo
  shape.
- A diferenca atual e apenas URL/nome da rota.

Payload de sucesso:

```json
{
  "data": {
    "status": {},
    "synchronizationPreview": {},
    "syncPreview": {},
    "parity": {},
    "canonicalTotals": {},
    "nomenclature": {},
    "migrationPolicy": {},
    "meta": {}
  }
}
```

Shape de `data.status`:

- `readyForCanonicalReads`.
- `hasCanonicalParity`.
- `hasExpectedRecords`.
- `hasCanonicalRecords`.
- `hasMissingCanonicalRecords`.
- `hasDivergentCanonicalRecords`.
- `hasExtraCanonicalRecords`.
- `recommendedNextAction`.
- `sourceOfTruth`.
- `totals`.
- `dryRun`.

Shape de `data.status.totals`:

- `expected`.
- `existing`.
- `missing`.
- `divergent`.
- `extra`.

Shape de `data.synchronizationPreview` e `data.syncPreview`:

- `aplicar`.
- `obrigacoes`.
- `baixas`.
- `alocacoes`.

`synchronizationPreview` e `syncPreview` devem continuar iguais.

Shape de `obrigacoes` e `baixas` no preview:

- `criadas`.
- `atualizadas`.

Shape de `alocacoes` no preview:

- `criadas`.
- `atualizadas`.
- `semObrigacao`.

Shape de `data.parity`:

- `consistent`.
- `limit`.
- `obrigacoes`.
- `baixas`.
- `alocacoes`.
- `issues`.

Shape de `obrigacoes` e `baixas` em `parity`:

- `expected`.
- `existing`.
- `missing`.
- `divergent`.
- `extra`.

Shape de `alocacoes` em `parity`:

- `expected`.
- `existing`.
- `missing`.
- `divergent`.
- `extra`.
- `semObrigacao`.
- `semBaixa`.

Shape de itens em `parity.issues[]`, quando existirem:

- `tipo`.
- `chave`.
- `mensagem`.
- Campos adicionais podem existir conforme o tipo de issue, como `diffs`.

Shape de `data.canonicalTotals`:

- `obligations`.
- `settlements`.
- `allocations`.

Shape de `canonicalTotals.obligations`:

- `count`.
- `plannedAmount`.
- `realizedAmount`.
- `pendingAmount`.
- `overRealizedAmount`.

Shape de `canonicalTotals.settlements`:

- `count`.
- `inflowAmount`.
- `outflowAmount`.
- `financialResult`.

Shape de `canonicalTotals.allocations`:

- `count`.
- `allocatedAmount`.
- `interestAmount`.
- `fineAmount`.
- `discountAmount`.

Shape de `data.nomenclature`:

- `version`.
- `canonicalFields`.
- `legacyAliases`.
- `legacyAliasUsage`.
- `deprecatedAliases`.
- `frozenGenericFields`.
- `businessValueAliases`.
- `physicalFieldsPendingMigration`.
- `plannedPhysicalRenames`.
- `aliasRemovalPolicy`.

Shape de `data.migrationPolicy`:

- `legacyWritePathsActive`.
- `canonicalWritePathsActive`.
- `canonicalReadsRecommended`.
- `requiresExplicitApply`.
- `applyCommand`.
- `verifyCommand`.

Shape de `data.meta`:

- `generatedAt`.
- `source`, com valor `"backend"`.
- `readOnly`, com valor `true`.
- `currency`, com valor `"BRL"`.

Comportamento read-only/dry-run:

- A API chama `sincronizar_modelagem_financeira_canonica(aplicar=False)`.
- A API nao deve aplicar sincronizacao canonica.
- `synchronizationPreview.aplicar` deve permanecer `false`.
- A escrita canonica explicita continua restrita ao comando com `--aplicar`.

Dependencias atuais:

- `montar_payload_modelagem_financeira_canonica_api`.
- `sincronizar_modelagem_financeira_canonica`.
- `verificar_paridade_modelagem_financeira_canonica`.
- `serializar_status_canonico`.
- `serializar_totais_canonicos`.
- `montar_metadados_nomenclatura_financeira`.
- `normalizar_inteiro`.
- `ObrigacaoFinanceira`.
- `BaixaFinanceira`.
- `BaixaFinanceiraAlocacao`.

Complexidade de queries:

- O endpoint executa simulacao de sincronizacao canonica em memoria.
- O endpoint executa verificacao de paridade para obrigacoes, baixas e
  alocacoes.
- O endpoint calcula totais canonicos com agregacoes sobre models canonicos.
- A complexidade tende a crescer com volume de receitas, despesas, custos,
  parcelas, investimentos, financiamentos, lancamentos, obrigacoes, baixas e
  alocacoes.
- Query count exato pode ser sensivel ao volume de fixtures; se nao for viavel
  congelar contagem absoluta, deve haver ao menos teste de nao regressao
  grosseira ou cobertura de comportamento read-only.

## Riscos especificos de modelagem financeira canonica

- Endpoint financeiro canonico e operacionalmente sensivel.
- Embora seja `GET`, executa simulacao de sincronizacao e verificacao de
  paridade.
- Mudanca acidental pode confundir estado de migracao canonica, readiness ou
  recomendacao operacional.
- Mudanca em `limit`/`issueLimit` pode esconder ou expor issues de paridade
  diferente do contrato atual.
- Mudanca em `synchronizationPreview`/`syncPreview` pode quebrar consumidores
  que usam aliases de transicao.
- DRF, se usado sem cuidado, muda `405` para payload JSON padrao.
- DRF, se usar permissao global, pode substituir `401`/`403` atuais.
- Uso direto de `Response` pode perder headers `Cache-Control` atuais.
- OpenAPI tende a ficar generico sem schema manual, mas runtime tem prioridade.
- Query count pode piorar caso services/serializers sejam alterados.

## Guardrails

- Nao alterar frontend.
- Nao alterar settings.
- Nao alterar CORS.
- Nao alterar CSRF global.
- Nao alterar autenticacao global.
- Nao alterar models.
- Nao alterar services.
- Nao alterar selectors.
- Nao alterar serializers manuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao migrar outro endpoint na mesma PM.
- Nao alterar comandos de sincronizacao ou paridade.
- Reaproveitar `montar_payload_modelagem_financeira_canonica_api`.
- Reaproveitar services e serializers manuais atuais.
- Preservar `@require_GET` por fora da view DRF, ou mecanismo equivalente, para
  manter `405` Django padrao.
- Usar permissao local `AllowAny` se necessario para impedir que a permissao
  global do DRF substitua os `401`/`403` manuais.
- Converter para `Response` apenas na borda, preservando status e headers.
- Priorizar paridade runtime sobre OpenAPI.
- Se algum comportamento atual parecer estranho, congelar como esta antes de
  migrar.

## Criterios de aceite

- Testes de paridade criados antes da migracao.
- `GET` anonimo preserva `401` JSON atual nas duas rotas.
- `GET` autenticado sem permissao preserva `403` JSON atual nas duas rotas.
- `GET` autenticado com permissao preserva `200` e shape atual nas duas rotas.
- As duas rotas preservam igualdade funcional.
- Headers JSON/no-store preservados em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` preservam `405` Django atual nas duas rotas.
- Filtros `limit` e `issueLimit` preservados.
- Limites padrao/minimo/maximo preservados.
- `synchronizationPreview == syncPreview` preservado.
- `meta.readOnly == true` preservado.
- GET nao aplica sincronizacao indevida.
- OpenAPI valida sem alterar runtime.
- Suite completa passa.
- Nenhum endpoint fora das duas rotas da view
  `api_modelagem_financeira_canonica` e alterado.

## Criterios de bloqueio

Parar imediatamente se:

- Algum shape de `data` mudar.
- `status`, `parity`, `canonicalTotals`, `nomenclature`, `migrationPolicy` ou
  `meta` mudarem sem previsao.
- `synchronizationPreview` divergir de `syncPreview`.
- `limit` ou `issueLimit` mudarem de comportamento.
- GET passar a aplicar sincronizacao.
- `405` mudar para JSON DRF padrao.
- `401` ou `403` mudarem.
- Header `Cache-Control` mudar em respostas JSON.
- For necessario alterar services.
- For necessario alterar selectors.
- For necessario alterar serializers manuais.
- For necessario criar Serializer DRF.
- For necessario alterar settings, CORS, CSRF global ou autenticacao global.
- For necessario migrar baixas, obrigacoes, dashboard, mes financeiro ou outros
  endpoints financeiros junto.
- Houver divergencia de runtime apenas para melhorar OpenAPI.

## Estrategia de rollback

Rollback deve ser simples e localizado:

- Reverter a alteracao da view `api_modelagem_financeira_canonica`.
- Manter ou remover testes novos conforme decisao da revisao.
- Nao tocar em outros endpoints.
- Nao alterar settings.
- Nao alterar frontend.
- Rodar novamente testes focados e suite completa.

Como a migracao deve ficar limitada a uma view e testes, o rollback esperado e
baixo risco desde que nenhum service/selector/serializer manual seja alterado.

## Fases

### PM-27.1 - Diagnostico read-only

Status: concluida.

Resultado esperado:

- Contrato atual mapeado.
- Arquivos envolvidos identificados.
- Lacunas de paridade identificadas.
- Endpoint classificado como financeiro canonico sensivel.
- Decisao: migrar as duas rotas juntas porque usam a mesma view.
- Nenhuma alteracao de arquivo.

Arquivos lidos na PM-27.1:

- `caixa/views_modelagem_canonica.py`.
- `caixa/urls.py`.
- `caixa/permissions.py`.
- `caixa/serializers_modelagem_canonica.py`.
- `caixa/services_modelagem_canonica.py`.
- `caixa/constants_nomenclatura.py`.
- `caixa/tests.py`.

### PM-27.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes de qualquer migracao para DRF.

Cobrir:

- `GET` anonimo retorna `401` em ambas as URLs.
- `GET` autenticado sem `caixa.view_lancamentofinanceiro` retorna `403` em
  ambas as URLs.
- `GET` com permissao retorna `200` em ambas as URLs.
- Igualdade funcional entre rota PT-BR e rota EN.
- Headers JSON/no-store em `200`, `401` e `403`.
- `POST`, `PUT`, `PATCH` e `DELETE` retornam `405` em ambas as URLs com:
  - `Allow: GET`;
  - body vazio;
  - `Content-Type: text/html; charset=utf-8`;
  - sem `Cache-Control`, se esse for o contrato atual.
- Shape completo de `data`.
- Shape completo de:
  - `status`;
  - `synchronizationPreview`;
  - `syncPreview`;
  - `parity`;
  - `canonicalTotals`;
  - `nomenclature`;
  - `migrationPolicy`;
  - `meta`.
- `synchronizationPreview == syncPreview`.
- Filtros `limit` e `issueLimit` preservados.
- Limites preservados:
  - padrao `20`;
  - minimo `1`;
  - maximo `200`.
- `meta.readOnly == true`.
- GET nao aplica sincronizacao indevida.
- Query count ou teste de nao regressao grosseira, se viavel.

Validacao da fase:

```bash
python manage.py check
python manage.py test <testes focados de modelagem financeira canonica>
```

### PM-27.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Converter somente `api_modelagem_financeira_canonica` para DRF.

Regras:

- Usar `@api_view(["GET"])`.
- Usar `Response` apenas na borda.
- Preservar as duas rotas existentes apontando para a mesma view.
- Preservar `@require_GET` por fora, ou equivalente, para manter `405` Django
  padrao.
- Usar `AllowAny` local se necessario para preservar `401`/`403` manuais.
- Preservar permissao manual `caixa.view_lancamentofinanceiro`.
- Preservar `401` e `403` atuais.
- Preservar `405` Django padrao com `Allow: GET`, body vazio,
  `Content-Type: text/html; charset=utf-8` e sem `Cache-Control`.
- Preservar filtros `limit` e `issueLimit`.
- Preservar shape atual.
- Preservar comportamento read-only/dry-run.
- Reaproveitar services, selectors e serializers manuais atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet.
- Nao criar ModelViewSet.
- Nao mexer em baixas, obrigacoes, dashboard, mes financeiro ou outros
  endpoints financeiros.
- Se o OpenAPI precisar de ajuste, usar apenas `extend_schema` sem alterar
  runtime.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de modelagem financeira canonica>
```

### PM-27.4 - Validacao completa

Status: concluida.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <testes focados de modelagem financeira canonica>
python manage.py test <testes relacionados existentes>
python manage.py test
```

Validar:

- Testes focados de modelagem financeira canonica passam.
- Testes relacionados existentes passam.
- Suite completa passa.
- OpenAPI inclui as duas rotas:
  - `GET /api/modelagem-financeira-canonica/`;
  - `GET /api/canonical-financial-model/`.
- Warnings do spectacular sao reportados.
- Nenhum contrato runtime foi alterado.
- Comportamento read-only/dry-run foi preservado.

### PM-27.5 - Encerramento

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

### PM-27.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Contrato atual mapeado.
- As duas rotas apontam para a mesma view.
- Endpoint permanece Django puro antes da migracao.
- Endpoint classificado como financeiro canonico sensivel.
- Decisao: migrar as duas rotas juntas porque compartilham a mesma view e o
  mesmo contrato.
- Nenhuma alteracao de arquivo feita na PM-27.1.

### PM-27.2 - Congelamento de contrato em testes

Status: concluida.

Arquivos alterados:

- `caixa/tests.py`.

Testes criados/reforcados:

- `ModelagemFinanceiraCanonicaTests.test_api_modelagem_canonica_autenticacao_permissao_e_headers_em_ambas_rotas`.
- `ModelagemFinanceiraCanonicaTests.test_api_modelagem_canonica_metodos_nao_permitidos_preservam_405_em_ambas_rotas`.
- `ModelagemFinanceiraCanonicaTests.test_api_modelagem_canonica_preserva_shape_e_igualdade_funcional_das_rotas`.
- `ModelagemFinanceiraCanonicaTests.test_api_modelagem_canonica_preserva_limit_issue_limit_e_limites`.
- `ModelagemFinanceiraCanonicaTests.test_api_modelagem_canonica_get_preserva_dry_run_sem_aplicar_sincronizacao`.

Contrato congelado:

- `401` anonimo nas duas rotas.
- `403` autenticado sem `caixa.view_lancamentofinanceiro` nas duas rotas.
- `200` autenticado com permissao nas duas rotas.
- Igualdade funcional entre `/api/modelagem-financeira-canonica/` e
  `/api/canonical-financial-model/`.
- Headers JSON/no-store em respostas JSON.
- `405` Django padrao para `POST`, `PUT`, `PATCH` e `DELETE`, com
  `Allow: GET`, body vazio, `Content-Type: text/html; charset=utf-8` e sem
  `Cache-Control`.
- Shape completo de `data`, `status`, `synchronizationPreview`, `syncPreview`,
  `parity`, `canonicalTotals`, `nomenclature`, `migrationPolicy` e `meta`.
- `synchronizationPreview == syncPreview`.
- Filtros `limit` e `issueLimit`, com limite padrao `20`, minimo `1` e maximo
  `200`.
- `meta.readOnly == true`.
- GET preservado como read-only/dry-run, sem aplicar sincronizacao canonica.

Comandos executados:

```bash
python manage.py test <5 testes novos de modelagem financeira canonica>
python manage.py check
python manage.py test <6 testes relacionados existentes>
```

Resultados:

- 5 testes novos: OK.
- `python manage.py check`: OK.
- 6 testes relacionados existentes: OK.

### PM-27.3 - Migracao controlada para DRF

Status: concluida.

Arquivos alterados:

- `caixa/views_modelagem_canonica.py`.

Como a view foi migrada:

- `api_modelagem_financeira_canonica` foi convertida para DRF com
  `@api_view(["GET"])`.
- `Response` foi usado somente na borda do endpoint.
- `@require_GET` permaneceu por fora da view DRF para preservar o `405` Django
  padrao.
- `AllowAny` local foi usado para impedir que a permissao global do DRF
  substitua os `401` e `403` manuais atuais.
- A permissao manual `caixa.view_lancamentofinanceiro` foi preservada por meio
  de checagem explicita.
- O payload continua sendo montado por
  `montar_payload_modelagem_financeira_canonica_api(request.GET)`.
- Services, selectors e serializers manuais nao foram alterados.
- A view `api_baixas_financeiras_canonicas` nao foi alterada.
- Nenhum outro endpoint financeiro foi migrado.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test <9 testes focados/relacionados de modelagem canonica>
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- 9 testes focados/relacionados: OK.
- OpenAPI inclui:
  - `GET /api/modelagem-financeira-canonica/`;
  - `GET /api/canonical-financial-model/`.
- Warnings do `spectacular`: nenhum warning novo observado.

### PM-27.4 - Validacao completa

Status: concluida.

Comandos executados:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.ModelagemFinanceiraCanonicaTests caixa.tests.PermissoesTests
python manage.py test
```

Resultados:

- `python manage.py check`: OK.
- `python manage.py spectacular --validate`: OK.
- Testes relacionados de modelagem canonica e permissoes: 54 testes OK.
- Suite completa: 750 testes OK.
- Warnings do `spectacular`: nenhum warning novo observado.
- Logs esperados de CSRF/AXES apareceram em testes de autenticacao existentes,
  sem falha.
- Nenhum contrato runtime foi alterado fora da view alvo.
- Comportamento read-only/dry-run foi preservado.

### PM-27.5 - Encerramento

Status: concluida.

Arquivos alterados na PM-27:

- `caixa/tests.py`.
- `caixa/views_modelagem_canonica.py`.
- `docs/PLANO_PM27_MIGRACAO_MODELAGEM_FINANCEIRA_CANONICA_DRF.md`.

Confirmacoes finais:

- As duas rotas continuam apontando para a mesma view.
- `GET /api/modelagem-financeira-canonica/` foi migrado para DRF por meio da
  view compartilhada.
- `GET /api/canonical-financial-model/` foi migrado junto por compartilhar a
  mesma view.
- `405` Django padrao foi preservado.
- `401` e `403` JSON atuais foram preservados.
- Filtros `limit` e `issueLimit` foram preservados.
- Limites padrao/minimo/maximo foram preservados.
- `synchronizationPreview == syncPreview` foi preservado.
- GET permanece read-only/dry-run e nao aplica sincronizacao.
- Frontend nao foi alterado.
- Settings, CORS, CSRF global e autenticacao global nao foram alterados.
- Baixas, obrigacoes, dashboard, mes financeiro e outros endpoints financeiros
  nao foram alterados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.

Riscos residuais:

- O schema OpenAPI permanece generico (`type: object`) porque a PM prioriza
  paridade runtime e nao cria Serializer DRF.
- Query count absoluto nao foi congelado em numero fixo; a cobertura garante
  comportamento read-only/dry-run e paridade de contrato.
- O endpoint continua sensivel por executar simulacao e paridade financeira em
  leitura; futuras mudancas devem manter testes de contrato antes de qualquer
  ajuste.

`git status --short` ao final da validacao antes deste registro:

```text
 M caixa/tests.py
 M caixa/views_modelagem_canonica.py
?? docs/PLANO_PM27_MIGRACAO_MODELAGEM_FINANCEIRA_CANONICA_DRF.md
```

Recomendacao:

- PM-27 pronta para revisao e commit local manual.
