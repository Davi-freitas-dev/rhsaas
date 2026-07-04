### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: http://localhost:3000
- redirectsEnabled: True
- candidateSurfaces: custos_fixos_lista
- recommendedSurfaces: custos_fixos_lista
- readyToActivate: True

#### Superficies avaliadas
- custos_fixos_lista: status=migrated; django=/custos-fixos/; next=http://localhost:3000/custos-fixos; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=http://localhost:3000
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
- json: evidencias\pm06-1114-url-real-next-local-2026-05-31\custos_fixos_lista\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1114-url-real-next-local-2026-05-31\custos_fixos_lista\pm06-redirect-next-legado.md