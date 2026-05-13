import logging
import json
import logging
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import cv2
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD


# ─────────────────────────── CONFIGURAÇÃO ──────────────────────────────────────

# Pinagem (BCM)
BUTTON_BOM = 17
BUTTON_RUIM = 27
BUTTON_PESSIMO = 22
BUTTON_FOTO = 23

# LCD I2C
LCD_ADDRESS = 0x27
LCD_EXPANDER = "PCF8574"
LCD_COLS = 16

# Câmera
CAMERA_WARMUP_FRAMES = 5
CAMERA_WIDTH = 1920   # C920s: Full HD nativo
CAMERA_HEIGHT = 1080

# Identificação do dispositivo (útil quando houver mais de uma caixa)
DEVICE_ID = "raspberry-001"

# Diretórios
SCRIPT_DIR = Path(__file__).resolve().parent
FALLBACK_PHOTO_DIR = SCRIPT_DIR / "fotos_local"
METADATA_FILENAME = "metadados.jsonl"
PHOTOS_SUBDIR = "amostras_sangue"

# Mapeamento botão → tier
TIER_MAP = {
    BUTTON_BOM: "bom",
    BUTTON_RUIM: "ruim",
    BUTTON_PESSIMO: "pessimo",
}
TIER_DISPLAY = {"bom": "BOM", "ruim": "RUIM", "pessimo": "PESSIMO"}

# Timing (segundos)
POLL_INTERVAL = 0.05
MESSAGE_DISPLAY = 2.0
BUTTON_RELEASE_TIMEOUT = 2.0


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

def main() -> None:
  logger.info("Inicializando sistema...")
  init_gpio()
  lcd = init_lcd()
  lcd_msg(lcd, "Inicializando", "Aguarde...")

  camera = encontrar_camera()
  if camera is None:
    logger.error("Webcam C920s não detectada.")
    lcd_msg(lcd, "Camera nao", "encontrada!")
    time.sleep(3)
  else:
    logger.info("Câmera detectada em: %s", camera)

  out_dir, eh_pendrive = diretorio_de_saida()
  logger.info("Salvando em: %s (pendrive=%s)", out_dir, eh_pendrive)

  estado = Estado.AGUARDANDO_TIER
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
      if estado == Estado.AGUARDANDO_TIER:
        for pino, tier in TIER_MAP.items():
          if botao_pressionado(pino):
            tier_selecionado = tier
            log.info("Tier selecionado: %s", tier)
            lcd_msg(lcd, f"Tier: {TIER_DISPLAY[tier]}", "Aperte FOTO")
            aguardar_soltar_botao(pino)
            estado = Estado.AGUARDANDO_FOTO
            break

      # 2º Condição:
      elif estado == Estado.AGUARDANDO_FOTO:
        # Permite trocar o tier antes de tirar a foto
        trocou = False
        for pino, tier in TIER_MAP.items():
          if botao_pressionado(pino):
            tier_selecionado = tier
            log.info("Tier alterado para: %s", tier)
            lcd_msg(lcd, f"Tier: {TIER_DISPLAY[tier]}", "Aperte FOTO")
            aguardar_soltar_botao(pino)
            trocou = True
            break
        if not trocou and botao_pressionado(BUTTON_FOTO):
          aguardar_soltar_botao(BUTTON_FOTO)
          estado = Estado.CAPTURANDO

      elif estado == Estado.CAPTURANDO:
        lcd_msg(lcd, "Capturando...", "Aguarde")

        if camera is None:
          lcd_msg(lcd, "Sem camera!", "Reconecte USB")
          time.sleep(MESSAGE_DISPLAY)
          estado = Estado.AGUARDANDO_TIER
          tier_selecionado = None
          tela_inicial()
          continue

        photo_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{tier_selecionado}_{timestamp}_{photo_id}.png"
        filepath = out_dir / filename

        if capturar_foto(camera, filepath):
          log.info("Foto salva: %s", filepath)
          metadata = construir_metadados(
            photo_id=photo_id,
            filename=filename,
            filepath=filepath,
            tier=tier_selecionado,
          )
          salvar_metadados_local(metadata, out_dir)
          # As linhas abaixo só serão habilitadas no futuro:
          # enviar_para_api(metadata)
          # upload_para_gcp(filepath, metadata)
          lcd_msg(lcd, "Foto OK!", filename[:16])
        else:
            log.error("Falha ao capturar foto.")
            lcd_msg(lcd, "Erro captura!", "Tente de novo")

        time.sleep(MESSAGE_DISPLAY)
        estado = Estado.AGUARDANDO_TIER
        tier_selecionado = None
        tela_inicial()

      time.sleep(POLL_INTERVAL)

  except KeyboardInterrupt:
    log.info("Encerrando por Ctrl+C...")
  finally:
    try:
      lcd.clear()
    except Exception:
      pass
    GPIO.cleanup()


if __name__ == "__main__":
  main()