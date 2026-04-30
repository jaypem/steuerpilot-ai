# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.1.0] — 2026-04-30

### Added

- RAG pipeline with hybrid retrieval (dense + BM25) and cross-encoder reranking
- HyDE query expansion (opt-in via `HYDE_ENABLED=true`)
- AutoMerge for parent-chunk retrieval and §-reference resolution
- Retriever caching to avoid rebuilding BM25 index on every request
- Configurable context volume (`RAG_TOP_N`, `RAG_CHUNK_MAX_CHARS`, `MEMORY_TOKEN_LIMIT`)
- Ollama support (default: `gemma4:26b`) and Anthropic Claude as alternative LLM provider
- SSE streaming with typed chunks (text, source, risk_badge, saving, status, done, error)
- Thinking/status indicators in chat UI during LLM wait time
- Session management with SQLite persistence
- Expense scan feature (`/scan`) for quick deductibility checks
- Instagram post check for tax-relevant claims in social media content
- Idea transfer (Doppelt-Steuern-Sparen) flow with structured evaluation
- Ingest CLI for EStG, AO, UStG, EStDV, SolzG, GewStG, BFH, BMF, LStR
- Docker setup with multi-stage builds and persistent volumes for Chroma, SQLite, HF cache
- GitHub Actions CI (ruff, mypy, pytest, eslint, tsc, next build)
