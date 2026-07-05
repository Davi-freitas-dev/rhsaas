# ADR 0026 - Entitlements, planos e limites

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS tera planos, assinaturas, limites e funcionalidades liberadas por tenant.

## Problema

Misturar plano, assinatura, permissao, limite e feature flag gera autorizacao confusa e bugs comerciais.

## Alternativas

- Controlar tudo por feature flags.
- Controlar tudo por permissoes de usuario.
- Separar Plan, Subscription, Limits, Feature Access e Feature Flags.

## Decisao

Separar conceitos.

`Plan` define oferta. `Subscription` vincula tenant ao plano. `Limits` medem quotas. `Feature Access` define direito do tenant. `Feature Flags` controlam rollout tecnico.

## Consequencias

- Modelo mais claro.
- Billing futuro fica mais seguro.
- Backend precisa checar entitlement alem de permissao do usuario.

## Trade-offs

- Mais modelagem.
- Evita confundir rollout com cobranca.
- Reduz risco de liberar recurso indevidamente.

## Riscos

- Falha de medicao pode quebrar limites.
- Feature flag usada como billing pode gerar bypass.
- Plano suspenso precisa bloquear checkout corretamente.

## Criterios para revisao futura

- Billing implementado.
- Trial publico.
- Planos enterprise.
- Marketplace.
