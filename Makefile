SHELL := /bin/zsh
.DEFAULT_GOAL := help

# ============================================================================
# steuerpilot-ai — Developer Workflow
# ============================================================================

UV   ?= uv
PNPM ?= pnpm

# Colors
RED    := \033[0;31m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
BOLD   := \033[1m
NC     := \033[0m

# ============================================================================
# Help
# ============================================================================
.PHONY: help
help:
	@printf "\n$(BOLD)steuerpilot-ai — available targets$(NC)\n"
	@awk 'BEGIN {FS = ":.*##"} \
		/^# ---- [A-Za-z]/ { section=$$0; gsub(/^# -* *| -*$$/, "", section); printf "\n$(BLUE)%s$(NC)\n", section; next } \
		/^[a-zA-Z0-9_.-]+:.*##/ { printf "  $(GREEN)%-24s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\n$(YELLOW)Examples:$(NC)\n"
	@printf "  make setup\n"
	@printf "  make local.api\n"
	@printf "  make local.web\n"
	@printf "  make local.ingest\n\n"

# ============================================================================
# Helpers
# ============================================================================
define require
	@command -v $(1) >/dev/null 2>&1 || { printf "$(RED)Error: '$(1)' is required but not installed.$(NC)\n"; exit 1; }
endef

# ---- Setup ------------------------------------------------------------------

.PHONY: setup
setup: ## Install all dependencies and initialise env files
	$(call require,$(UV))
	$(call require,$(PNPM))
	@$(UV) sync --directory backend
	@cd frontend && $(PNPM) install
	@test -f backend/.env || { cp backend/.env.example backend/.env; \
		printf "$(YELLOW)Created backend/.env from template$(NC)\n"; }
	@test -f frontend/.env.local || { cp frontend/.env.example frontend/.env.local; \
		printf "$(YELLOW)Created frontend/.env.local from template$(NC)\n"; }
	@printf "$(GREEN)✓ Setup complete — run: make local.api  &&  make local.web$(NC)\n"

# ---- Local Development ------------------------------------------------------

.PHONY: local.api local.web local.ingest

local.api: ## Run the FastAPI backend (http://localhost:8000)
	@cd backend && $(UV) run uvicorn app.main:app --reload

local.web: ## Run the Next.js dev server (http://localhost:3000)
	@cd frontend && $(PNPM) dev

local.ingest: ## Build the core knowledge base — EStG, AO, UStG (YEAR=2025)
	@cd backend && $(UV) run steuerpilot ingest --year $(or $(YEAR),2025)

local.ingest-full: ## Build the full knowledge base — all 6 laws (YEAR=2025)
	@cd backend && $(UV) run steuerpilot ingest \
		--laws EStG EStDV AO UStG SolzG GewStG \
		--year $(or $(YEAR),2025)

# ---- Quality ----------------------------------------------------------------

.PHONY: test lint

test: ## Run backend tests
	$(call require,$(UV))
	@cd backend && $(UV) run pytest

lint: ## Lint frontend
	$(call require,$(PNPM))
	@cd frontend && $(PNPM) lint

# ---- Cleanup ----------------------------------------------------------------

.PHONY: clean
clean: ## Remove build artifacts and caches
	@printf "$(YELLOW)Cleaning…$(NC)\n"
	@find . -type d -name __pycache__ -not -path '*/.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -not -path '*/.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .mypy_cache -not -path '*/.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .ruff_cache -not -path '*/.venv/*' -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/.next 2>/dev/null || true
	@find . -name "*.pyc" -not -path '*/.venv/*' -delete 2>/dev/null || true
	@printf "$(GREEN)Done.$(NC)\n"
