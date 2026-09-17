"""Cliente da Battle.net API: token OAuth e leilões de commodities.

O endpoint de commodities é regional (não depende de realm) e devolve só a foto
atual da Auction House. O histórico é o que a ingestão acumula.
"""

import time
from typing import Any

import httpx

from .config import Settings

COPPER_PER_GOLD = 10_000
TOKEN_URL = "https://oauth.battle.net/token"


class ErroBlizzard(RuntimeError):
    pass


def valor_de_mercado(auctions: list[tuple[int, int]], cut: float = 0.15) -> tuple[float, int]:
    """Valor de mercado e quantidade total a partir de (preço_unitário, quantidade).

    Média ponderada da fatia `cut` mais barata do estoque, em vez da média simples:
    quem define o preço de venda real é o fundo da lista, e umas poucas ofertas
    absurdas no topo distorceriam a média. Preço entra em cobre, sai em ouro.
    """
    if not auctions:
        return 0.0, 0

    total = sum(q for _, q in auctions)
    alvo = max(1, int(total * cut))
    gasto = usado = 0
    for preco, qtd in sorted(auctions):
        leva = min(qtd, alvo - usado)
        gasto += preco * leva
        usado += leva
        if usado >= alvo:
            break

    return round(gasto / usado / COPPER_PER_GOLD, 4), total


def agregar(payload: dict[str, Any], cut: float = 0.15) -> dict[int, tuple[float, int]]:
    """Agrupa a resposta bruta por item e calcula valor e quantidade de cada um."""
    por_item: dict[int, list[tuple[int, int]]] = {}
    for a in payload.get("auctions", []):
        item_id = a.get("item", {}).get("id")
        preco, qtd = a.get("unit_price"), a.get("quantity")
        if item_id and preco and qtd:
            por_item.setdefault(item_id, []).append((preco, qtd))

    return {i: valor_de_mercado(lotes, cut) for i, lotes in por_item.items()}


class ClienteBlizzard:
    """Wrapper fino sobre httpx. O token é guardado até expirar."""

    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.http = client or httpx.Client(timeout=60)
        self._token = ""
        self._expira_em = 0.0

    def token(self) -> str:
        if self._token and time.time() < self._expira_em:
            return self._token

        if not self.settings.has_credentials:
            raise ErroBlizzard(
                "BLIZZARD_CLIENT_ID e BLIZZARD_CLIENT_SECRET não configurados "
                "(veja .env.example). Use `make seed` para rodar com dados fictícios."
            )

        r = self.http.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self.settings.client_id, self.settings.client_secret),
        )
        if r.status_code != 200:
            raise ErroBlizzard(f"falha ao obter token: HTTP {r.status_code}")

        dados = r.json()
        self._token = dados["access_token"]
        # 60s de folga para não usar um token que expira no meio da requisição.
        self._expira_em = time.time() + dados.get("expires_in", 3600) - 60
        return self._token

    def commodities(self, region: str) -> dict[str, Any]:
        r = self.http.get(
            f"https://{region}.api.blizzard.com/data/wow/auctions/commodities",
            params={"namespace": f"dynamic-{region}", "locale": "en_US"},
            headers={"Authorization": f"Bearer {self.token()}"},
        )
        if r.status_code != 200:
            raise ErroBlizzard(f"commodities {region}: HTTP {r.status_code}")
        return r.json()

    def item(self, region: str, item_id: int) -> dict[str, Any]:
        r = self.http.get(
            f"https://{region}.api.blizzard.com/data/wow/item/{item_id}",
            params={"namespace": f"static-{region}", "locale": "en_US"},
            headers={"Authorization": f"Bearer {self.token()}"},
        )
        if r.status_code != 200:
            raise ErroBlizzard(f"item {item_id}: HTTP {r.status_code}")
        return r.json()

    def fechar(self) -> None:
        self.http.close()
