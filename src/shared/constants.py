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
  "bom": "GRAU 1",
  "ruim": "GRAU 2",
  "pessimo": "GRAU 3",
}

# Mapeamento: tier interno → nome da pasta de armazenamento das fotos
TIER_FOLDER = {
  "bom": "amostras_boas",
  "ruim": "amostras_ruins",
  "pessimo": "amostras_pessimas",
}

# Lista de usuários disponíveis para seleção no início da sessão
DOCTORS = [f"Usuario {i:02d}" for i in range(1, 13)]  # Usuario 01 a Usuario 12

# ── Modos de operação ──
MODE_MANUAL = "manual"   # Operador escolhe o tier pelos botões antes da captura
MODE_IA = "ia"           # Captura e o modelo de IA classifica automaticamente

# Ordem de exibição na tela de seleção de modo (valor interno, texto no LCD)
MODES = [
  (MODE_MANUAL, "Manual"),
  (MODE_IA, "IA Auto"),
]

# Timings (em segundos)
POLL_INTERVAL = 0.05      # Intervalo de leitura dos botões no loop principal
MESSAGE_DISPLAY = 2.0     # Tempo que mensagens de status ficam visíveis no LCD
