### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: settings
- frontendBaseUrl: http://localhost:3000
- redirectsEnabled: False
- candidateSurfaces: -
- recommendedSurfaces: -
- readyToActivate: False

#### Superficies avaliadas
- -

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=http://localhost:3000
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=-

#### Comandos
- validateCandidate: -
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1114-url-real-next-local-2026-05-31\rollback\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1114-url-real-next-local-2026-05-31\rollback\pm06-redirect-next-legado.md