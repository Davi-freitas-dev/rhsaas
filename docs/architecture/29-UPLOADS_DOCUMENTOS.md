# Uploads, Anexos e Documentos

Este capitulo amplia a arquitetura de upload alem de imagens de produto.

## Escopo

Preparar para:

- anexos de pedido;
- comprovantes de pagamento;
- documentos fiscais;
- evidencias de chargeback;
- comprovantes de entrega;
- arquivos de suporte;
- documentos de cadastro da loja.

## Principios

- todo arquivo pertence a um tenant ou ao `public` de plataforma;
- arquivos de tenant usam path/folder tenant-scoped;
- acesso exige autorizacao;
- metadados ficam no banco;
- segredo ou documento sensivel nao fica publico por padrao;
- downloads sao auditados quando sensiveis.

Decisao: imagens publicas de catalogo e documentos privados seguem pipelines separados.

- imagens publicas podem usar Cloudinary com URLs publicas controladas;
- documentos sensiveis usam storage privado, URL assinada curta ou download via backend;
- documentos sensiveis nunca devem ser tratados como imagem publica.

## Organizacao

Exemplo conceitual:

```text
uploads/tenants/{schema_name}/orders/{order_id}/
uploads/tenants/{schema_name}/payments/{payment_id}/
uploads/tenants/{schema_name}/chargebacks/{chargeback_id}/
uploads/platform/{scope}/
```

## Validacoes

- tamanho maximo;
- tipo/MIME permitido;
- extensao permitida;
- antivirus/moderacao quando necessario;
- nome seguro;
- owner/tenant;
- objeto relacionado;
- permissao de upload;
- permissao de download.

## Documentos Sensiveis

Para CPF/CNPJ, comprovantes e documentos fiscais:

- acesso restrito;
- URL assinada ou download via backend;
- expiracao de link;
- AuditLog;
- retencao definida;
- mascaramento quando possivel.
- antivirus ou scanner equivalente antes de liberar uso;
- metadados tenant-scoped;
- revogacao de acesso quando tenant e suspenso/encerrado.

## Testes Obrigatorios

- tenant A nao baixa arquivo do tenant B.
- upload rejeita MIME invalido.
- arquivo sensivel nao tem URL publica permanente.
- download sensivel gera auditoria.
- arquivo temporario expira/limpa.

## O Que Nao Fazer

- Nao salvar upload de tenant em pasta global sem schema.
- Nao confiar em extensao de arquivo.
- Nao expor documento sensivel por URL publica permanente.
- Nao permitir path traversal.
