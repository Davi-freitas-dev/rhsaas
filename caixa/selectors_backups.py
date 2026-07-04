from pathlib import Path

from django.conf import settings
from django.http import Http404


def backup_dir():
    return Path(settings.BASE_DIR) / "backups" / "db"


def listar_backups_disponiveis():
    arquivos = []
    pasta = backup_dir()

    if pasta.exists():
        for caminho in sorted(pasta.glob("backup_banco_*.json"), reverse=True):
            if caminho.name.endswith(".meta.json") or not caminho.is_file():
                continue

            arquivos.append({
                "nome": caminho.name,
                "tamanho_mb": caminho.stat().st_size / 1024 / 1024,
                "criado_em": caminho.stat().st_mtime,
            })

    return arquivos


def obter_caminho_backup(nome_arquivo):
    if Path(nome_arquivo).name != nome_arquivo:
        raise Http404("Arquivo não encontrado.")

    if not nome_arquivo.startswith("backup_banco_") or nome_arquivo.endswith(".meta.json"):
        raise Http404("Arquivo não encontrado.")

    pasta = backup_dir().resolve()
    caminho = (pasta / nome_arquivo).resolve()

    try:
        caminho.relative_to(pasta)
    except ValueError as erro:
        raise Http404("Arquivo não encontrado.") from erro

    if not caminho.is_file() or caminho.suffix != ".json":
        raise Http404("Arquivo não encontrado.")

    return caminho
