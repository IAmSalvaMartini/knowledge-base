# Knowledge Base Framework

An open-source, self-hostable framework for turning an organization's tribal
knowledge into a natural-language, cited Q&A system using Retrieval-Augmented
Generation (RAG).

Engineers author docs in a wiki (or upload files through an SSO-gated page); the
framework ingests them into a local vector store and answers questions through a
chat widget embedded in every wiki page (and a CLI) — every answer backed by
citations to the source pages.

> **This repository contains only the framework code.** It ships with **no
> organizational content and no secrets.** Your private knowledge lives in a
> separate, private repository (see [Two-Repository Model](#two-repository-model)).

## Architecture

```
Wiki.js (authoring) ─Git storage─▶ knowledgebase-content (PRIVATE repo) ─┐
                                                                         │
SSO upload page (PDF/Word/MD/txt) ─▶ data/uploads/ ─────────────────────┤
                                                                         │
   ┌──────────────────────── ingest ─────────────────────────▼──────────┐
   │  load/parse → sensitivity gate → chunk → embed (local Ollama) → Chroma │
   └────────────────────────────────────────────────────────────────────┘
                                              │
   ┌──────────────────────── retrieval ──────▼───────────────────────┐
   │  embed query → top-K search → grounded prompt → LLM → answer+cite│
   └──────────────────────────────────────────────────────────────────┘
                                              │
        ask widget embedded in Wiki.js pages  ·  CLI (`kb ask`)
                  (all browser access via Entra ID SSO / OIDC)
```

- **Authoring:** [Wiki.js](https://js.wiki) (FOSS, self-hosted) with its Git storage module, plus an SSO-gated upload page for PDF/Word/Markdown/text.
- **Auth:** Microsoft Entra ID (Azure AD) via OIDC for all browser surfaces.
- **Embeddings:** local [Ollama](https://ollama.com) — text never leaves the host.
- **Generation:** provider-abstracted; default backend is Anthropic (enterprise/EDP terms). Any OpenAI-compatible endpoint can be substituted via config.
- **Vector store:** [ChromaDB](https://www.trychroma.com), persisted locally.

## Two-Repository Model

| Repo | Visibility | Contents |
|------|-----------|----------|
| **this framework** | **Public / OSS** | Code, config templates, docs. No content, no secrets. |
| `knowledgebase-content` | **Private** | Your Wiki.js Markdown — the actual tribal knowledge. |

The framework reads private content at runtime by cloning the private repo into
`content_mirror/` (gitignored). Derived embeddings are written to `data/`
(gitignored) because **the vector store contains the text of your private
documents**. Neither directory is ever committed to this public repo.

## Security

This project is built to be published safely:

- **No secrets in git.** All credentials are read from `.env`, which is
  gitignored. Only [`.env.example`](.env.example) (placeholders) is committed.
- **No private content in git.** `content_mirror/` and `data/` are gitignored.
- **Secret scanning.** A [pre-commit](https://pre-commit.com) hook runs
  [gitleaks](https://github.com/gitleaks/gitleaks) and `detect-private-key` on
  every commit (see [`.pre-commit-config.yaml`](.pre-commit-config.yaml)).
- **Defense in depth.** Enable GitHub **secret scanning + push protection** on
  the repository (Settings → Code security) so pushes containing secrets are
  blocked server-side.
- **No hardcoded config.** Models, endpoints, and paths come from environment
  variables — nothing vendor- or org-specific is baked into source.

### Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Enable the secret-scanning git hooks (do this before your first commit)
pip install pre-commit
pre-commit install

# 3. Create your local config from the template
cp .env.example .env
#   ...then edit .env with real values (never commit it)

# 4. Pull a local embedding model
ollama pull nomic-embed-text

# 5. Ingest content and run
python -m ingest.run        # build/refresh the vector store
python app.py               # start the web API + chat UI
kb ask "how do I resolve a merge conflict during a backport?"   # or use the CLI
```

## Configuration

All configuration is environment-driven. See [`.env.example`](.env.example) for
the full list. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `KB_LLM_PROVIDER` | `anthropic` | Generation backend (`anthropic` \| `openai_compatible`). |
| `KB_ANSWER_MODEL` | `claude-haiku-4-5-20251001` | Default low-cost answering model. |
| `KB_ESCALATION_MODEL` | `claude-sonnet-4-6` | Higher-capability model for complex questions. |
| `KB_EMBED_MODEL` | `nomic-embed-text` | Local Ollama embedding model. |
| `KB_OLLAMA_HOST` | `http://127.0.0.1:11434` | Local Ollama endpoint. |
| `KB_TOP_K` | `8` | Chunks retrieved per query. |
| `KB_CHROMA_PATH` | `./data/chroma` | Vector store location (gitignored). |

## Implementation Plan

The full, phased build plan lives in
[`plan/feature-knowledge-base-1.md`](plan/feature-knowledge-base-1.md).

## Contributing

1. Run `pre-commit install` before committing — secret scanning is mandatory.
2. Never add real credentials, internal URLs, or organizational content.
3. Add tests under `tests/` for new modules (see the plan's Testing section).

## License

[MIT](LICENSE) © 2026 IAmSalvaMartini
