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

<!-- One paragraph describing what this project does. -->

TODO: describe the project.

## Architecture

<!-- Brief architecture summary. Link to docs/architecture.md for details. -->

```text
src/
├── api/        # REST API layer
├── domain/     # Business logic / domain models
├── infra/      # Persistence, external service clients
└── ...
tests/
├── unit/
├── integration/
└── e2e/
```

See [docs/architecture.md](docs/architecture.md) for a detailed overview.

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

- Write unit tests for all business logic in `src/domain/`.
- Write integration tests for database and external service interactions.
- Run `make test` before pushing. CI will block PRs with failing tests.

## Environment Variables

All required variables are documented in [.env.example](.env.example).
Never commit real credentials to the repository — secrets go in `.env` (gitignored)
or in the deployment environment's secrets manager.

## CI/CD

Pipelines are defined in [bitbucket-pipelines.yml](bitbucket-pipelines.yml):

- Pull Requests: lint + type-check + test + build (no deploy)
- `main`: above + deploy to **staging** (automatic)
- Tags `v*`: above + deploy to **production** (manual approval required)

## Important Files

| File                                | Purpose                              |
| ----------------------------------- | ------------------------------------ |
| `Makefile`                          | All developer workflow commands      |
| `Dockerfile`                        | Multi-stage production container     |
| `docker-compose.yml`                | Local dev stack (app, DB, cache)     |
| `bitbucket-pipelines.yml`           | CI/CD pipeline                       |
| `.pre-commit-config.yaml`           | Pre-commit hooks (lint, format, etc) |
| `.env.example`                      | Environment variable documentation   |
| `CONTRIBUTING.md`                   | Branching, commits, PR process       |
| `CHANGELOG.md`                      | Release history                      |
| `SECURITY.md`                       | Vulnerability reporting policy       |
| `CODEOWNERS`                        | PR review ownership                  |
