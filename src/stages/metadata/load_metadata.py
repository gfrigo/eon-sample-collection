"""Construção e persistência dos metadados de cada captura."""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.shared.constants import DEVICE_ID, TIER_FOLDER

METADATA_FILENAME = "metadados.jsonl"


def build_metadata(
  photo_id: str,
  filename: str,
  filepath: Path,
  tier: str,
  mode: str = "manual",
  confidence: float | None = None,
  model_version: str | None = None,
) -> dict:
  """
  Estrutura de metadados de uma captura.

  Esta é a forma que será enviada à API FastAPI futuramente.
  Os campos relativos a GCP e API ficam reservados (None/False)
  até a integração ser feita.

  Args:
    mode: "manual" (operador escolheu o tier) ou "ia" (classificado pelo modelo).
    confidence: confiança da IA (0-1), preenchido apenas quando mode == "ia".
    model_version: versão do modelo de IA usado, quando mode == "ia".
  """
  now_utc = datetime.now(timezone.utc)
  return {
    "photo_id": photo_id,
    "device_id": DEVICE_ID,
    "filename": filename,
    "local_path": str(filepath),
    "tier": tier,
    "tier_folder": TIER_FOLDER[tier],
    "mode": mode,
    "confidence": confidence,
    "model_version": model_version,
    "timestamp_utc": now_utc.isoformat(),
    "timestamp_local": datetime.now().isoformat(),
    # ── Campos reservados para integrações futuras ──
    "gcp_bucket": None,           # ex: "amostras-sangue-tcc"
    "gcp_object_path": None,      # ex: "raspberry-001/2026/05/foto_xxx.png"
    "uploaded_to_gcp": False,
    "sent_to_api": False,
  }


def save_local_metadata(metadata: dict, directory: Path) -> None:
  """Append no arquivo metadados.jsonl (uma linha JSON por captura)."""
  path = directory / METADATA_FILENAME
  with path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(metadata, ensure_ascii=False) + "\n")
