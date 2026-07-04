### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: settings
- frontendBaseUrl: https://adm.rhremoto.com
- redirectsEnabled: True
- candidateSurfaces: backups_lista,lista_investimentos,lista_financiamentos,pagamentos_custos_extras,pagamentos_custos_servico,pagamentos_fcf,pagar_parcela,receitas_lista,despesas_lista,custos_fixos_lista,custos_por_evento,custo_extra_adicionar,pagamentos
- recommendedSurfaces: backups_lista,lista_investimentos,lista_financiamentos,pagamentos_custos_extras,pagamentos_custos_servico,pagamentos_fcf,pagar_parcela,receitas_lista,despesas_lista,custos_fixos_lista,custos_por_evento,custo_extra_adicionar,pagamentos
- readyToActivate: True

#### Superficies avaliadas
- backups_lista: status=migrated; django=/backups/; next=https://adm.rhremoto.com/backups; redirectEligible=True
- lista_investimentos: status=migrated; django=/fci/; next=https://adm.rhremoto.com/fci; redirectEligible=True
- lista_financiamentos: status=migrated; django=/fcf/; next=https://adm.rhremoto.com/fcf; redirectEligible=True
- pagamentos_custos_extras: status=migrated; django=/eventos/custos-extras/pagamentos/; next=https://adm.rhremoto.com/pagamentos?source=custo_extra; redirectEligible=True
- pagamentos_custos_servico: status=migrated; django=/eventos/custos-servico/pagamentos/; next=https://adm.rhremoto.com/pagamentos?source=custo_servico; redirectEligible=True
- pagamentos_fcf: status=migrated; django=/fcf/pagamentos/; next=https://adm.rhremoto.com/pagamentos?source=parcela_divida; redirectEligible=True
- pagar_parcela: status=migrated; django=/fcf/parcelas/1/pagar/; next=https://adm.rhremoto.com/pagamentos?source=parcela_divida; redirectEligible=True
- receitas_lista: status=migrated; django=/receitas/; next=https://adm.rhremoto.com/receitas; redirectEligible=True
- despesas_lista: status=migrated; django=/despesas/; next=https://adm.rhremoto.com/despesas; redirectEligible=True
- custos_fixos_lista: status=migrated; django=/custos-fixos/; next=https://adm.rhremoto.com/custos-fixos; redirectEligible=True
- custos_por_evento: status=migrated; django=/custos-por-evento/; next=https://adm.rhremoto.com/custos-por-evento; redirectEligible=True
- custo_extra_adicionar: status=migrated; django=/eventos/custos-extras/adicionar/; next=https://adm.rhremoto.com/custos-extras; redirectEligible=True
- pagamentos: status=migrated; django=/pagamentos/; next=https://adm.rhremoto.com/pagamentos; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://adm.rhremoto.com
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
- json: evidencias\pm06-1115-prod-url-real-2026-05-31\agregado\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1115-prod-url-real-2026-05-31\agregado\pm06-redirect-next-legado.md