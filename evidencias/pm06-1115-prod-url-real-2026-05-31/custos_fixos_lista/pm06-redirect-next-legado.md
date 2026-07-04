### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://adm.rhremoto.com
- redirectsEnabled: True
- candidateSurfaces: custos_fixos_lista
- recommendedSurfaces: custos_fixos_lista
- readyToActivate: True

#### Superficies avaliadas
- custos_fixos_lista: status=migrated; django=/custos-fixos/; next=https://adm.rhremoto.com/custos-fixos; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://adm.rhremoto.com
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=custos_fixos_lista

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=custos_fixos_lista --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1115-prod-url-real-2026-05-31\custos_fixos_lista\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1115-prod-url-real-2026-05-31\custos_fixos_lista\pm06-redirect-next-legado.md