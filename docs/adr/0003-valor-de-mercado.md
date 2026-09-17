# ADR 0003 — Valor de mercado pela fatia mais barata do estoque

**Data:** 2026-09-16
**Status:** aceito

## Contexto

A API devolve os lotes em aberto: cada um com preço unitário e quantidade. Um
item popular tem centenas de lotes, e é preciso reduzir isso a **um** número por
hora.

O detalhe que decide a escolha: sempre há lotes com preço absurdo. Alguém lista
minério a mil vezes o preço corrente — para testar, por engano, ou apostando em
um comprador distraído. Esses lotes ficam na lista para sempre, porque ninguém
compra.

## Decisão

Média ponderada pela quantidade dos **15% mais baratos do estoque**. A fração é
configurável em `WOW_MARKET_VALUE_CUT`.

```python
total = sum(q for _, q in auctions)
alvo = max(1, int(total * cut))
# percorre em ordem crescente de preço até cobrir `alvo` unidades
```

## Por quê

**Quem define o preço real é o fundo da lista.** Um comprador varre do mais
barato para cima. O preço que ele efetivamente paga é o da ponta barata — não a
média de tudo que está listado.

**A média simples é fácil de envenenar.** Um único lote de uma unidade a um
preço absurdo desloca a média de um item com dez mil unidades. Existe um teste
exatamente para isso:

```python
def test_valor_de_mercado_ignora_oferta_absurda_no_topo():
```

**Ponderar pela quantidade, e não por lote.** Dez lotes de uma unidade não
valem o mesmo que um lote de mil unidades na formação do preço.

## O que foi descartado

**Menor preço.** É volátil demais: um lote de uma unidade mal precificada viraria
"o preço" daquela hora.

**Mediana.** Resistente a outlier, mas ignora a quantidade — e no caso de itens
com muitos lotes pequenos e caros acima da ponta barata, ela devolve um número
que ninguém pagaria.

**Percentil fixo em 5%.** Estreito demais para item de pouca liquidez, onde 5%
do estoque pode ser um único lote.

## Consequência aceita

O número não é comparável com o de outros sites que usam outra fórmula. Por isso
a fórmula está documentada aqui e coberta por teste, em vez de escondida numa
linha de código.
