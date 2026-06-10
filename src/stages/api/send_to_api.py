import logging
import urllib.request
import urllib.error
import json

logger = logging.getLogger(__name__)

API_URL = "https://eon-aab-api-66396884579.southamerica-east1.run.app"

GCS_PUBLIC_BASE = "https://storage.googleapis.com"


def send_to_api(metadata: dict) -> bool:
    """Registra a amostra na API após upload para GCP. Retorna True se OK."""
    if not metadata.get("uploaded_to_gcp"):
        logger.warning("API: upload GCP não ocorreu, abortando envio.")
        return False

    bucket = metadata.get("gcp_bucket", "")
    obj_path = metadata.get("gcp_object_path", "")
    gcp_url = f"{GCS_PUBLIC_BASE}/{bucket}/{obj_path}"

    payload = {
        "photo_id":    metadata["photo_id"],
        "tier":        metadata["tier"],
        "gcp_url":     gcp_url,
        "collected_at": metadata["timestamp_utc"],
        "doctor_name": metadata.get("doctor"),
        "confidence":  metadata.get("confidence"),
        "model_version": metadata.get("model_version"),
    }

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_URL}/samples/rasp",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("API: amostra registrada (status %d)", resp.status)
            return True
    except urllib.error.HTTPError as e:
        logger.error("API: erro HTTP %d — %s", e.code, e.read().decode())
    except Exception as e:
        logger.error("API: falha ao enviar — %s", e)

    return False
