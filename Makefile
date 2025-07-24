.PHONY: help format lint typecheck test check install clean dev-install
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Available targets:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync

dev-install: ## Install development dependencies
	uv sync --group dev
	uv run lefthook install

format: ## Format code with ruff
	@echo "$(BLUE)🧹 Formatting code...$(RESET)"
	uv run ruff format src/ tests/

lint: ## Lint code with ruff
	@echo "$(BLUE)🔍 Linting code...$(RESET)"
	uv run ruff check src/ tests/ --fix

lint-check: ## Check linting without fixing
	@echo "$(BLUE)🔍 Checking linting...$(RESET)"
	uv run ruff check src/ tests/

lint-src: ## Lint only source code (strict)
	@echo "$(BLUE)🔍 Linting source code...$(RESET)"
	uv run ruff check src/ --fix

lint-src-check: ## Check linting of source code only
	@echo "$(BLUE)🔍 Checking source code linting...$(RESET)"
	uv run ruff check src/

lint-tests: ## Lint tests (non-failing)
	@echo "$(BLUE)🔍 Linting tests (warnings only)...$(RESET)"
	-uv run ruff check tests/ --fix

format-check: ## Check formatting without fixing
	@echo "$(BLUE)🧹 Checking formatting...$(RESET)"
	uv run ruff format src/ tests/ --check

typecheck: ## Run type checking with ty (src only)
	@echo "$(BLUE)⚡ Type checking...$(RESET)"
	uvx ty check src/

test: ## Run all tests
	@echo "$(BLUE)🧪 Running all tests...$(RESET)"
	uv run pytest -v

test-unit: ## Run only unit tests
	@echo "$(BLUE)🧪 Running unit tests...$(RESET)"
	uv run pytest tests/unit/ -v

test-integration: ## Run only integration tests
	@echo "$(BLUE)🧪 Running integration tests...$(RESET)"
	uv run pytest tests/integration/ -v

test-cov: ## Run tests with coverage
	@echo "$(BLUE)🧪 Running tests with coverage...$(RESET)"
	uv run pytest -v --cov=src --cov-report=term-missing

check: format-check lint-src-check typecheck test ## Run all checks (CI mode)
	@echo "$(GREEN)✅ All checks passed!$(RESET)"

fix: format lint-src lint-tests ## Fix all auto-fixable issues
	@echo "$(GREEN)🔧 Auto-fixed all issues!$(RESET)"

clean: ## Clean up temporary files
	@echo "$(BLUE)🧽 Cleaning up...$(RESET)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache dist build .coverage htmlcov .ruff_cache

serve: ## Start the development server
	@echo "$(BLUE)🚀 Starting development server...$(RESET)"
	uv run python -m uvicorn src.the_assistant.main:app --reload --host 0.0.0.0 --port 8000

build: ## Build the package
	@echo "$(BLUE)📦 Building package...$(RESET)"
	uv build

docker-build: ## Build Docker image
	@echo "$(BLUE)🐳 Building Docker image...$(RESET)"
	docker build -t the-assistant .

docker-run: ## Run Docker container
	@echo "$(BLUE)🐳 Running Docker container...$(RESET)"
	docker run -p 8000:8000 the-assistant

worker: ## Start the Temporal worker
	@echo "$(BLUE)⚙️ Starting Temporal worker...$(RESET)"
	uv run python src/the_assistant/worker.py

daily-briefing: ## Trigger the daily briefing workflow
	@echo "$(BLUE)📅 Triggering daily briefing workflow...$(RESET)"
	uv run python scripts/run_daily_briefing.py

# Development workflow shortcuts
dev: dev-install ## Setup development environment
	@echo "$(GREEN)🎉 Development environment ready!$(RESET)"
	@echo "$(YELLOW)Run 'make help' to see available commands$(RESET)"

ci: check ## Run CI checks locally
	@echo "$(GREEN)🎯 Ready for CI!$(RESET)"

migrate: ## Run database migrations
	DATABASE_URL="postgresql+asyncpg://temporal:temporal@localhost:5432/the_assistant" uv run alembic upgrade head

migration: ## Create new migration (usage: make migration MESSAGE="description")
	DATABASE_URL="postgresql+asyncpg://temporal:temporal@localhost:5432/the_assistant" uv run alembic revision --autogenerate -m "$(MESSAGE)"
