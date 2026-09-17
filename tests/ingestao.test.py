"""Testes da ingestão: alinhamento de hora, idempotência e cálculo de vendas.

A idempotência é a promessa central da arquitetura (ADR 0004): reprocessar a
mesma hora tem de sobrescrever, nunca duplicar. Se algum teste deste arquivo
falhar, o retry do agendador deixou de ser seguro.
"""

import httpx
import pytest

from backend.app import banco, ingestao
from backend.app.config import Settings

HOUR = 3600
TS = 1_767_225_600  # 2026-01-01 00:00:00 UTC


@pytest.fixture
def conn(tmp_path):
    c = banco.conectar(tmp_path / "ingestao.db")
    banco.criar_esquema(c)
    yield c
    c.close()


def total_linhas(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM snapshots").fetchone()["n"]


# ---------------------------------------------------------------------------
# hora_cheia
# ---------------------------------------------------------------------------


def test_hora_cheia_trunca_para_baixo():
    assert ingestao.hora_cheia(TS + 59 * 60) == TS


def test_hora_cheia_e_estavel_dentro_da_mesma_hora():
    # Rodar às 14:03 ou às 14:58 tem de gravar a mesma hora.
    assert ingestao.hora_cheia(TS + 3 * 60) == ingestao.hora_cheia(TS + 58 * 60)


def test_hora_cheia_avanca_na_virada():
    assert ingestao.hora_cheia(TS + HOUR) == TS + HOUR


def test_hora_cheia_sem_argumento_usa_o_relogio():
    assert ingestao.hora_cheia() % HOUR == 0


# ---------------------------------------------------------------------------
# salvar
# ---------------------------------------------------------------------------


def test_salvar_grava_uma_linha_por_item(conn):
    n = ingestao.salvar(conn, "us", TS, {1: (10.0, 100), 2: (20.0, 200)})

    assert n == 2
    assert total_linhas(conn) == 2


def test_salvar_cria_o_item_no_catalogo(conn):
    # A FK exige que o item exista antes do snapshot.
    ingestao.salvar(conn, "us", TS, {42: (1.0, 1)})

    assert conn.execute("SELECT COUNT(*) AS n FROM items WHERE id = 42").fetchone()["n"] == 1


def test_reprocessar_a_mesma_hora_sobrescreve_em_vez_de_duplicar(conn):
    ingestao.salvar(conn, "us", TS, {1: (10.0, 100)})
    ingestao.salvar(conn, "us", TS, {1: (99.0, 500)})

    linha = conn.execute("SELECT value, quantity FROM snapshots").fetchone()

    assert total_linhas(conn) == 1
    assert linha["value"] == 99.0
    assert linha["quantity"] == 500


def test_regioes_diferentes_nao_colidem(conn):
    ingestao.salvar(conn, "us", TS, {1: (10.0, 100)})
    ingestao.salvar(conn, "eu", TS, {1: (20.0, 100)})

    assert total_linhas(conn) == 2


def test_vendas_saem_da_queda_de_estoque(conn):
    ingestao.salvar(conn, "us", TS, {1: (10.0, 1000)})
    ingestao.salvar(conn, "us", TS + HOUR, {1: (10.0, 700)})

    vendas = conn.execute("SELECT sales FROM snapshots WHERE ts = ?", (TS + HOUR,)).fetchone()[
        "sales"
    ]

    assert vendas == 300


def test_estoque_que_cresceu_nao_vira_venda_negativa(conn):
    ingestao.salvar(conn, "us", TS, {1: (10.0, 100)})
    ingestao.salvar(conn, "us", TS + HOUR, {1: (10.0, 900)})

    vendas = conn.execute("SELECT sales FROM snapshots WHERE ts = ?", (TS + HOUR,)).fetchone()[
        "sales"
    ]

    assert vendas == 0


def test_item_visto_pela_primeira_vez_nao_conta_venda(conn):
    ingestao.salvar(conn, "us", TS, {7: (10.0, 500)})

    assert conn.execute("SELECT sales FROM snapshots").fetchone()["sales"] == 0


def test_hora_faltando_no_meio_nao_inventa_venda(conn):
    # Sem a hora anterior imediata, não há base de comparação: vendas = 0.
    ingestao.salvar(conn, "us", TS, {1: (10.0, 1000)})
    ingestao.salvar(conn, "us", TS + 5 * HOUR, {1: (10.0, 200)})

    vendas = conn.execute("SELECT sales FROM snapshots WHERE ts = ?", (TS + 5 * HOUR,)).fetchone()[
        "sales"
    ]

    assert vendas == 0


def test_salvar_agregado_vazio_nao_grava_nada(conn):
    assert ingestao.salvar(conn, "us", TS, {}) == 0
    assert total_linhas(conn) == 0


# ---------------------------------------------------------------------------
# executar
# ---------------------------------------------------------------------------


def test_executar_sem_credencial_reporta_erro_por_regiao(tmp_path, monkeypatch):
    # Sem credencial o cliente levanta ErroBlizzard; `executar` tem de capturar
    # por região e seguir, em vez de derrubar o processo inteiro.
    sem = Settings(db_path=tmp_path / "x.db", client_id="", client_secret="", market_value_cut=0.15)
    monkeypatch.setattr(ingestao, "settings", sem)
    monkeypatch.setattr(banco, "settings", sem)

    resultado = ingestao.executar(("us", "eu"))

    assert set(resultado["regioes"]) == {"us", "eu"}
    assert all(isinstance(v, str) and "erro" in v for v in resultado["regioes"].values())


def test_executar_grava_o_que_a_api_devolveu(tmp_path, monkeypatch):
    cfg = Settings(
        db_path=tmp_path / "y.db", client_id="id", client_secret="s", market_value_cut=1.0
    )
    monkeypatch.setattr(ingestao, "settings", cfg)
    monkeypatch.setattr(banco, "settings", cfg)

    def rotas(req):
        if req.url.host == "oauth.battle.net":
            return httpx.Response(200, json={"access_token": "t", "expires_in": 3600})
        return httpx.Response(
            200,
            json={"auctions": [{"item": {"id": 5}, "unit_price": 30_000, "quantity": 4}]},
        )

    cliente = ingestao.ClienteBlizzard(cfg, httpx.Client(transport=httpx.MockTransport(rotas)))

    resultado = ingestao.executar(("us",), cliente)

    assert resultado["regioes"]["us"] == 1
    with banco.sessao(cfg.db_path) as c:
        linha = c.execute("SELECT value, quantity FROM snapshots").fetchone()
    assert linha["quantity"] == 4
    assert linha["value"] == 3.0  # 30.000 de cobre = 3 de ouro


def test_main_devolve_codigo_de_erro_quando_a_regiao_falha(tmp_path, monkeypatch):
    sem = Settings(db_path=tmp_path / "z.db", client_id="", client_secret="", market_value_cut=0.15)
    monkeypatch.setattr(ingestao, "settings", sem)
    monkeypatch.setattr(banco, "settings", sem)

    assert ingestao.main(["--region", "us"]) == 1
