import Path
import logging

logger = logging.getLogger(__name__)

def upload_para_gcp(filepath:Path, metadata:dict) -> None:
  """
  PLACEHOLDER. Quando o GCP estiver definido, fazer upload aqui e
  preencher metadata['gcp_bucket'] / metadata['gcp_object_path'].
  Não chamado no fluxo principal por enquanto.
  """
  logger.debug("GCP: upload não implementado. Arquivo: %s", filepath)