import json
from pathlib import Path

from django.http import Http404

from .tenant_files import artifact_scope_for_schema, backup_dir_for_schema


def backup_dir(schema_name=None):
    return backup_dir_for_schema(schema_name)


def _metadata_path(caminho):
    return caminho.with_name(f"{caminho.stem}.meta.json")


def _metadata_valida_para_schema(caminho, schema_name, scope):
    metadata_path = _metadata_path(caminho)
    if not metadata_path.is_file():
        return False

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return (
        metadata.get("arquivo") == caminho.name
        and metadata.get("schema_name") == schema_name
        and metadata.get("scope") == scope
    )


def listar_backups_disponiveis():
    arquivos = []
    scope, schema_name = artifact_scope_for_schema()
    pasta = backup_dir(schema_name)

    if pasta.exists():
        for caminho in sorted(pasta.glob("backup_banco_*.json"), reverse=True):
            if caminho.name.endswith(".meta.json") or not caminho.is_file():
                continue
            if not _metadata_valida_para_schema(caminho, schema_name, scope):
                continue

            arquivos.append(
                {
                    "nome": caminho.name,
                    "tamanho_mb": caminho.stat().st_size / 1024 / 1024,
                    "criado_em": caminho.stat().st_mtime,
                    "scope": scope,
                    "schema_name": schema_name,
                }
            )

    return arquivos


def obter_caminho_backup(nome_arquivo):
    scope, schema_name = artifact_scope_for_schema()
    if Path(nome_arquivo).name != nome_arquivo:
        raise Http404("Arquivo nao encontrado.")

    if not nome_arquivo.startswith("backup_banco_") or nome_arquivo.endswith(".meta.json"):
        raise Http404("Arquivo nao encontrado.")

    pasta = backup_dir(schema_name).resolve()
    caminho = (pasta / nome_arquivo).resolve()

    try:
        caminho.relative_to(pasta)
    except ValueError as erro:
        raise Http404("Arquivo nao encontrado.") from erro

    if not caminho.is_file() or caminho.suffix != ".json":
        raise Http404("Arquivo nao encontrado.")

    if not _metadata_valida_para_schema(caminho, schema_name, scope):
        raise Http404("Arquivo nao encontrado.")

    return caminho
