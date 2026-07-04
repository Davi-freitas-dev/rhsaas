### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: http://localhost:3000
- redirectsEnabled: True
- candidateSurfaces: lista_financiamentos
- recommendedSurfaces: lista_financiamentos
- readyToActivate: True

#### Superficies avaliadas
- lista_financiamentos: status=migrated; django=/fcf/; next=http://localhost:3000/fcf; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=http://localhost:3000
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=lista_financiamentos

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=lista_financiamentos --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1114-url-real-next-local-2026-05-31\lista_financiamentos\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1114-url-real-next-local-2026-05-31\lista_financiamentos\pm06-redirect-next-legado.md