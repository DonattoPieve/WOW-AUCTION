"""Agregações sobre a série de snapshots.

Tudo que dá para fazer em SQL fica em SQL: o SQLite agrega mais rápido do que
Python itera, e a consulta é a documentação do cálculo.
"""

import sqlite3
from typing import Any, Literal

HOUR = 3600
Field = Literal["value", "quantity"]


def serie(conn: sqlite3.Connection, item_id: int, region: str, hours: int) -> list[dict[str, Any]]:
    """Os últimos `hours` pontos, do mais antigo para o mais novo."""
    rows = conn.execute(
        """
        SELECT ts, value, quantity, sales FROM snapshots
         WHERE item_id = ? AND region = ?
         ORDER BY ts DESC LIMIT ?
        """,
        (item_id, region, hours),
    ).fetchall()
    return [dict(r) for r in reversed(rows)]


def ultimo(conn: sqlite3.Connection, item_id: int, region: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT ts, value, quantity, sales FROM snapshots
         WHERE item_id = ? AND region = ?
         ORDER BY ts DESC LIMIT 1
        """,
        (item_id, region),
    ).fetchone()
    return dict(row) if row else None


def media(conn: sqlite3.Connection, item_id: int, region: str, hours: int) -> float:
    """Média do valor nas últimas `hours` horas. 0.0 se não houver dado."""
    row = conn.execute(
        """
        SELECT AVG(value) AS m FROM (
            SELECT value FROM snapshots
             WHERE item_id = ? AND region = ?
             ORDER BY ts DESC LIMIT ?
        )
        """,
        (item_id, region, hours),
    ).fetchone()
    return round(row["m"], 4) if row and row["m"] is not None else 0.0


def diario(conn: sqlite3.Connection, item_id: int, region: str) -> dict[str, Any]:
    """Painel do dia: valor atual, variação em 24h, vendas e volume negociado.

    A variação compara o snapshot mais recente com o de 24 pontos atrás, não com
    "ontem no relógio" — assim uma hora faltante na série não zera o cálculo.
    """
    pts = serie(conn, item_id, region, 25)
    if not pts:
        return {
            "value": 0.0,
            "quantity": 0,
            "change": 0.0,
            "change_pct": 0.0,
            "market_value": 0.0,
            "sales": 0,
            "volume": 0.0,
            "ts": None,
        }

    now, day = pts[-1], pts[-24:]
    before = pts[0]["value"] if len(pts) > 1 else now["value"]
    change = now["value"] - before
    return {
        "value": round(now["value"], 4),
        "quantity": now["quantity"],
        "change": round(change, 4),
        "change_pct": round(change / before * 100, 2) if before else 0.0,
        "market_value": round(sum(p["value"] for p in day) / len(day), 4),
        "sales": sum(p["sales"] for p in day),
        "volume": round(sum(p["sales"] * p["value"] for p in day), 2),
        "ts": now["ts"],
    }


def mapa_calor(
    conn: sqlite3.Connection,
    item_id: int,
    region: str,
    field: Field = "value",
    weeks: int = 4,
) -> list[list[float]]:
    """Matriz 7x24 (domingo..sábado x hora) com a média das últimas `weeks` semanas.

    Serve para achar o padrão semanal da AH: reset, noites de raide, fim de semana.
    """
    if field not in ("value", "quantity"):  # a coluna entra na query por f-string
        raise ValueError(f"campo inválido: {field}")

    cutoff = weeks * 7 * 24
    rows = conn.execute(
        f"""
        SELECT CAST(strftime('%w', ts, 'unixepoch') AS INTEGER) AS dow,
               CAST(strftime('%H', ts, 'unixepoch') AS INTEGER) AS hour,
               AVG({field}) AS m
          FROM (SELECT ts, {field} FROM snapshots
                 WHERE item_id = ? AND region = ?
                 ORDER BY ts DESC LIMIT ?)
         GROUP BY dow, hour
        """,
        (item_id, region, cutoff),
    ).fetchall()

    grid = [[0.0] * 24 for _ in range(7)]
    for r in rows:
        grid[r["dow"]][r["hour"]] = round(r["m"], 4)
    return grid


ORDENS = {
    "name": "i.name COLLATE NOCASE ASC",
    "value": "s.value DESC",
    "quantity": "s.quantity DESC",
    "change": "change_pct DESC",
}


def listar_itens(
    conn: sqlite3.Connection,
    region: str,
    q: str = "",
    category: str = "",
    sort: str = "name",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Catálogo com o snapshot mais recente e a variação de 24h de cada item."""
    order = ORDENS.get(sort, ORDENS["name"])
    rows = conn.execute(
        f"""
        WITH ultimo AS (
            SELECT item_id, MAX(ts) AS ts FROM snapshots
             WHERE region = ? GROUP BY item_id
        )
        SELECT i.id, i.name, i.category, i.quality,
               s.ts, s.value, s.quantity,
               COALESCE(
                   ROUND((s.value - antes.value) / NULLIF(antes.value, 0) * 100, 2),
                   0
               ) AS change_pct
          FROM items i
          JOIN ultimo u  ON u.item_id = i.id
          JOIN snapshots s ON s.item_id = i.id AND s.region = ? AND s.ts = u.ts
          LEFT JOIN snapshots antes
                 ON antes.item_id = i.id AND antes.region = ?
                AND antes.ts = u.ts - 24 * {HOUR}
         WHERE (? = '' OR i.name LIKE '%' || ? || '%')
           AND (? = '' OR i.category = ?)
         ORDER BY {order}
         LIMIT ?
        """,
        (region, region, region, q, q, category, category, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def categorias(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT category FROM items ORDER BY category")
    return [r["category"] for r in rows]
