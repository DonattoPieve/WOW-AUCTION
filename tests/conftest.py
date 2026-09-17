"""Fixtures compartilhadas.

Cada teste roda contra um banco temporário próprio, populado com uma janela
curta de dados determinísticos. Sem estado compartilhado entre testes, sem
banco de desenvolvimento poluído.
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import banco, semente
from backend.app.main import app

TS_FIXO = 1_767_225_600  # 2026-01-01 00:00:00 UTC — ancora os testes no tempo


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    c = banco.conectar(tmp_path / "teste.db")
    banco.criar_esquema(c)
    semente.popular(c, dias=40, fim=TS_FIXO)
    yield c
    c.close()


@pytest.fixture
def vazio(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    c = banco.conectar(tmp_path / "vazio.db")
    banco.criar_esquema(c)
    yield c
    c.close()


@pytest.fixture
def client(conn: sqlite3.Connection) -> Iterator[TestClient]:
    """TestClient com a dependência de conexão apontada para o banco do teste."""
    app.dependency_overrides[banco.conexao] = lambda: conn
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
