"""Ponto de entrada da aplicação: API em /api e o frontend estático na raiz."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import banco
from .config import ROOT
from .rotas import itens

log = logging.getLogger(__name__)
FRONTEND = ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Criar o schema no boot deixa o projeto rodar em banco vazio sem passo extra.
    with banco.sessao() as conn:
        banco.criar_esquema(conn)
    log.info("banco pronto em %s", banco.settings.db_path)
    yield


app = FastAPI(
    title="WoW AH Prices",
    description="Preços e histórico das commodities da Auction House do World of Warcraft.",
    version="1.0.0",
    lifespan=lifespan,
)

# O frontend é servido pelo mesmo host; o CORS só existe para quem rodar o
# front em outra porta (Live Server, por exemplo).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(itens.router)

if FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
