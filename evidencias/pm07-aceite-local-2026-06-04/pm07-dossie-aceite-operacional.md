# PM-07 dossie de aceite operacional

Gerado em: 2026-06-04T19:56:25-03:00

Status: preparado localmente; pendente de ambiente alvo, backup, commit/tag, monitoramento e aceite humano.

## Referencias locais

- Backend antes do commit final: d08c4ea.
- Frontend antes do commit final: 275aa10.
- Entradas alteradas no backend: 93.
- Entradas alteradas no frontend: 37.
- Evidencia local base: evidencias/pm07-aceite-local-2026-06-04/pm07-aceite-local.md.
- Plano local de commit/release: evidencias/pm07-aceite-local-2026-06-04/pm07-plano-commit-release.md.

## Ordem de aceite final

1. Revisar diffs e confirmar que todos os arquivos alterados pertencem ao pacote PM-06/PM-07.
2. Criar commits finais separados no backend e no frontend, depois tags/referencias publicaveis.
3. Executar backup real do banco no ambiente alvo antes de aplicar migrations/deploy.
4. Registrar rollback: codigo/tag anterior, backup, responsavel, janela e criterio de abortar.
5. Reexecutar validacoes PM-07 no ambiente alvo ou janela aprovada.
6. Ativar rotina periodica de auditoria/alerta.
7. Registrar aceite semantico financeiro/operacao e aceite tecnico.
8. Conferir dados reais apos a primeira janela completa de uso.

## Comandos obrigatorios no ambiente alvo

- python manage.py backup_banco_mensal --force --manter 12
- python manage.py check
- python manage.py makemigrations --check --dry-run
- python manage.py migrate --plan
- python manage.py validar_preflight_deploy_financeiro --falhar --json
- python manage.py validar_operacao_obrigacoes --validar-canonico --validar-escrita-canonica --validar-valores-editaveis --falhar --json
- python manage.py auditar_totais_negocio --validar-valores-editaveis --falhar-com-divergencia --falhar-com-valores-editaveis --json
- python manage.py verificar_conciliacao_obrigacoes --json --falhar-com-divergencia
- corepack pnpm run verify:publish

## Monitoramento canonical-first condicional

Executar somente quando uma origem entrar em janela canonical-first real:

- python manage.py monitorar_janela_canonical_first --source=<origem> --data-inicial=<data_ativacao> --exigir-data-ativacao --exigir-canonical-first --falhar-com-legado-na-janela --json --falhar

## Bloqueadores de fechamento

- Worktree com alteracoes nao revisadas ou fora do pacote PM-06/PM-07.
- Backup real ausente ou sem referencia registrada.
- migrate --plan com operacao inesperada nao revisada.
- Qualquer comando PM-07 com exit code diferente de zero.
- preflight, operacao, totais ou conciliacao com issues, divergencias ou ready diferente de true.
- verify:publish falhando no frontend.
- Ausencia de aceite semantico ou tecnico.
- Primeira janela completa sem conferencia de dados reais.

## Criterio para encerrar PM-07

PM-07 so pode ser encerrada depois de commit/tag final, backup, rollback, janela, validacoes do ambiente alvo, rotina ativa de monitoramento, aceite semantico/tecnico e revisao de dados reais apos a primeira janela completa, ou depois de qualquer pendencia residual ser aceita explicitamente.
