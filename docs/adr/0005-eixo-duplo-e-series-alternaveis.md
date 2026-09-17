# ADR 0005 — Eixo duplo no gráfico, com as séries alternáveis

**Data:** 2026-09-16
**Status:** aceito, com ressalva registrada

## Contexto

O gráfico mostra três medidas da mesma hora: valor de mercado e min buyout, em
ouro (dezenas a milhares), e quantidade listada, em unidades (centenas a
milhões). Três ordens de grandeza de diferença entre a maior e a menor.

Colocar as três num eixo só achataria as duas de ouro numa linha reta rente ao
zero: com a quantidade definindo a escala, uma variação de 20% no preço vira
menos de um pixel.

## Decisão

Ouro no eixo da esquerda, quantidade no eixo da direita. A legenda liga e
desliga cada série, e a última ligada não pode ser desligada.

## A ressalva

**Eixo duplo é criticado com razão na literatura de visualização de dados**, e
o guia que este projeto segue o lista como o erro número um em gráficos. Dois
motivos, os dois legítimos:

1. Fica ambíguo qual linha se lê em qual escala.
2. É possível sugerir correlação entre as séries só mexendo na escala de um
   lado — o cruzamento das linhas passa a ser artefato da escala, não do dado.

Foi aceito porque é o formato pedido para este projeto, e com duas mitigações:

- **Cor amarrada a eixo.** Os rótulos do eixo direito saem na cor da série de
  quantidade. É o que liga a escala à linha sem depender de legenda.
- **A ambiguidade é removível pelo leitor.** Desligando a quantidade na
  legenda, sobra um eixo só e a comparação entre valor e min buyout fica sem
  intermediário.

## O que foi descartado

**Dois painéis empilhados compartilhando o eixo do tempo.** É a solução sem
ambiguidade nenhuma, e seria a escolha se o formato não estivesse definido.
Custa altura de tela e separa o cruzamento visual que é justamente o que se
quer observar (preço subindo enquanto estoque cai).

**Indexar tudo a uma base comum (variação percentual).** Resolve a escala e
perde os valores absolutos — e "quantas unidades tem listadas" é uma das
perguntas que a tela existe para responder.

**Escala logarítmica num eixo só.** Acomoda as três, e torna a leitura de
preço não-intuitiva para quem só quer saber se está caro.

## Quando revisitar

Se entrar uma quarta medida, ou se o gráfico passar a ser lido por quem não
acompanhou esta decisão: nesse ponto os dois painéis empilhados passam a valer
mais que o cruzamento visual.
