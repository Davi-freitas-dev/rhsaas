# Melhorias e proximos passos

Atualizado em: 2026-06-01

> Aviso RH SaaS: este arquivo e historico do projeto antigo e nao deve ser usado
> como roteiro de deploy, dominio, banco ou configuracao do RH SaaS. Use os
> documentos atuais em `docs/` e os exemplos `.env*.example`.

Este arquivo registra as melhorias aplicadas no ciclo atual e os proximos passos recomendados para continuar deixando a aplicacao mais segura, performatica e escalavel.

Para a conclusao da arquitetura financeira premium/canonical-first, o roteiro oficial e o `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md`, secao `Plano mestre para conclusao da arquitetura premium`. Este arquivo permanece como historico e apoio operacional; em retomadas, consultar primeiro o plano mestre.

## Atualizacao - PM-06.1212 gate de base limpa manual

- Adicionado `validar_prontidao_base_limpa_pm06`, gate read-only especifico
  para a estrategia de base limpa com recadastro manual.
- O gate exige preparacao PM-06 com backup/preflight, recadastro manual aprovado
  e comparado com a base atual, rollback/conciliacao aprovado, relatorio atual,
  aceite operacional, tres revisoes e liberacao explicita.
- A decisao aprovada libera apenas prontidao operacional para recadastro manual;
  limpeza de producao, restauracao automatica e migrations de limpeza seguem
  bloqueadas.

## Atualizacao - PM-06.1211 evidencias JSON com BOM

- Os gates `validar_preparacao_pm06`, `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` passaram a aceitar evidencias JSON
  em UTF-8 com BOM (`utf-8-sig`), comum em arquivos gerados no Windows.
- A validacao local de preparacao PM-06 com backup, auditoria e preflight foi
  repetida com sucesso apos esse ajuste.

## Atualizacao - PM-06.1210 recadastro comparado com base atual

- `validar_recadastro_manual_pm06` ganhou `--comparar-base-atual`, que monta um
  pacote read-only da base atual e compara `summary` e `outOfManualScope` com o
  JSON exportado.
- O gate bloqueia pacote desatualizado, por exemplo quando clientes, orcamentos,
  eventos, custos ou FCF mudarem depois da exportacao.
- `validar_prontidao_migracao_limpeza_pm06 --exigir-recadastro-manual` agora
  exige evidencia de recadastro manual ja comparada com a base atual e sem
  divergencias.

## Atualizacao - PM-06.1209 fechamento recomenda recadastro validado

- `validar_fechamento_pm06` passou a recomendar explicitamente a exportacao e
  validacao do recadastro manual quando o caminho de base limpa for usado.
- A recomendacao de prontidao de migration/limpeza ja inclui
  `--recadastro-manual-json` e `--exigir-recadastro-manual`, mantendo a logica
  do fechamento compatível com fluxos antigos.

## Atualizacao - PM-06.1208 recadastro manual no gate de limpeza

- `validar_prontidao_migracao_limpeza_pm06` agora aceita
  `--recadastro-manual-json` e pode exigir essa evidencia com
  `--exigir-recadastro-manual` no caminho de base limpa.
- A evidencia exigida deve vir de `validar_recadastro_manual_pm06`, estar
  aprovada, ser read-only, liberar apenas recadastro manual e manter limpeza de
  dados/restauracao automatica bloqueadas.
- O comando antigo permanece compativel quando a flag de recadastro manual nao
  e usada, mas a recomendacao do gate ja mostra o fluxo completo para base
  limpa.

## Atualizacao - PM-06.1207 validacao do recadastro manual

- Adicionado o comando `validar_recadastro_manual_pm06`, que valida de forma
  read-only o JSON `pm06-recadastro-manual.json` ou um pacote montado em memoria
  a partir da base atual.
- O gate confere identidade, politica, secoes obrigatorias, consistencia das
  contagens, orcamentos, eventos, FCF e itens fora do pacote manual.
- A decisao aprovada libera apenas o uso do pacote como guia de recadastro
  manual; limpeza de dados e restauracao automatica continuam explicitamente
  bloqueadas.

## Atualizacao - PM-06.1206 orcamentos no recadastro manual

- O comando `exportar_recadastro_manual_pm06` agora inclui orcamentos no pacote
  read-only de recadastro em base limpa, com itens, custos extras de orcamento,
  totais e vinculo ao evento aprovado quando existir.
- O resumo JSON/Markdown passou a expor contagens e totais de orcamentos para
  conferencia manual antes/depois da limpeza.
- A checklist deixa explicito que orcamentos devem ser recriados e aprovados
  apenas quando o evento correspondente ainda nao existir na base limpa,
  reduzindo risco de duplicar eventos/custos.

## Atualizacao - PM-06.1202 pacote de recadastro manual em base limpa

- Adicionado o comando `exportar_recadastro_manual_pm06`, que gera JSON e
  Markdown read-only para recadastrar manualmente clientes, contratos, eventos,
  custos por evento, custos extras, custos fixos e FCF em uma base limpa.
- A estrategia preserva todo o codigo e as protecoes ja implementadas na PM-06,
  separando backup bruto completo para rollback de emergencia do pacote
  canonico usado como guia de recadastro.
- O pacote declara explicitamente que obrigacoes, lancamentos, baixas,
  despesas/receitas derivadas e totais salvos nao entram como fonte primaria e
  devem ser recalculados/sincronizados pelo sistema novo.
- Custo extra de orcamento aprovado com pagamento agora e preservado ao remover
  a origem do orcamento: a copia do evento zera o previsto, mantem o realizado e
  nao deixa pendencia negativa/falsa.

## Atualizacao - PM-06.1201 datas validas em references rollback

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora validam
  `references.windowStart/windowEnd` da evidencia de rollback/conciliacao como
  datas ISO reais e ordenadas.
- O downstream bloqueia `references` com datas impossiveis ou invertidas mesmo
  quando o bloco `window` nao estiver presente.
- A regra permanece compatível com artefatos antigos sem `references` e nao
  executa rollback/conciliacao.

## Atualizacao - PM-06.1200 janela consistente com references

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora exigem
  `windowStart/windowEnd` em `references` quando esse bloco existir na
  evidencia de rollback/conciliacao.
- Quando `window` e `references` coexistem, os gates bloqueiam divergencia de
  referencia, inicio ou fim da janela.
- A regra impede evidencia manual contraditoria e preserva compatibilidade com
  artefatos antigos sem esses blocos.

## Atualizacao - PM-06.1199 planFiles consistente com references

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora comparam `planFiles` com
  `references` da evidencia de rollback/conciliacao quando ambos existem.
- O downstream bloqueia divergencia entre rollback, conciliacao ou politica de
  dados delta declarados nos dois blocos.
- A regra impede evidencia manual contraditoria e continua compativel com
  artefatos antigos sem os blocos novos.

## Atualizacao - PM-06.1198 references de rollback no downstream

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora validam `references` da
  evidencia de rollback/conciliacao quando o bloco estiver presente.
- Fechamento e migration de limpeza bloqueiam evidencia aprovada que declare
  backup, janela, planos, responsavel, homologacao, aceite ou revisoes finais
  ausentes.
- Artefatos antigos sem `references` seguem aceitos por compatibilidade; a
  validacao continua read-only.

## Atualizacao - PM-06.1197 planFiles validado no downstream

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora validam `planFiles` da
  evidencia de rollback/conciliacao quando o bloco estiver presente.
- Fechamento e migration de limpeza bloqueiam JSON aprovado que declare
  rollback, conciliacao ou politica de dados delta vazios dentro de
  `planFiles`.
- Artefatos antigos sem `planFiles` seguem aceitos por compatibilidade.

## Atualizacao - PM-06.1196 evidencia nao sobrescreve planos

- `validar_rollback_conciliacao_pm06` agora registra os arquivos de plano em
  `planFiles` e bloqueia saida de evidencia que aponte para o mesmo caminho.
- O comando impede que `--salvar-json` ou `--salvar-registro` sobrescrevam
  rollback, conciliacao ou politica de dados delta usados como entrada.
- Regressao confirma que o plano original permanece intacto quando a saida e
  recusada.

## Atualizacao - PM-06.1195 rollback com data invalida controlada

- `validar_rollback_conciliacao_pm06` agora trata datas ISO impossiveis, como
  mes ou dia fora do calendario, como pendencia do gate em vez de erro de
  execucao.
- O JSON gerado marca `startValid/endValid=False` e reporta
  `janela-inicio invalido`/`janela-fim invalido`.
- O comando continua read-only e nao executa rollback, conciliacao ou qualquer
  alteracao de dados.

## Atualizacao - PM-06.1194 datas reais na janela rollback/conciliacao

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora conferem se `window.start`
  e `window.end` da evidencia de rollback/conciliacao sao datas ISO validas
  quando o bloco `window` estiver presente.
- Os gates tambem recalculam se inicio e fim estao ordenados, bloqueando JSON
  manual que marque `ordered=True` com datas invertidas.
- Datas invalidas viram pendencia controlada, nao erro de execucao; nenhuma
  rotina de rollback ou conciliacao e executada.

## Atualizacao - PM-06.1193 freezeScope protegido no downstream

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora validam `freezeScope` da
  evidencia de congelamento legado quando o bloco estiver presente.
- O escopo precisa manter `removeOnlyInVersion=financeiro-v3`, contrato atual
  diferente da versao de remocao e regra de aliases preenchida.
- A validacao impede congelamento aprovado com escopo contraditorio, sem
  congelar escrita nem criar/aplicar migrations.

## Atualizacao - PM-06.1192 politica financeiro-v3 no gate de limpeza

- `validar_prontidao_migracao_limpeza_pm06` agora valida
  `financeiroV3Policy` do JSON de fechamento quando esse bloco estiver
  presente.
- O gate bloqueia fechamento aprovado que declare versao de corte diferente de
  `financeiro-v3`, contrato atual ja na versao de remocao de aliases ou regra
  de preservacao ausente.
- Artefatos antigos sem o bloco seguem aceitos por compatibilidade; a regra nao
  cria nem aplica migrations de limpeza.

## Atualizacao - PM-06.1191 congelamento com evidencia frontend canonica

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora validam
  `references.frontendValidationRef` e `frontendCanonicalValidationPolicy` da
  evidencia de congelamento legado quando esses blocos estiverem presentes.
- A regra bloqueia JSON de congelamento `ready=True` que declare validacao
  frontend generica ou politica sem `financial-canonical`/`financeiro-v3`.
- Artefatos antigos sem esses blocos seguem aceitos por compatibilidade; a
  mudanca nao executa congelamento real.

## Atualizacao - PM-06.1190 politica frontend canonica explicita

- `validar_fechamento_pm06`, `validar_prontidao_congelamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora publicam no JSON/registro a
  politica de validacao frontend canonica aceita pela PM-06.
- O gate de migration de limpeza valida essa politica quando o fechamento novo
  a declarar, bloqueando politica generica sem `financial-canonical` ou corte
  de aliases diferente de `financeiro-v3`.
- A mudanca e read-only: nao congela escrita, nao cria/aplica migration, nao
  executa rollback/conciliacao e nao remove aliases publicados.

## Atualizacao - PM-06.1189 evidencia frontend canonica no gate de limpeza

- `validar_prontidao_migracao_limpeza_pm06` agora valida
  `references.frontendValidationRef` do fechamento PM-06 quando esse bloco
  estiver presente.
- Fechamentos novos que carreguem `references` precisam comprovar
  `verify:publish` ou `check:financial-canonical`; artefatos antigos sem
  `references` seguem aceitos por compatibilidade.
- Regressao direta adicionada no validador de fechamento consumido pelo gate de
  migration de limpeza.

## Atualizacao - PM-06.1188 evidencia frontend canonica no gate

- `validar_fechamento_pm06` e `validar_prontidao_congelamento_pm06` agora
  rejeitam `frontend-validacao-ref` generico que nao cite `verify:publish`,
  `verify-publish`, `check:financial-canonical` ou marcador equivalente.
- A mudanca amarra a decisao PM-06.1187 ao gate final: a validacao frontend
  precisa comprovar o guardrail canonico, nao apenas um smoke textual.
- Regressao direta adicionada para referencia generica bloqueada e referencias
  canonicas aceitas.

## Atualizacao - PM-06.1187 Next.js canonico com aliases preservados

- Decisao operacional segura: a PM-06 fecha o item de Next.js com campos
  canonicos priorizados nos fluxos principais e aliases legados preservados
  somente nas bordas de compatibilidade ate o corte `financeiro-v3`.
- O guardrail frontend `check:financial-canonical` passou a vigiar
  `costCenterId` e `saldo_em_aberto` como aliases de transicao obrigatorios,
  alem de exigir que arquivos liberados para aliases sejam services, utils,
  tipos ou mocks de contrato.
- Nenhum alias publicado foi removido e nenhum corte `financeiro-v3` foi
  iniciado nesta decisao.

## Atualizacao - PM-06.1186 redirects com ambiente recomendado valido

- `validar_fechamento_pm06` agora valida `activation.recommendedEnvironment`
  quando o bloco estiver presente na evidencia de redirects.
- O ambiente recomendado precisa trazer URL do frontend, redirects ligados
  (`NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True`) e allowlist nao vazia.
- Regressao direta adicionada no validador de redirects do fechamento PM-06.

## Atualizacao - PM-06.1185 redirects com allowlist recomendada

- `validar_fechamento_pm06` agora rejeita evidencia de redirects que declare
  `activation.recommendedSurfacesValue` vazio.
- Campo ausente segue aceito por compatibilidade, mas allowlist recomendada
  declarada sem superficie bloqueia o fechamento.
- Regressao direta adicionada no validador de redirects do fechamento PM-06.

## Atualizacao - PM-06.1184 redirects com ativacao pronta

- `validar_fechamento_pm06` agora rejeita evidencia de redirects que declare
  `activation.readyToActivate=False`.
- Campo ausente segue aceito por compatibilidade, mas contradicao explicita
  entre `ready=True` e ativacao nao pronta bloqueia o fechamento.
- Regressao direta adicionada no validador de redirects do fechamento PM-06.

## Atualizacao - PM-06.1183 redirects com superficies identificadas

- `validar_fechamento_pm06` agora rejeita item malformado dentro de
  `surfaces`: cada superficie precisa ser objeto JSON e trazer chave `surface`
  preenchida.
- A regra impede evidencia manual baseada em lista de strings ou objetos vazios,
  mantendo compativel o formato publicado por `validar_redirects_next_legado`.
- Regressao direta adicionada no validador de redirects do fechamento PM-06.

## Atualizacao - PM-06.1182 redirects com superficies declaradas

- `validar_fechamento_pm06` agora rejeita evidencia de redirects cujo campo
  `surfaces` exista como lista vazia.
- O fechamento final continua exigindo rollback de redirects, mas agora tambem
  impede pacote `ready=True` sem nenhuma superficie migrada declarada.
- Regressao direta adicionada no validador de redirects do fechamento PM-06.

## Atualizacao - PM-06.1181 janela rollback/conciliacao identificada

- `validar_fechamento_pm06` e `validar_prontidao_migracao_limpeza_pm06`
  agora rejeitam evidencia de rollback/conciliacao cujo bloco `window` esteja
  presente sem `ref`, `start` ou `end` preenchidos.
- A validacao downstream passa a conferir o contrato completo do bloco
  `window`: referencia, inicio, fim, flags de validade e ordenacao.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1180 janela rollback/conciliacao com datas validas

- `validar_fechamento_pm06` e `validar_prontidao_migracao_limpeza_pm06`
  agora rejeitam evidencia de rollback/conciliacao cujo bloco `window` esteja
  presente sem `startValid=True` ou `endValid=True`.
- O bloco `window` continua opcional por compatibilidade com artefatos antigos,
  mas, quando declarado, precisa carregar inicio, fim e ordenacao validos.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1179 janela rollback/conciliacao ordenada

- `validar_fechamento_pm06` e `validar_prontidao_migracao_limpeza_pm06`
  agora rejeitam evidencia de rollback/conciliacao cujo bloco `window` esteja
  presente sem `ordered=True`.
- Artefatos antigos sem `window` seguem aceitos por compatibilidade, mas
  janela declarada nao ordenada bloqueia os gates finais.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1178 closureNextAction pronta

- `validar_prontidao_migracao_limpeza_pm06` agora valida `closureNextAction`
  quando presente no fechamento PM-06.
- A acao explicita precisa usar `key=advanceToPm07`, `status=ready`,
  `mayAdvanceSequence=True` e `mayStartNextStep=True`; campos ausentes seguem
  aceitos por compatibilidade.
- Regressao direta adicionada para acao de fechamento ainda bloqueada.

## Atualizacao - PM-06.1177 closureNextAction do fechamento

- `validar_prontidao_migracao_limpeza_pm06` agora rejeita evidencia de
  fechamento PM-06 cujo `closureNextAction.nextStep` explicito seja diferente
  de `PM-07`.
- A validacao mantem compatibilidade com artefatos sem `closureNextAction`, mas
  bloqueia acao contraditoria quando o campo existir.
- Regressao direta adicionada no validador de fechamento consumido pelo gate de
  migration de limpeza.

## Atualizacao - PM-06.1176 conclusao da PM-06 no fechamento

- `validar_prontidao_migracao_limpeza_pm06` agora rejeita evidencia de
  fechamento cujo `closureDecision.mayMarkCurrentStepDone` explicito seja
  diferente de `True`.
- A validacao mantem compatibilidade com artefatos sem esse campo, mas bloqueia
  fechamento que declare nao marcar a PM-06 como concluida.
- Regressao direta adicionada no validador de fechamento consumido pelo gate de
  migration de limpeza.

## Atualizacao - PM-06.1175 nextStep do fechamento

- `validar_prontidao_migracao_limpeza_pm06` agora rejeita evidencia de
  fechamento PM-06 cujo `closureDecision.nextStep` explicito seja diferente de
  `PM-07`.
- A validacao mantem compatibilidade com artefatos sem `nextStep`, mas bloqueia
  divergencia declarada.
- Regressao direta adicionada no validador de fechamento consumido pelo gate de
  migration de limpeza.

## Atualizacao - PM-06.1174 step das decisoes

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora rejeitam decisoes finais que
  tragam `step` diferente de `PM-06`.
- A validacao permite `step` ausente por compatibilidade com artefatos antigos,
  mas bloqueia divergencia explicita.
- Regressao direta adicionada para fechamento, congelamento e
  rollback/conciliacao.

## Atualizacao - PM-06.1173 decisoes malformadas

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora rejeitam decisoes finais que
  nao sejam objetos JSON.
- A validacao transforma `closureDecision`, `freezeDecision` ou
  `rollbackConciliationDecision` malformados em pendencia controlada, sem erro
  inesperado no comando.
- Regressao direta adicionada para fechamento, congelamento e
  rollback/conciliacao.

## Atualizacao - PM-06.1172 decisoes sem blockedBy

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora rejeitam decisoes aprovadas
  que ainda carreguem `blockedBy`.
- O gate aceita `blockedBy` ausente ou vazio, mas bloqueia lista preenchida ou
  formato invalido.
- Regressao direta adicionada para fechamento, congelamento e
  rollback/conciliacao.

## Atualizacao - PM-06.1171 contadores do checksSummary

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora comparam `checksSummary`
  com a lista real de `checks` quando ambos existem.
- O gate bloqueia `total` e `okCount` divergentes, mesmo se `ready=True` e os
  checks internos estiverem aprovados.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1170 issues internas dos checks

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora rejeitam checks internos que
  tenham `issues` preenchido, mesmo quando o check declara `ok=True`.
- O gate tambem bloqueia `issues` de check em formato diferente de lista.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1169 checks internos consistentes

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora validam a lista `checks`
  quando ela estiver presente nos JSONs de entrada.
- O gate bloqueia `checks` que nao seja lista, item que nao seja objeto ou
  qualquer check interno com `ok` diferente de `True`.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1168 checksSummary estruturado

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora tratam `checksSummary` como
  parte estrutural da evidencia quando ele estiver presente.
- O gate bloqueia `checksSummary.ready` diferente de `True`, `pending` que nao
  seja lista, `pendingCount` nao zerado e `issueCount` nao zerado.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1167 issues estruturado

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora rejeitam evidencia de
  entrada que declare `ready=True` sem `issues` em formato de lista.
- A validacao evita aceitar JSON manual ou inconsistente que esconda pendencia
  em texto livre.
- Regressao direta adicionada nos dois validadores PM-06.

## Atualizacao - PM-06.1166 checksSummary consistente

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora rejeitam evidencia de
  entrada com `ready=True` quando `checksSummary` ainda aponta pendencia.
- O bloqueio cobre `checksSummary.ready=False`, lista `pending` preenchida ou
  `pendingCount` diferente de zero.
- Regressao adicionada para fechamento final e migration de limpeza.

## Atualizacao - PM-06.1165 decisoes aprovadas nos JSONs finais

- `validar_fechamento_pm06` agora rejeita evidencias de congelamento legado e
  rollback/conciliacao sem decisao `status=approved`.
- `validar_prontidao_migracao_limpeza_pm06` exige fechamento, congelamento e
  rollback/conciliacao explicitamente aprovados, alem das flags read-only ja
  validadas.
- Regressao adicionada para bloquear JSON `ready=True` com flags liberadas,
  mas decisao marcada como `blocked`.

## Atualizacao - PM-06.1164 entradas com extensao JSON

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora exigem extensao `.json` nas
  evidencias de entrada.
- O bloqueio acontece em `inputEvidenceFiles`, mesmo quando o conteudo do
  arquivo com extensao errada e JSON valido.
- Regressao adicionada para fechamento final e migration de limpeza.

## Atualizacao - PM-06.1163 evidencias de entrada distintas

- `validar_fechamento_pm06` e
  `validar_prontidao_migracao_limpeza_pm06` agora bloqueiam quando duas
  evidencias de entrada apontam para o mesmo arquivo.
- O novo check `inputEvidenceFiles` evita pacote ambíguo antes de validar a
  identidade individual dos JSONs.
- Regressao adicionada para fechamento final e migration de limpeza.

## Atualizacao - PM-06.1162 saida nao sobrescreve evidencia de entrada

- O fechamento final e o gate de migration de limpeza agora bloqueiam
  `--salvar-json` ou `--salvar-registro` quando o caminho coincide com uma
  evidencia de entrada carregada pelo proprio gate.
- O salvamento so grava artefatos quando `outputEvidenceFiles` esta valido,
  evitando sobrescrever JSONs usados como prova.
- Regressao adicionada para preservar o conteudo original de
  `pm06-validacao-backup-rollback.json` e `pm06-fechamento.json` em caso de
  conflito.

## Atualizacao - PM-06.1161 extensoes de evidencia

- Os quatro gates finais PM-06 agora exigem `--salvar-json` com extensao
  `.json` e `--salvar-registro` com extensao `.md` ou `.markdown`.
- O salvamento ignora destinos com extensao invalida, mantendo o gate
  bloqueado em `outputEvidenceFiles`.
- Regressao adicionada no gate de rollback/conciliacao para cobrir caminhos
  distintos com extensoes incorretas.

## Atualizacao - PM-06.1160 JSON e markdown em caminhos distintos

- Os quatro gates finais PM-06 agora bloqueiam `--salvar-json` e
  `--salvar-registro` apontando para o mesmo caminho.
- O salvamento tambem ignora esse destino invalido, evitando sobrescrever o
  JSON com o markdown ou o inverso.
- Regressao ampliada nos gates de fechamento, congelamento, rollback/
  conciliacao e migration de limpeza.

## Atualizacao - PM-06.1159 pai invalido em evidencia

- Adicionada regressao para confirmar que o gate de rollback/conciliacao
  bloqueia `--salvar-json` e `--salvar-registro` quando o diretorio pai do
  arquivo informado ja existe como arquivo comum.
- O bloqueio retorna pendencia em `outputEvidenceFiles` sem tentar criar
  diretorio sobre arquivo existente.

## Atualizacao - PM-06.1158 destino de evidencia como diretorio

- Os quatro gates finais PM-06 agora validam se `--salvar-json` e
  `--salvar-registro` apontam acidentalmente para diretorios ou para pai
  invalido.
- Quando isso acontece, o comando retorna bloqueio auditavel em
  `outputEvidenceFiles` e nao tenta escrever sobre o diretorio informado.
- Regressao ampliada nos gates de fechamento, congelamento, rollback/
  conciliacao e migration de limpeza.

## Atualizacao - PM-06.1157 evidencia persistida no fechamento final

- Adicionada regressao para confirmar que
  `validar_fechamento_pm06 --exigir-arquivos-evidencia` bloqueia o fechamento
  quando JSON e markdown do proprio gate nao foram definidos.
- Mesmo com todas as evidencias finais validas e `--liberar-pm07`, a PM-07
  continua bloqueada sem artefatos persistidos do fechamento.

## Atualizacao - PM-06.1156 evidencia persistida na migration de limpeza

- Adicionada regressao para confirmar que
  `validar_prontidao_migracao_limpeza_pm06 --exigir-arquivos-evidencia`
  bloqueia execucao sem destino de JSON e markdown.
- Mesmo com fechamento, congelamento, rollback/conciliacao e liberacao de
  criacao preenchidos, o gate nao aprova `mayCreateCleanupMigrations` sem
  artefatos persistidos.

## Atualizacao - PM-06.1155 evidencia persistida no congelamento

- Adicionada regressao para confirmar que
  `validar_prontidao_congelamento_pm06 --exigir-arquivos-evidencia` bloqueia
  uma execucao sem destino de JSON e registro markdown.
- O gate nao aprova `mayFreezeLegacyWrites` sem artefatos persistidos quando a
  janela exigir modo estrito.

## Atualizacao - PM-06.1154 politica v3 no congelamento

- Adicionada regressao para confirmar que
  `validar_prontidao_congelamento_pm06` bloqueia congelamento legado quando a
  politica de remocao de aliases nao aponta para `financeiro-v3`.
- Mesmo com canonical-first pronto e evidencias operacionais preenchidas, o
  gate preserva `mayFreezeLegacyWrites=False` quando a politica de corte esta
  inconsistente.

## Atualizacao - PM-06.1153 limpeza rejeita rollback executavel

- Adicionada regressao no gate
  `validar_prontidao_migracao_limpeza_pm06` para rejeitar evidencia de
  rollback/conciliacao que permita execucao real de rollback ou conciliacao.
- Mesmo com fechamento, congelamento, refs operacionais, revisoes e liberacao
  de criacao preenchidos, `mayCreateCleanupMigrations` permanece bloqueado
  quando a evidencia nao preserva `mayExecuteRollback=False` e
  `mayExecuteConciliation=False`.

## Atualizacao - PM-06.1152 evidencia obrigatoria no rollback estrito

- Adicionada regressao para confirmar que
  `validar_rollback_conciliacao_pm06 --exigir-arquivos-evidencia` bloqueia a
  execucao quando JSON e registro markdown de evidencia nao foram definidos.
- O bloqueio evita que uma validacao local sem artefatos persistidos seja usada
  nos gates de fechamento ou migration de limpeza.

## Atualizacao - PM-06.1151 planos locais obrigatorios no rollback

- Adicionada regressao para confirmar que
  `validar_rollback_conciliacao_pm06 --exigir-arquivos-plano` bloqueia
  caminhos inexistentes para plano de rollback, conciliacao e politica de
  dados delta.
- O modo estrito continua aceitando apenas arquivos locais reais antes de gerar
  evidencia utilizavel pelos gates seguintes.

## Atualizacao - PM-06.1150 intervalo da janela de rollback

- Adicionada regressao para confirmar que
  `validar_rollback_conciliacao_pm06` bloqueia janela com
  `--janela-inicio` maior que `--janela-fim`, mesmo quando as demais
  referencias operacionais estao preenchidas.
- O bloqueio preserva `rollbackConciliationDecision.status=blocked` e nao
  libera a evidencia para gate de migration de limpeza.

## Atualizacao - PM-06.1149 auto-resolucao da migration de limpeza

- Adicionada regressao para confirmar que
  `validar_prontidao_migracao_limpeza_pm06` encontra automaticamente, via
  `--diretorio-evidencias`, `pm06-fechamento.json`,
  `pm06-prontidao-congelamento-legado.json` e
  `pm06-rollback-conciliacao-janela.json`.
- A auto-resolucao nao relaxa o gate: backup, homologacao, auditoria, aceite,
  rollback, conciliacao, plano de migration, revisoes e liberacao explicita
  continuam obrigatorios.

## Atualizacao - PM-06.1148 rollback obrigatorio em redirects

- O fechamento PM-06 passou a validar que o JSON de redirects publica
  `activation.rollbackEnvironment`.
- A evidencia e rejeitada se o rollback nao definir
  `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False`.
- Adicionada regressao para bloquear payload de redirects `ready=True` sem
  ambiente de rollback explicito.

## Atualizacao - PM-06.1147 auto-resolucao das evidencias finais

- Adicionada regressao para confirmar que `validar_fechamento_pm06` encontra
  automaticamente os quatro JSONs finais quando recebe apenas
  `--diretorio-evidencias`.
- O gate final resolve `pm06-validacao-backup-rollback.json`,
  `pm06-redirect-next-legado.json`,
  `pm06-prontidao-congelamento-legado.json` e
  `pm06-rollback-conciliacao-janela.json`.
- O bloco operacional do plano mestre foi atualizado para mostrar os quatro
  artefatos exigidos e `--exigir-arquivos-evidencia`.

## Atualizacao - PM-06.1146 rollback/conciliacao no fechamento final

- O gate `validar_fechamento_pm06` passou a exigir tambem
  `pm06-rollback-conciliacao-janela.json`.
- Com `--diretorio-evidencias`, o fechamento agora procura automaticamente
  quatro JSONs: backup/rollback PM-06.2, redirects, congelamento legado e
  rollback/conciliacao da janela.
- A evidencia de rollback/conciliacao precisa ser read-only, liberar apenas
  uso no gate de migration de limpeza e manter bloqueadas execucao de rollback
  e execucao de conciliacao.
- Adicionada regressao para bloquear evidencia que tente liberar execucao real
  de rollback/conciliacao dentro do fechamento PM-06.

## Atualizacao - PM-06.1145 rollback/conciliacao da janela

- Criado `python manage.py validar_rollback_conciliacao_pm06`, comando
  read-only para validar o plano de rollback e conciliacao dos dados criados
  entre backup e janela.
- O gate exige backup, codigo da janela, intervalo valido, plano de rollback,
  script/plano de conciliacao, politica para dados delta, responsavel,
  homologacao, aceite operacional e tres revisoes finais.
- Com `--exigir-arquivos-plano`, rollback, conciliacao e politica de dados
  delta precisam apontar para arquivos locais existentes.
- O comando nunca executa rollback nem conciliacao; ele apenas libera a
  evidencia para ser usada no gate de migration de limpeza.
- `validar_prontidao_migracao_limpeza_pm06` passou a exigir
  `pm06-rollback-conciliacao-janela.json`.

## Atualizacao - PM-06.1144 gate de migration de limpeza

- Criado `python manage.py validar_prontidao_migracao_limpeza_pm06`, comando
  read-only para validar se ja e permitido criar migrations de limpeza depois
  do fechamento PM-06.
- O gate exige fechamento PM-06 aprovado, congelamento legado aprovado, backup,
  homologacao sem divergencias, auditoria sem divergencias, aceite operacional,
  rollback, script/plano de conciliacao, plano de migration pequena, revisoes
  finais e liberacao explicita.
- Mesmo aprovado, o comando mantem `mayApplyCleanupMigrations=False`: aplicar
  migration continua exigindo janela propria, revisao dos arquivos gerados,
  backup vigente e smoke pos-migration.
- `validar_fechamento_pm06` passou a listar esse comando como proxima
  recomendacao operacional sem criar dependencia circular no fechamento.

## Atualizacao - PM-06.1143 congelamento legado como evidencia final

- O gate `validar_fechamento_pm06` passou a exigir tambem
  `pm06-prontidao-congelamento-legado.json`, gerado por
  `validar_prontidao_congelamento_pm06`.
- Com `--diretorio-evidencias`, o fechamento procura automaticamente
  `pm06-validacao-backup-rollback.json`, `pm06-redirect-next-legado.json` e
  `pm06-prontidao-congelamento-legado.json`.
- A evidencia de congelamento precisa declarar `source=pm06_legacy_freeze_readiness`,
  `step=PM-06`, `readOnly=True`, `mayFreezeLegacyWrites=True` e
  `mayCreateCleanupMigrations=False`.

## Atualizacao - PM-06.1142 prontidao de congelamento legado

- Criado `python manage.py validar_prontidao_congelamento_pm06`, comando
  read-only para diagnosticar se a PM-06 pode iniciar congelamento de escrita
  em models legados.
- O comando bloqueia congelamento quando ainda houver escrita
  `legacyAdapterSynced`, origens adapter-only, campos fisicos pendentes,
  falta de validacao frontend, aceite operacional, backup/rollback, janela ou
  revisoes finais.
- Mesmo quando aprovado, o payload mantem `mayCreateCleanupMigrations=False`;
  migrations de limpeza continuam exigindo gate proprio.
- O gate final `validar_fechamento_pm06` passou a recomendar essa validacao
  antes de qualquer congelamento legado.

## Atualizacao - PM-06.1141 politica financeiro-v3 no gate final

- O gate final PM-06 passou a incluir um check read-only da politica publicada
  em `meta.nomenclature`.
- O payload agora registra `financeiroV3Policy`, incluindo versao atual,
  versao futura de remocao, regra de bloqueio, campos fisicos pendentes e
  renomes fisicos planejados.
- A validacao reprova se a politica de remocao nao apontar para
  `financeiro-v3`, se a versao atual ja for a versao de corte ou se a regra
  documental estiver ausente.

## Atualizacao - PM-06.1140 identidade estrita das evidencias finais

- O gate `validar_fechamento_pm06` passou a validar a identidade dos JSONs
  recebidos, nao apenas `ready=True`.
- A evidencia de preparacao precisa declarar `source=pm06_backup_rollback_preparation`,
  `step=PM-06.2` e `readOnly=True`; a evidencia de redirects precisa trazer
  origem valida, lista de superficies e plano de ativacao/rollback.
- Adicionada regressao para bloquear arquivo pronto, porem de origem errada,
  preservando PM-07 bloqueada ate evidencias reais e compatíveis.

## Atualizacao - PM-06.1139 gate final read-only da PM-06

- Criado `python manage.py validar_fechamento_pm06`, comando read-only para
  consolidar o fechamento da PM-06 antes de permitir PM-07.
- O gate exige JSON aprovado de PM-06.2, JSON aprovado de redirects/readonly,
  referencia da validacao frontend, aceite operacional, revisoes finais,
  evidencias atualizadas, consolidacao resolvida e liberacao explicita da PM-07.
- Quando `--diretorio-evidencias` e informado, o gate procura automaticamente
  `pm06-validacao-backup-rollback.json` e `pm06-redirect-next-legado.json` no
  diretorio, alem de salvar `pm06-fechamento.json/md`.
- Validacoes: compile do comando, testes focados do gate e execucao diagnostica
  `validar_fechamento_pm06 --json` bloqueando PM-07 sem evidencias finais.

## Atualizacao - PM-06.1137 reconciliacao visual do menu Next.js

- O rodape fixo da sidebar Next.js deixou de usar o texto fixo `Admin RH` e
  passou a exibir `displayName` ou `username` da sessao Django autenticada.
- A sidebar continua sendo o boundary aprovado para consultar
  `getBackendSession`, preservando o guardrail canonical-first do frontend.
- Guardrail: nenhuma API Django, rota/template, migration, congelamento de
  escrita, remocao fisica ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1136 pre-publicacao frontend consolidada

- O frontend passou a ter `verify:lockfile` e `verify:publish`, consolidando a
  validacao de `pnpm-lock.yaml` congelado com lint, typecheck, guardrails do
  dashboard e build.
- O fluxo oficial local ficou alinhado ao `packageManager: pnpm@10.33.4`,
  reduzindo diferenca entre maquina local e deploy Vercel.
- Validacao registrada no frontend: `npx --yes pnpm@10.33.4 run verify:publish`.

## Atualizacao - PM-06.1127 prioridade canonica no KPI financeiro

- O normalizador principal do dashboard Next.js passou a priorizar o candidato
  canonico de resultado financeiro ao montar o KPI visual de saldo/resultado.
- O alias legado `saldoCaixa` continua aceito como fallback, mas nao vence mais
  quando o backend tambem entrega o campo canonico normalizado.
- Guardrail: nenhum alias foi removido do contrato, nenhuma API Django,
  migration, congelamento de escrita ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1126 FCF sem alias visual de saldo em aberto

- A tela Next.js de FCF deixou de ler diretamente o alias legado
  `saldo_em_aberto` ao calcular pendencia de parcelas.
- O componente agora usa apenas `pendingPaymentAmount` e
  `pendingAccountsAmount`, que ja chegam normalizados pelo service do
  dashboard financeiro.
- O alias segue preservado nos tipos e no service como compatibilidade de
  entrada ate o corte `financeiro-v3`.
- Guardrail: nenhuma API, rota/template Django, migration, congelamento de
  escrita ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1125 despesas editaveis no Next.js

- A tela Next.js `/despesas` passou a abrir a mesma edicao lateral usada em
  `/receitas`, agora para alterar `valor previsto` e marcar a despesa como paga
  ou nao paga.
- A escrita usa `PUT /api/despesas/<id>/`, com sessao Django, CSRF e permissao
  `caixa.change_despesaoperacional`; usuarios apenas com
  `caixa.view_despesaoperacional` continuam em leitura.
- O endpoint opera somente despesas operacionais manuais
  (`DespesaOperacional.ORIGEM_MANUAL`), preservando custos de servico e custos
  extras sincronizados nas telas de pagamento proprias.
- Guardrail: nenhuma rota/template Django foi removida, nenhuma migration,
  congelamento de escrita ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1124 header usa evento canonico

- O header compartilhado do Next.js deixou de emitir `costCenterId` ao aplicar
  ou alterar filtros de evento.
- O filtro visual agora monta explicitamente o payload com `eventId`, mantendo
  `costCenterId` apenas aceito na borda de normalizacao para URLs/consumidores
  legados.
- Validacao local: `npm run lint`, `npm run typecheck` e
  `npm run check:financial-canonical` passaram.
- Guardrail: nenhuma API, template Django, migration, remocao fisica ou corte
  de compatibilidade foi alterado.

## Atualizacao - PM-06.1123 receitas editaveis no Next.js

- A tela Next.js `/receitas` passou a abrir edicao lateral para alterar
  `valor previsto` e marcar a receita como recebida ou nao recebida.
- A escrita usa `PUT /api/receitas/<id>/`, com sessao Django, CSRF e
  permissao `caixa.change_receitaoperacional`; usuarios apenas com
  `caixa.view_receitaoperacional` continuam em leitura.
- O backend atualiza `valor_previsto`, `valor_recebido`, `data_recebimento` e
  deixa o model recalcular `status`, preservando sinais de sincronizacao de
  ledger/obrigacoes ja existentes.
- Validacao local: `caixa.tests.ReceitasApiTests`, `python manage.py check`,
  `python manage.py makemigrations --check --dry-run`, `npm run lint`,
  `npm run typecheck`, `npm run check:financial-canonical` e `git diff --check`
  passaram.
- Guardrail: nenhuma rota/template Django foi removida, nenhuma migration de
  limpeza foi criada, nenhum congelamento de escrita e nenhum corte
  `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1122 clareza da fila de pagamentos

- A tela Next.js `/pagamentos` foi revisada como fila de baixa, nao como
  historico completo: ela lista somente contas a pagar com saldo pendente,
  excluindo itens `liquidado` e `cancelado`.
- O estado vazio da fila agora informa que nao ha pendencias no recorte atual
  e orienta que itens ja liquidados continuam disponiveis em `Obrigacoes`.
- A investigacao confirmou que `custo_extra` e retornado pelo backend no
  escopo `permissionScope=payments` quando o usuario tem
  `caixa.add_pagamentoeventocustoextra`.
- Validacao local: `npm run lint`, `npm run typecheck`,
  `npm run check:financial-canonical` e o teste backend focado
  `caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_pagamentos_usa_permissoes_de_baixa_sem_ledger`
  passaram.

## Atualizacao - PM-06.1121 logout direciona ao login do frontend

- O botao `Sair` do header compartilhado agora encerra a sessao no Django e
  recarrega a rota atual do Next.js, fazendo a propria tela cair no estado de
  login do frontend.
- A mudanca evita retorno visual para uma tela autenticada antiga pelo historico
  do navegador e preserva o contrato atual, sem criar rota `/login` separada.
- Validacao local: `npm run lint`, `npm run typecheck`,
  `npm run check:financial-canonical` e `git diff --check` passaram.

## Atualizacao - PM-06.1120 guardrail canonico das telas PM-06

- O verificador `npm run check:financial-canonical` foi atualizado para
  reconhecer explicitamente as telas PM-06 adicionadas ao Next.js: backups,
  clientes, custos fixos, eventos, FCI e orcamentos.
- As allowlists passaram a documentar os boundaries de compatibilidade usados
  por services/hooks dessas telas, incluindo aliases de query ainda aceitos na
  borda de API e imports controlados de CSRF, auth, URLs de navegacao e barrel
  financeiro.
- O sidebar ficou registrado como excecao compartilhada controlada para ler a
  sessao Django e montar links backend/Next sem espalhar a regra fora do menu.
- Validacao local: `npm run check:financial-canonical`, `npm run lint`,
  `npm run typecheck`, `git diff --check` e `python manage.py check`
  passaram.
- Guardrail: a mudanca e de validacao/contrato de frontend; nenhuma migration,
  remocao fisica, congelamento de escrita ou corte `financeiro-v3` foi
  iniciado.

## Atualizacao - PM-06.1119 permissoes Next.js alinhadas ao Django

- O payload de `/api/auth/session/` passou a expor permissoes granulares para
  receitas, despesas, eventos, custos por evento, custos de servico, custos
  extras, pagamentos e acoes de edicao/baixa usadas pelo Next.js.
- O menu Next.js agora filtra as telas operacionais por essas permissoes e
  deixa `Admin` e `PM-03 Evidencias` visiveis apenas para superusuario.
- Links de menu sem rota Next.js implementada foram removidos da navegacao
  principal para evitar 404 operacional e reduzir confusao de permissao.
- `/api/custos-por-evento/` foi separado do endpoint geral de obrigacoes e
  usa a mesma permissao da tela Django de eventos (`caixa.view_evento`).
- O endpoint de obrigacoes aceita leitura por origem quando o usuario tem a
  permissao Django equivalente do model, e o escopo `permissionScope=payments`
  usa as permissoes nativas de baixa sem exigir permissao geral de ledger.
- A tela FCI continua somente leitura no Next.js para usuarios comuns; atalhos
  de Admin FCI ficam ocultos fora de superusuario.
- Validacao local: frontend `lint` e `typecheck` passaram nesta retomada;
  backend `check` passou; na validacao da etapa de permissoes, a suite completa
  `caixa.tests` ja havia passado com 540 testes.
- Guardrail: nenhuma rota/template Django foi removida, nenhuma migration de
  limpeza foi criada, nenhum congelamento de escrita e nenhum corte
  `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1118 orcamentos em Next.js

- Criada API JSON de orcamentos em `GET/POST /api/orcamentos/`,
  `GET/PUT /api/orcamentos/<id>/` e
  `POST /api/orcamentos/<id>/aprovar/`.
- A edicao pelo Next.js substitui cabecalho, itens e custos extras apenas
  enquanto o orcamento estiver em `rascunho` ou `enviado`; depois de aprovado,
  o fluxo Next.js fica somente leitura para preservar o evento gerado.
- O payload de sessao passou a publicar permissoes granulares
  `canViewBudgets`, `canAddBudget`, `canChangeBudget` e `canApproveBudget`.
- Validacao local: `OrcamentosApiTests` e contrato de sessao passaram; frontend
  respondeu 200 em `http://localhost:3000/orcamentos`.
- Guardrail: nenhuma rota/template Django foi removida e nenhuma migration,
  congelamento de escrita ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1117 smoke autenticado de producao

- PM-06.1117 foi registrada em 2026-05-31 com relato do operador e output do
  servidor.
- Smoke autenticado aprovado: receitas, despesas, pagamentos, obrigacoes, FCI,
  FCF, backups, clientes, custos por evento, custos extras e admin abriram suas
  respectivas paginas normalmente.
- O servidor executou o validador com `--diretorio-evidencias` e
  `--exigir-arquivos-evidencia`, retornando `ready=True`, `issues=[]`,
  `redirectsEnabled=True` e salvando JSON/Markdown em
  `evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31/`.
- Guardrail: PM-06 esta validada operacionalmente em producao, mas remocao
  fisica, migrations de limpeza, corte de aliases e `financeiro-v3` continuam
  bloqueados.

## Atualizacao - PM-06.1116 runtime efetivo de producao

- PM-06.1116 foi registrada em 2026-05-31 a partir do output executado no
  servidor `ubuntu@vminstancia:~/sites/controledecaixa`.
- `python manage.py validar_redirects_next_legado --falhar --json` retornou
  `ready=True`, `issues=[]`, `redirectsEnabled=True`,
  `frontendBaseUrl=https://adm.rhremoto.com` e as 13 superficies migradas em
  `configuredSurfaces`.
- Evidencia local criada em
  `evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31/`.
- Guardrail: redirect controlado esta ativo, mas remocao fisica de rotas,
  templates, migrations, aliases e corte `financeiro-v3` continuam bloqueados.

## Atualizacao - PM-06.1115 dominios reais de producao

- PM-06.1115 foi registrada em 2026-05-31 como preflight de producao direta.
- Frontend real informado: `https://adm.rhremoto.com`; backend real informado:
  `https://caixa.rhremoto.com`.
- Checagens HTTPS read-only retornaram 200 para as rotas Next.js migradas e
  para o backend base; `/api/dashboard/financial-overview/` retornou 401 sem
  sessao, esperado para API protegida.
- `validar_redirects_next_legado` foi executado com `NEXT_FRONTEND_URL` real de
  producao, 13 superficies unitarias, rodada agregada e rollback, gerando
  evidencias em `evidencias/pm06-1115-prod-url-real-2026-05-31/`.
- Guardrail: nenhuma variavel foi persistida automaticamente no servidor,
  nenhuma rota/template foi removida e o rollback segue por
  `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False` ou allowlist vazia.

## Atualizacao - PM-06.1112 fechamento local da PM-06

- PM-06.1109 a PM-06.1112 foram concluidas em desenvolvimento local em
  2026-05-31.
- Canarios locais de redirect/readonly ficaram registrados para 13 superficies:
  `backups_lista`, `lista_investimentos`, `lista_financiamentos`,
  `pagamentos_custos_extras`, `pagamentos_custos_servico`, `pagamentos_fcf`,
  `pagar_parcela`, `receitas_lista`, `despesas_lista`, `custos_fixos_lista`,
  `custos_por_evento`, `custo_extra_adicionar` e `pagamentos`.
- `custos_fixos_lista` passou a publicar a ponte Next.js para `/custos-fixos`
  e a respeitar redirect controlado por flag/allowlist.
- Corrigido o formset de custos extras em orcamentos para que formularios
  extras vazios nao bloqueiem a criacao de orcamento sem custo extra.
- Validacao: `manage.py check`, `makemigrations --check --dry-run`, suite
  `caixa` com 528 testes, `corepack pnpm lint`, `typecheck`, `build`,
  validacao agregada das superficies migradas e `git diff --check` aprovados.
- Guardrail: nenhuma rota/template Django foi removida, nenhum alias publicado
  foi cortado, nenhuma migration, congelamento de escrita ou corte
  `financeiro-v3` foi iniciado; homologacao/producao ainda devem repetir
  evidencias com URL real do Next.js antes de ativar allowlist.

## Atualizacao - PM-06.1099 telas operacionais Next.js priorizadas

- PM-06.1099 foi registrada em desenvolvimento local em 2026-05-31.
- Frontend Next.js passou a cobrir as rotas operacionais `/custos-por-evento`, `/centro-de-custos`, `/receitas`, `/despesas`, `/custos-extras` e `/pagamentos`, consumindo APIs canonicas quando aplicavel e preservando Django como fonte da verdade.
- Guardrail: nenhuma tela Django foi removida, nenhum alias publicado foi cortado, nenhuma migration, congelamento de escrita ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1100 inventario de telas Django apos migracao Next.js

- PM-06.1100 foi registrada em desenvolvimento local em 2026-05-31.
- Rotas/templates Django de custos por evento, receitas, despesas, cadastro de custo extra e central de pagamentos ficaram classificados como migrados para superficie Next.js, mantendo Django como fallback legado ate decisao de redirect/somente leitura.
- Pagamentos especializados de custos de servico/extras ficaram parcialmente cobertos por `/pagamentos`, mas preservados como excecao operacional ate validacao de baixa real; FCF/FCI/Mes Financeiro seguem como excecoes ainda nao migradas.
- Guardrail: nenhuma rota/template Django foi removida ou alterada em runtime; nenhum alias, migration, limpeza ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1101 ponte visual Django -> Next.js

- PM-06.1101 foi registrada em desenvolvimento local em 2026-05-31.
- Telas Django ja migradas passaram a publicar uma ponte visual para o Next.js via contexto `frontend_migration`, usando `NEXT_FRONTEND_URL` como base configuravel.
- Foram marcadas como `migrated`: custos por evento, receitas, despesas, cadastro de custos extras e central de pagamentos.
- Pagamentos de custos de servico/extras ficaram marcados como `partial`, preservando liquidacao especializada no Django ate validacao operacional.
- Guardrail: nao houve redirect automatico, remocao de template, mudanca de formulario, migration, alias, dado financeiro ou corte `financeiro-v3`.

## Atualizacao - PM-06.1102 redirect controlado por flag

- PM-06.1102 foi registrada em desenvolvimento local em 2026-05-31.
- Backend agora possui `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED` e `NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES` para ensaiar redirect de telas Django migradas para Next.js com allowlist.
- O redirect preserva query string, so vale para superficies `migrated` e so roda em metodos seguros `GET`/`HEAD`.
- Guardrail: flag desligada e allowlist vazia por padrao; POST legado permanece no Django; nenhuma rota/template foi removida e nenhum corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.1103 validador de redirects Next legados

- PM-06.1103 foi registrada em desenvolvimento local em 2026-05-31.
- Foi criado `python manage.py validar_redirects_next_legado` para validar URL do Next, allowlist, rotas Django e elegibilidade `migrated` antes de ativar qualquer redirect.
- O comando aceita `--surface`, `--exigir-unitario`, `--json` e `--falhar`, permitindo ensaio unitario de canario como `receitas_lista`.
- Guardrail: o comando e somente leitura, nao liga flag, nao altera `.env`, nao remove rota/template e nao inicia corte `financeiro-v3`.

## Atualizacao - PM-06.1104 registro de canario e rollback Next legado

- PM-06.1104 foi registrada em desenvolvimento local em 2026-05-31.
- `validar_redirects_next_legado` agora publica `executionRecord.markdown`, ambiente recomendado de ativacao, ambiente de rollback e comandos de validacao antes/depois da flag.
- O registro facilita ensaiar uma unica superficie migrada, como `receitas_lista`, sem improvisar variaveis de ambiente.
- Guardrail: nada e ativado automaticamente; o comando continua somente leitura e o fallback Django permanece intacto.

## Atualizacao - PM-06.1105 evidencias persistidas do canario de redirect

- PM-06.1105 foi registrada em desenvolvimento local em 2026-05-31.
- `validar_redirects_next_legado` agora aceita `--salvar-json`, `--salvar-registro`, `--diretorio-evidencias` e `--exigir-arquivos-evidencia`.
- Com `--diretorio-evidencias`, o comando salva `pm06-redirect-next-legado.json` e `pm06-redirect-next-legado.md` e publica os caminhos em `outputEvidenceFiles`.
- Guardrail: persistir evidencia nao ativa redirect, nao altera `.env`, nao remove fallback Django e nao inicia corte `financeiro-v3`.

Atualizacao PM-02: o backend agora possui o comando somente leitura `python manage.py gerar_snapshot_baseline_financeira --json` para registrar versao do codigo backend, versao/git do frontend quando disponivel, referencia manual do deploy Vercel via `--frontend-ref` ou `--frontend-deploy-url`, canonical-first, cache, cookies, banco sem senha e comandos PM-02 antes de ampliar origens canonical-first. Tambem foi criado `python manage.py validar_baseline_pm02 --falhar --json` para agregar snapshot, `check`, `makemigrations --check --dry-run`, pre-flight financeiro, validacao operacional e auditoria de totais. O modo de servidor pode usar `--modo-servidor-estrito` para ativar `--falhar`, dirty/debug, referencia declarada do frontend publicado, release, backup, ambiente e fechamento PM-02; tambem aceita `--ambiente=producao` ou `--ambiente=homologacao` para identificar a janela no registro. O snapshot e o validador agora publicam o comando estrito em `pm02StrictServerCommand`/`strictServerCommand`, a alternativa por URL em `pm02StrictServerCommandWithDeployUrl`/`strictServerCommandWithDeployUrl`, o comando preenchido em `strictServerCommandResolved`, o resumo `manualEvidenceComplete`/`manualEvidenceStatus`, o resumo `strictServerFlagsComplete`/`strictServerFlagsStatus`, o sinal `pm02ClosureReady`, os bloqueios `pm02ClosureBlockers`, o bloco `executionRecord.markdown` para colar no plano mestre e validacoes opcionais de ambiente com cookies, cache, canonical-first, banco, `--esperar-allowed-hosts`, `--esperar-csrf-trusted-origins` e `--esperar-cors-allowed-origins`. As expectativas de ambiente tambem entram no comando resolvido e no markdown da janela quando informadas. O relatorio humano diferencia baseline automatica aprovada de conclusao operacional da PM-02, reduzindo risco de executar a janela com parametro faltante. Validado com testes focados dos comandos, execucao local de `validar_baseline_pm02 --json`, validacao local com `--frontend-ref`, modo estrito de referencia do frontend, modo estrito de release/backup/ambiente/fechamento, `check`, `makemigrations --check --dry-run` e suite completa Django com 462 testes.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--salvar-json=<arquivo>` e `--salvar-registro=<arquivo>` para gravar, no servidor, o payload completo e o bloco markdown de evidencia da janela.

Atualizacao PM-02 adicional: quando esses arquivos sao informados, o validador publica `evidenceFiles` e a linha `Arquivos salvos` no `executionRecord.markdown`.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--salvar-snapshot-json=<arquivo>` para gravar o snapshot interno junto do JSON consolidado e do registro markdown.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--diretorio-evidencias=<diretorio>` para gerar `pm02-baseline.json`, `pm02-registro.md` e `pm02-snapshot.json` com nomes padronizados.

Atualizacao PM-02 adicional: quando `--diretorio-evidencias` e usado, o payload tambem publica `evidenceFiles.directory` e o markdown registra `diretorio=<diretorio>` em `Arquivos salvos`.

Atualizacao PM-02 adicional: `--diretorio-evidencias` agora reprova de forma clara quando aponta para um arquivo em vez de diretorio.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--exigir-arquivos-evidencia` para reprovar a baseline quando os tres caminhos de evidencia nao forem informados.

Atualizacao PM-02 adicional: `gerar_snapshot_baseline_financeira` tambem aceita `--salvar-json=<arquivo>` para preservar o snapshot bruto de ambiente/backend/frontend no servidor.

Atualizacao PM-02 adicional: quando o snapshot bruto e salvo, o payload tambem publica `evidenceFiles.json` com o caminho gerado.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--exigir-backup-arquivo-existente` para conferir, quando `--backup-ref` for caminho local, que o arquivo de backup realmente existe no servidor.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--exigir-release-git-ref-existente` para conferir, quando `--release-ref` for tag ou commit local, que a referencia existe no git do backend.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--exigir-frontend-deploy-url-https` para conferir, quando a evidencia do frontend for URL publicada, que o deploy informado usa HTTPS.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--perfil-rhremoto-producao` para preencher `--ambiente=producao`, cookies `.rhremoto.com` e Redis local esperados na janela PM-02 da producao RHRemoto; canonical-first e banco continuam explicitos quando a janela exigir esses gates.

Atualizacao PM-02 adicional: quando `--perfil-rhremoto-producao` e usado, o relatorio publica `environmentProfile=rhremoto-producao` no JSON e `Perfil de ambiente: rhremoto-producao` no markdown da janela.

Atualizacao PM-02 adicional: `strictServerCommandResolved` agora preserva `--perfil-rhremoto-producao` quando esse perfil foi usado, alem de manter os valores concretos expandidos de ambiente, cookies e Redis.

Atualizacao PM-02 adicional: o snapshot e o validador agora publicam comandos prontos para producao RHRemoto em `pm02StrictServerCommandRhremotoProduction`, `pm02StrictServerCommandRhremotoProductionWithDeployUrl`, `strictServerCommandRhremotoProduction` e `strictServerCommandRhremotoProductionWithDeployUrl`.

Atualizacao PM-02 adicional: `manualRequirements` passou a incluir sugestoes RHRemoto em `suggestedRhremotoCommand` e `suggestedRhremotoCommandWithDeployUrl`, mantendo `suggestedCommand` generico como compatibilidade.

Atualizacao PM-02 adicional: tambem foram adicionadas variantes RHRemoto com evidencias em `pm02StrictServerCommandRhremotoProductionWithEvidence`, `pm02StrictServerCommandRhremotoProductionWithDeployUrlAndEvidence`, `strictServerCommandRhremotoProductionWithEvidence`, `strictServerCommandRhremotoProductionWithDeployUrlAndEvidence`, `suggestedRhremotoCommandWithEvidence` e `suggestedRhremotoCommandWithDeployUrlAndEvidence`.

Atualizacao PM-02 adicional: quando `--diretorio-evidencias` e usado, `strictServerCommandResolved` preserva a flag original e tambem mostra os caminhos expandidos `--salvar-json`, `--salvar-registro` e `--salvar-snapshot-json`.

Atualizacao PM-02 adicional: `validar_baseline_pm02` agora publica `pm02NextAction` no JSON e no markdown, indicando se o proximo passo e corrigir validacoes, informar evidencias reais, reexecutar modo estrito ou registrar revisoes para fechamento.

Atualizacao PM-02 adicional: quando a proxima acao exige comando, `pm02NextAction` tambem publica `suggestedCommand` e `suggestedRhremotoCommand`; o markdown registra `pm02NextActionSuggestedCommand` e `pm02NextActionSuggestedRhremotoCommand`.

Atualizacao PM-02 adicional: `--perfil-rhremoto-producao` agora tem regressao cobrindo que defaults do perfil nao sobrescrevem valores informados explicitamente no comando, como `--ambiente=homologacao`.

Atualizacao PM-02 adicional: quando o perfil RHRemoto e usado, o JSON publica `environmentProfileDefaults` e o markdown registra `Defaults do perfil de ambiente`, separando defaults do perfil dos valores efetivos usados na janela.

Atualizacao PM-02 adicional: o validador tambem publica `environmentProfileDefaultsApplied` e `environmentProfileOverrides`, registrando quais defaults do perfil foram aplicados e quais valores explicitos prevaleceram.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--esperar-session-cookie-secure=true` e `--esperar-csrf-cookie-secure=true` para validar cookies seguros por HTTPS quando a janela exigir esse gate. Essas flags sao opcionais e nao entram automaticamente no `--perfil-rhremoto-producao`.

Atualizacao PM-02 adicional: `validar_baseline_pm02` tambem aceita `--esperar-session-cookie-samesite=Lax` e `--esperar-csrf-cookie-samesite=Lax` para validar o escopo `SameSite` dos cookies na janela PM-02, sem mudar runtime, login ou regras financeiras.

Atualizacao PM-02 adicional: o `executionRecord.markdown` agora mostra tambem `sessionSecure`, `csrfSecure`, `sessionSameSite` e `csrfSameSite` no resumo de cookies, facilitando auditoria da janela mesmo quando esses gates opcionais nao forem exigidos.

Atualizacao PM-03.1: `monitorar_janela_canonical_first` agora aceita `--salvar-json`, `--salvar-registro`, `--diretorio-evidencias` e `--exigir-arquivos-evidencia` para preservar o JSON e o markdown de monitoramento de `custo_fixo`. O payload publica `evidenceFiles` e `executionRecord.markdown`, sem alterar allowlist, baixa, ledger, models ou regras financeiras.

## Atualizacao - PM-06.1017 listas compostas em mapas de aliases

- PM-06.1017 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou listas compostas nos mapas de aliases iniciais e de query do frontend.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1016 tipo, origem e excedente em amounts

- PM-06.1016 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de tipo, origem e excedente realizado nos utilitarios de valores de obrigacoes.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1015 origem e tipo em hook/util FCF

- PM-06.1015 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de origem de movimentacao e tipo em utilitario e hook de FCF/financiamento.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1014 aliases finais de valores, labels e originId

- PM-06.1014 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou arrays mistos simples restantes em valores do ledger/baixas, labels de contas a pagar e `originId` da query do ledger.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1013 nomes e indicadores do dashboard

- PM-06.1013 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados em nomes de categorias, servicos, contratos e indicadores do dashboard.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1012 labels de contrato em ledger e conciliacao

- PM-06.1012 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de label de contrato em itens do ledger financeiro e worklist de conciliacao de obrigacoes.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1011 origem e IDs na query FCF

- PM-06.1011 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de origem de movimentacao e IDs operacionais na montagem de query FCF/financiamento.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1010 IDs na query de baixas canonicas

- PM-06.1010 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de IDs operacionais na montagem de query de baixas financeiras canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1009 IDs em filtros normalizados de baixas

- PM-06.1009 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de IDs operacionais em filtros normalizados de baixas financeiras canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1008 origem e IDs em filtros FCF normalizados

- PM-06.1008 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de origem de movimentacao e IDs operacionais em filtros FCF/financiamento normalizados.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1007 IDs em filtros normalizados do ledger

- PM-06.1007 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de IDs operacionais em filtros normalizados do ledger financeiro.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1006 labels em filtros normalizados de obrigacoes

- PM-06.1006 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de labels operacionais em filtros normalizados de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1005 IDs em filtros normalizados de obrigacoes

- PM-06.1005 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de IDs operacionais em filtros normalizados de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1004 valor em itens de baixas canonicas

- PM-06.1004 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de valor em itens de baixas financeiras canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1003 valor e origem em itens do ledger financeiro

- PM-06.1003 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases de valor e origem/source em itens do ledger financeiro.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1002 status e labels operacionais de obrigacoes

- PM-06.1002 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados de status, label de liquidacao e label de contrato em itens de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1001 origem e referencia em itens de obrigacoes

- PM-06.1001 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados de origem/referencia em itens de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.1000 espelhos legados de filtros de obrigacoes

- PM-06.1000 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js agrupou espelhos legados de filtros de obrigacoes financeiras por periodo, vinculo operacional, classificacao e conciliacao.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.999 filtros vazios de obrigacoes

- PM-06.999 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou campos canonicos e legados no fallback vazio de filtros de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.998 default do ledger financeiro

- PM-06.998 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js reutilizou o fallback vazio de filtros do ledger financeiro no default normalizado, preservando `costCenterId`.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.996 a PM-06.997 aliases semanticos de obrigacoes

- PM-06.996 a PM-06.997 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou aliases semanticos de valores e filtros de obrigacoes em helpers dedicados.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.995 filtros vazios do ledger financeiro

- PM-06.995 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou campos canonicos e legados no fallback vazio de filtros do ledger financeiro.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.989 a PM-06.994 espelhos de filtros FCF

- PM-06.989 a PM-06.994 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou espelhos canonicos e legados de tipo, credor, origem, contrato, evento e cliente em filtros FCF.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.988 chaves de presenca dos filtros FCF

- PM-06.988 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou chaves canonicas e legadas usadas para detectar filtros FCF presentes no service.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.986 a PM-06.987 utilitarios de leitura/evidencia

- PM-06.986 a PM-06.987 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou fallback `fonteDados` e datas legadas de evidencias PM-03 em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.984 a PM-06.985 query e acoes de obrigacoes

- PM-06.984 a PM-06.985 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou chaves canonicas/legadas da query inicial de obrigacoes e centralizou o parametro legado `situacao`.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.981 a PM-06.983 aliases de query em hooks/filtros

- PM-06.981 a PM-06.983 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou chaves canonicas e legadas em `use-financial-obligations.ts`, `dashboard-filters.ts` e `financial-financing-view.tsx`.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.980 origem de movimentacao no hook FCF

- PM-06.980 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou `sourceType` canonico dos aliases legados `movementSourceType` e `origem_movimentacao` no hook FCF.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.962 a PM-06.979 utilitarios financeiros

- PM-06.962 a PM-06.979 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados em `financial-obligations-amounts.ts` e `financial-financing-filters.ts`.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.952 a PM-06.961 espelhos opcionais de obrigacoes

- PM-06.952 a PM-06.961 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou campos canonicos de espelhos opcionais `valor_*`, `diagnostico*`, `orientacao*` e `conciliado_ledger` em itens e resumos de obrigacoes.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.933 a PM-06.951 opcoes e fallbacks finais

- PM-06.933 a PM-06.951 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados restantes em opcoes de dashboard, opcoes FCF, movimentacoes FCF e resumos de obrigacoes.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.923 a PM-06.932 filtros de obrigacoes

- PM-06.923 a PM-06.932 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para contrato, evento, cliente, datas, natureza, busca e labels em filtros de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.919 a PM-06.922 conciliacao em itens de obrigacoes

- PM-06.919 a PM-06.922 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para diagnostico, orientacao, diferenca realizada e conciliacao ledger em itens de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.912 a PM-06.918 worklist de conciliacao

- PM-06.912 a PM-06.918 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para diagnostico, orientacao, contrato e cliente no worklist de conciliacao de obrigacoes.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.895 a PM-06.911 lancamentos financeiros canonicos

- PM-06.895 a PM-06.911 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para valores, origem, cliente, contrato, evento, data, natureza e descricao em lancamentos financeiros canonicos.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.876 a PM-06.894 itens de obrigacoes financeiras

- PM-06.876 a PM-06.894 foram concluidas em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para cliente, datas, natureza, status, fonte de leitura, descricao, contrato e evento em itens de obrigacoes financeiras.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.875 fallback de settlementDescription em latestSettlement canonico

- PM-06.875 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `settlementDescription` em latestSettlement canonico.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.874 fallback de descricao em latestSettlement canonico

- PM-06.874 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e de baixa para `description` em latestSettlement canonico.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.873 fallback de settlementDate em latestSettlement canonico

- PM-06.873 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `settlementDate` em latestSettlement canonico.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.872 fallback de data em latestSettlement canonico

- PM-06.872 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e de baixa para `date` em latestSettlement canonico.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.871 fallback de settlementAmount em latestSettlement canonico

- PM-06.871 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `settlementAmount` em latestSettlement canonico.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.870 fallback de valor em latestSettlement canonico

- PM-06.870 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e de baixa para `amount` em latestSettlement canonico.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.869 fallback de settlementDescription em itens de baixas canonicas

- PM-06.869 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `settlementDescription` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.868 fallback de descricao em itens de baixas canonicas

- PM-06.868 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, de baixa e legados para `description` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.867 alias de natureza em itens de baixas canonicas

- PM-06.867 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `nature` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.866 fallback de label do evento em itens de baixas canonicas

- PM-06.866 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `eventLabel` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.865 fallback de numero do evento em itens de baixas canonicas

- PM-06.865 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `eventNumber` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.864 alias de nome do evento em itens de baixas canonicas

- PM-06.864 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventName` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.863 alias de id do evento em itens de baixas canonicas

- PM-06.863 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventId` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.862 fallback de label do contrato em itens de baixas canonicas

- PM-06.862 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contractLabel` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.861 alias de codigo do contrato em itens de baixas canonicas

- PM-06.861 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractCode` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.860 alias de id do contrato em itens de baixas canonicas

- PM-06.860 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.859 alias de nome do cliente em itens de baixas canonicas

- PM-06.859 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientName` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.858 alias de id do cliente em itens de baixas canonicas

- PM-06.858 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.857 fallback de sourceLabel em itens de baixas canonicas

- PM-06.857 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `sourceLabel` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.856 alias de sourceId em itens de baixas canonicas

- PM-06.856 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceId` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.855 aliases de settlementAmount em itens de baixas canonicas

- PM-06.855 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `settlementAmount` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.854 aliases de valor em itens de baixas canonicas

- PM-06.854 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, settlement e legados para `amount` em itens de baixas canonicas.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.853 fallback de label de origem em alocacoes de baixas canonicas

- PM-06.853 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `sourceLabel` em alocacoes de baixas canonicas.
- Fallback por `source` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.852 fallback de label do evento em alocacoes de baixas canonicas

- PM-06.852 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `eventLabel` em alocacoes de baixas canonicas.
- Fallback `numero - nome` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.851 fallback de numero do evento em alocacoes de baixas canonicas

- PM-06.851 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `eventNumber` em alocacoes de baixas canonicas.
- Fallback por `contractCode` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.850 alias de nome do evento em alocacoes de baixas canonicas

- PM-06.850 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventName` em alocacoes de baixas canonicas.
- Fallback `evento_nome` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.849 alias de id do evento em alocacoes de baixas canonicas

- PM-06.849 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventId` em alocacoes de baixas canonicas.
- Fallback `evento_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.848 fallback de label do contrato em alocacoes de baixas canonicas

- PM-06.848 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contractLabel` em alocacoes de baixas canonicas.
- Fallback por `contractCode` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.847 alias de codigo do contrato em alocacoes de baixas canonicas

- PM-06.847 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractCode` em alocacoes de baixas canonicas.
- Fallback `contrato_codigo` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.846 alias de id do contrato em alocacoes de baixas canonicas

- PM-06.846 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em alocacoes de baixas canonicas.
- Fallback `contrato_operacional_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.845 alias de nome do cliente em alocacoes de baixas canonicas

- PM-06.845 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientName` em alocacoes de baixas canonicas.
- Fallback `cliente_nome` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.844 alias de id do cliente em alocacoes de baixas canonicas

- PM-06.844 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em alocacoes de baixas canonicas.
- Fallback `cliente_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.843 fallback de label em opcoes de filtro do dashboard

- PM-06.843 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `label` em opcoes de filtro do dashboard.
- Fallback por `value` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.842 alias de valor em opcoes de filtro do dashboard

- PM-06.842 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `value` em opcoes de filtro do dashboard.
- Fallback `valor` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.841 fallback de label em opcoes de evento operacional

- PM-06.841 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js consolidou candidatos derivados de `label` em opcoes de evento operacional.
- Fallbacks `numero - nome`, `eventName`, `eventNumber` e `id` continuam aceitos, agora encapsulados em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.840 fallback textual de contrato em opcoes de evento operacional

- PM-06.840 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contract` em opcoes de evento operacional.
- Fallback por `contractCode` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.839 fallback de numero por contrato em opcoes de evento operacional

- PM-06.839 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e textuais para fallback de `eventNumber` em opcoes de evento operacional.
- Fallbacks `contractCode`, `contrato_codigo`, `contract` e `contrato` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.838 fallback de contractDescription em opcoes de contrato operacional

- PM-06.838 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `contractDescription` em opcoes de contrato operacional.
- Fallback pela descricao normalizada continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.837 fallback de descricao em opcoes de contrato operacional

- PM-06.837 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados, descritivos e derivados para `description` em opcoes de contrato operacional.
- Fallback por `label` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.836 fallback de nome exibido em opcoes de contrato operacional

- PM-06.836 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `name` em opcoes de contrato operacional.
- Fallbacks `contractName` e `label` continuam aceitos, agora encapsulados em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.835 fallback textual de contrato em opcoes de contrato operacional

- PM-06.835 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contract` em opcoes de contrato operacional.
- Fallbacks `contractCode` e `label` continuam aceitos, agora encapsulados em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.834 fallback de label em opcoes de contrato operacional

- PM-06.834 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, descritivos e derivados para `label` em opcoes de contrato operacional.
- Fallbacks `contractCode`, `contractName` e `id` continuam aceitos, agora encapsulados em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.833 fallback de label em opcoes financeiras legadas

- PM-06.833 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos legados, canonicos e derivados para `rotulo` em opcoes financeiras legadas.
- Fallback pelo valor legado continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.832 fallback de label em opcoes financeiras genericas

- PM-06.832 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `label` em opcoes financeiras genericas.
- Fallback pelo valor normalizado continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.831 fallback de nome exibido em opcoes de credor

- PM-06.831 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `name` em opcoes de credor.
- Fallback pelo nome canonico do credor continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.830 fallback de label em opcoes de credor

- PM-06.830 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `label` em opcoes de credor.
- Fallback pelo nome canonico do credor continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.829 alias de nome exibido em opcoes de evento do dashboard

- PM-06.829 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos de exibicao e derivados para `name` em opcoes de evento do dashboard.
- Fallbacks `name`, `nome`, `eventName` e `label` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.828 alias textual de contrato em opcoes de evento do dashboard

- PM-06.828 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contract` em opcoes de evento do dashboard.
- Fallbacks `contrato`, `contractCode` e `label` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.827 aliases de data inicial em opcoes de evento do dashboard

- PM-06.827 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `startDate` em opcoes de evento do dashboard.
- Fallbacks `dataInicio` e `data_inicio` continuam aceitos, agora encapsulados em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.826 alias de nome do cliente em opcoes de evento do dashboard

- PM-06.826 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientName` em opcoes de evento do dashboard.
- Fallback `cliente_nome` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.825 alias de id do cliente em opcoes de evento do dashboard

- PM-06.825 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em opcoes de evento do dashboard.
- Fallback `cliente_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.824 fallback de label em opcoes de evento do dashboard

- PM-06.824 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `label` em opcoes de evento do dashboard.
- Fallback derivado `numero - nome` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.823 aliases de codigo do contrato em opcoes de evento do dashboard

- PM-06.823 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados, textuais e derivados para `contractCode` em opcoes de evento do dashboard.
- Fallbacks `contrato_codigo`, `contract`, `contrato` e `eventNumber` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.822 alias de id do contrato em opcoes de evento do dashboard

- PM-06.822 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em opcoes de evento do dashboard.
- Fallback `contrato_operacional_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.821 aliases de numero em opcoes de evento do dashboard

- PM-06.821 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e de contrato para `eventNumber` em opcoes de evento do dashboard.
- Fallbacks `evento_numero`, `numero`, `contractCode`, `contrato_codigo`, `contract` e `contrato` continuam aceitos.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.820 aliases de nome em opcoes de evento do dashboard

- PM-06.820 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e de exibicao para `eventName` em opcoes de evento do dashboard.
- Fallbacks `evento_nome`, `name` e `nome` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.819 alias de id em opcoes de evento do dashboard

- PM-06.819 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventId` em opcoes de evento do dashboard.
- Fallback `evento_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.818 alias de nome exibido em opcoes de contrato do dashboard

- PM-06.818 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos de exibicao e derivados para `name` em opcoes de contrato do dashboard.
- Fallbacks `name`, `nome`, `contractName` e `label` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.817 alias textual de contrato em opcoes de contrato do dashboard

- PM-06.817 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contract` em opcoes de contrato do dashboard.
- Fallbacks `contrato`, `contractCode` e `label` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.816 alias de nome do cliente em opcoes de contrato do dashboard

- PM-06.816 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientName` em opcoes de contrato do dashboard.
- Fallback `cliente_nome` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.815 alias de id do cliente em opcoes de contrato do dashboard

- PM-06.815 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em opcoes de contrato do dashboard.
- Fallback `cliente_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.814 fallback de label em opcoes de contrato do dashboard

- PM-06.814 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, descritivos e derivados para `label` em opcoes de contrato do dashboard.
- Fallbacks `contractDescription`, `contrato_operacional_label`, `contractCode`, `contractName` e `id` continuam aceitos.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.813 aliases de nome em opcoes de contrato do dashboard

- PM-06.813 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e de exibicao para `contractName` em opcoes de contrato do dashboard.
- Fallbacks `name` e `nome` continuam aceitos, agora encapsulados em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.812 aliases de codigo em opcoes de contrato do dashboard

- PM-06.812 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e textuais para `contractCode` em opcoes de contrato do dashboard.
- Fallbacks `contrato_codigo`, `contract` e `contrato` continuam aceitos, agora encapsulados em helpers locais.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.811 alias de id em opcoes de contrato do dashboard

- PM-06.811 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em opcoes de contrato do dashboard.
- Fallback `contrato_operacional_id` continua aceito, agora encapsulado em helper local.
- Guardrail: nenhum alias, endpoint, migration, congelamento, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.810 fallback de label em opcoes de entidade do dashboard

- PM-06.810 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, descritivos e derivados para `label` em opcoes de entidade do dashboard.
- O fallback `description` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.809 aliases de nome do cliente em opcoes de entidade do dashboard

- PM-06.809 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e de exibicao para `clientName` em opcoes de entidade do dashboard.
- Os fallbacks `cliente_nome`, `name`, `nome` e `label` ficaram em helpers proprios, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.808 alias de id do cliente em opcoes de entidade do dashboard

- PM-06.808 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em opcoes de entidade do dashboard.
- O fallback `cliente_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.807 fallback de label em opcoes de evento operacional

- PM-06.807 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, descritivos e derivados para `label` em opcoes de evento operacional.
- O fallback derivado `numero - nome` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.806 alias de nome do cliente em opcoes de evento operacional

- PM-06.806 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientName` em opcoes de evento operacional.
- O fallback `cliente_nome` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.805 alias de id do cliente em opcoes de evento operacional

- PM-06.805 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em opcoes de evento operacional.
- O fallback `cliente_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.804 alias textual de contrato em opcoes de evento operacional

- PM-06.804 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contract` em opcoes de evento operacional.
- O fallback `contrato` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.803 aliases de codigo do contrato em opcoes de evento operacional

- PM-06.803 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e textuais para `contractCode` em opcoes de evento operacional.
- O fallback `contrato_codigo` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.802 alias de id do contrato em opcoes de evento operacional

- PM-06.802 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em opcoes de evento operacional.
- O fallback `contrato_operacional_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.801 aliases de data inicial em opcoes de evento operacional

- PM-06.801 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `startDate` em opcoes de evento operacional.
- Os fallbacks `dataInicio` e `data_inicio` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.800 aliases de id em opcoes de evento operacional

- PM-06.800 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e serializados para `eventId` em opcoes de evento operacional.
- Os fallbacks `id` e `value` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.799 aliases de numero em opcoes de evento operacional

- PM-06.799 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e de contrato para `eventNumber` em opcoes de evento operacional.
- O fallback `numero` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.798 alias de nome em opcoes de evento operacional

- PM-06.798 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventName` em opcoes de evento operacional.
- O fallback `nome` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.797 alias de descricao em opcoes de contrato operacional

- PM-06.797 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `description` em opcoes de contrato operacional.
- O fallback `descricao` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.796 alias de nome exibido em opcoes de contrato operacional

- PM-06.796 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `name` em opcoes de contrato operacional.
- O fallback `nome` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.795 alias textual de contrato em opcoes de contrato operacional

- PM-06.795 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e derivados para `contract` em opcoes de contrato operacional.
- O fallback `contrato` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.794 fallback de label em opcoes de contrato operacional

- PM-06.794 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e derivados para `label` em opcoes de contrato operacional.
- O fallback `contractDescription` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.793 alias de nome do cliente em opcoes de contrato operacional

- PM-06.793 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientName` em opcoes de contrato operacional.
- O fallback `cliente_nome` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.792 alias de id do cliente em opcoes de contrato operacional

- PM-06.792 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em opcoes de contrato operacional.
- O fallback `cliente_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.791 aliases de nome em opcoes de contrato operacional

- PM-06.791 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e de exibicao para `contractName` em opcoes de contrato operacional.
- Os fallbacks `name` e `nome` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.790 aliases de codigo em opcoes de contrato operacional

- PM-06.790 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e textuais para `contractCode` em opcoes de contrato operacional.
- Os fallbacks `contrato_codigo`, `contract` e `contrato` ficaram em helpers proprios, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.789 aliases de id em opcoes de contrato operacional

- PM-06.789 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e serializados para id de contrato operacional.
- Os fallbacks `contrato_operacional_id`, `id` e `value` ficaram em helpers proprios, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.788 fallback de label em opcoes financeiras legadas

- PM-06.788 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos legados e canonicos para `rotulo` ao gerar opcoes financeiras legadas.
- O fallback canonico `label` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.787 fallback canonico em opcoes financeiras legadas

- PM-06.787 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos legados e canonicos para `valor` ao gerar opcoes financeiras legadas.
- O fallback canonico `value` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.786 alias de rotulo em opcoes financeiras genericas

- PM-06.786 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `label` em opcoes financeiras.
- O fallback `rotulo` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.785 alias de valor em opcoes financeiras genericas

- PM-06.785 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `value` em opcoes financeiras.
- O fallback `valor` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.784 alias de busca em filtros de baixas canonicas

- PM-06.784 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `search` em filtros normalizados de baixas canonicas.
- O fallback `busca` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.783 alias de natureza em filtros de baixas canonicas

- PM-06.783 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `nature` em filtros normalizados de baixas canonicas.
- O fallback `natureza` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.782 alias de data final em filtros de baixas canonicas

- PM-06.782 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `endDate` em filtros normalizados de baixas canonicas.
- O fallback `data_final` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.781 alias de data inicial em filtros de baixas canonicas

- PM-06.781 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `startDate` em filtros normalizados de baixas canonicas.
- O fallback `data_inicial` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.780 aliases de id do cliente em filtros de baixas canonicas

- PM-06.780 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em filtros normalizados de baixas canonicas.
- Os fallbacks `cliente_id` e `cliente` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.779 aliases de id do evento em filtros de baixas canonicas

- PM-06.779 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventId` em filtros normalizados de baixas canonicas.
- Os fallbacks `costCenterId`, `evento_id` e `evento` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.778 aliases de id do contrato em filtros de baixas canonicas

- PM-06.778 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em filtros normalizados de baixas canonicas.
- Os fallbacks `contrato_operacional_id` e `contrato_operacional` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.777 alias de busca em filtros de ledger financeiro

- PM-06.777 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `search` em filtros normalizados de ledger.
- O fallback `busca` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.776 alias de natureza em filtros de ledger financeiro

- PM-06.776 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `nature` em filtros normalizados de ledger.
- O fallback `natureza` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.775 alias de data final em filtros de ledger financeiro

- PM-06.775 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `endDate` em filtros normalizados de ledger.
- O fallback `data_final` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.774 alias de data inicial em filtros de ledger financeiro

- PM-06.774 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `startDate` em filtros normalizados de ledger.
- O fallback `data_inicial` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.773 aliases de id do cliente em filtros de ledger financeiro

- PM-06.773 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em filtros normalizados de ledger.
- Os fallbacks `cliente_id` e `cliente` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.772 aliases de id do evento em filtros de ledger financeiro

- PM-06.772 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventId` em filtros normalizados de ledger.
- Os fallbacks `costCenterId`, `evento_id` e `evento` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.771 aliases de id do contrato em filtros de ledger financeiro

- PM-06.771 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em filtros normalizados de ledger.
- Os fallbacks `contrato_operacional_id` e `contrato_operacional` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.770 alias de sourceDetail em filtros de ledger financeiro

- PM-06.770 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceDetail` em filtros normalizados de ledger.
- O fallback `source_detail` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.769 alias de originId em filtros de ledger financeiro

- PM-06.769 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `originId` em filtros normalizados de ledger.
- O fallback `origin_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.768 alias de sourceId em filtros de ledger financeiro

- PM-06.768 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceId` em filtros normalizados de ledger.
- O fallback `source_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.767 alias de origem em filtros de ledger financeiro

- PM-06.767 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `origin` em filtros normalizados de ledger.
- O fallback `origem` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.766 aliases de id do cliente em filtros FCF

- PM-06.766 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `clientId` em filtros FCF.
- Os fallbacks `cliente_id` e `cliente` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.765 aliases de id do evento em filtros FCF

- PM-06.765 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `eventId` em filtros FCF.
- Os fallbacks `costCenterId`, `evento_id` e `evento` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.764 aliases de id do contrato em filtros FCF

- PM-06.764 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `contractId` em filtros FCF.
- Os fallbacks `contrato_operacional_id` e `contrato_operacional` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.763 alias de nome do credor em filtros FCF

- PM-06.763 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `creditor` em filtros FCF.
- O fallback `credor` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.762 alias de tipo de divida em filtros FCF

- PM-06.762 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `type` em filtros FCF.
- O fallback `tipo` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.761 aliases de origem da movimentacao em filtros FCF

- PM-06.761 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceType` em filtros FCF.
- Os fallbacks `movementSourceType` e `origem_movimentacao` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.760 alias de busca em query de ledger financeiro

- PM-06.760 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `search` em overrides da query de ledger financeiro.
- O fallback `busca` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.759 alias de detalhe de origem em query de ledger financeiro

- PM-06.759 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceDetail` em overrides da query de ledger financeiro.
- O fallback `source_detail` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.758 aliases de id de origem em query de ledger financeiro

- PM-06.758 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceId` em overrides da query de ledger financeiro.
- Os fallbacks `source_id`, `originId` e `origin_id` ficaram em helpers proprios, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.757 alias de origem em query de ledger financeiro

- PM-06.757 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `origin` em overrides da query de ledger financeiro.
- O fallback `origem` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.756 alias de natureza em query de ledger financeiro

- PM-06.756 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `nature` em overrides da query de ledger financeiro.
- O fallback `natureza` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.755 alias de busca em query de obrigacoes financeiras

- PM-06.755 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `search` em overrides da query de obrigacoes financeiras.
- O fallback `busca` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.754 aliases de id do cliente em query de baixas canonicas

- PM-06.754 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e vindos de `query` para `clientId` na query de baixas canonicas.
- Os fallbacks `cliente_id` e `cliente` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.753 aliases de id do evento em query de baixas canonicas

- PM-06.753 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e vindos de `query` para `eventId` na query de baixas canonicas.
- Os fallbacks `costCenterId`, `evento_id` e `evento` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.752 aliases de id do contrato em query de baixas canonicas

- PM-06.752 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e vindos de `query` para `contractId` na query de baixas canonicas.
- Os fallbacks `contrato_operacional_id` e `contrato_operacional` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.751 alias de busca em query de baixas canonicas

- PM-06.751 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `search` em overrides da query de baixas canonicas.
- O fallback `busca` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.750 alias de data final em query de baixas canonicas

- PM-06.750 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `endDate` em overrides da query de baixas canonicas.
- O fallback `data_final` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.749 alias de data inicial em query de baixas canonicas

- PM-06.749 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `startDate` em overrides da query de baixas canonicas.
- O fallback `data_inicial` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.748 aliases de id do cliente em query FCF

- PM-06.748 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e vindos de `query` para `clientId` na query FCF.
- Os fallbacks `cliente_id` e `cliente` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.747 aliases de id do evento em query FCF

- PM-06.747 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e vindos de `query` para `eventId` na query FCF.
- Os fallbacks `costCenterId`, `evento_id` e `evento` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.746 aliases de id do contrato em query FCF

- PM-06.746 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e vindos de `query` para `contractId` na query FCF.
- Os fallbacks `contrato_operacional_id` e `contrato_operacional` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.745 aliases de origem da movimentacao em query FCF

- PM-06.745 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `sourceType` em overrides da query FCF.
- Os fallbacks `movementSourceType` e `origem_movimentacao` ficaram em helper proprio, preservando os mesmos valores aceitos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.744 alias de tipo de divida em query FCF

- PM-06.744 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `type` em overrides da query FCF.
- O fallback `tipo` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.743 alias de nome do credor em query FCF

- PM-06.743 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `creditor` em overrides da query FCF.
- O fallback `credor` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.742 alias de id do credor em query FCF

- PM-06.742 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `creditorId` em overrides da query FCF.
- O fallback `credor_id` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.741 alias de data final em query FCF

- PM-06.741 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `endDate` em overrides da query FCF.
- O fallback `data_final` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.740 alias de data inicial em query FCF

- PM-06.740 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para `startDate` em overrides da query FCF.
- O fallback `data_inicial` ficou em helper proprio, preservando o mesmo valor aceito.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.739 alias de nome do credor em opcoes FCF

- PM-06.739 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e textuais para nome de credor em opcoes FCF.
- O espelho `credor_nome` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.738 alias de id do credor em opcoes FCF

- PM-06.738 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, legados e serializados para id de credor em opcoes FCF.
- O espelho `credor_id` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.737 alias de id do credor em filtros FCF

- PM-06.737 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos e espelhos canonicos/legados para `creditorId` em filtros FCF.
- O espelho `credor_id` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.736 alias de data final em filtros FCF

- PM-06.736 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos e espelhos canonicos/legados para `endDate` em filtros FCF.
- O espelho `data_final` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.735 alias de data inicial em filtros FCF

- PM-06.735 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos e espelhos canonicos/legados para `startDate` em filtros FCF.
- O espelho `data_inicial` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.734 alias textual credor em parcelas FCF

- PM-06.734 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o fallback legado `credor` dos demais candidatos de credor em parcelas FCF.
- A resolucao de `creditorName` e `creditor` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.733 fallback textual creditor em parcelas FCF

- PM-06.733 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato textual `creditor` dos demais fallbacks de credor em parcelas FCF.
- A resolucao de `creditorName` e `creditor` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.732 alias de nome do credor em parcelas FCF

- PM-06.732 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou `credor_nome` em helper proprio de candidatos legados em parcelas FCF.
- A resolucao continua preferindo `creditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.731 fallback de descricao da divida em dividas FCF

- PM-06.731 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou `description` de `debtDescription` nos candidatos de descricao em dividas FCF.
- `debtDescription` ficou isolado em helper proprio de fallback, preservando o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.730 alias textual credor em dividas FCF

- PM-06.730 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o fallback legado `credor` dos demais candidatos de credor em dividas FCF.
- A resolucao de `creditorName` e `creditor` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.729 fallback textual creditor em dividas FCF

- PM-06.729 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato textual `creditor` dos demais fallbacks de credor em dividas FCF.
- A resolucao de `creditorName` e `creditor` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.728 alias de nome do credor em dividas FCF

- PM-06.728 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou `credor_nome` em helper proprio de candidatos legados em dividas FCF.
- A resolucao continua preferindo `creditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.727 alias textual de credor em grupos de credor FCF

- PM-06.727 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para alias textual de credor em grupos de credor FCF.
- O espelho `credor` preserva o mesmo valor publicado a partir de `creditor`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.726 alias de nome do credor em grupos de credor FCF

- PM-06.726 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para nome do credor em grupos de credor FCF.
- O espelho `credor_nome` preserva o mesmo valor publicado a partir de `creditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.725 alias de id do credor em grupos de credor FCF

- PM-06.725 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id do credor em grupos de credor FCF.
- O espelho `credor_id` preserva o mesmo valor publicado a partir de `creditorId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.724 alias de lista de dividas em grupos de credor FCF

- PM-06.724 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para lista de dividas em grupos de credor FCF.
- O espelho `dividas` preserva o mesmo valor publicado a partir de `debts`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.723 alias de lista de parcelas em grupos de divida FCF

- PM-06.723 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para lista de parcelas em grupos de divida FCF.
- O espelho `parcelas` preserva o mesmo valor publicado a partir de `installments`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.722 alias de parcelas vencidas em grupos FCF

- PM-06.722 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para parcelas vencidas em grupos FCF.
- O espelho `quantidade_parcelas_vencidas` preserva o mesmo valor publicado em grupos de divida e credor.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.721 aliases de parcelas abertas em grupos FCF

- PM-06.721 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou aliases legados `openInstallmentsCount` e `quantidade_parcelas_abertas` em grupos FCF.
- Os espelhos de parcelas abertas preservam o mesmo valor publicado a partir de `pendingInstallmentsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.720 alias de quantidade de parcelas pendentes em grupos FCF

- PM-06.720 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para parcelas pendentes em grupos FCF.
- O espelho `quantidade_parcelas_pendentes` preserva o mesmo valor publicado a partir de `pendingInstallmentsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.719 alias de quantidade total de parcelas em grupos FCF

- PM-06.719 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade total de parcelas em grupos FCF.
- O espelho `quantidade_parcelas` preserva o mesmo valor publicado a partir de `installmentsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.718 alias de subtotal em aberto em grupos FCF

- PM-06.718 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para subtotal pendente em grupos FCF.
- O espelho `subtotal_em_aberto` preserva o mesmo valor publicado em grupos de divida e credor.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.717 alias de subtotal de contas pendentes em grupos FCF

- PM-06.717 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para subtotal de contas pendentes em grupos FCF.
- O espelho `subtotal_contas_pendentes` preserva o mesmo valor publicado a partir de `subtotalPendingAccountsAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.716 alias de subtotal pago em grupos FCF

- PM-06.716 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para subtotal pago em grupos FCF.
- O espelho `subtotal_pago` preserva o mesmo valor publicado a partir de `subtotalPaidAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.715 alias de subtotal devido em grupos FCF

- PM-06.715 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para subtotal devido em grupos FCF.
- O espelho `subtotal_devido` preserva o mesmo valor publicado a partir de `subtotalDueAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.714 alias de descricao em grupos de divida FCF

- PM-06.714 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos, fallback de descricao de divida e legado para descricao em grupos de divida FCF.
- O espelho `descricao` preserva o mesmo valor publicado a partir de `description`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.713 alias de nome do credor em grupos de divida FCF

- PM-06.713 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para nome do credor em grupos de divida FCF.
- O espelho `credor_nome` preserva o mesmo valor publicado a partir de `creditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.712 alias de id do credor em grupos de divida FCF

- PM-06.712 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id do credor em grupos de divida FCF.
- O espelho `credor_id` preserva o mesmo valor publicado a partir de `creditorId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.711 alias de id da divida em grupos FCF

- PM-06.711 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id da divida em grupos FCF.
- O espelho `divida_id` preserva o mesmo valor publicado a partir de `debtId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.710 alias de estatisticas no response FCF

- PM-06.710 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para estatisticas no response FCF.
- O espelho `estatisticas` preserva o mesmo valor publicado a partir de `statistics`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.709 alias de totais no response FCF

- PM-06.709 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para totais no response FCF.
- O espelho `totais` preserva o mesmo valor publicado a partir de `totals`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.708 alias de opcoes no response FCF

- PM-06.708 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para opcoes no response FCF.
- O espelho `opcoes` preserva o mesmo valor publicado a partir de `filterOptions`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.707 alias de filtros no response FCF

- PM-06.707 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou o espelho de filtros no response FCF.
- O espelho `filtros` preserva o mesmo valor publicado a partir de `filters`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.706 alias de grupos de credor no response FCF

- PM-06.706 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para grupos de credor no response FCF.
- O espelho `grupos_credor` preserva o mesmo valor publicado a partir de `creditorGroups`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.705 alias de lista de movimentacoes no response FCF

- PM-06.705 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para lista de movimentacoes no response FCF.
- O espelho `movimentacoes_financiamento` preserva o mesmo valor publicado a partir de `financingMovements`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.704 alias de lista de parcelas no response FCF

- PM-06.704 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para lista de parcelas no response FCF.
- O espelho `parcelas` preserva o mesmo valor publicado a partir de `installments`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.703 alias de lista de dividas no response FCF

- PM-06.703 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidato canonico e legado para lista de dividas no response FCF.
- O espelho `dividas` preserva o mesmo valor publicado a partir de `debts`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.702 alias de quantidade de movimentacoes manuais em estatisticas FCF

- PM-06.702 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de movimentacoes manuais em estatisticas FCF.
- O espelho `quantidade_movimentacoes_financiamento_manuais` preserva o mesmo valor publicado a partir de `manualFinancingMovementsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.701 alias de quantidade de movimentacoes automaticas em estatisticas FCF

- PM-06.701 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de movimentacoes automaticas em estatisticas FCF.
- O espelho `quantidade_movimentacoes_financiamento_automaticas` preserva o mesmo valor publicado a partir de `automaticFinancingMovementsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.700 alias de quantidade de movimentacoes vencidas em estatisticas FCF

- PM-06.700 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de movimentacoes vencidas em estatisticas FCF.
- O espelho `quantidade_movimentacoes_financiamento_vencidas` preserva o mesmo valor publicado a partir de `overdueFinancingMovementsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.699 alias de quantidade de movimentacoes em estatisticas FCF

- PM-06.699 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de movimentacoes em estatisticas FCF.
- O espelho `quantidade_movimentacoes_financiamento` preserva o mesmo valor publicado a partir de `financingMovementsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.698 alias de quantidade de parcelas vencidas em estatisticas FCF

- PM-06.698 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de parcelas vencidas em estatisticas FCF.
- O espelho `quantidade_parcelas_vencidas` preserva o mesmo valor publicado a partir de `overdueInstallmentsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.697 alias de quantidade de parcelas em estatisticas FCF

- PM-06.697 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de parcelas em estatisticas FCF.
- O espelho `quantidade_parcelas` preserva o mesmo valor publicado a partir de `installmentsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.696 alias de rotulo de tipo de fluxo em movimentacoes FCF

- PM-06.696 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de tipo de fluxo em movimentacoes FCF.
- O espelho `tipo_fluxo_display` preserva o mesmo valor publicado a partir de `flowTypeLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.695 alias de tipo de fluxo em movimentacoes FCF

- PM-06.695 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para tipo de fluxo em movimentacoes FCF.
- O espelho `tipo_fluxo` preserva o mesmo valor publicado a partir de `flowType`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.694 alias de rotulo de categoria em movimentacoes FCF

- PM-06.694 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de categoria em movimentacoes FCF.
- O espelho `categoria_display` preserva o mesmo valor publicado a partir de `categoryLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.693 alias de categoria em movimentacoes FCF

- PM-06.693 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para categoria em movimentacoes FCF.
- O espelho `categoria` preserva o mesmo valor publicado a partir de `category`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.692 alias em portugues de descricao em movimentacoes FCF

- PM-06.692 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `descricao` para descricao em movimentacoes FCF.
- O espelho `descricao` preserva o mesmo valor publicado a partir de `description`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.691 alias tecnico de descricao em movimentacoes FCF

- PM-06.691 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato canonico `description` do alias legado `financingMovementDescription` em movimentacoes FCF.
- O espelho `financingMovementDescription` preserva o mesmo valor publicado a partir de `description`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.690 alias de descricao da divida em movimentacoes FCF

- PM-06.690 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para descricao da divida em movimentacoes FCF.
- O espelho `descricao_divida` preserva o mesmo valor publicado a partir de `debtDescription`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.689 alias de nome do credor da divida em movimentacoes FCF

- PM-06.689 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `nome_credor_divida` para nome do credor da divida em movimentacoes FCF.
- O espelho `nome_credor_divida` preserva o mesmo valor publicado a partir de `debtCreditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.688 alias em portugues do credor da divida em movimentacoes FCF

- PM-06.688 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `credor_divida` para credor da divida em movimentacoes FCF.
- O espelho `credor_divida` preserva o mesmo valor publicado a partir de `debtCreditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.687 alias tecnico do credor da divida em movimentacoes FCF

- PM-06.687 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato canonico `debtCreditorName` do alias legado `debtCreditor` em movimentacoes FCF.
- O espelho `debtCreditor` preserva o mesmo valor publicado a partir de `debtCreditorName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.686 alias de id do credor da divida em movimentacoes FCF

- PM-06.686 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id do credor da divida em movimentacoes FCF.
- O espelho `credor_divida_id` preserva o mesmo valor publicado a partir de `debtCreditorId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.685 alias de id da divida em movimentacoes FCF

- PM-06.685 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id da divida em movimentacoes FCF.
- O espelho `divida_id` preserva o mesmo valor publicado a partir de `debtId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.684 alias em portugues de origem automatica em movimentacoes FCF

- PM-06.684 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `entrada_automatica_divida` para origem automatica em movimentacoes FCF.
- O espelho `entrada_automatica_divida` preserva o mesmo valor publicado a partir de `automaticFromDebt`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.683 alias tecnico de origem automatica em movimentacoes FCF

- PM-06.683 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato canonico `automaticFromDebt` do alias legado `isAutomaticFromDebt` em movimentacoes FCF.
- O espelho `isAutomaticFromDebt` preserva o mesmo valor publicado a partir de `automaticFromDebt`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.682 alias em portugues de rotulo de origem em movimentacoes FCF

- PM-06.682 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `origem_movimentacao_display` para rotulo de origem em movimentacoes FCF.
- O espelho `origem_movimentacao_display` preserva o mesmo valor publicado a partir de `sourceTypeLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.681 alias tecnico de rotulo de origem em movimentacoes FCF

- PM-06.681 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato canonico `sourceTypeLabel` do alias legado `movementSourceTypeLabel` em movimentacoes FCF.
- O espelho `movementSourceTypeLabel` preserva o mesmo valor publicado a partir de `sourceTypeLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.680 alias em portugues de origem em movimentacoes FCF

- PM-06.680 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `origem_movimentacao` para origem em movimentacoes FCF.
- O espelho `origem_movimentacao` preserva o mesmo valor publicado a partir de `sourceType`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.679 alias tecnico de origem em movimentacoes FCF

- PM-06.679 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato canonico `sourceType` do alias legado `movementSourceType` em movimentacoes FCF.
- O espelho `movementSourceType` preserva o mesmo valor publicado a partir de `sourceType`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.678 alias de dias em atraso em movimentacoes FCF

- PM-06.678 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para dias em atraso em movimentacoes FCF.
- O espelho `dias_atraso` preserva o mesmo valor publicado a partir de `overdueDays`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.677 alias de rotulo de status em movimentacoes FCF

- PM-06.677 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de status em movimentacoes FCF.
- O espelho `status_display` preserva o mesmo valor publicado a partir de `statusLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.676 alias de data de realizacao em movimentacoes FCF

- PM-06.676 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para data de realizacao em movimentacoes FCF.
- O espelho `data_realizacao` preserva o mesmo valor publicado a partir de `realizedDate`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.675 alias de data prevista em movimentacoes FCF

- PM-06.675 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para data prevista em movimentacoes FCF.
- O espelho `data_prevista` preserva o mesmo valor publicado a partir de `plannedDate`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.674 alias de valor pendente de realizacao em movimentacoes FCF

- PM-06.674 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para valor pendente de realizacao em movimentacoes FCF.
- O espelho `valor_pendente_realizacao` preserva o mesmo valor publicado a partir de `pendingRealizationAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.673 alias de valor realizado em movimentacoes FCF

- PM-06.673 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para valor realizado em movimentacoes FCF.
- O espelho `valor_realizado` preserva o mesmo valor publicado a partir de `realizedAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.672 alias de valor previsto em movimentacoes FCF

- PM-06.672 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para valor previsto em movimentacoes FCF.
- O espelho `valor_previsto` preserva o mesmo valor publicado a partir de `plannedAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.671 alias de baixa manual em parcelas FCF

- PM-06.671 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para baixa manual em parcelas FCF.
- O espelho `baixado_manualmente` preserva o mesmo valor publicado a partir de `manuallySettled`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.670 alias de dias em atraso em parcelas FCF

- PM-06.670 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para dias em atraso em parcelas FCF.
- O espelho `dias_atraso` preserva o mesmo valor publicado a partir de `overdueDays`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.669 alias de rotulo de status em parcelas FCF

- PM-06.669 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de status em parcelas FCF.
- O espelho `status_display` preserva o mesmo valor publicado a partir de `statusLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.668 alias de disponibilidade para pagamento em parcelas FCF

- PM-06.668 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para disponibilidade de pagamento em parcelas FCF.
- O espelho `disponivel_para_pagamento` preserva o mesmo valor publicado a partir de `availableForPayment`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.667 alias de saldo em aberto em parcelas FCF

- PM-06.667 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js isolou o fallback legado `saldo_em_aberto` para pendencia de pagamento em parcelas FCF.
- O espelho `saldo_em_aberto` preserva o mesmo valor publicado a partir de `pendingPaymentAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.666 alias de contas pendentes em parcelas FCF

- PM-06.666 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para contas pendentes em parcelas FCF.
- O espelho `contas_pendentes` preserva o mesmo valor publicado a partir de `pendingAccountsAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.665 alias de valor pendente de pagamento em parcelas FCF

- PM-06.665 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou o candidato canonico `pendingPaymentAmount` do alias legado direto em parcelas FCF.
- O espelho `valor_pendente_pagamento` preserva o mesmo valor publicado a partir de `pendingPaymentAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.664 alias de valor pago em parcelas FCF

- PM-06.664 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para valor pago em parcelas FCF.
- O espelho `valor_pago` preserva o mesmo valor publicado a partir de `paidAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.663 alias de valor total devido em parcelas FCF

- PM-06.663 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para valor total devido em parcelas FCF.
- O espelho `valor_total_devido` preserva o mesmo valor publicado a partir de `totalDueAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.662 alias de vencimento atual em parcelas FCF

- PM-06.662 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para vencimento atual em parcelas FCF.
- O espelho `data_vencimento_atual` preserva o mesmo valor publicado a partir de `dueDate`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.661 alias de vencimento original em parcelas FCF

- PM-06.661 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para vencimento original em parcelas FCF.
- O espelho `data_vencimento_original` preserva o mesmo valor publicado a partir de `originalDueDate`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.660 aliases textuais do credor em parcelas FCF

- PM-06.660 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para nome textual do credor em parcelas FCF.
- Os espelhos `credor_nome` e `credor` preservam os mesmos valores publicados a partir de `creditorName` e `creditor`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.659 alias de id do credor em parcelas FCF

- PM-06.659 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id do credor em parcelas FCF.
- O espelho `credor_id` preserva o mesmo valor publicado a partir de `creditorId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.658 alias de rotulo de parcela FCF

- PM-06.658 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de parcela FCF.
- O espelho `rotulo_parcela` preserva o mesmo valor publicado a partir de `installmentLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.657 alias de numero de parcela FCF

- PM-06.657 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para numero de parcela FCF.
- O espelho `numero_parcela` preserva o mesmo valor publicado a partir de `installmentNumber`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.656 alias de descricao de divida em parcelas FCF

- PM-06.656 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para descricao de divida em parcelas FCF.
- O espelho `descricao_divida` preserva o mesmo valor publicado a partir de `debtDescription`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.655 alias de id de divida em parcelas FCF

- PM-06.655 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id de divida em parcelas FCF.
- O espelho `divida_id` preserva o mesmo valor publicado a partir de `debtId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.654 alias de nome de cliente em dimensoes FCF

- PM-06.654 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para nome de cliente em dimensoes FCF.
- O espelho `cliente_nome` preserva o mesmo valor publicado a partir de `clientName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.653 alias de id de cliente em dimensoes FCF

- PM-06.653 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id de cliente em dimensoes FCF.
- O espelho `cliente_id` preserva o mesmo valor publicado a partir de `clientId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.652 alias de rotulo de evento em dimensoes FCF

- PM-06.652 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de evento em dimensoes FCF.
- O espelho `evento_label` preserva o mesmo valor publicado a partir de `eventLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.651 alias de numero de evento em dimensoes FCF

- PM-06.651 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para numero de evento em dimensoes FCF.
- O espelho `evento_numero` preserva o mesmo valor publicado a partir de `eventNumber`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.650 alias de nome de evento em dimensoes FCF

- PM-06.650 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para nome de evento em dimensoes FCF.
- O espelho `evento_nome` preserva o mesmo valor publicado a partir de `eventName`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.649 alias de id de evento em dimensoes FCF

- PM-06.649 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id de evento em dimensoes FCF.
- O espelho `evento_id` preserva o mesmo valor publicado a partir de `eventId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.648 alias curto de contrato em dimensoes FCF

- PM-06.648 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou o alias curto `contract` em dimensoes FCF por helper local dedicado.
- O espelho `contract` preserva o mesmo valor publicado a partir de `contractLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.647 alias de rotulo de contrato operacional em dimensoes FCF

- PM-06.647 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de contrato operacional em dimensoes FCF.
- O espelho `contrato_operacional_label` preserva o mesmo valor publicado a partir de `contractLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.646 alias de codigo de contrato operacional em dimensoes FCF

- PM-06.646 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para codigo de contrato operacional em dimensoes FCF.
- O espelho `contrato_codigo` preserva o mesmo valor publicado a partir de `contractCode`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.645 alias de id de contrato operacional em dimensoes FCF

- PM-06.645 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id de contrato operacional em dimensoes FCF.
- O espelho `contrato_operacional_id` preserva o mesmo valor publicado a partir de `contractId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.644 alias de data de contratacao da divida FCF

- PM-06.644 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para data de contratacao da divida FCF.
- O espelho `data_contratacao` preserva o mesmo valor publicado a partir de `contractedDate`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.643 alias de rotulo de status da divida FCF

- PM-06.643 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo de status da divida FCF.
- O espelho `status_display` preserva o mesmo valor publicado a partir de `statusLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.642 alias de rotulo do tipo da divida FCF

- PM-06.642 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para rotulo do tipo da divida FCF.
- O espelho `tipo_display` preserva o mesmo valor publicado a partir de `typeLabel`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.641 alias de tipo da divida FCF

- PM-06.641 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para tipo da divida FCF.
- O espelho `tipo` preserva o mesmo valor publicado a partir de `type`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.640 alias de descricao da divida FCF

- PM-06.640 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para descricao da divida FCF.
- O espelho `descricao` preserva o mesmo valor publicado a partir de `description`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.639 aliases textuais do credor da divida FCF

- PM-06.639 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para nome textual do credor da divida FCF.
- Os espelhos `credor_nome` e `credor` preservam os mesmos valores publicados a partir de `creditorName` e `creditor`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.638 alias de id do credor da divida FCF

- PM-06.638 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para id do credor da divida FCF.
- O espelho `credor_id` preserva o mesmo valor publicado a partir de `creditorId`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.637 alias de quantidade de parcelas da divida FCF

- PM-06.637 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para quantidade de parcelas da divida FCF.
- O espelho `quantidade_parcelas` preserva o mesmo valor publicado a partir de `installmentsCount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.636 alias de valor contratado da divida FCF

- PM-06.636 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js separou candidatos canonicos e legados para valor contratado da divida FCF.
- O espelho `valor_contratado` preserva o mesmo valor publicado a partir de `contractedAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.635 helpers de resultado do fluxo FCF

- PM-06.635 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de resultado do fluxo FCF em helpers locais.
- Os espelhos `resultadoFinanceiro` e `resultado_financeiro` preservam os mesmos valores publicados a partir de `financialResultAmount`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.634 helpers de direcao do fluxo FCF

- PM-06.634 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de direcao do fluxo FCF em helpers locais.
- Os espelhos `entradas` e `saidas` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Estado atual

- A aplicacao continua em Django server-side render.
- A arquitetura foi organizada com uma separacao inspirada em Angular: views finas, selectors para leitura, services para escrita/regras de negocio, guards de permissao e templates compartilhados.
- As melhorias recentes nao exigiram mudanca de Nginx.
- A ultima rodada gerou migracoes de integridade e origem explicita de despesas operacionais.
- Os pacotes locais de teste avancado continuam fora do fluxo de producao.

## Melhorias feitas

### Performance e queries

- Otimizacao da tela de custos por evento em `caixa/selectors_dashboard.py`.
- Pagamentos de `EventoCustoServico` agora sao resumidos por agregacao no banco, em vez de carregar cada objeto somente para calcular totais.
- Pagamentos de `EventoCustoExtra` tambem passaram a ser resumidos por agregacao no banco.
- Totais abertos de receitas e despesas em `caixa/selectors_cadastros.py` agora sao calculados por agregacao no banco, sem materializar a lista inteira somente para somar saldos.
- Fallback de item inicial nas telas de pagamentos de custos de servico e custos extras agora tambem usa `prefetch_related("pagamentos")`, evitando consultas extras ao calcular saldo inicial quando o item selecionado nao esta na lista filtrada.
- Foram adicionados testes para garantir que esses resumos usam 1 query.
- Foi adicionado teste garantindo que totais de receitas/despesas calculam valores abertos com 1 query.
- Foram adicionados testes garantindo que o fallback de custo inicial mantem saldos com consultas controladas.
- Foram adicionados testes de pagina para garantir que pagamentos de custos de servico, custos extras e FCF mantem quantidade constante de queries quando o volume de registros cresce.
- Foi adicionado teste de pagina para garantir que o mes financeiro mantem quantidade constante de queries quando o volume de receitas, despesas, custos fixos, FCI e FCF cresce.
- Custos fixos agora materializam a lista ordenada uma unica vez e reaproveitam essa lista para totais, quantidades e agrupamento por categoria.
- FCF agora reaproveita as parcelas ja carregadas para contar dividas com saldo e montar a lista de dividas do contexto, removendo consultas redundantes.
- Foi adicionado teste de pagina para garantir que listas de receitas, despesas, custos fixos e FCF mantem quantidade constante de queries quando o volume de registros cresce.
- As telas de pagamentos agora filtram `situacao` no banco, em vez de carregar todos os registros e filtrar em Python:
  - custos de servico;
  - custos extras;
  - parcelas FCF.
- Os testes desses selectors cobrem a situacao legada `em_aberto` e `quitado`, mantendo `prefetch_related` para os valores pendentes exibidos no template.
- O mes financeiro agora calcula `receita_aberta` usando `saldo_a_receber`, respeitando receitas recebidas por valor menor, canceladas ou baixadas manualmente.
- Foi adicionado teste de regressao para garantir que receitas ja fechadas nao voltam a aparecer como saldo aberto no mes financeiro.
- O resumo financeiro do mes financeiro agora fica em helper proprio (`calcular_resumo_financeiro_mes`), cobrindo resultado financeiro projetado, resultado realizado, contas pendentes e deficit de caixa.
- Foi adicionado teste direto para garantir que o deficit de caixa considera somente caixa realizado positivo como disponivel.
- Os acumulados da tabela de movimentacoes do mes financeiro agora ficam em helper proprio (`aplicar_acumulados_movimentacoes_mes`).
- Foi adicionado teste direto para proteger resultado financeiro projetado/realizado acumulado e deficit de caixa progressivo.
- A montagem dos itens de movimentacao do mes financeiro foi separada em helpers para receitas e contas a pagar.
- Foi adicionado teste direto protegendo ordenacao, valores e acumulados da tabela de movimentacoes do mes financeiro.
- A montagem de contas a pagar do mes financeiro foi separada por origem: FCF, despesas, custos fixos e FCI.
- Foi adicionado teste direto para proteger os campos e a ordenacao das contas a pagar por origem.
- A resolucao de periodo do mes financeiro agora fica em helper proprio, mantendo as regras de mes padrao, datas parciais, periodo `todos` e `vencidos` com datas informadas.
- Foi adicionado teste direto cobrindo os principais cenarios de periodo do mes financeiro.
- A busca de movimentos do mes financeiro agora orquestra helpers menores para querysets base, periodo, vencidos, filtros relacionais, status, origem e materializacao ordenada.
- Foi adicionado teste direto para proteger os helpers de intervalo e vencidos usados nos querysets do mes financeiro.
- Os totais do mes financeiro agora sao consolidados em um helper unico, reaproveitando as listas ja carregadas para a tabela e evitando consultas extras desnecessarias.
- O calculo de divida vencida ficou mais resiliente para uso futuro, tratando contas sem `dias_atraso` como nao vencidas.
- Foi adicionado teste direto para proteger receitas, dividas, saldos e deficit de caixa no helper consolidado de totais do mes financeiro.
- As opcoes compartilhadas de eventos/clientes para filtros agora ficam em `caixa/selectors_opcoes_filtros.py`, reutilizadas pelo dashboard e pelo mes financeiro.
- As telas de eventos, receitas e despesas tambem passaram a reutilizar essas opcoes compartilhadas de filtro.
- A listagem recente de eventos usada na tela de custos extras agora tambem reaproveita o selector compartilhado, preservando a ordenacao por data e id para manter o ultimo evento correto.
- As telas de pagamento de custos de servico e custos extras tambem passaram a usar o selector compartilhado para eventos com custos, mantendo apenas eventos relacionados e carregando somente os campos usados no filtro.
- As opcoes de credores do FCF agora tambem ficam no selector compartilhado, reutilizadas por financiamentos e pagamentos FCF.
- O selector compartilhado de opcoes de filtro foi organizado com helpers internos para base e ordenacao de eventos, reduzindo repeticao e facilitando novas opcoes futuras.
- A API publica do selector de opcoes ficou limitada aos casos usados pelas telas; a filtragem generica por relacao agora e helper interno.
- `views_cadastros.py` foi limpo apos a centralizacao: removeu import desnecessario de `Evento`, queryset vazio de filtro substituido por lista vazia e redirect duplicado simplificado.
- A view de custo extra tambem removeu helper morto de permissao e passou a reaproveitar variaveis locais para `add/view`, evitando checagens repetidas no mesmo request.
- A view de adicionar orcamento agora reaproveita a permissao `view_orcamento` em variavel local e usa lista vazia quando a listagem auxiliar nao pode ser exibida.
- A regra de periodo rapido da lista de eventos saiu da view e foi para helper em `selectors_cadastros.py`, mantendo a view mais fina e protegendo os casos de `vencidos` com datas informadas.
- Essas opcoes carregam somente os campos usados nos selects, reduzindo trafego e memoria sem mudar o comportamento dos templates.
- Foi adicionado teste direto protegendo ordenacao e campos carregados/diferidos nas opcoes compartilhadas de filtro.
- Foi adicionado teste direto protegendo a resolucao de periodo rapido da lista de eventos.
- As listas de clientes, orcamentos e eventos agora materializam a lista uma vez e usam `len()` para `quantidade`, evitando `COUNT(*)` redundante quando a tela ja vai renderizar todos os registros.
- Foi adicionado teste de query count para garantir que clientes, orcamentos e eventos mantem consultas constantes com mais registros.
- O contexto do FCI agora materializa os investimentos uma unica vez e reaproveita a mesma lista para totais, grupos por categoria e listagem recente.
- Foi adicionado teste direto garantindo que o contexto do FCI monta totais, ordenacoes e grupos com uma unica query.
- A pagina FCI entrou no teste de performance das listas financeiras, protegendo a tela contra regressao de query count conforme o volume de investimentos cresce.
- O filtro de status do dashboard agora tambem filtra parcelas FCF pelo status da divida quando recebe status como `ativa` ou `quitada`, em vez de deixar todas as parcelas passarem.
- Foi adicionado teste direto para proteger esse filtro de status da divida no dashboard.
- O mes financeiro tambem passou a aceitar filtro por status da divida FCF (`ativa` e `quitada`), alinhando o comportamento com o dashboard.
- O formulario do mes financeiro agora exibe as opcoes `Dívida ativa` e `Dívida quitada`, e ha teste cobrindo contexto e opcao selecionada no HTML.
- A lista de status do mes financeiro passou a vir do selector, deixando o template apenas iterar opcoes de contexto como nas demais telas.
- A lista de origem do mes financeiro tambem passou a vir do selector, removendo mais um conjunto de opcoes fixas do template.
- As opcoes de filtro do mes financeiro agora ficam em helper unico, facilitando reaproveitamento futuro em endpoint JSON quando o frontend for separado.
- Foi criado o primeiro endpoint JSON para a futura separacao frontend/backend: `/api/mes-financeiro/`, reaproveitando o selector atual e serializando filtros, opcoes, totais, receitas, contas a pagar e movimentacoes.
- A serializacao do mes financeiro ficou em `caixa/serializers_mes_financeiro.py`, mantendo a view fina e criando um padrao para novos endpoints.
- Foram adicionados testes de contrato e permissao para a API do mes financeiro.
- Foram criados endpoints JSON para FCI e FCF: `/api/fci/` e `/api/fcf/`, cobrindo filtros, opcoes, totais, listagens e agrupamentos usados pelo futuro frontend.
- A serializacao comum de `Decimal`, datas e choices agora fica em `caixa/serializers_utils.py`, reaproveitada pelos contratos JSON financeiros.
- Foram adicionados testes de contrato e permissao para as APIs de FCI e FCF.
- Foi criado o endpoint inicial do dashboard Next.js: `/api/dashboard/financial-overview/`, reaproveitando os selectors do dashboard Django para KPIs, graficos, contas a pagar/receber, receitas por servico, contratos, indicadores, metas e fluxo de caixa.
- O contrato do dashboard ficou em `caixa/serializers_dashboard.py`, mantendo calculos no backend e entregando envelope `{ "data": ... }` compativel com o service atual do frontend.
- O CORS inicial para o Next.js passou a ser controlado por `CORS_ALLOWED_ORIGINS` e `CORS_ALLOW_CREDENTIALS`, sem liberar todas as origens.
- Foram adicionados testes de rota, permissao, CORS preflight e contrato JSON para o endpoint financeiro inicial do dashboard.
- A tela FCF agora monta tipos de divida e status de parcela a partir dos `CHOICES` oficiais dos modelos, evitando listas duplicadas no template.
- A tela de pagamentos FCF tambem passou a usar o selector compartilhado de tipos de divida.
- Foi adicionado teste garantindo que os filtros FCF usam essas choices e preservam a selecao no HTML.
- A tela FCI agora monta categorias, tipos de fluxo e status a partir dos `CHOICES` oficiais do modelo `Investimento`, removendo listas duplicadas do template.
- O agrupamento de investimentos por categoria tambem passou a usar os mesmos `CHOICES` do modelo para exibir o nome da categoria.
- Foi adicionado teste garantindo que os filtros FCI usam essas choices e preservam a selecao no HTML.
- A tela de custos fixos agora monta categorias e status a partir dos `CHOICES` oficiais do modelo `CustoFixo`, removendo listas duplicadas do template.
- As opcoes de recorrencia e tipo de registro dos custos fixos passaram a ficar no selector, mantendo o template apenas iterando dados prontos.
- Foi adicionado teste garantindo que os filtros de custos fixos usam essas opcoes e preservam a selecao no HTML.
- As telas de receitas e despesas agora montam status/categorias a partir dos `CHOICES` oficiais de `ReceitaOperacional` e `DespesaOperacional`.
- Foi adicionado teste garantindo que os filtros de receitas/despesas usam essas choices e preservam a selecao no HTML.
- As telas de eventos e orcamentos agora montam status a partir dos `CHOICES` oficiais de `Evento` e `Orcamento`.
- O filtro de orcamentos recentes na tela de adicionar orcamento tambem passou a usar as mesmas choices oficiais.
- Foi adicionado teste garantindo que esses filtros usam as choices dos modelos e preservam a selecao no HTML.
- Dashboard e custos por evento agora compartilham a mesma lista de status de filtro no contexto base do dashboard, removendo duplicacao nos dois templates.
- Foi adicionado teste garantindo que os dois templates usam essas opcoes compartilhadas e preservam a selecao no HTML.
- Foram adicionados testes de regressao para impedir que N+1 volte no dashboard:
  - `montar_contexto_dashboard` mantem queries constantes com mais registros.
  - `montar_contexto_custos_por_evento` mantem queries constantes com mais registros.
  - Os filtros `eventos_filtro` e `clientes_filtro` tambem sao materializados no teste para simular o uso do template.

### Seguranca, CSP e PWA

- O registro do service worker permanece protegido por Trusted Types usando a policy `rhremoto`.
- Foi adicionado teste garantindo que `pwa.js` usa `TrustedScriptURL` ao registrar `/sw.js`, evitando retorno do erro visto no Lighthouse.
- Headers de isolamento agora ficam configuraveis por ambiente:
  - `PERMISSIONS_POLICY`;
  - `CROSS_ORIGIN_OPENER_POLICY`;
  - `CROSS_ORIGIN_RESOURCE_POLICY`;
  - `X_PERMITTED_CROSS_DOMAIN_POLICIES`.
- Os valores padrao reforcam isolamento da aplicacao sem mudar telas ou fluxo financeiro.
- `.env.production.example` foi atualizado com essas variaveis.

### Autenticacao para o frontend Next.js

- Criados endpoints JSON seguros para o painel de login do Next.js:
  - `GET /api/auth/csrf/`;
  - `POST /api/auth/login/`;
  - `POST /api/auth/logout/`;
  - `GET /api/auth/session/`.
- O login usa `AuthenticationForm`, sessao Django em cookie HttpOnly, CSRF obrigatorio via `X-CSRFToken`, CORS com credenciais e allowlist de origens.
- `.env.example` e `.env.production.example` foram ajustados para incluir as origens do frontend em `CSRF_TRUSTED_ORIGINS`.
- Foram adicionados testes de contrato para CSRF, login valido, login invalido generico, sessao publica e logout exigindo CSRF.
- Revisao adicional reforcou os endpoints de auth com `never_cache`, login aceitando JSON com ou sem charset e teste de resposta nao cacheavel.

### Padronizacao de filtros

- Criado o helper `filtros_texto` em `caixa/utils_request.py`.
- Esse helper centraliza limpeza de texto vindo de `request.GET`, aplica defaults e evita repeticao de codigo.
- Views financeiras e de cadastros passaram a reutilizar esse helper:
  - `views_pagamentos.py`
  - `views_custos_fixos.py`
  - `views_investimentos.py`
  - `views_financiamentos.py`
  - `views_mes_financeiro.py`
  - `views_cadastros.py`

### Testes e seguranca contra regressao

- A suite Django passou a cobrir mais cenarios de performance.
- O pytest local tambem cobre os testes avancados instalados no ambiente de desenvolvimento.
- Os testes locais ajudam a validar:
  - comportamento financeiro;
  - permissoes;
  - filtros;
  - pagamentos;
  - query count;
  - protecao contra retorno de N+1.

### Backups

- O backup mensal automatico continua disponivel pelo comando `backup_banco_mensal`.
- A tela `/backups/` agora tem o botao `Gerar backup manual`, restrito a superusuarios e protegido por POST/CSRF.
- O backup manual cria arquivo imediatamente, mesmo que os dados estejam iguais ao ultimo backup, util para antes de deploys ou alteracoes importantes.
- O comando automatico e o botao manual reutilizam o mesmo servico de backup.
- Foram adicionados testes garantindo:
  - usuario comum nao consegue acionar backup manual;
  - superusuario cria backup manual com arquivo `.json` e metadados `.meta.json`;
  - o comando automatico continua criando backup e evitando duplicado quando nao ha alteracao.

### Arquitetura

- O arquivo `ARQUITETURA.md` documenta a organizacao atual:
  - `views_*.py` para entrada HTTP;
  - `selectors_*.py` para leitura e montagem de contexto;
  - `selectors_opcoes_filtros.py` para opcoes reutilizaveis de filtros compartilhados;
  - `services_*.py` para escritas e regras de negocio;
  - `permissions.py` como guards;
  - `shared/` e `layouts/` para reutilizacao de templates.
- Foi iniciada a quebra segura do dashboard em modulos menores:
  - `caixa/selectors_opcoes_filtros.py` concentra opcoes compartilhadas de eventos/clientes usadas em filtros do dashboard e do mes financeiro.
  - `caixa/selectors_dashboard_filtros.py` concentra resolucao de filtros e montagem dos querysets filtrados do dashboard.
  - `caixa/selectors_dashboard_urls.py` concentra helpers puros de URLs, parametros e classe CSS usados pelo dashboard.
  - `caixa/selectors_dashboard_alertas.py` concentra a montagem dos alertas do dashboard.
  - `caixa/selectors_dashboard_movimentacoes.py` concentra a montagem das movimentacoes, totais e acumulados do dashboard.
  - `caixa/selectors_dashboard_totais.py` concentra os totais basicos e financeiros do dashboard.
  - `caixa/selectors_dashboard_custos_evento.py` concentra custos por evento, resumos de pagamentos, extras e despesas manuais.
  - `caixa/selectors_dashboard_contexto.py` concentra campos de contexto, filtros visiveis, opcoes de filtros, resultados derivados e links de resumo.
  - `caixa/selectors_dashboard.py` continua como orquestrador dos contextos principais.
- Foram adicionados testes diretos para filtros/querysets, helpers de URL/parametros, alertas, movimentacoes, totais basicos/financeiros, custos por evento, contexto base e resumo do dashboard, protegendo links, cards de resumo, totais, acumulados, mapas por evento, FCO/FCI/FCF, composicao de servicos/extras/manuais, filtros visiveis e mapeamento de status para custos de evento.
- A chamada de totais financeiros agora recebe o dicionario de totais basicos, removendo uma lista longa de argumentos soltos e reduzindo risco de troca de campos.

### Deploy

- O arquivo `DEPLOY_ORACLE.md` documenta o fluxo recomendado para servidor:
  - `git pull`;
  - ativar `venv`;
  - `pip install -r requirements.txt`;
  - `python manage.py migrate`;
  - `python manage.py collectstatic --noinput`;
  - `python manage.py check`;
  - `python manage.py check --deploy`;
  - `python manage.py verificar_consistencia_financeira`;
  - `python manage.py auditar_totais_negocio --falhar-com-divergencia --validar-valores-editaveis --falhar-com-valores-editaveis`;
  - `python manage.py validar_operacao_obrigacoes --validar-canonico --validar-escrita-canonica --validar-valores-editaveis --falhar`;
  - restart do service systemd correto.

## Validacoes executadas

Ultima validacao local executada:

```text
python manage.py check
OK

python manage.py makemigrations --check --dry-run
No changes detected

python manage.py sqlmigrate caixa 0031
OK; migration de metadados/labels com operacoes (no-op)

python manage.py migrate --plan
OK; migrations recentes revisadas ate caixa.0033_cadastro_credores_dividas

python manage.py test
375 testes OK na ultima validacao local desta leva operacional

npm run typecheck
OK

npm run build
OK

git diff --check
OK; apenas avisos CRLF conhecidos
```

Observacao: nos comandos locais foi usada `SECRET_KEY` temporaria de teste somente para executar checks, sem alterar o `.env`.

## Proximos passos recomendados

### 1. Auditar selectors restantes

Revisar os arquivos abaixo procurando somas e filtros feitos em Python que podem virar agregacoes no banco:

- `caixa/selectors_mes_financeiro.py`

Observacao: `caixa/selectors_cadastros.py`, `caixa/selectors_financiamentos.py` e `caixa/selectors_pagamentos.py` ja receberam rodadas de otimizacao. Podem voltar para revisao em casos novos, mas sairam da lista principal de pendencias imediatas.

Observacao: `caixa/selectors_mes_financeiro.py` recebeu uma correcao de regra financeira em `receita_aberta` e extracoes do resumo financeiro, totais consolidados, acumulados, itens de movimentacao, contas a pagar, resolucao de periodo e filtros aplicados aos querysets. A revisao de agregacoes indicou que, nesta tela, reaproveitar as listas ja carregadas evita consultas extras porque os mesmos objetos precisam ser renderizados.

Objetivo: reduzir carregamento de objetos quando o banco puder calcular totais com `Sum`, `Count`, `Case`, `When` e filtros agregados.

### 2. Quebrar o dashboard em modulos menores

O arquivo `caixa/selectors_dashboard.py` agora fica majoritariamente como orquestrador. As extracoes seguras ja foram feitas para filtros/querysets, URLs/parametros, alertas, movimentacoes, totais basicos/financeiros, custos por evento, contexto base e resumo. Proximas etapas podem dividir por tema:

- avaliar se outras funcoes ainda recebem listas longas de argumentos e reduzir somente onde houver ganho claro.

Objetivo: facilitar manutencao sem mudar comportamento.

### 3. Preparar separacao frontend/backend

Como o HTML sera substituido por outro frontend, as proximas rodadas devem priorizar contratos de backend:

- manter regras financeiras em selectors/services, nao nos templates;
- seguir tambem o documento `INTEGRACAO_NEXT_DJANGO.md` antes de alterar backend ou frontend da migracao;
- criar endpoints JSON por tela ou por caso de uso antes de remover as telas HTML;
- padronizar os novos contratos da migracao sob `/api/dashboard/`;
- iniciar a integracao do dashboard pelo contrato `GET /api/dashboard/financial-overview/`;
- manter endpoints JSON ja existentes (`/api/mes-financeiro/`, `/api/fci/` e `/api/fcf/`) enquanto forem uteis para o frontend ou para testes de contrato;
- adicionar Django REST Framework e `django-cors-headers` de forma incremental, preservando settings de seguranca, HTTPS, cookies, CSRF, CSP e middleware atuais;
- configurar CORS por variavel de ambiente, liberando somente os dominios do futuro frontend Next.js;
- proteger APIs com autenticacao e permissoes equivalentes as telas Django atuais;
- definir formato de datas, Decimals e opcoes de filtro usados pelo novo frontend;
- cobrir os contratos dos endpoints com testes de resposta e permissao;
- cobrir endpoints financeiros com testes de query count quando houver listas ou agregacoes sensiveis;
- prever paginacao e filtros para listas que podem crescer;
- evitar novas melhorias puramente visuais nos templates atuais.
- manter `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS` alinhados sempre que o dominio do frontend mudar.
- quando o frontend ganhar botao de logout, consumir `POST /api/auth/logout/` com CSRF e cobrir esse fluxo em teste.

Objetivo: remover o HTML depois que o backend ja tiver contratos estaveis para o novo frontend consumir.

Ordem segura sugerida para a migracao:

1. Criar a base DRF/CORS com `python manage.py check` e testes passando.
2. Criar namespace `/api/dashboard/` sem alterar as rotas HTML atuais.
3. Expor primeiro `summary`, `fluxo-de-caixa` e indicadores financeiros usando `selectors_dashboard*.py` e `selectors_mes_financeiro.py`.
4. Expor `receitas`, `despesas`, `clientes`, `contratos/eventos`, `contas-a-pagar` e `contas-a-receber` reaproveitando selectors ja existentes.
5. Expor agregacoes como `despesas-por-categoria`, `receitas-por-servico`, indicadores financeiros e metricas operacionais com `annotate`/`aggregate` quando possivel.
6. Conectar o Next.js somente depois dos contratos testados.
7. Manter Django templates como fallback ate a tela Next.js equivalente estar validada.

### 4. Criar mais testes de query count

As principais telas financeiras ja possuem testes de query count. Manter esse padrao para novas telas e novos filtros.

Objetivo: proteger as telas mais usadas contra regressao de performance.

### 5. Revisar indices com base em uso real

Antes de criar novos indices, confirmar no banco de producao quais filtros sao mais usados. Depois revisar campos como:

- datas de vencimento;
- status;
- categoria;
- chaves estrangeiras usadas em filtros;
- campos usados em ordenacao frequente.

Objetivo: adicionar indices com criterio, evitando custo desnecessario de escrita.

### 6. Fortalecer observabilidade

Adicionar ou revisar:

- logging estruturado para erros de producao;
- logs de operacoes financeiras sensiveis;
- alertas para falhas de pagamento/sincronizacao;
- rotina de teste de restauracao de backup.

Objetivo: detectar problema cedo, nao somente depois do usuario perceber.

### 7. Revisar CSP, PWA e Trusted Types

Base inicial ja aplicada. Proximos ajustes devem ser validados no navegador/Lighthouse em producao:

- service worker sem erro no console;
- CSP efetiva;
- Trusted Types sem bloquear scripts legitimos;
- headers de seguranca coerentes com Django e Nginx.

Objetivo: melhorar seguranca e nota de boas praticas sem quebrar o PWA.

### 8. Deploy seguro apos push

Para publicar as mudancas atuais, em geral o fluxo esperado e:

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
python manage.py check --deploy
python manage.py validar_preflight_deploy_financeiro --falhar
python manage.py verificar_consistencia_financeira
python manage.py auditar_totais_negocio --falhar-com-divergencia --validar-valores-editaveis --falhar-com-valores-editaveis
python manage.py validar_operacao_obrigacoes --validar-canonico --validar-escrita-canonica --validar-valores-editaveis --falhar
sudo systemctl restart controledecaixa
```

`validar_preflight_deploy_financeiro --falhar` e um atalho somente leitura para o pacote principal de deploy: executa `check`, auditoria de totais com valores editaveis e validacao operacional completa. Os comandos detalhados continuam documentados para investigacao quando o pre-flight apontar uma causa especifica.

Nas fases operacionais recentes ha migrations novas que devem ser aplicadas em ordem:

- `caixa.0031_padroniza_verbose_names_financeiros`: metadados/labels.
- `caixa.0032_entrada_fcf_divida_financeira`: origem da entrada FCF automatica vinculada a divida financeira.
- `caixa.0033_cadastro_credores_dividas`: cadastro mestre de credores e vinculo `credor_cadastro` nas dividas.

Nao ha necessidade de alterar Nginx, a menos que alguma mudanca futura envolva headers, arquivos estaticos servidos diretamente pelo Nginx ou service worker.

Revisao final de prontidao:

- `showmigrations caixa` nao deve listar pendencias depois de aplicar ate `0033_cadastro_credores_dividas`.
- `sqlmigrate caixa 0031` foi validado localmente como no-op estrutural; `0032` e `0033` sao migrations funcionais desta leva.
- A suite Django passou com 375 testes nesta leva operacional; `npm run typecheck`, `npm run lint` e `npm run build` do Next.js tambem passaram na revisao final deste checkpoint.
- As auditorias locais de totais, obrigacoes canonicas e valores editaveis passaram depois do alinhamento da base local de desenvolvimento.
- Se o servidor ja tiver dados canonicos sincronizados, manter a validacao com `validar_operacao_obrigacoes --validar-canonico --validar-escrita-canonica --validar-valores-editaveis --falhar` antes de reiniciar o servico.

### 9. Janelas canonical-first

PM-03.1 de `custo_fixo` foi concluida em producao RHRemoto em 2026-05-26. PM-03.2 de `despesa_operacional` foi concluida em producao/homologacao em 2026-05-27, com canario rollback-only, allowlist `custo_fixo,despesa_operacional`, uma baixa real `canonicalFirst` de 550.00, monitoramento sem legado na janela, auditoria de totais sem divergencia e fechamento PM-03 `ready=True`. PM-03.3 de `investimento` tambem foi concluida em 2026-05-27, com allowlist `custo_fixo,despesa_operacional,investimento`, baixa real `canonicalFirst` de 1.00, auditorias, monitoramento e fechamento `ready=True`.

Nao incluir ainda `custo_servico`, `custo_extra` ou `parcela_divida` na allowlist direta, porque elas ainda passam por models dedicados de pagamento e dependem da decisao PM-04. A proxima candidata direta da PM-03 e `financiamento_movimentacao`, com descoberta de candidato FCF de saida/a pagar, regressao agregada de dividas, canario, allowlist, primeira baixa real, auditoria, monitoramento e fechamento.

Roteiro seguro para proximas origens diretas:

```bash
python manage.py validar_ativacao_canonical_first --source=despesa_operacional --source-id=<sourceId-de-canaryCandidates> --username=<usuario> --payment-date=<DATA> --executar-canario --exigir-canario --exigir-source-id-canario --exigir-data-pagamento-canario --diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional> --exigir-arquivos-evidencia --json --falhar
```

Se `custo_fixo` ja estiver ativo, manter a origem antiga na lista:

```env
CANONICAL_FIRST_SETTLEMENT_ENABLED=True
CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional
```

Apos registrar a primeira baixa real da nova origem:

```bash
python manage.py validar_janela_canonical_first --source=despesa_operacional --data-ativacao=DATA_DA_ATIVACAO --validar-preflight-operacional --falhar-com-preflight-operacional --exigir-feature-flag-ativa --exigir-baixa-canonical-first --exigir-data-ativacao --diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional> --exigir-arquivos-evidencia --json --falhar
python manage.py auditar_fonte_escrita_baixas --source=despesa_operacional --data-ativacao=DATA_DA_ATIVACAO --write-model-source=canonicalFirst --exigir-canonical-first --exigir-data-ativacao --diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional> --exigir-arquivos-evidencia --json
python manage.py monitorar_janela_canonical_first --source=despesa_operacional --data-ativacao=DATA_DA_ATIVACAO --exigir-canonical-first --falhar-com-legado-na-janela --exigir-data-ativacao --diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional> --exigir-arquivos-evidencia --json --falhar
python manage.py auditar_totais_negocio --falhar-com-divergencia --validar-valores-editaveis --falhar-com-valores-editaveis --diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional> --exigir-arquivos-evidencia --json
python manage.py validar_fechamento_pm03 --source=despesa_operacional --data-ativacao=DATA_DA_ATIVACAO --validacao-janela-json=<diretorio-evidencias-pm03-despesa-operacional>/pm03-validacao-resultado-janela.json --diretorio-evidencias=<diretorio-evidencias-pm03-despesa-operacional> --exigir-validacao-ativacao --json --falhar
```

`--data-ativacao` e um alias operacional de `--data-inicial` nos comandos de validacao, auditoria e monitoramento de janela canonical-first.

Para PM-03.4, a regressao de dividas FCF agora tem artefato proprio e deve ser rodada antes do canario rollback-only:

```bash
python manage.py listar_candidatos_canario_pm03 --source=financiamento_movimentacao --username=<usuario> --payment-date=<DATA> --diretorio-evidencias=<diretorio-evidencias-pm03-financiamento-movimentacao> --exigir-arquivos-evidencia --json --falhar
python manage.py validar_regressao_dividas_pm03 --source=financiamento_movimentacao --diretorio-evidencias=<diretorio-evidencias-pm03-financiamento-movimentacao> --exigir-arquivos-evidencia --json --falhar
```

O comando de candidatos salva `pm03-candidatos-canario.json/md`, diferencia pendencias `receber` de candidatos `pagar` e aceita `--username`/`--payment-date` para preencher o canario sugerido. Quando `validar_ativacao_canonical_first` ou `validar_janela_canonical_first` recebem esses valores, eles tambem repassam os mesmos parametros para `candidateDiscovery` e `discoverCanaryCandidate`. Quando nao houver candidato elegivel, os payloads de ativacao, janela e descoberta trazem `candidateCreationGuidance` com caminho do admin, campos sugeridos e comandos para reexecutar apos criar o registro controlado; a mesma sequencia tambem aparece em `recommendedCommands.afterControlledCandidateCreate`, com sincronizacao canonica, paridade, pre-flight operacional, redescoberta e canario rollback-only. O comando de regressao salva `pm03-regressao-dividas-fcf.json/md`, consolidando dry-run de credores FCF, integridade das entradas automaticas de dividas e `validar_preflight_deploy_financeiro`. Para `source=financiamento_movimentacao`, o `validar_fechamento_pm03` exige os JSONs de candidatos e regressao, e o checklist `postWindow.validatePm03Closure` ja sugere `--validacao-janela-json`, `--candidatos-canario-json` e `--regressao-dividas-json` apontando para os artefatos esperados.

Os comandos de auditoria/pre-flight agora retornam mensagens de erro mais acionaveis quando algo falha: a primeira divergencia, inconsistencia de valores editaveis, problema de paridade, contexto de canario ou filtro da janela aparece diretamente no `CommandError`. Mesmo assim, o relatorio completo e o JSON continuam sendo a fonte para revisao detalhada.

Nota operacional em 2026-05-25: o usuario informou que `custo_fixo` ja foi pago
pelo frontend com canonical-first ativo e passou no fluxo real. Essa informacao
reforca que canonical-first e o caminho correto para a baixa canonica de uma
origem habilitada, mas nao muda a politica de promocao: novas origens continuam
exigindo backup, versao de codigo, migrations, pre-flight, canario, auditoria de
fonte de escrita, monitoramento da janela e auditoria de totais antes de ampliar
`CANONICAL_FIRST_SETTLEMENT_SOURCES`.

## Cuidado ao continuar

- Nao colocar pacotes de teste local em `requirements.txt` de producao.
- Manter arquivos locais de pytest/factory fora do deploy.
- Rodar testes antes de cada push.
- Evitar refatoracoes grandes sem teste de comportamento e teste de query.
- Sempre verificar `makemigrations --check --dry-run` antes de assumir que nao ha mudanca de banco.
- Ao final de cada passo relevante, atualizar documentacao com mudancas, validacoes e proximas melhorias.

## Atualizacao - Credores cadastrados em dividas FCF

- Implementado cadastro mestre `Credor` para uso no Django admin.
- `DividaFinanceira` agora seleciona `credor_cadastro`, mantendo `credor` textual apenas como compatibilidade.
- A migration `0033_cadastro_credores_dividas` cria credores a partir dos textos existentes e vincula as dividas.
- APIs, filtros, agrupamentos e pagamentos FCF foram ajustados para usar `creditorId`/`creditorName` com fallback legado.
- As entradas FCF automaticas das fases anteriores continuam preservadas e agora tambem publicam `debtCreditorId`.
- Validado com `python manage.py check`, `makemigrations --check --dry-run`, testes focados e suite completa Django com 375 testes.
- Proximo passo recomendado: quando o Next.js ganhar cadastro de dividas, criar endpoint/service de credores e enviar o ID do credor cadastrado, nao texto livre.

## Atualizacao - Leitura FCF preparada no Next.js

- O frontend passou a ter `getFinancialFinancingData()` para consumir `GET /api/fcf/`.
- O frontend tambem passou a ter `useFinancialFinancing()` para carregar essa leitura com loading, erro, abort e refetch centralizados.
- Foi criada a rota Next.js `/fcf` somente leitura, com KPIs, parcelas, credores agrupados e movimentacoes.
- A rota `/fcf` passou a ter filtros locais de credor (`creditorId`) e origem (`sourceType`).
- A leitura normaliza `filterOptions.creditors` para manter `creditorId`, `creditorName`, `value` e aliases de transicao consistentes.
- Nao foi criada escrita de dividas no Next.js; enquanto o cadastro estiver no admin, o Django continua sendo a unica origem de cadastro.
- A regra de entrada FCF automatica de `emprestimo` e `financiamento` continua exclusiva do backend.
- Checkpoint apos essa preparacao: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram sem pendencias.

## Atualizacao - Registro dos projetos no workspace

- Confirmado que o trabalho atual envolve dois projetos locais:
  - Backend Django: `c:\Users\Davif\OneDrive\Desktop\Projetos\controledecaixa`
  - Frontend Next.js: `c:\Users\Davif\OneDrive\Desktop\Projetos\dashboardFinanceiro\v0-dashboard-financeiro-rhremoto`
- `INTEGRACAO_NEXT_DJANGO.md` recebeu a secao `Workspace e Projetos Relacionados` com caminhos absolutos, caminhos relativos e responsabilidades de cada projeto.
- No backend ficam regras financeiras, banco, admin, selectors, serializers, templates Django, migrations e testes de negocio.
- No frontend ficam UI, tipos TypeScript, mocks, services/hooks e documentacao visual.

## Atualizacao - Status das decisoes de arquitetura

- `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md` recebeu um checkpoint em `Decisoes de arquitetura` com status objetivo das decisoes base.
- Foram marcadas como concluidas no ciclo atual: `Evento` como centro operacional, `ContratoOperacional`, ledger central `LancamentoFinanceiro`, comportamento especial de dividas `emprestimo`/`financiamento` no FCF/caixa e cadastro mestre de credores de dividas FCF.
- A arquitetura premium canonica foi registrada como `em andamento controlado`, porque ainda depende de validacao em dados reais, janelas canonical-first por origem e auditoria sem divergencias antes de qualquer remocao de legados.
- Conclusao operacional: manter aliases, models legados e validacoes ate a futura versao `financeiro-v3`.

## Atualizacao - Consolidacao de conclusao e deploy

- O roteiro de deploy foi atualizado para deixar claro que as migrations recentes vao ate `caixa.0033_cadastro_credores_dividas`.
- A revisao final de prontidao passou a citar a suite Django com 375 testes e as validacoes frontend `typecheck`, `lint` e `build`.
- A conclusao atual e aplicar `python manage.py migrate` ate `0033`, rodar os checks/pre-flight documentados e manter a proxima tela Next.js de cadastro de dividas como evolucao futura.

## Atualizacao - Validacao final consolidada

- Backend validado com `python manage.py check` e `python manage.py makemigrations --check --dry-run`.
- Suite completa Django executada novamente com 375 testes OK.
- Frontend validado com `npm run typecheck`, `npm run lint` e `npm run build`.
- `git diff --check` aprovado nos dois projetos, restando apenas avisos CRLF/LF conhecidos no backend.
- Estado atual: pacote pronto para push/pull operacional e validacao em servidor com `python manage.py migrate`, `collectstatic`, `check` e `validar_preflight_deploy_financeiro --falhar`.

## Atualizacao - Ensaio local pos-migrate

- A base local aplicou `python manage.py migrate` com sucesso ate `caixa.0033_cadastro_credores_dividas`.
- `python manage.py showmigrations caixa` confirmou `0031`, `0032` e `0033` aplicadas.
- `python manage.py validar_preflight_deploy_financeiro --falhar` passou apos as migrations locais.
- `python manage.py sincronizar_entradas_fcf_dividas` em modo somente leitura reportou `criadas=0`, `atualizadas=0`, `removidas=0` e `inalteradas=16`.
- Observacao operacional: em servidor, o pre-flight deve ser executado somente depois de `python manage.py migrate`, pois antes da `0033` a coluna `credor_cadastro_id` ainda nao existe no banco.

## Atualizacao - Normalizacao defensiva de credores

- `Credor.clean()` agora bloqueia nomes duplicados ignorando diferencas de maiusculas/minusculas.
- Salvamentos legados de `DividaFinanceira` por `credor` textual reaproveitam um `Credor` existente por comparacao case-insensitive antes de criar novo cadastro.
- Nao houve migration nova; a protecao fica na camada de aplicacao/admin.
- A regra de caixa das dividas `emprestimo` e `financiamento` foi preservada e validada em testes focados.
- Validado com `makemigrations --check --dry-run`, `check`, 7 testes focados de credores/entrada FCF, 3 testes focados de API/admin FCF e suite completa Django com 377 testes OK.

## Atualizacao - Endpoint de credores FCF

- Criado `GET /api/fcf/creditors/` para retornar credores ativos cadastrados no formato usado por selects do Next.js.
- O endpoint usa a permissao de leitura do FCF e nao altera cadastro, dividas, parcelas ou movimentacoes financeiras.
- O contrato retorna `creditors`, alias textual `credores` e `meta.onlyActive=true`.
- O frontend recebeu tipo e service para consumir esse endpoint futuramente, sem criar tela nova neste ciclo.
- Validado com 6 testes focados de rota, permissao, contrato JSON, API FCF existente, `makemigrations --check --dry-run`, `check` e suite completa Django com 378 testes OK.

## Atualizacao - Permissoes de credores no admin

- O perfil `Financeiro` agora recebe `view_credor`, `add_credor` e `change_credor`.
- O perfil `Operacional` continua sem acesso ao cadastro de credores.
- Usuario staff do grupo `Financeiro` foi validado acessando o admin de `Credor`.
- Nao houve migration nova; em deploy, `python manage.py migrate` dispara o `post_migrate` que sincroniza os grupos.
- Validado com 3 testes focados de permissoes/admin financeiro, `makemigrations --check --dry-run` e `check`.

## Atualizacao - Credores ativos no admin de dividas

- O admin de `DividaFinanceira` agora lista apenas credores ativos para novas dividas.
- Ao editar divida antiga, um credor inativo ja vinculado continua disponivel para preservar historico.
- O autocomplete de `credor_cadastro` no contexto de dividas filtra credores ativos.
- Nao houve migration nova nem alteracao nas regras de caixa/FCF.
- Validado com testes focados de admin de dividas, autocomplete, entrada FCF automatica de `emprestimo`/`financiamento`, `makemigrations --check --dry-run` e `check`.

## Atualizacao - Validacao de credor ativo no dominio

- `DividaFinanceira.clean()` agora rejeita novas dividas com `credor_cadastro` inativo.
- Dividas antigas que ja tenham credor inativo vinculado continuam editaveis, preservando historico.
- A regra protege futuras APIs/criacoes programaticas alem do filtro visual do admin.
- Nao houve migration nova nem alteracao nas regras de caixa/FCF.
- Validado com testes focados de dominio/admin/entrada FCF automatica, `makemigrations --check --dry-run`, `check` e suite completa Django com 384 testes OK.

## Atualizacao - Diretriz da arquitetura principal/prime

- A arquitetura principal/prime fica registrada como direcao aprovada, mas a virada nao deve ser feita como troca total imediata.
- Backup do banco antes da janela e obrigatorio, porem ele e plano de recuperacao; nao substitui tag do codigo, migrations controladas, pre-flight, canario, allowlist por origem, auditoria e monitoramento.
- `CANONICAL_FIRST_SETTLEMENT_ENABLED` deve continuar desligado por padrao no codigo. A ativacao deve acontecer no ambiente, por origem suportada em `CANONICAL_FIRST_SETTLEMENT_SOURCES`.
- O rollback preferencial e remover a origem da allowlist/desligar a flag quando nao houver corrupcao real. Restore de backup fica reservado para falha grave de dados e exige reconciliar movimentos feitos depois do backup.
- As regras de dividas `emprestimo` e `financiamento` continuam protegidas: elas geram entrada FCF/caixa automatica e devem entrar em qualquer bateria de regressao antes de ampliar canonical-first.
- Proxima candidata segue sendo `despesa_operacional`, depois de pre-flight e canario rollback-only; nao ativar `custo_servico`, `custo_extra` ou `parcela_divida` ate haver suporte direto seguro.

## Atualizacao - Strategy enxuta para entradas FCF de dividas

- Mantida a escolha de aplicar Strategy porque ha ganho real: `emprestimo` e `financiamento` tem comportamento diferente dos demais tipos e novos tipos podem exigir regras proprias sem mexer em signal, comando, admin ou API.
- A Strategy ficou local em `services_dividas_fcf.py`, sem criar pacote novo nem camada pesada.
- `EntradaFCFContratacaoDividaStrategy` cobre `emprestimo` e `financiamento`; os demais tipos continuam sem entrada FCF automatica.
- Os helpers de descricao/observacao preservam fallback padrao para tipos sem Strategy.
- Fora do escopo: cadastro de credores, pagamentos, parcelas, canonical-first, migrations, API e frontend.
- Validado com 7 testes focados de entrada FCF/caixa/comando, `makemigrations --check --dry-run`, `check` e `git diff --check`.

## Atualizacao - Regra central de parcela FCF pagavel

- Criado `parcela_disponivel_para_pagamento()` em `services_dividas.py` para concentrar a regra de status nao final e saldo pendente maior que zero.
- A tela `pagar_parcela`, o registro transacional com `select_for_update` e a prorrogacao de parcelas pendentes agora usam a mesma decisao de dominio.
- A mudanca reduz duplicidade sem criar camada pesada nem alterar models, migrations, APIs, frontend ou canonical-first.
- A regra especial de dividas `emprestimo` e `financiamento` foi preservada e entrou na bateria focada.
- Validado com testes focados de helper, pagamento com lock, tela de pagamento FCF, entrada FCF/caixa de dividas especiais, `makemigrations --check --dry-run`, `check` e `git diff --check`.

## Atualizacao - Parcela FCF pagavel no agregado e no contrato JSON

- `ParcelaDivida` agora possui a propriedade derivada `disponivel_para_pagamento`.
- O helper `parcela_disponivel_para_pagamento()` continua existindo, mas delega para o model.
- Selectors e templates FCF usam a propriedade do model para contagens e acoes de pagamento.
- A API FCF passou a publicar `disponivel_para_pagamento` e `availableForPayment` em cada parcela.
- Nao houve migration, endpoint novo, mudanca de escrita, canonical-first ou tela Next.js nova.
- Validado com testes focados de API FCF, telas FCF, helper/model, pagamento com lock e regressao de entrada FCF/caixa para `emprestimo`.

## Atualizacao - Next.js alinhado ao booleano FCF pagavel

- `FinancialFinancingInstallmentApi` passou a declarar `availableForPayment` e o alias `disponivel_para_pagamento`.
- O mock de nomenclatura local recebeu `availableForPayment` como campo canonico e `disponivel_para_pagamento` como alias de transicao.
- A documentacao do frontend orienta futuras telas FCF a usar esse booleano do backend junto com permissoes, sem recalcular status/saldo no Next.js.
- Nao houve tela nova, package.json, pnpm-lock, dependencias, API ou banco.
- Validado no frontend com `npx --yes pnpm@10.33.4 run typecheck`, `npx --yes pnpm@10.33.4 run lint` e `git diff --check`.

## Atualizacao - Predicado SQL central de parcelas FCF pagaveis

- Criados `filtro_parcela_disponivel_para_pagamento()` e `filtrar_parcelas_disponiveis_para_pagamento()` em `selectors_pagamentos.py`.
- Forms, situacao de parcelas e filtro rapido de FCF vencidos passam a reutilizar o mesmo predicado SQL.
- A propriedade `ParcelaDivida.disponivel_para_pagamento` continua sendo a fonte para objetos ja carregados, enquanto o selector centraliza a versao de banco.
- Nao houve migration, API nova, frontend novo, canonical-first ou alteracao de pagamentos.
- Validado com testes focados de selector, pagina de pagamentos FCF, API FCF, botao de pagamento e regressao de entrada FCF/caixa para `emprestimo`.

## Atualizacao - Metadata backend para availableForPayment

- `meta.nomenclature.canonicalFields` agora inclui `availableForPayment`.
- `disponivel_para_pagamento` foi registrado como alias transicional para `availableForPayment`.
- O inventario `legacyAliasUsage` tambem registra esse alias para `api_fcf` e `next_types`.
- Isso mantem a API real em paridade com o mock local do Next.js.
- Validado com testes focados do contrato do dashboard e da API FCF.

## Atualizacao - Cobertura do bloqueio de pagamento FCF no contrato

- Adicionado teste da API FCF para parcela quitada retornando `availableForPayment=false`.
- O alias `disponivel_para_pagamento` tambem foi validado como `false`.
- O teste confirma `pendingPaymentAmount=0.00` e `pendingDebtsCount=0`.
- Nao houve mudanca de producao; a entrega reforca o contrato para futuras telas Next.js.

## Atualizacao - Validacao ampla backend/frontend

- Suite completa Django executada com 389 testes OK.
- Build de producao do Next.js executado com sucesso usando `npx --yes pnpm@10.33.4 run build`.
- O pacote atual de credores, dividas FCF, disponibilidade de pagamento, metadata e tipos frontend passou validacao transversal local.

## Atualizacao - Integracao Django/Next para availableForPayment

- `INTEGRACAO_NEXT_DJANGO.md` agora registra `availableForPayment` nas parcelas FCF.
- O documento reforca que `disponivel_para_pagamento` e alias de transicao.
- Futuras acoes de pagamento no Next.js devem combinar esse booleano do backend com permissoes da sessao, sem recalcular status/saldo no frontend.

## Atualizacao - Documentacao de entradas FCF automaticas no frontend

- `docs/INTEGRACAO_FRONTEND_BACKEND.md` e `docs/PROJECT_GUIDE.md` agora reforcam `automaticFromDebt=true` e `sourceType=divida_automatica`.
- A documentacao deixa claro que entradas FCF geradas por dividas `emprestimo`/`financiamento` nao devem ser tratadas como movimentacao FCF manual editavel livremente no frontend.
- Nao houve codigo novo; a regra permanece no backend.

## Atualizacao - Metadata de movimentacoes FCF automaticas

- `meta.nomenclature.canonicalFields` agora registra `sourceType`, `sourceTypeLabel`, `automaticFromDebt`, `debtId`, `debtCreditorId` e `debtCreditorName`.
- Aliases de transicao como `movementSourceType`, `origem_movimentacao`, `isAutomaticFromDebt`, `entrada_automatica_divida`, `divida_id`, `credor_divida_id`, `debtCreditor`, `credor_divida` e `nome_credor_divida` foram registrados no backend e no mock do Next.js.
- Nao houve mudanca de payload ou regra; o ajuste so alinha contrato, metadata e tipos ja existentes.
- Validado com testes focados do contrato do dashboard/API FCF e typecheck do frontend.

## Atualizacao - Aliases TypeScript depreciados para movimentacoes FCF

- `FinancialFinancingMovementApi` agora marca `movementSourceType`, `movementSourceTypeLabel`, `isAutomaticFromDebt`, `debtCreditor` e `credor_divida` como aliases depreciados.
- O caminho canonico recomendado fica explicito: `sourceType`, `sourceTypeLabel`, `automaticFromDebt`, `debtCreditorName`.
- Nao houve mudanca de runtime; validado com typecheck do frontend.

## Atualizacao - Cobertura de aliases da entrada FCF automatica

- O teste de entrada FCF automatica agora valida aliases do payload, incluindo `movementSourceType`, `origem_movimentacao`, `isAutomaticFromDebt`, `entrada_automatica_divida`, `divida_id`, `credor_divida_id`, `credor_divida` e `nome_credor_divida`.
- A cobertura protege compatibilidade enquanto novas telas usam os campos canonicos.
- Nao houve mudanca de producao; validado com teste focado do fluxo automatico.

## Atualizacao - Validacao ampla apos metadata FCF

- Suite completa Django executada novamente com 389 testes OK.
- Build de producao do Next.js executado novamente com sucesso.
- O pacote atual segue validado apos metadata, mock e aliases das movimentacoes FCF automaticas.

## Atualizacao - Revisao de duplicacoes da regra FCF pagavel

- Revisada a base para confirmar que a disponibilidade de pagamento FCF ficou centralizada.
- `ParcelaDivida.disponivel_para_pagamento` segue como decisao para objetos carregados.
- `filtrar_parcelas_disponiveis_para_pagamento()` segue como predicado SQL central para queries.
- A leitura em `selectors_obrigacoes.py` foi mantida fora dessa regra porque calcula status de obrigacao canonica, nao disponibilidade operacional de pagamento.
- Nao houve codigo novo; a etapa registra o levantamento e protege proximas implementacoes.

## Atualizacao - Select de credores FCF preparado para escrita futura

- `/api/fcf/creditors/` e `filterOptions.creditors` agora publicam `value` como id serializado do credor.
- As opcoes de credor tambem trazem `creditorId`, `creditorName`, `credor_id` e `credor_nome`.
- `label` e `name` continuam sendo o texto exibido.
- O tipo `CreateFinancialDebtRequestPayload` do Next.js passou a esperar `creditorId` numerico.
- A documentacao Django/Next orienta converter o valor do select antes de enviar futura escrita de divida.
- Nao houve endpoint de escrita, tela nova, migration, canonical-first ou mudanca na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - Validacao ampla apos contrato de credores FCF

- Suite completa Django executada com 389 testes OK.
- Build de producao do Next.js executado com sucesso.
- O ajuste de `value`/`creditorId` para selects de credor FCF ficou validado de ponta a ponta localmente.

## Atualizacao - Admin de dividas reforcado para credor cadastrado

- `DividaFinanceiraAdminForm` agora orienta o usuario a selecionar um credor ativo ja cadastrado.
- Teste novo garante que `credor_cadastro` e o campo principal do admin de dividas.
- Teste novo garante que `credor` legado fica fora dos fieldsets editaveis e permanece readonly.
- O fluxo atual continua pelo Django admin, sem tela Next.js ou API de escrita nova.

## Atualizacao - Service Next.js normaliza credores FCF

- `getFinancialCreditorsData()` agora normaliza opcoes de credores para entregar `value` como id serializado.
- Cada opcao tambem sai com `creditorId` numerico e `creditorName` textual.
- `useFinancialCreditors()` fica pronto para uma futura tela de dividas sem duplicar normalizacao em componente.
- A mudanca e defensiva para payloads antigos e nao cria tela ou escrita nova.

## Atualizacao - Filtro FCF protegido por id de credor

- Adicionado teste garantindo que `/api/fcf/` aceita `credor` com o id serializado do credor cadastrado.
- O mesmo teste confirma que `filterOptions.creditors[].value` permanece alinhado ao id.
- Isso permite que selects futuros usem o mesmo valor para filtro e para preparar escrita por `creditorId`.

## Atualizacao - Payload futuro de dividas com ids numericos

- `CreateFinancialDebtRequestPayload` agora tipa `contractId` e `eventId` como numeros.
- `UpdateFinancialDebtRequestPayload` agora tipa `debtId` como numero.
- A documentacao do frontend orienta converter valores de select para numero antes de chamar o Django.
- Nao houve service de escrita, tela nova ou endpoint novo.

## Atualizacao - Validacao ampla apos credores FCF

- Suite completa Django executada com 391 testes OK.
- `makemigrations --check --dry-run` confirmou que nao ha migration pendente.
- `manage.py check` executou sem alertas.
- Build de producao do Next.js executado com sucesso.
- O pacote atual de credores FCF, filtro por id e normalizacao frontend ficou validado.

## Atualizacao - Cookies `.rhremoto.com` e cache LocMem/Redis

- `settings.py` agora le `SESSION_COOKIE_DOMAIN` e `CSRF_COOKIE_DOMAIN` do `.env`.
- `.env.production.example` registra `SESSION_COOKIE_DOMAIN=.rhremoto.com` e `CSRF_COOKIE_DOMAIN=.rhremoto.com`.
- Valor vazio em desenvolvimento vira `None`, evitando dominio de cookie indevido em localhost.
- A documentacao de deploy explica que `LocMemCache` e a opcao mais simples para servidor unico, mas isolada por processo.
- Para multiplos workers/servidores ou cache compartilhado critico, a recomendacao passa a ser Redis em etapa separada com `django-redis` no deploy.

## Atualizacao - Redis como cache de producao

- `requirements.txt` agora inclui `django-redis==6.0.0` e `redis==7.4.0`.
- `.env.production.example` passou a usar `CACHE_BACKEND=django.core.cache.backends.redis.RedisCache`.
- `CACHE_LOCATION=redis://127.0.0.1:6379/1` ficou registrado como padrao de producao.
- `DEPLOY_ORACLE.md` agora inclui instalacao do `redis-server`, teste com `redis-cli ping` e validacao pelo Django cache.
- `LocMemCache` permanece documentado apenas como fallback simples para desenvolvimento ou servidor unico sem Redis.

## Atualizacao - Filtro FCF canonico por creditorId

- `/api/fcf/` agora aceita `creditorId` e `credor_id` como aliases de filtro por credor cadastrado.
- O filtro legado `credor` continua funcionando para compatibilidade.
- O payload `filters` ecoa `credor`, `creditorId` e `credor_id` com o valor resolvido.
- Parcelas e movimentacoes FCF usam o mesmo helper de selector para resolver o credor.
- Futuras telas Next.js devem preferir `creditorId`.

## Atualizacao - Filtros startDate/endDate em FCI e FCF

- `/api/fci/` e `/api/fcf/` agora aceitam `startDate` e `endDate`.
- Os aliases legados `data_inicial` e `data_final` continuam funcionando.
- Os payloads de `filters` passam a ecoar tanto camelCase quanto snake_case.
- A conversao fica nos selectors antes de chamar a regra central de periodo rapido.

## Atualizacao - Filtro de origem das movimentacoes FCF

- `/api/fcf/` agora aceita `sourceType=manual` e `sourceType=divida_automatica`.
- `movementSourceType`, `origem_movimentacao` e `automaticFromDebt` ficam como aliases de transicao.
- `filterOptions.financingMovementSourceTypes` publica as opcoes canonicas para a futura tela Next.js.
- A filtragem e somente de leitura e nao altera criacao de dividas, pagamentos, ledger ou entrada automatica de `emprestimo`/`financiamento`.

## Atualizacao - Action hints FCI/FCF com filtros canonicos

- `actionHints` de obrigacoes que abrem FCI/FCF agora carregam `startDate` e `endDate` baseados na data da obrigacao.
- Movimentacoes FCF tambem carregam `sourceType=manual` ou `sourceType=divida_automatica` quando a origem e conhecida.
- O fallback local do Next.js para FCI/FCF tambem passou a incluir o periodo da obrigacao.
- A mudanca e apenas de navegacao e nao altera regras de baixa, caixa, ledger, dividas ou pagamentos.

## Atualizacao - Validacoes de servidor para fases FCI/FCF recentes

- `DEPLOY_ORACLE.md` agora registra a bateria focada de `python manage.py test` para filtros FCI/FCF, credores, origem de movimentacoes FCF e `actionHints`.
- O teste de cache via Django foi ajustado para `python manage.py shell --no-imports`, evitando avisos de autoimport de models historicos.
- A documentacao reforca que comandos `manage.py` devem usar o `python` do `venv`, deixando `sudo` apenas para `systemctl`/Nginx.

## Atualizacao - Filtro visual de origem da movimentacao FCF

- A tela Django de FCF agora exibe o filtro `Origem da movimentacao`.
- O filtro usa `sourceType=manual` ou `sourceType=divida_automatica`, a mesma semantica da API.
- Os atalhos de periodo rapido preservam `sourceType` quando ele estiver selecionado.
- A mudanca e apenas de leitura/UX e nao altera dividas, caixa, pagamentos ou ledger.
- `DEPLOY_ORACLE.md` tambem passou a incluir o teste da tela FCF nessa bateria focada de servidor.

## Atualizacao - Validacao regressiva consolidada FCI/FCF

- Rodada regressiva revisou as fases recentes de Redis/cache, filtros `creditorId`, `startDate`, `endDate`, `sourceType`, `actionHints` e filtro visual FCF.
- Bateria focada com 8 testes Django passou.
- Suite completa Django passou com 396 testes.
- Frontend passou em `typecheck` e `build`.
- A validacao confirmou ausencia de migrations pendentes e preservacao da regra de entrada FCF automatica para `emprestimo`/`financiamento`.

## Atualizacao - Tela FCF usa credor cadastrado no filtro visual

- O filtro visual de credor da tela Django FCF passou de `credor` textual para `creditorId`.
- As opcoes agora usam `credores_cadastrados_filtro`, mantendo o cadastro mestre de credores como fonte da UI.
- Os atalhos de periodo rapido preservam `creditorId` quando o filtro estiver selecionado.
- Os aliases antigos continuam aceitos no backend para compatibilidade com links ou integracoes existentes.
- A mudanca e apenas de leitura/UX e nao altera cadastro de dividas, pagamentos, ledger ou entrada automatica de caixa para `emprestimo`/`financiamento`.

## Atualizacao - Pagamentos FCF tambem filtram por creditorId

- A tela Django de pagamentos de parcelas FCF passou a usar `creditorId` no select de credor.
- O selector de parcelas FCF aceita `creditorId`, `credor_id` e o legado `credor` pela mesma funcao compartilhada de filtro por credor de divida.
- O helper comum foi isolado em `selectors_dividas.py`, evitando acoplamento circular entre selectors de financiamentos e pagamentos.
- A bateria de servidor em `DEPLOY_ORACLE.md` ganhou os testes de selector e tela de pagamentos FCF.
- Suite completa Django passou com 396 testes apos a extracao do helper comum.
- A documentacao do frontend tambem registra que FCF e pagamentos FCF usam `creditorId` nos filtros visuais; `typecheck` e `build` do Next.js passaram.
- A mudanca nao altera baixa, valor pendente, regra de disponibilidade para pagamento, ledger, canonical-first ou entrada automatica de `emprestimo`/`financiamento`.

## Atualizacao - creditorId FCF com filtro estrito por id

- `creditorId` e `credor_id` agora filtram estritamente por `credor_cadastro_id`.
- O alias legado `credor` continua aceitando busca textual para compatibilidade.
- A protecao evita que um credor diferente apareca no filtro por id apenas porque seu nome contem o numero do credor selecionado.
- A mesma regra vale para API FCF, tela FCF e tela de pagamentos FCF.
- Nao houve mudanca em cadastro, baixa, ledger, canonical-first ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - Roteiro de realizado acima do previsto revisado

- O plano deixou de tratar filtros/alertas de `realizado acima do previsto` como proximo incremento a criar.
- Essa capacidade ja existe na API e na tela Next.js de obrigacoes financeiras.
- O proximo uso recomendado passa a ser validacao com dados reais por contrato, evento, origem ou periodo antes de qualquer consolidacao fisica futura.

## Atualizacao - Regressao de creditorId invalido em FCF

- Adicionada cobertura para garantir que `creditorId` e `credor_id` invalidos nao fazem busca textual no campo legado `credor`.
- A API FCF deve retornar vazio quando o alias canonico de id recebe valor nao numerico.
- O selector de pagamentos FCF tambem foi coberto para manter a mesma regra antes da baixa.
- A bateria focada de servidor em `DEPLOY_ORACLE.md` passou a incluir essa regressao.

## Atualizacao - Frontend descarta credor sem id numerico

- `getFinancialCreditorsData()` agora normaliza credores usando apenas id inteiro positivo como `creditorId`.
- Opcoes recebidas sem id numerico valido sao descartadas antes de chegar a futuros selects.
- A documentacao do frontend registra que `value` continua sendo o `creditorId` serializado, sem fallback textual.
- `typecheck` e `build` do Next.js passaram apos a alteracao.

## Atualizacao - Bateria de servidor cobre endpoint de credores FCF

- `DEPLOY_ORACLE.md` agora inclui o teste de `/api/fcf/creditors/` na bateria focada de servidor.
- Esse teste valida somente credores ativos, ordenacao, aliases `creditorId`/`credor_id` e `value` serializado para select.
- A bateria focada passou com 12 testes.

## Atualizacao - Checkpoint de lockfile do Vercel

- O frontend nao possui suite unitaria configurada neste momento; a validacao ficou em `typecheck`, `build` e instalacao congelada.
- `pnpm install --frozen-lockfile --ignore-scripts` passou com pnpm 10.33.4.
- Isso confirma localmente que `pnpm-lock.yaml` esta alinhado ao `package.json` para o fluxo de CI/Vercel.

## Atualizacao - Validacao frontend documentada com pnpm

- Guias de deploy/integracao foram alinhados para usar `npx --yes pnpm@10.33.4`, acompanhando o `pnpm-lock.yaml` detectado pela Vercel.
- A validacao recomendada agora inclui `install --frozen-lockfile`, `lint`, `typecheck` e `build` com pnpm.
- A sequencia completa passou localmente, incluindo lint.

## Atualizacao - Bateria protege entrada FCF automatica de dividas

- A bateria focada de servidor agora inclui testes da Strategy de entrada FCF por tipo de divida.
- Tambem valida que divida `emprestimo` gera movimentacao FCF, lancamento financeiro e saldo de caixa.
- A bateria valida que tipo comum, como `fornecedor`, nao gera entrada automatica.
- A bateria focada passou com 15 testes.

## Atualizacao - README do frontend alinhado ao pnpm

- O README do frontend passou a orientar `npx --yes pnpm@10.33.4` para dev, lint, typecheck e build.
- A checklist antes de push/pull operacional agora inclui `install --frozen-lockfile`.
- A mudanca fecha a consistencia entre README, guias de integracao, `DEPLOY_ORACLE.md` e Vercel.

## Atualizacao - Guia backend/Next reforca pnpm no frontend

- `INTEGRACAO_NEXT_DJANGO.md` agora orienta validar mudancas de frontend com pnpm.
- A regra para IA/Codex passou a citar `install --frozen-lockfile`, `lint`, `typecheck` e `build`.
- Isso evita que uma retomada pelo backend ignore o fluxo real do frontend na Vercel.

## Atualizacao - Ponto de retomada usa pnpm

- O `Ponto de retomada` do plano vivo deixou de citar `npx tsc --noEmit` e `npm run build` como validacao atual.
- A orientacao viva agora usa a sequencia pnpm validada: `install --frozen-lockfile`, `lint`, `typecheck` e `build`.
- Entradas historicas antigas com `npm run` foram preservadas como registro do que foi executado no passado.

## Atualizacao - Frozen lockfile validado sem ignore-scripts

- O comando documentado `npx --yes pnpm@10.33.4 install --frozen-lockfile` foi executado exatamente como escrito.
- O lockfile permaneceu alinhado ao `package.json`.
- Esse checkpoint cobre melhor o comportamento esperado na Vercel do que a validacao anterior com `--ignore-scripts`.

## Atualizacao - Checkpoint Django consolidado

- `python manage.py check` passou sem issues.
- `python manage.py makemigrations --check --dry-run` confirmou que nao ha migration pendente.
- Suite completa Django passou novamente com 397 testes.
- O checkpoint cobre o pacote atual de credores FCF, filtros canonicos, pagamentos FCF, action hints e entrada FCF automatica.

## Atualizacao - Pagamentos FCF cobrem credor_id invalido

- O teste do selector de pagamentos FCF agora cobre `credor_id` invalido alem de `creditorId`.
- Ambos os aliases canonicos de id retornam vazio quando recebem valor textual, sem fallback no campo legado `credor`.
- Testes focados e bateria curta de servidor passaram.

## Atualizacao - Pagamentos FCF preservam credor textual legado

- Corrigida a normalizacao de filtros da tela de pagamentos FCF para nao transformar `credor` textual em `creditorId`.
- `creditorId` e `credor_id` continuam estritos por id; `credor` continua compatibilidade textual.
- A bateria focada de servidor passou a incluir essa regressao e agora roda 16 testes.

## Atualizacao - Checkpoint Django apos correcao de pagamentos FCF

- `python manage.py check` passou sem issues apos a mudanca runtime.
- `python manage.py makemigrations --check --dry-run` confirmou ausencia de migration pendente.
- Suite completa Django passou com 398 testes.

## Atualizacao - API FCF separa credor textual de creditorId no payload

- A API/tela FCF principal agora ecoa `creditorId` e `credor_id` somente quando o filtro recebido veio por alias canonico de id.
- Filtros legados por `credor` continuam funcionando como busca textual, mas nao preenchem `filters.creditorId`.
- Documentacao backend/frontend foi alinhada a essa semantica.
- A bateria focada de servidor passou com 17 testes.

## Atualizacao - Checkpoint Django apos ajuste do payload FCF

- `python manage.py check` passou sem issues.
- `python manage.py makemigrations --check --dry-run` confirmou ausencia de migration pendente.
- Suite completa Django passou com 399 testes apos o ajuste de `filters.creditorId` no FCF principal.

## Atualizacao - Atalhos FCF preservam credor textual legado

- Os atalhos de periodo da tela FCF agora preservam `credor` textual quando a tela veio de link legado e nao existe `creditorId`.
- `creditorId` continua sendo o filtro preferencial e estrito por id para novas telas e selects.
- A bateria focada de servidor foi atualizada para cobrir essa compatibilidade visual e passou com 18 testes.

## Atualizacao - Checkpoint Django apos ajuste dos atalhos FCF

- `python manage.py check` passou sem issues.
- `python manage.py makemigrations --check --dry-run` confirmou ausencia de migration pendente.
- Suite completa Django passou com 400 testes apos a preservacao de `credor` textual nos atalhos FCF.

## Atualizacao - Credor cadastrado vence texto legado

- `DividaFinanceira` agora prioriza `credor_cadastro` quando ele existe, sincronizando `credor` textual a partir do cadastro mestre.
- O campo `credor` continua servindo para compatibilidade quando ainda nao ha FK cadastrada.
- Adicionado teste para impedir que texto legado divergente crie/troque credor quando a divida ja aponta para um credor cadastrado.
- A regressao da entrada FCF automatica foi ajustada para trocar credor pelo cadastro mestre, preservando atualizacao de valor/data e remocao ao mudar tipo.
- A bateria focada de servidor passou com 20 testes.

## Atualizacao - Checkpoint Django apos regra principal de credor

- `python manage.py check` passou sem issues.
- `python manage.py makemigrations --check --dry-run` confirmou ausencia de migration pendente.
- Suite completa Django passou com 401 testes apos tornar `credor_cadastro` a fonte principal da divida FCF.

## Atualizacao - Action hint FCF automatico leva creditorId

- Obrigacoes de `financiamento_movimentacao` geradas automaticamente por divida agora incluem `creditorId` no `actionHints.primary.query` quando houver credor cadastrado.
- O link operacional continua levando `sourceType=divida_automatica`, `startDate` e `endDate`.
- A documentação backend/Next e os guias do frontend foram alinhados para repassar `sourceType` e `creditorId` quando vierem do backend.
- A bateria focada de servidor passou novamente com 20 testes.

## Atualizacao - Checkpoint Django apos action hint FCF

- `python manage.py check` passou sem issues.
- `python manage.py makemigrations --check --dry-run` confirmou ausencia de migration pendente.
- Suite completa Django passou com 401 testes apos incluir `creditorId` no action hint FCF automatico.

## Atualizacao - Checkpoint frontend pnpm apos action hint FCF

- `npx --yes pnpm@10.33.4 install --frozen-lockfile` confirmou lockfile alinhado ao `package.json`.
- `npx --yes pnpm@10.33.4 run lint` passou.
- `npx --yes pnpm@10.33.4 run typecheck` passou.
- `npx --yes pnpm@10.33.4 run build` passou com Next.js 16.2.6.

## Atualizacao - Ponto de retomada inclui credores FCF

- O `Ponto de retomada` do plano vivo agora registra que as Fases 641 a 649 consolidaram credores FCF.
- A retomada passa a lembrar que `credor_cadastro` e a fonte principal da divida, enquanto `credor` textual e compatibilidade.
- A retomada tambem registra que action hint FCF manual nao deve levar `creditorId`, enquanto FCF automatico pode levar `sourceType` e `creditorId`.
- Tambem registra a validacao atual de backend com 401 testes e frontend com pnpm install/lint/typecheck/build.

## Atualizacao - Action hint FCF manual nao leva creditorId

- Adicionada regressao garantindo que action hint de movimentacao FCF manual continua com `sourceType=manual`, sem `creditorId`.
- O action hint de entrada FCF automatica permanece coberto com `sourceType=divida_automatica` e `creditorId`.
- A bateria focada de servidor passou novamente com 20 testes.

## Atualizacao - Checkpoint Django apos regressao de action hint manual

- `python manage.py check` passou sem issues.
- `python manage.py makemigrations --check --dry-run` confirmou ausencia de migration pendente.
- `git diff --check` passou sem erros.

## Atualizacao - Suite completa apos action hint manual

- Suite completa Django passou com 401 testes apos a regressao que diferencia action hint FCF manual sem `creditorId` e automatico com `creditorId`.

## Atualizacao - Deploy documenta action hints FCF por origem

- `DEPLOY_ORACLE.md` agora explicita que action hints FCF manuais nao devem levar `creditorId`.
- O mesmo trecho registra que entradas automaticas por divida podem levar `sourceType=divida_automatica` e `creditorId`.
- A orientacao de deploy fica alinhada a bateria focada ja documentada.

## Atualizacao - Guia backend/Next diferencia creditorId por origem FCF

- `INTEGRACAO_NEXT_DJANGO.md` agora explica que `sourceType` separa FCF manual de entrada automatica por divida.
- O guia tambem explicita que `creditorId` acompanha apenas action hints de entradas automaticas com credor cadastrado.
- Action hints FCF manuais ficam documentados sem `creditorId`.

## Atualizacao - Guias frontend alinham action hints FCF

- `docs/INTEGRACAO_FRONTEND_BACKEND.md` e `docs/PROJECT_GUIDE.md` agora orientam repassar `sourceType` quando vier do backend.
- Os guias deixam `creditorId` condicionado ao backend enviar esse filtro, normalmente em entrada automatica por divida com credor cadastrado.
- FCF manual tambem ficou documentado no frontend sem `creditorId`.

## Atualizacao - Pre-flight audita credores de dividas FCF

- Criado o servico de integridade que detecta dividas FCF sem `credor_cadastro` ou com `credor` textual diferente do cadastro mestre.
- Criado `python manage.py sincronizar_credores_dividas_fcf`, em dry-run por padrao e com aplicacao somente via `--aplicar`.
- `validar_preflight_deploy_financeiro --falhar` agora inclui `debtCreditorIntegrity` e sugere o comando de sincronizacao quando encontrar divergencia.
- O comando atualiza somente `credor_cadastro`/`credor`, sem salvar a divida pelo model e sem disparar nova entrada FCF automatica.
- Testes focados passaram cobrindo dry-run, aplicacao e reprova do pre-flight quando o alias textual diverge do credor cadastrado.
- `python manage.py check`, `makemigrations --check --dry-run`, `validar_preflight_deploy_financeiro --falhar` e suite completa Django com 403 testes passaram apos a mudanca.

## Atualizacao - Credores FCF indicam correcao automatica

- `debtCreditorIntegrity.items` agora inclui `action` e `canFix`.
- Quando a divida nao tem `credor_cadastro` nem texto legado, o comando marca `action=corrigir_manual` e `canFix=false`.
- `sincronizar_credores_dividas_fcf --aplicar --falhar-com-pendencia` falha se ainda restar uma pendencia manual.
- Testes focados passaram cobrindo o caso sem texto legado, o caminho corrigivel e o pre-flight.
- `python manage.py check`, `makemigrations --check --dry-run` e `validar_preflight_deploy_financeiro --falhar` passaram apos o ajuste.

## Atualizacao - Pre-flight protege entradas FCF automaticas

- `validar_preflight_deploy_financeiro` agora inclui `debtAutomaticFcfEntryIntegrity`.
- A auditoria compara cada `DividaFinanceira` com a entrada `FinanciamentoMovimentacao` esperada pela Strategy de `emprestimo`/`financiamento`.
- O pre-flight passa a sugerir `python manage.py sincronizar_entradas_fcf_dividas --aplicar` quando houver entrada a criar, atualizar ou remover.
- Isso protege restores, updates diretos e correcoes de credor que possam deixar a entrada FCF automatica desatualizada.
- Testes focados passaram cobrindo base limpa, entrada FCF ausente, credor divergente e o comando de sincronizacao existente.
- `python manage.py check`, `makemigrations --check --dry-run`, `sincronizar_entradas_fcf_dividas --falhar-com-pendencia`, `validar_preflight_deploy_financeiro --falhar` e suite completa Django com 405 testes passaram apos o ajuste.

## Atualizacao - Auditoria FCF automatica sem N+1

- `resumir_integridade_entradas_fcf_dividas()` agora carrega as movimentacoes FCF por divida em lote.
- A regra de auditoria continua igual, mas o pre-flight evita uma consulta por divida em bases maiores.
- Testes focados e `validar_preflight_deploy_financeiro --falhar` passaram apos a otimizacao.

## Atualizacao - Bateria de deploy cobre pre-flight FCF

- `DEPLOY_ORACLE.md` agora inclui os testes dos comandos/pre-flight de credores de dividas FCF.
- A bateria tambem inclui o teste que reprova entrada FCF automatica ausente para divida promovida a `emprestimo`.
- O roteiro de deploy passa a proteger o caminho de correcao automatica e o caminho de pendencia manual sem texto legado.
- A bateria focada documentada passou localmente com 24 testes.

## Atualizacao - Checkpoint frontend pnpm

- O frontend Next.js foi validado novamente com pnpm apos o bloco de pre-flight FCF.
- `npx --yes pnpm@10.33.4 run lint` passou.
- `npx --yes pnpm@10.33.4 run typecheck` passou.
- `npx --yes pnpm@10.33.4 run build` passou com Next.js 16.2.6.

## Atualizacao - JSON no comando de entradas FCF automaticas

- `sincronizar_entradas_fcf_dividas` agora aceita `--json`.
- O payload publica `mode`, `readOnly`, contagens de criadas/atualizadas/removidas/inalteradas, `pendingCount`, `pending` e `consistentAfter`.
- O roteiro de deploy passou a usar `--json` no dry-run e na aplicacao desse comando.
- Testes focados passaram cobrindo a saida JSON em dry-run e aplicacao.
- `python manage.py check`, `makemigrations --check --dry-run`, `sincronizar_entradas_fcf_dividas --json --falhar-com-pendencia` e `validar_preflight_deploy_financeiro --falhar` passaram apos o ajuste.

## Atualizacao - Comando FCF automatico sem N+1

- `sincronizar_entradas_fcf_dividas` agora carrega as movimentacoes FCF vinculadas em lote.
- A saida humana e JSON permanece igual.
- O teste focado do comando e o dry-run JSON local passaram apos a otimizacao.
- Suite completa Django passou novamente com 405 testes apos o JSON e a otimizacao do comando.

## Atualizacao - JSON de entradas FCF alinha checked e limit

- `sincronizar_entradas_fcf_dividas --json` agora publica `checked`.
- O comando passou a aceitar `--limit`, alinhado ao comando de credores FCF.
- O dry-run real com `--limit 5` avaliou 16 dividas e retornou JSON consistente.
- `python manage.py check` e `makemigrations --check --dry-run` passaram apos o ajuste.

## Atualizacao - Entradas FCF revalidam apos aplicar

- `sincronizar_entradas_fcf_dividas --aplicar --json` agora reexecuta a auditoria apos aplicar as correcoes.
- O JSON passou a publicar `remainingIssues`.
- `--falhar-com-pendencia` agora tambem reprova quando restar pendencia depois de `--aplicar`.
- Teste focado e dry-run real passaram apos o ajuste.
- `python manage.py check`, `makemigrations --check --dry-run` e `validar_preflight_deploy_financeiro --falhar` passaram apos a revalidacao pos-aplicacao.

## Atualizacao - Checkpoint completo pos-FCF

- A suite completa Django foi repetida depois das fases de credores FCF, pre-flight e entradas FCF automaticas.
- No servidor, os comandos `python manage.py ...` assumem o `venv` ativado; no Windows local foi usado `venv\\Scripts\\python.exe`.
- O erro do Python global sem Django foi tratado como problema de ambiente local, nao como falha da aplicacao.
- `venv\\Scripts\\python.exe manage.py test` passou com 405 testes.

## Atualizacao - Regressao do fluxo credor -> entrada FCF

- Criada regressao garantindo que `sincronizar_credores_dividas_fcf --aplicar` corrige somente o cadastro/alias do credor.
- A entrada FCF automatica de `emprestimo`/`financiamento` nao e recriada por esse comando; se ficar desatualizada, o pre-flight aponta a pendencia.
- `sincronizar_entradas_fcf_dividas --aplicar --json --falhar-com-pendencia` continua sendo o passo responsavel por atualizar a movimentacao automatica.
- O roteiro de deploy passou a documentar essa sequencia em duas etapas.
- Teste novo e bateria focada de credores/pre-flight/entrada FCF automatica passaram.
- `python manage.py check`, `makemigrations --check --dry-run`, `validar_preflight_deploy_financeiro --falhar` e suite completa Django com 406 testes passaram apos a regressao.

## Atualizacao - JSON de credores FCF publica pendingCount

- `sincronizar_credores_dividas_fcf --json` agora publica `pendingCount`.
- `checked` foi mantido para compatibilidade com as fases anteriores do comando.
- A saida humana do comando passou a usar `pendingCount` para exibir pendencias encontradas.
- O roteiro de deploy documenta o novo campo para revisao no servidor.
- `python manage.py check`, `makemigrations --check --dry-run` e dry-run JSON real passaram apos o ajuste.

## Atualizacao - Bateria de deploy FCF revalidada

- A bateria focada de deploy foi repetida depois de incluir a regressao do fluxo credor -> entrada FCF.
- O roteiro `DEPLOY_ORACLE.md` agora lista 25 testes recentes de FCI/FCF, credores, action hints, pagamentos FCF, pre-flight e entradas automaticas.
- A bateria passou localmente com 25 testes.

## Atualizacao - Suite completa apos pendingCount de credores FCF

- A suite completa Django foi repetida depois do ajuste `pendingCount` no comando de credores FCF.
- `venv\\Scripts\\python.exe manage.py test` passou com 406 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Limit negativo bloqueado nos comandos FCF

- `sincronizar_credores_dividas_fcf` e `sincronizar_entradas_fcf_dividas` agora rejeitam `--limit` negativo com `CommandError`.
- `--limit` continua controlando apenas a quantidade de itens detalhados no relatorio.
- O roteiro de deploy passou a documentar que o valor deve ser maior ou igual a zero.
- Testes focados, `python manage.py check` e `makemigrations --check --dry-run` passaram apos o ajuste.

## Atualizacao - Checkpoint Vercel/pnpm final

- O frontend Next.js foi validado novamente depois dos checkpoints backend recentes.
- `npx --yes pnpm@10.33.4 install --frozen-lockfile` confirmou lockfile sincronizado.
- `npx --yes pnpm@10.33.4 run lint` passou.
- `npx --yes pnpm@10.33.4 run typecheck` passou.
- `npx --yes pnpm@10.33.4 run build` passou com Next.js 16.2.6.

## Atualizacao - Pre-flight FCF publica pendingCount

- `debtCreditorIntegrity` e `debtAutomaticFcfEntryIntegrity` agora publicam `pendingCount`.
- `totalIssues` foi mantido para compatibilidade com o contrato anterior do pre-flight.
- O roteiro de deploy documenta o campo para revisoes JSON no servidor.
- Testes focados, pre-flight JSON real, `python manage.py check` e `makemigrations --check --dry-run` passaram apos o ajuste.

## Atualizacao - Suite completa apos pendingCount no pre-flight

- A suite completa Django foi repetida depois de alinhar `pendingCount` no pre-flight FCF.
- `venv\\Scripts\\python.exe manage.py test` passou com 408 testes.

## Atualizacao - Remediation plan FCF usa falha por pendencia

- O `remediationPlan` do pre-flight passou a sugerir `--falhar-com-pendencia` nas sincronizacoes FCF.
- Isso vale para `sincronizar_credores_dividas_fcf --aplicar` e `sincronizar_entradas_fcf_dividas --aplicar`.
- O roteiro de deploy foi alinhado para aplicar entradas FCF automaticas com `--falhar-com-pendencia`.
- Testes focados, `python manage.py check`, `makemigrations --check --dry-run` e pre-flight real passaram apos o ajuste.
- A suite completa Django foi repetida depois do ajuste e passou com 408 testes.

## Atualizacao - Pre-flight rejeita limits negativos

- `validar_preflight_deploy_financeiro` agora rejeita limites negativos antes de executar auditorias.
- A validacao cobre `--canonical-limit`, `--valores-editaveis-limit`, `--lancamentos-limit`, `--credores-dividas-limit` e `--entradas-fcf-dividas-limit`.
- `DEPLOY_ORACLE.md` documenta essa regra.
- Testes focados, `python manage.py check`, `makemigrations --check --dry-run` e pre-flight real passaram apos o ajuste.
- A suite completa Django foi repetida depois do ajuste e passou com 409 testes.

## Atualizacao - Boundary interno do pre-flight validado

- A validacao de limites do pre-flight foi movida para a funcao `validar_preflight_deploy_financeiro()`.
- Assim, chamadas programaticas futuras tambem rejeitam limites negativos, nao apenas o uso via CLI.
- O teste de limites cobre o comando e a chamada direta da funcao.
- Testes focados, `python manage.py check`, `makemigrations --check --dry-run` e pre-flight real passaram apos o ajuste.
- A suite completa Django foi repetida depois do ajuste e passou com 409 testes.

## Atualizacao - Services FCF rejeitam limit negativo

- Os services de integridade de credores FCF e entradas FCF automaticas agora rejeitam `limit` negativo com `ValueError`.
- Isso protege chamadas internas futuras, alem dos comandos CLI ja validados.
- Testes focados, `python manage.py check`, `makemigrations --check --dry-run` e pre-flight real passaram apos o ajuste.
- A suite completa Django foi repetida depois do ajuste e passou com 410 testes.

## Atualizacao - Limit zero preserva contagens FCF

- `limit=0` nos services de integridade FCF preserva contagens e retorna listas de itens vazias.
- `--limit=0` nos comandos JSON de credores FCF e entradas FCF automaticas tambem preserva `pendingCount` e omite detalhes.
- O roteiro de deploy documenta esse uso para relatorios somente com contagens.
- Testes focados, `python manage.py check`, `makemigrations --check --dry-run` e pre-flight real passaram apos o ajuste.
- A suite completa Django foi repetida depois do ajuste e passou com 411 testes.

## Atualizacao - Checkpoint backend/frontend de prontidao

- O pre-flight JSON do backend foi repetido com `validar_preflight_deploy_financeiro --json --falhar`.
- A validacao confirmou `debtCreditorIntegrity.pendingCount=0`, `debtAutomaticFcfEntryIntegrity.pendingCount=0`, `remediationPlan.steps=[]` e system check sem issues.
- O frontend Next.js foi revalidado na trilha Vercel/pnpm: `install --frozen-lockfile`, `lint`, `typecheck` e `build`.
- Nenhuma regra financeira, migration, endpoint ou tela nova foi aberta neste checkpoint.

## Atualizacao - Checkpoint de deploy cache/cookies

- O comando documentado para validar cache pelo Django foi testado com `shell --no-imports` e retornou `ok`.
- `check --deploy` foi repetido com variaveis temporarias de producao simulando HTTPS, cookies seguros, HSTS, proxy SSL, `ALLOWED_HOSTS` e `SECRET_KEY` forte.
- A validacao de deploy simulada passou sem issues.
- O `check --deploy` com `DEBUG=True` local continua gerando alertas esperados de ambiente, sem indicar erro da aplicacao.

## Atualizacao - Normalizador frontend de credores mais robusto

- `getFinancialCreditorsData()` agora usa o primeiro id inteiro positivo entre `creditorId`, `credor_id`, `id` e `value`.
- Um alias invalido como `creditorId=0` nao bloqueia outro alias valido recebido no mesmo item.
- O alias legado `credor_id` tambem passa a refletir o id normalizado.
- Opcoes sem id inteiro positivo continuam descartadas, sem fallback textual para `creditorId`.
- A documentacao do frontend foi alinhada e a trilha pnpm `install --frozen-lockfile`, `lint`, `typecheck` e `build` passou.

## Atualizacao - Permissao do endpoint mestre de credores FCF

- `GET /api/fcf/creditors/` agora exige `caixa.view_credor`.
- A API FCF principal continua protegida pela permissao da tela FCF, sem alterar filtros, agrupamentos ou pagamentos.
- Isso separa a leitura do cadastro mestre de credores da leitura de parcelas FCF.
- Testes focados de permissao/API passaram e os guias backend/frontend foram atualizados.

## Atualizacao - Suite completa apos permissao de credores

- A suite completa Django foi repetida depois da troca de permissao do endpoint dedicado de credores.
- `venv\\Scripts\\python.exe manage.py test` passou com 411 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Endpoint de credores FCF responde erros em JSON

- `GET /api/fcf/creditors/` passou a usar a protecao de API com resposta JSON para 401/403.
- Sem sessao, o endpoint retorna `{"detail": "Authentication credentials were not provided."}`.
- Sem `view_credor`, o endpoint retorna `{"detail": "Permission denied."}`.
- Isso prepara melhor o consumo pelo Next.js sem alterar a API FCF principal.

## Atualizacao - Suite completa apos erros JSON de credores

- A suite completa Django foi repetida depois de alinhar 401/403 JSON no endpoint dedicado de credores.
- `venv\\Scripts\\python.exe manage.py test` passou com 412 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - APIs FCI/FCF respondem erros em JSON

- `/api/fci/` e `/api/fcf/` passaram a usar protecao de API com respostas JSON para 401/403.
- As telas Django HTML de FCI/FCF continuam usando as permissoes atuais de tela.
- O contrato foi documentado para o Next.js junto com `/api/dashboard/financial-overview/` e `/api/fcf/creditors/`.
- Testes focados, `check`, `makemigrations --check`, lint e typecheck do frontend passaram.

## Atualizacao - Suite completa apos APIs FCI/FCF JSON

- A suite completa Django foi repetida depois de alinhar `/api/fci/` e `/api/fcf/` para 401/403 JSON.
- `venv\\Scripts\\python.exe manage.py test` passou com 413 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - API mes financeiro responde erros em JSON

- `require_api_permission()` agora aceita uma lista de permissoes e exige todas elas.
- `/api/mes-financeiro/` passou a usar esse boundary de API para retornar 401/403 em JSON.
- A tela HTML de mes financeiro continua usando a permissao de tela existente.
- Testes focados, `check`, `makemigrations --check`, lint e typecheck do frontend passaram.

## Atualizacao - Suite completa apos API mes financeiro JSON

- A suite completa Django foi repetida depois de alinhar `/api/mes-financeiro/` para 401/403 JSON.
- `venv\\Scripts\\python.exe manage.py test` passou com 414 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Boundary JSON da mutation de baixa

- A mutation `/api/obrigacoes-financeiras/liquidar/` ja retornava 401/403 em JSON; agora esse contrato tem regressao explicita.
- O teste de falta de permissao valida `{"detail": "Permission denied."}`.
- O teste sem sessao valida `{"detail": "Authentication credentials were not provided."}`.
- Nenhuma regra de baixa, ledger ou canonical-first foi alterada.

## Atualizacao - Suite completa apos boundary da mutation

- A suite completa Django foi repetida depois de adicionar a regressao da mutation de baixa.
- `venv\\Scripts\\python.exe manage.py test` passou com 415 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Boundary JSON de ledger e obrigacoes canonicas

- As APIs `/api/lancamentos-financeiros/`, `/api/obrigacoes-financeiras/`, `/api/modelagem-financeira-canonica/` e `/api/baixas-financeiras-canonicas/` agora tem regressao explicita para 401/403 em JSON.
- A cobertura protege o contrato consumido pelo Next.js sem alterar leitura, filtros, baixas, ledger ou canonical-first.
- Testes focados passaram com 4 testes; `check`, `makemigrations --check`, lint e typecheck do frontend tambem passaram.

## Atualizacao - Suite completa apos boundary de ledger/canonico

- A suite completa Django foi repetida depois de adicionar as regressoes das APIs read-only de ledger, obrigacoes e modelagem canonica.
- `venv\\Scripts\\python.exe manage.py test` passou com 417 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Respostas JSON 401/403 centralizadas

- `permissions.py` passou a concentrar as respostas JSON padrao de API para sessao ausente e permissao negada.
- `require_api_permission()` e a mutation `/api/obrigacoes-financeiras/liquidar/` agora reutilizam os mesmos helpers.
- A mudanca reduz risco de drift no contrato do Next.js sem alterar permissoes, baixa, ledger, canonical-first ou regras FCF.
- Testes focados passaram com 6 testes; `check` e `makemigrations --check` tambem passaram.

## Atualizacao - Suite completa apos centralizar boundary JSON

- A suite completa Django foi repetida depois de centralizar as respostas 401/403 de API.
- `venv\\Scripts\\python.exe manage.py test` passou com 417 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Checkpoint Vercel/pnpm apos boundary JSON

- O frontend Next.js foi revalidado com pnpm 10.33.4 depois das atualizacoes de documentacao de integracao.
- `npx --yes pnpm@10.33.4 install --frozen-lockfile` confirmou que o lockfile esta atualizado.
- `npx --yes pnpm@10.33.4 run build` passou com Next.js 16.2.6.

## Atualizacao - Login API aceita JSON com charset

- O login `/api/auth/login/` agora aceita `Content-Type: application/json; charset=utf-8`, mantendo rejeicao para formatos que nao sejam JSON.
- A mudanca evita incompatibilidade comum entre clientes HTTP e Django sem abrir formulario ou payload nao JSON.
- Testes focados de login, `check` e `makemigrations --check` passaram.

## Atualizacao - Suite completa apos login com charset

- A suite completa Django foi repetida depois de aceitar charset no `Content-Type` do login da API.
- `venv\\Scripts\\python.exe manage.py test` passou com 417 testes.
- Nenhuma migration nova foi criada nesse checkpoint.

## Atualizacao - Documentacao do login com charset

- `INTEGRACAO_NEXT_DJANGO.md` e os guias do frontend agora dizem que o login aceita JSON com ou sem `charset`.
- A documentacao antiga que falava apenas em `application/json` foi ajustada para evitar interpretacao restritiva incorreta.
- A mudanca e apenas documental.

## Atualizacao - Logout visivel no Next.js

- O frontend passou a exibir botao `Sair` no header das telas autenticadas.
- O logout usa `POST /api/auth/logout/` com CSRF pelo service de auth, sem `fetch` direto no componente visual.
- Dashboard financeiro e tela de obrigacoes fazem `refetch` apos encerrar a sessao, retornando ao estado de login quando o backend responder 401.
- A mudanca nao altera sessao, CSRF, permissoes, APIs financeiras, baixa, ledger, canonical-first ou regras FCF.
- `install --frozen-lockfile`, `lint`, `typecheck`, `build` do frontend e `git diff --check` passaram apos a mudanca.

## Atualizacao - Headers HTTP enxutos no Next.js

- `lib/api/http-client.ts` passou a enviar `Content-Type: application/json` somente quando a chamada tem body.
- GETs continuam enviando `Accept: application/json`, mas evitam preflight CORS desnecessario por `Content-Type`.
- A mudanca preserva POSTs com body JSON, como login e baixa, sem alterar APIs Django ou regras financeiras.
- `check`, `makemigrations --check`, `lint`, `typecheck` e `build` passaram apos a mudanca.

## Atualizacao - Service de sessao no Next.js

- `features/auth/services/backend-auth-service.ts` passou a expor `getBackendSession()` para consumir `GET /api/auth/session/`.
- A mudanca completa o contrato frontend/backend de auth sem ligar UI nova.
- Nenhuma regra financeira, baixa, ledger, canonical-first ou comportamento FCF foi alterado.

## Atualizacao - `apiFetch` separa opcoes internas

- `apiFetch()` deixou de repassar `query` e `timeoutMs` para o objeto nativo do `fetch`.
- O client agora separa opcoes internas antes de montar `RequestInit`, preservando headers normalizados e abort externo.
- `lint`, `typecheck` e `build` do frontend passaram apos a mudanca.

## Ponto de pausa - investigar caixa acumulado do mes financeiro

- Pausa registrada apos a Fase 709, com backend e frontend staged e sem commit.
- Possivel correcao seguinte: revisar por que o Mes Financeiro de `2026-03-01` a `2026-03-28` mostra `Caixa acumulado para pagamento` de `R$ 7.821,97`.
- Comparacao informada:
  - Fevereiro `2026-02-01` a `2026-02-28`: caixa acumulado `R$ 1,21`, contas pendentes `R$ 590,80`, deficit `R$ 590,80`.
  - Marco `2026-03-01` a `2026-03-28`: resultado realizado `R$ 727,42`, contas pendentes `R$ 272,12`, caixa acumulado `R$ 7.821,97`.
- Diagnostico tecnico inicial:
  - O cartao usa `caixa_disponivel_acumulado`, vindo de `saldo_caixa_disponivel(data_final)`.
  - `saldo_caixa_disponivel()` soma entradas e saidas realizadas acumuladas ate a data limite, nao apenas o periodo filtrado.
  - Entradas consideradas: receitas recebidas, investimentos de entrada realizados e financiamentos de entrada realizados ate a data.
  - Saidas consideradas: despesas manuais pagas, custos fixos pagos, investimentos de saida, financiamentos de saida, pagamentos de parcelas FCF, custos de servico, custos extras e parcelas legadas.
  - Portanto, mesmo sem FCF ou investimento no periodo, o saldo pode vir de receitas recebidas ou pagamentos fora do recorte mensal, mas com data efetiva ate `2026-03-28`.
- Comandos recomendados no servidor antes de corrigir:
  - `python manage.py diagnosticar_caixa_disponivel --data=2026-02-28 --data-inicial=2026-02-01 --limit=200`
  - `python manage.py diagnosticar_caixa_disponivel --data=2026-03-28 --data-inicial=2026-03-01 --limit=200`
  - Se a saida ficar grande: repetir com `--sem-detalhes` primeiro e depois aumentar `--limit`.
- Hipotese para revisar:
  - Se o nome esperado pelo usuario for "caixa do mes", o template pode estar exibindo o acumulado correto com label ambigua.
  - Se o valor deveria bater apenas com o periodo, a regra deve trocar o cartao para `caixa_final_mes` ou expor os dois campos com nomes diferentes.
  - Antes de alterar, conferir as entradas detalhadas do comando para localizar exatamente os `R$ 7.093,34` alem do resultado de marco.

## Atualizacao - Diagnostico do caixa acumulado de marco

- Resultado informado pelo servidor:
  - `2026-02-28`: entradas acumuladas `R$ 5.492,00`, saidas acumuladas `R$ 5.490,79`, caixa `R$ 1,21`.
  - `2026-03-28`: entradas acumuladas `R$ 15.550,00`, saidas acumuladas `R$ 7.728,03`, caixa `R$ 7.821,97`.
- Leitura:
  - De fevereiro para marco, entraram `R$ 10.058,00` e sairam efetivamente pelo caixa `R$ 2.237,24`.
  - Entao o caixa acumulado de marco veio de `R$ 1,21 + R$ 10.058,00 - R$ 2.237,24 = R$ 7.821,97`.
  - A diferenca nao aponta FCF/investimento; aponta divergencia de base entre o `Pago` da tela (`R$ 9.330,58`) e as saidas efetivas de caixa do periodo (`R$ 2.237,24`).
- Entrega feita:
  - `diagnosticar_caixa_disponivel` agora compara `Pago` do Mes Financeiro com saidas de caixa por data efetiva dentro do periodo.
  - Nova flag: `--detalhar-mes-financeiro`, para listar as contas que formam o total pago da tela.
  - Validacao local: `python manage.py test` passou com 419 testes e `makemigrations --check --dry-run` nao apontou migrations.
- Proximo comando recomendado no servidor:
  - `python manage.py diagnosticar_caixa_disponivel --data=2026-03-28 --data-inicial=2026-03-01 --detalhar-mes-financeiro --limit=300`
- Ainda fora do escopo:
  - Nao foi alterado calculo da tela, API do Next.js, baixa, ledger, canonical-first nem regra FCF de `emprestimo`/`financiamento`.

## Atualizacao - Caixa reconhece custo de servico legado

- O diagnostico detalhado do servidor mostrou que `R$ 7.093,34` estavam em despesas sincronizadas de custo de servico do ARTNOR com `valor_pago`, mas sem `PagamentoEventoCustoServico`.
- O caixa agora considera essas saidas como `pagamento_custo_servico_legado`, somente pela diferenca ainda nao coberta por pagamentos estruturados.
- Isso preserva historico antigo e evita dupla contagem quando `PagamentoEventoCustoServico` ja existe.
- A implementacao final usa agregacao em lote para preservar os testes de queries constantes.
- `factory-boy` e `Faker` ja estao disponiveis no ambiente dev; nao foi necessario adicionar dependencia de producao.
- Validacao local: `python manage.py test` passou com 421 testes; `check` e `makemigrations --check --dry-run` tambem passaram.
- Depois do deploy, repetir:
  - `python manage.py diagnosticar_caixa_disponivel --data=2026-03-28 --data-inicial=2026-03-01 --detalhar-mes-financeiro --limit=300`
- Resultado esperado, se os dados nao mudaram:
  - A saida por origem deve incluir `pagamento_custo_servico_legado`.
  - O caixa acumulado de marco deve ficar perto de `R$ 728,63`, que e o resultado realizado de marco `R$ 727,42` mais o saldo anterior `R$ 1,21`.
- Confirmacao no servidor:
  - O diagnostico retornou caixa disponivel `R$ 728,63`.
  - `Pago` do Mes Financeiro e saidas de caixa do periodo bateram em `R$ 9.330,58`.
  - `pagamento_custo_servico_legado` apareceu com 5 itens e total `R$ 7.093,34`.
  - A diferenca restante de `R$ 1,21` e o saldo positivo anterior de fevereiro, nao uma nova divergencia de marco.

## Atualizacao - Regressao de sessao autenticada

- `GET /api/auth/session/` agora tem teste cobrindo usuario autenticado para o frontend.
- A regressao valida `authenticated`, `csrfToken`, dados publicos do usuario e `canViewDashboard`.
- Testes focados, `check` e `makemigrations --check` passaram.

## Atualizacao - Suite completa apos sessao/auth

- A suite completa Django foi repetida depois da regressao de sessao autenticada.
- `venv\\Scripts\\python.exe manage.py test` passou com 418 testes.
- O build de producao do Next.js tambem foi repetido e passou.

## Atualizacao - Painel de login consulta sessao ativa

- O frontend Next.js passou a consumir `getBackendSession()` no `DashboardAuthState`.
- Quando o painel de login abre e a sessao Django ainda esta autenticada com permissao de dashboard, a UI chama `onRetry()` e recarrega os dados reais sem pedir senha novamente.
- A checagem fica restrita ao service de auth e ao client HTTP; nao houve `fetch` direto no componente nem armazenamento de token no navegador.
- Fora do escopo: backend runtime, migrations, regras financeiras, caixa, canonical-first, baixas, ledger e regra FCF de `emprestimo`/`financiamento`.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Roteiro de auth sem pendencia duplicada

- O roteiro do frontend deixou de listar "implementar logout" como pendencia, porque o botao de sair ja foi entregue.
- A pendencia correta agora e criar teste automatizado para CSRF, sessao expirada, sessao ativa via `getBackendSession()` e logout visivel.
- `INTEGRACAO_NEXT_DJANGO.md` registra que componentes visuais nao devem chamar `fetch` diretamente para auth.
- Nao houve mudanca de runtime, migration, endpoint, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.

## Atualizacao - Cancelamento robusto no client HTTP do frontend

- `apiFetch()` agora respeita `AbortSignal` ja abortado antes de chamar `fetch`.
- Isso melhora hooks de dados e auth em troca rapida de filtros, logout/login ou desmontagem de componente.
- A mudanca nao altera endpoints, credentials, headers JSON, timeout, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Auth service sem cache no frontend

- O service de auth do Next.js agora usa `cache: "no-store"` em CSRF, login, sessao e logout.
- Isso acompanha o contrato do Django de respostas de autenticacao nao cacheaveis.
- A regra ficou no service; componentes visuais continuam sem `fetch` direto e sem armazenamento de senha, sessao ou CSRF.
- Nao houve mudanca de runtime backend, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - AbortError compativel no frontend

- `isAbortError()` agora reconhece qualquer objeto com `name === "AbortError"`.
- Isso deixa os hooks mais robustos quando cancelamentos passam por browser, runtime Next.js ou Node sem depender de `DOMException`/`Error`.
- Nao houve mudanca de backend runtime, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Auth nao vira fallback auxiliar no dashboard

- Chamadas auxiliares de obrigacoes usadas pelo dashboard agora repropagam 401/403.
- O fallback parcial continua permitido apenas para indisponibilidade comum da API auxiliar, sem mascarar sessao expirada ou falta de permissao.
- Os guias backend/frontend foram alinhados com essa regra.
- Nao houve mudanca de backend runtime, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Dados financeiros sem cache no frontend

- Services financeiros reais do Next.js agora usam `cache: "no-store"`.
- A politica cobre dashboard, obrigacoes, ledger, credores FCF, baixas canonicas e liquidacao de obrigacao.
- Isso evita saldos, baixas e conciliacoes defasadas no cliente sem alterar regra financeira.
- Nao houve mudanca de backend runtime, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Content-Type JSON apenas para body serializado

- `apiFetch()` agora aplica `Content-Type: application/json` automaticamente apenas quando o body e string.
- Login e liquidacao continuam funcionando porque usam `JSON.stringify(...)`.
- Isso evita header JSON indevido em futuros `FormData`/uploads.
- Nao houve mudanca de backend runtime, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Resposta vazia tolerada no frontend

- `parseResponse()` do client HTTP agora le o texto da resposta e retorna `null` quando o body vem vazio.
- Isso evita erro de JSON parsing em respostas sem corpo, como 204 ou futuras mutations sem payload.
- Nao houve mudanca de backend runtime, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Detail do Django preservado no frontend

- `apiFetch()` agora usa `detail` de erros JSON do Django como `ApiError.message` quando esse campo existe.
- O payload original continua em `ApiError.details`, mantendo compatibilidade com consumers que leem `errors`, status ou detalhes estruturados.
- O login continua usando mensagem propria no service de auth para nao expor detalhe sensivel.
- Nao houve mudanca de backend runtime, endpoints financeiros, regra de caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Mensagem de API sem mojibake no frontend

- Uma mensagem local de `getFinancialLedgerData()` foi padronizada para `NEXT_PUBLIC_API_BASE_URL não configurada.`.
- A correcao ficou restrita ao texto comprovadamente corrompido, sem alterar fallback, fetch, contrato, regra financeira ou mocks.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.

## Atualizacao - Mensagem de API centralizada no service financeiro

- `financial-dashboard-service` agora usa `API_BASE_URL_NOT_CONFIGURED_MESSAGE` para todos os guards de API base ausente.
- Isso evita nova divergencia textual entre dashboard, ledger, credores FCF, obrigacoes, baixas canonicas e liquidacao.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Payload de erro centralizado no frontend

- `lib/api/http-client` agora publica `getApiErrorPayloadMessage()` para ler a primeira mensagem em `errors` e depois `detail`.
- `apiFetch()` e a tela de obrigacoes financeiras usam o mesmo helper, mantendo `ApiError.details` como payload tecnico.
- O login continua com mensagem propria no service de auth.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Classificacao auth centralizada no frontend

- `lib/api/http-client` agora publica `ApiErrorKind` e `getApiErrorKind()`.
- Hooks de dashboard, obrigacoes financeiras e credores FCF passaram a usar esse helper para distinguir `unauthorized`, `forbidden` e `unknown`.
- Os nomes publicos `FinancialDashboardErrorKind`, `FinancialObligationsErrorKind` e `FinancialCreditorsErrorKind` foram preservados como aliases.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Normalizacao de erro centralizada no frontend

- `lib/api/http-client` agora publica `normalizeApiError(error, fallbackMessage)`.
- Hooks de dashboard, obrigacoes financeiras e credores FCF passaram a usar esse helper antes de salvar erro no estado.
- `ApiError` e `Error` reais continuam intactos; valores desconhecidos recebem a mensagem fallback especifica do hook.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Payloads DRF de erro mais resilientes no frontend

- `getApiErrorPayloadMessage()` agora entende `errors`, `detail`, `non_field_errors`, `field_errors`, `message` e erros de campo no topo do payload.
- Campos reservados como `status`, `code`, `meta`, `data`, `results` e paginacao sao ignorados na busca generica por erro de campo.
- `ApiError.details` continua preservando o payload original para consumers que precisem de campos estruturados.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Fallback financeiro com policy local no frontend

- `financial-dashboard-service` agora centraliza a regra `abort/auth/permissao => rethrow` em `shouldRethrowFinancialDashboardError()`.
- O fallback auxiliar de obrigacoes e o fallback mockado do dashboard continuam com o mesmo comportamento, mas sem duplicar a condicao.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.

## Atualizacao - Auth usa helper central de status HTTP

- `getAuthErrorMessage()` agora usa `getApiErrorStatus(error)` em vez de ler `ApiError.status` diretamente.
- As mensagens de login para 400/401, 403 e erro generico foram preservadas.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` temporaria apenas para o comando.
- Validacao backend completa: `python manage.py test` passou com `SECRET_KEY` e `DEBUG=True` temporarios locais, 421 testes.
- Observacao de ambiente: uma tentativa sem `DEBUG=True` local redirecionou requisicoes para HTTPS por `SECURE_SSL_REDIRECT`, gerando 301 em massa; para rodar testes locais, usar `DEBUG=True` ou desativar esse redirect no ambiente de teste.

## Atualizacao - Guard de API financeira centralizado no frontend

- `financial-dashboard-service` agora usa `shouldUseFinancialMockFallback()` e `requireFinancialApiBaseUrl()` para tratar API base ausente.
- Fluxos que ja permitiam mock continuam retornando mock/empty fallback quando `useMockFallback` esta habilitado.
- Baixas canonicas e liquidacao continuam exigindo backend real.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Mensagem de API base no client HTTP

- `API_BASE_URL_NOT_CONFIGURED_MESSAGE` agora e exportada por `lib/api/http-client`.
- `buildUrl()` e `financial-dashboard-service` usam a mesma constante para evitar drift textual.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Estado de erro dos hooks financeiros centralizado

- Criado `financial-hook-state.ts` no frontend para compartilhar montagem de estado de sucesso e erro dos hooks financeiros.
- Dashboard, obrigacoes e credores continuam preservando dados antigos em erro comum e limpando dados em 401/403.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Estado visual dos hooks financeiros centralizado

- `financial-hook-state.ts` agora tambem publica `getFinancialHookViewState()`.
- Dashboard, obrigacoes e credores usam o helper para calcular erro visivel, loading e refreshing.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Refetch dos hooks financeiros centralizado

- `financial-hook-state.ts` agora publica `useFinancialHookRequestVersion()`.
- Dashboard, obrigacoes e credores usam o hook compartilhado para incrementar a versao de request no `refetch`.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Estado inicial dos hooks financeiros centralizado

- `financial-hook-state.ts` agora publica `buildFinancialHookInitialState()`.
- Dashboard, obrigacoes e credores usam o helper para iniciar `data`, `error`, `errorKind` e `completedRequestKey`.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Boundary client do helper de hooks financeiros

- `financial-hook-state.ts` agora declara `'use client'`, porque tambem exporta um hook React compartilhado.
- A mudanca deixa explicito que o helper pertence ao fluxo client-side do Next.js.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Contrato de refetch dos hooks financeiros tipado

- Criado `FinancialHookRequestVersionState` no helper compartilhado do frontend.
- `useFinancialHookRequestVersion()` passou a declarar retorno explicito com `requestVersion` e `refetch`.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Chave de request dos hooks financeiros centralizada

- Criado `buildFinancialHookRequestKey()` no helper compartilhado do frontend.
- Dashboard e obrigacoes usam o helper para montar a chave `queryKey:requestVersion`.
- `useFinancialCreditors` permanece com chave numerica propria, porque nao usa `queryKey`.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Origem esperada dos hooks financeiros centralizada

- Criado `isFinancialHookUsingFallbackData()` no helper compartilhado do frontend.
- Dashboard e obrigacoes continuam esperando `backend`; credores continua esperando `cadastro_credor`.
- A mudanca reduz duplicidade sem alterar fallback, mocks, endpoints ou payloads.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Ciclo assincrono dos hooks financeiros centralizado

- Criado `useFinancialHookResource()` no helper compartilhado do frontend.
- Dashboard, obrigacoes e credores agora compartilham `AbortController`, sucesso, erro normalizado e view state.
- Cada hook ainda mantem seus filtros, query keys, services e fontes esperadas explicitos.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Fontes esperadas dos hooks financeiros tipadas

- Criadas `FINANCIAL_HOOK_BACKEND_SOURCE` e `FINANCIAL_HOOK_CREDITORS_SOURCE` no helper compartilhado do frontend.
- Criado `FinancialHookExpectedSource` para tipar o contrato aceito por `isFinancialHookUsingFallbackData()`.
- Dashboard e obrigacoes seguem usando `backend`; credores segue usando `cadastro_credor`.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Guards do service financeiro com retorno explicito

- `shouldRethrowFinancialDashboardError()` e `shouldUseFinancialMockFallback()` agora declaram retorno `boolean`.
- `requireFinancialApiBaseUrl()` agora declara retorno `void`.
- A mudanca explicita contratos internos sem alterar fallback, API base, endpoints, payloads ou mocks.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Helpers internos de numero e periodo tipados

- Criado `FinancialPeriodDateRange` no service financeiro do frontend.
- Tipados retornos de helpers internos de numero, data e periodo usados por normalizacao e filtros.
- A mudanca explicita contratos sem alterar calculo financeiro, filtros, endpoints ou payloads.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Contratos de query do service financeiro tipados

- Importado `DashboardQueryParams` no service financeiro do frontend.
- Criados contratos serializaveis para queries de obrigacoes e ledger.
- Tipados `toQuery()`, `normalizeObligationStatusForScope()`, `toObligationsQuery()` e `toLedgerQuery()`.
- A mudanca explicita contratos sem alterar filtros, endpoints, payloads ou mocks.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Retornos async de leitura financeira tipados

- Tipados retornos das leituras async de obrigacoes, ledger e baixas canonicas no service financeiro do frontend.
- A mudanca explicita a superficie consumida por hooks e telas sem alterar chamadas, endpoints ou payloads.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Defaults de query financeira centralizados

- Criadas constantes locais para fonte canonica, tipo padrao da obrigacao e limites de listagem/preview/divergencias no service financeiro do frontend.
- Builders e leituras financeiras passaram a usar as constantes sem alterar os valores enviados ao Django.
- A mudanca reduz literais soltos em futuras telas e preserva filtros, endpoints, payloads e mocks.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Validacao ampla backend do bloco financeiro

- Executada a suite completa do backend pelo `venv` local.
- `python manage.py test` passou com 421 testes usando `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.
- A validacao fecha o bloco recente de hooks/service financeiro antes de voltar a fluxos maiores.
- Nao houve mudanca de backend runtime, endpoint, migration, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.

## Atualizacao - Helpers de payload futuro para dividas FCF

- Criados helpers no service financeiro do frontend para montar payloads futuros de criacao/edicao de dividas.
- `buildCreateFinancialDebtRequestPayload()` e `buildUpdateFinancialDebtRequestPayload()` convertem ids de formulario/select para inteiros positivos antes da chamada ao Django.
- A documentacao backend/frontend foi alinhada para orientar o uso desses helpers em futuras telas Next.js.
- Nao houve criacao de tela, endpoint, mutation real, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Mensagens de id dos helpers de dividas refinadas

- `optionalFinancialDebtPositiveId()` passou a receber o nome do campo.
- Helpers futuros de payload de divida agora diferenciam erro de `contractId` e `eventId`.
- Nao houve criacao de tela, endpoint, mutation real, regra financeira, caixa, baixa, ledger, canonical-first ou FCF.
- Validacao frontend: `npx --yes pnpm@10.33.4 run lint`, `npx --yes pnpm@10.33.4 run typecheck` e `npx --yes pnpm@10.33.4 run build` passaram.
- Observacao: o frontend ainda nao possui runner de teste unitario configurado; a validacao disponivel segue por lint/typecheck/build.
- Validacao backend local: `python manage.py check` e `python manage.py makemigrations --check --dry-run` passaram com `SECRET_KEY` e `DEBUG=True` temporarios apenas para o comando.

## Atualizacao - Checkpoint backend apos tela FCF Next.js

- Executados `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` pelo `venv` local.
- O backend passou com 421 testes e sem migrations novas.
- A validacao cobre o bloco recente de leitura FCF no Next.js sem alterar runtime Django.
- Nao houve endpoint Django novo, migration, mutation de divida, baixa, ledger, canonical-first ou mudanca na regra FCF de `emprestimo`/`financiamento`.

## Atualizacao - Documentacao backend da tela FCF Next.js atual

- `INTEGRACAO_NEXT_DJANGO.md` foi alinhado ao estado atual da rota `/fcf`.
- Registrado que a tela e somente leitura e exibe KPIs, dividas, parcelas, credores agrupados, movimentacoes e exportacao CSV.
- Registrados os filtros `creditorId`, `type`/`tipo`, `sourceType` e o uso preferencial de `filterOptions.installmentStatuses`.
- Reforcado que cadastro, edicao e pagamento de dividas continuam fora do Next.js nesta etapa.

## Atualizacao - Documentacao backend dos refinamentos FCF read-only

- Registrado que `/fcf` pode exibir contadores de movimentacoes automaticas/manuais vindos de `statistics`.
- Registrado que parcelas FCF podem exibir `overdueDays`, sem recalcular status ou disponibilidade no frontend.
- Registrado que linhas FCF podem exibir contrato/evento usando apenas campos publicados pela API.
- Nao houve codigo Django runtime, endpoint, migration, mutation de divida, baixa, ledger, canonical-first ou mudanca na regra FCF de `emprestimo`/`financiamento`.

## Atualizacao - Periodo rapido Next.js na API FCF

- `utils_periodos.py` passou a concentrar o mapeamento de periodos frontend.
- `views_dashboard.py` reutiliza o helper compartilhado, preservando o contrato atual.
- `GET /api/fcf/` aceita `period` do Next.js e converte para `periodo_rapido` ou `startDate`/`endDate` antes dos selectors.
- O frontend FCF passou a enviar `period` no service.
- Adicionado teste de API para `period=previous-month`.
- Preservada a regressao existente de `periodo_rapido=vencidos` com intervalo manual.
- Validacao: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, testes focados e `python manage.py test` completo passaram com 422 testes.

## Atualizacao - Periodo rapido Next.js na API FCI

- `GET /api/fci/` agora aceita `period` do Next.js usando os mesmos helpers compartilhados de periodo ja aplicados ao dashboard e FCF.
- `current-month` e convertido para `periodo_rapido=mes_atual`; `previous-month`, `quarter`, `semester` e `year` viram intervalo `startDate`/`endDate` antes dos selectors.
- Datas manuais continuam prevalecendo sobre `period`, preservando a regressao de `periodo_rapido=vencidos` com intervalo informado.
- Nao houve mutation, baixa, ledger, canonical-first, regra de caixa, FCF ou dividas.
- Validacao focada: `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_investimentos_filtra_por_periodo_frontend`, `python manage.py test caixa.tests.FiltrosHtmlTests.test_fci_periodo_vencidos_respeita_intervalo_informado` e `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_investimentos_filtra_por_aliases_start_end_date` passaram.

## Atualizacao - Periodo rapido Next.js na API do Mes Financeiro

- `GET /api/mes-financeiro/` agora aceita `period`, `startDate` e `endDate`.
- O endpoint preserva `mes`, `periodo_rapido`, `data_inicial` e `data_final` para compatibilidade com a tela Django e links legados.
- O payload `filters` passa a ecoar `period`, `startDate` e `endDate` junto dos campos legados.
- Nao houve alteracao em calculos financeiros, caixa, baixa, ledger, canonical-first, FCF ou dividas; a mudanca fica limitada a normalizacao de filtros antes dos selectors.
- Validacao focada: `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_filtra_por_periodo_frontend`, `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_retorna_contrato_json_para_frontend` e `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_mes_financeiro_separa_caixa_final_de_caixa_acumulado` passaram.

## Atualizacao - Periodo rapido Next.js na API de Lancamentos Financeiros

- `GET /api/lancamentos-financeiros/` agora aceita `period` do Next.js.
- Como o ledger trabalha diretamente com datas de lancamento, o backend converte `period` para `startDate`/`endDate` antes de filtrar `LancamentoFinanceiro`.
- Datas manuais continuam prevalecendo sobre `period`, e o payload `filters` ecoa `period`, `startDate`, `endDate`, `data_inicial` e `data_final`.
- O tipo `FinancialLedgerQueryParams` do frontend passou a declarar `period`, alinhando o tipo ao envio real ja feito por `toLedgerQuery()`.
- Nao houve alteracao em criacao/sincronizacao de lancamentos, baixa, conciliacao, canonical-first, FCF ou regra de dividas.
- Validacao focada: `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_filtra_por_periodo_frontend` e `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_lancamentos_financeiros_retorna_payload_para_next` passaram.
- Validacao frontend: `npx --yes pnpm@10.33.4 run typecheck` passou.

## Atualizacao - Periodo rapido Next.js na API de Obrigacoes Financeiras

- `GET /api/obrigacoes-financeiras/` agora aceita `period` do Next.js.
- Quando datas manuais nao forem enviadas, o backend converte `period` para `startDate`/`endDate` antes dos selectors de obrigacoes.
- O payload `filters` passa a ecoar `period`, preservando `startDate`, `endDate`, `data_inicial` e `data_final`.
- Nao houve alteracao em liquidacao, baixa, canonical-first, ledger, FCF, caixa ou regra de dividas.
- Validacao focada: `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_filtra_por_periodo_frontend` e `python manage.py test caixa.tests.FiltrosHtmlTests.test_api_obrigacoes_financeiras_unifica_fontes_por_contrato` passaram.

## Atualizacao - Checkpoint amplo apos alinhamento de periodos financeiros

- Executados `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test`.
- A suite completa passou com 426 testes e sem migrations novas.
- O checkpoint cobre o alinhamento de `period` em FCI, FCF, Mes Financeiro, Ledger e Obrigacoes.
- Nao houve alteracao em liquidacao, baixa, canonical-first, criacao de lancamentos, FCF ou regra de dividas.

## Atualizacao - Periodo rapido Next.js na API de Baixas Canonicas

- `GET /api/canonical-settlements/` e `/api/baixas-financeiras-canonicas/` agora aceitam `period` do Next.js.
- Quando datas manuais nao forem enviadas, o backend converte `period` para `startDate`/`endDate` antes de filtrar `BaixaFinanceira.data_baixa`.
- O payload `filters` passa a ecoar `period`, preservando `startDate`, `endDate`, `data_inicial` e `data_final`.
- A mudanca fecha a simetria de filtros read-only entre Mes Financeiro, Ledger, Obrigacoes e Baixas Canonicas.
- Nao houve alteracao em liquidacao, baixa, canonical-first, criacao de lancamentos, FCF, caixa ou regra de dividas.
- Validacao backend: testes focados da API de baixas canonicas, `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 427 testes.

## Atualizacao - Frontend envia period direto em Obrigacoes

- A documentacao backend foi alinhada ao estado atual do service Next.js de obrigacoes financeiras.
- `GET /api/obrigacoes-financeiras/` continua aceitando `period`, `startDate` e `endDate`, mas o frontend agora envia `period` diretamente quando o filtro rapido esta ativo.
- A conversao de `period` para janela de vencimento fica no Django, evitando regra de calendario duplicada no Next.js.
- Nao houve codigo runtime backend, migration, endpoint novo, liquidacao, baixa, canonical-first, ledger, FCF, caixa ou regra de dividas.
- Validacao de referencia: frontend `typecheck`, `lint` e `build` passaram apos a mudanca do service; backend completo ja passou com 427 testes apos aceitar `period` em baixas canonicas.

## Atualizacao - Checkpoint amplo apos period direto

- Executados novamente `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test`.
- A suite completa do backend passou com 427 testes e sem migrations novas.
- No frontend, `npx --yes pnpm@10.33.4 run typecheck`, `lint` e `build` passaram.
- O checkpoint cobre o estado staged atual do contrato `period` em FCI, FCF, Mes Financeiro, Ledger, Obrigacoes e Baixas Canonicas.
- Nao houve codigo novo nesta etapa, migration, endpoint novo, liquidacao, baixa, canonical-first, ledger write, FCF, caixa ou regra de dividas.

## Atualizacao - Filtro FCF por cliente

- `GET /api/fcf/` passou a aceitar `clientId`, `cliente_id` e `cliente` como filtro de cliente.
- Parcelas e movimentacoes FCF agora respeitam o cliente por contrato, evento ou dimensao operacional ligada a divida.
- `filterOptions` do payload FCF passou a publicar `clients` e o alias `clientes` para a rota Next.js `/fcf`.
- O frontend envia `clientId` pelo service de FCF e usa as opcoes vindas do backend no filtro global de cliente.
- A mudanca e somente leitura: nao houve cadastro, edicao, baixa, ledger write, canonical-first ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de API FCF por cliente, regressao de dimensao operacional FCI/FCF, periodo FCF e entrada FCF automatica de divida especial passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 428 testes.

## Atualizacao - Dimensao operacional herdada da divida FCF

- Movimentacoes FCF que tenham `divida_financeira` mas nao tenham contrato/evento duplicado diretamente agora herdam contrato, evento e cliente da divida ao serializar o payload.
- O selector de movimentacoes FCF passou a carregar tambem o cliente do contrato herdado pelo evento da divida.
- O teste de filtro FCF por cliente foi ajustado para cobrir movimentacoes vinculadas somente pela divida.
- A mudanca e somente leitura e preserva a regra de entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: API FCF por cliente e regressao de entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 428 testes.

## Atualizacao - clientId FCF com filtro estrito por id

- `clientId`, `cliente_id` e `cliente` em `GET /api/fcf/` passaram a ser tratados como filtros estritos por id de cliente.
- Valores nao numericos retornam listas vazias para dividas, parcelas e movimentacoes, sem busca textual e sem erro 500.
- A regra acompanha a postura ja adotada para `creditorId`: aliases canonicos de id nao caem para texto legado.
- Nao houve migration, endpoint novo, baixa, ledger write, canonical-first ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: API FCF com cliente invalido, API FCF por cliente valido e regressao de entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 429 testes.

## Atualizacao - IDs operacionais FCF estritos

- `contractId`, `contrato_operacional_id`, `contrato_operacional`, `eventId`, `evento_id` e `evento` em `GET /api/fcf/` passaram a ser tratados como filtros estritos por id.
- Valores nao numericos retornam recorte vazio para dividas, parcelas e movimentacoes, sem erro 500.
- `GET /api/fcf/` tambem passou a aceitar explicitamente os aliases `contrato_operacional_id` e `evento_id`.
- O filtro de movimentacoes FCF por evento agora cobre tambem movimentacoes ligadas pela `divida_financeira` de origem.
- Nao houve migration, baixa, ledger write, canonical-first ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: IDs operacionais invalidos, cliente invalido, cliente valido, dimensao operacional FCI/FCF e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 430 testes.

## Atualizacao - IDs operacionais FCI estritos

- `contractId`, `contrato_operacional_id`, `contrato_operacional`, `eventId`, `evento_id` e `evento` em `GET /api/fci/` passaram a ser tratados como filtros estritos por id.
- Valores nao numericos retornam recorte vazio para investimentos, sem erro 500.
- `GET /api/fci/` passou a aceitar explicitamente os aliases `contrato_operacional_id` e `evento_id`.
- A mudanca alinha FCI ao contrato ja aplicado em FCF, mantendo filtros operacionais como IDs.
- Nao houve migration, baixa, ledger write, canonical-first ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: IDs operacionais FCI invalidos, periodo FCI, dimensao operacional FCI/FCF e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 431 testes.

## Atualizacao - Aliases operacionais do Mes Financeiro

- `GET /api/mes-financeiro/` passou a aceitar `eventId`, `costCenterId`, `evento_id`, `clientId`, `cliente_id` e `contrato_operacional_id`, alem dos nomes ja existentes.
- `resolver_filtros_mes_financeiro()` normaliza os aliases de evento, cliente e contrato para os mesmos IDs no payload `filters`/`filtros`.
- A mudanca alinha o Mes Financeiro aos nomes usados pelo Next.js sem duplicar regra financeira no frontend.
- Nao houve migration, baixa, ledger write, canonical-first, regra de caixa, FCF ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: aliases operacionais do Mes Financeiro, filtro por contrato, periodo frontend, IDs FCI/FCF invalidos e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 432 testes.

## Atualizacao - costCenterId no ledger financeiro

- `GET /api/lancamentos-financeiros/` passou a aceitar `costCenterId` como alias legado de evento, alem de `eventId`, `evento_id` e `evento`.
- O payload `filters` do ledger ecoa `costCenterId` com o mesmo ID normalizado de `eventId`.
- A mudanca fecha compatibilidade de leitura com o filtro global do Next.js sem alterar lancamentos, totais, baixa, canonical-first ou FCF.
- Validacao: filtro do ledger por `costCenterId`, contrato JSON do ledger e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 433 testes.

## Atualizacao - costCenterId em obrigacoes financeiras

- `GET /api/obrigacoes-financeiras/` passou a aceitar `costCenterId` como alias legado de evento, alem de `eventId`, `evento_id` e `evento`.
- O payload `filters` de obrigacoes ecoa `costCenterId` com o mesmo ID normalizado de `eventId`.
- A mudanca e somente leitura e preserva liquidacao, canonical-first, ledger write, caixa e regra FCF.
- Validacao: aliases de dimensoes operacionais de obrigacoes, periodo frontend de obrigacoes e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 433 testes.

## Atualizacao - costCenterId em baixas canonicas

- `GET /api/canonical-settlements/` e `/api/baixas-financeiras-canonicas/` passaram a aceitar `costCenterId` como alias legado de evento.
- O payload `filters` de baixas canonicas ecoa `costCenterId` com o mesmo ID normalizado de `eventId`.
- A mudanca e somente leitura e preserva liquidacao, canonical-first, ledger write, caixa e regra FCF.
- Validacao: filtro de baixas canonicas por `costCenterId`, payload de auditoria de baixas e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 434 testes.

## Atualizacao - costCenterId em FCI e FCF

- `GET /api/fci/` e `GET /api/fcf/` passaram a aceitar `costCenterId` como alias legado de evento, alem de `eventId`, `evento_id` e `evento`.
- Os payloads `filters` de FCI e FCF ecoam `costCenterId` com o mesmo valor normalizado de `eventId`.
- Valores nao numericos em `costCenterId` retornam recorte vazio, acompanhando os demais aliases operacionais estritos.
- A mudanca e somente leitura e preserva caixa, baixa, canonical-first, ledger write e entrada FCF automatica.
- Validacao: IDs operacionais invalidos em FCI/FCF, dimensao operacional FCI/FCF e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 434 testes.

## Atualizacao - costCenterId no metadata de nomenclatura

- `meta.nomenclature.legacyAliases` passou a listar `costCenterId` como alias temporario de `eventId`.
- `meta.nomenclature.legacyAliasUsage` registra as superficies onde o alias ainda e aceito: Dashboard, Mes Financeiro, FCI, FCF, Obrigacoes, Ledger, Baixas Canonicas e filtros antigos do Next.js.
- A mudanca fecha a paridade entre contrato publicado, endpoints ja validados e mock offline do frontend.
- Nao houve migration, baixa, mutation, canonical-first, ledger write, caixa ou alteracao na entrada FCF automatica.
- Validacao: contrato de nomenclatura do dashboard e entrada FCF automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 434 testes.

## Atualizacao - Status FCF preservado no Next.js

- A normalizacao de filtros do frontend passou a permitir opt-in de status por endpoint.
- A rota `/fcf` preserva os status publicados por `filterOptions.installmentStatuses`, incluindo valores especificos de `ParcelaDivida` que nao pertencem ao conjunto generico do dashboard.
- O backend continua sendo a fonte da verdade para choices de parcela FCF; nao houve alteracao em models, selectors, migrations, baixa, ledger, canonical-first, caixa ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: frontend `lint`, `typecheck` e `build` passaram; regressao backend de entrada FCF automatica de `emprestimo` passou.

## Atualizacao - sourceType FCF invalido descartado

- `GET /api/fcf/` agora aceita como origem de movimentacao somente `manual` ou `divida_automatica`.
- Valores invalidos em `sourceType` deixam `sourceType`, `movementSourceType`, `origem_movimentacao` e `automaticFromDebt` vazios no payload de filtros, evitando filtro ativo sem efeito.
- A mudanca e somente leitura e preserva a entrada FCF/caixa automatica de dividas `emprestimo` e `financiamento`.
- Validacao: testes focados de origem FCF e regressao de entrada automatica de `emprestimo` passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 435 testes.

## Atualizacao - sourceType inicial da rota FCF no Next.js

- A rota Next.js `/fcf` passou a aceitar na query inicial somente `sourceType=manual` ou `sourceType=divida_automatica`.
- Valores invalidos de origem abrem a tela como "Todas", acompanhando a normalizacao backend.
- Nao houve backend runtime adicional, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `lint`, `typecheck` e `build` passaram; `python manage.py makemigrations --check --dry-run` passou.

## Atualizacao - tipo FCF invalido descartado

- `GET /api/fcf/` agora preserva `tipo` somente quando o valor pertence aos tipos de divida publicados pelo backend.
- Valores invalidos em `tipo` sao ecoados como vazio no payload `filters`, evitando filtro ativo sem efeito.
- A rota Next.js `/fcf` tambem normaliza `type`/`tipo` inicial e abre valores invalidos como "Todos".
- A mudanca e somente leitura e preserva a entrada FCF/caixa automatica de dividas `emprestimo` e `financiamento`.
- Validacao: testes focados de `tipo` invalido, `sourceType` invalido e regressao de entrada automatica de `emprestimo` passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 436 testes; frontend `lint`, `typecheck` e `build` passaram.

## Atualizacao - creditorId FCF normalizado no Next.js

- A rota Next.js `/fcf` passou a aceitar na query inicial somente `creditorId`/`credor_id` como inteiro positivo.
- O service FCF tambem normaliza `creditorId` e `credor_id` antes de chamar `GET /api/fcf/`.
- O alias textual `credor` segue separado como compatibilidade backend; o caminho canonico do Next.js nao cai para busca textual quando o ID e invalido.
- Nao houve backend runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `lint`, `typecheck` e `build` passaram.

## Atualizacao - status FCF invalido descartado

- `GET /api/fcf/` agora preserva `status` somente quando o valor pertence as choices de parcelas FCF ou movimentacoes FCF.
- Valores invalidos em `status` sao ecoados como vazio no payload `filters`, evitando filtro ativo sem efeito.
- A rota Next.js `/fcf` limpa status local invalido usando `filterOptions.installmentStatuses` e `filterOptions.financingStatuses` recebidos da API.
- A mudanca e somente leitura e preserva a entrada FCF/caixa automatica de dividas `emprestimo` e `financiamento`.
- Validacao: testes focados de `status`, `tipo`, `sourceType` e entrada automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 437 testes; frontend `lint`, `typecheck` e `build` passaram.

## Atualizacao - bateria de servidor FCF ampliada

- `DEPLOY_ORACLE.md` passou a incluir os testes focados que descartam `sourceType`, `tipo` e `status` invalidos em `GET /api/fcf/`.
- O texto da bateria agora explicita que valores invalidos devem ser descartados sem sumir com os dados do recorte.
- Nao houve codigo runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: `git diff --check` passou para a documentacao alterada.

## Atualizacao - query key FCF com creditorId normalizado

- `useFinancialFinancing()` passou a normalizar `creditorId` e `credor_id` antes de montar `financingQueryOptions`.
- A query key e a request de `GET /api/fcf/` passam a usar o mesmo ID canonico, evitando cache/refetch separado para valor que o service descartaria.
- Nao houve backend runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `lint`, `typecheck` e `build` passaram.

## Atualizacao - filtros locais FCF seguem resposta normalizada

- A rota Next.js `/fcf` passou a limpar `type`/`tipo` local quando a resposta de `/api/fcf/` vier com `filters.tipo` vazio.
- A rota Next.js `/fcf` tambem limpa `sourceType` local quando a resposta vier com origem de movimentacao vazia.
- A mudanca mantem o backend como autoridade final do contrato de filtro e evita select ativo sem recorte real.
- Nao houve backend runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `lint`, `typecheck` e `build` passaram.

## Atualizacao - normalizadores FCF centralizados no Next.js

- Criado `features/financial-dashboard/utils/financial-financing-filters.ts` para centralizar normalizacao de `creditorId`, `type`/`tipo` e `sourceType`.
- Tela, hook e service FCF passaram a usar os mesmos helpers, alinhando UI, query key e request.
- Nao houve backend runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `lint`, `typecheck` e `build` passaram apos limpar artefato local `.next/types` que travou a primeira limpeza do build.

## Atualizacao - alias type aceito na API FCF

- `GET /api/fcf/` passou a aceitar `type` como alias de `tipo` para filtro de tipo de divida.
- O payload `filters` agora ecoa tambem `type` com o mesmo valor normalizado de `tipo`.
- Valores invalidos continuam sendo descartados para vazio e a entrada FCF/caixa automatica de `emprestimo` e `financiamento` foi preservada.
- Validacao: teste focado de alias `type`, filtros invalidos e regressao de entrada automatica passaram; `python manage.py check`, `python manage.py makemigrations --check --dry-run` e `python manage.py test` completo passaram com 438 testes.

## Atualizacao - Next.js deixa tipo FCF ser validado pelo backend

- O normalizador frontend de `type`/`tipo` deixou de duplicar a lista de tipos de divida.
- O Next.js agora preserva candidatos nao vazios e deixa `/api/fcf/` validar contra `DividaFinanceira.TIPO_CHOICES`.
- A tela continua limpando o filtro local quando a resposta vier com `filters.tipo`/`filters.type` vazios.
- Nao houve backend runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `lint`, `typecheck` e `build` passaram.

## Atualizacao - espelhamento filters/filtros FCF protegido em teste

- O teste principal de contrato JSON de `GET /api/fcf/` passou a garantir que `filters` e `filtros` saem iguais no payload.
- A protecao evita divergencia entre o nome canonico consumido pelo Next.js e o alias legado mantido para transicao.
- Nao houve mudanca runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: teste focado de contrato FCF e regressao de entrada automatica de `emprestimo` passaram com `.\\venv\\Scripts\\python.exe manage.py test`.

## Atualizacao - bateria de servidor cobre contrato FCF principal

- `DEPLOY_ORACLE.md` passou a incluir `test_api_financiamentos_retorna_contrato_json_para_frontend` na bateria focada de FCI/FCF.
- O texto do roteiro agora explicita que essa bateria protege tambem o espelhamento `filters`/`filtros`.
- Nao houve codigo runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: `git diff --check` passou para a documentacao alterada.

## Checkpoint - suite backend apos contratos FCF

- Apos tipagem/normalizacao frontend, protecao de `filters`/`filtros` e atualizacao da bateria de servidor, a suite completa do backend foi executada localmente.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 438 testes.
- `manage.py makemigrations --check --dry-run` tambem confirmou que nao ha migrations pendentes.
- Observacao: a primeira tentativa com `python manage.py test` usou o Python global do Windows e falhou por falta do Django; a validacao correta deve usar o Python do `venv` local ou o `python` do venv ativado no servidor.

## Atualizacao - texto do Mes Financeiro corrigido

- Corrigido o label visivel `Caixa final do mês` no template `mes_financeiro.html`, que podia aparecer como texto mojibake.
- O teste da pagina do Mes Financeiro passou a validar a presenca desse texto correto.
- Nao houve regra financeira, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: `.\\venv\\Scripts\\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_mes_financeiro_exibe_receitas_e_dividas_do_mes_atual` (OK).

## Atualizacao - alias type vazio protegido em FCF invalido

- O teste de `GET /api/fcf/` com tipo de divida invalido passou a validar que `filters.type` tambem fica vazio, alem de `filters.tipo`.
- A protecao acompanha o contrato do Next.js, que agora consome `type` como alias canonico de UI e sincroniza `type`/`tipo` no service.
- Nao houve mudanca runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: `$env:SECRET_KEY='local-validation-secret'; $env:DEBUG='True'; .\\venv\\Scripts\\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_financiamentos_descarta_tipo_invalido caixa.tests.LancamentoFinanceiroDominioTests.test_divida_emprestimo_gera_entrada_fcf_no_caixa_e_mes_financeiro` (OK); `manage.py check` (OK); `manage.py makemigrations --check --dry-run` (OK, no changes detected).

## Atualizacao - aliases operacionais FCF protegidos em teste

- Os testes de `GET /api/fcf/` passaram a validar aliases operacionais em `filters`: contrato por `contractId`/`contrato_operacional_id`/`contrato_operacional` e cliente por `clientId`/`cliente_id`/`cliente`.
- A protecao acompanha o adapter do Next.js, que normaliza esses aliases para consumo por exportacoes e futuras telas.
- Nao houve mudanca runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: `$env:SECRET_KEY='local-validation-secret'; $env:DEBUG='True'; .\\venv\\Scripts\\python.exe manage.py test caixa.tests.FiltrosHtmlTests.test_api_fci_e_fcf_filtram_e_expoem_dimensao_operacional caixa.tests.FiltrosHtmlTests.test_api_financiamentos_filtra_por_cliente_frontend caixa.tests.LancamentoFinanceiroDominioTests.test_divida_emprestimo_gera_entrada_fcf_no_caixa_e_mes_financeiro` (OK); `manage.py check` (OK); `manage.py makemigrations --check --dry-run` (OK, no changes detected).

## Atualizacao - bateria de servidor cobre aliases operacionais FCF

- `DEPLOY_ORACLE.md` passou a incluir os testes de dimensao operacional FCI/FCF e filtro FCF por cliente na bateria focada.
- O texto da bateria passou a citar `contractId`, `eventId` e `clientId` junto dos filtros canonicos de FCF.
- Nao houve codigo runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: `git diff --check` (OK).

## Checkpoint - suite backend apos normalizacoes FCF do Next.js

- Apos as fases de normalizacao frontend de filtros FCF, foi executada uma validacao ampla do backend para confirmar que o bloco staged continua consistente.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 438 testes.
- `manage.py check` passou sem issues.
- `manage.py makemigrations --check --dry-run` confirmou que nao ha migrations pendentes.
- Nao houve codigo runtime novo, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.

## Atualizacao - resposta FCF normaliza automaticFromDebt para sourceType

- O adapter do Next.js passou a derivar `filters.sourceType` a partir de `automaticFromDebt` quando a resposta FCF vier apenas com esse alias legado.
- `filters.automaticFromDebt` tambem fica espelhado a partir de `sourceType`, mantendo `filters`/`filtros`, componentes e exportacoes no mesmo contrato.
- A mudanca e apenas no boundary frontend de leitura e nao altera endpoint Django, migration, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: frontend `typecheck`, `lint` e `build` passaram; regressao backend focada de filtros FCF por `sourceType` e entrada FCF automatica de divida passou com 4 testes.

## Atualizacao - automaticFromDebt=true protegido na API FCF

- O teste de `GET /api/fcf/` passou a cobrir explicitamente `automaticFromDebt=true` como alias de `sourceType=divida_automatica`.
- A protecao complementa o caso `automaticFromDebt=false`, mantendo links/action hints legados coerentes com o contrato preferencial `sourceType`.
- Nao houve mudanca runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: teste focado de filtro FCF por origem e regressao de entrada FCF automatica de `emprestimo` passaram com `.\\venv\\Scripts\\python.exe manage.py test`.

## Atualizacao - prioridade textual de origem FCF no Next.js

- O frontend passou a usar `automaticFromDebt` como fallback apenas quando nenhum alias textual de origem FCF vier preenchido.
- Origem textual invalida em `sourceType`, `movementSourceType` ou `origem_movimentacao` passa a limpar o filtro, alinhando o Next.js ao comportamento da API.
- A mudanca fica no normalizer compartilhado do frontend e nao altera endpoint Django, migration, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - origem FCF invalida prevalece sobre automaticFromDebt

- O teste de `GET /api/fcf/` com `sourceType` invalido agora tambem envia `automaticFromDebt=true`.
- A regressao confirma que a API limpa `sourceType`/aliases e nao usa o booleano quando uma origem textual invalida veio preenchida.
- Nao houve mudanca runtime, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: teste focado de origem FCF invalida, filtro por origem e regressao de entrada FCF automatica de `emprestimo` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite backend apos prioridade de origem FCF

- Apos alinhar `automaticFromDebt` como fallback apenas quando nao houver origem textual e proteger a API contra `sourceType` invalido com booleano positivo, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 438 testes.
- `DEPLOY_ORACLE.md` tambem passou a explicar que a bateria FCI/FCF cobre `automaticFromDebt=true/false` e a prioridade da origem textual invalida.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - query inicial FCF preserva aliases textuais de origem

- A rota Next.js `/fcf` passou a enviar `sourceType`, `movementSourceType` e `origem_movimentacao` separadamente ao normalizer compartilhado.
- Isso preserva alias textual valido depois de valor vazio/whitespace e mantem origem textual invalida como bloqueio correto para `automaticFromDebt`.
- A mudanca e apenas no frontend e nao altera endpoint Django, migration, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - query inicial FCF preserva aliases de credor e tipo

- A rota Next.js `/fcf` passou a enviar `creditorId`/`credor_id` e `type`/`tipo` separadamente aos normalizers compartilhados.
- Isso impede que alias preferencial vazio ou com espacos oculte alias legado valido em links antigos.
- A mudanca e apenas no frontend e nao altera endpoint Django, migration, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - type prevalece sobre tipo na API FCF

- `valor_filtro_tipo_divida()` passou a ler `type` antes de `tipo`, alinhando o backend ao contrato canonico consumido pelo Next.js.
- O teste de alias `type` agora envia tambem `tipo=fornecedor` e confirma que `type=emprestimo` prevalece.
- Nao houve migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: teste focado de alias `type`, tipo invalido e regressao de entrada FCF automatica de `emprestimo` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite backend apos precedencia canonica de type

- Apos alinhar `type` antes de `tipo` no selector FCF, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 438 testes.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - origem FCF invalida bloqueia aliases posteriores

- O normalizer FCF do Next.js passou a respeitar a ordem dos aliases textuais de origem.
- Valor vazio/espacos permite avaliar o proximo alias, mas valor invalido preenchido limpa a origem e nao cai em alias posterior nem em `automaticFromDebt`.
- O teste backend de origem invalida agora tambem envia `movementSourceType=manual`, confirmando a mesma prioridade na API.
- Nao houve migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram; teste backend focado de origem FCF invalida, filtro por origem e regressao de entrada FCF automatica passou; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - adapter FCF espelha contratos e eventos legados

- O adapter FCF do Next.js passou a fazer fallback de `contracts` para `contratos` e de `events` para `eventos`.
- O backend atual ja publica nomes canonicos e aliases, mas a leitura fica protegida para payloads legados ou parciais.
- Nao houve migration, endpoint novo, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram; regressao backend de entrada FCF automatica de `emprestimo` passou; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - cobertura dos aliases operacionais FCF

- O teste de dimensoes operacionais FCF agora confirma que `contracts`/`contratos`, `events`/`eventos` e `clients`/`clientes` permanecem espelhados no payload.
- A mudanca protege o contrato consumido pelo adapter Next.js sem alterar runtime, migrations, caixa, ledger ou canonical-first.
- Validacao: teste focado de dimensoes FCI/FCF e regressao de entrada FCF automatica de `emprestimo` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - CSV FCF usa labels operacionais

- A exportacao CSV da tela FCF no Next.js passou a resolver contrato, evento e cliente do filtro pelas opcoes normalizadas do payload.
- Quando a opcao nao existir, o fallback continua sendo `#id`, preservando compatibilidade.
- Nao houve migration, endpoint novo, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram.

## Checkpoint - suite backend apos bloco FCF operacional

- Apos os ajustes de adapter FCF, aliases operacionais e CSV por labels, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 438 testes.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - navegacao FCF para pagamento Django

- O frontend extraiu helpers de URL backend/frontend para `navigation-urls.ts`.
- A tabela de parcelas FCF do Next.js passou a exibir link `Pagar` somente quando `availableForPayment=true` e a URL backend esta configurada.
- O link aponta para `/fcf/parcelas/<id>/pagar/`, mantendo pagamento/baixa no Django.
- Nao houve API de pagamento no Next.js, mutation, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram; regressao backend de entrada FCF automatica de `emprestimo` passou; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - actionHints nas parcelas FCF

- `/api/fcf/` passou a publicar `actionHints.primary` em parcelas FCF pagaveis, apontando para a tela Django de pagamento.
- Parcelas nao pagaveis retornam `primary=null` e lista de acoes vazia.
- O Next.js passou a preferir esse hint para montar o link `Pagar`, mantendo a rota direta como fallback.
- Nao houve API de pagamento no Next.js, mutation, migration, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram; testes focados de contrato FCF, parcela nao pagavel e regressao de entrada FCF automatica passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite backend apos actionHints FCF

- Apos publicar `actionHints` nas parcelas FCF e ajustar o Next.js para consumir o hint, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 438 testes.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - label do pagamento FCF vem do action hint

- A tela FCF do Next.js passou a usar `actionHints.primary.label` como texto do botao de pagamento.
- `Pagar` permanece como fallback quando a API nao publicar hint.
- Nao houve backend, API de pagamento no Next.js, mutation, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - actionHints FCF seguem contrato completo

- `installments[].actionHints` em `/api/fcf/` passou a publicar tambem `admin=null`, mantendo a mesma forma `{ primary, admin, actions }` usada nas obrigacoes financeiras.
- Parcelas pagaveis continuam com `primary` apontando para a tela Django de pagamento; parcelas nao pagaveis continuam com `primary=null` e `actions=[]`.
- A mudanca e apenas de contrato JSON e nao altera API de pagamento no Next.js, mutation, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica.
- Validacao: testes focados de contrato FCF, parcela nao pagavel e regressao de entrada FCF automatica de `emprestimo` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - actionHints FCF respeitam permissao de pagamento

- `/api/fcf/` agora publica `actionHints.primary` de pagamento somente quando a parcela esta disponivel e o usuario possui `caixa.add_pagamentoparceladivida`.
- Quando a parcela esta disponivel mas o usuario nao pode pagar, `availableForPayment` permanece verdadeiro como estado financeiro e `actionHints.primary` fica `null` como decisao de navegacao/autorizacao.
- O Next.js usa fallback direto para `/fcf/parcelas/<id>/pagar/` apenas quando `actionHints` estiver ausente, preservando compatibilidade com backend antigo sem ignorar uma negativa explicita do backend atual.
- Nao houve API de pagamento no Next.js, mutation de baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: testes focados de contrato FCF com permissao, contrato FCF sem permissao, parcela nao pagavel e regressao de entrada FCF automatica de `emprestimo` passaram; frontend `typecheck`, `lint` e `build` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite backend apos permissao dos actionHints FCF

- Apos proteger `actionHints.primary` de parcelas FCF por permissao de pagamento, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 439 testes.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - sessao publica permissao de pagamento FCF

- `GET /api/auth/session/` e o retorno de login passaram a publicar `canPayFinancialDebtInstallment`.
- O payload de usuario tambem inclui `permissions.canViewDashboard` e `permissions.canPayFinancialDebtInstallment`, mantendo os booleans de topo por compatibilidade.
- A permissao de sessao prepara futuras telas/controles gerais; a acao por parcela continua sendo decidida por `installments[].actionHints.primary` em `/api/fcf/`.
- Nao houve API de pagamento no Next.js, mutation de baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: testes focados de login/sessao, FCF sem permissao e regressao de entrada FCF automatica de `emprestimo` passaram; frontend `typecheck`, `lint` e `build` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - actionHints de obrigacoes respeitam permissao de pagamento

- `/api/obrigacoes-financeiras/` e `/api/payment-obligations/` passaram a publicar action hints `legacyPayment` somente quando o usuario possui a permissao de pagamento da origem.
- Isso cobre `custo_servico`, `custo_extra` e `parcela_divida`, mantendo `legacyList` e `adminChange` fora dessa regra.
- A tela de obrigacoes no Next.js usa fallback local de pagamento/listagem apenas quando `actionHints` estiver ausente em payload legado; se `primary=null`, nao reconstrui link.
- Nao houve mutation de baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: testes focados de obrigacoes com permissao, obrigacoes FCF sem permissao, FCF sem permissao e regressao de entrada FCF automatica de `emprestimo` passaram; frontend `typecheck`, `lint` e `build` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite backend apos permissao dos actionHints de obrigacoes

- Apos aplicar permissao aos action hints `legacyPayment` de obrigacoes financeiras, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 440 testes.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - adminChange de obrigacoes respeita permissao da origem

- `/api/obrigacoes-financeiras/` e `/api/payment-obligations/` passaram a publicar `actionHints.admin` somente quando o usuario possui `view_*` ou `change_*` do model de origem.
- A tela de obrigacoes no Next.js usa fallback local de admin apenas quando `actionHints` estiver ausente em payload legado; se `admin=null`, nao reconstrui URL.
- A mudanca alinha `adminChange` com a mesma politica de action hints autorizados usada em `legacyPayment`.
- Nao houve mutation de baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: testes focados de obrigacoes com permissao, obrigacoes FCF sem permissao, contas a receber canonicas e regressao de entrada FCF automatica de `emprestimo` passaram; frontend `typecheck`, `lint` e `build` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite backend apos adminChange autorizado

- Apos proteger `adminChange` de obrigacoes por permissao de origem, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 440 testes.
- Nao houve migration pendente, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - actionHints preservados apos baixa de obrigacao

- A resposta da mutation `/api/obrigacoes-financeiras/liquidar/` agora serializa o item atualizado com o mesmo contexto de permissao usado na listagem de obrigacoes.
- Isso evita que `legacyPayment` ou `adminChange` desaparecam ou aparecam fora da politica autorizada logo apos uma baixa.
- A regressao de parcela FCF passou a conferir `actionHints.primary` de pagamento e `actionHints.admin` no item devolvido depois da liquidacao parcial.
- Nao houve migration, nova escrita canonica, API de pagamento no Next.js, caixa ou alteracao na entrada FCF automatica.
- Validacao: baixa FCF focada e regressao de entrada FCF automatica de `emprestimo` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Checkpoint - suite ampla apos actionHints pos-baixa

- Apos propagar permissoes de action hints para o item retornado pela mutation de baixa, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 440 testes.
- O frontend tambem passou em `typecheck`, `lint` e `build`.
- Nao houve migration pendente, ledger write novo, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - pagamento de obrigacao exige saldo pendente no actionHint

- `legacyPayment` em obrigacoes financeiras agora exige permissao de pagamento e saldo pendente maior que zero.
- Itens liquidados ou cancelados retornam `actionHints.primary=null`, mesmo quando o usuario ainda possui permissao de adicionar pagamento na origem.
- A regressao FCF cobre baixa parcial com link de pagamento e baixa quitada sem link de pagamento, preservando `adminChange` quando autorizado.
- Nao houve migration, nova escrita canonica, API de pagamento no Next.js, caixa ou alteracao na entrada FCF automatica.
- Validacao: testes focados de baixa FCF parcial/quitada, obrigacoes com/sem permissao e regressao de entrada FCF automatica de `emprestimo` passaram; `manage.py check` e `makemigrations --check --dry-run` passaram.

## Atualizacao - fallback frontend de pagamento respeita saldo

- O fallback local da tela de obrigacoes do Next.js, usado apenas para payload legado sem `actionHints`, agora tambem exige saldo pendente e status diferente de `liquidado`/`cancelado`.
- A regra vale para `custo_servico`, `custo_extra` e `parcela_divida`; links de listagem e admin continuam independentes.
- Nao houve backend runtime, migration, nova escrita canonica, API de pagamento no Next.js, caixa ou alteracao na entrada FCF automatica.
- Validacao: frontend `typecheck` e `lint` passaram.

## Checkpoint - suite ampla apos saldo em actionHints e fallback

- Apos exigir saldo pendente para `legacyPayment` no backend e no fallback legado do frontend, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 440 testes.
- O frontend passou em `typecheck`, `lint` e `build`.
- Nao houve migration pendente, ledger write novo, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - baixa nativa informa capacidade autorizada

- `meta.settlementCapabilities.sources[*]` passou a publicar `canSettle` e `canUseNativeSettlement` conforme a permissao do usuario autenticado para cada origem.
- A tela de obrigacoes do Next.js passou a respeitar essa capacidade antes de exibir o formulario de baixa nativa.
- O contrato nao expõe o codename da permissao e nao altera a validacao do endpoint de baixa, que continua sendo a barreira real de escrita.
- Nao houve migration, ledger write novo, canonical-first, caixa ou alteracao na entrada FCF automatica.
- Validacao: testes focados de obrigacoes com/sem permissao, regressao de entrada FCF automatica de `emprestimo`, `manage.py check`, `makemigrations --check --dry-run`, frontend `typecheck` e `lint` passaram.

## Checkpoint - suite ampla apos capacidade autorizada

- Apos publicar `canSettle`/`canUseNativeSettlement` e consumir a capacidade no Next.js, a suite completa do backend foi executada.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test` passou com 440 testes.
- O frontend passou em `build`.
- Nao houve migration pendente, ledger write novo, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - indicadores tecnicos do FCO no Mes Financeiro

- O Mes Financeiro passou a exibir Custo Variavel, Margem de Contribuicao, Margem de Contribuicao (%) e Lucro Operacional / EBIT como cards adicionais.
- Os cards existentes foram preservados sem renomeacao ou remocao.
- O backend calcula Custo Variavel apenas com `DespesaOperacional` FCO do periodo; `CustoFixo` fica separado; FCI/FCF nao entram nesses indicadores.
- A margem percentual retorna `0.00` quando a receita prevista e zero, evitando divisao por zero.
- A API publica aliases camelCase: `variableCostAmount`, `contributionMarginAmount`, `contributionMarginPercent` e `operatingProfitEbitAmount`, alem dos aliases `planned*`.
- Nao houve migration, mudanca de regra de caixa/competencia, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados do Mes Financeiro passaram; suite completa backend passou com 442 testes; `check` e `makemigrations --check --dry-run` passaram; frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - indicadores tecnicos do FCO no Dashboard principal

- `/api/dashboard/financial-overview/` passou a publicar KPIs adicionais `custoVariavel`, `margemContribuicao`, `margemContribuicaoPercentual` e `lucroOperacionalEbit`.
- Os KPIs antigos foram mantidos sem renomeacao: `receitaTotal`, `despesasTotais`, `lucroLiquido`, `margemLiquida` e `resultadoFinanceiro`.
- O calculo usa `DespesaOperacional` como Custo Variavel, separa `CustoFixo`, preserva FCI/FCF fora da Margem/EBIT e usa margem percentual zero quando a receita e zero.
- O frontend adiciona uma segunda linha de cards e exporta esses indicadores no CSV, sem remover a linha antiga de KPIs.
- Nao houve migration, mudanca de regra de caixa/competencia, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do dashboard passou; suite completa backend passou com 442 testes; `check` e `makemigrations --check --dry-run` passaram; frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - indicadores tecnicos no Dashboard HTML do Django

- O dashboard HTML legado do Django passou a exibir Custo Variavel, Margem de Contribuicao, Margem de Contribuicao (%) e Lucro Operacional / EBIT.
- Os cards antigos do resumo foram preservados sem remocao ou renomeacao.
- O contexto do dashboard agora inclui esses quatro campos a partir dos totais financeiros ja calculados no backend.
- A regra segue o mesmo criterio do Mes Financeiro e do dashboard Next: `DespesaOperacional` como Custo Variavel, `CustoFixo` separado e FCI/FCF fora da Margem/EBIT.
- Nao houve migration, mudanca de regra de caixa/competencia, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do dashboard HTML passou; suite completa backend passou com 442 testes; `check` e `makemigrations --check --dry-run` passaram; frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - indicadores tecnicos no widget de Indicadores Financeiros

- `financialIndicators` do dashboard passou a incluir `Margem de Contribuicao` e `Lucro Operacional / EBIT`.
- Os indicadores antigos, como `Margem` e `Liquidez`, foram mantidos sem renomeacao ou remocao.
- O valor da Margem de Contribuicao usa o percentual ja calculado no backend; o EBIT usa valor monetario formatado em BRL.
- O mock do frontend e a documentacao de contrato foram atualizados para refletir esses indicadores.
- Nao houve migration, mudanca de regra de caixa/competencia, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do contrato do dashboard e `typecheck` do frontend passaram.

## Revisao - metas financeiras apos indicadores tecnicos do FCO

- `financialGoals` foi revisado e permanece sem nova meta de Margem de Contribuicao nesta etapa.
- A meta existente de `Margem liquida` tem alvo proprio de 25% e nao deve ser reaproveitada automaticamente para Margem de Contribuicao.
- Os novos valores tecnicos ja estao disponiveis como KPIs e indicadores; uma meta futura deve nascer com alvo de negocio definido.
- Nao houve alteracao runtime, migration, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: revisao de contrato em `caixa/serializers_dashboard.py` e nas referencias frontend de `financialGoals`; `manage.py check`, frontend `typecheck` e `git diff --check` passaram.

## Checkpoint - suite ampla apos revisao de metas financeiras

- Apos registrar a decisao de manter `financialGoals` sem nova meta tecnica, foi executada validacao ampla.
- Resultado backend: `.\\venv\\Scripts\\python.exe manage.py test` passou com 442 testes.
- Resultado frontend: `npx --yes pnpm@10.33.4 run lint` e `npx --yes pnpm@10.33.4 run build` passaram.
- Nao houve migration, nova meta, regra financeira, canonical-first, ledger write, FCI, FCF ou alteracao em `emprestimo`/`financiamento`.

## Atualizacao - variacoes reais nos KPIs do dashboard

- `/api/dashboard/financial-overview/` passou a calcular variacao contra o periodo anterior disponivel, preservando filtros aplicados.
- Cards com ausencia de base anterior agora recebem `changePercent=null` e devem exibir `—`, nao `+0,0%`.
- Indicadores monetarios usam variacao percentual com divisor `abs(anterior)`; Margem Liquida e Margem de Contribuicao (%) usam pontos percentuais.
- `serviceRevenue[].variation` e `summary.serviceRevenueTotalVariation` passaram a seguir a mesma regra.
- Nao houve mudanca nos valores-base dos KPIs, migration, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de variacao sem anterior, gap de historico e contrato do dashboard passaram; suite completa backend passou com 444 testes; `check` e `makemigrations --check --dry-run` passaram; frontend `typecheck`, `lint` e `build` passaram.

## Ajuste - mocks e metadados de variacao nula

- A descricao canonica de `changePercent` agora registra que a variacao pode ser nula quando nao houver base historica real.
- O mock do Next.js usa `changePercent=null` nos KPIs tecnicos sem historico mockado.
- O normalizador do frontend forca `sem comparação` quando a variacao e nula, mesmo se um payload legado trouxer descricao antiga.
- Nao houve mudanca de calculo financeiro, migration, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do contrato do dashboard e frontend `typecheck` passaram.

## Regressao - variacao com periodo anterior zerado

- Adicionado teste para garantir que um periodo anterior existente com valor zero gera `changePercent=null`, nunca `0.0` nem divisao por zero.
- A regressao cobre Receita Total, Margem Liquida, Margem de Contribuicao (%), receitas por servico e total de receitas por servico.
- Nao houve mudanca de calculo financeiro, frontend, migration, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de variacao sem anterior, com gap historico e com anterior zero passaram; suite completa backend passou com 445 testes; frontend `typecheck`, `lint` e `build` passaram.

## Regressao - contrato de unidade p.p. nos KPIs

- O teste de variacao do dashboard agora confirma `unit="p.p."` em Margem Liquida e Margem de Contribuicao (%).
- Isso protege a exibicao correta do Next.js, que usa essa unidade para renderizar pontos percentuais.
- Nao houve mudanca de calculo financeiro, serializer runtime, migration, canonical-first, ledger write, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado de variacao com mes anterior disponivel passou.

## Atualizacao - sessao API com permissoes por area financeira

- `/api/auth/login/` e `/api/auth/session/` agora publicam tambem `canViewFinancialMonth`, `canViewFinancialDebtInstallments`, `canViewFinancialCreditors`, `canViewFinancialInvestments`, `canViewFinancialLedger` e `canViewFinancialObligations`.
- `canViewFinancialMonth` reflete o contrato atual de Mes Financeiro: `caixa.view_parceladivida` e `caixa.view_receitaoperacional`.
- `canViewFinancialDebtInstallments` reflete `caixa.view_parceladivida`, usado pela tela FCF.
- `canViewFinancialCreditors` reflete `caixa.view_credor`, preparando o consumo futuro do cadastro mestre de credores.
- `canViewFinancialInvestments` reflete `caixa.view_investimento`, usado pela area FCI.
- `canViewFinancialLedger` reflete `caixa.view_lancamentofinanceiro`, usado pelo ledger de lancamentos financeiros.
- `canViewFinancialObligations` reflete `caixa.view_lancamentofinanceiro`, usado por Obrigacoes financeiras e contratos canonicos relacionados.
- `canPayFinancialDebtInstallment` continua separado, porque permissao de consultar FCF nao e a mesma coisa que permissao de pagar parcela.
- Nao houve migration, regra financeira, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; suite completa Django passou com 445 testes; `manage.py check` passou; `makemigrations --check --dry-run` passou; frontend `typecheck`, `lint` e `build` passaram.

## Atualizacao - constantes compartilhadas de permissoes financeiras

- As permissoes usadas por Dashboard, Mes Financeiro, FCI, FCF, ledger, Obrigacoes e pagamento FCF foram centralizadas em `caixa/permissions.py`.
- `views_api_auth.py` e as views financeiras passaram a consumir essas constantes, mantendo os mesmos codenames e decorators ja existentes.
- A mudanca reduz risco de divergencia entre a permissao exposta em `/api/auth/session/` e a permissao exigida pelos endpoints.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; suite completa Django passou com 445 testes; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Regressao - sessao diferencia FCF de Mes Financeiro

- Adicionado teste para garantir que `canViewFinancialMonth` so fica verdadeiro quando o usuario possui `view_parceladivida` e `view_receitaoperacional`.
- O mesmo teste confirma que `view_parceladivida` sozinho continua liberando a capacidade geral de leitura FCF (`canViewFinancialDebtInstallments`), mas nao o Mes Financeiro.
- Isso protege o contrato do Next.js para reaproveitar sessao ativa sem confundir permissoes compostas de tela.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos contrato de permissoes por area

- Apos ampliar o contrato de sessao, centralizar constantes de permissoes e adicionar regressao de permissao composta do Mes Financeiro, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 446 testes.
- `git diff --check` e `git diff --cached --check` passaram.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou alteracao na entrada FCF automatica de `emprestimo`/`financiamento`.

## Ajuste documental - ordem das fases recentes no plano vivo

- `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md` foi reorganizado para manter as fases recentes 879 a 893 em ordem cronologica.
- A mudanca e apenas documental e preserva o conteudo registrado nas fases.
- Nao houve alteracao runtime, migration, teste, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: `git diff --check` e `git diff --cached --check` passaram.

## Regressao - sessao diferencia FCI de ledger e Obrigacoes

- Adicionado teste para garantir que `view_lancamentofinanceiro` libera `canViewFinancialLedger` e `canViewFinancialObligations`, mas nao libera `canViewFinancialInvestments`.
- O mesmo teste confirma que `view_investimento` libera `canViewFinancialInvestments` separadamente.
- Isso preserva o contrato de sessao por area sem duplicar codenames no frontend.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos regressoes de sessao por area

- Apos adicionar a regressao que diferencia FCI de ledger/Obrigacoes, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 447 testes.
- `git diff --check` e `git diff --cached --check` passaram nos dois projetos.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - respostas de sessao e logout nao cacheaveis

- Adicionado teste para garantir que `GET /api/auth/session/` retorna `Cache-Control` com `no-store` sem sessao e com sessao autenticada.
- O mesmo teste cobre `POST /api/auth/logout/`, preservando a regra de respostas de auth nao cacheaveis.
- Isso evita que o frontend leia estado de sessao antigo em transicoes de login/logout.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos cache-control de auth

- Apos adicionar a regressao de cache-control em sessao/logout, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 448 testes.
- `git diff --check` e `git diff --cached --check` passaram nos dois projetos.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - login tambem nao e cacheavel

- Os testes de login valido e credenciais invalidas agora confirmam `Cache-Control` com `no-store`.
- A cobertura complementa a regressao de sessao/logout e protege todo o fluxo `/api/auth/*` usado pelo Next.js.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos cache-control de login

- Apos adicionar assertivas de `no-store` para login valido e invalido, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 448 testes.
- `git diff --check` e `git diff --cached --check` passaram nos dois projetos.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - JSON invalido de login nao e cacheavel

- O teste de content-type do login agora tambem cobre JSON invalido com `Content-Type: application/json`.
- A resposta `400 {"detail": "JSON invalido."}` passa a ter assertiva explicita de `Cache-Control: no-store`.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado de auth passou; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Ajuste - respostas 401 e 403 das APIs financeiras nao cacheaveis

- Os helpers `api_authentication_required_response()` e `api_permission_denied_response()` passaram a aplicar os cabecalhos de `add_never_cache_headers()`.
- Isso garante `Cache-Control: no-store` tambem nos JSON `401` e `403` gerados por `require_api_permission`.
- A regressao do Mes Financeiro confirma o comportamento para usuario nao autenticado e usuario autenticado sem permissao.
- A escolha foi centralizar no helper comum para proteger Dashboard, Mes Financeiro, FCI, FCF, ledger, Obrigacoes e APIs canonicas sem repetir cabecalho nas views.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de permissoes passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos 401 e 403 no-store

- Apos centralizar `Cache-Control: no-store` nos helpers de `401` e `403` das APIs financeiras, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 448 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - no-store em 401 e 403 por area financeira

- Testes existentes de Dashboard, FCI, FCF, credores FCF, ledger, Obrigacoes e APIs canonicas passaram a validar `Cache-Control: no-store` nos retornos `401` e `403`.
- A cobertura confirma que o helper comum protege as areas financeiras alem do Mes Financeiro.
- Nao houve nova alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de permissoes passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Ajuste - respostas 200 das APIs protegidas tambem nao cacheaveis

- `require_api_permission` agora aplica `add_never_cache_headers()` tambem na resposta bem-sucedida da view protegida.
- Isso alinha o backend ao `cache: "no-store"` usado pelo Next.js para dados financeiros reais e reduz risco de saldos, permissoes ou conciliacoes defasadas em caches intermediarios.
- Testes de Dashboard, FCI, FCF e credores FCF confirmam `Cache-Control: no-store` em respostas `200`.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de permissoes passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos no-store em APIs protegidas

- Apos aplicar `Cache-Control: no-store` nas respostas bem-sucedidas de APIs protegidas, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 448 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - no-store em ledger e APIs canonicas com sucesso

- Testes existentes de ledger, modelagem canonica e baixas canonicas passaram a validar `Cache-Control: no-store` em respostas `200`.
- A cobertura complementa Dashboard, FCI, FCF e credores FCF, confirmando o decorator comum em mais areas consumidas pelo Next.js.
- Nao houve nova alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de ledger/modelagem/baixas passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Regressao - no-store em Mes Financeiro e Obrigacoes com sucesso

- Testes existentes de `GET /api/mes-financeiro/` e `GET /api/obrigacoes-financeiras/` passaram a validar `Cache-Control: no-store` em respostas `200`.
- A cobertura fecha as principais telas financeiras consumidas pelo Next.js no contrato de respostas protegidas nao cacheaveis.
- Nao houve nova alteracao runtime, migration, endpoint, regra financeira, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de Mes Financeiro e Obrigacoes passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Ajuste - no-store na baixa de obrigacoes financeiras

- A API `POST /api/obrigacoes-financeiras/liquidar/` passou a usar um helper JSON comum com `Cache-Control: no-store` tambem para respostas `200` e `400`.
- As respostas `401` e `403` ja vinham pelos helpers comuns; os testes agora confirmam explicitamente o cabecalho nesses casos da baixa.
- A escolha preserva o fluxo manual da view, necessario porque a permissao final depende da origem liquidada, sem alterar a regra de liquidacao.
- Nao houve migration, endpoint novo, regra financeira, calculo, ledger write, canonical-first, caixa, FCI, FCF ou entrada automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de liquidacao passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou.

## Checkpoint - suite ampla apos no-store na baixa

- Apos aplicar `Cache-Control: no-store` nas respostas da mutation de baixa, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 449 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, calculo, baixa adicional, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Limpeza - assertiva duplicada de no-store

- Removida uma assertiva duplicada de `Cache-Control: no-store` no teste de `401` do Mes Financeiro.
- A cobertura permanece a mesma; a mudanca apenas reduz ruido no teste.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, calculo, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado de Mes Financeiro `401` passou.

## Checkpoint - regra de entrada FCF automatica preservada

- Repetida regressao focada da regra especial de dividas FCF.
- Confirmado que `emprestimo` e `financiamento` continuam usando a strategy de entrada de caixa, gerando `FinanciamentoMovimentacao`, `LancamentoFinanceiro` FCF e impacto no caixa/Mes Financeiro.
- Confirmado que `fornecedor` continua sem entrada automatica e que mudar uma divida para `fornecedor` remove a entrada FCF correspondente.
- Nao houve alteracao runtime nesta etapa, apenas validacao da regra critica apos as mudancas de auth/cache/API.
- Validacao: testes focados de `LancamentoFinanceiroDominioTests` passaram.

## Regressao - alias ingles da baixa tambem nao e cacheavel

- A rota alias `POST /api/payment-obligations/settle/` passou a ter regressao explicita para JSON invalido com `Cache-Control: no-store`.
- O teste protege consumidores futuros do alias sem duplicar a regra de liquidacao, pois a view continua sendo a mesma da rota principal.
- Nao houve alteracao runtime, migration, endpoint novo, regra financeira, calculo, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do alias de baixa passou.

## Regressao - login sem credenciais tambem nao e cacheavel

- O teste de login JSON passou a cobrir payload valido sem usuario/senha.
- A resposta `400 {"detail": "Informe usuario e senha."}` agora tambem tem assertiva explicita de `Cache-Control: no-store`.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, calculo, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado de login JSON passou.

## Atualizacao - sessao API expõe permissao de credores financeiros

- `/api/auth/login/` e `/api/auth/session/` passaram a publicar `canViewFinancialCreditors`.
- O campo reflete `caixa.view_credor` e prepara futuras telas de cadastro de dividas com select de credor cadastrado.
- A mudanca e aditiva e nao altera a permissao atual de leitura FCF (`canViewFinancialDebtInstallments`).
- Nao houve migration, endpoint novo, regra financeira, calculo, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: testes focados de auth passaram; `manage.py check` passou; `makemigrations --check --dry-run` passou; frontend `typecheck` e `lint` passaram.

## Checkpoint - suite ampla apos permissao de credores financeiros

- Apos adicionar `canViewFinancialCreditors` e complementar regressoes de auth/cache, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 450 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, calculo, baixa adicional, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - permissao de credores separada do FCF

- Adicionado teste para confirmar que `caixa.view_credor` libera `canViewFinancialCreditors` sem liberar `canViewFinancialDebtInstallments`.
- Isso preserva a separacao entre consultar credores cadastrados e consultar parcelas/dividas FCF.
- Nao houve alteracao runtime, migration, endpoint, regra financeira, calculo, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado de sessao/credores passou.

## Checkpoint - pre-flight financeiro local

- Executado `validar_preflight_deploy_financeiro` em modo somente leitura.
- O resultado consolidado veio `ready=true`, `issues=[]`, integridade de ledger consistente e validacao operacional pronta.
- As verificacoes de credores de dividas FCF e entradas FCF automaticas de dividas vieram consistentes, sem pendencias.
- O comando foi repetido com `--falhar --json` e tambem passou.
- Nao houve alteracao de dados, migration, endpoint, regra financeira, calculo, baixa, ledger write, canonical-first, caixa ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - dashboard com margem de contribuicao sem receita

- Adicionado teste para `GET /api/dashboard/financial-overview/` com custo variavel no periodo e Receita Bruta igual a zero.
- O contrato agora protege explicitamente `Margem de Contribuicao (%) = 0.0`, sem erro de divisao por zero, mantendo a Margem de Contribuicao e o Lucro Operacional / EBIT negativos quando houver custo sem receita.
- Nao houve alteracao de calculo: a fase apenas registrou a cobertura do comportamento ja esperado no backend.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do dashboard passou.

## Regressao - variacao com prejuizo menor

- Adicionado teste para o dashboard comparar dois periodos negativos, em que o prejuizo atual e menor que o prejuizo anterior.
- O contrato confirma variacao positiva em `lucroLiquido` e `resultadoFinanceiro`, preservando o divisor por `abs(anterior)`.
- A `margemLiquida` segue em pontos percentuais, com diferenca absoluta entre percentuais.
- Nao houve alteracao de calculo: a fase apenas protege a regra ja usada pelo backend.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do dashboard passou.

## Checkpoint - suite ampla apos regressoes FCO/variacoes

- Apos adicionar as regressoes de margem de contribuicao sem receita e prejuizo menor, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 453 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, calculo, baixa adicional, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - API do Mes Financeiro com margem sem receita

- Adicionado teste para `GET /api/mes-financeiro/` com custo variavel no periodo e Receita Bruta igual a zero.
- A API agora tem cobertura explicita para publicar `Margem de Contribuicao (%) = 0.00`, mantendo `Margem de Contribuicao` e `Lucro Operacional / EBIT` negativos.
- O teste cobre aliases `totais` e `totals`, preservando compatibilidade com o frontend.
- Nao houve alteracao de calculo: a fase apenas registrou a cobertura do comportamento ja esperado no backend.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado da API do Mes Financeiro passou.

## Checkpoint - suite ampla apos regressao do Mes Financeiro

- Apos adicionar a regressao de contrato de `/api/mes-financeiro/`, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 454 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, calculo, baixa adicional, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Regressao - Receitas por Servico com variacao negativa

- Adicionado teste para `GET /api/dashboard/financial-overview/` quando a receita de um servico cai em relacao ao periodo anterior.
- A API agora tem cobertura explicita para publicar `variation = -40.0` no item de `serviceRevenue` e em `summary.serviceRevenueTotalVariation`.
- Isso protege a representacao do frontend com seta vermelha/para baixo sem duplicar regra de variacao no Next.js.
- Nao houve alteracao de calculo: a fase apenas registrou a cobertura do comportamento ja esperado no backend.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do dashboard passou.

## Regressao - KPIs tecnicos com base anterior zero

- Adicionado teste para `GET /api/dashboard/financial-overview/` quando o periodo anterior existe, mas tem valores-base zerados.
- A API agora tem cobertura explicita para retornar `changePercent = None` em Receita Total, Despesas Totais, Custo Variavel, Margem de Contribuicao, Margem de Contribuicao (%), Lucro Operacional / EBIT e Resultado Financeiro.
- Isso evita que o frontend exiba `0,0%` como fallback quando a comparacao nao tem divisor valido.
- Nao houve alteracao de calculo: a fase apenas registrou a cobertura do comportamento ja esperado no backend.
- Nao houve migration, endpoint novo, regra financeira, baixa, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.
- Validacao: teste focado do dashboard passou.

## Checkpoint - suite ampla apos variacoes do dashboard

- Apos adicionar as regressoes de Receitas por Servico em queda e KPIs tecnicos com base anterior zero, a suite completa Django foi repetida.
- Resultado: `.\\venv\\Scripts\\python.exe manage.py test --verbosity 1` passou com 456 testes.
- Nao houve nova alteracao de runtime nesta etapa, apenas registro do checkpoint amplo.
- Nao houve migration, endpoint novo, regra financeira, calculo, baixa adicional, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Checkpoint - pre-flight financeiro apos variacoes

- Executado `validar_preflight_deploy_financeiro` em modo somente leitura apos a suite completa.
- O resultado consolidado veio `ready=true`, `issues=[]`, ledger consistente, validacao operacional pronta, credores FCF consistentes e entradas FCF automaticas consistentes.
- O comando foi repetido com `--falhar --json` e tambem passou.
- Nao houve alteracao de dados, migration, endpoint novo, regra financeira, calculo, baixa adicional, ledger write, canonical-first, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - guias PM-03.1 com evidencia do monitor

- `DEPLOY_ORACLE.md` e `INTEGRACAO_NEXT_DJANGO.md` agora apontam explicitamente a PM-03.1 de `custo_fixo` como proxima etapa depois da PM-02 real aprovada.
- Os guias registram o comando `monitorar_janela_canonical_first` com `--diretorio-evidencias`, `--json` e `--falhar`, alem dos arquivos `pm03-monitor-canonical-first.json` e `pm03-monitor-canonical-first.md`.
- O plano mestre tambem recebeu o registro incremental dessa amarracao para manter backend e frontend com o mesmo proximo passo operacional.
- Nao houve alteracao de baixa, allowlist, ledger, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - evidencia da auditoria de fonte PM-03

- `auditar_fonte_escrita_baixas` agora aceita `--salvar-json`, `--salvar-registro`, `--diretorio-evidencias` e `--exigir-arquivos-evidencia`.
- Com `--diretorio-evidencias`, o comando gera `pm03-auditoria-fonte-escrita.json` e `pm03-auditoria-fonte-escrita.md`, publicando `evidenceFiles` e `executionRecord.markdown`.
- `DEPLOY_ORACLE.md`, `INTEGRACAO_NEXT_DJANGO.md` e o plano mestre foram alinhados para usar essa evidencia junto do monitor PM-03.1 de `custo_fixo`.
- Validacao: teste focado de auditoria de fonte, `manage.py check`, `makemigrations --check --dry-run`, frontend `typecheck` e `lint` passaram.
- Nao houve alteracao de baixa, allowlist, ledger, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - evidencia da auditoria de totais PM-03

- `auditar_totais_negocio` agora aceita `--salvar-json`, `--salvar-registro`, `--diretorio-evidencias` e `--exigir-arquivos-evidencia`.
- Com `--diretorio-evidencias`, o comando gera `pm03-auditoria-totais-negocio.json` e `pm03-auditoria-totais-negocio.md`, publicando `evidenceFiles` e `executionRecord.markdown`.
- `DEPLOY_ORACLE.md`, `INTEGRACAO_NEXT_DJANGO.md` e o plano mestre foram alinhados para usar essa evidencia como terceiro artefato da PM-03.1 de `custo_fixo`.
- Validacao: teste focado da auditoria de totais, regressao PM-03 com monitor/fonte/totais, `manage.py check`, `makemigrations --check --dry-run`, frontend `typecheck`, `lint` e `build` passaram.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - checklist PM-03 sugere evidencias

- O checklist retornado por `validar_janela_canonical_first` agora sugere `--diretorio-evidencias`, `--json` e os comandos com artefatos para auditoria de fonte, monitor e auditoria de totais.
- Isso evita copiar comandos antigos da propria validacao de janela ao executar PM-03.1 no servidor.
- Validacao: teste focado de `validar_janela_canonical_first` com pre-flight operacional passou.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - evidencia da validacao de janela PM-03

- `validar_janela_canonical_first` agora aceita `--salvar-json`, `--salvar-registro`, `--diretorio-evidencias` e `--exigir-arquivos-evidencia`.
- Com `--diretorio-evidencias`, o comando gera JSON e markdown da validacao de janela e publica `evidenceFiles` e `executionRecord.markdown`.
- Com `--exigir-arquivos-evidencia`, a validacao reprova quando os caminhos de evidencia nao forem informados.
- O checklist automatico tambem passou a sugerir esses artefatos para `validateFeatureFlag` e `validateWindowResult`.
- Validacao: teste focado da validacao de janela cobriu `--exigir-arquivos-evidencia`; regressao PM-03 com validacao de janela, monitor, fonte e totais passou; `manage.py check`, `makemigrations --check --dry-run`, suite Django completa com 462 testes, frontend `typecheck`, `lint` e `build` passaram.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - monitor PM-03 exige evidencia quando solicitado

- `monitorar_janela_canonical_first` agora tambem aceita `--exigir-arquivos-evidencia`.
- Quando essa flag e usada, o monitor reprova se `--diretorio-evidencias`, `--salvar-json` ou `--salvar-registro` nao preencherem os caminhos de JSON/markdown.
- O checklist de `validar_janela_canonical_first` e os guias foram alinhados para sugerir essa trava no monitor de janela.
- Validacao: testes focados de monitoramento e checklist de janela passaram.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - auditoria de fonte PM-03 exige evidencia quando solicitado

- `auditar_fonte_escrita_baixas` agora tambem aceita `--exigir-arquivos-evidencia`.
- Quando essa flag e usada, a auditoria reprova se `--diretorio-evidencias`, `--salvar-json` ou `--salvar-registro` nao preencherem os caminhos de JSON/markdown.
- O checklist de `validar_janela_canonical_first` e os guias foram alinhados para sugerir essa trava na auditoria de fonte de escrita.
- Validacao: testes focados da auditoria de fonte e checklist de janela passaram.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - auditoria de totais PM-03 exige evidencia quando solicitado

- `auditar_totais_negocio` agora tambem aceita `--exigir-arquivos-evidencia`.
- Quando essa flag e usada, a auditoria reprova se `--diretorio-evidencias`, `--salvar-json` ou `--salvar-registro` nao preencherem os caminhos de JSON/markdown.
- O checklist de `validar_janela_canonical_first` e os guias foram alinhados para sugerir essa trava na auditoria final de totais.
- Validacao: regressao PM-03 com validacao de janela, monitor, fonte e totais passou; `manage.py check`, `makemigrations --check --dry-run`, suite Django completa com 462 testes, frontend `typecheck`, `lint` e `build` passaram.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - fechamento documental PM-03

- Criado `validar_fechamento_pm03` para ler os JSONs de validacao, monitor, auditoria de fonte e auditoria de totais de uma janela PM-03.
- O checklist de `validar_janela_canonical_first` agora sugere esse fechamento como ultimo passo pos-janela.
- Com `--diretorio-evidencias`, ele espera os quatro artefatos gerados pelos comandos anteriores e salva `pm03-fechamento-canonical-first.json` e `pm03-fechamento-canonical-first.md`; com `--data-ativacao`, tambem confere se as evidencias pertencem ao mesmo recorte.
- `DEPLOY_ORACLE.md`, `INTEGRACAO_NEXT_DJANGO.md` e o plano mestre passaram a listar esse comando como conferencia final antes de marcar a origem como concluida.
- Validacao: teste focado de fechamento PM-03 e checklist PM-03 passaram; `manage.py check`, `makemigrations --check --dry-run`, suite Django completa com 463 testes, frontend `typecheck`, `lint` e `build` passaram.
- Nao houve alteracao de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.1 custo_fixo concluida em producao

- PM-03.1 de `custo_fixo` foi fechada em producao RHRemoto na janela iniciada em 2026-05-26.
- Evidencias salvas em `~/evidencias_pm03_custo_fixo`.
- Monitoramento retornou `ready=True`, com 1 baixa `canonicalFirst` de 81.90 e 0 baixas `legacyAdapterSynced`.
- Auditoria de fonte retornou `canonicalFirst.count=1`, valor 81.90, `legacyAdapterSynced.count=0` e issues=nenhuma.
- Auditoria de totais retornou divergencias=0, diferenca=0.00 e valores editaveis consistentes.
- `validar_fechamento_pm03` retornou `ready=True`, com checks `windowValidation`, `monitor`, `sourceAudit` e `totalsAudit` OK.
- Decisao: `custo_fixo` fica aprovado para permanecer em `CANONICAL_FIRST_SETTLEMENT_SOURCES`; o proximo passo registrado ali, preparar PM-03.2 de `despesa_operacional`, foi cumprido em 2026-05-27.
- Nao houve alteracao local de baixa, allowlist, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.2 preparacao local

- Iniciada a preparacao de PM-03.2 para `despesa_operacional`, sem ativar nova origem.
- Validacoes read-only locais passaram: janela com pre-flight operacional, ativacao canonical-first e paridade canonica.
- Com `custo_fixo` ativo no ambiente, o roteiro preservou `CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional`.
- A base local nao possui pendencia elegivel de `despesa_operacional` (`canaryEligibleCount=0`), entao a etapa de servidor/homologacao continua pendente ate existir uma pendencia real/controlada para canario rollback-only.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, baixa, allowlist nova, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - candidatos de canario PM-03.2

- `validar_ativacao_canonical_first` agora retorna `pendingObligations.canaryCandidates` com ate 5 obrigacoes a pagar pendentes da origem validada.
- Cada candidato inclui `sourceId`, obrigacao, vencimento e saldo pendente para facilitar o comando de canario rollback-only no servidor/homologacao.
- O relatorio humano de `validar_ativacao_canonical_first`, `validar_janela_canonical_first` e `monitorar_janela_canonical_first` tambem lista os candidatos quando existirem.
- Os registros markdown de validacao/monitoramento PM-03 registram o resumo dos candidatos, preservando a evidencia operacional da escolha do canario.
- O checklist de pre-window gerado por `validar_janela_canonical_first` agora sugere `--source-id=<sourceId-de-canaryCandidates>` no canario rollback-only.
- `validar_ativacao_canonical_first` e `validar_janela_canonical_first` agora aceitam `--exigir-source-id-canario`, reprovando o canario controlado quando `--source-id` nao for informado.
- `validar_ativacao_canonical_first` e `validar_janela_canonical_first` agora tambem aceitam `--exigir-data-pagamento-canario`, reprovando o canario controlado quando `--payment-date` nao for informado explicitamente.
- Quando `--source-id` e informado, os validadores retornam `canary.sourceIdCheck` e reprovam ID inexistente, sem saldo pendente ou nao elegivel ao canario.
- O payload do canario passou a registrar `paymentDateRequired` e `paymentDateProvided`.
- O relatorio humano e o markdown de validacao de janela tambem mostram `Canario sourceId`, facilitando auditoria da evidencia.
- O checklist de pre-window passou a sugerir `validar_ativacao_canonical_first --source=<origem> --username=<usuario> --source-id=<sourceId-de-canaryCandidates> --payment-date=<DATA> --executar-canario --exigir-canario --exigir-source-id-canario --exigir-data-pagamento-canario --json --falhar`, validando readiness, candidato explicito, data explicita e rollback no mesmo gate.
- `validar_ativacao_canonical_first` agora aceita `--diretorio-evidencias`, `--salvar-json`, `--salvar-registro` e `--exigir-arquivos-evidencia`, gerando `pm03-validacao-ativacao-canonical-first.json` e `.md`.
- `validar_fechamento_pm03` agora aceita `--exigir-validacao-ativacao` para novas origens, validando esse artefato de pre-window sem quebrar fechamentos antigos da PM-03.1.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` tambem exige que o resultado do canario comprove `canary=True`, `rollbackOnly=True`, `writesPersisted=False`, data de pagamento igual a data explicita da validacao, origem consistente com a janela, `sourceId`, `obligationId` e `obligationKey` iguais ao candidato aprovado, `canonicalSettlement.synced=True`, `canonicalSettlement.writeModelSource=canonicalFirst`, obrigacao canonica igual ao candidato aprovado, valores canonicos iguais ao `requestedRealizedAmount` e ultima baixa canonica identificada, coerente com ledger e classificacao financeira.
- `validar_ativacao_canonical_first` tambem publica `recommendedCommands.canaryRollbackOnly`, preenchendo o `sourceId` do primeiro candidato quando existir.
- `validar_ativacao_canonical_first` agora publica `nextAction`, indicando se a etapa deve corrigir `sourceId`, executar canario, aguardar/criar pendencia controlada ou ativar a allowlist da janela.
- `validar_janela_canonical_first` tambem propaga `nextAction` para o JSON, relatorio humano e markdown de evidencia da janela.
- `monitorar_janela_canonical_first` tambem propaga `nextAction` para o JSON, relatorio humano e markdown de monitoramento.
- O fechamento PM-03 com `--exigir-validacao-ativacao` agora exige `nextAction=activateAllowlistWindow` no artefato de ativacao.
- O registro markdown do monitoramento agora usa o titulo generico `Registro PM-03 - monitoramento canonical-first`, porque PM-03.1 fica como historico de `custo_fixo`, enquanto PM-03.2 e origens futuras reutilizam o mesmo artefato.
- Campos antigos de `pendingObligations` foram preservados, mantendo compatibilidade com automacoes e evidencias PM-03.
- Validacao: testes focados de ativacao canonical-first com canario, comando recomendado, `nextAction`, entrada pendente, exigencia de `sourceId`, `sourceId` invalido, validacao de janela com `nextAction`, monitoramento com `nextAction` e fechamento PM-03 exigindo `canary=True` e `nextAction=activateAllowlistWindow` passaram; suite Django completa com 472 testes, `manage.py check`, `makemigrations --check --dry-run`, frontend `lint`, `typecheck` e `build` tambem passaram.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, baixa, allowlist nova, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - fechamento PM-03 exige marcador canary

- `validar_fechamento_pm03 --exigir-validacao-ativacao` agora reprova artefato de ativacao cujo resultado nao traga `canary=True`.
- A trava complementa as exigencias de `rollbackOnly=True`, `writesPersisted=False`, origem, `sourceId`, sincronizacao canonica e `writeModelSource=canonicalFirst`.
- Validacao: teste focado de fechamento PM-03 cobre a ausencia de `canary=True`; suite Django completa com 472 testes, `manage.py check`, `makemigrations --check --dry-run`, frontend `lint`, `typecheck` e `build` passaram.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, baixa, allowlist nova, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - paymentDate comprovado no canario PM-03

- `testar_baixa_canonical_first` agora retorna `paymentDate` no resultado rollback-only.
- `testar_baixa_canonical_first` tambem retorna `obligationId` no resultado rollback-only.
- `validar_ativacao_canonical_first` agora registra `canary.paymentDate` quando a data foi informada explicitamente.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` compara a data explicita da validacao com `canary.result.paymentDate`.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` tambem compara `obligationId` e `obligationKey` entre `sourceIdCheck` e resultado do canario.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` tambem compara `obligationId` e `obligationKey` do `canonicalSettlement`.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` passou a exigir `deltaAmount` positivo e a comparar `canonicalSettlement.realizedAmount` e `canonicalSettlement.allocatedAmount` com `requestedRealizedAmount`.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` passou a exigir `settlementCount`/`allocationCount` positivos e `latestSettlement.writeModelSource=canonicalFirst`, com data e valor da ultima baixa coerentes.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` tambem exige `latestSettlement.status=realizado` e `latestSettlement.ledgerEntryId` preenchido.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` tambem exige `latestSettlement.type=saida` e `latestSettlement.cashFlowGroup`/`latestSettlement.nature` preenchidos.
- `validar_fechamento_pm03 --exigir-validacao-ativacao` tambem exige `latestSettlement.id`, `latestSettlement.key` e `latestSettlement.settlementDate` coerente.
- Validacao: testes focados de canario, ativacao e fechamento PM-03 cobrem data, resultado, obrigacao canonica, valor canonico, ultima baixa, ledger e classificacao financeira divergentes; suite Django completa com 472 testes, `manage.py check`, `makemigrations --check --dry-run`, frontend `lint`, `typecheck` e `build` passaram.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, baixa, allowlist nova, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - item atualizado no fechamento PM-03

- `validar_fechamento_pm03 --exigir-validacao-ativacao` agora tambem confere o `canary.result.item` retornado pelo canario rollback-only.
- O item precisa existir, apontar para a mesma origem/sourceId do candidato aprovado, refletir o `requestedRealizedAmount`, trazer `ledgerRealizedAmount` equivalente e estar conciliado com o ledger.
- A trava complementa a conferencia da baixa canonica: o fechamento agora valida tanto a escrita/ledger quanto o item que a API devolveria ao Next.js apos a baixa.
- Validacao: testes focados de canario, ativacao e fechamento PM-03 passaram.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, baixa, allowlist nova, ledger write persistente, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.2A matriz read-only de origens futuras

- `verificar_prontidao_escrita_canonica` agora retorna `adapterOnlySources` e `pm04DecisionMatrix`.
- A matriz diferencia as origens diretas de PM-03 das origens que ainda exigem decisao futura PM-04: `custo_extra`, `custo_servico` e `parcela_divida`.
- Para cada origem, o payload informa fase recomendada, necessidade de decisao, suporte a canonical-first direto, `requiresSourceDetail`, ajustes, adapter legado e campo de origem da baixa canonica.
- `validar_ativacao_canonical_first` tambem publica essa matriz dentro de `writeReadiness`, para orientar automaticamente tentativas de ativar origem adapter-only pela trilha errada.
- O registro fica como apoio PM-03.2A: inventario read-only para manter a sequencia do projeto, sem abrir PM-04.
- Validacao: testes focados de prontidao de escrita canonica e rejeicao de origem sem suporte direto passaram.
- Fora do escopo: nao houve promocao de `custo_extra`, `custo_servico` ou `parcela_divida`, baixa, allowlist nova, ledger write, models, migrations, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.2 pre-window local reaplicado

- Seguindo a ordem do plano, a rodada continuou em PM-03.2 de `despesa_operacional`, sem avancar PM-04.
- Executado `sincronizar_modelagem_financeira_canonica --json` em modo dry-run: obrigacoes=109 atualizaveis, baixas=39 atualizaveis, alocacoes=39 atualizaveis, sem criacoes.
- Executado `sincronizar_modelagem_financeira_canonica --aplicar --json` no banco local: obrigacoes=109 atualizadas, baixas=39 atualizadas, alocacoes=39 atualizadas, criacoes=0.
- `verificar_paridade_modelagem_canonica --falhar` confirmou obrigacoes=109, baixas=39 e alocacoes=39 consistentes, sem ausentes, divergentes ou extras.
- `validar_operacao_obrigacoes --validar-canonico --validar-escrita-canonica --validar-valores-editaveis --falhar` confirmou contrato, conciliacao, paridade canonica, adapters transicionais e valores editaveis consistentes.
- `validar_janela_canonical_first --source=despesa_operacional --validar-preflight-operacional --falhar-com-preflight-operacional --json` retornou `ready=True`, `issues=0` e `nextAction=awaitCanaryCandidate`.
- A base local continua sem `canaryCandidates` para `despesa_operacional`; a etapa real permanece pendente ate servidor/homologacao com pendencia real/controlada e canario rollback-only.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, allowlist nova, baixa real, ledger write novo, migration, endpoint, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.2 comando sugerido preserva data explicita

- `validar_ativacao_canonical_first` passou a montar `recommendedCommands.canaryRollbackOnly` com `--payment-date=<DATA>` quando a validacao foi chamada sem `--payment-date` explicito.
- Quando o operador informa `--payment-date`, o comando sugerido continua reaproveitando a data fornecida.
- `validar_janela_canonical_first` tambem passou a montar o passo `validateActivationCanaryRollbackOnly` do checklist com `--payment-date=<DATA>` quando a data nao foi explicitada.
- A mudanca evita que a recomendacao copie automaticamente a data local do servidor em uma janela PM-03.2 que precisa ser rastreavel e explicitamente datada.
- Validacao: testes focados de preservacao de origens ativas e checklist da janela confirmaram que o comando sugerido, a saida humana e o checklist usam `<DATA>` quando a data nao foi informada e preservam a data real quando ela foi explicitada.
- Validacao ampla local: `manage.py check`, `makemigrations --check --dry-run`, suite completa backend com 472 testes, `validar_preflight_deploy_financeiro --falhar --json`, lint/typecheck/build do frontend (OK).
- Fora do escopo: nao houve ativacao de `despesa_operacional`, allowlist nova, baixa real, ledger write, migration, endpoint, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.2 canario compativel com PostgreSQL

- No servidor, o pre-window encontrou candidatos reais para `despesa_operacional` e mudou `nextAction` para `runCanaryRollbackOnly`.
- Ao executar o canario rollback-only com `sourceId=91`, o PostgreSQL reprovou `FOR UPDATE` no lado nullable de um `LEFT OUTER JOIN` usado por `DespesaOperacional.select_related(...)`.
- `services_obrigacoes.select_for_update_self()` passou a usar `select_for_update(of=("self",))` quando o banco suporta `FOR UPDATE OF`, restringindo o lock a tabela principal e preservando fallback para bancos sem esse recurso.
- As baixas nativas que usam `select_related()` com lock tambem passaram pelo helper, evitando a mesma falha em origens futuras.
- Validacao: testes focados do helper confirmaram `select_for_update_of=("self",)` quando suportado e fallback sem `OF` quando nao suportado; suite completa backend com 472 testes, `manage.py check`, `makemigrations --check --dry-run` e `validar_preflight_deploy_financeiro --falhar --json` passaram.
- Fora do escopo: nao houve ativacao de `despesa_operacional`, allowlist nova, baixa real persistida, ledger write, migration, endpoint, calculo financeiro, caixa, FCI, FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.2 despesa operacional fechada

- No servidor, o canario rollback-only de `despesa_operacional` passou com `--username=Davi --source-id=91 --payment-date=2026-05-27`, `synced=True`, `rollbackOnly=True` e `writesPersisted=False`.
- A janela foi ativada com `CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional`.
- A primeira baixa real da origem foi registrada em `canonicalFirst` no valor de 550.00; a auditoria de fonte retornou `canonicalFirst.count=1` e `legacyAdapterSynced.count=0`.
- `validar_janela_canonical_first`, `monitorar_janela_canonical_first`, `auditar_totais_negocio` e `validar_fechamento_pm03 --exigir-validacao-ativacao` passaram com evidencias em `evidencias/pm03-despesa-operacional-2026-05-27`.
- `validar_fechamento_pm03` passou a preferir `pm03-validacao-resultado-janela.json` quando o arquivo existe, mantendo fallback para `pm03-validacao-feature-flag.json`.
- PM-03.2 fica marcada como concluida; a proxima origem direta deve abrir nova subetapa PM-03.3, sem promover origens PM-04.
- Validacao local da correcao documental/fechamento: testes focados de `validar_fechamento_pm03` passaram com venv local e `SECRET_KEY` temporaria; `manage.py check` passou.

## Atualizacao - PM-03.3 investimento preparado localmente

- Seguindo a sequencia do plano, a atualizacao abriu PM-03.3 para `investimento`, sem ativar nova origem.
- `sincronizar_modelagem_financeira_canonica --json` e `--aplicar --json` passaram localmente com obrigacoes=109, baixas=39 e alocacoes=39 atualizaveis, criacoes=0.
- `verificar_paridade_modelagem_canonica --falhar` confirmou paridade consistente; `validar_operacao_obrigacoes --validar-canonico --validar-escrita-canonica --validar-valores-editaveis --falhar` confirmou ambiente pronto.
- `validar_ativacao_canonical_first --source=investimento --json` retornou `ready=True`, mas `canaryEligibleCount=0` e `nextAction=awaitCanaryCandidate`.
- Com `CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional` simulado, o validador recomendou preservar `custo_fixo,despesa_operacional,investimento` quando a janela real for aberta.
- `validar_janela_canonical_first --source=investimento --validar-preflight-operacional --falhar-com-preflight-operacional --json` retornou `ready=True`, sem pendencias e com `nextAction=awaitCanaryCandidate`.
- PM-03.3 fica aguardando investimento real/controlado pendente em servidor/homologacao para canario rollback-only com `--source-id` e `--payment-date` explicitos.
- Fora do escopo: nao houve ativacao de `investimento`, allowlist nova, baixa real, ledger write de janela, migration, endpoint, calculo financeiro, caixa, FCI/FCF ou entrada FCF automatica de `emprestimo`/`financiamento`.

## Atualizacao - PM-03.4 financiamento mapeado read-only

- Naquele momento, como PM-03.3 ainda estava bloqueada por falta de investimento pendente, PM-03.4 foi apenas mapeada em modo read-only para antecipar riscos tecnicos, sem ativacao.
- Com `CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional` simulado, `validar_ativacao_canonical_first --source=financiamento_movimentacao --json` retornou `ready=True`, `canaryEligibleCount=0` e `nextAction=awaitCanaryCandidate`.
- O ambiente recomendado preservou as origens aprovadas e sugeriu `custo_fixo,despesa_operacional,financiamento_movimentacao` para uma futura janela.
- `validar_janela_canonical_first --source=financiamento_movimentacao --validar-preflight-operacional --falhar-com-preflight-operacional --json` retornou `ready=True`, sem pendencias e com pre-flight pronto.
- Apos o fechamento de PM-03.3, PM-03.4 passa a ser o proximo gate operacional; antes dela, ainda sera necessario caso FCF real/controlado e regressao de dividas `emprestimo`/`financiamento`.
- Fora do escopo: nao houve ativacao de `financiamento_movimentacao`, allowlist nova, baixa real, ledger write de janela, migration, endpoint, calculo financeiro, caixa, FCI/FCF ou mudanca na entrada automatica de `emprestimo`/`financiamento`.

## Atualizacao - regra explicita de sequenciamento do plano

- O plano mestre recebeu uma regra formal de sequenciamento: fase/subetapa operacional so avanca quando a atual fecha.
- Dependencias futuras necessarias para a fase atual devem ser movidas por completo ou parcialmente extraidas, sem duplicar a mesma etapa em duas fases.
- Mapeamentos read-only de etapas futuras continuam permitidos como diagnostico, mas nao autorizam allowlist, baixa real, mudanca de fase ou ativacao fora de ordem.
- PM-03.2A ficou documentada como extracao parcial da futura PM-04: apenas inventario/matriz read-only foi movido; decisoes, implementacao e promocao real permanecem em PM-04.
- O ponto de retomada naquele momento ficou explicito: PM-03.3 `investimento`, aguardando investimento FCI real/controlado pendente para canario rollback-only.
- O plano tambem passou a exigir status operacional, gate de entrada, gate de saida, proxima acao permitida e acoes bloqueadas para a etapa ativa.
- PM-03.3 passou a declarar que estava bloqueada por falta de candidato real/controlado e que seu gate de saida exigia canario, allowlist, primeira baixa real, auditorias, monitoramento e fechamento PM-03 `ready=True`.
- PM-03.4 ficou marcada como preparada read-only, bloqueada para ativacao ate PM-03.3 fechar; apos o fechamento de PM-03.3, ela passa a ser o proximo gate operacional.

## Atualizacao - gate operacional estruturado nos validadores PM-03

- `validar_ativacao_canonical_first --json` agora publica `operationalGate` com subetapa atual, status, gate de entrada, gate de saida, nota de sequencia, acoes permitidas, acoes bloqueadas e evidencias exigidas.
- `validar_janela_canonical_first --json` propaga o mesmo gate para a evidencia da janela.
- `monitorar_janela_canonical_first --json` tambem propaga `operationalGate` e registra o gate no markdown de monitoramento.
- `validar_fechamento_pm03 --json` agora publica `operationalGateSummary`, consolidando gates das evidencias sem exigir o campo em arquivos antigos; se gates novos divergirem em subetapa ou origem, o fechamento reprova.
- Os markdowns de ativacao e janela passaram a registrar `Gate operacional`, facilitando auditoria quando PM-03.3 estiver bloqueada por falta de investimento FCI real/controlado.
- Para `investimento`, o gate explicita PM-03.3 como ponto atual e bloqueia PM-03.4/PM-04 ate o fechamento. Para `financiamento_movimentacao`, reforca que PM-03.4 fica read-only enquanto PM-03.3 nao fechar.
- O gate tambem publica `canaryCandidateCriteria`; em PM-03.3, o candidato precisa ser `Investimento.tipo_fluxo=saida`, nao cancelado, com obrigacao a pagar pendente, `source-id` e `payment-date` explicitos.
- `pendingObligations` tambem passou a expor `nonCanaryPendingCount` e `nonCanaryPendingItems`, mostrando pendencias que existem mas nao destravam o canario, como investimento FCI de entrada/receber.
- `nextAction.detail` passou a diferenciar ausencia total de pendencias de pendencias existentes mas nao elegiveis para canario.
- Validacao local: testes focados de ativacao/janela PM-03 passaram.

## Atualizacao - PM-03.3 investimento fechado

- No servidor, foi criado investimento FCI controlado de saida, categoria `software`, valor 1.00, `sourceId=2`, com obrigacao canonica `obrigacao=161` e vencimento `2026-05-27`.
- O canario rollback-only de `investimento` passou com `--username=Davi --source-id=2 --payment-date=2026-05-27`, `canary.executed=True`, `canary.synced=True`, `rollbackOnly=True` e `writesPersisted=False`.
- A janela foi ativada com `CANONICAL_FIRST_SETTLEMENT_SOURCES=custo_fixo,despesa_operacional,investimento`.
- A primeira baixa real de `investimento` foi registrada em `canonicalFirst`, valor 1.00, grupo `fci`, tipo `saida`; a auditoria de fonte retornou `canonicalFirst.count=1`, `allocatedAmount=1.0` e `legacyAdapterSynced.count=0`.
- `validar_janela_canonical_first`, `monitorar_janela_canonical_first`, `auditar_totais_negocio` e `validar_fechamento_pm03 --exigir-validacao-ativacao` passaram com evidencias em `evidencias/pm03-investimento-2026-05-27`.
- PM-03.3 fica marcada como concluida. A pendencia remanescente de investimento de entrada/receber nao e candidata a canario rollback-only e nao bloqueou o fechamento.
- Ponto de retomada atual: PM-03.4 `financiamento_movimentacao`, ainda dependente de caso FCF real/controlado e regressao das regras de dividas `emprestimo`/`financiamento` antes de qualquer ativacao.

## Atualizacao - gate PM-03.4 como retomada atual

- `validar_ativacao_canonical_first` foi realinhado para tratar `financiamento_movimentacao` como ponto de retomada atual apos o fechamento de PM-03.3.
- O `operationalGate` de PM-03.4 agora orienta confirmar/criar/aguardar movimentacao FCF de saida/a pagar pendente e reexecutar regressao de dividas `emprestimo`/`financiamento` antes de qualquer allowlist.
- `recommendedCommands` e `operationalGate` agora publicam `listar_candidatos_canario_pm03` como descoberta de candidato (`candidateDiscovery`/`candidateDiscoveryCommand`) e os comandos de regressao de dividas (`debtRegression`/`debtRegressionCommands`) para PM-03.4.
- O `operationalChecklist.preWindow` de PM-03.4 agora inclui descoberta de candidato, `validar_regressao_dividas_pm03`, regressao de credores/entradas FCF e pre-flight financeiro antes do canario rollback-only.
- `validar_regressao_dividas_pm03` cria `pm03-regressao-dividas-fcf.json/md`, publica `regressionDecision` com `mayContinuePm03_4`/`blockedBy`, e `validar_fechamento_pm03` exige essa evidencia quando `source=financiamento_movimentacao`, validando tambem a decisao da regressao quando o campo existir e agregando `debtRegressionSummary` no fechamento.
- `listar_candidatos_canario_pm03` cria `pm03-candidatos-canario.json/md`, aceita `--username`/`--payment-date`, registra o `canaryRollbackOnly` recomendado, publica `candidateDecision` com `mayRunCanaryRollbackOnly`/`selectedSourceId`/`blockedBy` e falha com `--falhar` quando so ha pendencias `receber`, nenhuma pendencia elegivel ou quando `--limit=0` esconder candidatos existentes.
- `pendingObligations` agora informa `canaryCandidatesLimit`, `canaryCandidatesReturnedCount`, `canaryCandidatesTruncated`, `nonCanaryPendingItemsReturnedCount` e `nonCanaryPendingItemsTruncated`, deixando claro se a evidencia listou todos os candidatos ou apenas um recorte.
- `candidateListHealth` centraliza essa leitura para ativacao, descoberta, validacao de janela e monitoramento, com `status` (`empty`, `onlyNonCanaryPending`, `ready`, `readyTruncated` ou `blockedByLimit`), `recommendedAction`, `hasSelectableCandidate`, `requiresLimitIncrease` e contadores de elegiveis/retornados. A UI e os roteiros devem preferir esse resumo para decidir entre criar candidato, usar candidato retornado ou reexecutar a descoberta com limite maior.
- `validar_fechamento_pm03` agora agrega esses resumos em `candidateListHealthSummary`, com estados encontrados por evidencia, acoes recomendadas e `requiresLimitIncrease`, sem exigir consistencia entre descoberta pre-canario e janela pos-baixa.
- Quando ha candidato elegivel mas nenhum `sourceId` retornado por limite, `nextAction=expandCanaryCandidateList`, `operationalGate.status=blockedCandidateListLimit` e `candidateDecision.status=blockedCandidateListLimit`, orientando reexecutar a descoberta com `--limit` maior antes do canario.
- `activationDecision` tambem usa `status=blockedCandidateListLimit` nesse caso, preservando `requiresControlledCandidate=False` e apontando o comando de redescoberta, para a ativacao nao parecer uma falta real de candidato.
- O fechamento PM-03 agora adiciona issue especifica quando a evidencia de ativacao chega com `activationDecision.status=blockedCandidateListLimit`, evitando diagnostico generico de allowlist nao liberada.
- O fechamento PM-03.4 tambem adiciona issue especifica quando `pm03-candidatos-canario.json` traz `candidateDecision.status=blockedCandidateListLimit`, evitando diagnostico generico de candidato nao pronto.
- Nesse mesmo caso, `candidateCreationGuidance.recommendedAction=expandCandidateList`, com `hasHiddenCandidate=True` e `requiredForNextCanary=False`, para nao sugerir criacao manual quando ja existe candidato elegivel escondido pelo limite.
- A descoberta de candidatos agora retorna `candidateCreationGuidance` com `adminPath`, `suggestedFields`, criterios, comandos `afterCreateCommands`, `requiredForNextCanary` e `recommendedAction`; isso orienta a criacao manual/controlada sem transformar a descoberta em comando de escrita. Os criterios deixam explicito que `tipo_fluxo=entrada` gera obrigacao a receber e nao vira candidato rollback-only; para canario controlado, use a tela/adminPath indicada com `tipo_fluxo=saida`.
- `validar_ativacao_canonical_first` e `validar_janela_canonical_first` tambem publicam a mesma orientacao e registram `Candidato controlado:` e `Comandos apos candidato:` no markdown de evidencia.
- `validar_ativacao_canonical_first` agora publica `activationDecision` com `mayRunCanaryRollbackOnly`, `mayActivateAllowlistWindow`, `requiresControlledCandidate` e `blockedBy`; `validar_janela_canonical_first` e `monitorar_janela_canonical_first` propagam esse resumo para a janela, e `validar_fechamento_pm03` valida a decisao quando a evidencia de ativacao trouxer o campo. Os artefatos de ativacao, janela, monitoramento, descoberta de candidatos e regressao de dividas tambem publicam `sequencePosition`, com anterior/atual/proximo da fila PM-03 direta antes mesmo do fechamento.
- O fechamento tambem publica `activationCanarySummary`, resumindo `required`, `executed`, `synced`, `sourceId`, `obligationId`, `paymentDate`, `expectedActivationDate`, `matchesActivationDate`, `rollbackOnly`, `writesPersisted`, `writeModelSource` e status da `activationDecision` sem precisar abrir `pm03-validacao-ativacao-canonical-first.json`; quando `--exigir-validacao-ativacao` e `--data-inicial/--data-ativacao` foram informados, o fechamento reprova canario com data de pagamento fora da janela de ativacao.
- `recommendedCommands.afterControlledCandidateCreate` explicita a sequencia apos criar o candidato controlado: sincronizar modelagem canonica, verificar paridade canonica, rodar pre-flight operacional, redescobrir candidato, em PM-03.4 reexecutar a regressao de dividas e entao rodar o canario rollback-only.
- O registro markdown de `monitorar_janela_canonical_first` agora escreve a decisao de allowlist com a origem monitorada, sem herdar texto fixo de `custo_fixo` em evidencias de `investimento` ou `financiamento_movimentacao`.
- `validar_janela_canonical_first` e `monitorar_janela_canonical_first` agora publicam `windowOutcome`, separando o resultado da janela do `nextAction` de ativacao; assim `awaitCanaryCandidate` nao parece bloquear uma janela que ja esta `ready=True`.
- `validar_janela_canonical_first` agora tambem publica `windowWriteAudit` sem filtro de fonte de escrita; `canonicalFirstAudit` continua filtrado para comprovar a baixa canonical-first, enquanto `windowWriteAudit` mostra se houve legado no recorte.
- `validar_fechamento_pm03` agora valida `windowOutcome` quando presente e publica `windowOutcomeSummary`, reprovando fechamento se a evidencia da janela estiver bloqueada ou se validacao/monitoramento divergirem; quando `canonicalFirstAudit`/`windowWriteAudit` existem, tambem exige baixa canonical-first, ausencia de legado no recorte completo e publica `windowWriteAuditSummary` comparando as contagens da validacao e do monitoramento. O fechamento tambem publica `sequencePosition` com anterior/atual/proximo na fila PM-03, `sequencePositionSummary` comparando a posicao declarada por ativacao/candidatos/regressao/janela/monitoramento, indicando `matchesExpected` contra a origem atual e expondo `rawPosition`/`positionValid` por evidencia para detectar e bloquear posicao malformada com issue explicita, `sequenceTransition` com `blocked`/`nextSource`/`nextPhase`, comando de validacao da proxima origem e sinal de revisao operacional, `evidenceChecklist` com artefatos obrigatorios, encontrados e ausentes por origem, `checksSummary` com total/ok/pendentes e mapa `byKey` dos checks, `missingEvidenceActions` com o proximo comando para gerar artefatos obrigatorios ausentes e `rerunClosureCommand`, `closureNextAction` consolidando a proxima acao entre gerar evidencia, resolver pendencia ou avancar para a proxima origem/fase com `followUpCommand` quando couber, `recommendedCommands` como alias operacional para `nextMissingEvidence`, `followUp`, `rerunClosure`, `closureNextAction` e `nextSequenceValidation` quando houver proxima origem direta, alem de `closureDecision` com status, subetapa PM-03.x, `mayMarkCurrentStepDone`, `mayAdvanceSequence`, `mayStartNextStep`, `nextStep`, `nextSource`, `nextLabel`, fim da sequencia direta e `blockedBy`; a saida humana mostra essa decisao, transicao da sequencia, proxima acao, comandos recomendados, posicao da sequencia, consistencia da sequencia nas evidencias, checklist de evidencias, resumo dos checks, acoes para evidencias faltantes, gate operacional, candidato x ativacao, resultado da janela, auditoria da janela e, quando houver bloqueios agregados, `Issues de fechamento`, sem exigir abrir o JSON.
- `sequenceTransition` tambem carrega `actionKey`, `actionLabel`, `blockingIssue`, `primaryCommand`, `followUpCommand`, `reviewChecklist` e `reviewChecklistReady`; assim a operacao/Next.js consegue exibir a transicao da etapa atual, o primeiro comando util e os pontos de revisao obrigatoria sem cruzar `closureNextAction`, `recommendedCommands` e `closureDecision`.
- `validar_ativacao_canonical_first` e `validar_janela_canonical_first` agora propagam `--username` e `--payment-date` para os comandos de descoberta de candidato quando esses valores ja foram informados, mantendo a sequencia PM-03.4 pronta para copiar/rodar sem trocar contexto.
- `validar_fechamento_pm03` tambem exige `pm03-candidatos-canario.json` em PM-03.4, validando `canaryCandidates`, `nextAction=runCanaryRollbackOnly`, gate `readyForCanaryRollbackOnly` e `candidateDecision` quando o campo existir.
- Quando as evidencias de candidatos e ativacao existem juntas, o fechamento adiciona o check `candidateActivation`, cruza o `sourceId`/`obligationId` do canario com `canaryCandidates` e reprova se o canario executado nao corresponde ao candidato descoberto.
- As acoes bloqueadas de PM-03.4 agora focam em nao iniciar PM-04 nem marcar a etapa como concluida antes de caso FCF, regressao de dividas e fechamento PM-03.
- Testes focados cobrem movimentacao FCF de entrada/receber como pendencia sem canario, lista truncada de candidatos, `--limit=0` bloqueado, `candidateListHealth`, `activationDecision` especifica para lista limitada, fechamento com issue especifica para lista limitada na ativacao e na descoberta de candidatos, confirmam `currentStep=PM-03.4`, criterio `Movimentacao FCF tipo_fluxo=saida`, nota de sequencia, bloqueio de PM-04, checklist pre-window com regressao e fechamento exigindo a evidencia de dividas.
- Validacao local: o teste direto de `validar_fechamento_pm03` cobre posicao de sequencia malformada, data do canario fora da janela, `activationCanarySummary.matchesActivationDate`, `sequenceTransition`, `primaryCommand`, `reviewChecklist`, `checksSummary`, `missingEvidenceActions`, `rerunClosureCommand`, `closureNextAction` e `recommendedCommands.nextSequenceValidation` com issue explicita; a bateria PM-03 focada passou com 17 testes, `manage.py check` passou e `makemigrations --check --dry-run` confirmou ausencia de migrations pendentes.

## Atualizacao - PM-05.1 baseline real e PM-05.2 recortes

- PM-05.1 foi registrada como concluida em 2026-05-28 no servidor/ambiente real com evidencias em `evidencias/pm05-leitura-canonica-2026-05-28`, `validar_baseline_pm05 ready=True`, 6 checks OK, `pendingCount=0` e `issues=[]`.
- Naquele momento, o ponto de retomada atual passou para PM-05.2, observacao de recortes reais. PM-05.3, as revisoes finais da PM-05 e PM-06 permaneciam bloqueadas ate PM-05.2 fechar sem divergencias abertas.
- Criado `validar_recortes_pm05`, comando read-only para validar baseline PM-05.1, leitura canonica de obrigacoes, opt-out legado explicito, equivalencia dashboard/ledger, mes financeiro versus ledger e ledger versus baixas canonicas nos recortes global, FCO, FCI e FCF.
- O comando aceita filtros de periodo, evento, cliente, contrato, centro de custo, origem, fluxo, tipo da obrigacao, natureza e status, alem de `--exigir-baseline`, `--exigir-canonico`, `--falhar-com-diferenca-baseline`, `--exigir-itens`, `--exigir-amostra-filtrada`, `--salvar-json` e `--salvar-registro`.
- O resultado global inclui `filteredSample.command`, tambem registrado no markdown, com uma sugestao de recorte filtrado baseada prioritariamente em obrigacao real e salvando `pm05-recortes-reais-filtrado.*` para nao sobrescrever o recorte global.
- A sugestao automatica nao exige `--status`; esse filtro continua disponivel para recortes manuais quando a semantica do status for apropriada para obrigacoes, ledger e baixas canonicas.
- A sugestao automatica tambem preserva `costCenterId` somente quando o item observado trouxer esse campo, evitando fabricar filtro de centro de custo a partir de outro campo.
- Em recortes por origem/fluxo/tipo/natureza/status, dashboard e mes financeiro so sao comparados quando a semantica do recorte for suportada; obrigacoes, ledger e baixas canonicas continuam obrigatorios.
- Validacao local: testes focados PM-05 passaram novamente, `manage.py check` passou, `makemigrations --check --dry-run` nao detectou migrations, `compileall` passou, `git diff --check` ficou limpo salvo avisos CRLF em markdown, o comando foi conferido via `--help`, e no frontend passaram ESLint, `next typegen`, `tsc --noEmit` e `next build`.

## Atualizacao - PM-05.2 recortes reais concluida

- PM-05.2 foi registrada como concluida em 2026-05-28 no servidor/ambiente real com evidencias em `evidencias/pm05-leitura-canonica-2026-05-28`.
- Recorte global: `pm05-recortes-reais.json`, `pm05-recortes-reais.md` e `pm05-recortes-reais.stdout.json`; resultado `ready=True`, `issues=[]`, `okCount=5`, `pendingCount=0` e `issueCount=0`.
- Recorte filtrado: `pm05-recortes-reais-filtrado.json`, `pm05-recortes-reais-filtrado.md` e `pm05-recortes-reais-filtrado.stdout.json`; filtros `source=custo_fixo`, `cashFlowGroup=fco`, `obligationType=pagar`, `nature=despesa_operacional`; resultado `ready=True`, `issues=[]`, `okCount=5`, `pendingCount=0` e `issueCount=0`.
- Naquele momento, o ponto de retomada atual passou para PM-05.3, decisao de corte para PM-06. PM-05 pai continuava aberta e PM-06 permanecia bloqueada ate PM-05.3 e revisoes finais da PM-05 fecharem.
- Fora do escopo nesta atualizacao: baixa, allowlist nova, migration, deploy, ledger write novo, remocao de fallback legado, troca de `realizedAmountBasis`, politica `financeiro-v3`, revisao final da PM-05 ou liberacao de PM-06.

## Atualizacao - PM-05.3 e revisao final PM-05

- PM-05.3 foi concluida em 2026-05-28 como decisao documental apos PM-05.1 baseline real e PM-05.2 recortes reais fecharem com `ready=True`, `issues=[]` e `pendingCount=0`.
- Decisao `realizedAmountBasis`: manter `originState` como padrao operacional e preservar `ledger` como opt-in de auditoria/comparacao.
- Decisao fallback legado: `dataSource=canonical` fica como fonte primaria; `dataSource=legacy` fica apenas como opt-out explicito de auditoria/rollback. Fallback silencioso bloqueia consolidacao fisica.
- Revisao final PM-05 concluida: revisao semantica, revisao tecnica e revisao extra foram feitas depois da fila PM-05.1/PM-05.2/PM-05.3, sem divergencias abertas.
- Naquele momento, o ponto de retomada atual passou para PM-06, somente checklist de entrada. Remocao fisica, migration de limpeza, congelamento, deploy estrutural e politica `financeiro-v3` continuavam bloqueados ate backup/tag/rollback e compatibilidade serem confirmados na propria PM-06.
- Fora do escopo nesta atualizacao: baixa, allowlist nova, migration, deploy, ledger write novo, remocao de fallback legado, troca efetiva de `realizedAmountBasis` padrao ou corte fisico `financeiro-v3`.

## Atualizacao - PM-06 checklist de entrada iniciado

- PM-06 foi retomada apenas pelo checklist de entrada em 2026-05-28.
- Itens confirmados: leitura da regra de controle, regra de sequenciamento e legenda de status; ponto de retomada PM-06 somente apos PM-05.3; PM-05.1/PM-05.2/PM-05.3 fechadas sem divergencias abertas; PM-05.3 aprovou apenas entrada controlada no checklist PM-06/planejamento `financeiro-v3`, sem corte fisico.
- Passo seguinte naquele momento: classificar fallback legado, aliases, mocks e opt-outs antes de definir backup/tag/rollback, contrato `financeiro-v3` ou limpeza fisica.
- Guardrail: remocao fisica, migration de limpeza, congelamento, deploy estrutural, baixa nova, allowlist nova e politica `financeiro-v3` continuam bloqueados ate os gates proprios da PM-06.

## Atualizacao - PM-06.1 classificacao inicial concluida

- PM-06.1 classificou fallback legado, aliases, mocks e opt-outs sem alterar runtime.
- `dataSource=legacy` ficou classificado como opt-out explicito de auditoria/rollback; `dataSource=canonical` continua fonte primaria.
- `realizedAmountBasis=ledger` fica como opt-in de auditoria/comparacao; `originState` continua padrao operacional.
- `custo_servico`, `custo_extra` e `parcela_divida` continuam fallback operacional adapter-only controlado, sem corte fisico nesta etapa.
- Aliases `alias_temporario`/`alias_entrada`, campos fisicos pendentes e mocks/fallback Next.js ficam preservados ate contrato `financeiro-v3`, consumidores atualizados e backup/tag/rollback.
- Proximo bloqueio PM-06: definir backup, tag, rollback e scripts de conciliacao antes de contrato `financeiro-v3`, migration, congelamento ou limpeza.

## Atualizacao - PM-06.2 roteiro backup/tag/rollback preparado

- PM-06.2 ficou preparada documentalmente e ganhou o gate read-only `validar_preparacao_pm06`, mas permanece bloqueada para execucao real no servidor.
- Comando base identificado: `python manage.py backup_banco_mensal --force --manter 12`, que gera `backups/db/backup_banco_*.json` e metadados `.meta.json` com `sha256` e `tamanho_bytes`.
- Condicoes para marcar backup/tag/rollback: backup real criado e verificado com integridade de arquivo, commit/tag backend, referencia frontend, plano de rollback/conciliacao aprovado, validacoes pos-backup sem issues bloqueantes e `validar_preparacao_pm06 ready=True`.
- O validador confere refs backend/frontend, backup real com metadata, nome, `sha256`, tamanho calculado, `criado_em` e `mes_referencia`, plano de rollback, plano de conciliacao, auditoria de totais e pre-flight pos-backup; salva `pm06-validacao-backup-rollback.json/md`.
- O gate ganhou `--exigir-planos-arquivo` para validar rollback/conciliacao como arquivos locais quando a evidencia for registrada desse modo.
- O gate tambem ganhou `--exigir-arquivos-evidencia` para garantir JSON/registro markdown do proprio fechamento.
- O gate ganhou `--exigir-backend-ref-git` para validar commit/tag local do backend quando a janela exigir essa prova.
- Validacao local: teste focado do gate PM-06.2 passou cobrindo pacote aprovado, `sha256` divergente, tamanho divergente, `criado_em` invalido, `mes_referencia` invalido, planos locais exigidos, plano ausente, arquivos de evidencia ausentes, backend-ref git valido/invalido e `backup-ref` ausente; `check`, `makemigrations --check --dry-run`, `compileall` e `git diff --check` tambem passaram.
- Guardrail: nenhum backup real foi executado nesta atualizacao local; nenhuma tag foi criada; nenhum rollback, migration, congelamento, limpeza ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.2 backup/tag/rollback concluido em servidor

- PM-06.2 foi concluida em 2026-05-29 no servidor/ambiente real.
- Evidencias salvas em `evidencias/pm06-backup-rollback-2026-05-28`.
- Backup real: `backups/db/backup_banco_2026-05_20260528_210850_427136.json`, `sha256=4ea77f7283f2ad50c5942760d9a6ad04c9fdce023869ee5c0bac75494ef6dc50`, `tamanho_bytes=7256621`.
- Referencias registradas: backend `da14e9215087ef3ad4818081662c993a403d3f87`; frontend `4c421da0fae8d275052ec50646b612edd53c95e4`.
- Planos de rollback e conciliacao foram registrados como arquivos locais e validados.
- `auditar_totais_negocio` pos-backup retornou `issues=[]`, valores editaveis consistentes, obrigacoes `divergentCount=0`, ledger `count=58` e obrigacoes `count=101`.
- `validar_preflight_deploy_financeiro` pos-backup retornou `ready=True`, `issues=[]`.
- `validar_preparacao_pm06` retornou `ready=True`, `issues=[]`, 8/8 checks OK, backend git ref confirmado, rollback/conciliacao como arquivos e evidencias JSON/markdown salvas.
- Proxima acao permitida naquele momento: definir contrato `financeiro-v3`, matriz de aliases/compatibilidade e endpoints de transicao antes de qualquer migration, congelamento, limpeza ou corte fisico.
- Guardrail: nenhum restore, `loaddata`, substituicao de banco, migration, congelamento, limpeza, remocao de alias ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.3 contrato `financeiro-v3` documentado

- PM-06.3 foi concluida documentalmente/read-only em 2026-05-28.
- O plano mestre agora define `financeiro-v2` como versao corrente preservando aliases e `financeiro-v3` como primeira versao autorizada a remover aliases dos fluxos principais.
- A matriz registra fonte de verdade em `meta.nomenclature`, aliases preservados, aliases candidatos a remocao, campos fisicos pendentes, origens adapter-only, endpoints de transicao e prazo de corte sem data fixa.
- Gates antes de qualquer remocao: consumidores principais usando campos canonicos, telas Django/admin/CSV/comandos revisados, PM-05 baseline e recortes reexecutados, auditoria/pre-flight verdes, backup/rollback valido e revisoes PM-06 aprovadas.
- Proxima acao permitida: inventariar consumidores/telas e preparar migracao canonica; congelamento, migration, limpeza fisica, remocao de alias e corte `financeiro-v3` continuam bloqueados.
- Guardrail: nenhum endpoint, model, migration, dado, alias ou comportamento de runtime foi alterado.

## Atualizacao - PM-06.4 inventario inicial de consumidores/aliases

- PM-06.4 foi concluida documentalmente/read-only em 2026-05-28 por busca de aliases candidatos a `financeiro-v3`.
- Frontend: usos concentrados em `financial-dashboard-service.ts`, `lib/types/dashboard.ts`, `lib/data/mock-data.ts`, hooks de dashboard/FCF/obrigacoes, `dashboard-filters.ts`, `dashboard-export.ts`, `financial-obligations-view.tsx` e `components/dashboard/header.tsx`.
- Backend: usos concentrados em serializers de dashboard/mes financeiro/obrigacoes/ledger, selectors de filtros/obrigacoes/mes financeiro, templates Django legados e campos/modelos fisicos de saldo/contrato.
- Classificacao: migrar primeiro services/hooks/exports/components do Next.js; manter normalizadores/mocks/tipos como compatibilidade defensiva; depois revisar serializers/selectors; deixar templates/admin/campos fisicos por ultimo com plano proprio.
- Proxima acao permitida: preparar plano de migracao canonica por superficie, ainda sem remocao, congelamento, migration ou corte fisico.
- Guardrail: nenhum endpoint, template, service, serializer, selector, type, dado, migration ou comportamento de runtime foi alterado.

## Atualizacao - PM-06.5 plano de migracao canonica por superficie

- PM-06.5 foi concluida documentalmente/read-only em 2026-05-28.
- Ordem definida: Next.js services/normalizadores/tipos; hooks/filtros/header/views/exportacoes; serializers/selectors backend v2; templates Django/admin; contrato de corte `financeiro-v3`; campos fisicos e migrations pequenas.
- Validacoes minimas registradas por superficie: lint/typecheck/build no frontend; testes focados, `check`, `makemigrations --check --dry-run`, PM-05 baseline/recortes, auditoria de totais e pre-flight no backend conforme o tipo de mudanca.
- Proxima acao permitida: executar a primeira migracao canonica no Next.js, mantendo aliases como compatibilidade publicada e fallback defensivo.
- Guardrail: nenhum service, hook, component, serializer, selector, template, model, dado, migration, alias ou comportamento de runtime foi alterado.

## Atualizacao - PM-06.6 primeira migracao canonica Next.js

- PM-06.6 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: hooks de dashboard/obrigacoes/FCF e `components/dashboard/header.tsx` agora normalizam filtro de evento para `eventId`, preservando `costCenterId` apenas como alias de entrada/deprecated.
- Arquivos alterados no frontend: `use-financial-dashboard.ts`, `use-financial-obligations.ts`, `use-financial-financing.ts` e `components/dashboard/header.tsx`.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em normalizadores de dashboard, exports e componentes de obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhuma migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.7 migracao canonica do fluxo realizado

- PM-06.7 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-dashboard-service.ts` agora resolve `cashBasisRealizedFlow` uma unica vez a partir do campo canonico, com fallback para `realizedCashFlow`.
- O alias `realizedCashFlow` segue publicado no view model, mas passa a espelhar `cashBasisRealizedFlow`, reduzindo a dependencia interna do alias legado.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em exports, views e componentes de obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhuma migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.8 export de obrigacoes com tipo canonico

- PM-06.8 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `dashboard-export.ts` agora usa `getFinancialObligationTypeValue()` nos CSVs de obrigacoes e worklist, resolvendo `obligationType` primeiro e centralizando fallback para `tipoObrigacao`/`tipo_obrigacao`.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em views e componentes de obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum cabecalho CSV, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.9 worklist de obrigacoes com tipo canonico

- PM-06.9 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-obligations-view.tsx` agora usa `getFinancialObligationTypeValue()` na worklist de conciliacao e na acao de abrir grupo, resolvendo `obligationType` primeiro e centralizando fallback para `tipoObrigacao`/`tipo_obrigacao`.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em componentes de FCF e demais pontos de obrigacoes, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.10 filtro de origem FCF canonico

- PM-06.10 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-financing-filters.ts` agora resolve origem FCF pelo primeiro `sourceType` valido, preservando `movementSourceType`, `origem_movimentacao` e `automaticFromDebt` apenas como fallback transicional.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF/obrigacoes, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.11 labels FCF com resolvedores canonicos

- PM-06.11 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-financing-filters.ts` ganhou helpers de label para credor, credor da divida e origem FCF; `financial-financing-view.tsx` e `dashboard-export.ts` passaram a usar esses resolvedores canônicos primeiro.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.12 listas FCF normalizadas como canonicas

- PM-06.12 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialFinancingResponse()` agora faz `dividas`, `parcelas`, `movimentacoes_financiamento` e `grupos_credor` espelharem `debts`, `installments`, `financingMovements` e `creditorGroups` no view model normalizado.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.13 totais e estatisticas FCF canonicos

- PM-06.13 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-dashboard-service.ts` agora normaliza `totals`/`statistics` por campos canonicos primeiro e faz `totais`/`estatisticas` espelharem esses envelopes no view model normalizado.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.14 opcoes FCF canonicas

- PM-06.14 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialFinancingFilterOptions()` agora faz aliases de opcoes FCF espelharem as opcoes canonicas normalizadas; `credores` preserva fallback legado quando nao ha lista canonica de credores.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.15 fluxos FCF canonicos

- PM-06.15 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-dashboard-service.ts` agora normaliza `projectedFinancingFlow` e `realizedFinancingFlow` por `inflowAmount`, `outflowAmount` e `financialResultAmount`, espelhando aliases de fluxo e usando totais FCF normalizados como fallback.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.16 tipo de obrigacao em filtros canonicos

- PM-06.16 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-obligations-amounts.ts` ganhou `getOptionalFinancialObligationTypeValue()`; filtros ativos e contexto CSV de obrigacoes agora resolvem `obligationType` canônico primeiro sem assumir `pagar` quando o filtro esta vazio.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.17 fonte de leitura de obrigacoes canonica

- PM-06.17 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financial-obligations-read-model.ts` agora centraliza fontes `canonical`/`legacy` e resolve `readModelSource` primeiro, com fallback para `dataSource`; CSV de obrigacoes usa o mesmo helper.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.18 filtros de obrigacoes canonicos

- PM-06.18 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsResponse()` agora normaliza `dataSource`/`fonteDados` e `obligationType`/`tipoObrigacao`/`tipo_obrigacao` em `filters`, mantendo aliases espelhados.
- Validacoes frontend: `git diff --check` sem erro, `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.19 filtros operacionais de obrigacoes canonicos

- PM-06.19 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsFilters()` agora espelha `source`/`origin`/`origem`, `cashFlowGroup`/`fluxo`, `settlementStatus`/`status`/`situacao`, `reconciliationStatus`/`statusConciliacao` e `reconciliationDiagnosis`/`diagnosticoConciliacao`.
- Validacoes frontend/docs: `git diff --check` sem erro, apenas avisos CRLF conhecidos; `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.20 filtros dimensionais/textuais de obrigacoes canonicos

- PM-06.20 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsFilters()` agora espelha datas, contrato, evento, cliente, labels, natureza, base/excedente de realizado e busca textual.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.30 CSV FCF com filtros canonicos

- PM-06.30 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financialFinancingFilterContext()` passou a consumir `contractId`, `eventId`, `clientId`, `type`, `status` e `sourceType` canonicos ja normalizados, sem reler aliases legados para montar o contexto do CSV FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.33 conciliacao de obrigacoes normalizada

- PM-06.33 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsResponse()` passou a normalizar metadados de conciliacao em itens e worklist, espelhando campos canonicos e aliases de diagnostico, label, orientacao, tipo de obrigacao e origem.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em consumidores visuais/export de conciliacao, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.34 consumidores de conciliacao canonicos

- PM-06.34 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: tela de obrigacoes e CSVs de obrigacoes/worklist passaram a consumir `reconciliationDiagnosisLabel`, `reconciliationGuidance` e `guidance` canonicos em itens e worklist ja normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.259 id visual do filtro acima do previsto canonico

- PM-06.259 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `FinancialObligationsView` troca o id visual `obligation-over-realized` por `obligation-realized-above-planned`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.260 valor planejado canonico em conta a pagar derivada

- PM-06.260 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `obligationToAccountPayable()` consolida `plannedAmount` antes de espelhar `value` na conta a pagar derivada de obrigacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.261 overrides vazios no hook de obrigacoes

- PM-06.261 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `useFinancialObligations()` passa a escolher o primeiro override textual nao vazio antes de montar a query normalizada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.262 credor textual FCF nao vazio

- PM-06.262 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `useFinancialFinancing()` e `toFinancingQuery()` passam a escolher o primeiro credor textual nao vazio entre `creditor` e `credor`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.263 IDs operacionais FCF nao vazios

- PM-06.263 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `toFinancingQuery()` escolhe o primeiro valor nao vazio para contrato, evento e cliente antes de cair para filtros globais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.264 IDs operacionais de baixas canonicas nao vazios

- PM-06.264 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `toCanonicalSettlementsQuery()` escolhe o primeiro valor nao vazio para contrato, evento e cliente antes de cair para filtros globais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.265 sourceId do ledger nao vazio

- PM-06.265 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `toLedgerQuery()` escolhe o primeiro identificador de origem nao vazio e compartilha a conversao de IDs de query com FCF/baixas canonicas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.266 periodo/status nao vazios em queries financeiras

- PM-06.266 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `toCanonicalSettlementsQuery()` normaliza `period`, e `toFinancingQuery()` normaliza `period`, `periodo_rapido` e `status` antes de montar a query.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.267 alias semantico de excedente canonico

- PM-06.267 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: metadata local de semantica de obrigacoes mapeia `valor_excedente_realizado` para `realizedAbovePlannedAmount`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.268 aliases locais de excedente no CSV marcados

- PM-06.268 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tipo local `RealizedAbovePlannedSource` em exportacoes CSV marca aliases de excedente como deprecated e prioriza `realizedAbovePlannedAmount`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.269 fonte de leitura de obrigacao nao vazia

- PM-06.269 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationItem()` normaliza `readModelSource`, `read_model_source` e `dataSource` por primeiro valor nao vazio antes de validar o enum; helper de read model aceita string transicional e retorna somente fonte canonica valida.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.270 diagnostico de conciliacao espelhado em resumos

- PM-06.270 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resumos por diagnostico normalizam `reconciliationDiagnosis`/`diagnosticoConciliacao` por primeiro valor nao vazio e fazem aliases espelharem campos canonicos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.271 tipo de obrigacao validado antes de aliases

- PM-06.271 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de tipo de obrigacao escolhe o primeiro valor valido entre `obligationType`, `tipoObrigacao` e `tipo_obrigacao`, e item normalizado nao reaproveita tipo invalido sem validacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.272 tipo de fluxo FCF nao vazio

- PM-06.272 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialFinancingMovement()` normaliza `flowType`/`tipo_fluxo` por primeiro valor nao vazio antes de espelhar aliases, preservando o union tipado `entrada`/`saida`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.273 status nao vazio em queries canonicas

- PM-06.273 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `toLedgerQuery()` e `toCanonicalSettlementsQuery()` normalizam `status` por primeiro valor nao vazio antes de enviar consultas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.274 alias tipado de excedente documentado

- PM-06.274 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `FinancialObligationItem` e `FinancialObligationSummary` marcam `overRealizedAmount` com `@deprecated Use realizedAbovePlannedAmount`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.275 origem de obrigacao validada antes de aliases

- PM-06.275 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de origem financeira valida `source`/`origin`/`origem`/`origem_obrigacao` antes de aplicar queries e itens de obrigacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.276 grupo de fluxo validado antes de aliases

- PM-06.276 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de fluxo financeiro valida `cashFlowGroup`/`fluxo` antes de aplicar queries e itens normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.277 status de liquidacao validado antes de aliases

- PM-06.277 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de status de liquidacao valida `settlementStatus`/`situacao`/`status` antes de aplicar filtros, query e itens normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.278 status de conciliacao validado antes de aliases

- PM-06.278 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de status de conciliacao valida `reconciliationStatus`/`statusConciliacao` antes de aplicar filtros e query de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.279 diagnostico de conciliacao validado antes de aliases

- PM-06.279 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de diagnostico de conciliacao valida `reconciliationDiagnosis`/`diagnosticoConciliacao` antes de aplicar filtros, query, itens e worklist.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.280 filtro de realizado acima do previsto validado

- PM-06.280 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de filtro valida `realizedAbovePlanned`/`overRealized`/`excedenteRealizado` como `with`/`without`, preservando `excedenteRealizado` numerico como alias de valor.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.281 base de realizado validada antes de aliases

- PM-06.281 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de base de realizado valida `realizedAmountBasis`/`baseRealizado` como `originState`/`ledger` antes de aplicar filtros e query de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.282 origem e fluxo validados em envelopes de filtro

- PM-06.282 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros normalizados de ledger, obrigacoes e baixas canonicas reutilizam helpers validados de origem financeira e grupo de fluxo.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.283 tipo de lancamento validado antes de aliases

- PM-06.283 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de tipo de lancamento valida `type`/`tipo` como `entrada`/`saida` antes de aplicar filtros, queries e itens normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.284 origem de escrita validada antes de aliases

- PM-06.284 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de origem de escrita valida `writeModelSource`/`write_model_source`/`fonteEscrita`/`fonte_escrita` antes de aplicar filtros, query, itens e contexto de liquidacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.285 origem em baixas canonicas validada

- PM-06.285 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens e alocacoes de baixas canonicas reutilizam o helper validado de origem financeira antes de aliases/fallbacks.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.286 ultima baixa canonica validada

- PM-06.286 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `latestSettlement` de baixa canonica usa helpers validados de tipo de lancamento e grupo de fluxo antes de fallback textual.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.287 worklist de conciliacao validada

- PM-06.287 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: worklist de conciliacao usa helpers validados de tipo de obrigacao e origem antes de espelhar aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.288 origem agregada por fonte validada

- PM-06.288 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resumo `bySource` usa helper validado de origem financeira para campos de origem e chave agregada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.289 opcoes de filtro canonicas validadas

- PM-06.289 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de filtro de baixas canonicas validam tipos, fluxos, origens e fontes de escrita antes de expor valores para UI.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.290 opcoes de filtro de obrigacoes validadas

- PM-06.290 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de filtro de obrigacoes validam fontes, fluxos, status, diagnosticos, bases, tipos e fontes de dados antes de expor valores para UI.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.422 helpers de dimensoes da query de baixas canonicas

- PM-06.422 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query de baixas canonicas passou a resolver contrato, evento e cliente por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.633 helpers de estatisticas de movimentacoes FCF

- PM-06.633 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de estatisticas de movimentacoes FCF em helpers locais.
- Os espelhos `quantidade_movimentacoes_financiamento`, `quantidade_movimentacoes_financiamento_vencidas`, `quantidade_movimentacoes_financiamento_automaticas` e `quantidade_movimentacoes_financiamento_manuais` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.632 helpers de estatisticas de parcelas FCF

- PM-06.632 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de estatisticas de parcelas FCF em helpers locais.
- Os espelhos `quantidade_parcelas` e `quantidade_parcelas_vencidas` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.631 helpers de estatisticas de dividas FCF

- PM-06.631 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de estatisticas de dividas FCF em helpers locais.
- Os espelhos `quantidade_dividas`, `quantidade_dividas_pendentes` e `quantidade_dividas_listadas` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.630 helpers de movimentacoes dos totais FCF

- PM-06.630 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de movimentacoes dos totais FCF em helpers locais.
- Os espelhos `total_movimentacoes_financiamento_previsto_entrada`, `total_movimentacoes_financiamento_previsto_saida`, `total_movimentacoes_financiamento_realizado_entrada`, `total_movimentacoes_financiamento_realizado_saida` e `total_movimentacoes_financiamento_contas_pendentes` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.629 helpers de parcelas dos totais FCF

- PM-06.629 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de parcelas dos totais FCF em helpers locais.
- Os espelhos `total_parcelas_previsto_saida`, `total_parcelas_realizado_saida` e `total_parcelas_contas_pendentes` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.628 helpers de pendencias dos totais FCF

- PM-06.628 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de pendencias dos totais FCF em helpers locais.
- Os espelhos `total_contas_pendentes`, `total_em_aberto`, `contas_pendentes`, `total_contas_vencidas`, `total_vencido` e `contas_vencidas` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.627 helpers de resultado dos totais FCF

- PM-06.627 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de resultado dos totais FCF em helpers locais.
- Os espelhos `saldo_previsto_fcf`, `saldo_realizado_fcf`, `resultado_financeiro_fcf_projetado` e `resultado_financeiro_fcf_realizado` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.626 helpers de fluxo dos totais FCF

- PM-06.626 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de fluxo dos totais FCF em helpers locais.
- Os espelhos `total_previsto_entrada`, `total_previsto_saida`, `total_realizado_entrada` e `total_realizado_saida` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.625 helpers de resumo de contratos

- PM-06.625 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de resumo de contratos em helpers locais.
- Os espelhos `service`, `contracts`, `contractCount` e `value` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.624 helpers de metas financeiras

- PM-06.624 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de metas financeiras em helpers locais.
- Os espelhos `current` e `target` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.623 helpers de evolucao de caixa

- PM-06.623 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de evolucao de caixa em helpers locais.
- Os espelhos `accumulatedFinancialResult` e `value` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.622 helpers detalhados de metricas KPI

- PM-06.622 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases detalhados de metricas KPI em helpers locais.
- Os espelhos `value`, `change` e `changeLabel` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.621 helpers de indicadores financeiros

- PM-06.621 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de indicadores financeiros em helpers locais.
- Os espelhos `title`, `value` e `label` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.620 helpers de receita por servico

- PM-06.620 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de receita por servico em helpers locais.
- Os espelhos `service`, `revenue` e `percentage` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.619 helpers de resultado do fluxo no view model

- PM-06.619 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de resultado do fluxo de caixa no view model em helpers locais.
- Os espelhos `resultadoFinanceiro` e `saldoFinal` preservam os mesmos valores publicados no view model.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.618 helpers de entradas e saidas do fluxo de caixa

- PM-06.618 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de entradas e saidas do fluxo de caixa em helpers locais.
- Os espelhos `entradas` e `saidas` preservam os mesmos valores publicados no fluxo normalizado e no view model.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.617 helpers de resultado do fluxo de caixa

- PM-06.617 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de resultado do fluxo de caixa em helpers locais.
- Os espelhos `resultadoFinanceiro` e `saldoFinal` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.616 helpers de segmentos do resultado financeiro

- PM-06.616 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de segmentos do resultado financeiro em helpers locais.
- Os espelhos `investimentosRealizado` e `financiamentosRealizado` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.615 helpers operacionais do resultado financeiro

- PM-06.615 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases operacionais do resultado financeiro em helpers locais.
- Os espelhos `operacionalProjetado` e `operacionalRealizado` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.614 helpers projetados do resultado financeiro

- PM-06.614 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases projetados e consolidados do resultado financeiro em helpers locais.
- Os espelhos `projetado`, `realizado`, `consolidadoProjetado` e `consolidadoRealizado` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.613 helpers de liquidez do resultado financeiro

- PM-06.613 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de liquidez do resultado financeiro em helpers locais.
- Os espelhos `deficitCaixa` e `contasPendentes` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.612 helpers de disponibilidade de caixa do dashboard

- PM-06.612 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de disponibilidade de caixa do dashboard em helpers locais.
- O campo `availableCashAmount` e os espelhos `cashAvailableAmount`, `caixaDisponivel` e `saldoCaixaDisponivel` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.611 helpers de origem da query FCF

- PM-06.611 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de origem da query FCF em helpers locais.
- Os espelhos `movementSourceType`, `origem_movimentacao` e `automaticFromDebt` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.610 helpers financeiros do merge do dashboard

- PM-06.610 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases financeiros do merge do dashboard em helpers locais.
- Os espelhos `deficitCaixa` e `contasPendentesTotal` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.609 helpers de obrigacao como conta a pagar

- PM-06.609 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases da conversao de obrigacao financeira em conta a pagar.
- Os espelhos `value`, `pendingPaymentAmount`, `valor_pendente_pagamento` e `contas_pendentes` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.608 helpers de contas a receber

- PM-06.608 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de contas a receber em helpers locais.
- Os espelhos `client`, `pendingValue`, `pendingReceivableAmount`, `valor_pendente_recebimento` e `value` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.607 helpers de contas a pagar

- PM-06.607 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de contas a pagar em helpers locais.
- Os espelhos `pendingValue`, `pendingPaymentAmount`, `valor_pendente_pagamento`, `contas_pendentes`, `value` e `realizedAmount` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.606 helpers de metricas KPI

- PM-06.606 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de metricas KPI em helper local.
- Os espelhos `value`, `change` e `changeLabel` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.605 helpers de categorias de despesas

- PM-06.605 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de categorias de despesas em helper local.
- O espelho `value` preserva o mesmo valor publicado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.604 helpers de metas financeiras

- PM-06.604 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de metas financeiras em helper local.
- Os espelhos `current` e `target` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.603 helpers de indicadores financeiros

- PM-06.603 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de indicadores financeiros em helper local.
- Os espelhos `title`, `value` e `label` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.602 helpers de evolucao de caixa

- PM-06.602 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de evolucao de caixa em helper local.
- Os espelhos `accumulatedFinancialResult` e `value` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.601 helpers de resumo de contratos

- PM-06.601 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases do resumo de contratos em helper local.
- Os espelhos `service`, `contracts`, `contractCount` e `value` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.600 helpers de receita por servico

- PM-06.600 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de receita por servico em helper local.
- Os espelhos `service`, `revenue` e `percentage` preservam os mesmos valores publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.599 helpers financeiros de topo da view

- PM-06.599 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases financeiros de topo da view em helpers locais.
- Fluxo realizado, deficit e contas pendentes de topo preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.598 helpers de cashFlow da view financeira

- PM-06.598 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de cashFlow da view financeira em helpers locais.
- Saldo inicial, entradas/saidas, resultado, pendencias, grupos de fluxo e deficit preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.597 helpers de resultado financeiro do dashboard

- PM-06.597 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de resultado financeiro do dashboard em helpers locais.
- Resultado projetado/realizado, operacional, segmentos, fonte e liquidez preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.596 helpers de cashFlow do dashboard

- PM-06.596 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de cashFlow do dashboard em helpers locais.
- Saldo inicial, entradas/saidas, pendencias, resultado e deficit preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.595 helpers da resposta de credores FCF

- PM-06.595 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases da resposta de credores FCF em helper local.
- O alias `credores` preserva a mesma lista de labels publicada.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.594 helpers de query FCF

- PM-06.594 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de query FCF em helpers locais.
- Credor, tipo, origem e periodo rapido preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.593 helpers do envelope de resposta FCF

- PM-06.593 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases do envelope de resposta FCF em helpers locais.
- Controle, resumo e colecoes preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.592 helpers de grupos por credor FCF

- PM-06.592 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de grupos por credor FCF em helpers locais.
- Credor, subtotais, contagens e dividas preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.591 helpers de grupos por divida FCF

- PM-06.591 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de grupos por divida FCF em helpers locais.
- Identidade, subtotais, contagens e parcelas preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.590 helpers de movimentacoes FCF

- PM-06.590 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de movimentacoes FCF em helpers locais.
- Identidade, fluxo, valores, datas/status, origem e vinculo com divida preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.589 helpers de parcelas FCF

- PM-06.589 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de parcelas FCF em helpers locais.
- Divida, credor, vencimento, valores, disponibilidade e status preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.588 helpers de dimensoes operacionais FCF

- PM-06.588 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de dimensoes operacionais FCF em helpers locais.
- Contrato, evento e cliente preservam os mesmos aliases publicados nas entidades FCF normalizadas.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.587 helpers de dividas FCF

- PM-06.587 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de dividas FCF em helpers locais.
- Credor, descricao, tipo/status e contrato financeiro preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.586 helpers de fluxo consolidado FCF

- PM-06.586 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de fluxo consolidado FCF em helpers locais.
- Entradas, saidas e resultado financeiro preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.585 helpers de totais e estatisticas FCF

- PM-06.585 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de totais e estatisticas FCF em helpers locais.
- Fluxo, resultado, pendencias, parcelas, movimentacoes, dividas e contagens preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.584 helpers de opcoes de filtro FCF

- PM-06.584 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases das opcoes de filtro FCF em helpers locais.
- Credores, escolhas, dimensoes e origens de movimentacao preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.583 helpers de opcoes globais de filtro

- PM-06.583 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases das opcoes globais de filtro do dashboard em helpers locais.
- Entidade, contrato, cliente, evento e datas preservam os mesmos aliases publicados nas opcoes normalizadas.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.582 helpers de opcoes operacionais

- PM-06.582 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases das opcoes operacionais de contrato e evento em helpers locais.
- Contrato, cliente, evento e datas preservam os mesmos aliases publicados nas opcoes normalizadas.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.581 helpers de aliases de alocacoes de baixas

- PM-06.581 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases operacionais das alocacoes de baixas canonicas em helpers locais.
- Cliente, contrato e evento preservam os mesmos aliases publicados nas alocacoes normalizadas.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.580 helpers de resumos por diagnostico

- PM-06.580 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases dos resumos por diagnostico de conciliacao em helpers locais.
- Campos canonicos, label e orientacao de diagnostico preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.579 helpers de valores dos resumos de obrigacoes

- PM-06.579 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de valores dos resumos de obrigacoes financeiras em helpers locais.
- Valores base, excedente realizado, valores de origem e valores de ledger preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.578 helpers de aliases da worklist de conciliacao

- PM-06.578 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases transicionais da worklist de conciliacao de obrigacoes em helpers locais.
- Tipo, diagnostico, origem e dimensoes operacionais preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.577 helpers de opcionais de itens de obrigacoes

- PM-06.577 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou campos opcionais transicionais dos itens de obrigacoes financeiras em helpers locais.
- Fonte de leitura, pendencias, excedente realizado, conciliacao de origem, conciliacao de ledger e diagnostico preservam os mesmos aliases publicados quando disponiveis.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.576 helpers de mirrors de itens de obrigacoes

- PM-06.576 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos itens de obrigacoes financeiras em helpers locais.
- Origem, linha do tempo, classificacao, dimensoes operacionais e valores preservam os mesmos aliases publicados, agora concentrados por superficie.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.575 helpers de mirrors de filtros do ledger financeiro

- PM-06.575 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos filtros do ledger financeiro em helpers locais.
- Datas, dimensoes, classificacao, origem/detalhe e busca preservam os mesmos aliases publicados, agora concentrados por superficie.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.574 helpers de mirrors de itens de baixas canonicas

- PM-06.574 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos itens de baixas canonicas em helpers locais.
- Movimento, descricao, fonte de escrita, origem e dimensoes operacionais preservam os mesmos aliases publicados, agora concentrados por superficie.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.573 helpers de mirrors de itens do ledger financeiro

- PM-06.573 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos itens do ledger financeiro em helpers locais.
- Movimento, descricao, origem e dimensoes operacionais preservam os mesmos aliases publicados, agora concentrados por superficie.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.572 helpers de mirrors de filtros de baixas canonicas

- PM-06.572 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos filtros de baixas canonicas em helpers locais.
- Datas, dimensoes, origem, tipo, fluxo, natureza, fonte de escrita e busca preservam os mesmos aliases publicados, agora concentrados por superficie.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.571 helpers de mirrors de filtros de obrigacoes

- PM-06.571 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos filtros de obrigacoes em helpers locais.
- Data, dimensoes, labels, fonte, tipo, origem, fluxo, natureza, situacao, conciliacao, base de realizado, excedente e busca preservam os mesmos aliases publicados.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.570 helpers de mirrors de filtros FCF

- PM-06.570 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou mirrors transicionais dos filtros FCF em helpers locais.
- Datas, tipo, credor, origem, contrato, evento e cliente preservam os mesmos aliases publicados, agora concentrados por superficie.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.569 helpers de fallback operacional legado

- PM-06.569 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou parametros legados de URLs operacionais de obrigacoes.
- Parametros `custo_servico`, `custo_extra`, `situacao`, `busca`, `evento` e `cliente` seguem somente em helpers `getLegacy...`.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.568 helper de motivo de leitura

- PM-06.568 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos de motivo da fonte de leitura de obrigacoes.
- `readModelStatusReason`, `legacyReadReason`, `canonicalFallbackReason` e `fallbackReason` continuam aceitos apenas como fallback transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.567 helpers de opcoes e total de despesa

- PM-06.567 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos de opcoes de filtro e total de despesa previsto.
- Fallbacks de `contracts/contratos`, `events/eventos`, `clients/clientes` e total de despesa agora passam por helpers locais.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.566 helpers de labels visuais

- PM-06.566 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos de labels visuais do dashboard e da acao primaria FCF.
- Labels de categoria, servico, indicador, conta a pagar e acao de pagamento agora passam por helpers locais.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.565 helpers de fluxo e KPIs do dashboard

- PM-06.565 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/fallback de fluxo de caixa, ledger e KPIs financeiros do dashboard.
- Entradas, saidas, saldo inicial, resultado financeiro e aliases operacionais agora passam por helpers locais.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.564 helpers de totais do dashboard

- PM-06.564 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/fallback de totais do dashboard, deficit de caixa, contas pendentes e caixa disponivel.
- Campos canonicos seguem preferenciais; aliases continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.563 helpers de pagamento pendente FCF

- PM-06.563 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/fallback do total de pagamento pendente FCF.
- Fallback para contas pendentes segue apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.562 helpers de estatisticas FCF

- PM-06.562 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases das estatisticas FCF normalizadas.
- Aliases de contagens de dividas, parcelas e movimentacoes seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.561 helpers de totais FCF

- PM-06.561 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos totais FCF normalizados.
- Aliases de contas pendentes, entradas/saidas, resultado e vencidos seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.560 helpers de labels de credor FCF

- PM-06.560 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases de labels de credor no util FCF.
- Aliases de credor e credor da divida seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.559 helpers de busca da query de obrigacoes

- PM-06.559 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases do filtro de busca da query de obrigacoes.
- Alias `busca` segue apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.558 helpers da query de baixas canonicas

- PM-06.558 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos filtros restantes da query de baixas canonicas.
- Alias de busca segue apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.557 helpers da query FCF no service

- PM-06.557 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos overrides usados pela query FCF no service.
- Aliases de periodo rapido, credor, tipo e origem de movimentacao seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.556 helpers de overrides do hook FCF

- PM-06.556 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos overrides consumidos pelo hook FCF.
- Aliases de credor, tipo, origem de movimentacao e periodo rapido seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.555 helpers de resumos e diagnosticos de obrigacoes

- PM-06.555 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases de resumos e diagnosticos de obrigacoes financeiras.
- Aliases de diferenca realizada, labels de diagnostico e orientacao seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.554 helpers da worklist de reconciliacao de obrigacoes

- PM-06.554 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da worklist de reconciliacao de obrigacoes.
- Aliases de diagnostico, orientacao, contrato e cliente seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.553 helpers de itens de obrigacoes financeiras

- PM-06.553 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos itens de obrigacoes financeiras.
- Aliases de origem, detalhes, datas, dimensoes operacionais, status, diagnosticos e reconciliacao seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.552 helpers de itens de baixas canonicas

- PM-06.552 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos itens de baixas canonicas.
- Aliases de valores, origem, dimensoes operacionais, natureza, descricao e alocacoes seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.551 helpers de alocacoes de baixas canonicas

- PM-06.551 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases das alocacoes de baixas canonicas.
- Aliases de cliente, contrato, evento e labels seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.550 helpers de itens do ledger financeiro

- PM-06.550 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos itens do ledger financeiro.
- Aliases de valores, origem, dimensoes operacionais, datas, natureza, descricao e labels seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.549 helpers de filtros do ledger financeiro

- PM-06.549 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos filtros do ledger financeiro.
- Aliases de datas, contrato, evento, cliente, origem, detalhe, natureza e busca seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.548 helpers do envelope FCF

- PM-06.548 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases do envelope de resposta FCF.
- Aliases de listas, opcoes, totais e estatisticas seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.547 helpers de filtros FCF

- PM-06.547 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos filtros FCF normalizados.
- Aliases de datas, tipo, credor, origem, contrato, evento e cliente seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.546 helpers de agrupamentos FCF

- PM-06.546 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos agrupamentos FCF por divida e por credor.
- Aliases de divida, credor, subtotais, contagens, parcelas e dividas seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.545 helpers de movimentacoes FCF

- PM-06.545 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da normalizacao de movimentacoes FCF.
- Aliases de descricao, categoria, fluxo, datas, status, origem, divida, credor, atraso e valores seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.544 helpers de dimensoes operacionais FCF

- PM-06.544 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da dimensao operacional compartilhada no FCF.
- Aliases de contrato, evento e cliente seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.543 helpers de parcelas FCF

- PM-06.543 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da normalizacao de parcelas FCF.
- Aliases de divida, credor, vencimentos, valores, parcela, atraso e disponibilidade seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.542 helpers de dividas FCF

- PM-06.542 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da normalizacao de dividas FCF.
- Aliases de credor, descricao, tipo, data, valor e parcelas seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.541 helpers de opcoes de eventos do dashboard

- PM-06.541 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases das opcoes de eventos do dashboard.
- Aliases de evento, contrato, cliente e data inicial seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.540 helpers de opcoes de contratos do dashboard

- PM-06.540 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases das opcoes de contratos do dashboard.
- Aliases de contrato e cliente seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.539 helpers de opcoes de entidades do dashboard

- PM-06.539 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases do filtro generico de entidade do dashboard.
- Aliases de cliente e nome seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.538 helpers de opcoes de eventos operacionais

- PM-06.538 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases de opcoes de eventos operacionais no service.
- Aliases de evento, contrato, cliente e data inicial seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.537 helpers de opcoes de contratos operacionais

- PM-06.537 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases de opcoes de contratos operacionais no service.
- Aliases de contrato e cliente seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.536 helpers de opcoes financeiras legadas

- PM-06.536 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases ao gerar opcoes financeiras legadas no service.
- `valor` e `rotulo` seguem publicados apenas como compatibilidade transicional para consumers antigos.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.535 helpers de opcoes financeiras

- PM-06.535 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases de opcoes financeiras no service.
- Aliases de credor e choices financeiros seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.534 helpers de opcoes de filtro

- PM-06.534 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases do normalizador generico de opcoes de filtro.
- Aliases `valor` e `rotulo` seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.533 helpers de filtros de baixas canonicas

- PM-06.533 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos filtros normalizados de baixas canonicas.
- Aliases de contrato, evento, cliente, datas, natureza e busca seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.532 helpers de filtros de obrigacoes

- PM-06.532 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases dos filtros normalizados de obrigacoes.
- Aliases de contrato, evento, cliente, datas, natureza, busca e labels seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.531 helpers de query do ledger financeiro

- PM-06.531 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da query do ledger financeiro.
- Aliases de natureza, origem, origem/id, detalhe de origem e busca seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.530 helpers de query FCF

- PM-06.530 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da query FCF.
- Aliases de datas, contrato, evento, cliente e origem de movimentacao seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.529 helpers de query de baixas canonicas

- PM-06.529 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases da query de baixas canonicas.
- Aliases de datas, contrato, evento e cliente seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.528 helpers de candidatos numericos de obrigacoes

- PM-06.528 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases para valores numericos de obrigacoes.
- Aliases de valores pendentes, previstos, realizados, pagos e excedentes continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.527 helpers de candidatos de obrigacoes

- PM-06.527 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos canonicos/aliases usados pelos resolvedores de campos de obrigacoes.
- Aliases de tipo, origem, fluxo, situacao, conciliacao, base de realizado e fonte de escrita continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.526 helpers de candidatos de origem FCF

- PM-06.526 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou candidatos de label e valor da origem de movimentacao FCF.
- Aliases de origem de movimentacao seguem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.525 mapa de aliases da query de obrigacoes

- PM-06.525 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js centralizou aliases de query do hook de obrigacoes financeiras em mapa local.
- Aliases de base realizada, conciliacao, fonte, tipo, origem, fluxo, situacao e busca continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.524 helper de datas em evidencias PM-03

- PM-06.524 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou a compatibilidade `startDate`/`data_inicial` e `endDate`/`data_final` no label de periodo das evidencias PM-03.
- Evidencias antigas seguem legiveis, mas a leitura dos aliases fica concentrada em helper local.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.523 helper de evento no header

- PM-06.523 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou a compatibilidade `eventId`/`costCenterId` no header do dashboard.
- Contagem de filtros, submit e valor visual do filtro de evento passam pela mesma porta local.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.522 normalizador central para evento dos hooks

- PM-06.522 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js centralizou a compatibilidade `eventId`/`costCenterId` dos hooks financeiros no normalizador de filtros do dashboard.
- Hooks de dashboard, FCF e obrigacoes deixam de resolver esse alias localmente.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.521 helpers de query do hook FCF

- PM-06.521 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de query usados pelo hook de FCF.
- Aliases de credor, tipo de divida, origem, periodo rapido e automaticidade continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.520 helper de aliases da query inicial do dashboard

- PM-06.520 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou os aliases aceitos pela query inicial do dashboard financeiro.
- Aliases de periodo, status, datas, contrato, evento, cliente e servico continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.519 helpers de filtros iniciais da tela FCF

- PM-06.519 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou filtros iniciais da tela FCF derivados da query.
- Aliases de credor, tipo de divida e origem de movimentacao continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.518 helper de aliases da query inicial da tela de obrigacoes

- PM-06.518 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou a leitura de aliases aceitos pela query inicial da tela de obrigacoes.
- Aliases de base realizada, origem, fluxo, situacao, conciliacao, tipo de obrigacao e busca continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.517 helper de filtros default de baixas canonicas

- PM-06.517 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou o literal de filtros default usado por `normalizeCanonicalFinancialSettlementsFilters()`.
- Campos canonicos e aliases legados dos filtros default de baixas canonicas continuam preservados antes da normalizacao.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.516 helper de filtros default do normalizador do ledger financeiro

- PM-06.516 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou o literal de filtros default usado por `normalizeFinancialLedgerFilters()`.
- Campos canonicos e aliases legados dos filtros default do ledger continuam preservados antes da normalizacao.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.515 helper de filtros vazios de obrigacoes financeiras

- PM-06.515 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou o literal de filtros vazios emitido por `emptyFinancialObligationsResponse()`.
- Campos canonicos e aliases legados dos filtros vazios de obrigacoes continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.514 helper de filtros vazios do ledger financeiro

- PM-06.514 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou o literal de filtros vazios emitido por `emptyFinancialLedgerResponse()`.
- Campos canonicos e aliases legados dos filtros vazios do ledger continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.513 helper de aliases do conversor de obrigacao para conta a pagar

- PM-06.513 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases emitidos por `obligationToAccountPayable()`.
- Campos `value`, `pendingPaymentAmount`, `valor_pendente_pagamento` e `contas_pendentes` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.512 helpers de aliases de contas a pagar e receber

- PM-06.512 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases emitidos por `normalizeAccountsPayable()` e `normalizeAccountsReceivable()`.
- Campos de pendencia, valores, realizado e cliente visual continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.511 helper de campos de diagnostico dos resumos de conciliacao

- PM-06.511 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou campos de diagnostico emitidos por `normalizeFinancialObligationReconciliationSummaries()`.
- Campos `reconciliationDiagnosis`, `diagnosticoConciliacao`, labels e orientacao continuam apenas como compatibilidade transicional quando presentes.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.510 helper de aliases de origem dos resumos por fonte de obrigacoes

- PM-06.510 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de origem emitidos por `normalizeFinancialObligationBySourceSummaries()`.
- Campos `source`, `origin` e `origem` continuam apenas como compatibilidade transicional quando a origem e valida.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.509 helper de aliases de valores dos resumos de obrigacoes financeiras

- PM-06.509 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou aliases de valores emitidos por `normalizeFinancialObligationSummaryAmountAliases()`.
- Campos de valores previstos, realizados, pagos, pendentes, excedentes, origem/ledger e diferenca de realizado continuam apenas como compatibilidade transicional quando presentes.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.508 helper de campos legados da worklist de conciliacao de obrigacoes

- PM-06.508 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou campos legados emitidos por `normalizeFinancialObligationReconciliationWorklistItem()`.
- Campos condicionais de tipo, diagnostico, orientacao, origem e dimensoes de contrato/cliente continuam apenas como compatibilidade transicional quando presentes.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.507 helper de campos condicionais dos itens de obrigacoes financeiras

- PM-06.507 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou campos condicionais emitidos por `normalizeFinancialObligationItem()`.
- Campos de fonte de leitura, pendencias, excedentes, valores de origem/ledger, diferenca de realizado, conciliacao e diagnosticos continuam apenas como compatibilidade transicional quando presentes.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.506 helper de espelhos basicos dos itens de obrigacoes financeiras

- PM-06.506 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados basicos emitidos por `normalizeFinancialObligationItem()`.
- Campos como `tipoObrigacao`, `tipo_obrigacao`, `origin`, `origem`, `originId`, `source_detail`, `referencia`, datas legadas, `fluxo`, `natureza`, `status_display`, `situacao`, dimensoes de cliente/contrato/evento, `descricao`, valores basicos e pendencias continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.505 helper de espelhos dos itens de baixas canonicas

- PM-06.505 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeCanonicalFinancialSettlementItem()`.
- Campos como `tipo`, `fluxo`, `natureza`, `valorBaixa`, `valor_baixa`, `valorTotal`, `descricao`, `fonteEscrita`, `origin`, `origem`, `originId`, `cliente_id`, `cliente_nome`, `contrato_operacional_id`, `contrato_codigo`, `contrato_operacional_label`, `evento_id`, `evento_nome`, `evento_numero` e `evento_label` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.504 helper de espelhos das alocacoes de baixas canonicas

- PM-06.504 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeCanonicalFinancialSettlementAllocation()`.
- Campos como `cliente_id`, `cliente_nome`, `contrato_operacional_id`, `contrato_codigo`, `contrato_operacional_label`, `evento_id`, `evento_nome`, `evento_numero` e `evento_label` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.503 helper de espelhos dos filtros de baixas canonicas

- PM-06.503 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeCanonicalFinancialSettlementsFilters()`.
- Campos como `data_inicial`, `data_final`, `contrato_operacional`, `evento_id`, `cliente_id`, `origin`, `origem`, `tipo`, `fluxo`, `natureza`, `write_model_source`, `fonteEscrita`, `fonte_escrita` e `busca` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.502 helper de espelhos dos filtros de obrigacoes financeiras

- PM-06.502 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialObligationsFilters()`.
- Campos como `data_inicial`, `data_final`, `contrato_operacional`, `evento_id`, `cliente_id`, labels em portugues, `fonteDados`, `tipoObrigacao`, `tipo_obrigacao`, `origin`, `origem`, `fluxo`, `natureza`, `status`, `situacao`, `statusConciliacao`, `diagnosticoConciliacao`, `baseRealizado`, `overRealized`, `excedenteRealizado` e `busca` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.501 helper de espelhos da disponibilidade de caixa em obrigacoes

- PM-06.501 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeObligationsCashAvailability()`.
- Campos como `aplicavel`, `cashAvailableAmount`, `caixaDisponivel` e `saldoCaixaDisponivel` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.500 helper de espelhos dos itens do ledger financeiro

- PM-06.500 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialLedgerItem()`.
- Campos como `data`, `tipo`, `fluxo`, `natureza`, `valorLancamento`, `valor_lancamento`, `valor`, `descricao`, `origem`, `cliente_id`, `contrato_operacional_id`, `contrato_codigo`, `contract`, `evento_id`, `evento_nome`, `evento_numero` e `evento_label` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.499 helper de espelhos dos filtros do ledger financeiro

- PM-06.499 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialLedgerFilters()`.
- Campos como `data_inicial`, `data_final`, `contrato_operacional`, `evento_id`, `cliente_id`, `fluxo`, `tipo`, `natureza`, `origem`, `origem_obrigacao`, `source_id`, `origin_id`, `source_detail` e `busca` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.498 helpers nos fallbacks vazios de credores e ledger

- PM-06.498 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js passou a reutilizar helpers de espelhos legados nos fallbacks vazios de credores e ledger.
- Espelhos como `credores`, `entradas`, `saidas`, `resultadoFinanceiro` e `resultado_financeiro` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.497 helper de espelhos da dimensao operacional financeira

- PM-06.497 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialOperationalDimension()`.
- Campos como `contrato_operacional_id`, `contrato_codigo`, `contrato_operacional_label`, `contract`, `evento_id`, `evento_nome`, `evento_numero`, `evento_label`, `cliente_id` e `cliente_nome` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.496 helper de espelhos das opcoes de evento do dashboard

- PM-06.496 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeDashboardEventFilterOption()`.
- Campos como `evento_id`, `evento_nome`, `evento_numero`, `evento_label`, `numero`, `contrato_operacional_id`, `contrato_codigo`, `contrato`, `cliente_id`, `cliente_nome`, `nome`, `dataInicio` e `data_inicio` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.495 helper de espelhos das opcoes de contrato do dashboard

- PM-06.495 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeDashboardContractFilterOption()`.
- Campos como `contrato_operacional_id`, `contrato_codigo`, `contrato_operacional_label`, `contrato`, `nome`, `cliente_id` e `cliente_nome` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.494 helper de espelhos das opcoes de entidade do dashboard

- PM-06.494 foi concluida em desenvolvimento local em 2026-05-30.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeDashboardEntityFilterOption()`.
- Campos como `cliente_id`, `cliente_nome` e `nome` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.493 helper de espelhos das opcoes de evento operacional

- PM-06.493 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialOperationalEventOption()`.
- Campos como `nome`, `numero`, `contrato_operacional_id`, `contrato_codigo`, `contrato`, `cliente_id`, `cliente_nome`, `dataInicio` e `data_inicio` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.492 helper de espelhos das opcoes de contrato operacional

- PM-06.492 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialOperationalContractOption()`.
- Campos como `contrato_operacional_id`, `contrato_codigo`, `contrato`, `nome`, `cliente_id`, `cliente_nome` e `descricao` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.491 helper de espelhos da resposta de credores FCF

- PM-06.491 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialCreditorsResponse()`.
- O campo `credores` continua apenas como lista textual de compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.490 helper de espelhos condicionais dos filtros FCF

- PM-06.490 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos condicionais emitidos por `normalizeFinancialFinancingFilters()`.
- Pares como `startDate`/`data_inicial`, `endDate`/`data_final`, `type`/`tipo`, `creditorId`/`credor_id`, `sourceType`/`origem_movimentacao`, `contractId`/`contrato_operacional`, `eventId`/`evento_id` e `clientId`/`cliente_id` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.489 helper de espelhos do envelope FCF

- PM-06.489 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingResponse()`.
- Campos de topo como `filtros`, `opcoes`, `totais`, `estatisticas`, `dividas`, `parcelas`, `movimentacoes_financiamento` e `grupos_credor` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.488 helper de espelhos das opcoes de filtro FCF

- PM-06.488 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingFilterOptions()`.
- Campos como `credores`, `tipos_divida`, `status_parcelas`, `categorias_financiamento`, `tipos_fluxo_financiamento`, `status_financiamento`, `contratos`, `eventos`, `clientes`, `movementSourceTypes` e `origens_movimentacao_financiamento` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.487 helper de espelhos de grupos de credores FCF

- PM-06.487 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingCreditorGroup()`.
- Campos como `credor_id`, `credor_nome`, `credor`, subtotais snake_case, contagens de parcelas e `dividas` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.486 helper de espelhos de grupos de dividas FCF

- PM-06.486 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingDebtGroup()`.
- Campos como `divida_id`, `credor_id`, `credor_nome`, `descricao`, subtotais snake_case, contagens de parcelas e `parcelas` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.485 helper de espelhos de movimentacoes FCF

- PM-06.485 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingMovement()`.
- Campos como `financingMovementDescription`, `descricao`, `categoria`, `tipo_fluxo`, valores em portugues, datas, origem da movimentacao, vinculo com divida e `dias_atraso` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.484 helper de espelhos de parcelas FCF

- PM-06.484 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingInstallment()`.
- Campos como `divida_id`, `credor_id`, `numero_parcela`, `rotulo_parcela`, datas de vencimento, valores em portugues, `saldo_em_aberto`, `dias_atraso` e `baixado_manualmente` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.483 helper de espelhos de dividas FCF

- PM-06.483 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingDebt()`.
- Campos como `credor_id`, `credor_nome`, `tipo`, `tipo_display`, `data_contratacao`, `valor_contratado` e `quantidade_parcelas` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.482 helper de espelhos das estatisticas FCF normalizadas

- PM-06.482 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingStatistics()`.
- Contagens `quantidade_*` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.481 helper de espelhos dos totais FCF normalizados

- PM-06.481 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingTotals()`.
- Totais snake_case de entradas, saidas, resultado FCF, contas pendentes/vencidas, parcelas e movimentacoes continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.480 helper de espelhos dos fluxos FCF normalizados

- PM-06.480 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeFinancialFinancingFlowAmounts()`.
- `entradas`, `saidas`, `resultadoFinanceiro` e `resultado_financeiro` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.479 helper de espelhos do resumo de fluxo do ledger

- PM-06.479 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `normalizeLedgerFlowSummary()`.
- `entradas`, `saidas`, `resultadoFinanceiro` e `resultado_financeiro` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.478 espelhos do resultado financeiro normalizado

- PM-06.478 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js reutilizou `getDashboardFinancialResultLegacyMirrors()` tambem em `normalizeFinancialResult()`.
- Espelhos de resultado financeiro continuam apenas como compatibilidade transicional e agora compartilham o mesmo helper.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.477 helper de espelhos legados do resultado financeiro

- PM-06.477 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `mergeDashboardFinancialResult()`.
- Espelhos em portugues como `projetado`, `realizado`, `consolidadoProjetado`, `operacionalProjetado`, `deficitCaixa` e `contasPendentes` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.476 helper de disponibilidade de caixa normalizada

- PM-06.476 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos de disponibilidade de caixa emitidos por `normalizeDashboardCashAvailability()`.
- `cashAvailableAmount`, `caixaDisponivel` e `saldoCaixaDisponivel` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.475 helper de espelhos legados do merge de cash flow

- PM-06.475 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos por `mergeDashboardCashFlow()`.
- Espelhos como `saldoInicial`, `entradas`, `saidas`, `contasPendentes`, `resultadoFinanceiro`, `saldoFinal` e `deficitCaixa` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.474 helper de disponibilidade de caixa do cash flow

- PM-06.474 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos de disponibilidade de caixa emitidos dentro de `cashFlow`.
- `availableCashAmount` e `cashAvailableAmount` seguem preferenciais; `caixaDisponivel` e `saldoCaixaDisponivel` permanecem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.473 helper de espelhos legados do cash flow da view model

- PM-06.473 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos legados emitidos dentro de `cashFlow` na view model do dashboard.
- Espelhos como `saldoInicial`, `entradas`, `saidas`, `resultadoFinanceiro`, `contasPendentes`, `fluxosCaixa`, `deficitCaixa` e `saldoFinal` continuam apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.472 helper de espelhos financeiros legados da view model

- PM-06.472 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou espelhos financeiros legados emitidos pela view model do dashboard.
- `realizedCashFlow`, `deficitCaixa` e `contasPendentesTotal` continuam emitidos apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.471 helper de espelhos financeiros legados do merge do dashboard

- PM-06.471 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou os espelhos financeiros legados emitidos pelo merge do dashboard.
- `deficitCaixa` e `contasPendentesTotal` continuam emitidos apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.470 helper de alias legado de fluxo realizado

- PM-06.470 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou o alias legado `realizedCashFlow` usado como fallback de `cashBasisRealizedFlow`.
- `cashBasisRealizedFlow` segue preferencial e `realizedCashFlow` permanece apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.469 helpers de merge de KPIs do dashboard

- PM-06.469 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou defaults de metricas KPI e a leitura do alias visual legado `saldoCaixa`.
- Metricas canonicas seguem preferenciais; `saldoCaixa` permanece apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.468 helpers de deficit e contas pendentes do payload do dashboard

- PM-06.468 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js separou leitura de aliases do payload backend dos fallbacks operacionais de deficit e contas pendentes.
- `cashDeficitAmount`/`pendingAccountsAmount` seguem preferenciais; `deficitCaixa`, `contasPendentesTotal` e `contasPendentes` permanecem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.467 helper de resultado financeiro do fluxo de caixa da view model

- PM-06.467 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou aliases de resultado financeiro vindos do cash flow da view model.
- `financialResultAmount` segue preferencial; `resultadoFinanceiro` e `saldoFinal` permanecem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.466 helpers de valores base do fluxo de caixa da view model

- PM-06.466 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou aliases de caixa inicial, entradas e despesas da view model do dashboard.
- `initialCashAmount`, `inflowAmount` e `outflowAmount` seguem preferenciais; `saldoInicial`, `entradas` e `saidas` permanecem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.465 helper de contas pendentes da view model

- PM-06.465 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou aliases de contas pendentes da view model do dashboard.
- `pendingAccountsAmount` segue preferencial; `contasPendentesTotal` e `contasPendentes` permanecem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.464 helper de deficit de caixa da view model

- PM-06.464 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou aliases de deficit de caixa da view model do dashboard.
- `cashDeficitAmount` segue preferencial e `deficitCaixa` permanece apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.463 helper de disponibilidade de caixa da view model

- PM-06.463 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou aliases de disponibilidade de caixa da view model do dashboard.
- `availableCashAmount` segue preferencial; `caixaDisponivel` e `saldoCaixaDisponivel` permanecem apenas como compatibilidade transicional.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.462 helper do valor do KPI de resultado financeiro

- PM-06.462 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou a leitura do valor do KPI de resultado financeiro da view model.
- `resultadoFinanceiro` segue preferencial e `saldoCaixa` permanece apenas como fallback visual legado.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.461 helper de aliases depreciados de nomenclatura

- PM-06.461 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou o fallback `deprecatedAliases <- legacyAliasUsage` dos metadados de nomenclatura.
- `legacyAliasUsage` segue preservado como compatibilidade quando `deprecatedAliases` nao vem preenchido.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.460 helper de periodo efetivo da query FCF

- PM-06.460 foi concluida em desenvolvimento local em 2026-05-29.
- Frontend Next.js encapsulou a regra que remove `period` quando `periodo_rapido` esta presente no builder de query FCF.
- O payload final permanece compativel: `periodo_rapido` segue como espelho legado e `period` fica ausente nesse modo.
- Validacoes locais: `lint`, `typecheck`, `build` e `git diff --check` aprovados no frontend; `git diff --check` aprovado no backend, apenas com avisos CRLF ja conhecidos.
- Guardrail: nenhum alias, endpoint, migration, congelamento de escrita legada, limpeza ou corte fisico foi iniciado.

## Atualizacao - PM-06.459 helper de espelhos legados da query FCF

- PM-06.459 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: builder de query FCF passou a concentrar espelhos legados em helper local.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.458 helpers de paginacao da query de baixas canonicas

- PM-06.458 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: builder de query de baixas canonicas passou a resolver `limit` e `offset` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.457 helpers de paginacao da query do ledger

- PM-06.457 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: builder de query do ledger financeiro passou a resolver `limit` e `offset` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.456 helpers do builder de query de obrigacoes

- PM-06.456 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: builder de query de obrigacoes financeiras passou a resolver campos efetivos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.455 helpers de disponibilidade de caixa acumulada

- PM-06.455 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: disponibilidade de caixa acumulada e diferenca contra realizado do periodo passaram a ser resolvidas por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.454 helpers de aliases do resumo do payload do dashboard

- PM-06.454 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resumo do payload do dashboard passou a resolver contagens por helpers locais, preservando o alias `activeContractsCount`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.453 helpers de aliases de opcoes de filtro do dashboard

- PM-06.453 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de filtro do dashboard passaram a resolver contratos, eventos, clientes e status por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.452 helpers de aliases de valores KPI da view model

- PM-06.452 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: valores KPI derivados da view model do dashboard passaram a ser resolvidos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.451 helpers de aliases de contagens do resumo do dashboard

- PM-06.451 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contagens do resumo da view model do dashboard passaram a ser resolvidas por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.450 helper de alias de total de despesa prevista

- PM-06.450 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: o total de despesa prevista do payload do dashboard passou a ser resolvido por helper local.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.449 helpers de aliases dos filtros iniciais de obrigacoes

- PM-06.449 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `FinancialObligationsView` passou a iniciar filtros de obrigacoes por helpers locais, preservando aliases de query transicionais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.448 helpers de aliases de query do hook de obrigacoes

- PM-06.448 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `useFinancialObligations()` passou a resolver base de realizado, conciliacao, fonte, tipo, origem, fluxo, situacao, busca, limite e offset por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.447 helpers de aliases de query inicial do dashboard

- PM-06.447 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query inicial dos filtros do dashboard passou a resolver periodo, datas, contrato, evento, cliente, servico e status por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.446 helpers de resumo de obrigacoes do dashboard

- PM-06.446 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resumo de obrigacoes pendentes e divergentes do dashboard passou a ser calculado por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.445 helpers de aliases da conversao de obrigacoes para contas a pagar

- PM-06.445 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: a conversao de obrigacoes financeiras para contas a pagar do dashboard passou a resolver descricao, contrato, evento, origem e valores por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.444 helpers de aliases de contas a receber do dashboard

- PM-06.444 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contas a receber do dashboard passaram a resolver valores, cliente, descricoes e pendencia por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.443 helpers de aliases de contas a pagar do dashboard

- PM-06.443 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contas a pagar do dashboard passaram a resolver valores, descricoes e pendencia por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.423 helpers de dimensoes e origem da query FCF

- PM-06.423 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query FCF passou a resolver contrato, evento, cliente e origem de movimentacao por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.424 helpers de aliases da query do ledger financeiro

- PM-06.424 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query do ledger financeiro passou a resolver natureza, origem, sourceId, sourceDetail e busca por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.425 helpers de aliases restantes da query FCF

- PM-06.425 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query FCF passou a resolver datas, periodo rapido, status, credor e tipo de divida por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.426 helpers de aliases restantes da query de baixas canonicas

- PM-06.426 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query de baixas canonicas passou a resolver datas, periodo, status e busca por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.427 helpers de aliases de credor e tipo nos filtros FCF

- PM-06.427 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros FCF retornados pela API passaram a resolver tipo de divida, credor cadastrado e credor textual por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.428 helpers de aliases restantes dos filtros do ledger financeiro

- PM-06.428 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros do ledger financeiro retornados pela API passaram a resolver datas, natureza, status e busca por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.429 helpers de aliases restantes dos filtros de obrigacoes financeiras

- PM-06.429 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros de obrigacoes financeiras retornados pela API passaram a resolver datas, natureza e busca por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.430 helpers de aliases restantes dos filtros de baixas canonicas

- PM-06.430 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros de baixas canonicas retornados pela API passaram a resolver datas, natureza e busca por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.431 helpers de aliases de credor e tipo nos itens de divida FCF

- PM-06.431 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de divida FCF passaram a resolver credor, credor cadastrado, tipo e rotulo de tipo por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.432 helpers de aliases de parcelas FCF

- PM-06.432 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: parcelas FCF passaram a resolver credor, descricao de divida, vencimentos, status e flags por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.433 helpers de aliases de movimentacoes FCF

- PM-06.433 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: movimentacoes FCF passaram a resolver descricao, categoria, fluxo, datas, origem, divida e credor de divida por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.434 helpers de aliases de grupos FCF

- PM-06.434 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: grupos FCF por divida e por credor passaram a resolver credor e descricao por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.435 helpers de aliases e labels de itens do ledger financeiro

- PM-06.435 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens do ledger financeiro passaram a resolver data, natureza, descricao, status e labels por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.436 helpers de aliases de itens de baixas canonicas

- PM-06.436 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de baixas canonicas passaram a resolver natureza e descricao por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.437 helpers de aliases de itens de obrigacoes financeiras

- PM-06.437 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes financeiras passaram a resolver origem, datas, natureza, status, fonte de leitura, descricao e conciliacao por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.438 helpers de aliases da ultima baixa canonica

- PM-06.438 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: ultima baixa canonica no contexto de liquidacao passou a resolver valor, datas, descricao, tipo, natureza, status e ledgerEntryId por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.439 helpers de metadados do contexto de baixa canonica

- PM-06.439 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contexto de baixa canonica passou a resolver flags, modelos, contagens, valores e motivo por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.440 helpers de aliases da worklist de conciliacao de obrigacoes

- PM-06.440 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: worklist de conciliacao de obrigacoes passou a resolver diagnostico, orientacao e rotulo de origem por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.441 helpers de aliases de datasets visuais do dashboard

- PM-06.441 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: datasets visuais do dashboard passaram a resolver receita/despesa, categorias, servicos, contratos, evolucao, indicadores e metas por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.442 helpers de aliases de metricas KPI do dashboard

- PM-06.442 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: metricas KPI do dashboard passaram a resolver valor, variacao e descricao de variacao por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.421 helpers de filtros dimensionais de baixas canonicas

- PM-06.421 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros de baixas canonicas passaram a resolver contrato, evento e cliente por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.420 helpers de filtros dimensionais de obrigacoes financeiras

- PM-06.420 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros de obrigacoes financeiras passaram a resolver contrato, evento, cliente e labels por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.419 helpers de filtros dimensionais do ledger financeiro

- PM-06.419 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros do ledger financeiro passaram a resolver contrato, evento e cliente por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.418 helpers de dimensoes da worklist de reconciliacao de obrigacoes

- PM-06.418 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens da worklist de reconciliacao de obrigacoes passaram a resolver contrato, cliente e rotulos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.417 helpers de dimensoes de itens de obrigacao financeira

- PM-06.417 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacao financeira passaram a resolver cliente, contrato, evento e rotulos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.416 helpers de filtros FCF de origem e dimensoes

- PM-06.416 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros FCF passaram a resolver origem de movimentacao, contrato, evento, cliente e espelhamento transicional por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.415 helpers de dimensoes operacionais financeiras

- PM-06.415 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: dimensoes operacionais financeiras passaram a resolver contrato, evento, cliente e rotulos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.414 helpers de dimensoes de opcoes operacionais de evento

- PM-06.414 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes operacionais de evento passaram a resolver evento, contrato, cliente, data e rotulo por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.413 helpers de dimensoes de opcoes operacionais de contrato

- PM-06.413 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes operacionais de contrato passaram a resolver contrato, cliente e rotulos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.412 helpers de dimensoes de opcoes de entidade do dashboard

- PM-06.412 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de entidade do dashboard passaram a resolver cliente e rotulo por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.411 helpers de dimensoes de opcoes de contrato do dashboard

- PM-06.411 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de contrato do dashboard passaram a resolver contrato, cliente e rotulos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.410 helpers de dimensoes de opcoes de evento do dashboard

- PM-06.410 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de evento do dashboard passaram a resolver evento, contrato, cliente, datas e rotulos por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.409 helpers de dimensoes de alocacoes de baixas canonicas

- PM-06.409 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: alocacoes de baixas financeiras canonicas passaram a resolver cliente, contrato, rotulos e evento por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.408 helpers de dimensoes de baixas canonicas

- PM-06.408 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: baixas financeiras canonicas passaram a resolver cliente, contrato, rotulos e evento por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.407 helpers de dimensoes de itens do ledger

- PM-06.407 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens do ledger financeiro passaram a resolver cliente, contrato, rotulos e evento por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.406 helpers de totais de fluxo do ledger

- PM-06.406 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: totais de fluxo do ledger passaram a resolver `inflowAmount/entradas`, `outflowAmount/saidas` e `financialResultAmount/resultadoFinanceiro/resultado_financeiro` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.405 helpers de filtros de origem/fonte do ledger

- PM-06.405 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros do ledger financeiro passaram a resolver `origin/origem`, `source`, `sourceId/source_id`, `originId/origin_id` e `sourceDetail/source_detail` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.404 helpers de fonte de baixas canonicas

- PM-06.404 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de baixas financeiras canonicas passaram a resolver `source/origin/origem`, `sourceId/originId` e `sourceLabel` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.403 helpers de origem/fonte do ledger

- PM-06.403 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens do ledger financeiro passaram a resolver `origin/origem/source`, `originId/sourceId` e `sourceId` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.402 helper de lucro operacional EBIT

- PM-06.402 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: view model financeiro passou a resolver `lucroOperacionalEbit` com fallback em `operationalProjectedAmount/operacionalProjetado` por helper local.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.401 helpers de KPI resultado/saldo

- PM-06.401 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: view model financeiro passou a selecionar KPI `resultadoFinanceiro/saldoCaixa` por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.400 helper de fluxo realizado do view model

- PM-06.400 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: view model financeiro final passou a resolver `cashBasisRealizedFlow/realizedCashFlow` por helper local.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.399 helpers de grupos cashFlows do dashboard

- PM-06.399 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: grupos de fluxo de caixa do dashboard passaram a resolver `cashFlows/fluxosCaixa` por helper local antes da normalizacao FCO/FCI/FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.398 helpers de valores adicionais do resultado financeiro

- PM-06.398 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resultado financeiro passou a resolver valores projetados, consolidados, operacionais, investimentos, financiamentos, deficit e contas pendentes por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.397 helpers de caixa disponivel de obrigacoes

- PM-06.397 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: caixa disponivel de obrigacoes passou a resolver aplicabilidade, caixa disponivel, contas a pagar pendentes, caixa apos pendencias e deficit de cobertura por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.396 helpers de caixa disponivel do dashboard

- PM-06.396 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: caixa disponivel do dashboard passou a resolver realizado do periodo, caixa disponivel e caixa final por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.395 helpers de filtros do response FCF

- PM-06.395 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros FCF passaram a montar `filters/filtros` por helper local antes da normalizacao e espelhamento de aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.394 helpers de envelopes do response FCF

- PM-06.394 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: response FCF passou a resolver `filterOptions/opcoes`, `totals/totais` e `statistics/estatisticas` por helpers locais antes da normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.393 helpers do payload bruto do dashboard

- PM-06.393 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: o merge do payload bruto do dashboard passou a resolver contas pendentes, deficit de caixa e fluxo realizado em base caixa por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.392 helpers do view model financeiro final

- PM-06.392 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: o normalizador final do dashboard financeiro passou a resolver saldo inicial, entradas, despesas, resultado financeiro, deficit de caixa, contas pendentes e caixa disponivel por helpers locais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.391 helpers de valores do cashFlow do dashboard

- PM-06.391 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `cashFlow` principal do dashboard passou a resolver saldo inicial, entradas, saidas, contas pendentes, resultado financeiro e deficit de caixa por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.390 helpers de realizado do resultado financeiro

- PM-06.390 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resultado financeiro passou a resolver valor realizado e fonte do realizado por helpers locais, preservando validacao e fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.389 helpers locais de listas do response FCF

- PM-06.389 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: listas FCF de dividas, parcelas, movimentacoes e grupos de credor passaram a ser resolvidas por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.388 helpers locais de estatisticas FCF

- PM-06.388 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: estatisticas FCF de dividas, parcelas e movimentacoes passaram a ser resolvidas por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.387 helpers de valores de ledger e baixas canonicas

- PM-06.387 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: ledger e baixas canonicas passaram a resolver valores por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.386 helpers locais de valor contratado e parcelas de divida FCF

- PM-06.386 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: divida FCF passou a resolver valor contratado e quantidade de parcelas por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.385 helpers locais de listas legadas FCF

- PM-06.385 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: listas `installments`/`parcelas` e `debts`/`dividas` de grupos FCF passaram a ser resolvidas por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.384 helpers locais de numero e rotulo de parcela FCF

- PM-06.384 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: numero e rotulo de parcela FCF passaram a ser resolvidos por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.383 helpers locais de contagens de parcelas FCF

- PM-06.383 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: grupos FCF passaram a calcular quantidade total, pendente e vencida de parcelas via helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.382 helpers locais de subtotais devidos e pagos de grupos FCF

- PM-06.382 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: grupos FCF de divida e credor passaram a calcular subtotal devido e subtotal pago via helpers locais compartilhados, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.381 helper local de total devido de parcela FCF

- PM-06.381 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: total devido de parcela FCF passou a ser resolvido por helper local, preservando fallback antigo.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.380 helpers locais de totais de fluxo e resultado FCF

- PM-06.380 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: totais FCF de entradas/saidas e resultado financeiro passaram a ser resolvidos por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.379 helpers locais de totais pendentes e vencidos FCF

- PM-06.379 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: totais FCF de contas pendentes e vencidas passaram a ser resolvidos por helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.378 helpers locais de subtotais pendentes de grupos FCF

- PM-06.378 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: grupos FCF de divida e credor passaram a calcular subtotais pendentes via helpers locais compartilhados, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.377 helpers locais de valores de movimentacoes FCF

- PM-06.377 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: movimentacoes FCF passaram a calcular valor planejado, realizado e pendente de realizacao via helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.376 helpers locais de valores de parcelas FCF

- PM-06.376 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: parcelas FCF passaram a calcular valor pago, pendencia de pagamento e contas pendentes via helpers locais, preservando fallbacks antigos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.375 helper opcional de pendencia generica nas obrigacoes

- PM-06.375 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper opcional de pendencia generica preserva a ordem `pendingAmount`, `pendingValue`, `contas_pendentes` e reduz leitura direta de alias nos normalizadores.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.374 helpers opcionais de pendencia pagar/receber nas obrigacoes

- PM-06.374 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helpers opcionais de pendencia pagar/receber centralizam aliases e preservam valor ausente nos normalizadores de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.373 helper opcional de valor planejado nas obrigacoes

- PM-06.373 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper opcional de valor planejado preserva valor ausente em resumos e reduz leitura direta de `valor_previsto` nos normalizadores de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.372 helper opcional de valor pago nas obrigacoes

- PM-06.372 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper opcional de valor pago preserva valor ausente e reduz leitura direta de `valor_pago` nos normalizadores de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.371 helpers opcionais de realizado por origem e ledger

- PM-06.371 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helpers opcionais de realizado por origem/ledger preservam valor ausente e reduzem leitura direta de aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.370 helpers opcionais de pendencia por origem e ledger

- PM-06.370 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helpers opcionais de pendencia por origem/ledger preservam valor ausente e reduzem leitura direta de aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.369 helpers opcionais de excedente por origem e ledger

- PM-06.369 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helpers opcionais de excedente por origem/ledger preservam valor ausente e reduzem leitura direta de aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.368 helper canonico de excedente nos resumos de obrigacoes

- PM-06.368 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationSummaryAmountAliases()` usa helper canonico de excedente realizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.367 excedente realizado generico em helper canonico

- PM-06.367 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationItem()` usa helper canonico para realizado acima do previsto generico.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.366 pendencia tipada opcional em contas a receber

- PM-06.366 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeAccountsReceivable()` usa `getOptionalTypedPendingAmount()` com escopo `receber`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.365 pendencia tipada opcional para normalizadores

- PM-06.365 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalTypedPendingAmount()` permite normalizar pendencia sem forcar zero e centraliza aliases de pendencia.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.364 pendencia tipada ao converter obrigacoes em contas

- PM-06.364 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `obligationToAccountPayable()` usa `getTypedPendingAmount()` em vez de ler aliases de pendencia diretamente.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.363 pendencia canonica na auditoria do dashboard

- PM-06.363 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `ReconciliationAuditTable` usa `pendingAmount` como fallback canonico de pendencia de origem.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.362 exportador usa helper canonico de excedente

- PM-06.362 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` reutiliza helpers canonicos de excedente por origem/ledger e remove duplicacao local.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.361 excedente realizado de obrigacoes em helper canonico

- PM-06.361 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `FinancialObligationsView` usa helpers canonicos para valores de realizado acima do previsto por origem/ledger.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.360 payloads data sem casts

- PM-06.360 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `hasApiDataPayload()` centraliza guard de payload `{ data }` e remove casts dos unwrappers financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.359 detalhes de erro de obrigacoes sem cast

- PM-06.359 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `errorToMessage()` usa narrowing de `'details' in error` para ler detalhes do erro, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.358 filtro de status PM-03 sem cast

- PM-06.358 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `FinancialPm03EvidenceReviewer` valida filtro de status por type guard antes de aplicar o valor, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.357 diagnosticos divergentes de obrigacoes sem cast

- PM-06.357 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `FinancialObligationsView` valida chaves de diagnostico divergente antes de montar a lista tipada, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.356 opcoes de status do FCF sem cast

- PM-06.356 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `buildFilterOptions()` do FCF usa valor textual normalizado diretamente, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.355 status do header sem cast

- PM-06.355 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `DashboardHeader` valida status com `isDashboardStatus()` antes de gravar o filtro, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.354 labels de obrigacoes sem casts

- PM-06.354 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: mapas de labels de situacao, fluxo e tipo de obrigacao agora sao `Record` explicitos, sem casts.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.353 resumo de baixas canonicas sem cast generico

- PM-06.353 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeCanonicalFinancialSettlementsSummaryRecord()` usa accumulator tipado e deixa de usar helper generico com cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.352 grupos de fluxo de obrigacoes sem cast generico

- PM-06.352 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationCashFlowGroupSummaries()` normaliza `fco`, `fci` e `fcf` explicitamente, sem helper generico com cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.351 resultado financeiro do dashboard sem cast

- PM-06.351 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `mergeDashboardFinancialResult()` normaliza valores canonicos e aliases principais antes do retorno, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.350 fluxo de caixa do dashboard sem cast

- PM-06.350 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `mergeDashboardCashFlow()` normaliza valores canonicos e aliases principais antes do retorno, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.349 resumo do dashboard sem cast

- PM-06.349 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `mergeDashboardSummary()` normaliza contagens e variacao de receita com valores explicitos, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.348 opcoes de filtro do dashboard sem cast

- PM-06.348 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `mergeDashboardFilterOptions()` completa listas obrigatorias e aliases de filtro antes do retorno, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.347 diagnosticos de conciliacao sem casts

- PM-06.347 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationReconciliationSummaries()` tipa o item de diagnostico diretamente e elimina o cast final da atribuicao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.346 resumo vazio de obrigacoes sem cast

- PM-06.346 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `createEmptyFinancialObligationsSummary()` preenche `byCashFlowGroup` com `fco`, `fci` e `fcf` explicitamente, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.345 resumo de fluxo de caixa sem cast desnecessario

- PM-06.345 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeCashFlowGroupSummary()` reaproveita o tipo parcial aceito por `normalizeLedgerFlowSummary()`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.344 agregacao de obrigacoes por origem sem cast

- PM-06.344 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: agregacao `bySource` de obrigacoes agora usa accumulator tipado, sem cast final.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.343 agregacao de baixas por fonte de escrita sem cast

- PM-06.343 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: agregacao `byWriteModelSource` valida chaves de fonte de escrita antes de publicar, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.342 status de query de obrigacoes sem cast

- PM-06.342 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `toObligationsQuery()` deixou de converter `query.status` com cast antes do mapeamento por escopo.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.341 evidencia PM-03 sem casts de fonte/etapa

- PM-06.341 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizadores de fonte direta e etapa PM-03 validam valores por comparacao explicita, sem casts.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.340 status do dashboard sem casts

- PM-06.340 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeDashboardStatus()` retorna status permitido diretamente, sem casts.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.339 situacao de liquidacao de obrigacao sem cast

- PM-06.339 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationItem()` valida situacao de liquidacao antes de publicar `settlementStatus`/`situacao`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.338 grupo de fluxo de obrigacao sem cast

- PM-06.338 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationItem()` valida `fco`/`fci`/`fcf` antes de publicar `cashFlowGroup`/`fluxo`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.337 origem de obrigacao sem cast

- PM-06.337 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialObligationItem()` valida origem antes de publicar `source`/`origin`/`origem`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.336 fonte de escrita do contexto de baixa sem cast

- PM-06.336 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeCanonicalSettlementContext()` valida fonte de escrita antes de publicar `writeModelSource`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.335 grupo de fluxo da ultima baixa sem cast

- PM-06.335 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `latestSettlement.cashFlowGroup` valida `fco`/`fci`/`fcf` antes de publicar o contexto, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.334 fonte de escrita de baixa canonica sem cast

- PM-06.334 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeCanonicalFinancialSettlementItem()` valida fonte de escrita antes de publicar aliases, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.333 grupo de fluxo de baixa canonica sem cast

- PM-06.333 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeCanonicalFinancialSettlementItem()` valida `fco`/`fci`/`fcf` antes de publicar `cashFlowGroup`/`fluxo`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.332 tipo de baixa canonica sem cast

- PM-06.332 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeCanonicalFinancialSettlementItem()` valida `entrada`/`saida` antes de publicar `type`/`tipo`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.331 grupo de fluxo do ledger sem cast

- PM-06.331 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialLedgerItem()` valida `fco`/`fci`/`fcf` antes de publicar `cashFlowGroup`/`fluxo`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.330 tipo de lancamento do ledger sem cast

- PM-06.330 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialLedgerItem()` valida `entrada`/`saida` antes de publicar `type`/`tipo`, sem cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.329 callback do filtro de excedente realizado sem cast direto

- PM-06.329 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select `Acima do previsto` valida `all` ou filtro conhecido antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.328 callback do filtro de diagnostico sem cast direto

- PM-06.328 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select de diagnostico valida `all` ou diagnostico conhecido antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.327 callback do filtro de conciliacao sem cast direto

- PM-06.327 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select de conciliacao valida `all` ou status conhecido antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.326 callback do filtro de liquidacao sem cast direto

- PM-06.326 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select de liquidacao valida `all` ou status conhecido antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.325 callback do filtro de fluxo sem cast direto

- PM-06.325 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select de fluxo valida `all` ou grupo conhecido antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.324 callback do filtro de tipo de obrigacao sem cast direto

- PM-06.324 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select de tipo valida `pagar`/`receber` antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.323 callback do filtro de origem sem cast direto

- PM-06.323 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: select de origem valida `all` ou origem conhecida antes de chamar o handler, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.322 callback da base realizada sem cast direto

- PM-06.322 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: callback `Origem`/`Ledger` valida `originState`/`ledger` antes de atualizar estado, sem cast direto.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.321 lista de origens de obrigacoes sem cast

- PM-06.321 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financialObligationSourceValues` virou lista explicita e tipada, sem `Object.keys` com cast.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.320 label de capacidade por origem sem cast

- PM-06.320 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `formatCapabilitySourceLabel()` valida origem conhecida antes de consultar capacidades, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.319 helper de query inicial de obrigacoes sem cast

- PM-06.319 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `queryValueIn()` valida valores por comparacao direta com as opcoes recebidas, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.318 label contextual de status de liquidacao sem cast

- PM-06.318 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `contextualSettlementStatusLabel()` valida status conhecidos antes de consultar labels, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.317 helper de status do dashboard sem cast

- PM-06.317 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `isDashboardStatus()` valida status conhecidos por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.316 helper de periodo do dashboard sem cast

- PM-06.316 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `isDashboardPeriod()` valida periodos canonicos por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.315 helper de grupo de fluxo sem cast

- PM-06.315 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationCashFlowGroupValue()` valida `fco`/`fci`/`fcf` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.314 helper de fonte de escrita sem cast

- PM-06.314 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationWriteModelSourceValue()` valida `legacyAdapterSynced`/`canonicalFirst` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.313 helper de base de realizado sem cast

- PM-06.313 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationRealizedAmountBasisValue()` valida `originState`/`ledger` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.312 helper de filtro de excedente realizado sem cast

- PM-06.312 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationRealizedAbovePlannedFilterValue()` valida `with`/`without` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.311 helper de diagnostico de conciliacao sem cast

- PM-06.311 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationReconciliationDiagnosisValue()` valida diagnosticos canonicos por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.310 helper de status de conciliacao sem cast

- PM-06.310 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationReconciliationStatusValue()` valida `conciliado`/`divergente` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.309 helper de status de liquidacao sem cast

- PM-06.309 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationSettlementStatusValue()` valida status canonicos por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.308 helper de origem de obrigacao sem cast

- PM-06.308 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialObligationSourceValue()` valida fontes canonicas por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.307 helper de tipo de lancamento sem cast

- PM-06.307 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `getOptionalFinancialLedgerTypeValue()` valida `entrada`/`saida` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.306 helper de origem FCF sem cast

- PM-06.306 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialFinancingSourceType()` valida `manual`/`divida_automatica` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.305 helper de fluxo FCF sem cast

- PM-06.305 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `normalizeFinancialFinancingFlowType()` valida `entrada`/`saida` por comparacao explicita, sem cast interno.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.304 origem de item canonico validada

- PM-06.304 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de baixas canonicas publicam `source` apenas quando a origem passa pelo helper canonico, preservando `sourceLabel` textual.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.303 origem de alocacao canonica validada

- PM-06.303 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: alocacoes de baixas canonicas publicam `source` apenas quando a origem passa pelo helper canonico, preservando `sourceLabel` textual.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.302 IDs de filtros de baixas canonicas validados

- PM-06.302 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros normalizados de baixas canonicas validam `contractId`, `eventId` e `clientId` por inteiro positivo antes de espelhar aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.301 IDs de obrigacoes validados

- PM-06.301 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros normalizados de obrigacoes validam `contractId`, `eventId` e `clientId` por inteiro positivo antes de espelhar aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.300 IDs dimensionais do ledger validados

- PM-06.300 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros normalizados do ledger validam `contractId`, `eventId` e `clientId` por inteiro positivo antes de espelhar aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.299 IDs de origem do ledger validados

- PM-06.299 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros normalizados do ledger validam `sourceId`/`source_id`/`originId`/`origin_id` por inteiro positivo antes de espelhar aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.298 sourceId do ledger validado

- PM-06.298 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query do ledger valida `sourceId`/`source_id`/`originId`/`origin_id` por inteiro positivo antes de enviar consulta.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.297 IDs FCF validados

- PM-06.297 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query FCF valida `contractId`, `eventId` e `clientId` por inteiro positivo antes de enviar consulta.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.296 IDs de baixas canonicas validados

- PM-06.296 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query de baixas canonicas valida `contractId`, `eventId` e `clientId` por inteiro positivo antes de enviar consulta.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.295 periodo de baixas canonicas validado

- PM-06.295 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query de baixas canonicas valida `period` com `isDashboardPeriod()` antes de enviar consulta.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.294 periodo FCF validado

- PM-06.294 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: query FCF valida `period` com `isDashboardPeriod()` antes de publicar periodo; `periodo_rapido` segue como alias transicional.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.293 tipo de fluxo FCF validado

- PM-06.293 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: movimentacoes FCF validam `flowType`/`tipo_fluxo` com helper canonico antes de publicar `entrada`/`saida`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.292 diagnostico agregado de conciliacao validado

- PM-06.292 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resumo por diagnostico de conciliacao valida `reconciliationDiagnosis`/`diagnosticoConciliacao` com helper canonico antes de publicar chaves em `byReconciliationDiagnosis`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.291 fallback mock com base validada

- PM-06.291 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: fallback mock de obrigacoes valida `realizedAmountBasis`/`baseRealizado` com helper canonico antes de montar resposta vazia.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.258 aliases de indicadores financeiros espelhados

- PM-06.258 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de indicadores financeiros faz `title`, `value` e `label` espelharem `indicatorName`, `indicatorValue` e `indicatorDetail` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.257 aliases de origem em resumos de obrigacoes espelhados

- PM-06.257 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de resumos por origem de obrigacoes faz `origin` e `origem` espelharem `source` normalizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.256 aliases de contas a receber do dashboard espelhados

- PM-06.256 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de contas a receber do dashboard faz alias de cliente, pendencia e valor planejado espelharem `clientName`, `pendingAmount` e `plannedAmount` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.255 aliases de contas a pagar do dashboard espelhados

- PM-06.255 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de contas a pagar do dashboard faz aliases de pendencia, valor planejado e realizado espelharem `pendingAmount`, `plannedAmount` e `paidAmount` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.254 aliases de metas financeiras espelhados

- PM-06.254 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de metas financeiras faz `current` e `target` espelharem `currentValue` e `targetValue` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.253 aliases de evolucao de caixa espelhados

- PM-06.253 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de evolucao de caixa faz `accumulatedFinancialResult` e `value` espelharem `accumulatedFinancialResultAmount` normalizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.252 aliases de resumo por contrato espelhados

- PM-06.252 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de resumo por contrato faz `service`, `contracts`, `contractCount` e `value` espelharem `serviceName`, `operationalEventsCount` e `revenueAmount` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.251 aliases de receita por servico espelhados

- PM-06.251 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de receita por servico faz `service` e `revenue` espelharem `serviceName` e `revenueAmount` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.250 alias de valor em categorias de despesa espelhado

- PM-06.250 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de categorias de despesa faz `value` espelhar `expenseAmount` normalizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.249 aliases de grafico receita/despesa espelhados

- PM-06.249 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de grafico receita/despesa faz `receitas` e `despesas` espelharem `revenueAmount` e `expenseAmount` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.248 aliases de disponibilidade de caixa espelhados

- PM-06.248 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de disponibilidade de caixa faz `aplicavel`, `cashAvailableAmount`, `caixaDisponivel` e `saldoCaixaDisponivel` espelharem `applicable` e `availableCashAmount` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.247 alias de codigo de grupo de fluxo espelhado

- PM-06.247 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de grupo de fluxo faz `codigo` espelhar `code` normalizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.246 aliases de resumo de fluxo do ledger espelhados

- PM-06.246 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de resumo de fluxo do ledger faz `entradas`, `saidas`, `resultadoFinanceiro` e `resultado_financeiro` espelharem montantes canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.245 alias textual de opcao de credor espelhado

- PM-06.245 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de opcao de credor faz `credor_nome` espelhar `creditorName` normalizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.244 aliases de opcoes simples de escolha espelhados

- PM-06.244 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de opcoes simples de escolha faz `valor` e `rotulo` espelharem `value` e `label` normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.243 aliases de filtro de evento do dashboard espelhados

- PM-06.243 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de filtro de evento do dashboard faz `value`, aliases de evento, contrato, cliente, nomes e datas espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.242 aliases de filtro de contrato do dashboard espelhados

- PM-06.242 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de filtro de contrato do dashboard faz `value`, aliases de contrato, label operacional, cliente e nomes espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.241 aliases de opcoes de cliente espelhados

- PM-06.241 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de opcoes de cliente faz `value`, `cliente_id`, `cliente_nome`, `name` e `nome` espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.240 aliases de opcoes de evento operacional espelhados

- PM-06.240 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de opcoes de evento operacional faz `value`, aliases de evento, contrato, cliente, descricao e datas espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.239 aliases de opcoes de contrato operacional espelhados

- PM-06.239 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de opcoes de contrato operacional faz `value` e aliases de contrato, cliente, nome e descricao espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.238 alias textual de credores FCF espelhado

- PM-06.238 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de resposta de credores FCF deriva `credores` da lista canonica normalizada `creditors`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.237 aliases de dimensoes operacionais auxiliares espelhados

- PM-06.237 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helpers auxiliares de dimensoes operacionais e worklist de conciliacao de obrigacoes fazem aliases de contrato, evento e cliente espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.236 aliases financeiros de resumos de obrigacoes espelhados

- PM-06.236 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de resumos de obrigacoes faz aliases financeiros de previstos, realizados, pagos, pendentes, origem, ledger e diferenca espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.235 aliases financeiros de itens de obrigacoes espelhados

- PM-06.235 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de itens de obrigacoes faz aliases financeiros de previstos, realizados, pagos, pendentes, origem, ledger, diferenca e conciliacao espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.234 aliases de identidade de obrigacoes espelhados

- PM-06.234 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de itens de obrigacoes faz aliases de tipo, origem, referencia, datas, fluxo, natureza, situacao, fonte de leitura, cliente, contrato e evento espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.233 aliases de alocacoes de baixas canonicas espelhados

- PM-06.233 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de alocacoes de baixas canonicas faz aliases de cliente, contrato e evento espelharem campos canonicos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.232 aliases de baixas canonicas espelhados

- PM-06.232 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de baixas canonicas faz aliases legados espelharem campos canonicos normalizados de tipo, fluxo, natureza, valores, descricao, fonte de escrita, origem e dimensoes operacionais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.231 aliases de itens do ledger espelhados

- PM-06.231 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de itens do ledger faz aliases legados espelharem campos canonicos normalizados de data, tipo, fluxo, natureza, valores, descricao, origem e dimensoes operacionais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.230 aliases acima do previsto em obrigacoes espelhados

- PM-06.230 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizadores de itens e resumo de obrigacoes fazem aliases de excedente/acima do previsto espelharem `realizedAbovePlannedAmount`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.229 aliases de grupos por credor FCF espelhados

- PM-06.229 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de grupos por credor FCF faz aliases legados espelharem campos canonicos normalizados de credor, subtotais, contagens e dividas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.228 aliases de grupos de divida FCF espelhados

- PM-06.228 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de grupos de divida FCF faz aliases legados espelharem campos canonicos normalizados de divida, credor, descricao, subtotais, contagens e parcelas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.227 aliases de movimentacoes FCF espelhados

- PM-06.227 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de movimentacoes FCF faz aliases legados espelharem campos canonicos normalizados de descricao, categoria, fluxo, valores, datas, status, origem, divida e atraso.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.226 aliases de parcelas FCF espelhados

- PM-06.226 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de parcelas FCF faz aliases legados espelharem campos canonicos normalizados de divida, credor, rotulo, vencimento, valores, disponibilidade, status e atraso.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.225 aliases de dividas FCF espelhados

- PM-06.225 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizador de dividas FCF faz aliases legados espelharem campos canonicos normalizados de identidade, descricao, tipo, status, data, valor e contagem.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.224 creditor textual priorizado na query FCF

- PM-06.224 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: service FCF prioriza `creditor` antes de `credor` ao montar o filtro textual, mas continua enviando `credor` ao backend por compatibilidade.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.223 filtro textual de credor FCF canonico

- PM-06.223 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: response normalizado de FCF espelha `creditor`/`credor` quando houver filtro textual de credor, mantendo `creditorId` como preferencial para credores cadastrados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.222 helper de origem inicial FCF simplificado

- PM-06.222 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: helper de origem inicial FCF recebe o valor ja resolvido pela tabela centralizada de aliases, mantendo `automaticFromDebt` como fallback.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.221 aliases de query inicial FCF centralizados

- PM-06.221 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela FCF centraliza aliases de query inicial em helper local e prefere `creditorId`, `type` e `sourceType` antes dos nomes legados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.220 override canonico de periodo no hook FCF

- PM-06.220 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook FCF encaminha `period` canonico ao service quando recebido e preserva `periodo_rapido` como alias legado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.219 alias de credor consolidado no hook FCF

- PM-06.219 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook FCF consolida `credor` em `creditor` antes de chamar o service, que segue espelhando o alias na query enviada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.218 aliases legados explicitos no hook FCF

- PM-06.218 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook FCF marca aliases de tipo e origem como `legacy...` antes de consolidar os overrides canonicos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.217 deprecations acima do previsto canonicas

- PM-06.217 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: comentarios de depreciação de aliases de excedente realizado passam a apontar para `realizedAbovePlannedAmount`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.216 busca inicial de obrigacoes centralizada

- PM-06.216 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela de obrigacoes usa helper unico para inicializar `searchDraft` e `searchFilter` a partir de `search`/`busca`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.215 aliases de query inicial de obrigacoes centralizados

- PM-06.215 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela de obrigacoes centraliza chaves canônicas/legadas de query inicial em `financialObligationInitialQueryKeys`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.214 prioridade canonica acima do previsto

- PM-06.214 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela, CSV e service de obrigacoes preferem `realizedAbovePlannedAmount` antes de aliases legados quando ambos existem.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.213 aliases legados explicitos no hook de obrigacoes

- PM-06.213 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook de obrigacoes marca `overRealized` e `excedenteRealizado` como aliases locais legados antes de consolidar `realizedAbovePlanned`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.212 semantica canonica acima do previsto

- PM-06.212 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: metadados semanticos de obrigacoes incluem `realizedAbovePlannedAmount`, com a UI preferindo a chave canonica e mantendo fallback legado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.211 variaveis canonicas no service de obrigacoes

- PM-06.211 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: normalizadores de item e resumo de obrigacoes usam variaveis locais canonicas para realizado acima do previsto, mantendo todos os aliases de response.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.210 valor local canonico acima do previsto

- PM-06.210 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela de obrigacoes usa `realizedAbovePlannedAmount` como propriedade local de base calculada, mantendo payloads/metadados publicados sem alteracao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.209 helpers canonicos na tela de obrigacoes

- PM-06.209 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela de obrigacoes renomeia helpers e variaveis locais de realizado acima do previsto, mantendo campos legados apenas como fallback de leitura.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.208 helpers canonicos no CSV de obrigacoes

- PM-06.208 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: CSV de obrigacoes renomeia helpers internos de realizado acima do previsto, mantendo campos legados apenas como fallback de leitura.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.207 export canonico de opcoes acima do previsto

- PM-06.207 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: constantes de obrigacoes passam a exportar `financialObligationRealizedAbovePlannedFilterOptions`, mantendo `financialObligationOverRealizedFilterOptions` como alias compativel.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.206 handlers canonicos do filtro acima do previsto

- PM-06.206 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela de obrigacoes renomeia handlers do filtro para `handleRealizedAbovePlannedChange`/`handleShowRealizedAbovePlanned` e usa alias local canonico para a constante de opcoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.205 estado canonico do filtro acima do previsto

- PM-06.205 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: tela de obrigacoes renomeia estado interno `overRealizedFilter` para `realizedAbovePlannedFilter`, mantendo aliases apenas como fallback de URL.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.204 overrides canonicos no hook de obrigacoes

- PM-06.204 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook de obrigacoes consolida aliases recebidos em constantes efetivas canonicas antes de montar o objeto de query.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.203 limite explicito na lista de obrigacoes

- PM-06.203 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: lista de obrigacoes passa a aplicar `FINANCIAL_OBLIGATIONS_LIST_LIMIT` por helper dedicado, preservando `limit` explicito do chamador.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.202 aliases no hook de obrigacoes

- PM-06.202 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook de obrigacoes passa a resolver aliases de conciliacao, base de realizado, fonte de dados, tipo, origem, fluxo, situacao e busca antes de montar o request.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.201 hook FCF com overrides canonicos

- PM-06.201 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hook FCF passa a montar overrides internos com `creditorId`, `type` e `sourceType` normalizados, sem duplicar aliases que o service ja espelha na query enviada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.200 aliases de escopo na query FCF

- PM-06.200 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: overrides de query FCF passam a aceitar aliases para periodo, datas, contrato, evento e cliente, resolvendo tudo antes de montar a requisicao read-only.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.199 alias de base realizada no fallback mock

- PM-06.199 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: fallback mock de obrigacoes passa a resolver `realizedAmountBasis` e `baseRealizado` antes de montar o response vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.198 aliases de query de baixas canonicas

- PM-06.198 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: overrides de query de baixas canonicas passam a aceitar aliases para datas, origem, tipo, fluxo, contrato, evento, cliente, fonte de escrita e busca, com montagem canonica centralizada antes de enviar a requisicao ao backend.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.197 aliases de query de obrigacoes

- PM-06.197 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: overrides de query de obrigacoes passam a aceitar aliases para fonte de dados, tipo, origem, fluxo, situacao, conciliacao, base de realizado, excedente e busca, resolvendo tudo para os campos canonicos enviados ao backend.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.196 aliases de query do ledger

- PM-06.196 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: overrides de query do ledger passam a aceitar aliases para fluxo, tipo, natureza, origem, source, ids, detalhe de source e busca, resolvendo tudo para os campos canonicos enviados ao backend.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.195 aliases de itens do ledger

- PM-06.195 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens do ledger passam a normalizar nomes canonicos e aliases para datas, tipo, fluxo, natureza, valores, descricao, origem, cliente, contrato e evento.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.194 aliases de filtros do ledger

- PM-06.194 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros de ledger passam a resolver e espelhar nomes canonicos e aliases para datas, contrato, evento, cliente, fluxo, tipo, natureza, origem, source, ids, detalhe de source e busca.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.193 metadados ausentes de ledger

- PM-06.193 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `meta` ausente no payload de ledger passa a ser tratado como metadados minimos de backend durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.192 paginacao ausente de ledger

- PM-06.192 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `pagination` ausente no payload de ledger passa a ser tratado como pagina vazia durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.191 filtros ausentes de ledger

- PM-06.191 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `filters` ausente no payload de ledger passa a ser tratado como filtros vazios durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.190 resumo ausente de ledger

- PM-06.190 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `summary` ausente no payload de ledger passa a ser tratado como totais zerados durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.189 itens ausentes de ledger

- PM-06.189 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `items` ausente no payload de ledger passa a ser tratado como lista vazia durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.188 resumo ausente de obrigacoes

- PM-06.188 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `summary` ausente no payload de obrigacoes passa a ser tratado como resumo zerado durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.187 metadados ausentes de obrigacoes

- PM-06.187 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `meta` ausente no payload de obrigacoes passa a ser tratado como metadados minimos de backend durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.186 opcoes ausentes de obrigacoes

- PM-06.186 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `filterOptions` ausente no payload de obrigacoes passa a ser tratado como listas vazias minimas durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.185 paginacao ausente de obrigacoes

- PM-06.185 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `pagination` ausente no payload de obrigacoes passa a ser tratado como pagina vazia durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.184 filtros ausentes de obrigacoes

- PM-06.184 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `filters` ausente no payload de obrigacoes passa a ser tratado como filtros vazios durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.183 agregados ausentes de obrigacoes

- PM-06.183 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `byCashFlowGroup` e `bySource` ausentes no payload de obrigacoes passam a ser tratados como mapas vazios durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.182 itens ausentes de obrigacoes

- PM-06.182 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `items` ausente no payload de obrigacoes passa a ser tratado como lista vazia durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.181 resumo ausente de baixas canonicas

- PM-06.181 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `summary` ausente no payload de baixas canonicas passa a ser tratado como resumo zerado durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.180 metadados ausentes de baixas canonicas

- PM-06.180 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `meta` ausente no payload de baixas canonicas passa a ser tratado como metadados padrao read-only durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.179 paginacao ausente de baixas canonicas

- PM-06.179 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `pagination` ausente no payload de baixas canonicas passa a ser tratado como pagina vazia durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.178 filtros ausentes de baixas canonicas

- PM-06.178 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `filters` ausente no payload de baixas canonicas passa a ser tratado como filtros vazios durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.177 opcoes ausentes de baixas canonicas

- PM-06.177 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `filterOptions` ausente no payload de baixas canonicas passa a ser tratado como opcoes vazias durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.176 colecoes de baixas canonicas

- PM-06.176 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `items` e `allocations` ausentes no payload de baixas canonicas passam a ser tratados como listas vazias durante a normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.175 envelope de liquidacao de obrigacoes

- PM-06.175 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: retorno de liquidacao passou a aceitar envelope `data` ou payload direto, centralizando a normalizacao do resultado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.174 contexto canonico de liquidacao

- PM-06.174 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contexto `canonicalSettlement` retornado pela liquidacao passou a normalizar flags, contagens, valores e `latestSettlement`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.173 metadados de baixas canonicas

- PM-06.173 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: metadados de baixas canonicas passaram a normalizar `generatedAt`, `source`, `readOnly`, `currency`, `dateBasis`, `model` e `allocationModel`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.172 paginacao de baixas canonicas

- PM-06.172 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: paginacao de baixas canonicas passou a normalizar `limit`, `offset`, `total` e `hasMore`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.171 opcoes de filtro de baixas canonicas

- PM-06.171 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes de filtro de baixas canonicas passaram a normalizar contratos, eventos, clientes, tipos, fluxos, origens e fontes de escrita.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.170 resumo de baixas canonicas

- PM-06.170 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: resumo de baixas canonicas passou a normalizar totais gerais, grupos por fluxo, por origem e por fonte de escrita.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.169 itens de baixas canonicas

- PM-06.169 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens e alocacoes de baixas canonicas passaram a espelhar aliases de valores, fonte de escrita, origem, labels e dimensoes operacionais.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.168 filtros de baixas canonicas

- PM-06.168 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: respostas de baixas canonicas passaram a espelhar filtros canonicos e aliases de periodo, contrato, evento, cliente, origem, tipo, fluxo, natureza, fonte de escrita e busca.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.167 canonicalSettlement no retorno de liquidacao

- PM-06.167 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `settleFinancialObligation()` passou a espelhar `canonicalSettlement` e `settlement` no retorno da liquidacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.166 item normalizado no retorno de liquidacao

- PM-06.166 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `settleFinancialObligation()` passou a devolver `response.item` normalizado pelo mesmo contrato da leitura de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.165 labels canonicos na worklist de conciliacao

- PM-06.165 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: worklist de conciliacao passou a preencher labels canonicos de diagnostico e origem com fallback dos campos ja normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.164 labels canonicos em itens de obrigacoes

- PM-06.164 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a preencher labels canonicos de origem, detalhe de origem e status com fallback dos campos ja normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.163 origem em agregados bySource de obrigacoes

- PM-06.163 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: agregados `bySource` de obrigacoes passaram a declarar e espelhar `source`, `origin`, `origem` e label com fallback pela chave do grupo.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.162 aliases financeiros completos em agregados de obrigacoes

- PM-06.162 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: agregados de obrigacoes passaram a declarar e espelhar aliases de planejado, realizado, pago, pendente, origem, ledger e diferenca realizada sem alterar totais financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.161 aliases de excedente em agregados de obrigacoes

- PM-06.161 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: agregados de obrigacoes passaram a espelhar aliases de excedente realizado, origem e ledger em resumo geral, grupos e worklist sem alterar totais financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.160 aliases financeiros em itens de obrigacoes

- PM-06.160 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a espelhar aliases financeiros de valores planejados, realizados, pendentes, excedentes, origem e ledger sem alterar calculos financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck`, `build` e `git diff --check` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.159 diagnostico em agregados de conciliacao

- PM-06.159 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: agregados de conciliacao por diagnostico passaram a declarar e espelhar diagnostico/label canonicos e aliases sem alterar totais financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.158 dimensoes operacionais na worklist de conciliacao

- PM-06.158 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: worklist de conciliacao de obrigacoes passou a declarar e espelhar aliases de contrato e cliente sem alterar totais financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.157 read_model_source em itens de obrigacoes

- PM-06.157 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a declarar e espelhar `read_model_source` como alias transicional de `readModelSource`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.156 situacao em itens de obrigacoes

- PM-06.156 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a declarar e espelhar `situacao` como alias transicional de `settlementStatus`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.155 dimensoes operacionais em itens de obrigacoes

- PM-06.155 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a declarar e espelhar aliases de cliente, contrato e evento sem alterar calculos financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.154 source_detail em itens de obrigacoes

- PM-06.154 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a declarar e espelhar `source_detail` como alias transicional de `sourceDetail`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.153 itens de obrigacoes com aliases de identidade/status

- PM-06.153 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: itens de obrigacoes passaram a espelhar aliases de identidade/status sem alterar calculos financeiros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.152 aliases de rotulo em filtros genericos

- PM-06.152 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros genericos de contrato/evento passaram a espelhar `contrato_operacional_label` e `evento_label` a partir do rotulo canonico normalizado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.151 envelopes de opcoes FCF espelhados

- PM-06.151 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: opcoes FCF normalizadas passaram a reutilizar os mesmos conjuntos em envelopes canonicos e aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.150 envelopes de filtros genericos espelhados

- PM-06.150 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros genericos vazios e normalizados passaram a espelhar envelopes canonicos e aliases (`contracts/contratos`, `events/eventos`, `clients/clientes`).
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.149 contratos/eventos em filtros genericos com aliases espelhados

- PM-06.149 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros genericos de contrato/evento passaram a aceitar e espelhar aliases legados como `contratos`, `eventos`, `contrato`, `evento_nome` e `data_inicio`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.148 clientes em filtros genericos com aliases espelhados

- PM-06.148 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: filtros genericos de cliente passaram a aceitar e espelhar aliases `clientes`, `cliente_id`, `cliente_nome` e `nome`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.147 contexto PM-03 com texto explicito

- PM-06.147 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: linhas de clipboard e resumo PM-03 passaram a usar textos explicitos quando o contexto vier vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.146 comparacoes KPI ausentes com texto explicito

- PM-06.146 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: variacoes KPI sem base passaram a usar `Comparacao nao informada` em tela, exportacao e normalizacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.145 placeholders genericos com texto explicito

- PM-06.145 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contexto operacional, ledger, busca e categoria ausentes passaram a usar textos explicitos no Next.js.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.144 descricoes ausentes com texto explicito

- PM-06.144 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: exports e tabelas financeiras passaram a usar mensagens explicitas para descricao/nome/identificacao ausentes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.143 contexto operacional sem placeholder antigo

- PM-06.143 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` e `financial-obligations-view.tsx` passaram a usar textos explicitos para contrato/evento ausentes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.142 opcoes operacionais com aliases legados espelhados

- PM-06.142 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `lib/types/dashboard.ts` e `financial-dashboard-service.ts` passaram a aceitar e espelhar aliases legados reais nas opcoes operacionais de contrato/evento FCF/FCI.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.141 textos auxiliares sem marcador vazio

- PM-06.141 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-read-model.ts` e `pm03-evidence.ts` passaram a usar textos explicitos quando fonte/motivo/periodo parcial vierem vazios.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.140 datas FCF sem marcador vazio

- PM-06.140 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a exibir `Data nao informada` no helper visual de data FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.139 opcoes de cliente FCF canonicas

- PM-06.139 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ganhou normalizacao para opcoes de cliente FCF, preservando alias `clientes`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.138 opcoes operacionais FCF canonicas

- PM-06.138 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ganhou normalizacao para opcoes operacionais FCF de contrato/evento, preservando aliases espelhados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.137 dimensoes FCF canonicas

- PM-06.137 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ganhou normalizacao comum para dimensoes operacionais FCF de contrato/evento/cliente, preservando aliases espelhados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.136 dividas FCF canonicas

- PM-06.136 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ampliou a normalizacao canonica para dividas FCF de topo, preservando aliases espelhados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.135 grupos FCF canonicos

- PM-06.135 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ganhou normalizacao canonica para grupos FCF de credor/divida e parcelas aninhadas, preservando aliases espelhados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.134 movimentacoes FCF canonicas

- PM-06.134 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ganhou normalizacao canonica para movimentacoes FCF de topo, preservando aliases espelhados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.133 parcelas FCF canonicas

- PM-06.133 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` ganhou normalizacao canonica para parcelas FCF de topo, preservando aliases espelhados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.132 identidades canonicas em contas derivadas

- PM-06.132 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` passou a preservar `clientId`, `clientName`, `contractId`, `eventId` e `eventNumber` ao derivar contas a pagar a partir de obrigacoes financeiras.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.131 evidencias PM-03 sem texto vazio

- PM-06.131 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-pm03-evidence-summary.tsx` passou a usar fallback para sequencia, periodo e data de geracao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.130 acao FCF sem texto vazio

- PM-06.130 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a exibir `Sem acao` quando a parcela FCF nao possui link operacional.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.129 textos auxiliares de obrigacoes sem vazio

- PM-06.129 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback textual em `textValue()` e no resumo por diagnostico.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.128 detalhe de obrigacoes com texto nao vazio

- PM-06.128 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback para descricao, origem, fluxo, tipo de obrigacao e lancamentos vinculados no detalhe lateral.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.127 lista de obrigacoes com texto nao vazio

- PM-06.127 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback para descricao, contexto operacional, origem, fluxo e vencimento na lista principal de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.126 indicadores financeiros com texto nao vazio

- PM-06.126 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-indicator-card.tsx` passou a usar fallback para valor e detalhe quando o payload vier vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.125 contas do dashboard com texto nao vazio

- PM-06.125 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `accounts-payable-table.tsx` passou a usar fallback para descricao e vencimento; `accounts-receivable-table.tsx` passou a usar fallback para vencimento.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.124 auditoria de conciliacao com texto nao vazio

- PM-06.124 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-view.tsx` passou a usar fallback para descricao da obrigacao, contexto operacional e origem na auditoria de conciliacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.123 tabelas FCF com texto nao vazio

- PM-06.123 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a usar fallback para descricao, credor, tipo, parcela, fluxo e origem nas tabelas FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.122 badges de status FCF com texto nao vazio

- PM-06.122 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a usar fallback entre `statusLabel` e `status`, com texto visual padrao quando ambos vierem vazios.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.121 filtros no CSV de obrigacoes com texto nao vazio

- PM-06.121 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a exportar periodo completo, selecoes "Todos" e busca "Sem busca" quando filtros de obrigacoes nao estiverem aplicados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.120 CSV consolidado do dashboard com texto nao vazio

- PM-06.120 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar fallback para periodo, categorias, servicos, contas a pagar/receber, contratos e metas financeiras no CSV consolidado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.119 filtros no CSV FCF com texto nao vazio

- PM-06.119 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a exportar periodo completo e selecoes "Todos" para contrato, evento, cliente e status quando filtros nao estiverem aplicados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.118 identificadores no CSV FCF com texto nao vazio

- PM-06.118 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar fallback para descricao, credor, tipo/fluxo, data, status, contrato, evento, cliente, origem e categoria em dividas, parcelas, movimentacoes e grupos de credor.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.117 identificadores no CSV com texto nao vazio

- PM-06.117 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar fallback para descricao, origem, fluxo, vencimento, contrato, evento, cliente e escopo nos CSVs de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.116 status de leitura no CSV com texto nao vazio

- PM-06.116 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar fallback para leitura solicitada, leitura efetiva e label de status de leitura no CSV.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.115 conciliacao no CSV com texto nao vazio

- PM-06.115 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar fallback para diagnostico e titulo de orientacao de conciliacao nas linhas exportadas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.114 status de obrigacoes no CSV com texto nao vazio

- PM-06.114 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar fallback normalizado para status de obrigacoes no contexto de filtros e nas linhas exportadas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.113 status de obrigacoes com texto nao vazio

- PM-06.113 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar `settlementStatusDisplayLabel` com fallback visual para status de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.112 detalhes de obrigacoes sem espacos vazios

- PM-06.112 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a tratar strings compostas apenas por espacos como valor ausente em `textValue`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.111 metricas de obrigacoes com texto nao vazio

- PM-06.111 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a limpar label/descricao em `SummaryMetric` e ocultar tooltip quando a descricao vier vazia.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.110 badge de escopo de obrigacoes com texto nao vazio

- PM-06.110 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a montar o escopo com labels normalizados e ocultar o badge quando nao houver texto valido.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.109 fila de divergencias com texto nao vazio

- PM-06.109 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback para badge de tipo, label de diagnostico e titulo de orientacao na fila de divergencias.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.108 badge de status de leitura com texto nao vazio

- PM-06.108 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback em `title` e `displayText` do badge de status de leitura.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.107 alerta de fallback de leitura com texto nao vazio

- PM-06.107 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback no alerta quando label ou detalhe do status de leitura vierem vazios.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.106 conciliacao de obrigacoes com orientacao nao vazia

- PM-06.106 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback para titulo/descricao de orientacao e label de resumo de diagnostico de conciliacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.105 tabela de obrigacoes com descricao e fluxo nao vazios

- PM-06.105 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback para descricao vazia e label de fluxo vazio na lista principal de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.104 grafico de evolucao com periodo nao vazio

- PM-06.104 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `cash-evolution-chart.tsx` passou a normalizar `month` com fallback antes de entregar dados ao Recharts.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.103 grafico receitas x despesas com periodo nao vazio

- PM-06.103 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `revenue-expense-chart.tsx` passou a normalizar `month` com fallback antes de entregar dados ao Recharts.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.102 grafico de despesas com categoria nao vazia

- PM-06.102 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `expense-category-chart.tsx` passou a usar fallback visual quando `categoryName` vier vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.101 widgets de servico com nome nao vazio

- PM-06.101 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `service-revenue-table.tsx` e `contract-summary-widget.tsx` passaram a usar fallback visual para `serviceName` vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.100 indicadores financeiros com textos nao vazios

- PM-06.100 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-indicator-card.tsx` passou a usar fallback visual para nome, valor e detalhe vazios.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.99 metas financeiras com nome e status defensivos

- PM-06.99 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-goals-widget.tsx` passou a usar nome padrao para `goalName` vazio e configuracao padrao para status sem mapeamento.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.98 tabelas de contas com status defensivo

- PM-06.98 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `accounts-payable-table.tsx` e `accounts-receivable-table.tsx` passaram a usar fallback visual caso o status recebido nao encontre mapeamento.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.97 contas a receber com vencimento nao vazio

- PM-06.97 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `accounts-receivable-table.tsx` passou a higienizar `dueDate` e usar fallback visual/chave estavel quando ausente.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.96 CSV do dashboard com variacao de KPI nao vazia

- PM-06.96 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a higienizar `changeDescription` antes de compor a variacao de KPI exportada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.95 KPIs do dashboard com label de variacao nao vazio

- PM-06.95 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-view.tsx` passou a usar fallback quando `changeDescription` vier vazio com variacao numerica valida.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.94 auditoria de conciliacao com textos nao vazios

- PM-06.94 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-view.tsx` passou a exibir fallback para descricao e contexto operacional vazios na tabela de auditoria de conciliacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.93 tabelas FCF com contexto nao vazio

- PM-06.93 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a usar fallback nos subtitulos de contexto de dividas, parcelas e movimentacoes FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.92 cards de credores FCF com nome nao vazio

- PM-06.92 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a exibir fallback higienizado quando o nome do credor FCF estiver ausente.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.91 selects FCF com opcoes nao vazias

- PM-06.91 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a higienizar `value` e `label` das opcoes de credor, tipo e origem antes dos selects FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.90 acao operacional de obrigacoes com rotulo nao vazio

- PM-06.90 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a higienizar o rotulo da acao operacional de origem no sheet e nos atributos acessiveis da tabela.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.89 lancamentos vinculados de obrigacoes com textos nao vazios

- PM-06.89 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a higienizar data, fluxo, tipo e natureza dos lancamentos ledger vinculados no sheet de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.88 detalhe de obrigacoes com textos nao vazios

- PM-06.88 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a higienizar titulo, origem, fluxo, natureza, detalhe de origem e datas do sheet de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.87 CSV do dashboard com textos operacionais higienizados

- PM-06.87 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar `exportText()` nos textos analiticos e operacionais do CSV do dashboard.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.86 CSV do dashboard com periodo higienizado

- PM-06.86 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a calcular `periodLabel` higienizado uma vez e reutiliza-lo nas linhas do CSV do dashboard e no nome do arquivo.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.85 metadados do dashboard nao vazios

- PM-06.85 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` passou a ignorar strings vazias em `generatedAt`, `periodLabel` e `currency` antes de aplicar fallback.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.84 DashboardCard com periodo nao vazio

- PM-06.84 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/dashboard-card.tsx` passou a preencher label de periodo vazio com o valor da opcao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.83 status de obrigacoes normalizados no header

- PM-06.83 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a normalizar opcoes de status de obrigacoes antes de entrega-las ao header.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.82 selects de obrigacoes com labels nao vazias

- PM-06.82 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar fallback de valor para labels vazias nos selects de obrigacoes e metodo de pagamento.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.81 status FCF normalizados no header

- PM-06.81 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a normalizar opcoes de status FCF antes de entrega-las ao header, descartando `value` vazio e preenchendo label vazio com o valor.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.80 tabelas FCF com textos nao vazios

- PM-06.80 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a usar `financingText()` para textos exibidos em dividas, parcelas e movimentacoes FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.79 aliases legados de opcoes FCF nao vazios

- PM-06.79 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` passou a preencher `rotulo` legado com `valor` quando labels de opcoes FCF vierem vazias.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.78 CSV de FCF com textos nao vazios

- PM-06.78 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar `exportText()` em campos textuais de dividas, parcelas, movimentacoes e grupos de credor no CSV de FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.77 CSV de obrigacoes com textos nao vazios

- PM-06.77 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar `exportText()` em campos textuais de CSVs de obrigacoes/worklist, preservando colunas e valores numericos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.76 obrigacoes com filtros e vencimento nao vazios

- PM-06.76 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a descartar strings vazias em labels de filtros ativos e no vencimento exibido na tabela.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.75 header com labels de filtros nao vazias

- PM-06.75 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a descartar labels vazias em status, contrato, evento e cliente no sheet de filtros.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.74 header com labels de periodo nao vazias

- PM-06.74 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a descartar labels vazias nas opcoes de periodo exibidas no botao e no menu do header.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.73 dashboard com periodo e chave de auditoria nao vazios

- PM-06.73 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-view.tsx` passou a descartar strings vazias no rotulo de periodo e na chave da tabela de auditoria de divergencias.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.72 exportadores CSV com textos nao vazios

- PM-06.72 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a descartar strings vazias em rotulos de opcoes, nomes de arquivo de dashboard/FCF e data exibida de movimentos FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.71 obrigacoes com labels e sourceDetail nao vazios

- PM-06.71 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a descartar strings vazias em labels de capacidade, diagnostico de conciliacao e `sourceDetail` usado na consulta de ledger.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.70 acao FCF com rotulo nao vazio

- PM-06.70 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a usar `Pagar` quando `primaryAction.label` vier vazio/espacado.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.69 eventId normalizado em dashboard-filters

- PM-06.69 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-filters.ts` passou a usar `costCenterId` quando `eventId` vier vazio antes de normalizar o identificador.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.68 opcoes financeiras com aliases nao vazios

- PM-06.68 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` passou a usar o primeiro texto nao vazio entre `value`/`valor` e `label`/`rotulo` ao normalizar opcoes financeiras.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.67 opcoes de entidade do header com valor nao vazio

- PM-06.67 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a usar `id` quando `value` vier vazio em opcoes de contrato, evento ou cliente.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.66 selects do header com valores nao vazios

- PM-06.66 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a resolver texto nao vazio para os selects de status, contrato e cliente antes de cair em `Todos`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.65 canonicalEventId dos hooks com fallback canonico

- PM-06.65 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: hooks de dashboard, obrigacoes e FCF passaram a resolver `canonicalEventId` com texto nao vazio entre `eventId` e `costCenterId`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.64 valor de evento do header com fallback canonico

- PM-06.64 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a exibir `costCenterId` nos controles de evento quando `eventId` vier vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.63 contador de evento do header com fallback canonico

- PM-06.63 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a contar filtro de evento ativo quando `costCenterId` estiver preenchido e `eventId` vier vazio.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.62 busca inicial de obrigacoes nao vazia

- PM-06.62 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a descartar strings vazias/espacadas da query antes de preencher `searchDraft` e `searchFilter`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.61 lancamentos vinculados com textos nao vazios

- PM-06.61 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar descricao e origem nao vazias nos lancamentos vinculados ao detalhe de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.60 contas a pagar com textos nao vazios

- PM-06.60 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `accounts-payable-table.tsx` passou a usar descricao e vencimento nao vazios, com fallback para descricoes alternativas.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.59 obrigacoes divergentes com textos normalizados

- PM-06.59 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-service.ts` passou a usar textos nao vazios para descricao, contrato, evento e origem ao converter obrigacoes divergentes para contas a pagar do dashboard.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.58 contas a receber com textos nao vazios

- PM-06.58 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `accounts-receivable-table.tsx` passou a usar o primeiro texto nao vazio para cliente, descricao, contrato e evento na tabela compartilhada de contas a receber.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.57 CSVs de dashboard e obrigacoes com textos nao vazios

- PM-06.57 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar texto nao vazio em descricoes e contexto operacional de contas, obrigacoes e worklist de conciliacao exportadas para CSV.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.56 rotulos de obrigacoes com textos nao vazios

- PM-06.56 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar o primeiro texto nao vazio para contrato, evento, origem e cliente na worklist de conciliacao e na tabela de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.55 detalhe de obrigacoes com contexto nao vazio

- PM-06.55 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-obligations-view.tsx` passou a usar o primeiro texto nao vazio para contrato, evento e cliente no painel de detalhe de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.54 auditoria de conciliacao com textos nao vazios

- PM-06.54 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-view.tsx` passou a usar o primeiro texto nao vazio para descricao, origem e contexto operacional da auditoria de conciliacao.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.53 contexto operacional visual FCF nao vazio

- PM-06.53 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-financing-view.tsx` passou a usar o primeiro texto nao vazio de contrato, evento e cliente nas tabelas de dividas, parcelas e movimentacoes FCF.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.52 CSV FCF com contexto operacional nao vazio

- PM-06.52 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `dashboard-export.ts` passou a usar o primeiro texto nao vazio de contrato, evento e cliente nas linhas de dividas, parcelas e movimentacoes FCF exportadas para CSV.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.51 periodo dos cards com datas canonicas nao vazias

- PM-06.51 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `financial-dashboard-view.tsx` passou a descartar strings vazias em `startDate`/`endDate` antes de selecionar o modo `Personalizado` nos cards.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.50 header com filtros canonicos nao vazios

- PM-06.50 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `components/dashboard/header.tsx` passou a usar `cleanText()` em datas, status, contrato, evento, cliente e servico antes de montar label/contador de filtros ativos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.49 badges de filtros com valores nao vazios

- PM-06.49 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: `ActiveObligationFilters()` passou a descartar strings vazias em filtros canonicos antes de montar badges visuais, sem reler aliases legados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.48 contextos CSV com filtros nao vazios

- PM-06.48 foi concluida em desenvolvimento local em 2026-05-29.
- Mudanca: contextos CSV de obrigacoes e FCF passaram a descartar strings vazias em filtros canonicos antes de montar periodo, contrato, evento, cliente, status, origem, tipo e busca.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.47 filtros de obrigacoes contra strings vazias

- PM-06.47 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsFilters()` passou a usar normalizacao nao vazia para datas, contrato, evento, cliente, labels, origem, fluxo, natureza, situacao, conciliacao, base/excedente de realizado e busca.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.46 aliases de descricao de obrigacoes espelhados

- PM-06.46 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationItem()` passou a normalizar `obligationDescription` e `descricao` com fallback nao vazio para `description`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.45 metadados de conciliacao normalizados

- PM-06.45 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationItem()` e `normalizeFinancialObligationReconciliationWorklistItem()` passaram a tratar strings vazias como ausencia em diagnostico, label, origem e tipo de obrigacao antes dos aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.44 opcoes de credor FCF normalizadas

- PM-06.44 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialCreditorOption()` passou a normalizar `creditorName` tratando string vazia como ausencia antes de espelhar `label`, `name` e `credor_nome`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.43 indicadores e metas normalizados

- PM-06.43 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialIndicators()` normaliza `indicatorName`/`indicatorValue`/`indicatorDetail`; `normalizeFinancialGoals()` normaliza `goalName`, sempre tratando string vazia como ausencia antes dos aliases.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.42 labels analiticos/operacionais normalizados

- PM-06.42 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeExpenseCategories()`, `normalizeServiceRevenue()` e `normalizeContractSummary()` passaram a normalizar `categoryName`/`serviceName` antes de espelhar `name`/`service`, tratando string vazia como ausencia.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.41 contas a receber normalizadas

- PM-06.41 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeAccountsReceivable()` passou a calcular `clientName` e `receivableDescription` canonicos antes de espelhar `client`/`description`, tratando string vazia como ausencia.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.40 descricoes de contas pendentes normalizadas

- PM-06.40 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeAccountsPayable()` passou a normalizar `obligationDescription` de contas pendentes antes de espelhar `payableDescription`/`description`; tabela de auditoria visual e CSV geral priorizam os campos canonicos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.39 contas pendentes com descricao canonica

- PM-06.39 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `obligationToAccountPayable()` passou a consumir `description` canonico ja normalizado ao converter obrigacoes para contas pendentes do dashboard.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.38 descricoes de obrigacoes canonicas

- PM-06.38 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsResponse()` passou a normalizar `description`/`obligationDescription`/`descricao` em itens; pagamento contextual e CSV de obrigacoes consomem `description`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.37 descricoes de dividas FCF canonicas

- PM-06.37 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialFinancingResponse()` passou a normalizar `description`/`debtDescription`/`descricao` em dividas FCF; tabela e CSV FCF consomem `description`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.35 agregados de conciliacao normalizados

- PM-06.35 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialObligationsResponse()` passou a normalizar `summary.byReconciliationDiagnosis`, espelhando `guidance` e `orientacaoConciliacao`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: migrar o consumidor do resumo por diagnostico para `guidance` canonico, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.36 resumo de conciliacao canonico

- PM-06.36 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `ReconciliationSummaryRows()` passou a consumir `guidance` canonico no resumo por diagnostico, sem reler `orientacaoConciliacao`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros consumidores de dashboard/obrigacoes/FCF, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.32 badges de obrigacoes com filtros canonicos

- PM-06.32 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `ActiveObligationFilters()` passou a consumir filtros canonicos normalizados para datas, contrato, evento, cliente, labels, origem, fluxo, tipo, status, conciliacao e busca, sem reler aliases legados para exibir badges ativos.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.31 CSV de obrigacoes com filtros canonicos

- PM-06.31 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `financialObligationFilterContext()` passou a consumir filtros canonicos normalizados para datas, contrato, evento, cliente, labels, origem, fluxo, status, conciliacao e busca, sem reler aliases legados para montar o contexto do CSV de obrigacoes.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/obrigacoes/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.21 disponibilidade de caixa canonica no dashboard

- PM-06.21 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeDashboardCashAvailability()` normaliza `cashAvailability` do dashboard geral e espelha `availableCashAmount` com `cashAvailableAmount`, `caixaDisponivel` e `saldoCaixaDisponivel`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.22 origem do realizado canonica no resultado financeiro

- PM-06.22 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialResult()` agora espelha `realizedSource`/`realizadoFonte` quando a origem do realizado e informada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.23 fluxo realizado por caixa canonico no normalizador

- PM-06.23 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `normalizeFinancialDashboardViewModel()` agora espelha `cashBasisRealizedFlow`/`realizedCashFlow` para qualquer entrada de dashboard normalizada.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.24 CSV do dashboard consumindo campos canonicos

- PM-06.24 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `exportFinancialDashboardCsv()` passou a consumir campos canonicos ja normalizados para fluxo de caixa, totais pendentes e deficit de caixa.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.25 CSV do dashboard com blocos analiticos canonicos

- PM-06.25 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `exportFinancialDashboardCsv()` passou a consumir `revenueAmount`/`expenseAmount`, `categoryName`/`expenseAmount` e `serviceName`/`revenueAmount` nos blocos analiticos normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.26 CSV do dashboard com blocos operacionais canonicos

- PM-06.26 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `exportFinancialDashboardCsv()` passou a consumir `obligationDescription`/`pendingPaymentAmount`, `serviceName`/`revenueAmount`/`operationalEventsCount` e `goalName`/`currentValue`/`targetValue` nos blocos operacionais normalizados.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.27 CSV do dashboard com contas a receber canonicas

- PM-06.27 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `exportFinancialDashboardCsv()` passou a consumir `receivableDescription`, `receivedAmount` e `pendingReceivableAmount` em contas a receber, preservando a regra por status.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.28 CSV do dashboard com KPIs canonicos

- PM-06.28 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `exportFinancialDashboardCsv()` passou a consumir `metricValue` para KPIs principais e tecnicos FCO, sem reler o alias `value`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.

## Atualizacao - PM-06.29 CSV do dashboard com variacao de KPI canonica

- PM-06.29 foi concluida em desenvolvimento local em 2026-05-28.
- Mudanca: `formatKpiChangeForExport()` passou a consumir `changePercent` e `changeDescription`, sem reler `change`/`changeLabel`.
- Validacoes frontend: `npx --yes pnpm@10.33.4 lint`, `typecheck` e `build` aprovados.
- Proxima acao permitida: continuar migracao canonica do Next.js em outros aliases de dashboard/FCF e etapas futuras, ainda sem remover aliases publicados.
- Guardrail: nenhum alias foi removido de API/tipos/mocks/backend; nenhum endpoint, mutation, filtro, coluna, label, migration, limpeza, congelamento ou corte `financeiro-v3` foi iniciado.
