# ADR 0021 - Secret management para gateways

## Status

Aceito.

## Data

2026-07-05

## Contexto

Cada tenant pode configurar gateway e credenciais proprias.

## Problema

Guardar segredo em texto puro ou expor segredo em API/log/admin compromete pagamentos e isolamento.

## Alternativas

- Guardar segredo em campo comum no banco.
- Guardar segredo criptografado no banco com envelope encryption.
- Usar secret manager externo.
- Usar credencial global da plataforma.

## Decisao

Usar secret manager quando disponivel. Como alternativa aceitavel, usar envelope encryption com chaves fora do banco de aplicacao.

`PaymentProviderConfig` e `WebhookIngressRegistry` armazenam `secret_ref`, nao o segredo em texto puro.

## Consequencias

- Segredos nao aparecem em respostas de API.
- Rotacao fica planejavel.
- Ambientes sandbox/producao ficam separados.
- Operacao exige processo de secret management.

## Trade-offs

- Mais complexidade operacional.
- Muito mais seguranca para pagamentos.
- Pode aumentar custo de infraestrutura.

## Riscos

- Secret manager indisponivel pode afetar checkout/webhooks.
- Rotacao incompleta pode quebrar provider.
- Permissoes excessivas no secret manager anulam o ganho.

## Criterios para revisao futura

- Escolha de provedor cloud.
- Requisitos PCI/financeiros.
- Novos gateways.
- Planos enterprise com isolamento reforcado.
