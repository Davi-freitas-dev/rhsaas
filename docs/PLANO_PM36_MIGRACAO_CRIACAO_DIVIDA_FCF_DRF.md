# Plano PM-36 - Migracao incremental de `POST /api/fcf/debts/` para DRF

Atualizado em: 2026-06-17

## Objetivo

Migrar de forma incremental e controlada o endpoint `POST /api/fcf/debts/`
para Django REST Framework, preservando integralmente o contrato atual
consumido pelo frontend Next.js.

DRF deve entrar apenas como casca HTTP da view de criacao de divida FCF, sem
alterar regra de negocio, permissoes, CSRF, aliases, status HTTP, payloads,
transacao, serializers manuais, models, signals, lancamentos financeiros,
obrigacoes canonicas, baixas canonicas ou contrato do frontend.

## Escopo

- Congelar o contrato atual de `POST /api/fcf/debts/` em testes antes da
  migracao.
- Migrar somente a view `api_criar_divida_financeira`.
- Manter a URL atual `/api/fcf/debts/`.
- Manter o nome de rota `caixa:api_criar_divida_financeira`.
- Manter somente o metodo `POST`.
- Usar `@api_view(["POST"])`.
- Usar `Response` apenas na borda.
- Preservar `405` manual atual sem promover para `405` padrao Django/DRF.
- Preservar CSRF real no `POST`.
- Preservar permissao manual `caixa.add_dividafinanceira`.
- Nao exigir `caixa.view_parceladivida`.
- Preservar `Content-Type`, JSON invalido e body nao-dict atuais.
- Preservar aliases, defaults, validacoes e shapes atuais.
- Preservar `transaction.atomic`.
- Reaproveitar helpers, serializers manuais e regras atuais.
- Preservar signals e efeitos financeiros atuais.
- Validar OpenAPI sem alterar runtime para melhorar schema.

## Fora do escopo

- `GET/POST /api/fcf/`.
- `/api/fcf/creditors/`.
- Pagamento/liquidacao de parcelas FCF.
- Obrigacoes financeiras.
- Exportacao de obrigacoes.
- Baixas financeiras canonicas.
- Modelagem financeira canonica.
- Dashboard financeiro.
- Mes financeiro.
- Lancamentos financeiros.
- FCI.
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
- Criacao de divida financeira real na etapa de planejamento.
- Commit, push, merge ou deploy automatico.

## Politica geral da migracao incremental

Regra pratica obrigatoria:

- 1 PM = 1 endpoint; ou
- 1 PM = par pequeno e coeso de rotas quando compartilham a mesma view e o
  mesmo contrato.

Nesta PM, migrar somente `POST /api/fcf/debts/`.

Como o endpoint cria `DividaFinanceira`, `ParcelaDivida` e aciona efeitos
financeiros por signals, a PM deve manter a regra de seguranca ja adotada:

- paridade runtime antes de qualquer migracao;
- migracao minima;
- validacao completa depois da migracao;
- nenhum ajuste de schema OpenAPI pode justificar mudanca de runtime.

## Regra especial de OpenAPI

OpenAPI deve refletir o contrato existente.

Nao alterar JSON, status HTTP, headers, permissoes, CSRF, aliases, validacoes,
defaults, transacao, signals, efeitos financeiros ou comportamento runtime
apenas para melhorar a documentacao OpenAPI.

Se houver conflito entre paridade runtime e schema OpenAPI, a paridade runtime
tem prioridade.

Melhorias de schema devem ser feitas somente com anotacoes seguras, como
`extend_schema`, desde que nao alterem runtime.

## Contrato atual identificado na PM-36.1

Arquivos atuais:

- `caixa/urls.py`.
- `caixa/views_financiamentos.py`.
- `caixa/permissions.py`.
- `caixa/models_dividas.py`.
- `caixa/models_fcf.py`.
- `caixa/serializers_financiamentos.py`.
- `caixa/serializers_dimensoes_operacionais.py`.
- `caixa/services_dimensoes_operacionais.py`.
- `caixa/services_dividas_fcf.py`.
- `caixa/services_lancamentos.py`.
- `caixa/services_modelagem_canonica.py`.
- `caixa/signals.py`.
- `caixa/tests.py`.

View atual:

- `api_criar_divida_financeira`.

Rota atual:

- `path("api/fcf/debts/", api_criar_divida_financeira,
  name="api_criar_divida_financeira")`.

Nome de rota:

- `caixa:api_criar_divida_financeira`.

Implementacao atual:

- Django puro.
- Usa `api_no_store_json_response`.
- Ainda nao esta migrado para DRF.
- Usa `transaction.atomic` durante criacao da divida e geracao das parcelas.

Decorador atual:

- `@require_api_permission(ADD_FINANCIAL_DEBT_PERMISSION)`.

Permissao atual:

- `ADD_FINANCIAL_DEBT_PERMISSION = caixa.add_dividafinanceira`.
- O endpoint nao exige `caixa.view_parceladivida` diretamente.

Metodo aceito:

- `POST`.

Metodos nao permitidos:

- Metodos diferentes de `POST` retornam `405` manual para usuario autenticado
  com permissao.
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
`no-store`, quando a requisicao chega na view.

Comportamento para usuario autenticado sem `caixa.add_dividafinanceira`:

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
- `creditorId` / `credor_id` / `credorCadastroId` / `credor_cadastro`.
- `type` / `tipo`.
- `contractedDate` / `data_contratacao`.
- `contractedAmount` / `valor_contratado`.
- `monthlyInterestRate` / `taxa_juros_mensal`.
- `installmentsCount` / `quantidade_parcelas`.
- `dueDay` / `dia_vencimento`.
- `eventId` / `evento` / `evento_id`.
- `notes` / `observacao`.

Defaults atuais:

- `monthlyInterestRate = 0.0000`.
- `dueDay = 10`.

Validacoes principais:

- Credor invalido retorna erro em `creditorId`.
- Credor inexistente retorna erro em `creditorId`.
- Evento invalido retorna erro em `eventId`.
- Evento inexistente retorna erro em `eventId`.
- `contractedAmount` invalido retorna erro em `contractedAmount`.
- `monthlyInterestRate` invalido retorna erro em `monthlyInterestRate`.
- `installmentsCount` invalido retorna erro em `installmentsCount`.
- `dueDay` invalido retorna erro em `dueDay`.
- `contractedDate` invalida retorna erro em `contractedDate`.
- Validacoes do model `DividaFinanceira` continuam valendo:
  - credor cadastrado obrigatorio;
  - credor ativo;
  - valor contratado nao negativo;
  - taxa de juros mensal nao negativa;
  - quantidade de parcelas maior ou igual a 1;
  - dia de vencimento entre 1 e 31;
  - choices validos de tipo e status;
  - dimensao operacional por evento, se aplicavel.
- Validacoes do model `ParcelaDivida` continuam valendo:
  - numero da parcela maior que zero;
  - valores nao negativos;
  - status calculado conforme vencimento/pagamento.

Shape de erro de validacao:

```json
{"errors": {}}
```

Shape do sucesso:

```json
{
  "data": {
    "debt": {},
    "divida": {},
    "installments": [],
    "parcelas": [],
    "message": "Divida financeira cadastrada com sucesso."
  }
}
```

Contrato de aliases no sucesso:

- `data.debt` e `data.divida` publicam o mesmo conteudo serializado.
- `data.installments` e `data.parcelas` publicam a mesma lista serializada.

Shape de `debt` / `divida`:

- `id`.
- `debtId`.
- `descricao`.
- `description`.
- `debtDescription`.
- `credor_id`.
- `creditorId`.
- `credor_nome`.
- `creditorName`.
- `credor`.
- `creditor`.
- `tipo`.
- `type`.
- `tipo_display`.
- `typeLabel`.
- `status`.
- `status_display`.
- `statusLabel`.
- `data_contratacao`.
- `contractedDate`.
- `valor_contratado`.
- `contractedAmount`.
- `quantidade_parcelas`.
- `installmentsCount`.
- Campos de dimensao operacional:
  - `contractCode`;
  - `contractName`;
  - `contractLabel`;
  - `contract`;
  - `contrato_codigo`;
  - `eventId`;
  - `eventName`;
  - `eventNumber`;
  - `eventLabel`;
  - `evento_id`;
  - `evento_nome`;
  - `evento_numero`;
  - `evento_label`;
  - `clientId`;
  - `clientName`;
  - `clientTradeName`;
  - `clientDisplayName`;
  - `cliente_id`;
  - `cliente_nome`;
  - `cliente_nome_fantasia`;
  - `cliente_label`.

Shape de `installments[]` / `parcelas[]`:

- `id`.
- `divida_id`.
- `debtId`.
- `credor_id`.
- `creditorId`.
- `credor_nome`.
- `creditorName`.
- `credor`.
- `creditor`.
- `descricao_divida`.
- `debtDescription`.
- `numero_parcela`.
- `installmentNumber`.
- `rotulo_parcela`.
- `installmentLabel`.
- `data_vencimento_original`.
- `originalDueDate`.
- `data_vencimento_atual`.
- `dueDate`.
- `valor_total_devido`.
- `totalDueAmount`.
- `valor_pago`.
- `paidAmount`.
- `valor_pendente_pagamento`.
- `pendingPaymentAmount`.
- `contas_pendentes`.
- `pendingAccountsAmount`.
- `saldo_em_aberto`.
- `disponivel_para_pagamento`.
- `availableForPayment`.
- `status`.
- `status_display`.
- `statusLabel`.
- `dias_atraso`.
- `overdueDays`.
- `baixado_manualmente`.
- `manuallySettled`.
- `actionHints`.
- Campos de dimensao operacional herdados da divida/evento.

Status codes atuais:

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
- CSRF invalido continua sendo resposta HTML `403` do Django antes da view.

Efeitos colaterais do `POST`:

- Cria `DividaFinanceira`.
- Chama `gerar_parcelas_iniciais`.
- Cria `ParcelaDivida` conforme `installmentsCount`.
- Cada parcela dispara sincronizacao de `ObrigacaoFinanceira` canonica por
  signal de `ParcelaDivida`.
- O `post_save` de `DividaFinanceira` chama `sincronizar_entrada_fcf_divida`.
- Para tipos `emprestimo` e `financiamento`, cria ou atualiza
  `FinanciamentoMovimentacao` automatica vinculada a divida.
- Para tipos sem strategy de entrada FCF, remove/nao cria entrada FCF
  automatica.
- O `post_save` de `FinanciamentoMovimentacao` sincroniza:
  - `LancamentoFinanceiro`;
  - `ObrigacaoFinanceira` canonica da movimentacao;
  - `BaixaFinanceira` canonica quando houver lancamento aplicavel.
- Impacta FCF, caixa, mes financeiro, dashboard, obrigacoes, lancamentos e
  baixas por meio das sincronizacoes existentes.

Transacao:

- A view envolve criacao de divida e geracao inicial de parcelas em
  `transaction.atomic`.
- A migracao nao pode remover ou ampliar indevidamente esse limite
  transacional.

Testes existentes:

- `test_api_fcf_debts_post_cria_divida_parcelada_sem_movimentacao_manual`.
- `test_api_fcf_debts_post_exige_permissao_de_criar_divida`.

Cobertura existente:

- Sucesso `201`.
- Criacao de `DividaFinanceira`.
- Criacao de `ParcelaDivida`.
- Divisao de parcelas e arredondamento.
- Criacao de obrigacoes canonicas das parcelas.
- Criacao de entrada FCF automatica para tipo `financiamento`.
- Ausencia de movimentacao FCF manual sem `divida_financeira`.
- Permissao `add_dividafinanceira`.
- Endpoint aparece no payload de `/api/fcf/` depois da criacao.

Lacunas identificadas:

- CSRF real sem token.
- Anonimo com CSRF valido retornando `401`.
- Content-Type invalido `415`.
- JSON invalido/body nao-dict `400`.
- Metodos nao permitidos e ausencia de `Allow`.
- Headers JSON/no-store em `201`, `400`, `401`, `403`, `405` e `415`.
- Shape completo de `debt`, `divida`, `installments` e `parcelas`.
- Igualdade `debt == divida`.
- Igualdade `installments == parcelas`.
- Aliases de payload.
- Defaults de `monthlyInterestRate` e `dueDay`.
- Credor invalido/inexistente.
- Evento invalido/inexistente.
- Validacoes de valores, quantidade de parcelas, data, dia de vencimento e
  choices de tipo.
- Garantir que `emprestimo` e `financiamento` criam entrada FCF automatica.
- Garantir que outros tipos nao criam entrada FCF automatica, se esse for o
  contrato atual.
- Garantir que nao duplica divida, parcela, lancamento, obrigacao ou baixa.

## Riscos especificos da criacao de divida FCF

- Endpoint cria entidade financeira real.
- Endpoint cria parcelas dentro de transacao.
- Signals disparam obrigacoes canonicas por parcela.
- Signals podem criar entrada FCF automatica e, por consequencia, lancamento,
  obrigacao e baixa canonica.
- Alterar parsing de body via DRF pode mudar `Content-Type`, JSON invalido e
  body nao-dict.
- DRF pode trocar o `405` manual atual por `405` padrao com `Allow`.
- Permissao global DRF pode mudar o contrato de `401`/`403`.
- `SessionAuthentication` pode alterar o ponto de bloqueio de CSRF se a ordem
  de decorators nao for controlada.
- Qualquer mudanca em tipos de divida pode alterar entradas FCF automaticas.
- Qualquer mudanca em transacao pode deixar divida sem parcelas ou parcelas
  sem obrigacoes em falhas parciais.
- Schema OpenAPI pode ficar generico, mas isso nao justifica mudar runtime.

## Guardrails

- Nao criar divida financeira real durante planejamento.
- Em testes de criacao, usar apenas banco de teste e fixtures controladas.
- Nao acessar `request.data` se isso mudar `Content-Type`/JSON invalido.
- Nao trocar o `405` manual por DRF/Django padrao.
- Nao criar serializer DRF.
- Nao criar ViewSet ou ModelViewSet.
- Nao alterar `DividaFinanceira`.
- Nao alterar `ParcelaDivida`.
- Nao alterar `FinanciamentoMovimentacao`.
- Nao alterar signals.
- Nao alterar services de lancamento, obrigacao ou baixa.
- Nao alterar serializers manuais.
- Nao alterar `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard ou
  outros endpoints financeiros.
- Nao alterar frontend, settings, CORS, CSRF global ou auth global.
- Preservar runtime mesmo que o schema OpenAPI fique generico.

## Fases

### PM-36.1 - Diagnostico read-only

Status: concluida.

Objetivo:

- Mapear contrato atual de `POST /api/fcf/debts/`.
- Identificar arquivos, permissao, CSRF, aliases, payloads, headers, transacao,
  efeitos colaterais e lacunas de teste.

Resultado:

- Endpoint permanece Django puro.
- Contrato atual foi mapeado por leitura de codigo e testes existentes.
- Nenhum arquivo foi alterado.
- Nenhuma divida financeira real foi criada.

### PM-36.2 - Congelamento de contrato em testes

Status: concluida.

Objetivo:

- Criar/reforcar testes de paridade antes da migracao.

Cobrir:

- `POST` anonimo com CSRF valido retorna `401`.
- `POST` autenticado sem `caixa.add_dividafinanceira` retorna `403`.
- CSRF real: `POST` sem token valido bloqueia antes da view com `403` HTML.
- `POST` com CSRF valido chega na view.
- `Content-Type` invalido retorna `415`.
- JSON invalido retorna `400`.
- Body JSON nao-dict retorna `400`.
- Validacoes criticas retornam `{"errors": ...}`.
- Credor inexistente/invalido retorna erro de validacao.
- Evento inexistente/invalido retorna erro de validacao.
- Metodos nao permitidos preservam `405` manual:

```json
{"detail": "Metodo nao permitido."}
```

- `405` manual nao deve ganhar header `Allow`, se esse for o contrato atual.
- Headers JSON/no-store em `201`, `400`, `401`, `403`, `405` e `415`.
- Shape completo do sucesso:
  - `data.debt`;
  - `data.divida`;
  - `data.installments`;
  - `data.parcelas`;
  - `data.message`.
- Confirmar `debt == divida`.
- Confirmar `installments == parcelas`.
- Shape completo de `debt/divida`.
- Shape completo de `installments[]/parcelas[]`.
- Aliases de payload preservados:
  - `description` / `descricao`;
  - `creditorId` / `credor_id` / `credorCadastroId` / `credor_cadastro`;
  - `type` / `tipo`;
  - `contractedDate` / `data_contratacao`;
  - `contractedAmount` / `valor_contratado`;
  - `monthlyInterestRate` / `taxa_juros_mensal`;
  - `installmentsCount` / `quantidade_parcelas`;
  - `dueDay` / `dia_vencimento`;
  - `eventId` / `evento` / `evento_id`;
  - `notes` / `observacao`.
- Defaults preservados:
  - `monthlyInterestRate = 0.0000`;
  - `dueDay = 10`.
- Validacoes preservadas:
  - valores invalidos;
  - quantidade de parcelas invalida;
  - data invalida;
  - dia de vencimento invalido;
  - choices de tipo;
  - evento/credor inexistente.
- Efeitos colaterais preservados:
  - cria `DividaFinanceira`;
  - cria `ParcelaDivida`;
  - para `emprestimo` e `financiamento`, cria/atualiza entrada FCF automatica;
  - para outros tipos, nao cria entrada FCF automatica, se esse for o contrato
    atual;
  - sincroniza `LancamentoFinanceiro` quando aplicavel;
  - sincroniza `ObrigacaoFinanceira` canonica por parcelas;
  - sincroniza `BaixaFinanceira` canonica quando aplicavel;
  - nao duplica divida/parcela/lancamento/obrigacao/baixa.

Comandos previstos:

```bash
python manage.py check
python manage.py test caixa.tests.FiltrosHtmlTests
```

Criterio de aceite da fase:

- Testes focados passam.
- Nenhum arquivo runtime alterado.
- Endpoint ainda nao migrado para DRF.

### PM-36.3 - Migracao controlada para DRF

Status: concluida.

Objetivo:

- Migrar somente `api_criar_divida_financeira` para DRF, preservando o
  contrato runtime congelado na PM-36.2.

Regras:

- Converter somente `api_criar_divida_financeira`.
- Usar `@api_view(["POST"])`.
- Usar `Response` apenas na borda.
- Preservar `405` manual sem `Allow`.
- Preservar CSRF real no `POST`.
- Preservar permissao manual `caixa.add_dividafinanceira`.
- Nao exigir `caixa.view_parceladivida`.
- Preservar `Content-Type`, JSON invalido e body nao-dict atuais.
- Preservar aliases, defaults e validacoes.
- Preservar `transaction.atomic` atual.
- Preservar signals/efeitos financeiros atuais.
- Reaproveitar services, selectors, serializers manuais e helpers atuais.
- Nao criar Serializer, ViewSet ou ModelViewSet.
- Nao mexer em `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard ou
  outros endpoints financeiros.

Comandos previstos:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
```

Criterio de aceite da fase:

- Testes focados passam.
- `check` passa.
- `spectacular --validate` passa, mesmo que o schema seja generico.
- OpenAPI inclui `/api/fcf/debts/`.
- Nenhum contrato runtime alterado.

### PM-36.4 - Validacao completa

Status: concluida.

Objetivo:

- Validar que a migracao nao causou regressao em FCF/debts, ledger,
  obrigacoes, baixas canonicas e suite geral.

Executar:

```bash
python manage.py check
python manage.py spectacular --validate
python manage.py test caixa.tests.FiltrosHtmlTests
python manage.py test
```

Validar:

- Testes focados de criacao de divida FCF.
- Testes relacionados existentes de FCF/debts/ledger/obrigacao canonica.
- Suite completa.
- Sem mudanca em `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard ou
  outros endpoints.
- Sem mudanca em settings, CORS, CSRF global ou autenticacao global.

Criterio de aceite da fase:

- Todos os comandos passam.
- Sem mudanca de contrato.
- Sem mudanca de efeitos financeiros.

### PM-36.5 - Encerramento

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
- Confirmacao de que `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard
  e outros endpoints financeiros nao foram alterados.
- Confirmacao de que settings, CORS, CSRF global e auth global nao foram
  alterados.
- Confirmacao de pronto ou nao para commit manual.

## Criterios de aceite da PM

- `POST /api/fcf/debts/` migrado para DRF.
- URL e nome de rota preservados.
- Metodo `POST` preservado.
- `405` manual preservado.
- CSRF real preservado.
- Anonimo recebe `401` atual quando chega na view.
- Usuario sem permissao recebe `403` atual.
- `Content-Type` invalido preservado como `415`.
- JSON invalido/body nao-dict preservado como `400`.
- Shape do sucesso preservado.
- `debt == divida` preservado.
- `installments == parcelas` preservado.
- Shape de `debt/divida` preservado.
- Shape de `installments[]/parcelas[]` preservado.
- Aliases de payload preservados.
- Defaults preservados.
- Validacoes preservadas.
- `transaction.atomic` preservado.
- Signals e efeitos financeiros preservados.
- `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard e outros endpoints
  nao alterados.
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
- Shape do sucesso mudar.
- `debt` divergir de `divida`.
- `installments` divergir de `parcelas`.
- Shape de `debt/divida` mudar.
- Shape de `installments[]/parcelas[]` mudar.
- Algum alias de payload mudar.
- Defaults mudarem.
- Validacoes mudarem.
- `transaction.atomic` for removido ou alterado indevidamente.
- Divida, parcela, lancamento, obrigacao ou baixa canonica duplicar.
- Algum efeito financeiro mudar.
- `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard ou outros endpoints
  precisarem ser alterados.
- For necessario criar Serializer, ViewSet ou ModelViewSet.
- For necessaria decisao arquitetural fora do escopo.

## Estrategia de rollback

Se a migracao causar qualquer divergencia de contrato:

- Reverter apenas as alteracoes da PM-36.3 em `api_criar_divida_financeira`.
- Manter os testes de paridade da PM-36.2, se eles estiverem corretos e
  representarem o contrato atual.
- Remover somente ajustes de teste que dependam da implementacao migrada.
- Confirmar que `POST /api/fcf/debts/` voltou ao comportamento Django puro.
- Rodar testes focados de criacao de divida FCF e `python manage.py check`.

Nao usar rollback destrutivo de git sem aprovacao explicita.

## Registro de execucao

### PM-36.1

Status: concluida.

Resumo:

- Diagnostico read-only realizado.
- Nenhum arquivo alterado.
- Nenhuma divida financeira real criada.
- Contrato atual documentado neste plano.

### PM-36.2

Status: concluida.

Resumo:

- Testes de paridade de `POST /api/fcf/debts/` criados em `caixa/tests.py`.
- O contrato de autenticacao, permissao, CSRF real, `Content-Type`, JSON
  invalido, body nao-dict, validacoes, `405` manual, headers JSON/no-store,
  aliases, defaults, shapes e efeitos financeiros foi congelado antes da
  migracao.
- Foram adicionados helpers locais de teste para:
  - payload de divida FCF;
  - shape completo de `debt/divida`;
  - shape completo de `installments[]/parcelas[]`.
- Foram criados 5 testes novos focados:
  - `test_api_fcf_debts_preserva_auth_permissao_csrf_e_headers`;
  - `test_api_fcf_debts_preserva_erros_de_content_type_json_e_validacao`;
  - `test_api_fcf_debts_preserva_405_manual_sem_allow`;
  - `test_api_fcf_debts_post_preserva_aliases_defaults_shape_e_efeitos`;
  - `test_api_fcf_debts_post_preserva_tipos_sem_entrada_fcf_automatica`.
- Os 2 testes existentes de `/api/fcf/debts/` tambem foram mantidos no bloco
  focado:
  - `test_api_fcf_debts_post_cria_divida_parcelada_sem_movimentacao_manual`;
  - `test_api_fcf_debts_post_exige_permissao_de_criar_divida`.
- Resultado final da fase: 7 testes focados OK.
- `python manage.py check`: OK.
- Nenhum arquivo runtime foi alterado durante a PM-36.2.

### PM-36.3

Status: concluida.

Resumo:

- `api_criar_divida_financeira` foi migrado para DRF com
  `@api_view(["POST"])`.
- `Response` foi usado apenas na borda, convertendo as respostas JSON geradas
  pelos helpers atuais.
- `csrf_protect_drf_view` foi usado para preservar CSRF real antes da entrada
  no DRF.
- A permissao manual `caixa.add_dividafinanceira` continuou sendo aplicada por
  `require_api_permission`.
- O endpoint continua nao exigindo `caixa.view_parceladivida`.
- Foi criado o wrapper local `_preservar_metodo_manual_post_divida_fcf` para
  preservar o `405` manual sem header `Allow` antes do DRF.
- `transaction.atomic` permaneceu envolvendo a criacao da divida e a geracao
  inicial das parcelas.
- Helpers atuais preservados:
  - `_is_json_request`;
  - `_payload_json`;
  - `_financial_debt_from_payload`;
  - `_errors_from_validation_error`;
  - `serializar_divida_financiamento`;
  - `serializar_parcela_financiamento`;
  - `totais_financiamentos`.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard e demais endpoints
  financeiros nao foram alterados.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_post_cria_divida_parcelada_sem_movimentacao_manual caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_post_exige_permissao_de_criar_divida caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_preserva_auth_permissao_csrf_e_headers caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_preserva_erros_de_content_type_json_e_validacao caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_preserva_405_manual_sem_allow caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_post_preserva_aliases_defaults_shape_e_efeitos caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_post_preserva_tipos_sem_entrada_fcf_automatica
```

Resultados:

- `check`: OK.
- `spectacular --validate`: OK.
- Testes focados: 7 testes OK.
- OpenAPI inclui `/api/fcf/debts/`.

### PM-36.4

Status: concluida.

Resumo:

- Validacao completa executada depois da migracao.
- Os comandos foram executados com variaveis locais temporarias de validacao
  quando necessario:
  - `DEBUG=True`;
  - `SECRET_KEY=local-validation-secret`.

Comandos executados:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py spectacular --validate
venv\Scripts\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_financiamentos_retorna_contrato_json_para_frontend caixa.tests.FiltrosHtmlTests.test_api_fcf_debts_post_cria_divida_parcelada_sem_movimentacao_manual caixa.tests.PagamentosEventoTests.test_admin_blinda_entrada_fcf_automatica_da_divida caixa.tests.LancamentoFinanceiroDominioTests.test_divida_emprestimo_gera_entrada_fcf_no_caixa_e_mes_financeiro caixa.tests.LancamentoFinanceiroDominioTests.test_divida_fornecedor_nao_gera_entrada_fcf caixa.tests.LancamentoFinanceiroDominioTests.test_divida_entrada_fcf_atualiza_valor_data_e_remove_ao_mudar_tipo
venv\Scripts\python.exe manage.py test
```

Resultados:

- `check`: OK.
- `spectacular --validate`: OK, sem warnings reportados em stderr.
- Testes relacionados de FCF/debts/ledger/obrigacao canonica: 6 testes OK.
- Suite completa: 800 testes OK.
- Warnings/logs observados na suite:
  - warnings esperados de CSRF em testes com `Client(enforce_csrf_checks=True)`;
  - logs esperados do Axes em testes de login invalido;
  - erro simulado esperado de backup manual em teste de falha mockada.
- Nenhuma mudanca de contrato runtime foi identificada.
- Nenhuma duplicacao de divida, parcela, `LancamentoFinanceiro`,
  `ObrigacaoFinanceira` canonica ou `BaixaFinanceira` canonica foi observada
  nos testes focados.

### PM-36.5

Status: concluida.

Resumo:

- Este documento foi atualizado com o registro final da execucao.

Arquivos alterados:

- `caixa/tests.py`.
- `caixa/views_financiamentos.py`.
- `docs/PLANO_PM36_MIGRACAO_CRIACAO_DIVIDA_FCF_DRF.md`.

Confirmacoes finais:

- `POST /api/fcf/debts/` foi migrado para DRF.
- URL e nome de rota foram preservados.
- Metodo `POST` foi preservado.
- `405` manual sem header `Allow` foi preservado.
- CSRF real foi preservado.
- Permissao manual `caixa.add_dividafinanceira` foi preservada.
- O endpoint continua nao exigindo `caixa.view_parceladivida`.
- `401`, `403`, `400`, `405`, `415` e `201` foram preservados nos testes de
  paridade.
- `Content-Type`, JSON invalido, body nao-dict, aliases, defaults, validacoes,
  shapes e headers foram preservados.
- `debt == divida` foi preservado.
- `installments == parcelas` foi preservado.
- `transaction.atomic` foi preservado.
- Signals e efeitos financeiros atuais foram preservados nos testes focados.
- `/api/fcf/`, credores, liquidacao, obrigacoes, dashboard e outros endpoints
  financeiros nao foram alterados.
- Frontend, settings, CORS, CSRF global e autenticacao global nao foram
  alterados.
- Nenhum Serializer DRF, ViewSet ou ModelViewSet foi criado.
- PM-36 pronta para commit local manual.
