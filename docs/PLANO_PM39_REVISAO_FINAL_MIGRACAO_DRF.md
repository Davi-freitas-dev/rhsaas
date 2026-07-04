# Plano PM-39 - Revisao final pos-migracao DRF das rotas `/api/*`

Atualizado em: 2026-06-18

## Objetivo

Revisar e validar o fechamento da migracao incremental das rotas `/api/*` para
Django REST Framework, confirmando que nenhuma rota de API permanece em Django
puro no URLConf atual e que a aplicacao esta pronta para commit/deploy manual
apos revisao humana.

Esta PM nao executa migracao funcional, nao cria serializers DRF, nao altera
frontend e nao altera settings, CORS, CSRF global, autenticacao global, models,
migrations ou regra de negocio.

## Resumo da migracao

A migracao incremental para DRF foi concluida endpoint por endpoint, mantendo:

- mesmas URLs;
- mesmos nomes de rota;
- mesmos metodos HTTP;
- mesmos payloads;
- mesmos status HTTP;
- mesmas permissoes manuais;
- sessao Django;
- CSRF real;
- CORS global preservado;
- headers `no-store` nos JSONs existentes;
- `404` Django padrao onde ele ja era contrato;
- `405` Django/manual conforme o contrato de cada endpoint;
- CSV de exportacao preservado;
- efeitos financeiros preservados por testes;
- `Response` usado apenas na borda;
- nenhum Serializer DRF, ViewSet ou ModelViewSet criado nas PMs incrementais.

## Inventario final de rotas `/api/*`

Inventario gerado por introspeccao do URLConf atual com `DEBUG=True` e
`SECRET_KEY=local-validation-secret`.

### Rotas de aplicacao migradas para DRF

- `/api/auth/csrf/` -> `api_auth_csrf`.
- `/api/auth/login/` -> `api_auth_login`.
- `/api/auth/logout/` -> `api_auth_logout`.
- `/api/auth/session/` -> `api_auth_session`.
- `/api/backups/` -> `api_backups`.
- `/api/backups/criar/` -> `api_backup_criar_manual`.
- `/api/baixas-financeiras-canonicas/` -> `api_baixas_financeiras_canonicas`.
- `/api/canonical-financial-model/` -> `api_modelagem_financeira_canonica`.
- `/api/canonical-settlements/` -> `api_baixas_financeiras_canonicas`.
- `/api/clientes/` -> `api_clientes`.
- `/api/clientes/<int:pk>/` -> `api_cliente_detalhe`.
- `/api/custos-fixos/` -> `api_custos_fixos`.
- `/api/custos-fixos/<int:pk>/` -> `api_custo_fixo_detalhe`.
- `/api/custos-por-evento/` -> `api_custos_por_evento`.
- `/api/dashboard/financial-overview/` -> `api_dashboard_financial_overview`.
- `/api/despesas/<int:pk>/` -> `api_despesa_detalhe`.
- `/api/eventos/` -> `api_eventos`.
- `/api/eventos/<int:pk>/` -> `api_evento_detalhe`.
- `/api/eventos/custos-extras/` -> `api_criar_custo_extra_evento`.
- `/api/fcf/` -> `api_financiamentos`.
- `/api/fcf/creditors/` -> `api_credores_financiamentos`.
- `/api/fcf/debts/` -> `api_criar_divida_financeira`.
- `/api/fci/` -> `api_investimentos`.
- `/api/lancamentos-financeiros/` -> `api_lancamentos_financeiros`.
- `/api/mes-financeiro/` -> `api_mes_financeiro`.
- `/api/modelagem-financeira-canonica/` -> `api_modelagem_financeira_canonica`.
- `/api/obrigacoes-financeiras/` -> `api_obrigacoes_financeiras`.
- `/api/obrigacoes-financeiras/exportar/` -> `api_exportar_obrigacoes_financeiras`.
- `/api/obrigacoes-financeiras/liquidar/` -> `api_liquidar_obrigacao_financeira`.
- `/api/orcamentos/` -> `api_orcamentos`.
- `/api/orcamentos/<int:pk>/` -> `api_orcamento_detalhe`.
- `/api/orcamentos/<int:pk>/aprovar/` -> `api_aprovar_orcamento`.
- `/api/payment-obligations/` -> `api_obrigacoes_financeiras`.
- `/api/payment-obligations/settle/` -> `api_liquidar_obrigacao_financeira`.
- `/api/receitas/<int:pk>/` -> `api_receita_detalhe`.

Total de rotas de aplicacao `/api/*` migradas para DRF: 35.

### Rotas de documentacao DRF/drf-spectacular

As rotas abaixo existem somente quando `settings.ENABLE_API_DOCS == True` e
estao protegidas por `staff_member_required` em `config/urls.py`:

- `/api/schema/` -> `SpectacularAPIView`.
- `/api/docs/` -> `SpectacularSwaggerView`.
- `/api/redoc/` -> `SpectacularRedocView`.

Testes existentes confirmaram:

- com `ENABLE_API_DOCS=False`, as rotas nao existem;
- com `ENABLE_API_DOCS=True`, usuario anonimo nao recebe `200`;
- com `ENABLE_API_DOCS=True`, usuario autenticado nao-staff nao recebe `200`;
- com `ENABLE_API_DOCS=True`, usuario staff recebe `200`.

### Rotas `/api/*` ainda Django puro

Nenhuma rota `/api/*` permanece Django puro no URLConf atual.

## Conferencia de escopo

Estado do working tree antes da criacao deste documento:

- `git status --short`: sem saida.
- `git diff --stat`: sem saida.

Nao foram identificadas alteracoes pendentes em:

- frontend;
- settings;
- CORS;
- CSRF global;
- autenticacao global;
- models;
- migrations;
- rotas fora de `/api/*`;
- regras de negocio.

Durante a PM-39, a unica alteracao planejada foi este documento de fechamento.

## Validacao tecnica

Comandos executados com variaveis locais temporarias:

```bash
SECRET_KEY=local-validation-secret DEBUG=True python manage.py test caixa.tests.ApiDocsUrlsTests
SECRET_KEY=local-validation-secret DEBUG=True python manage.py check
SECRET_KEY=local-validation-secret DEBUG=True python manage.py spectacular --validate
SECRET_KEY=local-validation-secret DEBUG=True python manage.py test
```

Resultados:

- `ApiDocsUrlsTests`: 4 testes OK.
- `python manage.py check`: OK, sem issues.
- `python manage.py spectacular --validate`: OK.
- `python manage.py test`: 812 testes OK.

Warnings/logs observados:

- Warnings de CSRF esperados em testes que validam bloqueio antes da view.
- Logs do Axes esperados em testes de falha de login.
- Log de erro simulado em teste existente de backup manual.
- Nenhum warning critico novo do `spectacular`.

## Validacao de schema

O schema gerado por `drf_spectacular.generators.SchemaGenerator` inclui as 35
rotas de aplicacao `/api/*` migradas.

Paths confirmados no schema:

- `/api/auth/csrf/`
- `/api/auth/login/`
- `/api/auth/logout/`
- `/api/auth/session/`
- `/api/backups/`
- `/api/backups/criar/`
- `/api/baixas-financeiras-canonicas/`
- `/api/canonical-financial-model/`
- `/api/canonical-settlements/`
- `/api/clientes/`
- `/api/clientes/{id}/`
- `/api/custos-fixos/`
- `/api/custos-fixos/{id}/`
- `/api/custos-por-evento/`
- `/api/dashboard/financial-overview/`
- `/api/despesas/{id}/`
- `/api/eventos/`
- `/api/eventos/custos-extras/`
- `/api/eventos/{id}/`
- `/api/fcf/`
- `/api/fcf/creditors/`
- `/api/fcf/debts/`
- `/api/fci/`
- `/api/lancamentos-financeiros/`
- `/api/mes-financeiro/`
- `/api/modelagem-financeira-canonica/`
- `/api/obrigacoes-financeiras/`
- `/api/obrigacoes-financeiras/exportar/`
- `/api/obrigacoes-financeiras/liquidar/`
- `/api/orcamentos/`
- `/api/orcamentos/{id}/`
- `/api/orcamentos/{id}/aprovar/`
- `/api/payment-obligations/`
- `/api/payment-obligations/settle/`
- `/api/receitas/{id}/`

As rotas de documentacao (`/api/schema/`, `/api/docs/`, `/api/redoc/`) sao
rotas de infraestrutura protegidas e nao fazem parte do contrato de aplicacao
gerado como paths de negocio no schema.

## Validacao de contrato

Padroes preservados nas PMs incrementais:

- `401` e `403` manuais mantidos onde ja existiam.
- CSRF real preservado em endpoints mutaveis (`POST`/`PUT`).
- `404` Django padrao preservado onde era contrato.
- `405` Django/manual preservado conforme cada endpoint.
- `Response` usado apenas na borda DRF.
- Ausencia de Serializer DRF, ViewSet e ModelViewSet nas PMs incrementais.
- Payloads e aliases preservados por testes de paridade.
- Headers `no-store` preservados nas respostas JSON.
- Exportacao CSV preservada, incluindo headers, BOM, separador, terminador e
  nomes de arquivo.
- Efeitos financeiros preservados por testes focados e suite completa.

## Riscos residuais

- OpenAPI ainda usa schemas genericos (`object`) em muitos endpoints, por
  decisao consciente de priorizar paridade runtime sobre documentacao detalhada.
- Swagger/ReDoc podem exigir validacao visual em ambiente real por causa de CSP
  e assets, embora as rotas estejam protegidas e os testes de acesso passem.
- A migracao manteve helpers e serializers manuais; isso reduz risco runtime,
  mas a documentacao OpenAPI ainda pode ser refinada em PM futura com
  `extend_schema`, sem alterar contrato.
- Recomenda-se validação manual de frontend/staging antes do deploy, pois a
  suite automatizada nao substitui uma passada real nos fluxos principais.

## Checklist de deploy manual recomendado

- Rodar `git status --short`.
- Rodar `git diff --stat`.
- Revisar commits pendentes.
- Rodar suite completa local.
- Subir para branch/PR.
- Revisar diff de views migradas.
- Testar em staging, se existir.
- Testar login/logout.
- Testar dashboard.
- Testar FCI/FCF.
- Testar obrigacoes financeiras e liquidacao.
- Testar backup, listagem e download.
- Testar exportacao CSV.
- Verificar aba Network do frontend para `4xx` inesperados.
- Confirmar `ENABLE_API_DOCS=False` ou acesso staff-only em ambiente de
  producao.

## Criterios de bloqueio avaliados

- Rota `/api/*` ainda Django puro: nao encontrado.
- `check` falhar: nao ocorreu.
- `spectacular --validate` falhar: nao ocorreu.
- Suite completa falhar: nao ocorreu.
- Warning novo critico do spectacular: nao encontrado.
- Alteracao inesperada fora do escopo: nao encontrada.
- Necessidade de alterar frontend: nao identificada.

## Conclusao

A revisao final da PM-39 esta concluida.

A migracao DRF das rotas `/api/*` esta encerrada no URLConf atual e esta pronta
para commit/deploy manual, condicionada a revisao humana do diff e aos testes
manuais/staging recomendados no checklist.
