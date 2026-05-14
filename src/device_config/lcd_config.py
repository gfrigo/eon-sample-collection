"""Configuração e helpers do LCD 16x2 I2C (PCF8574)."""

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


def show_idle_screen(lcd: CharLCD, is_pendrive: bool) -> None:
  """
  Tela de instrução para o operador quando o sistema está pronto.

  Mostra qual botão corresponde a qual tier. Se não houver pen drive,
  alerta o operador (as fotos cairão na pasta local de fallback).
  """
  if is_pendrive:
    lcd_msg(lcd, "Selecione tier:", "1=B 2=R 3=Pes")
  else:
    lcd_msg(lcd, "SEM PENDRIVE!", "1=B 2=R 3=Pes")


def show_no_pendrive_screen(lcd: CharLCD) -> None:
  """Aviso de que o pen drive não foi detectado."""
  lcd_msg(lcd, "SEM PENDRIVE!", "Insira USB")
