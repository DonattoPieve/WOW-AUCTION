# Imagem de produção. Dois estágios: o primeiro resolve as dependências, o
# segundo só copia o que roda. Sem isso o pip e seu cache viajam para dentro da
# imagem final e ela mais que dobra de tamanho.

FROM python:3.11-slim AS dependencias

WORKDIR /build

# Só o pyproject primeiro: enquanto ele não muda, o Docker reaproveita esta
# camada e o build de um commit que mexeu em uma linha de Python não baixa o
# FastAPI de novo.
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --prefix=/instalado .

# ---------------------------------------------------------------------------

FROM python:3.11-slim

# Usuário sem privilégio: se alguém escapar do processo, escapa para um dono que
# não pode escrever em /usr nem instalar nada.
RUN useradd --create-home --uid 10001 ah
WORKDIR /app

COPY --from=dependencias /instalado /usr/local
COPY backend/ backend/
COPY frontend/ frontend/

# O banco vive em volume: sem isso o histórico acumulado morre com o contêiner,
# e o histórico é o único dado que a API da Blizzard não devolve de novo.
ENV WOW_DB_PATH=/dados/wow.db
RUN mkdir /dados && chown ah:ah /dados
VOLUME /dados

USER ah
EXPOSE 8000

# O healthcheck bate na rota que conta snapshots, e não na raiz: a raiz serve o
# HTML mesmo com o banco vazio, então ela responderia 200 num contêiner que na
# prática não tem nada para mostrar.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request,sys,json; \
d=json.load(urllib.request.urlopen('http://localhost:8000/api/health')); \
sys.exit(0 if d['snapshots'] else 1)"

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
