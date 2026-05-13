from pathlib import Path

import cv2
import subprocess

CAMERA_WARMUP_FRAMES = 5
CAMERA_WIDTH = 1920   # C920s: Full HD nativo
CAMERA_HEIGHT = 1080

def find_camera():
  """
  Detecta a Logitech C920s via v4l2-ctl; se não conseguir, faz fallback
  para o primeiro /dev/videoN que abrir com OpenCV.
  """
  try:
    result = subprocess.run(
      ["v4l2-ctl", "--list-devices"],
      capture_output=True, text=True, timeout=5,
    )
    lines = result.stdout.split("\n")
    achou_logitech = False
    for line in lines:
      if "C920" in line or "Logitech" in line:
        achou_logitech = True
      elif achou_logitech and "/dev/video" in line:
        return line.strip()
  except (FileNotFoundError, subprocess.TimeoutExpired):
    pass

  for index in range(10):
    cap = cv2.VideoCapture(index)
    if cap.isOpened():
      cap.release()
      return index
  return None

def capture_photo(device, output_path:Path) -> bool:
  cap = cv2.VideoCapture(device)
  if not cap.isOpened():
    return False
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
  for _ in range(CAMERA_WARMUP_FRAMES):
    cap.read()
  ret, frame = cap.read()
  cap.release()
  if not ret:
    return False
  cv2.imwrite(str(output_path), frame)
  return True