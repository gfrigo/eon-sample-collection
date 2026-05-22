import logging
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

import RPi.GPIO as GPIO

from src.shared.status import Status
from src.shared.constants import (
  TIER_MAP,
  TIER_DISPLAY,
  TIER_FOLDER,
  POLL_INTERVAL,
  MESSAGE_DISPLAY,
  DOCTORS,
)
from src.device_config.buttons_config import (
  init_gpio,
  button_pressed,
  wait_to_release_button,
  BUTTON_BOM,
  BUTTON_RUIM,
  BUTTON_PESSIMO,
)
from src.device_config.lcd_config import (
  init_lcd,
  lcd_msg,
  show_idle_screen,
  show_tier_selected,
  show_capturing_animation,
  show_photo_ok,
  show_doctor_selection,
  show_doctor_confirmed,
)
from src.device_config.camera_config import find_camera, capture_photo, CAMERA_FOCUS
from src.stages.metadata.load_metadata import (
  build_metadata,
  save_local_metadata,
)
from src.stages.gcp.load_to_storage import upload_to_gcp
from src.stages.api.send_to_api import send_to_api

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _apply_camera_focus(device) -> None:
  import os
  dev_path = f"/dev/video{device}"
  uid = subprocess.check_output(["id", "-u"]).decode().strip()
  env = os.environ.copy()
  env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
  env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
  try:
    subprocess.run(["systemctl", "--user", "stop", "wireplumber"], timeout=5, env=env)
    subprocess.run(["systemctl", "--user", "stop", "pipewire.socket"], timeout=5, env=env)
    subprocess.run(["systemctl", "--user", "stop", "pipewire"], timeout=5, env=env)
    time.sleep(2)
    result = subprocess.run(
      ["v4l2-ctl", "-d", dev_path,
       "-c", "focus_automatic_continuous=0",
       "-c", f"focus_absolute={CAMERA_FOCUS}"],
      capture_output=True, timeout=5,
    )
    if result.returncode == 0:
      logger.info("Foco manual aplicado: %d", CAMERA_FOCUS)
    else:
      logger.warning("Foco falhou: %s", result.stderr.decode().strip())
  except Exception as exc:
    logger.warning("Erro ao aplicar foco: %s", exc)
  finally:
    subprocess.run(["systemctl", "--user", "start", "pipewire.socket"], timeout=5, env=env)
    subprocess.run(["systemctl", "--user", "start", "pipewire"], timeout=5, env=env)
    subprocess.run(["systemctl", "--user", "start", "wireplumber"], timeout=5, env=env)
    time.sleep(1)


LONG_PRESS_SECONDS = 3.0


def _select_doctor(lcd) -> str:
  """Loop de seleção de médico no LCD. Retorna o nome confirmado."""
  doctor_index = 0
  selected = None
  show_doctor_selection(lcd, DOCTORS, doctor_index)
  while selected is None:
    if button_pressed(BUTTON_BOM):
      doctor_index = (doctor_index - 1) % len(DOCTORS)
      wait_to_release_button(BUTTON_BOM)
      show_doctor_selection(lcd, DOCTORS, doctor_index)
    elif button_pressed(BUTTON_PESSIMO):
      doctor_index = (doctor_index + 1) % len(DOCTORS)
      wait_to_release_button(BUTTON_PESSIMO)
      show_doctor_selection(lcd, DOCTORS, doctor_index)
    elif button_pressed(BUTTON_RUIM):
      selected = DOCTORS[doctor_index]
      wait_to_release_button(BUTTON_RUIM)
      show_doctor_confirmed(lcd, selected)
      logger.info("Medico selecionado: %s", selected)
      time.sleep(1.5)
    time.sleep(POLL_INTERVAL)
  return selected


def main() -> None:
  logger.info("Inicializando sistema...")
  init_gpio()
  lcd = init_lcd()
  lcd_msg(lcd, "Inicializando", "Aguarde...")

  # ── Detecta câmera ──
  camera = find_camera()
  if camera is None:
    logger.error("Webcam C920s não detectada.")
    lcd_msg(lcd, "Camera nao", "encontrada!")
    time.sleep(3)
  else:
    logger.info("Câmera detectada em: %s", camera)
    _apply_camera_focus(camera)

  base_dir = Path(__file__).resolve().parent / "fotos_local"
  base_dir.mkdir(exist_ok=True)
  logger.info("Diretorio base: %s", base_dir)

  # ── Seleção do médico ──
  selected_doctor = _select_doctor(lcd)
  status = Status.IDLE
  show_idle_screen(lcd)

  try:
    while True:
      if status == Status.IDLE:
        # Long press em BTN1 → troca de médico
        if button_pressed(BUTTON_BOM):
          press_start = time.time()
          long_pressed = False
          while button_pressed(BUTTON_BOM):
            elapsed = time.time() - press_start
            if elapsed >= 1.0:
              lcd_msg(lcd, "Segure...", f"Trocando em {max(0, int(LONG_PRESS_SECONDS - elapsed))}s")
            if elapsed >= LONG_PRESS_SECONDS:
              long_pressed = True
              wait_to_release_button(BUTTON_BOM)
              break
            time.sleep(0.05)
          if long_pressed:
            selected_doctor = _select_doctor(lcd)
            logger.info("Medico trocado: %s", selected_doctor)
            show_idle_screen(lcd)
          else:
            logger.info("Tier selecionado: bom")
            status = Status.CAPTURING
            selected_tier = "bom"
        else:
          # Botões de tier (ruim e pessimo)
          for pin, tier in {BUTTON_RUIM: "ruim", BUTTON_PESSIMO: "pessimo"}.items():
            if button_pressed(pin):
              logger.info("Tier selecionado: %s", tier)
              wait_to_release_button(pin)
              status = Status.CAPTURING
              selected_tier = tier
              break

      elif status == Status.CAPTURING:
        show_tier_selected(lcd, TIER_DISPLAY[selected_tier])

        if camera is None:
          lcd_msg(lcd, "Sem camera!", "Reconecte USB")
          time.sleep(MESSAGE_DISPLAY)
          status = Status.IDLE
          show_idle_screen(lcd)
          continue

        show_capturing_animation(lcd, TIER_DISPLAY[selected_tier])

        # Diretório específico do tier (cria se não existir)
        tier_dir = base_dir / TIER_FOLDER[selected_tier]
        tier_dir.mkdir(exist_ok=True)

        # Nome do arquivo: {tier}_{timestamp}_{id}.png
        photo_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{selected_tier}_{timestamp}_{photo_id}.png"
        filepath = tier_dir / filename

        if capture_photo(camera, filepath):
          logger.info("Foto salva: %s", filepath)
          metadata = build_metadata(
            photo_id=photo_id,
            filename=filename,
            filepath=filepath,
            tier=selected_tier,
          )
          metadata["doctor"] = selected_doctor
          upload_to_gcp(filepath, metadata)
          send_to_api(metadata)
          save_local_metadata(metadata, base_dir)
          show_photo_ok(lcd, TIER_DISPLAY[selected_tier])
        else:
          logger.error("Falha ao capturar foto.")
          lcd_msg(lcd, "Erro captura!", "Tente de novo")

        time.sleep(MESSAGE_DISPLAY)
        status = Status.IDLE
        show_idle_screen(lcd)

      time.sleep(POLL_INTERVAL)

  except KeyboardInterrupt:
    logger.info("Encerrando por Ctrl+C...")
  finally:
    try:
      lcd.clear()
    except Exception:
      pass
    GPIO.cleanup()


if __name__ == "__main__":
  main()
