# ADR 0011 - Cliente final tenant-scoped

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS tera lojas independentes. A mesma pessoa real pode comprar em mais de uma loja.

## Problema

Se o comprador for tratado como identidade global por padrao, uma loja pode inferir dados, comportamento ou existencia do comprador em outra loja.

## Alternativas Consideradas

- Conta global unica de comprador.
- Conta global com isolamento logico por loja.
- Customer separado por tenant.

## Decisao

O cliente final sera tenant-scoped inicialmente.

`Customer` vive no schema do tenant. O mesmo e-mail, CPF ou telefone pode existir em tenants diferentes como registros independentes, conforme regra de negocio e LGPD.

Conta global de comprador exigira ADR futuro, base legal, consentimento e desenho proprio de privacidade.

## Consequencias

- Login, sessao, reset de senha, carrinho, pedidos e perfil do comprador ficam restritos ao Host/tenant atual.
- Lojas nao compartilham dados de compradores.
- O mesmo comprador real pode ter contas tecnicas separadas.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Experiencia menos unificada para o comprador que compra em varias lojas.
- Suporte deve ter fluxo auditado para qualquer acesso transversal.
- Futuro marketplace exigira revisao dessa decisao.

## Criterios de Revisao Futura

- Necessidade real de marketplace.
- Necessidade legal/comercial de perfil global.
- Modelo de consentimento definido.
- Testes provando que identidade global nao permite vazamento entre lojas.
