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
  """Tela de instrução para o operador quando o sistema está pronto (modo manual)."""
  lcd_msg(lcd, "Selecione grau:", "1=G1 2=G2 3=G3")


def show_idle_screen_ia(lcd: CharLCD) -> None:
  """Tela de instrução para o operador quando o sistema está pronto (modo IA)."""
  lcd_msg(lcd, "Modo IA Auto", "OK = Capturar")


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


def show_mode_selection(lcd: CharLCD, modes: list, index: int) -> None:
  """Exibe tela de seleção de modo de operação (Manual / IA Auto)."""
  _, label = modes[index]
  total = len(modes)
  lcd.clear()
  lcd.write_string(f"< {label:<11} >"[:LCD_COLS])
  lcd.cursor_pos = (1, 0)
  lcd.write_string(f"Ant OK Prox {index+1}/{total}"[:LCD_COLS])


def show_mode_confirmed(lcd: CharLCD, mode_label: str) -> None:
  """Confirmação após selecionar o modo de operação."""
  lcd_msg(lcd, "Modo:", mode_label[:LCD_COLS])


def show_classifying_animation(lcd: CharLCD) -> None:
  """Anima três frames de pontos enquanto a IA classifica a foto."""
  for dots in (".", "..", "..."):
    lcd.clear()
    lcd.write_string(f"Classificando{dots}"[:LCD_COLS])
    time.sleep(0.3)


def show_ai_result(lcd: CharLCD, tier_display: str, confidence: float) -> None:
  """Exibe o resultado da classificação automática (tier + confiança)."""
  lcd.clear()
  lcd.write_string(f"IA: {tier_display}"[:LCD_COLS])
  lcd.cursor_pos = (1, 0)
  lcd.write_string(f"Confianca: {confidence * 100:.0f}%"[:LCD_COLS])
