### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://app.rhremoto.test
- redirectsEnabled: False
- candidateSurfaces: pagamentos
- recommendedSurfaces: pagamentos
- readyToActivate: True

#### Superficies avaliadas
- pagamentos: status=migrated; django=/pagamentos/; next=https://app.rhremoto.test/pagamentos; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://app.rhremoto.test
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=pagamentos

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=pagamentos --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1109-pagamentos-2026-05-31\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1109-pagamentos-2026-05-31\pm06-redirect-next-legado.md