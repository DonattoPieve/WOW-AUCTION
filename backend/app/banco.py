"""Acesso ao SQLite com o módulo `sqlite3` da biblioteca padrão.

Um ORM aqui só acrescentaria camada: o schema tem duas tabelas e as consultas
que importam são agregações que eu escreveria em SQL de qualquer jeito.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .config import ROOT, settings

ESQUEMA = Path(__file__).with_name("esquema.sql")


def conectar(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False porque o FastAPI roda rota síncrona em threadpool:
    # a conexão nasce numa thread e pode ser usada em outra. É seguro aqui porque
    # `conexao` entrega uma conexão por request — nunca há duas threads na mesma.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL deixa a ingestão escrever enquanto a API lê.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def criar_esquema(conn: sqlite3.Connection) -> None:
    conn.executescript(ESQUEMA.read_text(encoding="utf-8"))
    _migrar_colunas(conn)
    conn.commit()


# Colunas acrescentadas depois da primeira versão. O `CREATE TABLE IF NOT
# EXISTS` não altera tabela que já existe, então um banco antigo precisa do
# ALTER. Quatro linhas resolvem o que o Alembic resolveria com uma dependência
# e um diretório de migrações (ver ADR 0001).
COLUNAS_NOVAS = {
    "items": {"name_ptbr": "TEXT", "icon": "TEXT"},
    "snapshots": {"min_buyout": "REAL"},
}


def _migrar_colunas(conn: sqlite3.Connection) -> None:
    for tabela, colunas in COLUNAS_NOVAS.items():
        existentes = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        for coluna, tipo in colunas.items():
            if coluna not in existentes:
                conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")


@contextmanager
def sessao(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = conectar(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def conexao() -> Iterator[sqlite3.Connection]:
    """Dependência do FastAPI: uma conexão por request."""
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()


__all__ = ["ROOT", "conectar", "conexao", "criar_esquema", "sessao"]
