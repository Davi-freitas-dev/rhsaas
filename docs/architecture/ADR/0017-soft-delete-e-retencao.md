# ADR 0017 - Soft delete e retencao para entidades sensiveis

## Status

Aceito.

## Data

2026-07-05

## Contexto

E-commerce possui pedidos, pagamentos, clientes, documentos e auditoria.

## Problema

Excluir fisicamente dados financeiros ou auditaveis pode quebrar suporte, conciliacao, fiscal e rastreabilidade.

## Alternativas Consideradas

- Hard delete por padrao.
- Soft delete para tudo.
- Soft delete seletivo com retencao e anonimizacao.

## Decisao

Usar soft delete/arquivamento para entidades sensiveis e hard delete apenas para temporarios, cache, sessoes expiradas e arquivos rejeitados quando seguro.

Dados pessoais podem exigir anonimizacao conforme LGPD.

## Consequencias

- Historico preservado.
- Querysets precisam filtrar deletados.
- Politicas de retencao precisam ser definidas.

## Trade-offs

Os trade-offs principais estao descritos em consequencias e riscos. Revisoes futuras devem detalhar este item quando a decisao mudar.

## Riscos
- Crescimento de banco.
- Retencao excessiva.
- Confusao entre deletar, arquivar e anonimizar.

## Criterios de Revisao Futura

- Politica juridica de retencao.
- Fiscal integrado.
- Solicitacoes LGPD.
- Crescimento de dados.
