# Atalhos para o que se roda no dia a dia. Os mesmos comandos que o CI executa,
# para não existir um passo que só funciona na máquina de quem escreveu.
.DEFAULT_GOAL := help
.PHONY: help instalar seed servir ingerir teste cobertura lint formatar tipos checar e2e docker limpar

help:  ## Lista os alvos
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

instalar:  ## Instala o projeto e as ferramentas de desenvolvimento
	pip install -e ".[dev]"

seed:  ## Popula o banco com um ano de dados fictícios
	python -m backend.app.semente --dias 365

servir:  ## Sobe a API com recarga automática em http://localhost:8000
	uvicorn backend.app.main:app --reload

ingerir:  ## Busca os leilões de verdade (precisa das credenciais no .env)
	python -m backend.app.ingestao

teste:  ## Roda a suíte
	pytest

cobertura:  ## Roda a suíte medindo cobertura
	pytest --cov --cov-report=term-missing

lint:  ## Procura problema de estilo e de código morto
	ruff check .

formatar:  ## Aplica a formatação
	ruff format .
	npx prettier --write "frontend/**/*.{js,css,html}"

tipos:  ## Confere os tipos
	mypy backend/app

checar: lint tipos teste  ## Roda tudo que o CI roda

e2e:  ## Teste de ponta a ponta num navegador de verdade
	node scripts/ponta-a-ponta.mjs

docker:  ## Sobe a API e popula o banco em contêiner
	docker compose up -d api
	docker compose run --rm semente

limpar:  ## Remove cache, banco local e saída de teste
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml telas
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
