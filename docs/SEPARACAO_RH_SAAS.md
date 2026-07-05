# Separacao RH SaaS

Auditoria inicial da copia RH SaaS.

## Status seguro

- Remote esperado: novo repositorio `rhsaas`.
- Nao ha `package.json`, `next.config.*`, Dockerfile, Compose, Procfile, Gunicorn
  ou Nginx versionados nesta pasta.
- O `settings.py` le somente `.env` na raiz do projeto.
- O arquivo `caixa/.env` foi encontrado, mas nao e carregado por `settings.py`.

## Ajustes aplicados

- Exemplos de ambiente usam banco/cache/dominios de exemplo do RH SaaS.
- Branding textual de auth, PWA e e-mails de reset foi atualizado para RH SaaS.
- Defaults de cache, e-mail e Trusted Types foram renomeados para RH SaaS.

## Referencias herdadas que exigem revisao

- `DEPLOY_ORACLE.md` ainda contem roteiro historico do projeto antigo.
- `INTEGRACAO_NEXT_DJANGO.md`, `MELHORIAS_E_PROXIMOS_PASSOS.md`,
  `PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md`, `evidencias/` e alguns testes mantem
  referencias historicas ao projeto antigo e ao frontend antigo.
- Os comandos PM-02 em `caixa/management/commands/gerar_snapshot_baseline_financeira.py`
  e `caixa/management/commands/validar_baseline_pm02.py` ainda possuem perfil
  legado de producao do projeto antigo; nao foram alterados por serem
  validacoes operacionais.

## Pendencias antes de producao

- Confirmar dominio real do RH SaaS.
- Confirmar nome definitivo do banco PostgreSQL.
- Revisar ou substituir os roteiros de deploy herdados antes de qualquer uso.
- Confirmar se o frontend Next.js tera repositorio separado e quais serao as URLs.
