"""Popula o banco com um ano de histórico fictício.

Existe para o projeto rodar (e os testes passarem) sem credencial da Blizzard.
O gerador é determinístico: a mesma semente produz sempre a mesma série, então
um teste que depende dos números não fica intermitente.
"""

import argparse
import math
import random
import sqlite3
import sys
import time

from . import banco
from .config import REGIONS

HOUR = 3600

# (id, nome_en, nome_ptbr, categoria, qualidade, preço base, estoque base)
#
# ATENÇÃO: os nomes em português aqui são INVENTADOS, como todo o resto do
# seed. Não são as strings oficiais de localização do jogo — o seed é dado de
# mentira de ponta a ponta. Os nomes de verdade vêm da API com `locale=pt_BR`,
# gravados pela ingestão (`backend/app/ingestao.py`).
CATALOGO = [
    (
        237361,
        "Refulgent Copper Ore",
        "Minério de Cobre Refulgente",
        "Metal & Stone",
        "Common",
        25.4,
        270_000,
    ),
    (
        237359,
        "Umbral Tin Ore",
        "Minério de Estanho Umbral",
        "Metal & Stone",
        "Common",
        38.9,
        190_000,
    ),
    (236761, "Tranquility Bloom", "Flor da Tranquilidade", "Herb", "Common", 41.2, 150_000),
    (236774, "Argentleaf", "Folha Argêntea", "Herb", "Common", 18.7, 320_000),
    (238529, "Majestic Hide", "Pele Majestosa", "Leather", "Rare", 4930.0, 900),
    (
        238511,
        "Void-Tempered Leather",
        "Couro Temperado pelo Caos",
        "Leather",
        "Common",
        12.3,
        410_000,
    ),
    (236963, "Bright Linen", "Linho Brilhante", "Cloth", "Common", 3.1, 1_200_000),
    (253403, "Thalassian Fillet", "Filé Thalassiano", "Cooking", "Common", 0.44, 3_000_000),
    (
        240133,
        "Sunfire Silk Spellthread",
        "Fio Mágico de Seda Flamissolar",
        "Enchanting",
        "Epic",
        2440.0,
        1_400,
    ),
    (244025, "Ren'dorei Ingenuity", "Engenhosidade Ren'dorei", "Enchanting", "Rare", 1910.0, 2_100),
    (
        227773,
        "Pummel-Proof Plating",
        "Blindagem à Prova de Pancada",
        "Engineering",
        "Epic",
        10270.0,
        350,
    ),
    (219905, "Thunderous Drums", "Tambores Trovejantes", "Inscription", "Rare", 790.0, 4_800),
]


def gerar(
    base: float, estoque: int, horas: int, fim: int, semente: int
) -> list[tuple[int, float, float, int, int]]:
    """Série horária de (ts, valor, min_buyout, quantidade, vendas).

    O valor é um passeio aleatório com reversão à média (o preço volta para
    `base`), multiplicado por dois ciclos: um semanal, que imita o reset, e um
    diário, que imita o horário de pico. É ficção, mas com a forma certa para
    exercitar as agregações e os heatmaps.

    O min_buyout fica abaixo do valor de mercado e oscila mais: é o preço da
    próxima unidade à venda, então um único lote barato o derruba. O mergulho
    ocasional é de propósito — sem ele as duas linhas do gráfico ficariam
    paralelas e não haveria o que comparar.
    """
    rnd = random.Random(semente)
    pontos: list[tuple[int, float, float, int, int]] = []
    preco = base
    anterior = estoque

    for i in range(horas - 1, -1, -1):
        ts = fim - i * HOUR
        hora_do_dia = (ts // HOUR) % 24
        dia_da_semana = (ts // (HOUR * 24)) % 7

        ciclo_semana = 1 + 0.06 * math.sin((dia_da_semana + hora_do_dia / 24) / 7 * math.tau)
        ciclo_dia = 1 + 0.03 * math.sin(hora_do_dia / 24 * math.tau)

        preco += (base - preco) * 0.01 + preco * (rnd.random() - 0.5) * 0.03
        preco = max(preco, base * 0.05)  # sem preço negativo ou colapso total

        qtd = int(estoque * rnd.uniform(0.85, 1.15) / ciclo_semana)
        valor = preco * ciclo_semana * ciclo_dia

        # Em 1 hora de cada 25, alguém lista muito barato e o mínimo desaba.
        desconto = rnd.uniform(0.08, 0.35) if rnd.random() < 0.04 else rnd.uniform(0.9, 0.99)
        pontos.append(
            (
                ts,
                round(valor, 4),
                round(valor * desconto, 4),
                qtd,
                max(0, anterior - qtd),
            )
        )
        anterior = qtd

    return pontos


def popular(conn: sqlite3.Connection, dias: int = 365, fim: int | None = None) -> int:
    fim = fim if fim is not None else int(time.time() // HOUR * HOUR)
    horas = dias * 24
    total = 0

    conn.executemany(
        """INSERT INTO items (id, name, name_ptbr, category, quality)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT (id) DO UPDATE SET
               name = excluded.name,
               name_ptbr = excluded.name_ptbr,
               category = excluded.category,
               quality = excluded.quality""",
        [(i, en, pt, cat, qual) for i, en, pt, cat, qual, _, _ in CATALOGO],
    )

    for item_id, _, _, _, _, base, estoque in CATALOGO:
        for region in REGIONS:
            # A Europa negocia um pouco mais caro; a semente muda junto para as
            # duas regiões não gerarem a mesma série.
            fator = 1.08 if region == "eu" else 1.0
            pontos = gerar(base * fator, estoque, horas, fim, item_id + hash(region) % 1000)
            conn.executemany(
                """INSERT INTO snapshots
                       (item_id, region, ts, value, min_buyout, quantity, sales)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (item_id, region, ts) DO UPDATE SET
                       value = excluded.value,
                       min_buyout = excluded.min_buyout,
                       quantity = excluded.quantity,
                       sales = excluded.sales""",
                [(item_id, region, ts, v, mb, q, s) for ts, v, mb, q, s in pontos],
            )
            total += len(pontos)

    conn.commit()
    return total


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Popula o banco com dados fictícios.")
    p.add_argument("--dias", type=int, default=365)
    args = p.parse_args(argv)

    with banco.sessao() as conn:
        banco.criar_esquema(conn)
        n = popular(conn, args.dias)
    print(f"{n} snapshots gerados para {len(CATALOGO)} itens em {len(REGIONS)} regiões.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
