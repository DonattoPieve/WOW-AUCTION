"""Testes das rotas HTTP: contrato, filtros e códigos de erro."""

ITEM = 237361


def test_health_reporta_o_volume_de_dados(client):
    r = client.get("/api/health")

    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["snapshots"] > 0


def test_categories_devolve_lista_de_strings(client):
    r = client.get("/api/categories")

    assert r.status_code == 200
    assert "Herb" in r.json()


def test_items_devolve_o_catalogo(client):
    r = client.get("/api/items")
    itens = r.json()

    assert r.status_code == 200
    assert len(itens) == 12
    assert set(itens[0]) >= {"id", "name", "category", "quality", "value", "quantity", "change_pct"}


def test_items_aceita_busca_e_categoria(client):
    achados = client.get("/api/items", params={"q": "copper"}).json()

    assert [i["name"] for i in achados] == ["Refulgent Copper Ore"]
    assert len(client.get("/api/items", params={"category": "Leather"}).json()) == 2


def test_busca_casa_o_nome_em_portugues(client):
    # O mesmo item, procurado nos dois idiomas: quem digita "cobre" e quem
    # digita "copper" tem de chegar no mesmo lugar.
    por_en = client.get("/api/items", params={"q": "copper"}).json()
    por_pt = client.get("/api/items", params={"q": "cobre"}).json()

    assert [i["id"] for i in por_en] == [i["id"] for i in por_pt]


def test_items_devolve_os_dois_nomes(client):
    item = client.get("/api/items", params={"q": "copper"}).json()[0]

    assert item["name"] == "Refulgent Copper Ore"
    assert item["name_ptbr"] == "Minério de Cobre Refulgente"


def test_detalhe_devolve_os_dois_nomes(client):
    item = client.get(f"/api/items/{ITEM}").json()["item"]

    assert item["name"] == "Refulgent Copper Ore"
    assert item["name_ptbr"] == "Minério de Cobre Refulgente"


def test_items_recusa_ordem_desconhecida(client):
    r = client.get("/api/items", params={"sort": "preco"})

    assert r.status_code == 422  # validado pelo Literal do FastAPI


def test_items_recusa_regiao_invalida(client):
    assert client.get("/api/items", params={"region": "br"}).status_code == 422


def test_items_recusa_limite_fora_da_faixa(client):
    assert client.get("/api/items", params={"limit": 0}).status_code == 422
    assert client.get("/api/items", params={"limit": 9999}).status_code == 422


def test_detalhe_traz_painel_do_dia_e_medias_das_duas_regioes(client):
    r = client.get(f"/api/items/{ITEM}")
    d = r.json()

    assert r.status_code == 200
    assert d["item"]["name"] == "Refulgent Copper Ore"
    assert d["daily"]["value"] > 0
    assert set(d["averages"]) == {"us", "eu"}
    assert d["averages"]["us"]["weekly"] != d["averages"]["eu"]["weekly"]


def test_detalhe_de_item_inexistente_da_404(client):
    r = client.get("/api/items/999999")

    assert r.status_code == 404
    assert "não encontrado" in r.json()["detail"]


def test_series_respeita_a_faixa_pedida(client):
    dia = client.get(f"/api/items/{ITEM}/series", params={"range": "daily"}).json()

    assert dia["range"] == "daily"
    assert len(dia["points"]) == 24


def test_series_reduz_a_amostra_sem_passar_do_teto(client):
    r = client.get(f"/api/items/{ITEM}/series", params={"range": "year", "points": 100})
    pts = r.json()["points"]

    assert len(pts) <= 101  # o teto, mais o último ponto que é sempre preservado
    assert [p["ts"] for p in pts] == sorted(p["ts"] for p in pts)


def test_series_preserva_o_preco_atual_ao_reduzir(client):
    atual = client.get(f"/api/items/{ITEM}").json()["daily"]
    serie = client.get(f"/api/items/{ITEM}/series", params={"range": "year", "points": 50}).json()

    assert serie["points"][-1]["ts"] == atual["ts"]


def test_series_recusa_faixa_desconhecida(client):
    assert client.get(f"/api/items/{ITEM}/series", params={"range": "decada"}).status_code == 422


def test_heatmap_devolve_matriz_7x24(client):
    r = client.get(f"/api/items/{ITEM}/heatmap")
    grid = r.json()["grid"]

    assert r.status_code == 200
    assert len(grid) == 7
    assert all(len(linha) == 24 for linha in grid)


def test_heatmap_de_quantidade_difere_do_de_valor(client):
    valor = client.get(f"/api/items/{ITEM}/heatmap", params={"field": "value"}).json()["grid"]
    qtd = client.get(f"/api/items/{ITEM}/heatmap", params={"field": "quantity"}).json()["grid"]

    assert valor != qtd


def test_heatmap_recusa_campo_arbitrario(client):
    r = client.get(f"/api/items/{ITEM}/heatmap", params={"field": "value); DROP TABLE items--"})

    assert r.status_code == 422


def test_openapi_esta_publicado(client):
    r = client.get("/openapi.json")

    assert r.status_code == 200
    assert "/api/items/{item_id}" in r.json()["paths"]
