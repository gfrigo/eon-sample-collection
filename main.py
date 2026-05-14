import logging
import time
import uuid
from datetime import datetime

import RPi.GPIO as GPIO

from src.shared.status import Status
from src.shared.constants import (
  TIER_MAP,
  TIER_DISPLAY,
  POLL_INTERVAL,
  MESSAGE_DISPLAY,
)
from src.device_config.buttons_config import (
  init_gpio,
  button_pressed,
  wait_to_release_button,
)
from src.device_config.lcd_config import (
  init_lcd,
  lcd_msg,
  show_idle_screen,
  show_no_pendrive_screen,
)
from src.device_config.camera_config import find_camera, capture_photo
from src.device_config.pendrive_config import (
  get_output_directory,
  get_tier_directory,
)
from src.stages.metadata.load_metadata import (
  build_metadata,
  save_local_metadata,
)

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


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

  # ── Detecta pen drive (ou fallback) ──
  base_dir, is_pendrive = get_output_directory()
  logger.info(
    "Diretorio base: %s (pendrive=%s)",
    base_dir,
    is_pendrive,
  )

  status = Status.IDLE
  show_idle_screen(lcd, is_pendrive)

  try:
    while True:
      if status == Status.IDLE:
        # Aguardando seleção de tier — qualquer botão dispara a captura
        for pin, tier in TIER_MAP.items():
          if button_pressed(pin):
            logger.info("Tier selecionado: %s", tier)
            wait_to_release_button(pin)
            status = Status.CAPTURING
            selected_tier = tier
            break

      elif status == Status.CAPTURING:
        lcd_msg(lcd, "Capturando...", f"Tier: {TIER_DISPLAY[selected_tier]}")

        if camera is None:
          lcd_msg(lcd, "Sem camera!", "Reconecte USB")
          time.sleep(MESSAGE_DISPLAY)
          status = Status.IDLE
          show_idle_screen(lcd, is_pendrive)
          continue

        # Diretório específico do tier (cria se não existir)
        tier_dir = get_tier_directory(base_dir, selected_tier)

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
          save_local_metadata(metadata, base_dir)
          # As linhas abaixo serão habilitadas no futuro:
          # send_to_api(metadata)
          # upload_to_gcp(filepath, metadata)
          lcd_msg(lcd, "Foto OK!", f"Tier: {TIER_DISPLAY[selected_tier]}")
        else:
          logger.error("Falha ao capturar foto.")
          lcd_msg(lcd, "Erro captura!", "Tente de novo")

        time.sleep(MESSAGE_DISPLAY)
        status = Status.IDLE
        show_idle_screen(lcd, is_pendrive)

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
