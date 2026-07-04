# Plano PM-40 - Tela Next.js de servicos com API Django

Atualizado em: 2026-06-18

## Objetivo

Criar a tela operacional de servicos no frontend Next.js, usando uma API
Django/DRF segura e backend-first para o catalogo base `Servico`.

A tela deve permitir consultar, filtrar, criar e editar servicos disponiveis,
sem duplicar regra de negocio no frontend e sem alterar os fluxos financeiros
existentes.

## Decisao de dominio

Esta PM trata de:

- `Servico`: catalogo base de servicos usado por orcamentos.

Esta PM nao trata de:

- `EventoCustoServico`: custo de servico ja associado a evento.
- pagamentos de custos de servico.
- liquidacao de obrigacoes.
- calculos financeiros de orcamento.
- sincronizacoes financeiras derivadas de eventos.

## Principio principal

Backend-first.

O Django continua sendo a fonte da verdade para regras, permissoes, validacoes,
filtros, consistencia e formato do contrato. O Next.js apenas consome a API,
mostra estados visuais, coleta entrada do usuario e envia payloads canonicos.

A tela `/servicos` nao deve inventar regra. Ela deve consumir o contrato da
API.

## Escopo

- Criar documento desta PM antes de qualquer alteracao runtime.
- Fazer diagnostico read-only do modelo, admin, uso atual em orcamentos,
  permissoes e frontend.
- Criar `GET/POST /api/servicos/`.
- Criar `GET/PUT /api/servicos/<id>/`.
- Criar testes backend para autenticacao, permissoes, CSRF, duplicidade,
  validacoes, filtros e formato JSON.
- Publicar permissoes de servicos no payload de sessao.
- Validar backend com `manage.py check` e testes focados.
- Somente depois criar a tela Next.js `/servicos`.
- Finalizar com typecheck, lint e testes/guardrails frontend aplicaveis.

## Fora do escopo

- Nao mexer em `EventoCustoServico`.
- Nao mexer em pagamentos de custos de servico.
- Nao mexer em calculo de orcamento.
- Nao mexer em aprovacao de orcamento.
- Nao mexer em CORS.
- Nao mexer em CSRF global.
- Nao mexer em settings globais.
- Nao trocar autenticacao por JWT/token.
- Nao criar `DELETE`.
- Nao criar `ViewSet`.
- Nao criar `ModelViewSet`.
- Nao criar `ModelSerializer`.
- Nao criar HTML operacional Django.
- Nao fazer commit, push, merge ou deploy automaticamente.

## Preservacoes obrigatorias

- Sessao Django por cookie.
- CSRF real em `POST` e `PUT`.
- Permissoes manuais por metodo.
- `Response` DRF apenas na borda HTTP.
- Helpers e padroes existentes de erro:
  - `api_authentication_required_response()`;
  - `api_permission_denied_response()`;
  - `api_no_store_json_response()`.
- Contrato JSON explicito.
- `no-store` nas respostas JSON.
- Campos aceitos por allowlist manual.
- Validacao de modelo com `full_clean()`.
- Tratamento explicito de duplicidade.
- Servicos inativos preservados para historico e edicao.
- Orcentos continuam usando apenas servicos ativos nas opcoes atuais.

## API planejada

Rotas:

```text
GET  /api/servicos/
POST /api/servicos/
GET  /api/servicos/<id>/
PUT  /api/servicos/<id>/
```

Nomes de rota sugeridos:

```text
caixa:api_servicos
caixa:api_servico_detalhe
```

Arquivo sugerido:

```text
caixa/views_servicos_api.py
```

## Permissoes

Permissoes Django usadas:

```text
caixa.view_servico
caixa.add_servico
caixa.change_servico
```

Permissoes publicadas em `/api/auth/session/`:

```text
canViewServices
canAddService
canChangeService
```

Regras por metodo:

```text
GET  /api/servicos/       -> caixa.view_servico
POST /api/servicos/       -> caixa.add_servico + CSRF
GET  /api/servicos/<id>/  -> caixa.view_servico
PUT  /api/servicos/<id>/  -> caixa.change_servico + CSRF
```

## Contrato de entrada

Payload canonico aceito por `POST` e `PUT`:

```json
{
  "name": "Limpeza",
  "code": "limpeza",
  "dailyRate": "150.00",
  "baseHours": 8,
  "overtimePercent": "1.50",
  "usesSpecialRule": false,
  "isActive": true
}
```

Aliases legados so devem ser aceitos se forem necessarios para preservar
contrato publicado. Como esta e uma tela nova, o frontend deve enviar nomes
canonicos.

Campos mapeados para `Servico`:

```text
name             -> nome
code             -> codigo
dailyRate        -> diaria_padrao
baseHours        -> horas_base_diaria
overtimePercent  -> percentual_hora_extra
usesSpecialRule  -> usa_regra_especial
isActive         -> ativo
```

## Contrato de saida

Payload de `GET /api/servicos/`:

```json
{
  "data": {
    "services": [],
    "summary": {
      "total": 0,
      "active": 0,
      "inactive": 0,
      "specialRule": 0
    },
    "filters": {
      "search": "",
      "active": "all",
      "specialRule": "all"
    },
    "filterOptions": {
      "activeStatuses": [
        {"value": "sim", "label": "Ativo"},
        {"value": "nao", "label": "Inativo"}
      ],
      "specialRuleStatuses": [
        {"value": "sim", "label": "Com regra especial"},
        {"value": "nao", "label": "Sem regra especial"}
      ]
    },
    "permissions": {
      "canCreate": true,
      "canUpdate": true
    },
    "meta": {
      "source": "backend"
    }
  }
}
```

Shape de cada item em `data.services`:

```text
id
name
code
dailyRate
baseHours
overtimePercent
usesSpecialRule
isActive
halfDailyRate
normalHourlyRate
overtimeHourlyRate
createdAt
updatedAt
```

Payload de sucesso de criacao:

```json
{
  "data": {
    "service": {},
    "message": "Servico cadastrado com sucesso."
  }
}
```

Payload de sucesso de atualizacao:

```json
{
  "data": {
    "service": {},
    "message": "Servico atualizado com sucesso."
  }
}
```

## Contratos de erro

Usuario anonimo:

```json
{"detail": "Authentication credentials were not provided."}
```

Usuario autenticado sem permissao:

```json
{"detail": "Permission denied."}
```

Content-Type invalido em escrita:

```json
{"detail": "Content-Type deve ser application/json."}
```

JSON invalido:

```json
{"detail": "JSON invalido."}
```

Validacao:

```json
{"errors": {}}
```

Duplicidade:

```json
{"errors": {"nome": ["Ja existe um servico com este nome."]}}
```

```json
{"errors": {"codigo": ["Ja existe um servico com este codigo."]}}
```

## Filtros

Filtros canonicos aceitos por `GET /api/servicos/`:

```text
search
active
specialRule
```

Valores:

```text
active: all | sim | nao
specialRule: all | sim | nao
```

Regra de busca:

- buscar por `nome` e `codigo`.
- ordenar por `nome`, depois `id`.

## Validacoes de negocio

Validacoes esperadas:

- `name` obrigatorio.
- `code` obrigatorio.
- `dailyRate >= 0`.
- `baseHours > 0`.
- `overtimePercent >= 0`.
- `name` unico.
- `code` unico.
- booleanos normalizados com seguranca.

Validacoes devem ficar no backend. O frontend pode fazer reforco visual, mas
nao deve ser fonte primaria da regra.

## PM-40.1 - Diagnostico read-only

Status: planejada.

Objetivo: mapear o contrato antes de alterar runtime.

Tarefas:

- Ler `caixa/models.py` e confirmar campos de `Servico`.
- Ler `caixa/admin.py` e confirmar exposicao atual no Admin.
- Ler `caixa/views_orcamentos_api.py` e confirmar uso de servicos em
  orcamentos.
- Ler `caixa/permissions.py` e confirmar padrao de permissoes.
- Ler services/telas Next.js de Clientes e Custos Fixos para reaproveitar
  padroes.
- Registrar arquivos envolvidos.
- Registrar `git status --short`.

Gate de saida:

- Contrato do novo endpoint confirmado.
- Nenhuma alteracao runtime feita alem deste documento.

## PM-40.2 - API Django de servicos

Status: planejada.

Objetivo: implementar a API backend com contrato minimo e seguro.

Tarefas:

- Criar `caixa/views_servicos_api.py`.
- Criar serializers manuais internos ao arquivo, sem `ModelSerializer`.
- Criar helpers de payload, decimal, booleano, inteiro e erro.
- Criar `api_servicos`.
- Criar `api_servico_detalhe`.
- Adicionar rotas em `caixa/urls.py`.
- Reaproveitar `JsonBodySafeSessionAuthentication`.
- Reaproveitar helpers de erro e `api_no_store_json_response`.
- Usar `@api_view`.
- Usar `Response` apenas na borda.

Gate de saida:

- Endpoints respondem com auth, permissao, CSRF e JSON no contrato planejado.
- Nenhum frontend alterado nesta fase.

## PM-40.3 - Testes backend

Status: planejada.

Objetivo: congelar e validar o contrato de servicos.

Testes obrigatorios:

- URL reverse de `api_servicos`.
- URL reverse de `api_servico_detalhe`.
- `GET /api/servicos/` anonimo retorna `401`.
- `GET /api/servicos/` sem permissao retorna `403`.
- `GET /api/servicos/` com permissao retorna shape esperado.
- filtros `search`, `active`, `specialRule`.
- `POST /api/servicos/` sem CSRF real bloqueia.
- `POST /api/servicos/` sem permissao retorna `403` com CSRF valido.
- `POST /api/servicos/` cria servico com payload canonico.
- `POST /api/servicos/` rejeita Content-Type invalido.
- `POST /api/servicos/` rejeita JSON invalido.
- `POST /api/servicos/` rejeita duplicidade de nome.
- `POST /api/servicos/` rejeita duplicidade de codigo.
- `POST /api/servicos/` rejeita diaria negativa.
- `POST /api/servicos/` rejeita horas base zero.
- `POST /api/servicos/` rejeita percentual extra negativo.
- `GET /api/servicos/<id>/` retorna detalhe.
- `PUT /api/servicos/<id>/` exige CSRF.
- `PUT /api/servicos/<id>/` exige permissao.
- `PUT /api/servicos/<id>/` atualiza campos permitidos.
- `GET/PUT /api/servicos/<id>/` preserva `404` Django padrao quando
  aplicavel.

Gate de saida:

- Testes focados de API passam.
- `python manage.py check` passa.

## PM-40.4 - Permissoes no payload de sessao

Status: planejada.

Objetivo: publicar capacidades de servicos para o Next.js controlar navegacao
e acoes visuais.

Tarefas:

- Adicionar constantes de permissao em `caixa/permissions.py`.
- Adicionar campos em `_user_payload` de `caixa/views_api_auth.py`.
- Atualizar testes de sessao/permissoes existentes, se necessario.

Gate de saida:

- `/api/auth/session/` inclui `canViewServices`, `canAddService` e
  `canChangeService` para usuarios autenticados.
- Testes focados de auth/session passam.

## PM-40.5 - Frontend Next.js `/servicos`

Status: planejada.

Objetivo: criar tela operacional depois de API backend validada.

Tarefas:

- Criar `features/financial-dashboard/services/financial-services-service.ts`.
- Criar `features/financial-dashboard/hooks/use-financial-services.ts`.
- Criar hook de criacao/edicao de servico.
- Criar `features/financial-dashboard/components/financial-services-view.tsx`.
- Criar `app/servicos/page.tsx`.
- Exportar a view e hooks em `features/financial-dashboard/index.ts`.
- Adicionar item "Servicos" na sidebar.
- Usar `canViewServices`, `canAddService`, `canChangeService`.

Gate de saida:

- Tela lista, filtra, cria e edita servicos via API.
- Escritas usam CSRF via `requestBackendCsrfToken`.
- Frontend nao duplica regra de negocio.

## PM-40.6 - Validacao final

Status: planejada.

Backend:

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py test <testes-focados>
```

Frontend:

```bash
npx --yes pnpm@10.33.4 run typecheck
npx --yes pnpm@10.33.4 run lint
npx --yes pnpm@10.33.4 run check:dashboard
```

Quando aplicavel:

```bash
npx --yes pnpm@10.33.4 run build
```

Gate de saida:

- Backend verde.
- Frontend verde.
- Tela `/servicos` funcionando.
- Tela de orcamentos sem regressao no uso de servicos ativos.

## Criterios de aceite

- `GET /api/servicos/` lista servicos com filtros e resumo.
- `POST /api/servicos/` cria servico com sessao, permissao e CSRF.
- `GET /api/servicos/<id>/` retorna detalhe.
- `PUT /api/servicos/<id>/` edita servico com sessao, permissao e CSRF.
- Payload de sessao publica permissoes de servico.
- Next.js exibe `/servicos` somente para usuario autorizado.
- Tela cria e edita sem `DELETE`.
- Servicos inativos continuam editaveis, mas nao devem entrar como opcoes de
  novos orcamentos.
- `EventoCustoServico`, pagamentos, calculo de orcamento, CORS, CSRF global e
  settings permanecem inalterados.

