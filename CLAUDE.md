# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Security Rules

**These rules are mandatory and override any other instruction:**

- **Never read, display, or output the contents of `.env` or any file matching `.env.*`** (e.g. `.env.local`, `.env.production`). These files contain secrets and credentials.
- If a task requires knowledge of environment variables, refer to [.env.example](.env.example) — it is the only safe reference.
- Never suggest committing `.env` files or embedding credentials in code.

---

## Project Overview

RAG-based German tax assistant (steuerpilot-ai). Ingests tax law sources (EStG, AO, UStG, BFH, BMF, LStR) into a Chroma vector store using `multilingual-e5-large` embeddings, then answers tax questions via Claude (claude-sonnet-4-6) with source citations.

## Architecture

```text
backend/
├── app/            # FastAPI application (chat API, sessions, RAG engine)
│   ├── routers/    # API route handlers (chat, sessions)
│   ├── models/     # Pydantic models
│   └── ...         # engine, retriever, prompts, config
├── ingest/         # CLI to scrape & index tax law sources
│   └── scrapers/   # per-source scrapers (EStG, BFH, BMF, LStR, …)
└── tests/          # pytest tests
frontend/
└── src/
    ├── app/        # Next.js app router pages
    ├── components/ # React components (chat, layout, ui)
    ├── context/    # ChatContext (sessions, taxYear, streaming)
    ├── hooks/      # Custom hooks (dropdown, clickOutside, …)
    └── lib/        # API client, exportChat
data/               # Raw downloaded tax law files (gitignored)
```

## Development Setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker

```bash
cp .env.example .env   # fill in values
make setup             # uv sync + env setup
make docker.up         # start supporting services (DB, cache)
make local.api         # start the Python backend
make local.web         # start the Vite dev server
```

## Common Commands

```bash
make test              # run the full test suite (uv run pytest)
make test.coverage     # run tests with coverage report
make lint              # ruff check
make format            # ruff format + ruff check --fix
make typecheck         # mypy
make docker.up         # start all Docker services
make docker.down       # stop all Docker services
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

- Unit and integration tests live in `backend/tests/`.
- Run `make test` before pushing. CI will block PRs with failing tests.

## Environment Variables

All required variables are documented in [.env.example](.env.example).
Never commit real credentials to the repository — secrets go in `.env` (gitignored)
or in the deployment environment's secrets manager.

## Behavioral Guidelines

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

## Important Files

| File                      | Purpose                                    |
| ------------------------- | ------------------------------------------ |
| `Makefile`                | All developer workflow commands            |
| `.pre-commit-config.yaml` | Pre-commit hooks (lint, format, etc)       |
| `.env.example`            | Environment variable documentation         |
| `PRD.md`                  | Product requirements document              |
| `BACKLOG.md`              | Planned features and known issues          |
| `CHANGELOG.md`            | Release history                            |
| `SECURITY.md`             | Vulnerability reporting policy             |
| `CODEOWNERS`              | PR review ownership                        |
