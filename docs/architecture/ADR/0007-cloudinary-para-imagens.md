# ADR 0007 - Cloudinary para Imagens

## Status

Aceito.

## Data

2026-07-05

## Contexto

Produtos precisam de imagens publicas, otimizadas e escalaveis.

## Problema

Armazenar e entregar imagens sem sobrecarregar o backend.

## Alternativas Consideradas

- Storage local.
- S3/compatibilidade S3.
- Cloudinary.

## Decisao

Usar Cloudinary para imagens de produto.

## Consequencias

- Transformacoes e CDN.
- Upload assinado.
- Banco guarda referencias.
- Folders devem incluir tenant/schema.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Tenant associar imagem de outro tenant se nao validar public_id.
- Custos de bandwidth/transformacao.

## Criterios de Revisao Futura

- Volume/custo justificar S3 + CDN proprio.

