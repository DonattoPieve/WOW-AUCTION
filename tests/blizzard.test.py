"""Testes do cliente da Battle.net API.

Nenhum teste aqui toca a rede: o `httpx.MockTransport` responde no lugar dela.
Teste que depende de internet falha por motivo errado e ninguém confia nele
depois da terceira vez.
"""

import httpx
import pytest

from backend.app.blizzard import (
    COPPER_PER_GOLD,
    ClienteBlizzard,
    ErroBlizzard,
    agregar,
    valor_de_mercado,
)
from backend.app.config import Settings

CREDENCIAIS = Settings(
    db_path="/tmp/nao-usado.db",  # type: ignore[arg-type]
    client_id="id-de-teste",
    client_secret="segredo-de-teste",
    market_value_cut=0.15,
)

SEM_CREDENCIAIS = Settings(
    db_path="/tmp/nao-usado.db",  # type: ignore[arg-type]
    client_id="",
    client_secret="",
    market_value_cut=0.15,
)


def cliente_falso(rotas) -> ClienteBlizzard:
    """Monta um ClienteBlizzard cujo transporte é a função `rotas`."""
    return ClienteBlizzard(CREDENCIAIS, httpx.Client(transport=httpx.MockTransport(rotas)))


def responder(req: httpx.Request) -> httpx.Response:
    """Transporte padrão: devolve token e dois leilões."""
    if req.url.host == "oauth.battle.net":
        return httpx.Response(200, json={"access_token": "abc123", "expires_in": 3600})
    if "commodities" in req.url.path:
        return httpx.Response(
            200,
            json={
                "auctions": [
                    {"item": {"id": 1}, "unit_price": 10_000, "quantity": 100},
                    {"item": {"id": 1}, "unit_price": 20_000, "quantity": 100},
                ]
            },
        )
    return httpx.Response(404)


# --------------------------------------------------------------------------
# valor_de_mercado
# --------------------------------------------------------------------------


def test_valor_de_mercado_converte_cobre_em_ouro():
    valor, qtd = valor_de_mercado([(COPPER_PER_GOLD * 25, 10)])

    assert valor == 25.0
    assert qtd == 10


def test_valor_de_mercado_fica_muito_abaixo_da_media_simples():
    # 100 unidades a 1g e 900 a 100g. A média ponderada de tudo dá 90.1g — um
    # preço que ninguém consegue praticar. O corte de 15% pega as 150 unidades
    # mais baratas (as 100 a 1g, mais 50 a 100g) e chega a 34g.
    lotes = [(1 * COPPER_PER_GOLD, 100), (100 * COPPER_PER_GOLD, 900)]

    valor, qtd = valor_de_mercado(lotes, cut=0.15)

    assert qtd == 1000
    assert valor == pytest.approx(34.0)
    assert valor < valor_de_mercado(lotes, cut=1.0)[0]  # menor que a média de tudo


def test_valor_de_mercado_ignora_oferta_absurda_no_topo():
    normais = [(10 * COPPER_PER_GOLD, 1000)]
    com_outlier = [*normais, (50_000 * COPPER_PER_GOLD, 1)]

    assert valor_de_mercado(normais)[0] == valor_de_mercado(com_outlier)[0]


def test_valor_de_mercado_com_lista_vazia_devolve_zero():
    assert valor_de_mercado([]) == (0.0, 0)


def test_valor_de_mercado_com_corte_minusculo_ainda_usa_uma_unidade():
    # Um corte que arredondaria para zero unidades não pode dividir por zero.
    valor, qtd = valor_de_mercado([(7 * COPPER_PER_GOLD, 10)], cut=0.0001)

    assert valor == 7.0
    assert qtd == 10


def test_corte_maior_inclui_as_ofertas_caras():
    lotes = [(1 * COPPER_PER_GOLD, 500), (9 * COPPER_PER_GOLD, 500)]

    barato = valor_de_mercado(lotes, cut=0.1)[0]
    tudo = valor_de_mercado(lotes, cut=1.0)[0]

    assert barato == 1.0
    assert tudo == 5.0  # média ponderada das duas metades


# --------------------------------------------------------------------------
# agregar
# --------------------------------------------------------------------------


def test_agregar_agrupa_por_item():
    payload = {
        "auctions": [
            {"item": {"id": 1}, "unit_price": COPPER_PER_GOLD, "quantity": 5},
            {"item": {"id": 1}, "unit_price": COPPER_PER_GOLD, "quantity": 5},
            {"item": {"id": 2}, "unit_price": 3 * COPPER_PER_GOLD, "quantity": 2},
        ]
    }

    resultado = agregar(payload)

    assert set(resultado) == {1, 2}
    assert resultado[1] == (1.0, 10)
    assert resultado[2] == (3.0, 2)


def test_agregar_descarta_leilao_sem_campo_obrigatorio():
    payload = {
        "auctions": [
            {"item": {}, "unit_price": 100, "quantity": 1},  # sem id
            {"item": {"id": 3}, "quantity": 1},  # sem preço
            {"item": {"id": 4}, "unit_price": 100},  # sem quantidade
            {"item": {"id": 5}, "unit_price": COPPER_PER_GOLD, "quantity": 1},
        ]
    }

    assert set(agregar(payload)) == {5}


def test_agregar_com_resposta_vazia_nao_quebra():
    assert agregar({}) == {}


# --------------------------------------------------------------------------
# ClienteBlizzard
# --------------------------------------------------------------------------


def test_token_e_pedido_uma_vez_e_reaproveitado():
    chamadas = []

    def rotas(req):
        chamadas.append(str(req.url))
        return responder(req)

    c = cliente_falso(rotas)
    c.commodities("us")
    c.commodities("us")

    assert sum(1 for u in chamadas if "oauth" in u) == 1


def test_token_expirado_e_renovado():
    chamadas = []

    def rotas(req):
        chamadas.append(str(req.url))
        if req.url.host == "oauth.battle.net":
            # expires_in=0 menos a folga de 60s: o token já nasce vencido.
            return httpx.Response(200, json={"access_token": "t", "expires_in": 0})
        return responder(req)

    c = cliente_falso(rotas)
    c.commodities("us")
    c.commodities("us")

    # Duas chamadas, dois tokens: o cliente não reaproveitou o que venceu.
    assert sum(1 for u in chamadas if "oauth" in u) == 2


def test_sem_credenciais_erro_aponta_para_o_seed():
    c = ClienteBlizzard(SEM_CREDENCIAIS, httpx.Client(transport=httpx.MockTransport(responder)))

    with pytest.raises(ErroBlizzard, match=r"seed|semente|BLIZZARD_CLIENT_ID"):
        c.token()


def test_token_recusado_virou_erro_de_dominio():
    def rotas(req):
        return httpx.Response(401, json={"error": "invalid_client"})

    with pytest.raises(ErroBlizzard, match="401"):
        cliente_falso(rotas).token()


def test_commodities_manda_o_namespace_da_regiao():
    vistas = []

    def rotas(req):
        vistas.append(req.url)
        return responder(req)

    cliente_falso(rotas).commodities("eu")
    url = next(u for u in vistas if "commodities" in u.path)

    assert url.host == "eu.api.blizzard.com"
    assert url.params["namespace"] == "dynamic-eu"


def test_commodities_manda_o_bearer():
    vistos = []

    def rotas(req):
        vistos.append(req.headers.get("authorization"))
        return responder(req)

    cliente_falso(rotas).commodities("us")

    assert "Bearer abc123" in vistos


def test_erro_http_na_commodities_virou_erro_de_dominio():
    def rotas(req):
        if req.url.host == "oauth.battle.net":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(503)

    with pytest.raises(ErroBlizzard, match="503"):
        cliente_falso(rotas).commodities("us")
