"""Ingestão horária: busca os leilões, agrega e grava um snapshot por item.

Roda como `python -m backend.app.ingest`. Quem agenda é o sistema — Task
Scheduler, cron, um node do n8n. Um worker próprio (Celery e companhia) seria
infraestrutura demais para um job que roda uma vez por hora.
"""

import argparse
import logging
import sqlite3
import sys
import time
from typing import Any

from . import banco
from .blizzard import ClienteBlizzard, ErroBlizzard, agregar
from .config import REGIONS, settings

log = logging.getLogger("ingest")
HOUR = 3600


def hora_cheia(agora: float | None = None) -> int:
    """Alinha o instante na hora cheia: é o que torna a chave primária estável."""
    return int((agora if agora is not None else time.time()) // HOUR * HOUR)


def salvar(
    conn: sqlite3.Connection,
    region: str,
    ts: int,
    agregado: dict[int, tuple[float, int]],
) -> int:
    """Grava os snapshots da hora. Vendas = queda de estoque desde a hora anterior.

    A API não expõe quantas unidades foram vendidas; a queda de quantidade é a
    melhor aproximação disponível, e o `MAX(0, ...)` ignora as horas em que
    entrou mais estoque do que saiu.
    """
    anterior = {
        r["item_id"]: r["quantity"]
        for r in conn.execute(
            "SELECT item_id, quantity FROM snapshots WHERE region = ? AND ts = ?",
            (region, ts - HOUR),
        )
    }

    linhas = [
        (item_id, region, ts, valor, qtd, max(0, anterior.get(item_id, qtd) - qtd))
        for item_id, (valor, qtd) in agregado.items()
    ]

    # Itens novos precisam existir em `items` antes do snapshot (FK).
    conn.executemany(
        "INSERT OR IGNORE INTO items (id, name) VALUES (?, ?)",
        [(i, f"Item {i}") for i in agregado],
    )
    conn.executemany(
        """INSERT INTO snapshots (item_id, region, ts, value, quantity, sales)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (item_id, region, ts) DO UPDATE SET
               value = excluded.value,
               quantity = excluded.quantity,
               sales = excluded.sales""",
        linhas,
    )
    conn.commit()
    return len(linhas)


def executar(
    regions: tuple[str, ...] = REGIONS, cliente: ClienteBlizzard | None = None
) -> dict[str, Any]:
    """Ingere as regiões pedidas. `cliente` existe para o teste injetar o dele."""
    resultado: dict[str, Any] = {"ts": hora_cheia(), "regioes": {}}
    cliente = cliente or ClienteBlizzard(settings)
    try:
        with banco.sessao() as conn:
            banco.criar_esquema(conn)
            for region in regions:
                try:
                    bruto = cliente.commodities(region)
                    agregado = agregar(bruto, settings.market_value_cut)
                    n = salvar(conn, region, resultado["ts"], agregado)
                    resultado["regioes"][region] = n
                    log.info("%s: %d itens gravados", region, n)
                except ErroBlizzard as e:
                    resultado["regioes"][region] = f"erro: {e}"
                    log.error("%s: %s", region, e)
    finally:
        cliente.fechar()
    return resultado


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Ingere os leilões de commodities.")
    p.add_argument("--region", choices=REGIONS, action="append", dest="regions")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    resultado = executar(tuple(args.regions) if args.regions else REGIONS)
    falhou = any(isinstance(v, str) for v in resultado["regioes"].values())
    print(resultado)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
