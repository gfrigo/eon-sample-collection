from enum import Enum


class Status(Enum):
  """Estados do sistema durante o fluxo de captura."""

  IDLE = "idle"             # Aguardando o usuário apertar um botão de tier
  CAPTURING = "capturing"   # Foto sendo tirada e salva
