"""Configuração lida do ambiente.

Sem pydantic-settings de propósito: `os.environ` resolve, e uma dependência a
menos é uma dependência a menos para manter.
"""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REGIONS = ("us", "eu")

# Faixas do gráfico, em horas. A AH da Blizzard atualiza de hora em hora,
# então uma hora é a menor granularidade que faz sentido guardar.
RANGES = {
    "daily": 24,
    "weekly": 24 * 7,
    "monthly": 24 * 30,
    "quarter": 24 * 90,
    "half-year": 24 * 182,
    "year": 24 * 365,
}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    client_id: str
    client_secret: str
    # Fração da quantidade mais barata que entra no valor de mercado (ver ADR 0003).
    market_value_cut: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.environ.get("WOW_DB_PATH", ROOT / "wow.db")),
            client_id=os.environ.get("BLIZZARD_CLIENT_ID", ""),
            client_secret=os.environ.get("BLIZZARD_CLIENT_SECRET", ""),
            market_value_cut=float(os.environ.get("WOW_MARKET_VALUE_CUT", "0.15")),
        )

    @property
    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)


settings = Settings.from_env()
