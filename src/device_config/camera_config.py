"""Configuração e helpers da webcam Logitech C920s."""

import subprocess
from pathlib import Path

import cv2

# Frames descartados após abrir a câmera (aquecimento do sensor)
CAMERA_WARMUP_FRAMES = 5

# Resolução nativa Full HD da C920s
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080

# Foco manual (0=desligado usa autofoco, 1-250 define foco fixo)
# Ajuste conforme a distância do tubo à câmera (~140mm → ~30)
CAMERA_FOCUS = 200


def find_camera():
  """
  Detecta a Logitech C920s via v4l2-ctl.

  Se v4l2-ctl não estiver disponível ou não encontrar a câmera específica,
  faz fallback para o primeiro /dev/videoN que abrir com OpenCV.
  Retorna o device (string ou int) pronto para passar ao cv2.VideoCapture,
  ou None se nenhuma câmera for encontrada.
  """
  try:
    result = subprocess.run(
      ["v4l2-ctl", "--list-devices"],
      capture_output=True,
      text=True,
      timeout=5,
    )
    lines = result.stdout.split("\n")
    found_logitech = False
    for line in lines:
      if "C920" in line or "Logitech" in line:
        found_logitech = True
      elif found_logitech and "/dev/video" in line:
        path = line.strip()
        try:
          return int(path.replace("/dev/video", ""))
        except ValueError:
          return path
  except (FileNotFoundError, subprocess.TimeoutExpired):
    pass

  # Fallback: testa os 10 primeiros devices até achar um que abra
  for index in range(10):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
      cap.release()
      return index
  return None


def _set_focus(device: int) -> None:
  import logging
  dev_path = f"/dev/video{device}"
  try:
    result = subprocess.run(
      ["v4l2-ctl", "-d", dev_path,
       "-c", "focus_automatic_continuous=0",
       "-c", f"focus_absolute={CAMERA_FOCUS}"],
      capture_output=True,
      timeout=3,
    )
    if result.returncode != 0:
      logging.warning("v4l2-ctl focus falhou: %s", result.stderr.decode())
    else:
      logging.info("Foco aplicado: %d", CAMERA_FOCUS)
  except Exception as e:
    logging.warning("v4l2-ctl focus erro: %s", e)


def capture_photo(device, output_path: Path) -> bool:
  """
  Captura uma foto da câmera e salva no caminho informado.

  Retorna True em caso de sucesso, False em caso de falha.
  """
  _set_focus(device)

  cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
  if not cap.isOpened():
    return False

  # Força resolução Full HD nativa da C920s
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

  # Descarta primeiros frames (ajuste de exposição/foco)
  for _ in range(CAMERA_WARMUP_FRAMES):
    cap.read()

  ret, frame = cap.read()
  cap.release()
  if not ret:
    return False

  cv2.imwrite(str(output_path), frame)
  return True
