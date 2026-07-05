# Feature Flags

Feature flags permitem liberar funcionalidades com controle, sem transformar beta em risco global.

Feature flags nao substituem entitlements. A separacao entre `Plan`, `Subscription`, `Limits`, `Feature Access` e `Feature Flags` esta em [36 - Entitlements, Planos e Limites](36-ENTITLEMENTS_PLANOS_LIMITES.md).

## Objetivos

- liberar funcionalidade por tenant;
- beta fechado;
- rollout gradual;
- rollback rapido;
- testes em producao com escopo controlado;
- evitar deploy separado para cada cliente.

## Escopos

Flags podem existir em:

- plataforma/global;
- plano/assinatura;
- tenant;
- usuario interno;
- grupo beta;
- ambiente.

## Regras

- flags sensiveis sao avaliadas no backend;
- frontend pode esconder UI, mas backend decide permissao real;
- alteracao de flag gera auditoria;
- flag deve ter dono e data de revisao;
- flag temporaria deve ter plano de remocao;
- flags nao substituem permissao.

## Exemplos

```text
tenant.checkout.guest_enabled
tenant.payments.manual_pix_enabled
tenant.payments.gateway_stripe_enabled
tenant.catalog.seo_advanced_enabled
platform.support_impersonation_enabled
```

## Rollback

Feature flag deve permitir:

- desligar funcionalidade para um tenant;
- desligar globalmente em incidente;
- manter dados ja criados consistentes;
- registrar motivo.

## O Que Nao Fazer

- Nao usar flag como autorizacao unica.
- Nao deixar flag permanente sem dono.
- Nao liberar feature financeira sem teste.
- Nao permitir que tenant altere flag critica de seguranca.
