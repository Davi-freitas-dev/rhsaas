### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://app.rhremoto.test
- redirectsEnabled: False
- candidateSurfaces: custos_fixos_lista
- recommendedSurfaces: custos_fixos_lista
- readyToActivate: True

#### Superficies avaliadas
- custos_fixos_lista: status=migrated; django=/custos-fixos/; next=https://app.rhremoto.test/custos-fixos; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://app.rhremoto.test
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
- json: evidencias\pm06-1109-custos-fixos-lista-2026-05-31\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1109-custos-fixos-lista-2026-05-31\pm06-redirect-next-legado.md