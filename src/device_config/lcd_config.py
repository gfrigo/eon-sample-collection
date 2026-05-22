"""Configuração e helpers do LCD 16x2 I2C (PCF8574)."""

import time

from RPLCD.i2c import CharLCD

# ── Configuração do LCD ──
LCD_ADDRESS = 0x27
LCD_EXPANDER = "PCF8574"
LCD_COLS = 16


def init_lcd() -> CharLCD:
  """Instancia e retorna o controlador do LCD."""
  return CharLCD(LCD_EXPANDER, LCD_ADDRESS)


def lcd_msg(lcd: CharLCD, line1: str, line2: str = "") -> None:
  """Limpa o display e escreve até 2 linhas (16 caracteres por linha)."""
  lcd.clear()
  lcd.write_string(line1[:LCD_COLS])
  if line2:
    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2[:LCD_COLS])


def show_idle_screen(lcd: CharLCD) -> None:
  """Tela de instrução para o operador quando o sistema está pronto."""
  lcd_msg(lcd, "Selecione tier:", "1=B 2=R 3=Pes")


def show_tier_selected(lcd: CharLCD, tier_display: str) -> None:
  """Confirmação visual breve ao pressionar o botão de tier."""
  lcd.clear()
  lcd.write_string(f"> Tier: {tier_display}"[:LCD_COLS])
  lcd.cursor_pos = (1, 0)
  lcd.write_string("Confirmado!")
  time.sleep(0.5)


def show_capturing_animation(lcd: CharLCD, tier_display: str) -> None:
  """Anima três frames de pontos enquanto a câmera captura."""
  for dots in (".", "..", "..."):
    lcd.clear()
    lcd.write_string(f"Capturando{dots}"[:LCD_COLS])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(f"Tier: {tier_display}"[:LCD_COLS])
    time.sleep(0.3)


def show_doctor_selection(lcd: CharLCD, doctors: list, index: int) -> None:
  """Exibe tela de seleção de médico com navegação pelos botões."""
  name = doctors[index][:12]
  total = len(doctors)
  lcd.clear()
  lcd.write_string(f"< {name:<12} >"[:LCD_COLS])
  lcd.cursor_pos = (1, 0)
  lcd.write_string(f"Ant OK Prox {index+1}/{total}"[:LCD_COLS])


def show_doctor_confirmed(lcd: CharLCD, doctor: str) -> None:
  """Confirmação após selecionar o médico."""
  lcd_msg(lcd, f"Ola,", doctor[:LCD_COLS])


def show_photo_ok(lcd: CharLCD, tier_display: str) -> None:
  """Flash + confirmação de foto salva com sucesso."""
  lcd.clear()
  time.sleep(0.08)
  lcd.write_string("** Foto OK! **")
  lcd.cursor_pos = (1, 0)
  lcd.write_string(f"Tier: {tier_display}"[:LCD_COLS])
