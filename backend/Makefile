.DEFAULT_GOAL := help

.PHONY: help install sync run dev lint lint-fix format complexity test check clean

help: ## Lista os comandos disponiveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Instala/sincroniza dependencias (prod + dev) via uv
	uv sync

sync: install ## Alias de install (uv sync)

run: ## Roda o servidor de desenvolvimento (reload ativo)
	uv run uvicorn app.main:app --reload --port 8000

lint: ## Verifica sintaxe e estilo com ruff
	uv run ruff check .

lint-fix: ## Corrige automaticamente o que o ruff conseguir
	uv run ruff check --fix .

format: ## Formata o codigo com ruff
	uv run ruff format .

complexity: ## Analisa complexidade do codigo com complexipy
	PYTHONUTF8=1 uv run complexipy .

test: ## Roda os testes unitarios com pytest
	uv run pytest

check: lint complexity test ## Roda lint + complexidade + testes (gate de CI local)

clean: ## Remove caches e artefatos gerados
	rm -rf .pytest_cache .ruff_cache .complexipy_cache
	find . -type d -name '__pycache__' -not -path './.venv/*' -exec rm -rf {} +
