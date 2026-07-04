# PM-07 plano local de commit e release

Gerado em: 2026-06-04T20:04:22-03:00

Status: preparado localmente, nao executado.

## Referencias atuais

- Backend HEAD antes do commit final: d08c4ea.
- Frontend HEAD antes do commit final: 275aa10.
- Entradas alteradas no backend: 93.
- Entradas alteradas no frontend: 37.

## Commits sugeridos

Backend:

- Titulo sugerido: pm06: concluir arquitetura premium backend.
- Incluir: docs e Plano Mestre; migration 0035_remove_contrato_operacional; remocao de HTML Django operacional; preservacao/ajuste de API/Admin/services/selectors/serializers; guardrails/comandos de auditoria; testes backend; evidencias PM-07.
- Checks antes do commit: git diff --check; python manage.py check; python manage.py makemigrations --check --dry-run; python manage.py test caixa.tests --keepdb --verbosity 1.

Frontend:

- Titulo sugerido: pm06: alinhar Next.js a interface operacional premium.
- Incluir: docs frontend; services/hooks/utils canonicos; componentes operacionais; guardrails de aliases; E2E de filtros por contrato; verify:publish.
- Checks antes do commit: git diff --check; corepack pnpm run verify:publish; corepack pnpm run verify:pm06:e2e quando houver ambiente.

## Tags sugeridas apos commits

- Backend: pm07-acceptance-candidate-backend-2026-06-04 ou tag equivalente aprovada.
- Frontend: pm07-acceptance-candidate-frontend-2026-06-04 ou tag equivalente aprovada.

Nao criar tag com worktree sujo ou sem as validacoes de ambiente alvo combinadas.

## Plano de rollback da janela

1. Antes da janela, registrar commit/tag atual de producao backend e frontend.
2. Executar backup_banco_mensal --force --manter 12 e guardar referencia/arquivo.
3. Se falhar antes de migrations/deploy efetivo, cancelar janela e manter refs atuais.
4. Se falhar depois de migration/deploy, voltar codigo para refs anteriores e restaurar backup do banco; se houver delta operacional depois do backup, conciliar manualmente antes de retomar.
5. Manter CANONICAL_FIRST_SETTLEMENT_ENABLED desativado salvo origem explicitamente aprovada.
6. Desativar flags/allowlists de redirects ou canonical-first como primeira resposta quando o problema for operacional e reversivel por configuracao.
7. Rodar check, preflight, auditoria de totais e conciliacao apos rollback.

## Nao executado nesta preparacao

- git add, git commit ou git tag.
- Deploy.
- Backup real em ambiente alvo.
- migrate em ambiente alvo.

## Bloqueadores para executar o release

- Worktree nao revisado.
- Validacao local ou alvo falhando.
- Backup real ausente.
- Sem aceite semantico/tecnico.
- Sem plano de rollback registrado.
