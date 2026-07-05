# Entitlements, Planos e Limites

Este documento separa `Plan`, `Subscription`, `Limits`, `Feature Access` e `Feature Flags`.

Fica fora do MVP funcional completo, mas a arquitetura deve deixar fronteiras claras.

## Conceitos

### Plan

Define a oferta comercial.

Exemplos:

- Basic;
- Pro;
- Enterprise.

Contem:

- recursos inclusos;
- limites padrao;
- preco;
- regras comerciais.

### Subscription

Vincula um tenant a um plano.

Contem:

- tenant;
- plan;
- status;
- periodo;
- billing state;
- trial;
- renovacao/cancelamento.

### Limits

Definem limites mensuraveis.

Exemplos:

- quantidade de produtos;
- usuarios internos;
- uploads;
- storage;
- pedidos por mes;
- dominios customizados;
- provedores de pagamento ativos.

### Feature Access

Decide se o tenant pode usar uma funcionalidade.

Exemplos:

- guest checkout;
- Pix manual;
- gateway online;
- dominios customizados;
- SEO avancado;
- relatorios avancados;
- suporte prioritario.

### Feature Flags

Controlam rollout tecnico.

Exemplos:

- beta fechado;
- rollout gradual;
- desligamento emergencial;
- teste A/B tecnico.

Feature flag nao substitui entitlement.

## Regra Canonica

Permissao de uso de funcionalidade deve considerar:

```text
tenant status
subscription status
plan
limits
feature access
feature flags
role/permission do usuario
```

## Separacao de Responsabilidades

- `Plan`: produto comercial.
- `Subscription`: contrato/estado de cobranca do tenant.
- `Limits`: quotas e uso.
- `Feature Access`: direito do tenant usar a funcionalidade.
- `Feature Flags`: controle operacional/rollout.
- `Permissions`: autorizacao do usuario dentro do tenant.

## Exemplos

Tenant no plano Basic:

- pode vender produtos;
- nao pode dominio customizado;
- pode Pix manual;
- nao pode gateway avancado.

Tenant Enterprise:

- pode multiplos dominios;
- pode suporte prioritario;
- pode limites maiores;
- pode recursos beta se habilitados.

## Riscos

- misturar flag com permissao;
- frontend esconder recurso, mas backend permitir;
- tenant suspenso continuar vendendo;
- plano expirado continuar usando gateway;
- limite sem medicao confiavel.

## Fora do MVP

- billing completo;
- cobranca automatica;
- planos comerciais finais;
- marketplace de apps;
- entitlements complexos por modulo.

## O Que Nao Fazer

- Nao deixar frontend decidir entitlement.
- Nao usar `is_superuser` para liberar recurso comercial.
- Nao usar feature flag como billing.
- Nao bloquear export de dados obrigatorio apenas por inadimplencia sem politica legal/comercial.
