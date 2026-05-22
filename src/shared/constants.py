"""Constantes compartilhadas entre os módulos do sistema."""

from src.device_config.buttons_config import (
  BUTTON_BOM,
  BUTTON_RUIM,
  BUTTON_PESSIMO,
)

# Identificação do dispositivo (útil quando houver mais de uma caixa em campo)
DEVICE_ID = "raspberry-001"

# Mapeamento: pino do botão → identificador interno do tier
TIER_MAP = {
  BUTTON_BOM: "bom",
  BUTTON_RUIM: "ruim",
  BUTTON_PESSIMO: "pessimo",
}

# Mapeamento: tier interno → texto exibido no LCD (curto, máximo 7 chars)
TIER_DISPLAY = {
  "bom": "BOM",
  "ruim": "RUIM",
  "pessimo": "PESSIMO",
}

# Mapeamento: tier interno → nome da pasta de armazenamento das fotos
TIER_FOLDER = {
  "bom": "amostras_boas",
  "ruim": "amostras_ruins",
  "pessimo": "amostras_pessimas",
}

# Lista de médicos disponíveis para seleção no início da sessão
DOCTORS = [f"Medico {i:02d}" for i in range(1, 13)]  # Medico 01 a Medico 12

# Timings (em segundos)
POLL_INTERVAL = 0.05      # Intervalo de leitura dos botões no loop principal
MESSAGE_DISPLAY = 2.0     # Tempo que mensagens de status ficam visíveis no LCD
