# ADR 0004 — Ingestão como job externo, sem worker

**Data:** 2026-09-16
**Status:** aceito

## Contexto

A ingestão precisa rodar uma vez por hora: buscar os leilões, agregar e gravar.
Leva alguns segundos e não tem estado entre execuções.

## Decisão

Um módulo executável — `python -m backend.app.ingestao` — agendado por quem
hospeda: cron, Task Scheduler do Windows, um nó de Schedule no n8n, ou
`docker compose run`. A API não agenda nada.

## Por quê

**O agendamento é responsabilidade do sistema operacional.** Cron e Task
Scheduler já resolvem retry, log e a máquina que reinicia. Reimplementar isso
dentro da aplicação seria refazer o que o sistema faz melhor.

**Sem worker não há infraestrutura de worker.** Celery pediria um broker (Redis
ou RabbitMQ), um processo a mais para monitorar e um modo de falha novo — para
uma tarefa que roda 24 vezes por dia e pode simplesmente rodar de novo na hora
seguinte se falhar.

**Processo separado isola a falha.** Se a ingestão estourar memória ou travar no
HTTP, a API continua servindo o histórico que já está no banco. Numa thread de
background dentro do servidor, as duas cairiam juntas.

**A idempotência torna o retry trivial.** A chave `(item, região, hora)` faz
reprocessar ser inofensivo. Não é preciso rastrear "já rodei esta hora?" em
lugar nenhum: rodar de novo é seguro por construção.

## O que foi descartado

**Thread de background no FastAPI.** Some quando roda com mais de um worker do
uvicorn: cada processo agendaria a sua própria ingestão, e quatro workers
gravariam a mesma hora quatro vezes.

**Celery ou APScheduler.** Ver acima. APScheduler seria razoável se o
agendamento precisasse mudar em tempo de execução — não precisa.

**GitHub Actions com `schedule`.** Tentador por ser grátis, mas o runner não tem
onde guardar o banco entre execuções, e o atraso do agendador chega a dezenas
de minutos.

## Consequência aceita

Uma etapa manual na instalação: alguém precisa criar a entrada no agendador. O
README traz a linha pronta para cron e para o Task Scheduler.
