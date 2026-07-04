### Registro PM-06.1117 - smoke autenticado de producao

Data: 2026-05-31

Origem: relato do operador apos navegacao autenticada em producao e output do
servidor.

Smoke visual autenticado:

- `receitas`: abre a respectiva pagina normalmente.
- `despesas`: abre a respectiva pagina normalmente.
- `pagamentos`: abre a respectiva pagina normalmente.
- `obrigacoes`: abre a respectiva pagina normalmente.
- `fci`: abre a respectiva pagina normalmente.
- `fcf`: abre a respectiva pagina normalmente.
- `backups`: abre a respectiva pagina normalmente.
- `clientes`: abre a respectiva pagina normalmente.
- `custos por evento`: abre a respectiva pagina normalmente.
- `custos extras`: abre a respectiva pagina normalmente.
- `admin`: abre a respectiva pagina normalmente.

Validacao persistida no servidor:

Primeira tentativa a partir de `ubuntu@vminstancia:~` falhou porque `python`
nao estava no PATH fora do projeto/venv. O operador entrou em
`~/sites/controledecaixa`, ativou o virtualenv e executou:

```bash
source venv/bin/activate
python manage.py validar_redirects_next_legado --falhar --json --diretorio-evidencias=evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31 --exigir-arquivos-evidencia
```

Resultado observado:

- `ready=True`
- `issues=[]`
- `redirectsEnabled=True`
- `source=settings`
- `frontendBaseUrl=https://adm.rhremoto.com`
- `readyToActivate=True`
- `outputEvidenceFiles.directory=evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31`
- `outputEvidenceFiles.json=evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31/pm06-redirect-next-legado.json`
- `outputEvidenceFiles.record=evidencias/pm06-1116-prod-runtime-efetivo-2026-05-31/pm06-redirect-next-legado.md`

Superficies migradas validadas pelo servidor:

- `backups_lista`
- `lista_investimentos`
- `lista_financiamentos`
- `pagamentos_custos_extras`
- `pagamentos_custos_servico`
- `pagamentos_fcf`
- `pagar_parcela`
- `receitas_lista`
- `despesas_lista`
- `custos_fixos_lista`
- `custos_por_evento`
- `custo_extra_adicionar`
- `pagamentos`

Decisao: producao esta operacionalmente validada para a PM-06 no escopo de
redirect/readonly das superficies migradas e navegacao autenticada. Remocao
fisica de templates/rotas Django, migrations de limpeza, corte de aliases e
`financeiro-v3` continuam bloqueados ate etapa propria de aceite/rollback.
