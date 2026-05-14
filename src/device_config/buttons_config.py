"""Configuração e helpers dos botões PBS-29 conectados via GPIO."""

import time

import RPi.GPIO as GPIO

# ── Pinagem dos botões (BCM) ──
# Cada botão tem 2 pernas: uma vai para o GPIO, outra para GND.
BUTTON_BOM = 17       # Pino 11 → GND (Pino 9)
BUTTON_RUIM = 27      # Pino 13 → GND (Pino 14)
BUTTON_PESSIMO = 22   # Pino 15 → GND (Pino 20)

# Lista dos botões usados pelo sistema (facilita iterações)
ALL_BUTTONS = (BUTTON_BOM, BUTTON_RUIM, BUTTON_PESSIMO)

# Timeout máximo (em segundos) ao aguardar o usuário soltar um botão
BUTTON_RELEASE_TIMEOUT = 2.0


def init_gpio() -> None:
  """Configura o modo BCM e ativa pull-up interno em cada pino de botão."""
  GPIO.setmode(GPIO.BCM)
  GPIO.setwarnings(False)
  for pin in ALL_BUTTONS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def button_pressed(pin: int) -> bool:
  """Retorna True se o botão estiver pressionado (nível LOW por causa do pull-up)."""
  return GPIO.input(pin) == GPIO.LOW


def wait_to_release_button(
  pin: int,
  timeout: float = BUTTON_RELEASE_TIMEOUT,
) -> None:
  """Aguarda o botão voltar para HIGH antes de continuar (debounce simples)."""
  start = time.time()
  while GPIO.input(pin) == GPIO.LOW and (time.time() - start) < timeout:
    time.sleep(0.01)
  # Pequena folga adicional para descartar bounce mecânico residual
  time.sleep(0.05)
