import json
from pathlib import Path
from datetime import datetime, timezone

DEVICE_ID = "raspberry-001"
METADATA_FILENAME = "metadados.jsonl"

def build_metadata(
  photo_id: str,
  filename: str,
  filepath: Path,
  tier: str,
) -> dict:
  """
  Estrutura de metadados de cada captura.
  Esta é a forma que será enviada à API FastAPI futuramente.
  Os campos GCP/API ficam reservados (None/False) até a integração ser feita.
  """
  now = datetime.now(timezone.utc)

  return {
    "photo_id": photo_id,
    "device_id": DEVICE_ID,
    "filename": filename,
    "local_path": str(filepath),
    "tier": tier,
    "timestamp_utc": now.isoformat(),
    "timestamp_local": datetime.now().isoformat(),

    # ── Campos reservados para integrações futuras ──
    "gcp_bucket": None,         # ex.: "amostras-sangue-tcc"
    "gcp_object_path": None,    # ex.: "raspberry-001/2026/05/foto_xxx.png"
    "uploaded_to_gcp": False,
    "sent_to_api": False,
  }

def save_local_metadata(metadata: dict, diretorio: Path) -> None:
  """Append em metadados.jsonl (uma linha JSON por captura)."""
  path = diretorio / METADATA_FILENAME

  with path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(metadata, ensure_ascii=False) + "\n")