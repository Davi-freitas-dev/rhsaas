### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://adm.rhremoto.com
- redirectsEnabled: True
- candidateSurfaces: custo_extra_adicionar
- recommendedSurfaces: custo_extra_adicionar
- readyToActivate: True

#### Superficies avaliadas
- custo_extra_adicionar: status=migrated; django=/eventos/custos-extras/adicionar/; next=https://adm.rhremoto.com/custos-extras; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://adm.rhremoto.com
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=custo_extra_adicionar

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=custo_extra_adicionar --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1115-prod-url-real-2026-05-31\custo_extra_adicionar\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1115-prod-url-real-2026-05-31\custo_extra_adicionar\pm06-redirect-next-legado.md