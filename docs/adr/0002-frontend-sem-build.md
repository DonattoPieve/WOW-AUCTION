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

## A exceção: o tooltip do Wowhead

Este ADR diz que o frontend não depende de nada externo. Há **uma** exceção, e
ela merece estar escrita aqui em vez de ser descoberta no `index.html`:

```html
<script src="https://wow.zamimg.com/js/tooltips.js" defer></script>
```

É o script de embed oficial do Wowhead (documentado em
<https://www.wowhead.com/tooltips>). Ele varre os links para
`wowhead.com/item=ID` e anexa o tooltip do jogo — ícone, cor de qualidade,
tipo e o texto de sabor do item.

Entrou porque reproduzir aquele tooltip do zero significaria armazenar
descrição, tipo e arte de cada item — conteúdo que é deles — e mantê-lo
atualizado a cada patch. O script deixa esse conteúdo no servidor deles, onde
ele pertence, e é o caminho que o próprio Wowhead oferece para isso.

O que essa dependência **não** faz:

- Não alimenta o banco. O Wowhead não publica uma API de dados; nome e ícone
  que a ingestão grava continuam vindo da Battle.net API.
- Não é requisito de funcionamento. `defer` e ausência de qualquer chamada
  nossa a ele significam que, se o CDN cair, a página inteira continua: some o
  tooltip, e só. O teste de ponta a ponta trata falha desse domínio como aviso,
  não como defeito.

## Consequência aceita

O `innerHTML` reconstrói a tela inteira em cada navegação. Para duas telas é
imperceptível; se a interface crescer, será o primeiro ponto a doer — e o sinal
de que um framework passou a se pagar.
