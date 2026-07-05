# Internacionalizacao

Internacionalizacao fica para fase futura, mas a arquitetura deve evitar decisoes que bloqueiem idiomas, moedas e fusos horarios.

## Escopo Futuro

- idiomas;
- moedas;
- fuso horario;
- formato de data/hora;
- formato monetario;
- formato de telefone/documentos;
- traducoes de catalogo;
- checkout regional.

## Idiomas

Preparar para:

- idioma padrao da plataforma;
- idioma padrao do tenant;
- idioma escolhido pelo comprador;
- traducoes de produtos e categorias no futuro.

Nao implementar catalogo multilingue no MVP sem necessidade real.

## Moedas

Regras:

- armazenar valores em unidade menor quando possivel;
- registrar moeda no pedido e pagamento;
- gateway deve validar moeda;
- relatorios financeiros nao devem somar moedas diferentes sem conversao explicita.

## Fuso Horario

Regras:

- persistir datas em UTC;
- exibir datas no fuso do tenant/usuario;
- pedidos, pagamentos e webhooks devem manter timestamps originais e normalizados;
- relatorios devem declarar fuso usado.

## Formatacao Regional

Preparar para:

- separador decimal;
- moeda;
- telefone;
- endereco;
- documento fiscal.

## Fora da Fase Inicial

- multi-moeda real;
- precificacao por pais;
- impostos internacionais;
- catalogo traduzido completo;
- checkout internacional.

## Testes Futuros

- pedido armazena moeda.
- pagamento valida moeda.
- relatorio respeita fuso do tenant.
- exibicao nao altera valor persistido.
