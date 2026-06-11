"""Inferência leve (TFLite) para classificar a qualidade da amostra pela foto.

Usa ai-edge-litert (ou tflite-runtime / tensorflow.lite como fallback) para
manter o consumo de memória baixo no Raspberry Pi. O modelo é carregado uma
única vez e reutilizado entre capturas.
"""

import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Raiz do projeto (eon-sample-collection/)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = _PROJECT_ROOT / "models" / "model.tflite"
MODEL_VERSION_PATH = _PROJECT_ROOT / "models" / "model.version"

IMAGE_SIZE = (224, 224)  # (largura, altura) — igual ao treino

# Índice de saída do modelo -> tier interno usado no resto do sistema
CLASS_TO_TIER = {0: "bom", 1: "ruim", 2: "pessimo"}

DEFAULT_MODEL_VERSION = "mobilenetv2-tflite-v1"

_interpreter = None
_input_details = None
_output_details = None


def is_model_available() -> bool:
  """Verifica se o arquivo model.tflite já foi baixado/copiado para o device."""
  return MODEL_PATH.exists()


def get_model_version() -> str:
  """Retorna a versão do modelo (lida de models/model.version, se existir)."""
  if MODEL_VERSION_PATH.exists():
    return MODEL_VERSION_PATH.read_text(encoding="utf-8").strip()
  return DEFAULT_MODEL_VERSION


def _load_interpreter():
  """Carrega o interpretador TFLite, preferindo runtimes leves."""
  global _interpreter, _input_details, _output_details

  if _interpreter is not None:
    return _interpreter

  if not MODEL_PATH.exists():
    raise FileNotFoundError(
      f"Modelo não encontrado em {MODEL_PATH}. "
      "Rode 'python scripts/download_model.py' para baixar a versão mais recente."
    )

  try:
    from ai_edge_litert.interpreter import Interpreter  # type: ignore
  except ImportError:
    try:
      from tflite_runtime.interpreter import Interpreter  # type: ignore
    except ImportError:
      from tensorflow.lite.python.interpreter import Interpreter  # type: ignore
      logger.warning(
        "ai-edge-litert/tflite-runtime não encontrados — usando tensorflow.lite "
        "(pacote pesado). Instale ai-edge-litert para um runtime mais leve."
      )

  interpreter = Interpreter(model_path=str(MODEL_PATH))
  interpreter.allocate_tensors()

  _interpreter = interpreter
  _input_details = interpreter.get_input_details()
  _output_details = interpreter.get_output_details()
  logger.info("Modelo TFLite carregado: %s", MODEL_PATH)
  return _interpreter


def _preprocess(filepath: Path) -> np.ndarray:
  """Carrega a foto e aplica o mesmo pré-processamento usado no treino."""
  image = Image.open(filepath).convert("RGB").resize(IMAGE_SIZE, Image.BILINEAR)
  array = np.asarray(image, dtype=np.float32) / 255.0
  return np.expand_dims(array, axis=0)


def classify_image(filepath: Path) -> tuple[str, float]:
  """
  Classifica a foto capturada usando o modelo TFLite.

  Args:
    filepath (Path): Caminho da foto a classificar.

  Returns:
    tuple[str, float]: (tier interno "bom"|"ruim"|"pessimo", confiança 0-1)
  """
  interpreter = _load_interpreter()
  input_detail = _input_details[0]
  output_detail = _output_details[0]

  batch = _preprocess(filepath)

  # Modelos quantizados (int8/uint8) esperam a entrada já escalonada.
  if input_detail["dtype"] != np.float32:
    scale, zero_point = input_detail["quantization"]
    batch = (batch / scale + zero_point).astype(input_detail["dtype"])

  interpreter.set_tensor(input_detail["index"], batch)
  interpreter.invoke()
  output = interpreter.get_tensor(output_detail["index"])[0]

  if output.dtype != np.float32:
    scale, zero_point = output_detail["quantization"]
    output = (output.astype(np.float32) - zero_point) * scale

  # Garante que a saída seja uma distribuição de probabilidades.
  if not np.isclose(output.sum(), 1.0, atol=1e-2):
    exps = np.exp(output - np.max(output))
    output = exps / exps.sum()

  class_idx = int(np.argmax(output))
  confidence = float(output[class_idx])
  tier = CLASS_TO_TIER.get(class_idx, "pessimo")

  logger.info("Inferencia: tier=%s confianca=%.3f scores=%s", tier, confidence, output.tolist())
  return tier, confidence
