### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://adm.rhremoto.com
- redirectsEnabled: True
- candidateSurfaces: pagamentos_custos_servico
- recommendedSurfaces: pagamentos_custos_servico
- readyToActivate: True

#### Superficies avaliadas
- pagamentos_custos_servico: status=migrated; django=/eventos/custos-servico/pagamentos/; next=https://adm.rhremoto.com/pagamentos?source=custo_servico; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://adm.rhremoto.com
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=pagamentos_custos_servico

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=pagamentos_custos_servico --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1115-prod-url-real-2026-05-31\pagamentos_custos_servico\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1115-prod-url-real-2026-05-31\pagamentos_custos_servico\pm06-redirect-next-legado.md