import logging
import time
import uuid
from datetime import datetime

import RPi.GPIO as GPIO

from src.shared.status import Status
from src.device_config.buttons_config import (
  BUTTON_BOM,
  BUTTON_RUIM,
  BUTTON_PESSIMO,
  init_gpio,
  button_pressed,
  wait_to_release_button
)
from src.device_config.lcd_config import init_lcd, lcd_msg
from src.device_config.camera_config import find_camera, capture_photo
from src.device_config.pendrive_config import get_output_directory
from src.stages.metadata.load_metadata import build_metadata, save_local_metadata

# Mapeamento botão → tier
TIER_MAP = {
  BUTTON_BOM: "bom",
  BUTTON_RUIM: "ruim",
  BUTTON_PESSIMO: "pessimo",
}

TIER_DISPLAY = {
  "bom": "BOM",
  "ruim": "RUIM",
  "pessimo": "PESSIMO",
}

# Timing (segundos)
POLL_INTERVAL = 0.05
MESSAGE_DISPLAY = 2.0

logger = logging.getLogger(__name__)


def main() -> None:
  logger.info("Inicializando sistema...")

  init_gpio()

  lcd = init_lcd()

  lcd_msg(lcd, "Inicializando", "Aguarde...")

  camera = find_camera()

  if camera is None:
    logger.error("Webcam C920s não detectada.")
    lcd_msg(lcd, "Camera nao", "encontrada!")
    time.sleep(3)
  else:
    logger.info("Câmera detectada em: %s", camera)

  out_dir, eh_pendrive = get_output_directory()

  logger.info(
    "Salvando em: %s (pendrive=%s)",
    out_dir,
    eh_pendrive,
  )

  status = Status.AGUARDANDO_TIER
  tier_selecionado: str | None = None

  def tela_inicial() -> None:
    if eh_pendrive:
      lcd_msg(lcd, "Selecione tier:", "1=B 2=R 3=P")
    else:
      lcd_msg(lcd, "SEM PENDRIVE!", "1=B 2=R 3=P")

  tela_inicial()

  try:
    while True:

      # 1º Condição:
      if status == Status.AGUARDANDO_TIER:
        for pino, tier in TIER_MAP.items():
          if button_pressed(pino):
            tier_selecionado = tier

            logger.info("Tier selecionado: %s", tier)

            lcd_msg(
              lcd,
              f"Tier: {TIER_DISPLAY[tier]}",
              "Aperte FOTO",
            )

            wait_to_release_button(pino)

            status = Status.AGUARDANDO_FOTO

            break

      # 2º Condição:
      elif status == Status.AGUARDANDO_FOTO:

        # Permite trocar o tier antes de tirar a foto
        trocou = False

        for pino, tier in TIER_MAP.items():
          if button_pressed(pino):
            tier_selecionado = tier

            logger.info("Tier alterado para: %s", tier)

            lcd_msg(
              lcd,
              f"Tier: {TIER_DISPLAY[tier]}",
              "Aperte FOTO",
            )

            wait_to_release_button(pino)

            trocou = True

            break

        if not trocou and button_pressed(23):
          wait_to_release_button(23)

          status = Status.CAPTURANDO

      elif status == Status.CAPTURANDO:
        lcd_msg(lcd, "Capturando...", "Aguarde")

        if camera is None:
          lcd_msg(lcd, "Sem camera!", "Reconecte USB")

          time.sleep(MESSAGE_DISPLAY)

          status = Status.AGUARDANDO_TIER
          tier_selecionado = None

          tela_inicial()

          continue

        photo_id = uuid.uuid4().hex[:12]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{tier_selecionado}_{timestamp}_{photo_id}.png"

        filepath = out_dir / filename

        if capture_photo(camera, filepath):
          logger.info("Foto salva: %s", filepath)

          metadata = build_metadata(
            photo_id=photo_id,
            filename=filename,
            filepath=filepath,
            tier=tier_selecionado,
          )

          save_local_metadata(metadata, out_dir)

          # As linhas abaixo só serão habilitadas no futuro:
          # enviar_para_api(metadata)
          # upload_para_gcp(filepath, metadata)

          lcd_msg(lcd, "Foto OK!", filename[:16])

        else:
          logger.error("Falha ao capturar foto.")

          lcd_msg(
            lcd,
            "Erro captura!",
            "Tente de novo",
          )

        time.sleep(MESSAGE_DISPLAY)

        status = Status.AGUARDANDO_TIER
        tier_selecionado = None

        tela_inicial()

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