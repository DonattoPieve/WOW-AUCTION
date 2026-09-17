-- Catálogo de itens. Preenchido pela ingestão ou pelo seed.
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,          -- en_US: é a chave de busca do jogo
    name_ptbr  TEXT,                   -- pt_BR: NULL enquanto não foi buscado
    category   TEXT NOT NULL DEFAULT 'Outros',
    quality    TEXT NOT NULL DEFAULT 'Common',
    icon       TEXT                    -- URL do ícone; NULL enquanto não buscado
);

-- Uma linha por item, região e hora. A chave primária é o que torna a
-- ingestão idempotente: reprocessar a mesma hora sobrescreve em vez de duplicar.
CREATE TABLE IF NOT EXISTS snapshots (
    item_id  INTEGER NOT NULL REFERENCES items(id),
    region   TEXT    NOT NULL,
    ts       INTEGER NOT NULL,  -- epoch em segundos, truncado na hora cheia
    value      REAL    NOT NULL,  -- valor de mercado, em ouro
    min_buyout REAL,                -- menor preço unitário listado, em ouro
    quantity   INTEGER NOT NULL,  -- unidades listadas
    sales    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (item_id, region, ts)
) WITHOUT ROWID;

-- Toda consulta filtra por item+região e ordena por tempo decrescente.
CREATE INDEX IF NOT EXISTS idx_snapshots_recentes
    ON snapshots (item_id, region, ts DESC);
