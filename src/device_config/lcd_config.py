from RPLCD.i2c import CharLCD

# LCD I2C
LCD_ADDRESS = 0x27
LCD_EXPANDER = "PCF8574"
LCD_COLS = 16

def init_lcd() -> CharLCD:
  return CharLCD(LCD_EXPANDER, LCD_ADDRESS)

def lcd_msg(lcd: CharLCD, linha1: str, linha2: str = "") -> None:
  lcd.clear()
  lcd.write_string(linha1[:LCD_COLS])
  if linha2:
    lcd.cursor_pos = (1, 0)
    lcd.write_string(linha2[:LCD_COLS])