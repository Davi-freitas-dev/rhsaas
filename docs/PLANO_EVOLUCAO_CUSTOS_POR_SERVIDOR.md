# Plano vivo — custos por servidor

Status: primeira evolução implementada; validação final concluída

Última revisão: 2026-08-09

Backend analisado: `rhsaas` em `6030f86`

Frontend analisado: `rhsaasfront` em `13dc552`

## Finalidade deste arquivo

Este documento é a referência para evoluir a tela **Custos por servidor** sem
misturar conceitos financeiros, expor salários sem permissão ou contar o mesmo
custo duas vezes.

A primeira entrega desejada deve substituir os cards genéricos atuais por:

1. **Custo com diaristas**;
2. **Salários de mensalistas**;
3. **Custo total da equipe**.

Os cards **Servidores** e **Eventos** podem permanecer. O card
**Apropriação gerencial**, que hoje nunca é calculado, deve ser ocultado até a
funcionalidade correspondente existir. Quando implementado, o nome recomendado
é **Custo de mensalistas nos eventos**.

Este é um documento vivo. Todo novo comportamento, inconsistência ou decisão
deve ser acrescentado às seções apropriadas e ao histórico no final. Um item só
pode ser marcado como concluído depois dos testes e critérios de aceite
correspondentes.

## Escopo e limites

### Incluído na primeira evolução

- tornar explícita a separação entre diárias e salários;
- apresentar o total da equipe sem dupla contagem;
- distinguir valor zero de valor restrito, não aplicável ou incompleto;
- preservar permissões salariais e isolamento entre tenants;
- manter compatibilidade temporária com o contrato atual da API;
- deixar claro ao usuário qual base financeira e temporal está sendo exibida.

### Fora da primeira evolução

- criar despesas, pagamentos ou obrigações novas;
- ratear salário entre eventos;
- alterar a materialização de salários;
- ratear automaticamente meses parciais de contrato ou de vigência salarial;
- inventar uma jornada padrão para mensalistas;
- alterar dados históricos;
- alterar regras de diaristas, eventos ou serviços.

## Glossário e nomes recomendados

| Nome na interface | Significado | Não significa |
| --- | --- | --- |
| **Custo com diaristas** | Soma do custo financeiro das participações de diaristas incluídas no período e nos filtros | Salário, adiantamento ou apropriação de mensalista |
| **Salários de mensalistas** | Soma das ocorrências salariais materializadas e válidas incluídas no período | Necessariamente valor pago, encargos trabalhistas ou salário apenas cadastrado |
| **Custo total da equipe** | `custo com diaristas + salários de mensalistas`, quando os dois componentes estão disponíveis | Soma da apropriação gerencial nem criação de nova saída |
| **Custo de mensalistas nos eventos** | Futura distribuição analítica do custo salarial entre eventos | Nova despesa, novo pagamento ou valor adicional no total da equipe |

Enquanto o card salarial usar `CustoFixo.valor_previsto`, a interface deve
explicar: **“Salários previstos materializados com vencimento no período.”**
Não usar apenas “custo real”, pois o pagamento pode estar pendente ou parcial.

## Comportamento comprovado atualmente

### Cadastro do mensalista

O fluxo de criação e edição está em:

- `caixa/models_servidores.py`;
- `caixa/serializers_servidores.py`;
- `caixa/services_servidores.py`;
- `caixa/views_servidores_api.py`;
- `rhsaasfront/features/financial-dashboard/components/financial-servers-view.tsx`;
- `rhsaasfront/features/financial-dashboard/services/financial-servers-service.ts`.

O mensalista possui hoje:

- salário mensal;
- data de vigência do salário e histórico salarial;
- início e fim do contrato;
- dia de pagamento;
- data de início da automação/materialização salarial;
- serviços aos quais está vinculado.

Não existe campo de jornada diária, carga horária semanal ou quantidade de
horas mensais contratadas. O valor `horas_base_diaria_snapshot`, atualmente com
padrão 8, pertence à participação/rateio do serviço no evento. Ele não é uma
jornada contratual do mensalista e não pode ser reutilizado silenciosamente
como tal.

Ao criar ou editar um mensalista, o backend:

1. salva o servidor e seus vínculos com serviços;
2. cria ou fecha vigências no histórico salarial;
3. sincroniza um plano recorrente salarial, quando toda a automação está
   configurada;
4. tenta materializar a competência indicada ou a competência atual.

A materialização é deliberadamente bloqueada se o contrato ou a vigência
salarial cobrir apenas parte do mês. Não existe rateio automático de mês
parcial.

### Custo com diaristas

Em `caixa/selectors_custos_servidores.py`, cada participação de diarista usa
`ParticipacaoServidorEvento.valor_final` como `financialRealCost`. Uma
participação de mensalista sempre contribui `0.00` para esse subtotal.

O período atual é aplicado por `Evento.data_inicio`, não pelas datas realmente
trabalhadas em `ServidorEventoDiaTrabalhado`. Logo, um evento que começou fora
do período fica fora por inteiro, ainda que existam dias trabalhados dentro do
período.

O nome atual `participationCostTotal` é genérico, mas o valor representa, na
prática, somente o custo financeiro de diaristas.

### Salários de mensalistas

O relatório consulta `CustoFixo` classificado como salário e permitido ao
usuário. A ocorrência é incluída pela faixa de `data_vencimento` e o valor
somado é `valor_previsto`.

Consequências:

- o valor não representa necessariamente o que já foi pago;
- `valor_pago`, `status`, cancelamento e saldo não definem o subtotal atual;
- o relatório depende de a competência ter sido materializada;
- como o período padrão termina na data de hoje, um salário do mês atual com
  vencimento futuro ainda fica fora do card;
- salário apenas cadastrado no servidor, sem ocorrência materializada, não
  aparece;
- competência bloqueada ou ausente reduz o total sem aviso de incompletude.

### Total atual

`summary.totalPeriod` é a soma de:

```text
participações de diaristas pelo valor final
+ ocorrências salariais pelo valor previsto
```

A apropriação gerencial não entra nessa soma. Atualmente ela é sempre `0.00`
com `managerialAppropriationCalculated=false`, portanto a interface mostra
“Não calculada”.

### Filtros atuais

| Filtro | Participações | Salários materializados | Observação |
| --- | --- | --- | --- |
| período | início do evento no intervalo | vencimento no intervalo | duas bases temporais diferentes |
| servidor | id atual ou snapshot | servidor atual ou snapshot do histórico | adequado para registros excluídos quando há snapshot |
| cadastro existente/excluído | aplicado | aplicado | usa o vínculo atual/nulo |
| ativo/inativo | situação atual do servidor | situação atual do servidor | um relatório histórico pode mudar após ativação/inativação |
| vínculo diarista | somente diaristas | nenhum | coerente com o recorte |
| vínculo mensalista | somente mensalistas | salários | participação mensalista vale zero financeiramente |
| serviço | aplicado | **todos os salários são removidos** | remoção silenciosa |
| evento | aplicado | **todos os salários são removidos** | não existe apropriação para atribuí-los ao evento |
| valor editado | aplicado | **todos os salários são removidos** | filtro pertence somente a participações |

### Permissões atuais

- a tela exige `view_custos_servidor`;
- ocorrências salariais só são consultadas com a permissão salarial;
- a apropriação possui permissão própria;
- sem permissão salarial, os salários são excluídos antes da agregação;
- apesar disso, `totalPeriod` continua numérico e `salaryCostTotal` pode ser
  serializado como `0.00`, sem distinguir **sem salário** de **restrito**;
- o frontend não usa `canViewSalary` para explicar essa diferença na tela de
  custos por servidor.

Não foi encontrada fuga direta do valor salarial no selector. O problema atual
é de semântica: dois usuários podem ver um card com o mesmo nome e totais de
escopos diferentes.

## Invariantes obrigatórios

Estes pontos não são decisões abertas:

1. `teamCostTotal = diaristCostTotal + monthlySalaryTotal` somente quando os
   componentes necessários estiverem calculados no mesmo escopo.
2. Apropriação de mensalista nunca entra em `teamCostTotal`; o salário já está
   incluído uma vez.
3. Apropriação nunca cria `CustoFixo`, lançamento, obrigação, baixa ou saída de
   caixa.
4. Usuário sem permissão salarial não pode inferir salários por diferença entre
   totais.
5. `0.00` significa valor calculado e realmente igual a zero. Não pode substituir
   “restrito”, “não aplicável” ou “incompleto”.
6. Nenhuma jornada de 8 horas pode ser presumida para mensalistas a partir do
   snapshot de uma participação.
7. Histórico e snapshots devem continuar identificando servidor excluído sem
   reassociá-lo por nome ou outra heurística.
8. Toda agregação permanece dentro do schema/tenant atual.

## Achados do levantamento

As prioridades abaixo registram tanto as decisões tomadas nesta entrega quanto
melhorias futuras. Cada achado informa explicitamente se foi corrigido agora ou
se permaneceu fora do escopo.

### P1 — totais podem transmitir uma composição incorreta

`totalPeriod` não informa se contém salários. Sem permissão salarial, com
materialização ausente ou com filtros de evento/serviço/edição, o total pode
conter apenas diaristas e ainda ser apresentado como “Custo no período”.

Recomendação: cada métrica deve possuir valor e estado explícitos. O total da
equipe deve ser `null`/indisponível quando um componente obrigatório estiver
restrito ou incompleto.

### P1 — ocorrências salariais canceladas ou inativas não são excluídas

O selector filtra classificação, vencimento e servidor, mas não filtra
`CustoFixo.ativo` nem `CustoFixo.status`. Uma ocorrência salarial cancelada ou
inativa pode continuar compondo `salaryCostTotal` pelo valor previsto.

Decisão fechada: o subtotal de salários previstos exclui ocorrências canceladas
e inativas. Pendentes, parciais e pagas permanecem pelo `valor_previsto`. Se o
produto quiser um histórico de previsão original, ele deve ser uma métrica
separada e nomeada como tal.

### P1 — custo salarial legado pode ser omitido ou quebrar o relatório

A política salarial também reconhece `categoria="salario"`. O modelo permite
um custo legado dessa categoria sem `competencia`, plano ou histórico. Se ele
não possuir referência de servidor, o selector o omite silenciosamente. Se
possuir uma referência determinística, mas continuar sem competência, o
selector chega a `ocorrencia.competencia.strftime(...)` e pode retornar erro
500. A migration `0044_recorrencias_salariais` adicionou os campos, mas não
converteu automaticamente todo custo salarial legado.

Recomendação: antes de ampliar o relatório, adicionar cobertura para registros
legados e tratar esses registros de forma determinística e somente quando houver
uma associação confiável. Registro sem referência não deve ser atribuído por
nome. O endpoint não deve retornar erro 500; deve sinalizar cobertura
incompleta sem expor conteúdo salarial.

### P1 — ausência de materialização parece salário zero

O salário cadastrado e seu histórico não entram diretamente no relatório. Se a
ocorrência mensal não foi materializada — por falha operacional, período
parcial, bloqueio ou automação não configurada — o total fica menor sem indicar
o motivo.

Recomendação: reutilizar uma verificação de completude baseada nos planos e nas
competências esperadas, sem projetar valores no total. A API deve retornar um
estado agregado seguro, sem revelar salário a quem não tem permissão.

### P1 — período sem limite poderia tornar a checagem de cobertura excessiva

Achado durante a implementação: o relatório legado aceita períodos amplos e a
nova verificação de competências poderia iterar mês a mês sem limite para cada
mensalista. Isso criaria risco de consumo excessivo por uma consulta autenticada.

Decisão tomada nesta entrega: limitar a análise semântica de cobertura a 120
meses, alinhada ao limite já usado pelas recorrências. Acima disso, os novos
cards salariais retornam `incomplete` com
`SALARY_COVERAGE_PERIOD_EXCEEDS_LIMIT`; `totalPeriod` continua disponível como
subtotal legado e nenhuma escrita é realizada.

### P2 — bases temporais diferentes no mesmo total

Diaristas usam início do evento; salários usam vencimento. O subtítulo atual
fala em “salários por competência”, embora o filtro efetivo seja vencimento.

Recomendação para a primeira fase: preservar os números atuais, documentar a
base em `meta` e no texto auxiliar. Uma mudança para dias trabalhados ou
competência é uma fase separada, pois pode alterar totais históricos.

### P2 — vínculo histórico pode ser misturado no mesmo grupo

Os grupos são indexados apenas por `serverReferenceId`. Se uma pessoa mudou de
diarista para mensalista dentro de um período amplo, participações de vínculos
diferentes e salário podem cair no mesmo grupo. O `linkType` exibido vem do
primeiro item processado, podendo esconder subtotal ou usar o rótulo errado.

Recomendação: os totais globais devem ser calculados por natureza do custo, não
pelo rótulo do grupo. No detalhamento, representar os vínculos encontrados ou
separar subgrupos por vínculo sem duplicar a pessoa no contador de servidores.

### P2 — filtros incompatíveis não informam “não aplicável”

Evento, serviço e edição manual não possuem relação determinística com o salário
mensal. O código atual remove os salários, mas retorna zero. Não se deve inventar
uma atribuição para preencher o card.

Recomendação: retornar `notApplicable` com motivo explícito. Enquanto não houver
apropriação implementada, o total completo da equipe também deve ficar
indisponível nesses recortes, salvo quando o filtro de vínculo limitar
explicitamente o relatório a diaristas.

### P2 — status “real” é usado para valor previsto

Os campos `financialRealCost` das ocorrências salariais recebem
`valor_previsto`. Isso pode induzir manutenção futura a tratar previsão como
realização.

Recomendação: usar nomes de contrato que expressem a base, como
`plannedSalaryAmount`, e reservar “pago/realizado” para `valor_pago` ou para a
modelagem financeira canônica correspondente.

### P2 — relatório histórico depende do estado atual

Os filtros ativo/inativo usam o estado atual do servidor. Alterar o cadastro
hoje pode mudar a composição de um relatório de meses anteriores.

Recomendação: manter esse comportamento apenas se o filtro for claramente
rotulado “Situação atual”. Caso a intenção seja situação no período, será
necessário snapshot histórico e uma mudança separada.

### P2 — detalhamento de serviços pode ficar vazio ou incompleto

O grupo coleta serviços somente das participações encontradas no período. Um
mensalista que aparece apenas por salário materializado terá `services=[]`,
embora possua serviços cadastrados.

Recomendação: renomear o bloco para **Serviços nos eventos do período** ou
ocultá-lo quando não houver participações. Não preencher com vínculos atuais
como se fossem evidência histórica.

### P2 — mocks de frontend contêm totais internamente inconsistentes

Em `rhsaasfront/tests/e2e/servers.spec.ts`, há fixture com duas participações de
eventos diferentes, ambas de `100.00`, mas `eventCount=1` e
`participationCostTotal/totalPeriod=100.00`. O teste verifica apresentação, mas
essa inconsistência pode mascarar erro de agregação no contrato.

Recomendação: criar builders de fixtures que calculem contagens e totais ou
validar invariantes antes de responder ao route mock.

Decisão tomada nesta entrega: a fixture diretamente afetada foi corrigida para
duas participações, dois eventos e total `200.00`. A criação de builders
reutilizáveis permanece uma melhoria de testes sem impacto no contrato atual.

### P2 — o OpenAPI gerou três nomes para o mesmo enum de estado

Achado durante a implementação: os campos de estado dos três cards usavam o
mesmo conjunto de valores, mas o `drf-spectacular` inicialmente gerou nomes de
enum distintos e emitiu `W001`. O schema era válido, porém clientes gerados
poderiam criar tipos duplicados para o mesmo conceito.

Decisão tomada nesta entrega: registrar `ServerCostStateEnum` em
`SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES` e cobrir por teste que os três campos
referenciam o mesmo componente canônico.

### P3 — nomes de origem divergentes

O item salarial usa `MATERIALIZED_SALARY_OCCURRENCE`, o `meta` usa
`materializedSalaryOccurrence` e fixtures antigas usam `salaryHistory`.

Recomendação: definir enum canônico e manter alias apenas durante a transição.

### P3 — filtros inválidos são geralmente ignorados

Datas inválidas retornam 400, mas ids/textos inválidos dos outros filtros podem
ser tratados como filtro vazio. Isso dificulta diagnóstico e pode produzir um
total mais amplo do que o solicitante imaginou.

Recomendação: validar todos os filtros no serializer de entrada e responder 400
para valores fora do contrato.

### P3 — guardrail agregado do dashboard bloqueado por rota fora deste diff

Achado durante os checks: `pnpm run check:dashboard` interrompe em
`check:financial-canonical` porque `app/dashboard/page.tsx` não consta na
allowlist do barrel financeiro. Nenhum arquivo dessa rota foi alterado nesta
entrega, portanto a correção seria externa ao escopo autorizado.

Decisão tomada nesta entrega: não modificar a rota nem a allowlist
silenciosamente. Os guardrails diretamente relevantes foram executados de forma
isolada: responsividade financeira, layout de filtros, acessibilidade e fronteira
de serviços passaram.

## Contrato recomendado da API

Fazer uma evolução aditiva primeiro. Manter `totalPeriod` por uma janela de
compatibilidade, mas não usá-lo nos novos cards.

Exemplo conceitual:

```json
{
  "summary": {
    "serverCount": 4,
    "eventCount": 7,
    "diaristCostTotal": "1800.00",
    "diaristCostState": "calculated",
    "monthlySalaryTotal": "6500.00",
    "monthlySalaryState": "calculated",
    "teamCostTotal": "8300.00",
    "teamCostState": "calculated",
    "totalPeriod": "8300.00"
  },
  "meta": {
    "diaristPeriodBasis": "eventStartDate",
    "salaryPeriodBasis": "dueDate",
    "salaryValueBasis": "plannedMaterializedAmount",
    "salaryCoverage": "complete"
  }
}
```

Estados mínimos recomendados:

- `calculated`: cálculo completo; zero é um valor válido;
- `restricted`: usuário não pode acessar o componente;
- `notApplicable`: filtros não permitem relacionar o componente ao recorte;
- `outOfFilter`: o vínculo foi explicitamente excluído pelo filtro;
- `incomplete`: há competência esperada ausente, bloqueada ou registro legado
  não correlacionável.

Motivos devem ser códigos estáveis, por exemplo:

- `SALARY_PERMISSION_REQUIRED`;
- `EVENT_SCOPE_REQUIRES_MONTHLY_ALLOCATION`;
- `SERVICE_SCOPE_REQUIRES_MONTHLY_ALLOCATION`;
- `PARTICIPATION_FILTER_NOT_APPLICABLE_TO_SALARY`;
- `SALARY_OCCURRENCE_MISSING`;
- `SALARY_OCCURRENCE_BLOCKED`;
- `LEGACY_SALARY_UNCORRELATED`;
- `SALARY_COVERAGE_PERIOD_EXCEEDS_LIMIT`.

Não incluir nomes nem valores salariais nos motivos de completude retornados a
usuários sem permissão.

## Matriz recomendada de apresentação

| Situação | Custo com diaristas | Salários de mensalistas | Custo total da equipe |
| --- | --- | --- | --- |
| sem filtros incompatíveis e cobertura completa | valor | valor | soma dos dois |
| salário calculado igual a zero | valor | `R$ 0,00` | soma dos dois |
| sem permissão salarial | valor | `Restrito` | `Restrito` |
| materialização salarial incompleta | valor | `Dados incompletos` | `Dados incompletos` |
| filtro de evento/serviço sem apropriação | valor do recorte | `Não aplicável` | `Não disponível` |
| filtro explícito `DIARISTA` | valor do recorte | `Fora do filtro` | mesmo valor, deixando claro que o total respeita o filtro |
| filtro explícito `MENSALISTA`, sem filtro incompatível | `Fora do filtro` | valor | mesmo valor |

O frontend deve usar os estados recebidos do backend. Não deve deduzir estado a
partir de `null`, `0`, lista vazia ou permissão isoladamente.

## Plano de implementação

### Fase 0 — decisões antes de codificar

- [x] Confirmar se “Salários de mensalistas” significa previsto materializado,
  pago ou ambos em cards diferentes.
- [x] Confirmar se a primeira fase preservará vencimento como base do período.
- [x] Confirmar que cancelados e inativos ficam fora do subtotal principal.
- [x] Definir a janela de compatibilidade de `totalPeriod`.
- [x] Definir a apresentação de estado restrito/incompleto/não aplicável.

Decisão final: usar previsto materializado, vencimento no período, excluir
cancelados/inativos e explicar isso no card. `totalPeriod` permanece como
subtotal numérico legado durante esta primeira evolução, mas os novos cards não
dependem dele.

### Fase 1 — contrato e cálculo explícitos no backend

- [x] Criar testes de caracterização antes de alterar o selector.
- [x] Calcular `diaristCostTotal` diretamente pela natureza da participação.
- [x] Calcular `monthlySalaryTotal` diretamente pelas ocorrências válidas.
- [x] Calcular `teamCostTotal` apenas quando o subtotal salarial estiver
  disponível e completo.
- [x] Adicionar estados, motivos e metadados de base.
- [x] Excluir ocorrências canceladas/inativas conforme a decisão da Fase 0.
- [x] Tratar custos salariais legados sem erro 500 e sem associação heurística.
- [x] Detectar materialização ausente/bloqueada sem projetar valor no total.
- [x] Preservar `totalPeriod` temporariamente.
- [x] Atualizar serializers e OpenAPI.

Os três cards, isoladamente, não exigem migration.

### Fase 2 — frontend

- [x] Atualizar os tipos de `ServerCostsResponse`.
- [x] Manter **Servidores** e **Eventos**.
- [x] Substituir **Custo no período** e **Apropriação gerencial** pelos três
  cards definidos neste documento.
- [x] Exibir texto auxiliar da base prevista/materializada e do período.
- [x] Exibir estado sem converter indisponibilidade em `R$ 0,00`.
- [x] Não renderizar valor salarial nem total inferível sem permissão.
- [x] Revisar o cabeçalho de cada servidor para mostrar total coerente ou estado.
- [x] Renomear/ocultar “Serviços” quando não houver participações no período.
- [x] Manter layout responsivo com cinco métricas no total.

### Fase 3 — consistência histórica e filtros

- [ ] Validar filtros por serializer de entrada.
- [ ] Tornar a base de cada filtro observável na resposta.
- [ ] Decidir se o período de diaristas continuará pelo início do evento ou será
  atribuído às datas trabalhadas.
- [ ] Resolver a apresentação de mudança de vínculo no mesmo período.
- [ ] Definir se “ativo/inativo” significa situação atual ou situação histórica.

Mudanças de base temporal devem ser entregues separadamente, com comparação de
totais antes/depois.

### Fase 4 — futura apropriação de mensalistas nos eventos

Nome de produto recomendado: **Custo de mensalistas nos eventos** ou
**Salários alocados aos eventos**.

Fórmula conceitual:

```text
custo-hora mensal = custo mensal considerado / jornada mensal contratada
custo no evento = custo-hora mensal × horas aprovadas no evento
```

Requisitos antes de implementar:

- [ ] definir o que compõe o custo mensal: salário ou salário + encargos;
- [ ] cadastrar jornada/carga horária com vigência histórica;
- [ ] definir tratamento de férias, afastamentos e mês parcial;
- [ ] usar horas efetivamente registradas/aprovadas no evento;
- [ ] materializar snapshots da regra, jornada e valor usados;
- [ ] mostrar custo não alocado/ociosidade, sem forçar 100% do salário nos
  eventos;
- [ ] garantir que a apropriação seja somente analítica;
- [ ] garantir que ela nunca seja somada novamente ao custo total da equipe.

Esta fase provavelmente exige migration, pois a jornada contratada não existe
no modelo atual. Não reutilizar o padrão de 8 horas de uma participação.

## Matriz mínima de testes

### Backend — unidade/selector

- [x] somente diarista;
- [x] somente mensalista com ocorrência materializada;
- [x] combinação de ambos e invariante da soma;
- [x] valor zero calculado versus estado indisponível;
- [x] salário pendente, parcial, pago, cancelado e inativo;
- [x] competência ausente e configuração necessária ausente;
- [x] salário legado sem competência/histórico/servidor;
- [ ] servidor excluído com snapshots;
- [ ] servidor que mudou de vínculo no período;
- [ ] evento iniciado fora do período com dias trabalhados dentro;
- [x] filtros de vínculo, evento, serviço e edição, inclusive combinação;
- [ ] valores manuais de diaristas;
- [ ] mês parcial sem rateio automático;
- [ ] arredondamento monetário e soma de muitas linhas;
- [ ] quantidade de queries constante para volumes maiores.
- [x] período superior a 120 meses não executa varredura mensal ilimitada.

### Backend — API e segurança

- [ ] 401, 403 e permissão de custos;
- [x] com e sem permissão salarial;
- [x] impossibilidade de inferir salário por diferença;
- [ ] permissão de apropriação independente;
- [ ] estados e motivos sem conteúdo sensível;
- [ ] validação 400 de cada filtro inválido;
- [x] schema OpenAPI atualizado com enum canônico;
- [x] isolamento entre dois tenants com salários sentinela distintos.

### Frontend

- [x] os três cards usam exclusivamente os valores/estados do backend;
- [x] `R$ 0,00` somente quando o estado for `calculated`;
- [x] estados restrito, incompleto, não aplicável e fora do filtro;
- [x] cinco métricas em desktop e telas estreitas;
- [ ] filtros e atualização durante carregamento;
- [x] salário nunca aparece sem permissão;
- [x] total não permite inferir salário restrito;
- [ ] detalhamento de diarista, mensalista, excluído e mudança de vínculo;
- [x] fixture diretamente relacionada corrigida para contagens e totais consistentes;
- [ ] E2E com backend real para pelo menos um cenário misto.

### Regressão financeira

- [x] nenhum `CustoFixo`, lançamento, obrigação ou pagamento é criado ao abrir o
  relatório;
- [x] nenhuma participação é alterada ao abrir ou filtrar o relatório;
- [x] salário não é contado como participação de mensalista;
- [ ] apropriação futura não altera caixa nem o total da equipe;
- [x] `totalPeriod` e novos totais são comparados nos testes de compatibilidade da
  primeira entrega; comparações de produção permanecem parte do rollout, não
  desta implementação local.

## Critérios de aceite da primeira entrega

1. A tela mostra **Custo com diaristas**, **Salários de mensalistas** e
   **Custo total da equipe**.
2. Cada número pode ser explicado por registros identificáveis e pela base
   declarada na resposta.
3. O total da equipe satisfaz a fórmula e não inclui apropriação.
4. Nenhum estado ausente/restrito/incompleto aparece como zero.
5. Filtros incompatíveis não produzem um falso total completo.
6. Usuário sem permissão salarial não vê nem infere salário.
7. Ocorrência cancelada/inativa não entra no subtotal principal, conforme
   decisão registrada.
8. Dados legados não causam erro 500 nem são associados por heurística.
9. Nenhum comportamento de escrita ou materialização é acionado pela consulta.
10. Testes de tenant comprovam ausência de vazamento entre schemas.
11. OpenAPI, tipos TypeScript e fixtures refletem o mesmo contrato.
12. A entrega informa explicitamente se houve migration; para a divisão inicial
    dos cards, a expectativa é **não haver migration**.

## Arquivos provavelmente envolvidos na implementação futura

Backend:

- `caixa/selectors_custos_servidores.py`;
- `caixa/views_custos_servidores_api.py`;
- `caixa/serializers_custos_servidores.py`;
- `caixa/security_salarios.py`;
- `caixa/test_servidores.py`;
- eventualmente `caixa/test_custos_recorrentes.py`.

Frontend:

- `rhsaasfront/features/financial-dashboard/components/financial-server-costs-view.tsx`;
- `rhsaasfront/lib/types/servers.ts`;
- `rhsaasfront/tests/e2e/servers.spec.ts`;
- preferencialmente novos testes unitários para a apresentação dos estados.

Para a apropriação futura, também serão envolvidos os modelos, serviços,
migrations e formulários de cadastro de mensalistas.

## Decisões fechadas

Não há decisão funcional pendente para a primeira evolução. Alterações futuras
nas bases financeira ou temporal exigem nova decisão registrada neste arquivo.

| ID | Decisão final | Estado |
| --- | --- | --- |
| D01 | Usar `valor_previsto` das ocorrências salariais materializadas; pagamentos realizados pertencem a outra métrica. | fechada |
| D02 | Usar `data_vencimento`; descrever “Salários previstos materializados com vencimento no período”. | fechada |
| D03 | Excluir `status=cancelado` e `ativo=false`; manter pendentes, parciais e pagas pelo previsto. | fechada |
| D04 | Preservar diaristas pela data de início do evento nesta entrega. | fechada |
| D05 | Evento, serviço ou valor editado tornam salário não aplicável e total indisponível, sem rateio; `DIARISTA` explícito continua sendo exceção calculável. | fechada |
| D06 | Apropriação futura exigirá carga horária mensal contratada, com vigência histórica e sem padrão. | fechada para esta evolução |
| D07 | Considerar somente salário materializado; encargos só entram quando cadastrados explicitamente. | fechada para esta evolução |

### Regras semânticas fechadas

- sem permissão salarial: salário e total da equipe ficam `restricted`; diaristas
  continuam calculados;
- ocorrência salarial esperada e ausente: salário e total ficam `incomplete`;
- mensalista ativo com salário cadastrado, mas sem configuração necessária para
  materialização: salário e total ficam `incomplete`;
- filtro explícito `DIARISTA`: salário fica `outOfFilter` e o total é igual ao
  custo dos diaristas;
- filtro explícito `MENSALISTA`, sem filtro incompatível: diaristas ficam
  `outOfFilter` e o total acompanha o salário materializado;
- em `MENSALISTA`, o total herda `restricted`, `incomplete` ou `notApplicable`
  do salário e nunca fabrica zero;
- evento, serviço ou valor editado: salário fica `notApplicable` e o total é
  exibido como “Não disponível”, exceto no recorte explícito `DIARISTA`;
- `0.00` só representa zero realmente calculado;
- o card de apropriação permanece oculto;
- `totalPeriod` é compatibilidade temporária e não alimenta os novos cards.

## Histórico de atualização

| Data | Alteração | Evidência/resultado |
| --- | --- | --- |
| 2026-08-09 | levantamento inicial criado | mapeados cadastro de mensalista, materialização, selector, API, permissões, frontend e testes relacionados |
| 2026-08-09 | D01–D07 e regras semânticas fechadas | contrato autorizado para a primeira evolução, sem rateio salarial nem mudança de bases históricas |
| 2026-08-09 | limite defensivo da cobertura e fixture E2E corrigida | novo achado P1 limitado a 120 meses; contagens e totais do mock responsivo alinhados |
| 2026-08-09 | enum OpenAPI consolidado | achado P2 resolvido com `ServerCostStateEnum` canônico e teste de contrato |
| 2026-08-09 | guardrail agregado documentado | achado P3 externo ao diff mantido fora do escopo; quatro checks relevantes passaram isoladamente |
| 2026-08-09 | primeira evolução implementada e revisada | contrato aditivo no backend, três cards no frontend, testes direcionados verdes e nenhuma migration gerada |
