import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone


def hash_conteudo(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def ultimo_hash_backup(backup_dir):
    metadados = sorted(backup_dir.glob("backup_banco_*.meta.json"))

    for metadata_path in reversed(metadados):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if metadata.get("sha256"):
            return metadata["sha256"]

    return None


def criar_backup_banco(force=False, manter=3):
    pasta_backup = Path(settings.BASE_DIR) / "backups" / "db"
    pasta_backup.mkdir(parents=True, exist_ok=True)

    agora = timezone.localtime()
    mes_referencia = agora.strftime("%Y-%m")

    with NamedTemporaryFile("w+b", suffix=".json", delete=False) as temporario:
        caminho_temporario = Path(temporario.name)

    try:
        call_command(
            "dumpdata",
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            output=str(caminho_temporario),
            verbosity=0,
        )

        conteudo = caminho_temporario.read_bytes()
        hash_atual = hash_conteudo(conteudo)
        ultimo_hash = ultimo_hash_backup(pasta_backup)

        if not force and ultimo_hash == hash_atual:
            removidos = limpar_backups_antigos(pasta_backup, manter)
            return {
                "criado": False,
                "arquivo": "",
                "caminho": None,
                "removidos": removidos,
                "mensagem": "Nenhum backup criado: dados iguais ao ultimo backup.",
            }

        nome_base = f"backup_banco_{mes_referencia}_{agora.strftime('%Y%m%d_%H%M%S_%f')}"
        destino = pasta_backup / f"{nome_base}.json"
        meta_destino = pasta_backup / f"{nome_base}.meta.json"

        caminho_temporario.replace(destino)

        metadata = {
            "arquivo": destino.name,
            "criado_em": agora.isoformat(),
            "mes_referencia": mes_referencia,
            "sha256": hash_atual,
            "tamanho_bytes": destino.stat().st_size,
        }
        meta_destino.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        removidos = limpar_backups_antigos(pasta_backup, manter)
        return {
            "criado": True,
            "arquivo": destino.name,
            "caminho": destino,
            "removidos": removidos,
            "mensagem": f"Backup criado: {destino}",
        }
    finally:
        if caminho_temporario.exists():
            caminho_temporario.unlink()


def limpar_backups_antigos(backup_dir, manter):
    if manter <= 0:
        return 0

    backups = sorted(
        (
            caminho
            for caminho in backup_dir.glob("backup_banco_*.json")
            if not caminho.name.endswith(".meta.json")
        ),
        key=lambda caminho: caminho.stat().st_mtime,
        reverse=True,
    )
    removidos = 0

    for backup_path in backups[manter:]:
        meta_path = backup_path.with_name(f"{backup_path.stem}.meta.json")
        backup_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        removidos += 1

    return removidos
