import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_GCS_BUCKET = "fotos-treinamento"
_PROJECT_ID = "project-13fcc269-a732-4c98-b00"
_SA_FILE = Path(__file__).resolve().parents[3] / "service_account.json"


def _get_client():
    from google.oauth2.service_account import Credentials
    from google.cloud import storage

    creds = Credentials.from_service_account_file(
        str(_SA_FILE),
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return storage.Client(credentials=creds, project=_PROJECT_ID)


def upload_to_gcp(filepath: Path, metadata: dict) -> bool:
    """Upload da foto para GCS. Atualiza metadata in-place. Retorna True se OK."""
    try:
        client = _get_client()
        date_part = datetime.now().strftime("%Y/%m/%d")
        object_path = (
            f"{metadata['device_id']}/"
            f"{metadata['tier_folder']}/"
            f"{date_part}/"
            f"{metadata['filename']}"
        )
        bucket = client.bucket(_GCS_BUCKET)
        blob = bucket.blob(object_path)
        blob.metadata = {
            "photo_id": metadata["photo_id"],
            "device_id": metadata["device_id"],
            "tier": metadata["tier"],
        }
        blob.upload_from_filename(str(filepath), content_type="image/png")
        metadata["gcp_bucket"] = _GCS_BUCKET
        metadata["gcp_object_path"] = object_path
        metadata["uploaded_to_gcp"] = True
        logger.info("GCP upload OK: %s", object_path)
        return True
    except Exception as exc:
        logger.error("GCP upload falhou: %s", exc)
        return False
