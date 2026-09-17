-- Catálogo de itens. Preenchido pela ingestão ou pelo seed.
CREATE TABLE IF NOT EXISTS items (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Outros',
    quality  TEXT NOT NULL DEFAULT 'Common'
);

-- Uma linha por item, região e hora. A chave primária é o que torna a
-- ingestão idempotente: reprocessar a mesma hora sobrescreve em vez de duplicar.
CREATE TABLE IF NOT EXISTS snapshots (
    item_id  INTEGER NOT NULL REFERENCES items(id),
    region   TEXT    NOT NULL,
    ts       INTEGER NOT NULL,  -- epoch em segundos, truncado na hora cheia
    value    REAL    NOT NULL,  -- valor de mercado, em ouro
    quantity INTEGER NOT NULL,  -- unidades listadas
    sales    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (item_id, region, ts)
) WITHOUT ROWID;

-- Toda consulta filtra por item+região e ordena por tempo decrescente.
CREATE INDEX IF NOT EXISTS idx_snapshots_recentes
    ON snapshots (item_id, region, ts DESC);
