### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: settings
- frontendBaseUrl: http://localhost:3000
- redirectsEnabled: True
- candidateSurfaces: backups_lista,lista_investimentos,lista_financiamentos,pagamentos_custos_extras,pagamentos_custos_servico,pagamentos_fcf,pagar_parcela,receitas_lista,despesas_lista,custos_fixos_lista,custos_por_evento,custo_extra_adicionar,pagamentos
- recommendedSurfaces: backups_lista,lista_investimentos,lista_financiamentos,pagamentos_custos_extras,pagamentos_custos_servico,pagamentos_fcf,pagar_parcela,receitas_lista,despesas_lista,custos_fixos_lista,custos_por_evento,custo_extra_adicionar,pagamentos
- readyToActivate: True

#### Superficies avaliadas
- backups_lista: status=migrated; django=/backups/; next=http://localhost:3000/backups; redirectEligible=True
- lista_investimentos: status=migrated; django=/fci/; next=http://localhost:3000/fci; redirectEligible=True
- lista_financiamentos: status=migrated; django=/fcf/; next=http://localhost:3000/fcf; redirectEligible=True
- pagamentos_custos_extras: status=migrated; django=/eventos/custos-extras/pagamentos/; next=http://localhost:3000/pagamentos?source=custo_extra; redirectEligible=True
- pagamentos_custos_servico: status=migrated; django=/eventos/custos-servico/pagamentos/; next=http://localhost:3000/pagamentos?source=custo_servico; redirectEligible=True
- pagamentos_fcf: status=migrated; django=/fcf/pagamentos/; next=http://localhost:3000/pagamentos?source=parcela_divida; redirectEligible=True
- pagar_parcela: status=migrated; django=/fcf/parcelas/1/pagar/; next=http://localhost:3000/pagamentos?source=parcela_divida; redirectEligible=True
- receitas_lista: status=migrated; django=/receitas/; next=http://localhost:3000/receitas; redirectEligible=True
- despesas_lista: status=migrated; django=/despesas/; next=http://localhost:3000/despesas; redirectEligible=True
- custos_fixos_lista: status=migrated; django=/custos-fixos/; next=http://localhost:3000/custos-fixos; redirectEligible=True
- custos_por_evento: status=migrated; django=/custos-por-evento/; next=http://localhost:3000/custos-por-evento; redirectEligible=True
- custo_extra_adicionar: status=migrated; django=/eventos/custos-extras/adicionar/; next=http://localhost:3000/custos-extras; redirectEligible=True
- pagamentos: status=migrated; django=/pagamentos/; next=http://localhost:3000/pagamentos; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=http://localhost:3000
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=backups_lista,lista_investimentos,lista_financiamentos,pagamentos_custos_extras,pagamentos_custos_servico,pagamentos_fcf,pagar_parcela,receitas_lista,despesas_lista,custos_fixos_lista,custos_por_evento,custo_extra_adicionar,pagamentos

#### Comandos
- validateCandidate: -
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1114-url-real-next-local-2026-05-31\agregado\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1114-url-real-next-local-2026-05-31\agregado\pm06-redirect-next-legado.md