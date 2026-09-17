"""Testes das agregações — o miolo do projeto."""

import pytest

from backend.app import estatisticas

ITEM = 237361  # Refulgent Copper Ore, presente no catálogo do seed


def test_series_devolve_a_janela_pedida_em_ordem_crescente(conn):
    pts = estatisticas.serie(conn, ITEM, "us", 48)

    assert len(pts) == 48
    assert [p["ts"] for p in pts] == sorted(p["ts"] for p in pts)


def test_series_nao_estoura_quando_pede_mais_do_que_existe(conn):
    pts = estatisticas.serie(conn, ITEM, "us", 10_000)

    assert len(pts) == 40 * 24  # o seed gerou 40 dias


def test_latest_e_o_ponto_mais_recente(conn):
    ultimo = estatisticas.ultimo(conn, ITEM, "us")
    serie = estatisticas.serie(conn, ITEM, "us", 24)

    assert ultimo["ts"] == serie[-1]["ts"]
    assert ultimo["value"] == serie[-1]["value"]


def test_latest_sem_dado_devolve_none(vazio):
    assert estatisticas.ultimo(vazio, ITEM, "us") is None


def test_average_bate_com_a_media_calculada_na_mao(conn):
    pts = estatisticas.serie(conn, ITEM, "us", 24)
    esperado = sum(p["value"] for p in pts) / len(pts)

    # `average` arredonda em 4 casas; a tolerância acompanha isso.
    assert estatisticas.media(conn, ITEM, "us", 24) == pytest.approx(esperado, abs=1e-4)


def test_average_sem_dado_devolve_zero(vazio):
    assert estatisticas.media(vazio, ITEM, "us", 24) == 0.0


def test_daily_calcula_variacao_contra_24_pontos_atras(conn):
    pts = estatisticas.serie(conn, ITEM, "us", 25)
    d = estatisticas.diario(conn, ITEM, "us")

    assert d["value"] == pytest.approx(pts[-1]["value"])
    assert d["change"] == pytest.approx(pts[-1]["value"] - pts[0]["value"], abs=1e-4)
    assert d["change_pct"] == pytest.approx(d["change"] / pts[0]["value"] * 100, abs=0.01)


def test_daily_em_banco_vazio_devolve_zeros_em_vez_de_quebrar(vazio):
    d = estatisticas.diario(vazio, ITEM, "us")

    assert d["value"] == 0.0
    assert d["ts"] is None


def test_daily_volume_e_a_soma_de_vendas_vezes_valor(conn):
    pts = estatisticas.serie(conn, ITEM, "us", 24)
    esperado = sum(p["sales"] * p["value"] for p in pts)

    assert estatisticas.diario(conn, ITEM, "us")["volume"] == pytest.approx(esperado, rel=1e-6)


def test_heatmap_tem_formato_7x24_e_vem_preenchido(conn):
    grid = estatisticas.mapa_calor(conn, ITEM, "us", "value", weeks=4)

    assert len(grid) == 7
    assert all(len(linha) == 24 for linha in grid)
    assert all(v > 0 for linha in grid for v in linha)


def test_heatmap_de_quantidade_usa_a_outra_coluna(conn):
    valores = estatisticas.mapa_calor(conn, ITEM, "us", "value")
    quantidades = estatisticas.mapa_calor(conn, ITEM, "us", "quantity")

    assert quantidades != valores
    assert quantidades[0][0] > 1000  # quantidade é estoque, não preço


def test_heatmap_recusa_campo_fora_da_lista(conn):
    # A coluna entra na query por f-string; o guard é o que impede injeção.
    with pytest.raises(ValueError):
        estatisticas.mapa_calor(conn, ITEM, "us", "value; DROP TABLE items")


def test_heatmap_de_banco_vazio_e_todo_zero(vazio):
    assert estatisticas.mapa_calor(vazio, ITEM, "us") == [[0.0] * 24 for _ in range(7)]


def test_list_items_traz_todo_o_catalogo_com_o_ultimo_valor(conn):
    itens = estatisticas.listar_itens(conn, "us")

    assert len(itens) == 12
    assert all(i["value"] > 0 for i in itens)
    assert all("change_pct" in i for i in itens)


def test_list_items_filtra_por_nome_sem_diferenciar_caixa(conn):
    assert [i["name"] for i in estatisticas.listar_itens(conn, "us", q="copper")] == [
        "Refulgent Copper Ore"
    ]


def test_list_items_filtra_por_categoria(conn):
    itens = estatisticas.listar_itens(conn, "us", category="Herb")

    assert {i["category"] for i in itens} == {"Herb"}


def test_list_items_ordena_por_valor_decrescente(conn):
    valores = [i["value"] for i in estatisticas.listar_itens(conn, "us", sort="value")]

    assert valores == sorted(valores, reverse=True)


def test_list_items_ordena_pelo_nome_exibido(conn):
    # O padrão ordena pelo nome em português, que é o que a tela mostra na
    # frente. Ordenar por um campo invisível faria a lista parecer desordenada.
    exibidos = [i["name_ptbr"] or i["name"] for i in estatisticas.listar_itens(conn, "us")]

    assert exibidos == sorted(exibidos, key=str.lower)


def test_list_items_ordem_invalida_cai_no_padrao_em_vez_de_quebrar(conn):
    itens = estatisticas.listar_itens(conn, "us", sort="'; DROP TABLE items--")
    exibidos = [i["name_ptbr"] or i["name"] for i in itens]

    assert exibidos == sorted(exibidos, key=str.lower)


def test_list_items_respeita_o_limite(conn):
    assert len(estatisticas.listar_itens(conn, "us", limit=3)) == 3


def test_regioes_tem_series_diferentes(conn):
    assert (
        estatisticas.ultimo(conn, ITEM, "us")["value"]
        != estatisticas.ultimo(conn, ITEM, "eu")["value"]
    )


def test_categories_vem_ordenado_e_sem_repeticao(conn):
    cats = estatisticas.categorias(conn)

    assert cats == sorted(set(cats))


def test_diario_traz_o_min_buyout(conn):
    d = estatisticas.diario(conn, ITEM, "us")

    # O seed sempre gera min_buyout abaixo do valor de mercado.
    assert d["min_buyout"] is not None
    assert d["min_buyout"] < d["value"] * 1.01


def test_diario_sem_dado_devolve_min_buyout_nulo(vazio):
    assert estatisticas.diario(vazio, ITEM, "us")["min_buyout"] is None


def test_serie_inclui_as_tres_series_do_grafico(conn):
    p = estatisticas.serie(conn, ITEM, "us", 5)[0]

    assert {"ts", "value", "min_buyout", "quantity"} <= set(p)
