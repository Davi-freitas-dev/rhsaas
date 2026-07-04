# Plano PM-38 - Migracao incremental de `GET/PUT /api/despesas/<id>/` para DRF

Atualizado em: 2026-06-18

## Objetivo

Migrar de forma incremental e controlada o endpoint `GET/PUT
/api/despesas/<id>/` para Django REST Framework, preservando integralmente o
contrato atual consumido pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da view de detalhe/edicao de despesa,
sem alterar regra de negocio, permissoes, CSRF, aliases, status HTTP, payloads,
serializers manuais, models, signals, lancamentos financeiros, obrigacoes
canonicas, baixas canonicas, dashboard, mes financeiro ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `GET/PUT /api/despesas/<id>/` em testes antes da
  migracao.
- Migrar somente a view `api_despesa_detalhe`.
- Manter a URL atual `/api/despesas/<id>/`.
- Manter o nome de rota `caixa:api_despesa_detalhe`.
- Manter somente os metodos `GET` e `PUT`.
- Usar `@api_view(["GET", "PUT"])`.
- Usar `Response` apenas na borda.
- Preservar `405` atual com `Allow: GET, PUT`.
- Preservar CSRF real no `PUT`.
- Preservar permissoes manuais por metodo.
- Preservar `404` padrao Django para registro inexistente.
- Preservar filtro `origem=DespesaOperacional.ORIGEM_MANUAL`.
- Preservar `Content-Type`, JSON invalido e body nao-dict atuais.
- Preservar aliases, campos ignorados, validacoes e shapes atuais.
- Reaproveitar helpers e serializers manuais atuais.
- Preservar signals e efeitos financeiros atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- Listagem/criacao de despesas.
- Receitas.
- Obrigacoes financeiras.
- Baixas financeiras canonicas.
- Lancamentos financeiros.
- Mes financeiro.
- Dashboard financeiro.
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
- Edicao de despesa real na etapa de planejamento.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de metodos quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, migrar somente `GET/PUT /api/despesas/<id>/`.

Como o `PUT` atualiza despesa manual e aciona efeitos financeiros por signals,
a PM deve manter a regra de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, aliases, campos
ignorados, filtro de origem manual, validacoes, signals, efeitos financeiros ou
comportamento runtime apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-38.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_despesas_api.py`.
- `caixa/permissions.py`.
- `caixa/models.py`.
- `caixa/serializers_dimensoes_operacionais.py`.
- `caixa/utils_financeiros.py`.
- `caixa/services_lancamentos.py`.
- `caixa/services_modelagem_canonica.py`.
- `caixa/signals.py`.
- `caixa/tests.py`.

View atual:

- `api_despesa_detalhe`.

Rota atual:

- `path("api/despesas/<int:pk>/", api_despesa_detalhe,
  name="api_despesa_detalhe")`.

Nome de rota:

- `caixa:api_despesa_detalhe`.

Implementacao atual:

- Django puro.
- Usa `api_no_store_json_response`.
- Ainda nao esta migrado para DRF.
- Usa `get_object_or_404(_despesas_queryset(), pk=pk)` para `GET` e `PUT`.
- O queryset aplica `origem=DespesaOperacional.ORIGEM_MANUAL`.
- Nao usa `transaction.atomic` explicitamente na view.

Decorador atual:

- `@require_http_methods(["GET", "PUT"])`.

Permissoes atuais:

- `GET` exige `caixa.view_despesaoperacional`.
- `PUT` exige `caixa.change_despesaoperacional`.
- `PUT` nao deve passar a exigir `caixa.view_despesaoperacional` se o contrato
  atual nao exige essa permissao no metodo de edicao.

Metodos aceitos:

- `GET`.
- `PUT`.

Metodos nao permitidos:

- `POST`, `PATCH`, `DELETE` e outros metodos sao bloqueados pelo Django com
  `405` e header `Allow: GET, PUT`.
- Essa resposta nao deve ser substituida por erro padrao DRF se isso alterar
  body, headers ou `Cache-Control`.

Comportamento para usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

com status `401`, `Content-Type: application/json` e `Cache-Control` com
`no-store`, quando a requisicao chega na view.

Comportamento para usuario autenticado sem permissao:

```json
{"detail": "Permission denied."}
```

com status `403`, `Content-Type: application/json` e `Cache-Control` com
`no-store`.

Registro inexistente:

- `GET` e `PUT`, quando passam por permissao, preservam `404` padrao Django.
- O `404` atual nao e payload JSON manual da API.

Despesa existente, mas nao manual:

- Como `_despesas_queryset()` filtra `origem=DespesaOperacional.ORIGEM_MANUAL`,
  despesas sincronizadas por custo de servico ou custo extra devem continuar
  aparecendo como `404` neste endpoint.

CSRF atual no `PUT`:

- `PUT` usa CSRF real do Django.
- Sem token valido, a requisicao deve ser bloqueada antes da view com `403`
  HTML.
- A migracao nao pode alterar CSRF global.

Content-Type no `PUT`:

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

Payload aceito no `PUT`:

- `plannedAmount` / `valor_previsto`.
- `paid` / `pago`.
- `paidAmount` / `valor_pago`.
- `paymentDate` / `data_pagamento`.
- `notes` / `observacao`.

Campos fora do contrato de atualizacao atual:

- `description`.
- `category`.
- `dueDate`.
- `paymentMethod`.
- `status`.
- `manuallySettled`.
- `settlementReason`.
- `eventId`.
- `clientId`.

Esses campos devem continuar ignorados pelo endpoint de edicao, salvo decisao
futura explicita fora desta PM.

Validacoes atuais:

- Valores monetarios invalidos retornam `400` com `{"errors": ...}`.
- Valores monetarios negativos retornam `400` com `{"errors": ...}`.
- Boolean invalido em `paid` / `pago` retorna `400` com `{"errors": ...}`.
- Data invalida em `paymentDate` / `data_pagamento` retorna `400` com
  `{"errors": ...}`.
- Erros de `ValidationError` do model retornam `400` com `{"errors": ...}`.
- Pode haver erro de caixa insuficiente em `valor_pago`, tambem retornando
  `400` com `{"errors": ...}`.

Erro de integridade atual:

```json
{"errors": {"detail": ["Nao foi possivel atualizar a despesa."]}}
```

com status `400`.

Shape de sucesso do `GET`:

```json
{
  "data": {
    "expense": {},
    "permissions": {
      "canView": true,
      "canUpdate": false,
      "canManageInAdmin": false
    },
    "meta": {
      "source": "backend"
    }
  }
}
```

Shape de sucesso do `PUT`:

```json
{
  "data": {
    "expense": {},
    "message": "Despesa atualizada com sucesso."
  }
}
```

Shape de `expense`:

- `id`.
- `description`.
- `category`.
- `categoryLabel`.
- `plannedAmount`.
- `paidAmount`.
- `pendingPaymentAmount`.
- `dueDate`.
- `paymentDate`.
- `status`.
- `statusLabel`.
- `paymentMethod`.
- `manuallySettled`.
- `settlementReason`.
- `notes`.
- `eventId`.
- `eventLabel`.
- `eventNumber`.
- `clientId`.
- `clientName`.
- `contractCode`.
- `contractLabel`.
- `createdAt`.
- `updatedAt`.

Regras atuais de atualizacao:

- Se `plannedAmount` / `valor_previsto` nao for enviado, preserva o valor atual.
- Se `paid` / `pago` nao for enviado, usa como base o status atual da despesa.
- Se `paid` for verdadeiro:
  - `paidAmount` / `valor_pago` informado e usado quando presente;
  - se o valor pago nao for informado, usa o valor previsto;
  - `paymentDate` / `data_pagamento` informado e usado quando presente;
  - se a data nao for informada, usa a data existente ou a data local atual.
- Se `paid` for falso:
  - zera `valor_pago`;
  - limpa `data_pagamento`;
  - volta status para pendente;
  - limpa forma de pagamento, baixa manual e motivo de baixa.
- `notes` / `observacao` atualiza a observacao; ausente preserva valor atual.

Headers atuais:

- Respostas JSON: `Content-Type: application/json`.
- Respostas JSON: `Cache-Control` com `no-store`.
- `405`: resposta padrao Django com `Allow: GET, PUT`.
- `404` padrao Django e falha CSRF nao sao JSON manual da API.

Efeitos colaterais atuais do `PUT`:

- Atualiza `DespesaOperacional`.
- Recalcula status da despesa.
- Recalcula realizado do evento relacionado.
- Sincroniza `LancamentoFinanceiro` quando a despesa manual possui pagamento.
- Remove o `LancamentoFinanceiro` quando a despesa fica sem pagamento,
  cancelada ou deixa de ser manual.
- Sincroniza `ObrigacaoFinanceira` canonica de despesa manual.
- Sincroniza ou remove `BaixaFinanceira` canonica conforme lancamento
  financeiro relacionado.
- Impacta caixa, dashboard e mes financeiro por meio dos dados financeiros
  sincronizados.

## Riscos especificos de despesa detalhe/edicao

- Alterar permissao do `PUT` e passar a exigir `view_despesaoperacional` junto
  com `change_despesaoperacional`.
- Remover ou esquecer o filtro `origem=DespesaOperacional.ORIGEM_MANUAL`.
- Expor despesas sincronizadas por custo de servico ou custo extra neste
  endpoint.
- Trocar `404` padrao Django por JSON DRF.
- Trocar `405` Django atual por `405` DRF com payload diferente.
- Deixar o parser do DRF substituir o erro atual de JSON invalido.
- Alterar CSRF real do `PUT`.
- Passar a aceitar campos atualmente ignorados.
- Alterar regra de valor pago, data de pagamento ou status.
- Alterar comportamento de caixa insuficiente.
- Duplicar ou remover indevidamente lancamento financeiro.
- Duplicar ou remover indevidamente obrigacao canonica.
- Duplicar ou remover indevidamente baixa canonica.
- Alterar totals de caixa, dashboard ou mes financeiro por efeito indireto.
- Melhorar schema OpenAPI alterando runtime.

## Guardrails

- Nao migrar nenhum outro endpoint.
- Nao mexer em listagem/criacao de despesas.
- Nao mexer em receitas.
- Nao mexer em obrigacoes, dashboard, mes financeiro ou outros endpoints
  financeiros.
- Nao alterar frontend.
- Nao alterar settings, CORS, CSRF global ou auth global.
- Nao criar Serializer DRF.
- Nao criar ViewSet ou ModelViewSet.
- Nao alterar serializers manuais.
- Nao alterar services, selectors, models ou signals.
- Preservar URL, nome de rota, metodos, payloads, status HTTP e headers.
- Preservar filtro de despesa manual.
- Preservar `api_no_store_json_response` como referencia de contrato das
  respostas JSON.
- Priorizar paridade runtime sobre OpenAPI.

## PM-38.1 - Diagnostico read-only

Status: concluida.

Resultado:

- Endpoint mapeado como Django puro.
- Permissoes, aliases, filtro de origem manual, headers, shapes e efeitos
  colaterais identificados.
- Lacunas de testes listadas para PM-38.2.
- Nenhum arquivo alterado.
- Nenhuma despesa real editada.

## PM-38.2 - Congelamento de contrato em testes

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.
- Nao migrar o endpoint nesta fase.
- Nao usar DRF nesse endpoint nesta fase.

Cobertura obrigatoria:

- `GET` anonimo retorna `401`.
- `GET` autenticado sem `caixa.view_despesaoperacional` retorna `403`.
- `GET` com `caixa.view_despesaoperacional` retorna `200`.
- `GET` registro inexistente preserva `404` Django padrao.
- `GET` de despesa existente, mas nao manual, preserva `404` Django padrao.
- `PUT` anonimo com CSRF valido retorna `401`.
- `PUT` autenticado sem `caixa.change_despesaoperacional` retorna `403`.
- Confirmar que `PUT` exige `change_despesaoperacional`, nao apenas
  `view_despesaoperacional`.
- `PUT` registro inexistente preserva `404` Django padrao.
- `PUT` de despesa existente, mas nao manual, preserva `404` Django padrao.
- CSRF real: `PUT` sem token valido bloqueia antes da view com `403` HTML.
- `PUT` com CSRF valido chega na view.
- `Content-Type` invalido retorna `415`.
- JSON invalido retorna `400`.
- Body JSON nao-dict retorna `400`.
- Validacoes criticas retornam `{"errors": ...}`.
- Erro de integridade preserva:

```json
{"errors": {"detail": ["Nao foi possivel atualizar a despesa."]}}
```

- `POST`, `PATCH` e `DELETE` preservam `405` com `Allow: GET, PUT`.
- Headers JSON/no-store em respostas JSON.
- Shape completo do `GET`:
  - `data.expense`.
  - `data.permissions`.
  - `data.meta`.
- Shape completo do `PUT` sucesso:
  - `data.expense`.
  - `data.message`.
- Shape completo de `expense`.
- Aliases `PUT` preservados:
  - `plannedAmount` / `valor_previsto`.
  - `paid` / `pago`.
  - `paidAmount` / `valor_pago`.
  - `paymentDate` / `data_pagamento`.
  - `notes` / `observacao`.
- Confirmar que campos fora do contrato de atualizacao continuam ignorados:
  - `description`.
  - `category`.
  - `dueDate`.
  - `paymentMethod`.
  - `status`.
  - `manuallySettled`.
  - `settlementReason`.
  - `eventId`.
  - `clientId`.
- Efeitos colaterais preservados:
  - atualiza `DespesaOperacional`;
  - recalcula status;
  - recalcula realizado do evento relacionado;
  - sincroniza `LancamentoFinanceiro`;
  - sincroniza `ObrigacaoFinanceira` canonica;
  - sincroniza/remove `BaixaFinanceira` canonica conforme pagamento;
  - nao duplica lancamento, obrigacao ou baixa.

Comandos esperados:

```bash
python manage.py check
python manage.py test caixa.tests.DespesasApiTests
```

## PM-38.3 - Migracao controlada para DRF

Objetivo:

- Converter somente `api_despesa_detalhe`.
- Manter contrato runtime congelado na PM-38.2.

Regras:

- Usar `@api_view(["GET", "PUT"])`.
- Usar `Response` apenas na borda.
- Preservar `@require_http_methods(["GET", "PUT"])`, ou equivalente, para
  manter `405` e `Allow: GET, PUT`.
- Preservar CSRF real no `PUT`.
- Preservar permissoes manuais:
  - `GET` exige `view_despesaoperacional`;
  - `PUT` exige `change_despesaoperacional`.
- Preservar `401` e `403` atuais.
- Preservar `404` Django padrao.
- Preservar filtro `origem=DespesaOperacional.ORIGEM_MANUAL`.
- Preservar `415`, JSON invalido e body nao-dict atuais.
- Preservar aliases, campos ignorados, validacoes e erro de integridade.
- Preservar signals e efeitos financeiros atuais.
- Reaproveitar serializers manuais e helpers atuais.
- Nao criar Serializer DRF.
- Nao criar ViewSet ou ModelViewSet.
- Nao mexer em receitas, listagem de despesas, obrigacoes, dashboard ou outros
  endpoints financeiros.

Validacao da fase:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.DespesasApiTests
```

## PM-38.4 - Validacao completa

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.DespesasApiTests
python manage.py test
```

Validar:

- Testes focados de despesa detalhe.
- Testes relacionados existentes de despesa, lancamentos, obrigacoes canonicas
  e baixas canonicas.
- Suite completa.
- OpenAPI valido.
- Nenhuma regressao de runtime.
- Nenhuma alteracao em frontend, settings, CORS, CSRF global ou auth global.

## PM-38.5 - Encerramento

Atualizar este documento com:

- Arquivos alterados.
- Testes criados ou alterados.
- Comandos executados.
- Resultados dos testes.
- Resultado do `python manage.py check`.
- Resultado do `python manage.py spectacular --validate`.
- Warnings, se houver.
- Confirmacao de que somente `api_despesa_detalhe` foi migrado.
- Confirmacao de que nenhuma despesa real foi editada fora dos testes.
- Confirmacao de que esta pronto, ou nao, para commit manual.

## Criterios de aceite

- Contrato runtime preservado.
- URL e nome de rota preservados.
- `GET` e `PUT` preservados.
- Permissoes por metodo preservadas.
- CSRF real preservado.
- `404` Django padrao preservado.
- `405` e `Allow: GET, PUT` preservados.
- Filtro de despesa manual preservado.
- JSONs, status HTTP e headers preservados.
- Aliases preservados.
- Campos ignorados continuam ignorados.
- Efeitos financeiros preservados.
- Nenhum lancamento, obrigacao ou baixa duplicado.
- Nenhum endpoint fora do escopo migrado.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet criado.
- Testes focados passam.
- Suite completa passa.
- `python manage.py check` passa.
- `python manage.py spectacular --validate` passa.

## Criterios de bloqueio

Parar imediatamente se:

- `PUT` passar a exigir permissao diferente.
- CSRF mudar.
- `404` padrao Django mudar.
- `405` ou `Allow: GET, PUT` mudar.
- Filtro `origem=DespesaOperacional.ORIGEM_MANUAL` mudar.
- Despesa sincronizada passar a aparecer neste endpoint.
- `415` mudar.
- JSON invalido/body nao-dict mudar.
- Algum alias mudar.
- Campo atualmente ignorado passar a alterar despesa.
- Validacoes mudarem.
- Shape de `expense` mudar.
- Status da despesa mudar de forma nao prevista.
- Houver duplicacao de `LancamentoFinanceiro`.
- Houver duplicacao de `ObrigacaoFinanceira` canonica.
- Houver duplicacao de `BaixaFinanceira` canonica.
- Algum total financeiro indireto mudar.
- For necessaria decisao arquitetural.
- For necessario alterar escopo fora desta PM.

## Estrategia de rollback

- Reverter somente as alteracoes da PM-38.
- Manter testes de paridade, se eles apenas congelarem o contrato real atual.
- Se a migracao causar divergencia, voltar `api_despesa_detalhe` para Django
  puro.
- Nao alterar frontend para compensar divergencia.
- Nao alterar settings, CORS, CSRF global ou auth global para contornar falha.
- Nao ajustar regras financeiras para fazer testes passarem.

## Registro de execucao

### PM-38.1

- Status: concluida.
- Tipo: diagnostico read-only.
- Arquivos alterados: nenhum.
- Despesa real editada: nao.

### PM-38.2

- Status: concluida.
- Arquivos alterados:
  - `caixa/tests.py`.
- Testes criados/alterados:
  - Helpers locais em `DespesasApiTests` para CSRF, headers JSON/no-store,
    404 padrao Django, shape de `expense` e despesa nao manual.
  - Cobertura de `GET` anonimo, sem permissao, sucesso, permissoes, 404 e
    despesa existente nao manual retornando 404.
  - Cobertura de `PUT` com CSRF real, anonimo, usuario apenas com
    `view_despesaoperacional`, 404, despesa nao manual, payload invalido,
    aliases, campos ignorados, erro de integridade e efeitos financeiros.
  - Cobertura de `POST`, `PATCH` e `DELETE` preservando `405` com
    `Allow: GET, PUT`.
- Comandos e resultados:
  - `venv\Scripts\python.exe manage.py test caixa.tests.DespesasApiTests`
    com `SECRET_KEY=local-validation-secret` e `DEBUG=True`: 10 testes OK.
  - `venv\Scripts\python.exe manage.py check` com variaveis locais: OK.
- Observacao:
  - A despesa nao manual de teste foi criada como manual e teve `origem`
    ajustada via `update()` no banco de teste para congelar o contrato do
    endpoint sem passar pelo fluxo normal de edicao/sincronizacao.

### PM-38.3

- Status: concluida.
- Arquivos alterados:
  - `caixa/views_despesas_api.py`.
- Migracao realizada:
  - `api_despesa_detalhe` migrada para DRF com `@api_view(["GET", "PUT"])`.
  - `Response` usado apenas na borda, convertendo as respostas JSON manuais.
  - `JsonBodySafeSessionAuthentication` reaproveitado.
  - `AllowAny` local usado para preservar autenticacao/permissao manual.
  - `@require_http_methods(["GET", "PUT"])` preservado para manter `405` e
    `Allow: GET, PUT`.
  - `csrf_protect` e `csrf_exempt = False` aplicados para preservar o `403`
    HTML Django em `PUT` sem token CSRF valido.
  - `page_not_found` usado para preservar `404` padrao Django.
  - Filtro `origem=DespesaOperacional.ORIGEM_MANUAL` preservado por
    reaproveitamento de `_despesas_queryset()`.
  - Helpers, serializer manual, aliases, validacoes e efeitos financeiros
    atuais foram reaproveitados.
- Comandos e resultados:
  - `venv\Scripts\python.exe manage.py check` com variaveis locais: OK.
  - `venv\Scripts\python.exe manage.py spectacular --validate` com variaveis
    locais: OK.
  - `venv\Scripts\python.exe manage.py test caixa.tests.DespesasApiTests` com
    variaveis locais: 10 testes OK.
- OpenAPI:
  - `/api/despesas/{id}/` aparece no schema com `GET` e `PUT`.
  - Sem warnings reportados pelo `spectacular --validate`.

### PM-38.4

- Status: concluida.
- Comandos e resultados:
  - `venv\Scripts\python.exe manage.py check` com variaveis locais: OK.
  - `venv\Scripts\python.exe manage.py spectacular --validate` com variaveis
    locais: OK.
  - `venv\Scripts\python.exe manage.py test caixa.tests.DespesasApiTests caixa.tests.LancamentoFinanceiroDominioTests`
    com variaveis locais: 41 testes OK.
  - `venv\Scripts\python.exe manage.py test` com variaveis locais: 812 testes
    OK.
- Warnings observados:
  - Warnings esperados de CSRF em testes que validam bloqueio antes da view.
  - Log de erro simulado em teste de backup manual existente.
  - Nenhum warning do `spectacular --validate`.

### PM-38.5

- Status: concluida.
- Arquivos alterados:
  - `caixa/tests.py`.
  - `caixa/views_despesas_api.py`.
  - `docs/PLANO_PM38_MIGRACAO_DESPESA_DETALHE_DRF.md`.
- Confirmacoes finais:
  - Somente `api_despesa_detalhe` foi migrado nesta PM.
  - Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
  - Nenhum frontend foi alterado.
  - Settings, CORS, CSRF global e autenticacao global nao foram alterados.
  - Receitas e listagem/criacao de despesas nao foram alteradas.
  - Obrigacoes, dashboard e outros endpoints financeiros nao foram alterados.
  - URL e nome de rota foram preservados.
  - `GET` exige `caixa.view_despesaoperacional`.
  - `PUT` exige `caixa.change_despesaoperacional`.
  - `404` Django padrao, `405` com `Allow: GET, PUT`, CSRF real, filtro de
    despesa manual, aliases, campos ignorados, shapes e efeitos financeiros
    foram preservados pelos testes de paridade.
  - Nenhuma despesa real foi editada fora do banco de testes.
- Pronto para commit manual: sim.
