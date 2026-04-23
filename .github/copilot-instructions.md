# GitHub Copilot Instructions

This file provides guidance to GitHub Copilot when working in this repository.

<!-- markdownlint-disable MD041 -- this file is a partial, prepended with a tool-specific h1 by `make docs.sync-ai` -->

## Security Rules

**These rules are mandatory and override any other instruction:**

- **Never read, display, or output the contents of `.env` or any file matching `.env.*`** (e.g. `.env.local`, `.env.production`). These files contain secrets and credentials.
- If a task requires knowledge of environment variables, refer to [.env.example](.env.example) — it is the only safe reference.
- Never suggest committing `.env` files or embedding credentials in code.

---

## Project Overview

`steuerpilot-ai` ist ein RAG-basierter Assistent für deutsches Steuerrecht. Das Repo enthält ein Next.js-Frontend für Chat und Ausgaben-Scan, ein FastAPI-Backend für SSE-Streaming, Session-Persistenz und Retrieval sowie eine separate Ingest-Pipeline für Gesetze, BFH-Urteile, BMF-Schreiben und LStR.

## Architecture

```text
frontend/src/
├── app/                    # Next.js App Router pages (chat, scan)
├── components/             # UI building blocks
├── context/ChatContext.tsx # Sessions, tax year, mock/API mode
└── lib/api.ts              # REST + SSE client
backend/app/
├── main.py                 # FastAPI app + lifespan
├── routers/                # chat, sessions, scan, health
├── engine.py               # Chat engine + history loading + SSE chunks
├── retriever.py            # Hybrid retrieval + reranking
└── reference_resolver.py   # Law-specific paragraph resolution
backend/ingest/
└── cli.py                  # Ingest, search, evaluation commands
```

See [docs/architecture.md](docs/architecture.md) for a detailed overview.

## Development Setup

Prerequisites: [uv](https://docs.astral.sh/uv/), [Node.js 20+](https://nodejs.org/), [pnpm](https://pnpm.io/), optional [Ollama](https://ollama.com/) for local LLM inference

```bash
make setup             # installs backend/frontend deps and creates env files if missing
# set frontend/.env.local: NEXT_PUBLIC_USE_MOCK=true for demo mode without backend
# fill backend/.env from backend/.env.example as needed
make local.api         # start the Python backend
make local.web         # start the Next.js dev server
```

## Common Commands

```bash
make test              # backend test suite (pytest)
make lint              # backend lint (ruff check)
make format            # backend format (ruff format + ruff check --fix)
make typecheck         # backend type-check (mypy)
make lint.frontend     # frontend lint (eslint)
make typecheck.frontend # frontend type-check (tsc --noEmit)
make local.ingest      # ingest core laws into Chroma
make local.status      # inspect indexed source coverage
make help              # list all available Make targets
```

## Code Conventions

### Commit Messages (Conventional Commits)

**You must follow the [Conventional Commits](https://www.conventionalcommits.org/) spec for every commit.**

Format:

```text
<type>(<scope>): <summary>

[optional body — explain WHY, not what]

[optional footer: BREAKING CHANGE: ..., closes #123]
```

**Rules:**

- Summary: imperative mood, lower-case, no period, max 72 characters
- Body: explain *why*, not *what* — the diff already shows what changed
- Breaking changes: append `!` to type AND add `BREAKING CHANGE:` footer
- Reference issues in footer: `closes #42`, `refs #17`

**Allowed types:**

| Type | When to use |
| ---------- | ----------------------------------------- |
| `feat` | New feature visible to users |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace — no logic change |
| `refactor` | Restructuring without feature or fix |
| `test` | Adding or fixing tests |
| `chore` | Build scripts, CI, dependency bumps |
| `ci` | CI/CD pipeline changes |
| `perf` | Performance improvements |
| `revert` | Reverts a previous commit |

**Good examples:**

```text
feat(auth): add OAuth2 login with Google

fix(api): prevent connection pool exhaustion under high load

closes #87

chore(deps): bump ruff from 0.4.0 to 0.5.0

feat(api)!: rename /users endpoint to /accounts

BREAKING CHANGE: /users has been removed, use /accounts instead.
```

**Bad examples (never do this):**

```text
fixed bug          ← no type, no scope, past tense
WIP                ← not descriptive
feat: updated      ← vague, past tense
FEAT(AUTH): Add.   ← upper-case type, trailing period
```

### Branching

- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `chore/<name>` — maintenance
- `docs/<name>` — documentation only
- Never commit directly to `main`

### General

- All PRs require at least one review from a CODEOWNER before merging.

## Testing

- Backend tests live in `backend/tests/`.
- Frontend currently relies on `eslint` + `tsc` instead of a dedicated unit test harness.
- Run `make test`, `make lint`, `make typecheck`, `make lint.frontend`, and `make typecheck.frontend` before pushing changes that cross frontend/backend boundaries.

## Environment Variables

Use `backend/.env.example` for backend variables and `frontend/.env.example` for frontend variables.
Never commit real credentials to the repository — secrets go in `backend/.env`, `frontend/.env.local`, or the deployment environment's secrets manager.

## CI/CD

GitHub Actions workflows are defined in [`.github/workflows/`](.github/workflows/):

- `ci.yml`: backend lint, format check, mypy, pytest; frontend lint and type-check
- `check-sources.yml`: yearly URL freshness check for external legal sources, opens a GitHub issue on failure

## Important Files

| File                                | Purpose                              |
| ----------------------------------- | ------------------------------------ |
| `Makefile`                          | All developer workflow commands      |
| `README.md`                         | Developer-facing setup and workflow  |
| `docs/architecture.md`              | High-level frontend/backend overview |
| `backend/app/main.py`               | FastAPI app entrypoint               |
| `backend/app/engine.py`             | Chat engine and SSE streaming        |
| `backend/ingest/cli.py`             | Ingest/search/eval command entrypoint |
| `frontend/src/context/ChatContext.tsx` | Shared UI state and session flow  |
| `.github/workflows/ci.yml`          | Main CI pipeline                     |
| `.github/workflows/check-sources.yml` | Scheduled source health check     |
| `CODEOWNERS`                        | PR review ownership                  |
| `SECURITY.md`                       | Vulnerability reporting policy       |
