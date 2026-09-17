# Changelog

Segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

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
