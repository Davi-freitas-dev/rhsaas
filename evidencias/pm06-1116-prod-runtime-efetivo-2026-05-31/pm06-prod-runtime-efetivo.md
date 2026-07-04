### Registro PM-06.1116 - runtime efetivo de producao

Data: 2026-05-31

Origem: output colado pelo operador a partir do servidor de producao:
`ubuntu@vminstancia:~/sites/controledecaixa`.

Comando executado no servidor:

```bash
python manage.py validar_redirects_next_legado --falhar --json
```

Resultado observado:

- `ready=True`
- `issues=[]`
- `source=settings`
- `redirectsEnabled=True`
- `frontendBaseUrl=https://adm.rhremoto.com`
- `readyToActivate=True`
- `NEXT_FRONTEND_URL=https://adm.rhremoto.com`
- `NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True`
- `NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES` configurada com as 13 superficies
  migradas.

Superficies efetivamente configuradas e aprovadas:

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

Destinos publicados:

- `https://adm.rhremoto.com/backups`
- `https://adm.rhremoto.com/fci`
- `https://adm.rhremoto.com/fcf`
- `https://adm.rhremoto.com/pagamentos?source=custo_extra`
- `https://adm.rhremoto.com/pagamentos?source=custo_servico`
- `https://adm.rhremoto.com/pagamentos?source=parcela_divida`
- `https://adm.rhremoto.com/receitas`
- `https://adm.rhremoto.com/despesas`
- `https://adm.rhremoto.com/custos-fixos`
- `https://adm.rhremoto.com/custos-por-evento`
- `https://adm.rhremoto.com/custos-extras`
- `https://adm.rhremoto.com/pagamentos`

Observacao:

- O comando foi executado sem `--diretorio-evidencias`, entao o proprio
  management command nao salvou JSON/Markdown no servidor nessa rodada.
- Este registro local preserva o resumo do output colado pelo operador.
- Rollback minimo segue sendo:

```env
NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=
```

Decisao: o runtime efetivo de producao esta configurado e validado para
redirect controlado das 13 superficies migradas. Remocao fisica de rotas,
templates, aliases, migrations de limpeza e corte `financeiro-v3` seguem
bloqueados.

Checagem externa sem sessao:

- `https://caixa.rhremoto.com/<rota-legada>` respondeu HTTP 302 para
  `/login/?next=<rota-legada>` nas 13 superficies testadas sem cookie de sessao.
- Interpretacao: a autenticacao Django intercepta usuarios anonimos antes da
  view aplicar a ponte/redirect para Next.js.
- Smoke ainda recomendado: testar as mesmas rotas antigas em navegador com
  usuario autenticado no Django, confirmando redirecionamento final para
  `https://adm.rhremoto.com/...`.
