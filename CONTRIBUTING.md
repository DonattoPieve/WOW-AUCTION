# Como contribuir

## Preparar o ambiente

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
make instalar
make seed        # um ano de dados fictícios, sem precisar de credencial
make servir      # http://localhost:8000
```

Opcional, mas recomendado:

```bash
pip install pre-commit && pre-commit install
```

A partir daí cada commit roda lint, formatação e tipos só nos arquivos que
mudaram.

## Antes de abrir um PR

```bash
make checar   # lint + tipos + suíte, o mesmo que o CI roda
```

## Convenções

**Nomes em português, termos do domínio em inglês.** `valor_de_mercado`,
`mapa_calor`, `hora_cheia` — mas `commodities`, `region` e `item_id` ficam como
estão, porque é assim que a API da Blizzard os chama e traduzir só criaria um
dicionário mental a mais.

**Arquivo de teste é `<modulo>.test.py`**, ao lado do nome do módulo que testa.
O pytest não descobre esse formato sozinho; a linha que o ensina está no
`pyproject.toml`.

**Nome de teste descreve o comportamento, não a função.**
`test_heatmap_recusa_campo_fora_da_lista` diz o que quebra se a asserção falhar.
`test_heatmap_2` não diz nada.

**SQL fica em SQL.** Agregação que o SQLite faz não vira laço em Python.

**Dependência nova precisa de justificativa no PR.** A biblioteca padrão e a
plataforma vêm primeiro: o gráfico é SVG escrito à mão e o banco é o módulo
`sqlite3` justamente por isso.

**Decisão de arquitetura vira ADR.** Um arquivo em `docs/adr/`, numerado, com o
contexto e o que foi descartado. Serve para o próximo leitor não refazer a
discussão do zero.

## Estrutura

```
backend/app/       API, ingestão e agregações
  banco.py         conexão e schema
  blizzard.py      cliente da Battle.net API
  estatisticas.py  as agregações (o miolo)
  ingestao.py      job horário
  semente.py       gerador de dados fictícios
  rotas/           rotas HTTP
frontend/          ES modules, sem build
tests/             pytest
scripts/           teste de ponta a ponta
docs/adr/          decisões de arquitetura
```
