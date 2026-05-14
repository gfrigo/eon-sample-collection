"""Detecção do pen drive e organização das pastas de armazenamento."""

import os
from pathlib import Path

from src.shared.constants import TIER_FOLDER

# Diretório do projeto (usado como fallback quando não há pen drive)
PROJECT_DIR = Path(__file__).resolve().parents[2]
FALLBACK_PHOTO_DIR = PROJECT_DIR / "fotos_local"

# Subdiretório raiz dentro do pen drive (organiza melhor o conteúdo)
PHOTOS_ROOT_SUBDIR = "amostras_sangue"


def find_pendrive() -> Path | None:
  """
  Procura um pen drive gravável em /media/<user>/* ou /mnt/*.

  Retorna o primeiro diretório utilizável encontrado, ou None.
  """
  candidates = []
  for base in ("/media", "/mnt"):
    base_path = Path(base)
    if not base_path.exists():
      continue
    for item in base_path.iterdir():
      if not item.is_dir():
        continue
      if base == "/media":
        # Layout /media/<usuario>/<label-do-pendrive>
        for sub in item.iterdir():
          if sub.is_dir() and os.access(sub, os.W_OK):
            candidates.append(sub)
      else:
        if os.access(item, os.W_OK):
          candidates.append(item)
  return candidates[0] if candidates else None


def get_output_directory() -> tuple[Path, bool]:
  """
  Retorna (diretório_base, é_pendrive?).

  Se houver pen drive, usa <pendrive>/amostras_sangue/.
  Caso contrário, usa fotos_local/ na raiz do projeto.
  """
  pendrive = find_pendrive()
  if pendrive:
    out = pendrive / PHOTOS_ROOT_SUBDIR
    out.mkdir(exist_ok=True)
    return out, True
  FALLBACK_PHOTO_DIR.mkdir(exist_ok=True)
  return FALLBACK_PHOTO_DIR, False


def get_tier_directory(base_dir: Path, tier: str) -> Path:
  """
  Retorna o subdiretório do tier dentro do diretório base.

  Cria a pasta se ainda não existir. Exemplo:
    base_dir = /media/pi/PENDRIVE/amostras_sangue
    tier     = "bom"
    retorno  = /media/pi/PENDRIVE/amostras_sangue/amostras_boas
  """
  folder_name = TIER_FOLDER[tier]
  tier_dir = base_dir / folder_name
  tier_dir.mkdir(exist_ok=True)
  return tier_dir
