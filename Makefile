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

.PHONY: local.api local.web local.ingest local.ingest-lstr local.ingest-bmf local.ingest-bfh local.status check-sources

local.api: ## Run the FastAPI backend (http://localhost:8000)
	@cd backend && $(UV) run uvicorn app.main:app --reload

local.web: ## Run the Next.js dev server (http://localhost:3000)
	@cd frontend && $(PNPM) dev

local.ingest: ## Build the core knowledge base — EStG, AO, UStG (YEAR=2025)
	@cd backend && $(UV) run python -m ingest.cli ingest --year $(or $(YEAR),2025)

local.ingest-full: ## Build the full knowledge base — all 6 laws (YEAR=2025)
	@cd backend && $(UV) run python -m ingest.cli ingest \
		--laws EStG EStDV AO UStG SolzG GewStG \
		--year $(or $(YEAR),2025)

local.ingest-lstr: ## Download and ingest LStR PDF (YEAR=2023)
	@cd backend && $(UV) run python -m ingest.cli ingest-lstr --year $(or $(YEAR),2023)

local.ingest-bfh: ## Download und Ingest BFH-Urteile (YEAR=2025)
	@cd backend && $(UV) run python -m ingest.cli ingest-bfh --year $(or $(YEAR),2025)

local.ingest-bmf: ## Download und Ingest BMF-Schreiben (YEAR=2025)
	@cd backend && $(UV) run python -m ingest.cli ingest-bmf --year $(or $(YEAR),2025)

local.status: ## Zeige Index-Status: welche Quellen sind indiziert (YEAR=2025)
	@cd backend && $(UV) run python -m ingest.cli status --year $(or $(YEAR),2025)

check-sources: ## HTTP-HEAD check all external sources (exit 1 on failure)
	@cd backend && $(UV) run python -m ingest.cli check-sources

# ---- Knowledge-Base ---------------------------------------------------------

.PHONY: search eval eval.snapshot eval.ablation eval.compare

search: ## Search the vector index — QUERY="..." YEAR=2025 TOP_K=5
	@cd backend && $(UV) run python -m ingest.cli search \
		"$(or $(QUERY),$(error QUERY is required — e.g. make search QUERY="Homeoffice"))" \
		--year $(or $(YEAR),2025) \
		--top-k $(or $(TOP_K),5)

eval: ## Run RAGAS evaluation over the goldset (YEAR=2025, LIMIT=0, OUTPUT=)
	@cd backend && $(UV) run python -m ingest.cli eval \
		--year $(or $(YEAR),2025) \
		$(if $(LIMIT),--limit $(LIMIT)) \
		$(if $(OUTPUT),--output $(OUTPUT)) \
		$(if $(LABEL),--label $(LABEL))

eval.snapshot: ## Run eval + save timestamped snapshot (LABEL=hierarchical YEAR=2025)
	@mkdir -p backend/evaluation/snapshots
	@cd backend && \
	 TS=$$(date +%Y%m%dT%H%M%S) && \
	 _LABEL=$(or $(LABEL),hierarchical) && \
	 SNAP="evaluation/snapshots/$${TS}_$${_LABEL}.json" && \
	 $(UV) run python -m ingest.cli eval \
		--year $(or $(YEAR),2025) \
		$(if $(LIMIT),--limit $(LIMIT)) \
		--label $${_LABEL} \
		--output "$${SNAP}" && \
	 cp "$${SNAP}" "evaluation/snapshots/latest_$${_LABEL}.json" && \
	 printf "$(GREEN)Snapshot gespeichert:$(NC) backend/$${SNAP}\n" && \
	 printf "$(GREEN)Latest-Link:$(NC) backend/evaluation/snapshots/latest_$${_LABEL}.json\n"

eval.ablation: ## Run eval twice (AutoMerge an + aus) + Vergleich ausgeben (YEAR=2025)
	@mkdir -p backend/evaluation/snapshots
	@cd backend && \
	 TS=$$(date +%Y%m%dT%H%M%S) && \
	 SNAP_H="evaluation/snapshots/$${TS}_hierarchical.json" && \
	 SNAP_N="evaluation/snapshots/$${TS}_no-automerge.json" && \
	 printf "$(BOLD)1/2 — AutoMerge an (hierarchical)$(NC)\n" && \
	 $(UV) run python -m ingest.cli eval \
		--year $(or $(YEAR),2025) \
		$(if $(LIMIT),--limit $(LIMIT)) \
		--label hierarchical \
		--output "$${SNAP_H}" && \
	 cp "$${SNAP_H}" "evaluation/snapshots/latest_hierarchical.json" && \
	 printf "$(BOLD)2/2 — AutoMerge aus (no-automerge)$(NC)\n" && \
	 $(UV) run python -m ingest.cli eval \
		--year $(or $(YEAR),2025) \
		$(if $(LIMIT),--limit $(LIMIT)) \
		--no-automerge \
		--label no-automerge \
		--output "$${SNAP_N}" && \
	 cp "$${SNAP_N}" "evaluation/snapshots/latest_no-automerge.json" && \
	 printf "\n$(BOLD)Vergleich:$(NC)\n" && \
	 $(UV) run python -m ingest.cli eval-compare "$${SNAP_H}" "$${SNAP_N}"

eval.compare: ## Vergleiche zwei Snapshots — A=path/a.json B=path/b.json
	@cd backend && $(UV) run python -m ingest.cli eval-compare \
		"$(or $(A),$(error A is required — e.g. make eval.compare A=evaluation/snapshots/a.json B=evaluation/snapshots/b.json))" \
		"$(or $(B),$(error B is required))"

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
