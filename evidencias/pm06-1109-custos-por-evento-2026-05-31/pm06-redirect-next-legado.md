### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://app.rhremoto.test
- redirectsEnabled: False
- candidateSurfaces: custos_por_evento
- recommendedSurfaces: custos_por_evento
- readyToActivate: True

#### Superficies avaliadas
- custos_por_evento: status=migrated; django=/custos-por-evento/; next=https://app.rhremoto.test/custos-por-evento; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://app.rhremoto.test
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=custos_por_evento

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=custos_por_evento --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1109-custos-por-evento-2026-05-31\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1109-custos-por-evento-2026-05-31\pm06-redirect-next-legado.md