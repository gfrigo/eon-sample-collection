def init_lcd() -> CharLCD:
    return CharLCD(LCD_EXPANDER, LCD_ADDRESS)

def lcd_msg(lcd: CharLCD, linha1: str, linha2: str = "") -> None:
    lcd.clear()
    lcd.write_string(linha1[:LCD_COLS])
    if linha2:
        lcd.cursor_pos = (1, 0)
        lcd.write_string(linha2[:LCD_COLS])