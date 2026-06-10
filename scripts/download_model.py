"""Baixa o model.tflite mais recente publicado no GitHub Releases.

O pipeline de treino (eon-aab-ml-train) publica o modelo exportado como
asset da release com tag "latest". Este script baixa esse asset para
models/model.tflite, pronto para ser usado por src/stages/ml/inference.py.

Uso:
    python scripts/download_model.py --repo usuario/eon-aab-ml-train
    # ou definindo a variável de ambiente:
    ML_MODEL_REPOSITORY=usuario/eon-aab-ml-train python scripts/download_model.py
"""

import argparse
import os
import urllib.request
from pathlib import Path

DEFAULT_REPO = os.getenv("ML_MODEL_REPOSITORY", os.getenv("REPOSITORY", ""))
DEFAULT_TAG = "latest"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"


def download_model(repo: str, tag: str = DEFAULT_TAG, filename: str = "model.tflite") -> Path:
  if not repo:
    raise SystemExit(
      "Defina o repositorio do modelo: --repo usuario/eon-aab-ml-train "
      "ou a variavel de ambiente ML_MODEL_REPOSITORY."
    )

  url = f"https://github.com/{repo}/releases/download/{tag}/{filename}"
  MODELS_DIR.mkdir(exist_ok=True)
  dest = MODELS_DIR / filename

  print(f"Baixando {url} -> {dest}")
  urllib.request.urlretrieve(url, dest)

  version_file = MODELS_DIR / "model.version"
  version_file.write_text(f"{repo}@{tag}", encoding="utf-8")

  size_kb = dest.stat().st_size / 1024
  print(f"OK: {dest} ({size_kb:.1f} KB)")
  return dest


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Baixa o model.tflite mais recente do GitHub Releases")
  parser.add_argument("--repo", default=DEFAULT_REPO, help="usuario/repositorio (ex: gfrigo/eon-aab-ml-train)")
  parser.add_argument("--tag", default=DEFAULT_TAG, help="Tag da release (padrao: latest)")
  args = parser.parse_args()

  download_model(args.repo, args.tag)
