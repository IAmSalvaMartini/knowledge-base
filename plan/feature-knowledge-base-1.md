---
goal: Build an LLM-Connected Org Knowledge Base for Tribal Knowledge Capture and Retrieval
version: 1.5
date_created: 2026-06-25
last_updated: 2026-06-26
owner: IAmSalvaMartini / Release Engineering
status: 'Completed'
tags: [feature, architecture, knowledge-base, rag, llm]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

This plan defines the implementation of a centralized, LLM-connected knowledge base that captures undocumented "tribal" knowledge held by individual engineers and makes it searchable through natural-language questions. Engineers author content in a self-hosted Wiki.js instance; Wiki.js's native Git storage backend writes the content as Markdown to a Git repository; an ingestion pipeline chunks and embeds the content into a vector store; a retrieval service answers questions using Retrieval-Augmented Generation (RAG) with cited sources. Knowledge enters from two sources: Wiki.js pages (via the Git mirror) and an SSO-gated upload page where users submit documents (PDF/Word/Markdown/text) that are parsed and ingested. Users ask questions through a chat widget embedded directly in Wiki.js pages (plus a CLI). All authenticated access uses the organization's existing Entra ID (Azure AD) SSO over OIDC.

The system root directory is `C:\knowledgebase`. The Python stack mirrors the existing the tool project (`C:\the tool`): Flask, requests, python-dotenv.

**Initial-version model strategy (cost-minimizing, EDP-compliant):** Generation uses the organization's existing **Anthropic enterprise** entitlement, which carries enterprise data-protection (no-training) terms and is free-to-team under the existing contract — keeping incremental cost near zero. To minimize cost and fully eliminate third-party data exposure for the embedding step, **embeddings run locally** via Ollama on-host; embedding text never leaves the machine. The model layer is provider-abstracted (PAT-002): the generation backend is selected by configuration, so an OpenAI-compatible or Copilot-style endpoint can be substituted later without code changes. Note: GitHub/M365 **Copilot does not expose a general chat-completions API** for custom applications, so it cannot serve as the KB generation backend directly; it is retained only as a future option behind the abstraction if/when an OpenAI-compatible endpoint is provisioned.

## 1. Requirements & Constraints

- **REQ-001**: Engineers author and edit knowledge content in a self-hosted Wiki.js instance through a browser (WYSIWYG or Markdown editor), with no code skills required.
- **REQ-002**: Wiki.js is configured with its Git storage module so all content is persisted as Markdown files in a Git repository for programmatic ingestion.
- **REQ-003**: The system answers natural-language questions and returns an answer plus citations to the exact source pages.
- **REQ-004**: The retrieval service uses RAG: embed query → retrieve top-K chunks → build grounded prompt → call the configured generation backend → return answer.
- **REQ-005**: Generation uses the organization's Anthropic enterprise entitlement (EDP / no-training terms) via the `anthropic` SDK. Initial-version default answering model is the lowest-cost tier `claude-haiku-4-5-20251001`; escalation model for complex synthesis is `claude-sonnet-4-6`. All model IDs are env-configurable (REQ-010).
- **REQ-006**: Embeddings run locally via Ollama (default model `nomic-embed-text`) to incur zero per-call cost and keep all embedding text on-host. The embedding model and Ollama endpoint are configurable via environment variable.
- **REQ-007**: The vector store persists locally on disk (ChromaDB) at `C:\knowledgebase\data\chroma`.
- **REQ-010**: The generation backend is provider-abstracted behind a single interface (PAT-002). The active backend is chosen by `KB_LLM_PROVIDER` (initial default `anthropic`); supported future value `openai_compatible` allows substituting any OpenAI-compatible / Copilot-style endpoint by configuration alone.
- **REQ-008**: Re-ingestion is incremental: only changed/added/deleted pages are re-embedded, keyed by content hash.
- **REQ-009**: Access surfaces are: (a) a chat widget embedded in Wiki.js pages calling the framework's `/api/ask`, (b) an SSO-gated document upload page, and (c) a CLI (`kb` command). No Slack/Teams bot.
- **REQ-011**: The upload page is a second ingestion source. It accepts `.pdf`, `.docx`, `.md`, `.txt` files, parses them to text, and runs them through the same chunk → embed → store pipeline as Wiki.js content, tagged with a distinct source (`upload:<filename>`). Uploaded originals are stored under `data/uploads/` (gitignored).
- **REQ-012**: All browser surfaces (upload page, ask widget endpoint) authenticate via the organization's Entra ID (Azure AD) using OIDC authorization-code flow. Unauthenticated requests are rejected. CLI uses a service token.
- **REQ-013**: `/api/ask` enables CORS restricted to the internal Wiki.js origin (`KB_WIKIJS_BASE_URL`) so the embedded widget can call it; all other origins are blocked.
- **SEC-001**: All secrets (`ANTHROPIC_API_KEY`, Wiki.js Git deploy key, Entra ID client secret, CLI service token) are stored in `C:\knowledgebase\.env` and never committed to Git. `.env` is listed in `.gitignore`. Local Ollama embeddings require no key.
- **SEC-002**: Answers must include citations; the generation prompt instructs the model to refuse to answer when no relevant context is retrieved ("I don't have that in the knowledge base").
- **SEC-003**: Embedding text stays on-host (local Ollama) and never reaches a third party. Only the final question plus retrieved context is sent to Anthropic under enterprise EDP (no-training) terms. Knowledge content classified above the org's approved data-sensitivity tier for EDP processing must still not be ingested; a content-sensitivity gate is enforced at ingestion (TASK-009).
- **CON-001**: Python 3.10+ only. Anthropic provides no first-party embeddings model; embeddings are therefore handled locally via Ollama (REQ-006), avoiding any third-party embeddings vendor.
- **CON-003**: Ollama must be installed and running on-host with the `KB_EMBED_MODEL` pulled. The generation backend depends on a valid Anthropic enterprise API key.
- **CON-002**: Wiki.js (FOSS, AGPL-3.0) is self-hosted internally via Docker; requires a host with Docker, a backing database (PostgreSQL), and network access to the internal Git repository. No SaaS licensing cost.
- **CON-004**: Two-repository separation is mandatory. The **framework** (this codebase at `C:\knowledgebase`) is published as a **public OSS repository** and must contain no secrets and no organizational content. The **content** repository `knowledgebase-content` (Wiki.js Markdown) is **private**. The framework consumes content at runtime only by cloning the private repo into `content_mirror/` (gitignored).
- **SEC-004**: The public repo must never track `.env` (secrets), `content_mirror/` (clone of private content), or `data/` (Chroma vectors embed private document text). All three are gitignored. Only `.env.example` (placeholders) is committed.
- **SEC-005**: A `gitleaks` pre-commit hook plus GitHub secret-scanning/push-protection guard against accidental secret commits (client- and server-side).
- **SEC-006**: Document upload is restricted to authenticated Entra ID users (REQ-012). Uploads enforce an allowlist of extensions (`.pdf`, `.docx`, `.md`, `.txt`), a max file size (`KB_MAX_UPLOAD_MB`, default 25), and content-type validation before parsing.
- **SEC-007**: Uploaded files and parsed text contain internal content; they are stored under `data/uploads/` which is gitignored (covered by `data/`) and never published to the public framework repo.
- **SEC-008**: `/api/ask` CORS is allowlisted to `KB_WIKIJS_BASE_URL` only (REQ-013); the endpoint requires a valid SSO session or service token.
- **GUD-001**: Follow the existing the tool convention: Python performs all data fetching/file operations; the LLM performs only analysis/generation.
- **GUD-002**: All configuration values are read from environment variables with documented defaults; no hardcoded secrets or model IDs in source.
- **PAT-001**: Module layout follows a service pattern: `ingest/`, `retrieval/`, `surfaces/`, `config.py`, `cli.py`, `app.py`.
- **PAT-002**: Generation is accessed through a single `LLMProvider` interface (`generate(messages) -> str`) with concrete `AnthropicProvider` (initial) and a future `OpenAICompatibleProvider`; the active class is selected by `KB_LLM_PROVIDER`. No caller imports a vendor SDK directly.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Stand up the self-hosted Wiki.js instance, Git-backed content repo, and project scaffold so content can be authored and pulled programmatically.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Deploy Wiki.js via Docker Compose internally (Wiki.js container + PostgreSQL). Configure an admin account and the top-level navigation/page structure: `Backporting`, `Build & Release`, `Environments`, `Debugging Playbooks`, `People & Ownership`. Restrict access to the internal network/SSO. | ✅ | 2026-06-25 |
| TASK-002 | Create an internal Git repository `knowledgebase-content` and enable the Wiki.js **Git storage module** (sync mode bidirectional, Markdown output) pointed at it with a deploy key. Confirm a test page edit in Wiki.js produces a Markdown commit in the repo. | ✅ | 2026-06-25 |
| TASK-003 | Create directory tree under `C:\knowledgebase`: `ingest/`, `retrieval/`, `surfaces/`, `auth/`, `data/`, `data/chroma/`, `data/uploads/`, `content_mirror/` (local clone of `knowledgebase-content`), `tests/`, `plan/`. | ✅ | 2026-06-25 |
| TASK-004 | Create `C:\knowledgebase\requirements.txt` with pinned deps (see Section 4): `flask>=2.3.0`, `requests>=2.31.0`, `python-dotenv>=1.0.0`, `anthropic>=0.40.0`, `ollama>=0.3.0`, `chromadb>=0.5.0`, `markdown-it-py>=3.0.0`, `pytest>=8.0.0`. | ✅ | 2026-06-25 |
| TASK-005 | Create `C:\knowledgebase\.env.example` listing required keys (`ANTHROPIC_API_KEY`, Wiki.js Git deploy key, `KB_OIDC_CLIENT_ID`, `KB_OIDC_CLIENT_SECRET`, `KB_OIDC_TENANT_ID`, `KB_CLI_TOKEN`) and tunables (`KB_LLM_PROVIDER=anthropic`, `KB_ANSWER_MODEL=claude-haiku-4-5-20251001`, `KB_ESCALATION_MODEL=claude-sonnet-4-6`, `KB_EMBED_MODEL=nomic-embed-text`, `KB_OLLAMA_HOST=http://127.0.0.1:11434`, `KB_TOP_K=8`, `KB_CHROMA_PATH=./data/chroma`, `KB_WIKIJS_BASE_URL`, `KB_MAX_UPLOAD_MB=25`). Use repo-relative paths for OSS portability. (`.gitignore`/`.env.example` created in Phase 0; see TASK-021/022.) | ✅ | 2026-06-25 |
| TASK-006 | Create `C:\knowledgebase\config.py` exposing a `Config` dataclass that loads all values from `TASK-005` env vars via `python-dotenv`, applying the documented defaults. Validation: importing `config` with a complete `.env` returns populated fields; missing required key raises `RuntimeError`. | ✅ | 2026-06-25 |

### Implementation Phase 2

- GOAL-002: Build the ingestion pipeline that converts both mirrored Markdown and uploaded documents into an incrementally-updated vector store.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-007 | Create `ingest/loader.py` with `load_pages(mirror_path: str) -> list[Page]`. Walk `content_mirror/` for `*.md`, parse front matter and body, and return `Page(path, title, body, sha256)` records where `sha256` is the hash of the body. | ✅ | 2026-06-25 |
| TASK-007B | Create `ingest/docparser.py` with `parse_document(file_path: str) -> Page`. Convert `.pdf` (pypdf), `.docx` (python-docx), `.md`/`.txt` (read directly) to plain text; return a `Page` with `path = "upload:<filename>"`, title from filename, and `sha256` of the extracted text. Raise `UnsupportedFormat` for other extensions. | ✅ | 2026-06-25 |
| TASK-008 | Create `ingest/chunker.py` with `chunk_page(page: Page, max_tokens: int = 800, overlap: int = 100) -> list[Chunk]`. Split on Markdown headings first, then size-bound; each `Chunk` carries `chunk_id`, `page_path`, `title`, `heading_path`, `text`. | ✅ | 2026-06-25 |
| TASK-009 | Create `ingest/sensitivity.py` with `is_ingestable(page: Page) -> bool` enforcing SEC-003: reject pages whose front matter contains `sensitivity: restricted`. Log and skip rejected pages. | ✅ | 2026-06-25 |
| TASK-010 | Create `ingest/embedder.py` with `embed_texts(texts: list[str]) -> list[list[float]]` — pluggable backends: `ollama`, `sentence_transformers`, `dummy` via `KB_EMBED_BACKEND`. | ✅ | 2026-06-26 |
| TASK-011 | Create `ingest/store.py` wrapping ChromaDB persistent client at `KB_CHROMA_PATH`, collection `kb_chunks`. Functions: `upsert(chunks, embeddings)`, `delete_by_page(page_path)`, `get_page_hash(page_path)`, `query(embedding, top_k)`. | ✅ | 2026-06-25 |
| TASK-012 | Create `ingest/run.py` orchestrating incremental ingest from BOTH sources: (a) `git pull` in `content_mirror/` then `load_pages`; (b) `parse_document` over `data/uploads/`. Diff each page's `sha256` against stored hash, re-embed changed/new pages, delete removed pages, upsert (all via the shared chunk → sensitivity → embed → store path). Validation: running twice with no content change performs zero embedding calls. | ✅ | 2026-06-25 |

### Implementation Phase 3

- GOAL-003: Build the RAG retrieval/generation service exposed as a Flask API.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-013 | Create `retrieval/retriever.py` with `retrieve(question: str, top_k: int) -> list[Chunk]`: embed the question via `ingest/embedder.py`, query `ingest/store.py`, return ranked chunks with scores. | ✅ | 2026-06-25 |
| TASK-014 | Create `retrieval/prompt.py` with `build_messages(question, chunks) -> list[dict]` producing a provider-neutral messages payload (system + user roles): a system prompt instructing grounded, cited answers and refusal when context is empty (SEC-002), plus user content embedding the retrieved chunks with `[source: page_path#heading]` markers. | ✅ | 2026-06-25 |
| TASK-015A | Create `retrieval/provider.py` implementing the `LLMProvider` interface (PAT-002): abstract `generate(messages, model) -> str`, concrete `AnthropicProvider` using the `anthropic` SDK and enterprise key, and a stub `OpenAICompatibleProvider` (raises `NotImplementedError`). Factory `get_provider()` selects by `KB_LLM_PROVIDER`. | ✅ | 2026-06-25 |
| TASK-015B | Create `retrieval/generator.py` with `answer(question) -> Answer`: call `retrieve`, `build_messages`, then `get_provider().generate(...)` with `KB_ANSWER_MODEL`. Implement escalation: if the answer confidence marker is low or context exceeds a threshold, retry with `KB_ESCALATION_MODEL`. Return `Answer(text, citations)`. No vendor SDK imported here directly. | ✅ | 2026-06-25 |
| TASK-016 | Create `C:\knowledgebase\app.py` Flask app exposing `POST /api/ask` (JSON `{question}` → `{answer, citations}`) and `GET /api/health`. Bind to `127.0.0.1:5057`. | ✅ | 2026-06-25 |

### Implementation Phase 4

- GOAL-004: Deliver SSO authentication, the upload page, the embedded ask widget, the CLI, and automated content refresh.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-016B | Create `auth/oidc.py` integrating Entra ID (Azure AD) via OIDC authorization-code flow using Authlib: routes `/auth/login`, `/auth/callback`, `/auth/logout`; a `@login_required` decorator that validates the session; and `require_token()` for CLI service-token auth (`KB_CLI_TOKEN`). Config from `KB_OIDC_*`. | ✅ | 2026-06-25 |
| TASK-016C | Wire CORS in `app.py` (flask-cors) restricting `/api/ask` to `KB_WIKIJS_BASE_URL` (SEC-008). Protect `/api/ask` with `@login_required` OR a valid service token. | ✅ | 2026-06-25 |
| TASK-017 | Create `surfaces/upload/` — an Entra-authenticated upload page (`GET /upload` form, `POST /upload` handler). Enforce SEC-006 (extension allowlist, `KB_MAX_UPLOAD_MB`, content-type check), save originals to `data/uploads/`, then trigger `ingest/run.py` for the new file. Show ingest status. | ✅ | 2026-06-25 |
| TASK-018 | Create `C:\knowledgebase\cli.py` with a `kb ask "<question>"` command that calls `retrieval/generator.answer` and prints the answer plus citations, authenticating via `KB_CLI_TOKEN`. Use standard argparse style. | ✅ | 2026-06-25 |
| TASK-019 | Create `surfaces/widget/ask-widget.js` — a self-contained embeddable chat widget. Document injecting it via Wiki.js Administration → Theme → custom JS/HTML; it renders a floating chat box on every wiki page and calls `/api/ask` (CORS-allowed origin, SSO session). Renders answer + citation links. | ✅ | 2026-06-25 |
| TASK-020 | Create `scripts/refresh.py` and a Windows Task Scheduler entry (or `start_ui.bat`-style launcher) that runs `ingest/run.py` on a fixed interval (default hourly) so the vector store tracks Wiki.js edits and new uploads. | ✅ | 2026-06-25 |

### Implementation Phase 0 — Repository Hygiene & OSS Readiness (prerequisite)

- GOAL-005: Guarantee the public framework repo carries no secrets and no organizational content before any code or publication (CON-004, SEC-004, SEC-005). Listed last for numbering but **must be completed first**.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-021 | Create `.gitignore` excluding `.env`/`.env.*` (keep `.env.example`), `content_mirror/`, `data/`, private keys, and Python/OS artifacts. | ✅ | 2026-06-25 |
| TASK-022 | Create `.env.example` with placeholder-only values for every required variable; no real secret, internal URL, or org name. | ✅ | 2026-06-25 |
| TASK-023 | Create `.pre-commit-config.yaml` (gitleaks + `detect-private-key` + large-file guard) and `.gitleaks.toml` allowlisting documented placeholders. | ✅ | 2026-06-25 |
| TASK-024 | Create `LICENSE` (MIT) and `README.md` documenting the two-repository model, security model, and setup. | ✅ | 2026-06-25 |
| TASK-025 | `git init` the framework repo, run `pre-commit install`, and verify `git status` shows no `.env`/`content_mirror/`/`data/`. Create the **private** `knowledgebase-content` repo separately. | ✅ | 2026-06-25 |
| TASK-026 | On the GitHub remote, enable secret scanning + push protection (Settings → Code security) before the first push. Publish only after a clean `gitleaks detect` run. | ✅ | 2026-06-25 |

## 3. Alternatives

- **ALT-001**: GitBook (SaaS) — rejected for the internal-only requirement: paid SaaS, content leaves the network, and Git Sync needs a paid tier. Wiki.js is FOSS, self-hosted, and its Git storage module gives the same clean-Markdown-in-Git ingestion path with no licensing cost.
- **ALT-008**: Other FOSS wikis — Outline (best editor, but DB-backed → ingestion needs an API crawler instead of git-pull), BookStack (DB-backed, API/export ingestion), MkDocs/Docusaurus (git-native but dev-centric authoring, weak for non-technical contributors). Wiki.js chosen as the only option pairing browser authoring (REQ-001) with native Git-Markdown storage (REQ-002), leaving the ingestion design unchanged.
- **ALT-002**: Fine-tuning a model on the knowledge corpus instead of RAG — rejected: tribal knowledge changes frequently, fine-tuning cannot cite sources, and retraining cost/latency is prohibitive versus incremental re-embedding.
- **ALT-003**: A hosted managed RAG service (e.g., vendor "chat-with-docs") — rejected to retain control over data residency (SEC-003), model selection, and integration with existing Python tooling.
- **ALT-004**: Hosted embeddings (Voyage AI, Azure/OpenAI `text-embedding-3`) — rejected for the initial version in favor of local Ollama embeddings to incur zero per-call cost and keep embedding text fully on-host (SEC-003). Embedding model remains configurable via `KB_EMBED_MODEL`; a hosted provider can be added later.
- **ALT-006**: GitHub/M365 Copilot as the generation backend — rejected: Copilot does not expose a general chat-completions API for custom applications. Anthropic enterprise (already EDP-covered and free-to-team under the existing contract) is used instead. The provider abstraction (PAT-002) keeps a Copilot/OpenAI-compatible endpoint as a drop-in future option.
- **ALT-007**: Frontier models (`claude-opus-4-8`) as the default answerer — deferred to control cost; the initial default is the lowest-cost `claude-haiku-4-5-20251001` with escalation to `claude-sonnet-4-6` only when needed.
- **ALT-009**: Slack/Teams chat bot as an access surface — dropped. Users already work inside the wiki, so an embedded ask widget on each Wiki.js page delivers Q&A in context without operating a separate bot, app registration, or message-platform integration.
- **ALT-010**: Separate per-app login instead of SSO — rejected; reusing the org's Entra ID (Azure AD) over OIDC avoids new credentials and centralizes access control (REQ-012).
- **ALT-005**: Postgres + pgvector instead of ChromaDB — viable at scale; deferred because ChromaDB requires no server and suits the initial single-host deployment. Migration path noted in RISK-003.

## 4. Dependencies

- **DEP-001**: Self-hosted Wiki.js (Docker) + PostgreSQL, with the Git storage module configured against the internal `knowledgebase-content` repo (CON-002).
- **DEP-002**: `anthropic` Python SDK (`>=0.40.0`) and a valid enterprise `ANTHROPIC_API_KEY` with EDP/no-training terms.
- **DEP-003**: Ollama installed and running on-host, with `KB_EMBED_MODEL` (default `nomic-embed-text`) pulled; `ollama` Python SDK (`>=0.3.0`).
- **DEP-004**: `chromadb` (`>=0.5.0`) for the persistent vector store.
- **DEP-005**: `flask`, `requests`, `python-dotenv` (mirrors the tool `requirements.txt`).
- **DEP-006**: `markdown-it-py` for heading-aware Markdown parsing in the chunker.
- **DEP-007**: Git CLI available on PATH for `content_mirror/` pulls.
- **DEP-008**: Entra ID (Azure AD) app registration (client ID/secret, redirect URI, tenant ID) for OIDC SSO (REQ-012).
- **DEP-009**: `authlib` (OIDC client) and `flask-cors` (REQ-013).
- **DEP-010**: `pypdf` and `python-docx` for document parsing (TASK-007B).

## 5. Files

- **FILE-001**: `C:\knowledgebase\config.py` — central env-driven configuration loader.
- **FILE-002**: `C:\knowledgebase\requirements.txt` — pinned Python dependencies.
- **FILE-003**: `C:\knowledgebase\.env.example` / `.gitignore` — secret template and ignore rules.
- **FILE-019**: `C:\knowledgebase\.pre-commit-config.yaml` / `.gitleaks.toml` — secret-scanning hooks and allowlist.
- **FILE-020**: `C:\knowledgebase\README.md` / `LICENSE` — OSS docs (two-repo model, security, setup) and MIT license.
- **FILE-004**: `C:\knowledgebase\ingest\loader.py` — Markdown loader and page hashing.
- **FILE-005**: `C:\knowledgebase\ingest\chunker.py` — heading-aware chunker.
- **FILE-006**: `C:\knowledgebase\ingest\sensitivity.py` — ingestion sensitivity gate (SEC-003).
- **FILE-007**: `C:\knowledgebase\ingest\embedder.py` — local Ollama embedding client.
- **FILE-008**: `C:\knowledgebase\ingest\store.py` — ChromaDB persistence wrapper.
- **FILE-009**: `C:\knowledgebase\ingest\run.py` — incremental ingestion orchestrator.
- **FILE-010**: `C:\knowledgebase\retrieval\retriever.py` — query embedding + vector search.
- **FILE-011**: `C:\knowledgebase\retrieval\prompt.py` — grounded RAG prompt builder.
- **FILE-012**: `C:\knowledgebase\retrieval\provider.py` — `LLMProvider` abstraction + Anthropic/OpenAI-compatible backends (PAT-002).
- **FILE-018**: `C:\knowledgebase\retrieval\generator.py` — provider-agnostic generation + escalation.
- **FILE-013**: `C:\knowledgebase\app.py` — Flask API (`/api/ask`, `/api/health`).
- **FILE-014**: `C:\knowledgebase\cli.py` — `kb ask` command-line surface.
- **FILE-015**: `C:\knowledgebase\surfaces\upload\` — Entra-authenticated document upload page + handler.
- **FILE-016**: `C:\knowledgebase\surfaces\widget\ask-widget.js` — embeddable chat widget for Wiki.js pages.
- **FILE-021**: `C:\knowledgebase\auth\oidc.py` — Entra ID OIDC auth, `@login_required`, CLI token auth.
- **FILE-022**: `C:\knowledgebase\ingest\docparser.py` — PDF/Word/Markdown/text document parser.
- **FILE-017**: `C:\knowledgebase\scripts\refresh.py` — scheduled re-ingestion runner.

## 6. Testing

- **TEST-001**: `tests/test_loader.py` — given a fixture Markdown tree, `load_pages` returns correct titles, bodies, and stable `sha256` values.
- **TEST-002**: `tests/test_chunker.py` — chunks never exceed `max_tokens`, preserve heading paths, and overlap by the configured amount.
- **TEST-003**: `tests/test_sensitivity.py` — pages with `sensitivity: restricted` front matter are rejected; others pass.
- **TEST-004**: `tests/test_store.py` — upsert then query returns the inserted chunk; `delete_by_page` removes all chunks for a page; `get_page_hash` round-trips.
- **TEST-005**: `tests/test_incremental.py` — running `ingest/run.py` twice with unchanged content issues zero embedding calls (mock embedder asserts call count == 0 on second run).
- **TEST-006**: `tests/test_retriever.py` — for a seeded store, a question semantically matching one page ranks that page's chunk first.
- **TEST-007**: `tests/test_prompt.py` — with empty retrieved context, the built prompt contains the refusal instruction; citations markers are present when chunks exist.
- **TEST-008**: `tests/test_api.py` — `POST /api/ask` returns `200` with `answer` and `citations` keys; `GET /api/health` returns `200`. Anthropic provider and Ollama embedder mocked.
- **TEST-009**: `tests/test_provider.py` — `get_provider()` returns `AnthropicProvider` when `KB_LLM_PROVIDER=anthropic`; `OpenAICompatibleProvider.generate` raises `NotImplementedError`; no caller in `retrieval/generator.py` imports a vendor SDK directly (PAT-002).
- **TEST-010**: `tests/test_docparser.py` — `parse_document` extracts text from fixture `.pdf`, `.docx`, `.md`, `.txt` files and assigns `path = "upload:<filename>"`; an unsupported extension raises `UnsupportedFormat`.
- **TEST-011**: `tests/test_upload.py` — `POST /upload` rejects unauthenticated requests (302/401), rejects disallowed extensions and oversize files (SEC-006), and on a valid file saves to `data/uploads/` and triggers ingest. Entra session and ingest mocked.
- **TEST-012**: `tests/test_auth_cors.py` — `/api/ask` returns 401/redirect without a session or valid `KB_CLI_TOKEN`; CORS preflight allows `KB_WIKIJS_BASE_URL` and denies other origins (SEC-008).

## 7. Risks & Assumptions

- **RISK-001**: Sending question + retrieved context to Anthropic may exceed approved data-handling policy. Mitigation: enterprise EDP (no-training) terms, local on-host embeddings (no third-party embeddings vendor), SEC-003 sensitivity gate, and explicit org sign-off before ingesting any content.
- **RISK-006**: Local Ollama embeddings have lower retrieval quality than hosted frontier embeddings and consume host RAM/CPU. Mitigation: `ingest/embedder.py` is the sole embedding touchpoint and `KB_EMBED_MODEL` is configurable, so a hosted embeddings provider can be swapped in if retrieval quality is insufficient (ALT-004).
- **RISK-007**: The upload page is an abuse/malware vector (oversized files, malicious PDFs, prompt-injection content). Mitigation: SSO-gate (SEC-006), extension allowlist, size cap, content-type validation; treat parsed text as untrusted and rely on the grounded/cited prompt. Optional AV scan of `data/uploads/` is a future enhancement.
- **RISK-008**: Document parsing (scanned PDFs, complex tables) may extract poor or empty text. Mitigation: `docparser.py` logs low-yield extractions; OCR is out of scope for the initial version and noted as a future enhancement.
- **RISK-009**: Embedding the widget requires injecting custom JS into Wiki.js (theme code). Mitigation: ship a single reviewed `ask-widget.js`, scope CORS to the wiki origin (SEC-008), and require an authenticated session so the endpoint is not open.
- **RISK-002**: RAG answers can hallucinate when retrieval is weak. Mitigation: enforce citation-or-refuse in the prompt (SEC-002) and surface retrieved sources in every answer for human verification.
- **RISK-003**: ChromaDB single-host storage may not scale to large corpora or multi-instance serving. Mitigation: `ingest/store.py` is the only module touching the vector DB, isolating a future migration to pgvector (ALT-005).
- **RISK-004**: Wiki.js Git-sync conflicts (e.g., concurrent edits vs. external commits) could stall content mirroring. Mitigation: treat Wiki.js as the sole writer to `knowledgebase-content`; `content_mirror/` pulls are read-only one-way for ingestion; resolve authoring conflicts inside Wiki.js.
- **RISK-005**: Model IDs and SDK interfaces evolve. Mitigation: model IDs are env-configurable (REQ-005); SDK versions pinned (TASK-004).
- **ASSUMPTION-001**: An internal host is available to run Wiki.js + PostgreSQL via Docker, and the org's Anthropic enterprise API access is provisioned. No third-party SaaS or embeddings budget is required.
- **ASSUMPTION-002**: Engineers will contribute content; an editorial owner curates structure and quality. Without contribution, the knowledge base provides no value regardless of technical correctness.
- **ASSUMPTION-003**: Initial deployment is single-host on the user's Windows environment, consistent with the the tool project footprint.

## 8. Related Specifications / Further Reading

- the tool BackPort Assistance Agent: `C:\the tool\CLAUDE.md` (Python-fetches / LLM-analyzes convention, GUD-001)
- Wiki.js documentation: https://docs.requarks.io — Git storage module: https://docs.requarks.io/storage/git
- Anthropic Messages API documentation: https://docs.anthropic.com
- Ollama embeddings documentation: https://docs.ollama.com
- ChromaDB persistent client documentation: https://docs.trychroma.com
