# ADR 0025 - Storage privado para documentos sensiveis

## Status

Aceito.

## Data

2026-07-05

## Contexto

O SaaS tera imagens publicas de catalogo e tambem pode ter comprovantes, documentos fiscais e evidencias sensiveis.

## Problema

Tratar documentos sensiveis como imagens publicas pode vazar dados pessoais, fiscais ou financeiros.

## Alternativas

- Usar apenas Cloudinary publico para todos os arquivos.
- Guardar documentos privados no mesmo fluxo de imagens com flags.
- Separar storage publico de imagens e storage privado para documentos.

## Decisao

Separar imagens publicas de catalogo de documentos sensiveis.

Documentos sensiveis usam storage privado, URLs assinadas/expiraveis ou download via backend autorizado, sempre tenant-scoped.

## Consequencias

- Menor risco de vazamento.
- Mais complexidade de storage.
- Melhor base para LGPD e fiscal.

## Trade-offs

- Mais custo operacional.
- Mais seguranca e controle.
- Menos simplicidade que uma unica pipeline de upload.

## Riscos

- Configuracao incorreta pode tornar documento publico.
- URL assinada longa demais aumenta risco.
- Antivirus/moderacao pode gerar custo.

## Criterios para revisao futura

- Fiscal implementado.
- Upload de comprovantes reais.
- Requisitos enterprise.
- Volume alto de documentos.
