# ADR 0001 — SQLite com o módulo `sqlite3`, sem ORM

**Data:** 2026-09-16
**Status:** aceito

## Contexto

O dado é uma série temporal de formato fixo: item, região, hora, três números.
As consultas que importam são agregações — média de janela, variação contra 24
pontos atrás, média por dia da semana e hora.

## Decisão

SQLite pelo módulo `sqlite3` da biblioteca padrão. Sem SQLAlchemy, sem Alembic.

## Por quê

**O ORM não ajudaria no que é difícil aqui.** A parte complicada não é mapear
linha em objeto: é a matriz 7x24 do heatmap, que sai de um `GROUP BY` com
`strftime`. Em SQLAlchemy isso seria escrito em SQL de qualquer forma, dentro de
um `text()` — ou seja, o ORM cobraria a dependência e ainda deixaria o trecho
difícil do mesmo tamanho.

**A migração não é um problema ainda.** Duas tabelas, e o `CREATE TABLE IF NOT
EXISTS` do `esquema.sql` roda no boot. Alembic resolve schema que evolui em
produção com dado que não pode ser perdido; não é o caso de um projeto de uma
pessoa que pode reprocessar a ingestão.

**A escala cabe.** Um item com um ano de histórico horário são 8.760 linhas.
Mil itens em duas regiões são ~17 milhões — dezenas de MB, com índice, e o
SQLite lê isso sem reclamar.

## O que foi descartado

**Postgres + SQLAlchemy.** Seria a escolha certa com escrita concorrente de
vários processos, ou com mais de uma aplicação no mesmo banco. Hoje há um
escritor (a ingestão, uma vez por hora) e leitores. O WAL do SQLite já permite
ler durante a escrita.

**JSON em arquivo.** Sem índice e sem agregação: o heatmap viraria laço em
Python sobre o ano inteiro a cada request.

## Quando revisitar

- Se a ingestão passar a rodar em paralelo por região **e** escrever na mesma
  tabela ao mesmo tempo (hoje é sequencial).
- Se entrarem os itens por realm: ~80 realms multiplicam o volume por duas
  ordens de grandeza.
- Se a API for para um host com disco efêmero, onde um arquivo local não
  sobrevive ao deploy.
