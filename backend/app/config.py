"""Configuração lida do ambiente.

Sem pydantic-settings de propósito: `os.environ` resolve, e uma dependência a
menos é uma dependência a menos para manter.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[2]

REGIONS = ("us", "eu")

# O app é fixado num realm só: Area 52, região US (connected realm 3676).
#
# ATENÇÃO, e isto vale estar escrito onde não se perde: o endpoint de
# commodities da Blizzard é REGIONAL, não por realm. O preço de minério que
# este app mostra é o mesmo para Area 52, Illidan, Stormrage e qualquer outro
# realm dos EUA — commodities têm um mercado único por região. O realm só
# passaria a importar se o projeto ingerisse itens não-commodity (armas,
# armaduras), que usam o endpoint
# /data/wow/connected-realm/{id}/auctions e aí sim são por realm.
#
# Ou seja: "Area 52" na interface identifica o realm do jogador, e os números
# são corretos para ele. Não são exclusivos dele.
REGIAO_PADRAO: Literal["us", "eu"] = "us"

REALM = {
    "nome": "Area 52",
    "slug": "area-52",
    "region": REGIAO_PADRAO,
    "connected_realm_id": 3676,
}

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
