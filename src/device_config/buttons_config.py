import time

import RPi.GPIO as GPIO

# Pinagem
BUTTON_BOM = 17
BUTTON_RUIM = 27
BUTTON_PESSIMO = 22
BUTTON_FOTO = 23
BUTTON_RELEASE_TIMEOUT = 2.0

def init_gpio() -> None:
  GPIO.setmode(GPIO.BCM)
  GPIO.setwarnings(False)
  for pin in (BUTTON_BOM, BUTTON_RUIM, BUTTON_PESSIMO, BUTTON_FOTO):
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_pressed(pino:int) -> bool:
  return GPIO.input(pino) == GPIO.LOW

def wait_to_release_button(pino:int, timeout:float=BUTTON_RELEASE_TIMEOUT) -> None:
  """Espera o botão voltar a HIGH antes de continuar (debounce simples)."""
  t0 = time.time()
  while GPIO.input(pino) == GPIO.LOW and (time.time() - t0) < timeout:
    time.sleep(0.01)
  # pequena folga adicional para descartar bounce mecânico
  time.sleep(0.05)