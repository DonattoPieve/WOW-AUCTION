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
from .blizzard import Agregado, ClienteBlizzard, ErroBlizzard, agregar
from .config import REGIAO_PADRAO, REGIONS, settings

log = logging.getLogger("ingest")
HOUR = 3600

# Prefixo do nome provisório. Um item com esse prefixo ainda não teve o nome
# buscado na API.
MARCADOR_NOME = "#item-"

# Teto de itens por execução. Cada nome são duas requisições (en_US e pt_BR);
# sem teto, a primeira ingestão de um banco vazio dispararia milhares de
# chamadas de uma vez e tomaria rate limit.
NOMES_POR_EXECUCAO = 50


def hora_cheia(agora: float | None = None) -> int:
    """Alinha o instante na hora cheia: é o que torna a chave primária estável."""
    return int((agora if agora is not None else time.time()) // HOUR * HOUR)


def salvar(
    conn: sqlite3.Connection,
    region: str,
    ts: int,
    agregado: dict[int, Agregado],
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
        (item_id, region, ts, valor, mb, qtd, max(0, anterior.get(item_id, qtd) - qtd))
        for item_id, (valor, mb, qtd) in agregado.items()
    ]

    # Itens novos precisam existir em `items` antes do snapshot (FK). O nome
    # entra como marcador e é trocado pelo de verdade em `preencher_nomes`:
    # descobrir nome custa duas requisições por item, e a ingestão da hora não
    # pode ficar presa a isso.
    conn.executemany(
        "INSERT OR IGNORE INTO items (id, name) VALUES (?, ?)",
        [(i, f"{MARCADOR_NOME}{i}") for i in agregado],
    )
    conn.executemany(
        """INSERT INTO snapshots
               (item_id, region, ts, value, min_buyout, quantity, sales)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (item_id, region, ts) DO UPDATE SET
               value = excluded.value,
               min_buyout = excluded.min_buyout,
               quantity = excluded.quantity,
               sales = excluded.sales""",
        linhas,
    )
    conn.commit()
    return len(linhas)


def preencher_nomes(
    conn: sqlite3.Connection,
    cliente: ClienteBlizzard,
    region: str,
    limite: int = NOMES_POR_EXECUCAO,
) -> int:
    """Troca os nomes provisórios pelos de verdade, em inglês e em português.

    Roda um pedaço por execução. Como o catálogo de commodities muda pouco, em
    algumas horas todos os itens já têm nome — e a partir daí esta função não
    encontra nada para fazer e sai de graça.
    """
    pendentes = [
        r["id"]
        for r in conn.execute(
            """SELECT id FROM items
                WHERE name LIKE ? OR name_ptbr IS NULL OR icon IS NULL
                LIMIT ?""",
            (f"{MARCADOR_NOME}%", limite),
        )
    ]

    preenchidos = 0
    for item_id in pendentes:
        try:
            en, pt = cliente.nomes(region, item_id)
        except ErroBlizzard as e:
            log.warning("nome do item %d: %s", item_id, e)
            continue
        # String vazia, e não NULL, quando a API não tem ícone: NULL significa
        # "ainda não procurei" e traria o item de volta para a fila em toda
        # execução, para sempre.
        icone = cliente.icone(region, item_id) or ""
        conn.execute(
            "UPDATE items SET name = ?, name_ptbr = ?, icon = ? WHERE id = ?",
            (en, pt, icone, item_id),
        )
        preenchidos += 1

    conn.commit()
    return preenchidos


def executar(
    regions: tuple[str, ...] = (REGIAO_PADRAO,), cliente: ClienteBlizzard | None = None
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
                    nomeados = preencher_nomes(conn, cliente, region)
                    resultado["regioes"][region] = n
                    log.info("%s: %d itens gravados, %d nomes preenchidos", region, n, nomeados)
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
    resultado = executar(tuple(args.regions) if args.regions else (REGIAO_PADRAO,))
    falhou = any(isinstance(v, str) for v in resultado["regioes"].values())
    print(resultado)
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
