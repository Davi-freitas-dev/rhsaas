# ADR 0024 - Dominio canonico e aliases

## Status

Aceito.

## Data

2026-07-05

## Contexto

Um tenant pode ter subdominio da plataforma, dominio proprio e aliases.

## Problema

Multiplos dominios podem causar confusao de sessao, SEO duplicado e roteamento incorreto.

## Alternativas

- Permitir apenas subdominio da plataforma.
- Permitir varios dominios sem canonico.
- Exigir dominio canonico por tenant e redirecionar aliases.

## Decisao

Cada tenant deve ter um dominio canonico.

Aliases podem existir, mas devem redirecionar para o canonico antes de login/checkout quando aplicavel.

Todo dominio exige verificacao de propriedade e HTTPS valido.

## Consequencias

- SEO mais limpo.
- Menos confusao de cookie/sessao.
- Operacao de dominios fica mais exigente.

## Trade-offs

- Mais trabalho de configuracao.
- Maior seguranca e previsibilidade.
- Menos flexibilidade para lojas que querem multiplos hosts ativos.

## Riscos

- Certificado expirado.
- Alias apontando errado.
- Dominio canonico mal configurado pode afetar vendas.

## Criterios para revisao futura

- Dominios customizados em escala.
- Multi-store por tenant.
- Expansao internacional.
- Requisitos especificos de SEO.
