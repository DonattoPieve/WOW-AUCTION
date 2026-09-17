# Changelog

Segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Adicionado

- Nome dos itens em português (`locale=pt_BR`), com o nome em inglês ao lado; a
  busca casa os dois idiomas.
- Ícone do item, vindo do endpoint de mídia da API, no catálogo e na busca.
- Busca global no cabeçalho, com dropdown de resultados com ícone e preço.
- `min_buyout` no modelo de dados: menor preço unitário listado na hora.
- Gráfico com três séries alternáveis na legenda (market value, min buyout e
  quantity), com eixo duplo — ver `docs/adr/0005-eixo-duplo-e-series-alternaveis.md`.
- Favoritos por item, guardados no navegador, com filtro na lista.
- App fixado no realm Area 52 (US).
- Tooltip do Wowhead pelo script de embed oficial: os nomes de item viram links
  para `wowhead.com/item=ID` e o hover mostra ícone, qualidade e descrição.

### Corrigido

- `preencher_nomes` marcava com `NULL` o item sem ícone e o devolvia para a
  fila em toda execução, para sempre. Agora grava string vazia, que distingue
  "não tem" de "ainda não procurei".
- Resposta inesperada da API de item derrubava a ingestão inteira por
  `KeyError` em vez de virar aviso no log.
- Rótulos do eixo de quantidade saíam repetidos ("2K" cinco vezes) quando a
  faixa era estreita.
- Ordenação por nome usava o nome em inglês, invisível na tela, e a lista
  parecia desordenada.
- Clicar num resultado da busca saía do app para o Wowhead depois que o nome
  virou link; o clique simples volta a abrir a página interna do item.

### Alterado

- Migração de coluna automática no boot para bancos criados antes destas
  colunas existirem (`banco._migrar_colunas`).

## [1.0.0] — 2026-09-16

Primeira versão utilizável: a API serve o histórico e o frontend desenha.

### Adicionado

- Ingestão horária dos leilões de commodities pela Battle.net API, idempotente
  por `(item, região, hora)`.
- Valor de mercado por média ponderada da fatia mais barata do estoque, em vez
  de média simples (ver `docs/adr/0003-valor-de-mercado.md`).
- API REST com catálogo, detalhe do item, série histórica em seis faixas e
  heatmap semanal de valor e de quantidade.
- Redução da série no servidor: um ano de dados horários cabe em 300 pontos.
- Frontend sem build: módulos ES nativos, gráfico em SVG e heatmap em CSS grid.
- Gerador de dados fictícios determinístico, para rodar e testar sem credencial.
- Suíte com 54 testes cobrindo agregações, rotas HTTP e o cliente da Blizzard
  com o transporte mockado.
- Teste de ponta a ponta num Chromium de verdade, com captura das telas.
- CI em duas versões do Python, com lint, formatação, tipos e cobertura.
- Publicação da imagem Docker por tag.
