"""Rotas REST do catálogo e da página de item."""

import math
import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import estatisticas
from ..banco import conexao
from ..config import RANGES, REALM, REGIAO_PADRAO, REGIONS

router = APIRouter(prefix="/api", tags=["items"])

Conn = Annotated[sqlite3.Connection, Depends(conexao)]
Region = Annotated[Literal["us", "eu"], Query(description="Região da AH")]


def _item(conn: sqlite3.Connection, item_id: int) -> dict:
    row = conn.execute(
        "SELECT id, name, name_ptbr, icon, category, quality FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"item {item_id} não encontrado")
    return dict(row)


@router.get("/realm")
def realm() -> dict:
    """O realm em que o app está fixado. A interface lê isto em vez de fixar
    o texto no HTML."""
    return REALM


@router.get("/health")
def health(conn: Conn) -> dict:
    n = conn.execute("SELECT COUNT(*) AS n FROM snapshots").fetchone()["n"]
    return {"status": "ok" if n else "vazio", "snapshots": n}


@router.get("/categories")
def categorias(conn: Conn) -> list[str]:
    return estatisticas.categorias(conn)


@router.get("/items")
def listar_itens(
    conn: Conn,
    region: Region = REGIAO_PADRAO,
    q: str = "",
    category: str = "",
    sort: Literal["name", "value", "quantity", "change"] = "name",
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[dict]:
    return estatisticas.listar_itens(conn, region, q, category, sort, limit)


@router.get("/items/{item_id}")
def item_detail(conn: Conn, item_id: int, region: Region = REGIAO_PADRAO) -> dict:
    item = _item(conn, item_id)
    return {
        "item": item,
        "region": region,
        "daily": estatisticas.diario(conn, item_id, region),
        "averages": {
            r: {
                "daily": estatisticas.media(conn, item_id, r, 24),
                "weekly": estatisticas.media(conn, item_id, r, 24 * 7),
                "monthly": estatisticas.media(conn, item_id, r, 24 * 30),
            }
            for r in REGIONS
        },
    }


@router.get("/items/{item_id}/series")
def item_series(
    conn: Conn,
    item_id: int,
    region: Region = REGIAO_PADRAO,
    range: Literal["daily", "weekly", "monthly", "quarter", "half-year", "year"] = "weekly",
    points: Annotated[int, Query(ge=10, le=2000)] = 300,
) -> dict:
    """Série do gráfico, já reduzida a no máximo `points` pontos.

    Reduzir no servidor evita mandar 8760 pontos (um ano de horas) para o
    navegador desenhar 300 pixels de largura.
    """
    _item(conn, item_id)
    pts = estatisticas.serie(conn, item_id, region, RANGES[range])
    passo = max(1, math.ceil(len(pts) / points))
    amostra = pts[::passo] if passo > 1 else pts
    if pts and amostra[-1] is not pts[-1]:
        amostra.append(pts[-1])  # o último ponto é o preço atual: nunca some
    return {"range": range, "region": region, "points": amostra}


@router.get("/items/{item_id}/heatmap")
def item_heatmap(
    conn: Conn,
    item_id: int,
    region: Region = REGIAO_PADRAO,
    field: Literal["value", "quantity"] = "value",
    weeks: Annotated[int, Query(ge=1, le=52)] = 4,
) -> dict:
    _item(conn, item_id)
    return {
        "field": field,
        "weeks": weeks,
        "grid": estatisticas.mapa_calor(conn, item_id, region, field, weeks),
    }
