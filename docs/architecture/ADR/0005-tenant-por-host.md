# ADR 0005 - Tenant por Host

## Status

Aceito.

## Data

2026-07-05

## Contexto

Cada loja sera acessada por subdominio ou dominio proprio.

## Problema

Identificar tenant sem confiar em parametro manipulavel pelo usuario.

## Alternativas Consideradas

- Query string.
- Header customizado.
- Payload.
- Host.

## Decisao

Resolver tenant exclusivamente por Host validado.

Nao resolver tenant por:

- query string;
- header customizado;
- payload;
- cookie editavel pelo usuario.

Cookies de sessao e CSRF devem ser host-only. A aplicacao nao deve usar `Domain=.meusaas.com` para cookies de sessao ou CSRF.

Cache, throttling, logs, jobs e arquivos ligados a tenant devem incluir `schema_name`.

## Consequencias

- Menor risco de troca maliciosa de tenant.
- Cookies host-only funcionam melhor.
- Login, logout, sessao, CSRF, carrinho, pedidos e pagamentos ficam independentes por subdominio.
- Dominio customizado exige verificacao.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Configuracao incorreta de proxy pode quebrar Host.
- ALLOWED_HOSTS precisa ser rigoroso.
- Algum cliente externo pode pedir selecao de tenant por header no futuro; isso exige ADR propria e nao deve afetar a aplicacao web.

## Criterios de Revisao Futura

- Apps mobile ou API publica podem exigir estrategia adicional, sem abandonar isolamento por dominio para web.
