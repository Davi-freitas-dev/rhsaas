import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class SecurityDocumentationGuardrailTests(SimpleTestCase):
    def test_cookie_domain_compartilhado_so_aparece_como_historico_superado(self):
        unsafe_cookie_pattern = re.compile(
            r"(?:SESSION|CSRF)_COOKIE_DOMAIN=\.rhremoto\.com"
            r"|--esperar-(?:session|csrf)-cookie-domain=\.rhremoto\.com"
        )
        for relative_path in (
            "MELHORIAS_E_PROXIMOS_PASSOS.md",
            "PLANO_EVOLUCAO_DOMINIO_FINANCEIRO.md",
        ):
            path = Path(settings.BASE_DIR) / relative_path
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if unsafe_cookie_pattern.search(line) and "HISTORICO SUPERADO" not in line:
                    self.fail(
                        f"{relative_path}:{line_number} recomenda cookie compartilhado."
                    )
