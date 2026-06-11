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
  MODE_MANUAL,
  MODE_IA,
  MODES,
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
  show_idle_screen_ia,
  show_tier_selected,
  show_capturing_animation,
  show_classifying_animation,
  show_ai_result,
  show_photo_ok,
  show_doctor_selection,
  show_doctor_confirmed,
  show_mode_selection,
  show_mode_confirmed,
)
from src.device_config.camera_config import find_camera, capture_photo, CAMERA_FOCUS
from src.stages.metadata.load_metadata import (
  build_metadata,
  save_local_metadata,
)
from src.stages.gcp.load_to_storage import upload_to_gcp
from src.stages.api.send_to_api import send_to_api
from src.stages.ml.inference import classify_image, get_model_version, is_model_available

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _run_quiet(cmd, env=None) -> None:
  """Executa um comando ignorando falhas/timeouts (ex: systemctl --user sem sessao ativa)."""
  try:
    subprocess.run(cmd, timeout=5, env=env, capture_output=True)
  except Exception as exc:
    logger.debug("Comando %s falhou: %s", cmd, exc)


def _apply_camera_focus(device) -> None:
  import os
  dev_path = f"/dev/video{device}"
  uid = subprocess.check_output(["id", "-u"]).decode().strip()
  env = os.environ.copy()
  env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
  env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
  try:
    _run_quiet(["systemctl", "--user", "stop", "wireplumber"], env=env)
    _run_quiet(["systemctl", "--user", "stop", "pipewire.socket"], env=env)
    _run_quiet(["systemctl", "--user", "stop", "pipewire"], env=env)
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
    _run_quiet(["systemctl", "--user", "start", "pipewire.socket"], env=env)
    _run_quiet(["systemctl", "--user", "start", "pipewire"], env=env)
    _run_quiet(["systemctl", "--user", "start", "wireplumber"], env=env)
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


def _select_mode(lcd) -> str:
  """Loop de seleção do modo de operação no LCD. Retorna MODE_MANUAL ou MODE_IA."""
  mode_index = 0
  selected = None
  show_mode_selection(lcd, MODES, mode_index)
  while selected is None:
    if button_pressed(BUTTON_BOM):
      mode_index = (mode_index - 1) % len(MODES)
      wait_to_release_button(BUTTON_BOM)
      show_mode_selection(lcd, MODES, mode_index)
    elif button_pressed(BUTTON_PESSIMO):
      mode_index = (mode_index + 1) % len(MODES)
      wait_to_release_button(BUTTON_PESSIMO)
      show_mode_selection(lcd, MODES, mode_index)
    elif button_pressed(BUTTON_RUIM):
      selected = MODES[mode_index][0]
      wait_to_release_button(BUTTON_RUIM)
      show_mode_confirmed(lcd, MODES[mode_index][1])
      logger.info("Modo selecionado: %s", selected)
      time.sleep(1.5)
    time.sleep(POLL_INTERVAL)
  return selected


def _show_idle(lcd, mode: str) -> None:
  if mode == MODE_IA:
    show_idle_screen_ia(lcd)
  else:
    show_idle_screen(lcd)


def _is_long_press(pin, lcd, message: str) -> bool:
  """Bloqueia enquanto o botão estiver pressionado; retorna True se foi long press."""
  press_start = time.time()
  while button_pressed(pin):
    elapsed = time.time() - press_start
    if elapsed >= 1.0:
      lcd_msg(lcd, "Segure...", f"{message} {max(0, int(LONG_PRESS_SECONDS - elapsed))}s")
    if elapsed >= LONG_PRESS_SECONDS:
      wait_to_release_button(pin)
      return True
    time.sleep(0.05)
  return False


def _select_mode_safe(lcd) -> str:
  """Seleciona o modo no LCD; volta para Manual se IA Auto for escolhido sem modelo disponível."""
  mode = _select_mode(lcd)
  if mode == MODE_IA and not is_model_available():
    logger.warning("Modo IA selecionado, mas model.tflite nao foi encontrado. Usando modo Manual.")
    lcd_msg(lcd, "Modelo nao", "encontrado!")
    time.sleep(2)
    mode = MODE_MANUAL
  return mode


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

  # ── Seleção do modo de operação ──
  mode = _select_mode_safe(lcd)

  status = Status.IDLE
  _show_idle(lcd, mode)

  try:
    while True:
      if status == Status.IDLE:
        # Long press em BTN1 → troca de usuário
        if button_pressed(BUTTON_BOM):
          if _is_long_press(BUTTON_BOM, lcd, "Trocando em"):
            selected_doctor = _select_doctor(lcd)
            logger.info("Usuario trocado: %s", selected_doctor)
            _show_idle(lcd, mode)
          elif mode == MODE_MANUAL:
            logger.info("Tier selecionado: bom")
            status = Status.CAPTURING
            selected_tier = "bom"
          # modo IA: toque curto em BTN1 não faz nada (sem seleção manual de tier)

        # Long press em BTN3 → troca de modo (Manual / IA Auto)
        elif button_pressed(BUTTON_PESSIMO):
          if _is_long_press(BUTTON_PESSIMO, lcd, "Modo em"):
            mode = _select_mode_safe(lcd)
            logger.info("Modo trocado: %s", mode)
            _show_idle(lcd, mode)
          elif mode == MODE_MANUAL:
            logger.info("Tier selecionado: pessimo")
            status = Status.CAPTURING
            selected_tier = "pessimo"
          # modo IA: toque curto em BTN3 não faz nada (sem seleção manual de tier)

        elif mode == MODE_MANUAL:
          # Botão de tier "ruim"
          if button_pressed(BUTTON_RUIM):
            logger.info("Tier selecionado: ruim")
            wait_to_release_button(BUTTON_RUIM)
            status = Status.CAPTURING
            selected_tier = "ruim"

        else:
          # Modo IA: BTN2 dispara a captura, a IA define o tier depois
          if button_pressed(BUTTON_RUIM):
            logger.info("Captura solicitada (modo IA)")
            wait_to_release_button(BUTTON_RUIM)
            status = Status.CAPTURING
            selected_tier = None

      elif status == Status.CAPTURING:
        if camera is None:
          lcd_msg(lcd, "Sem camera!", "Reconecte USB")
          time.sleep(MESSAGE_DISPLAY)
          status = Status.IDLE
          _show_idle(lcd, mode)
          continue

        photo_id = uuid.uuid4().hex[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if mode == MODE_IA:
          show_capturing_animation(lcd, "IA")
          tmp_path = base_dir / f"_tmp_{photo_id}.png"

          if not capture_photo(camera, tmp_path):
            logger.error("Falha ao capturar foto.")
            lcd_msg(lcd, "Erro captura!", "Tente de novo")
            time.sleep(MESSAGE_DISPLAY)
            status = Status.IDLE
            _show_idle(lcd, mode)
            continue

          show_classifying_animation(lcd)
          try:
            predicted_tier, confidence = classify_image(tmp_path)
          except Exception as exc:
            logger.error("Falha na inferencia: %s", exc)
            lcd_msg(lcd, "Erro na IA!", "Tente de novo")
            time.sleep(MESSAGE_DISPLAY)
            tmp_path.unlink(missing_ok=True)
            status = Status.IDLE
            _show_idle(lcd, mode)
            continue

          tier_dir = base_dir / TIER_FOLDER[predicted_tier]
          tier_dir.mkdir(exist_ok=True)
          filename = f"{predicted_tier}_{timestamp}_{photo_id}.png"
          filepath = tier_dir / filename
          tmp_path.rename(filepath)
          logger.info("Foto salva: %s", filepath)

          show_ai_result(lcd, TIER_DISPLAY[predicted_tier], confidence)
          time.sleep(MESSAGE_DISPLAY)

          metadata = build_metadata(
            photo_id=photo_id,
            filename=filename,
            filepath=filepath,
            tier=predicted_tier,
            mode=MODE_IA,
            confidence=confidence,
            model_version=get_model_version(),
          )
          metadata["doctor"] = selected_doctor
          upload_to_gcp(filepath, metadata)
          send_to_api(metadata)
          save_local_metadata(metadata, base_dir)
          show_photo_ok(lcd, TIER_DISPLAY[predicted_tier])

        else:
          show_tier_selected(lcd, TIER_DISPLAY[selected_tier])
          show_capturing_animation(lcd, TIER_DISPLAY[selected_tier])

          tier_dir = base_dir / TIER_FOLDER[selected_tier]
          tier_dir.mkdir(exist_ok=True)
          filename = f"{selected_tier}_{timestamp}_{photo_id}.png"
          filepath = tier_dir / filename

          if capture_photo(camera, filepath):
            logger.info("Foto salva: %s", filepath)
            metadata = build_metadata(
              photo_id=photo_id,
              filename=filename,
              filepath=filepath,
              tier=selected_tier,
              mode=MODE_MANUAL,
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
        _show_idle(lcd, mode)

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
