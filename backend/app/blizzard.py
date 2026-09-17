"""Cliente da Battle.net API: token OAuth e leilões de commodities.

O endpoint de commodities é regional (não depende de realm) e devolve só a foto
atual da Auction House. O histórico é o que a ingestão acumula.
"""

import time
from typing import Any, NamedTuple

import httpx

from .config import Settings

COPPER_PER_GOLD = 10_000
TOKEN_URL = "https://oauth.battle.net/token"


class ErroBlizzard(RuntimeError):
    pass


class Agregado(NamedTuple):
    """O que uma hora de leilões de um item vira depois de agregada."""

    valor: float
    min_buyout: float
    quantidade: int


def menor_preco(auctions: list[tuple[int, int]]) -> float:
    """Menor preço unitário listado, em ouro. É o "min buyout" da interface.

    Difere do valor de mercado de propósito: este é o preço da próxima unidade
    que alguém compraria, e por isso oscila muito mais. Ver os dois juntos é o
    que mostra se o mercado está espalhado ou concentrado.
    """
    if not auctions:
        return 0.0
    return round(min(preco for preco, _ in auctions) / COPPER_PER_GOLD, 4)


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


def agregar(payload: dict[str, Any], cut: float = 0.15) -> dict[int, Agregado]:
    """Agrupa a resposta bruta por item e reduz cada um a três números."""
    por_item: dict[int, list[tuple[int, int]]] = {}
    for a in payload.get("auctions", []):
        item_id = a.get("item", {}).get("id")
        preco, qtd = a.get("unit_price"), a.get("quantity")
        if item_id and preco and qtd:
            por_item.setdefault(item_id, []).append((preco, qtd))

    agregados = {}
    for item_id, lotes in por_item.items():
        valor, quantidade = valor_de_mercado(lotes, cut)
        agregados[item_id] = Agregado(valor, menor_preco(lotes), quantidade)
    return agregados


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

    def item(self, region: str, item_id: int, locale: str = "en_US") -> dict[str, Any]:
        r = self.http.get(
            f"https://{region}.api.blizzard.com/data/wow/item/{item_id}",
            params={"namespace": f"static-{region}", "locale": locale},
            headers={"Authorization": f"Bearer {self.token()}"},
        )
        if r.status_code != 200:
            raise ErroBlizzard(f"item {item_id}: HTTP {r.status_code}")
        return r.json()

    def icone(self, region: str, item_id: int) -> str | None:
        """URL do ícone do item, ou None se a API não tiver uma.

        Guardamos a URL, não a imagem: a arte é da Blizzard e fica servida pelo
        CDN dela.
        """
        try:
            r = self.http.get(
                f"https://{region}.api.blizzard.com/data/wow/media/item/{item_id}",
                params={"namespace": f"static-{region}"},
                headers={"Authorization": f"Bearer {self.token()}"},
            )
            if r.status_code != 200:
                return None
            for asset in r.json().get("assets", []):
                if asset.get("key") == "icon":
                    return str(asset["value"])
        except (httpx.HTTPError, KeyError, ValueError):
            return None
        return None

    def nomes(self, region: str, item_id: int) -> tuple[str, str | None]:
        """Nome em inglês e em português do mesmo item.

        São duas requisições porque o endpoint devolve um idioma por chamada.
        O inglês é obrigatório (é a chave de busca); o português é o que falha
        de forma tolerável, então um erro nele devolve None em vez de explodir.
        """
        try:
            en = str(self.item(region, item_id, "en_US")["name"])
        except KeyError as e:
            raise ErroBlizzard(f"item {item_id}: resposta sem 'name'") from e

        try:
            pt: str | None = str(self.item(region, item_id, "pt_BR")["name"])
        except (ErroBlizzard, KeyError):
            pt = None
        return en, pt

    def fechar(self) -> None:
        self.http.close()
