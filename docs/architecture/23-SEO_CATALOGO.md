# SEO e Catalogo

Este capitulo define a arquitetura futura para catalogo publico, indexacao e URLs amigaveis por tenant.

## Objetivos

- URLs amigaveis;
- sitemap por tenant;
- robots por tenant;
- Open Graph;
- Schema.org;
- slugs estaveis;
- separacao entre produtos publicados e rascunhos;
- indexacao isolada por tenant.

## URLs Amigaveis

Exemplos:

```text
https://loja-a.meusaas.com/produtos/camiseta-algodao
https://loja-a.meusaas.com/categorias/masculino
```

Regras:

- slug unico por tenant;
- slug nao e identificador global;
- alterar slug deve preservar redirect quando relevante;
- produto nao publicado nao deve ser indexado.

## Produtos Publicados e Rascunhos

Estados sugeridos:

```text
draft
published
hidden
archived
out_of_stock
```

Regras:

- rascunho nao aparece em catalogo publico;
- produto oculto nao aparece em listagens;
- produto arquivado nao deve ser comprado;
- estoque indisponivel pode continuar visivel conforme regra da loja, mas checkout deve bloquear compra se nao houver estoque.

## Sitemap e Robots

Cada tenant pode ter:

- `/sitemap.xml`;
- `/robots.txt`;
- sitemap de produtos;
- sitemap de categorias;
- regras de indexacao proprias.

Sitemap deve incluir apenas URLs publicas do tenant atual.

## Open Graph e Schema.org

Produto publicado pode expor:

- titulo;
- descricao curta;
- imagem publica segura;
- preco publico;
- disponibilidade;
- marca/categoria quando aplicavel.

Nunca expor:

- dados internos;
- estoque reservado;
- margem;
- dados de cliente;
- status financeiro.

## Indexacao por Tenant

Regras:

- cada Host e indexado separadamente;
- dominio customizado deve apontar para o mesmo tenant;
- dominio canonico por tenant deve ser respeitado;
- aliases devem redirecionar para o canonico para evitar conteudo duplicado;
- noindex pode ser configurado por tenant;
- ambiente staging nao deve ser indexado.

Dominio canonico, aliases e HTTPS estao em [24 - Dominios](24-DOMINIOS.md).

## Testes Obrigatorios

- sitemap de tenant A nao contem URLs de tenant B.
- rascunho nao aparece no catalogo publico.
- produto arquivado nao pode ser comprado.
- Open Graph nao vaza dados internos.
- dominio customizado gera URLs canonicas corretas.
