### Registro PM-06.1104 - canario de redirect Next legado

- ready: True
- source: argument
- frontendBaseUrl: https://app.rhremoto.test
- redirectsEnabled: False
- candidateSurfaces: pagar_parcela
- recommendedSurfaces: pagar_parcela
- readyToActivate: True

#### Superficies avaliadas
- pagar_parcela: status=migrated; django=/fcf/parcelas/1/pagar/; next=https://app.rhremoto.test/pagamentos?source=parcela_divida; redirectEligible=True

#### Pendencias
- nenhuma

#### Ativacao sugerida
- NEXT_FRONTEND_URL=https://app.rhremoto.test
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=True
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=pagar_parcela

#### Comandos
- validateCandidate: python manage.py validar_redirects_next_legado --surface=pagar_parcela --exigir-unitario --falhar --json
- validateEnvironment: python manage.py validar_redirects_next_legado --falhar --json
- rollbackValidation: python manage.py validar_redirects_next_legado --json

#### Rollback
- NEXT_FRONTEND_LEGACY_REDIRECTS_ENABLED=False
- NEXT_FRONTEND_LEGACY_REDIRECT_SURFACES=<vazio>

#### Arquivos salvos
- json: evidencias\pm06-1109-pagar-parcela-2026-05-31\pm06-redirect-next-legado.json
- registro: evidencias\pm06-1109-pagar-parcela-2026-05-31\pm06-redirect-next-legado.md