# Arquitetura

## O problema

A Battle.net API devolve **só a foto atual** da Auction House. Não existe
endpoint de histórico: se ninguém guardar, o preço de ontem não existe mais.
Todo o resto do projeto sai dessa frase.

O endpoint de commodities é regional (`us`, `eu`) e é republicado de hora em
hora. Uma hora é, então, a granularidade máxima útil — guardar de minuto em
minuto só gravaria o mesmo número sessenta vezes.

## O caminho do dado

```
Battle.net API                (foto atual, 1x por hora, ~1M de leilões)
      │
      │  ingestao.py          agrupa por item, calcula o valor de mercado
      ▼
   SQLite                     1 linha por (item, região, hora) — acumula o histórico
      │
      │  estatisticas.py      médias, variação 24h, matriz 7x24
      ▼
   API REST                   FastAPI, JSON, série já reduzida a ~300 pontos
      │
      ▼
   Frontend                   ES modules, SVG à mão, CSS grid
```

Quatro camadas, cada uma com uma responsabilidade e testável sozinha:

| Camada | Arquivo | Responsabilidade | Testado em |
|---|---|---|---|
| Ingestão | `ingestao.py` | buscar, agregar, gravar | `blizzard.test.py` |
| Cliente | `blizzard.py` | OAuth, HTTP, valor de mercado | `blizzard.test.py` |
| Agregação | `estatisticas.py` | as contas | `estatisticas.test.py` |
| Transporte | `rotas/itens.py` | contrato HTTP, validação | `api.test.py` |
| Interface | `frontend/` | desenhar | `scripts/ponta-a-ponta.mjs` |

## O modelo de dados

Duas tabelas. `items` é catálogo; `snapshots` é a série:

```sql
PRIMARY KEY (item_id, region, ts)
```

Essa chave é a peça mais importante do schema. Ela faz a ingestão ser
**idempotente**: reprocessar a mesma hora sobrescreve em vez de duplicar. Sem
ela, um job que rodasse duas vezes por engano envenenaria todas as médias, e a
única saída seria limpar a mão.

`ts` é epoch em segundos truncado na hora cheia — não o instante em que o job
rodou. Rodar às 14:03 ou às 14:58 grava a mesma hora, e a série não fica com
buracos de alinhamento.

## As decisões

Cada uma tem um ADR em [`adr/`](adr/), com o contexto e o que foi descartado:

- [0001](adr/0001-sqlite-sem-orm.md) — SQLite com o módulo `sqlite3`, sem ORM
- [0002](adr/0002-frontend-sem-build.md) — frontend sem bundler e gráfico em SVG
- [0003](adr/0003-valor-de-mercado.md) — como o valor de mercado é calculado
- [0004](adr/0004-ingestao-como-job.md) — ingestão como job externo, sem worker

## O que ainda não existe

Honestamente listado, porque projeto sem limite declarado engana quem lê:

- **Itens não-commodity** (armas, armaduras, transmog). Esses são por realm, o
  endpoint é outro e o volume é muito maior.
- **Autenticação.** A API é aberta e só faz leitura. Alertas por usuário
  precisariam de conta, e conta precisa de bem mais que uma tabela.
- **Previsão de preço.** Um ano de dados horários é material suficiente, mas
  previsão mal-feita é pior que nenhuma.
- **Postgres.** Um item com um ano de histórico são ~9 mil linhas; o catálogo
  inteiro de commodities cabe em algumas centenas de MB. O ADR 0001 explica em
  que ponto essa conta deixa de fechar.
