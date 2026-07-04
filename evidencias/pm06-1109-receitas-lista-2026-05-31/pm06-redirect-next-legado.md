### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://app.rhremoto.test
- redirectsEnabled: False
- candidateSurfaces: receitas_lista
- recommendedSurfaces: receitas_lista
- readyToActivate: True

#### Superficies avaliadas
- receitas_lista: status=migrated; django=/receitas/; next=https://app.rhremoto.test/receitas; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://app.rhremoto.test
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=receitas_lista

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=receitas_lista --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1109-receitas-lista-2026-05-31\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1109-receitas-lista-2026-05-31\pm06-redirect-next-legado.md