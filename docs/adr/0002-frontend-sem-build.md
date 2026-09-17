# ADR 0002 — Frontend sem bundler, gráfico em SVG escrito à mão

**Data:** 2026-09-16
**Status:** aceito

## Contexto

A interface são duas telas: uma tabela filtrável e uma página de item com
gráfico de linha, três cartões de números e dois heatmaps.

## Decisão

HTML, CSS e módulos ES nativos, servidos como estão pelo FastAPI. O gráfico é
um `<svg>` montado em JavaScript; o heatmap é `display: grid`.

## Por quê

**O gráfico é pequeno.** O desenho inteiro são duas funções de escala e um
`<polyline>`:

```js
const x = (i) => PL + (i * (W - PL - PR)) / (points.length - 1);
const y = (v) => PT + (1 - (v - min) / span) * (H - PT - PB);
```

Chart.js resolveria o mesmo problema com cerca de 200 KB, e ainda seria preciso
lutar com as opções dele para chegar no visual desejado.

**`viewBox` dá responsividade de graça.** O desenho acontece num sistema fixo de
800x260 e o navegador escala. Nenhum listener de `resize`, nenhum recálculo.

**Sem build não há build quebrado.** Não há `node_modules` para instalar antes
de abrir a página, nem versão de bundler para atualizar, nem passo de deploy
além de copiar arquivos. Em um ano, `git clone` e abrir ainda vai funcionar.

## O que foi descartado

**React ou Next.js.** O estado da tela são quatro campos (região, faixa, busca,
ordem) e a renderização é `innerHTML` em dois pontos. Não há ganho de
componentização que pague o custo de build e de dependências.

**Chart.js, ApexCharts, D3.** Ver acima. O D3 seria a escolha para escalas de
tempo irregulares ou zoom por eixo — nada disso é necessário aqui.

**Canvas.** Faria sentido acima de alguns milhares de pontos. A série já chega
reduzida a ~300 pelo servidor, e o SVG mantém o tooltip acessível e o texto
selecionável.

## Consequência aceita

O `innerHTML` reconstrói a tela inteira em cada navegação. Para duas telas é
imperceptível; se a interface crescer, será o primeiro ponto a doer — e o sinal
de que um framework passou a se pagar.
