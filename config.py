from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Required environment variable '{key}' is not set. See .env.example.")
    return value


def _get(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class Config:
    # Generation
    llm_provider: str
    answer_model: str
    escalation_model: str
    anthropic_api_key: str

    # OpenAI-compatible fallback (optional)
    openai_base_url: str
    openai_api_key: str

    # Embeddings
    embed_model: str
    ollama_host: str

    # Retrieval
    top_k: int
    chroma_path: Path

    # Content mirror
    content_repo_url: str
    content_mirror_path: Path

    # Wiki.js
    wikijs_base_url: str

    # SSO
    oidc_tenant_id: str
    oidc_client_id: str
    oidc_client_secret: str
    oidc_redirect_uri: str
    flask_secret_key: str

    # CLI
    cli_token: str

    # Uploads
    max_upload_mb: int
    uploads_path: Path


def load_config() -> Config:
    return Config(
        llm_provider=_get("KB_LLM_PROVIDER", "anthropic"),
        answer_model=_get("KB_ANSWER_MODEL", "claude-haiku-4-5-20251001"),
        escalation_model=_get("KB_ESCALATION_MODEL", "claude-sonnet-4-6"),
        anthropic_api_key=_get("ANTHROPIC_API_KEY", ""),

        openai_base_url=_get("KB_OPENAI_BASE_URL", ""),
        openai_api_key=_get("KB_OPENAI_API_KEY", ""),

        embed_model=_get("KB_EMBED_MODEL", "nomic-embed-text"),
        ollama_host=_get("KB_OLLAMA_HOST", "http://127.0.0.1:11434"),

        top_k=int(_get("KB_TOP_K", "8")),
        chroma_path=Path(_get("KB_CHROMA_PATH", "./data/chroma")),

        content_repo_url=_get("KB_CONTENT_REPO_URL", ""),
        content_mirror_path=Path(_get("KB_CONTENT_MIRROR_PATH", "./content_mirror")),

        wikijs_base_url=_get("KB_WIKIJS_BASE_URL", ""),

        oidc_tenant_id=_get("KB_OIDC_TENANT_ID", ""),
        oidc_client_id=_get("KB_OIDC_CLIENT_ID", ""),
        oidc_client_secret=_get("KB_OIDC_CLIENT_SECRET", ""),
        oidc_redirect_uri=_get("KB_OIDC_REDIRECT_URI", "http://127.0.0.1:5057/auth/callback"),
        flask_secret_key=_get("KB_FLASK_SECRET_KEY", ""),

        cli_token=_get("KB_CLI_TOKEN", ""),

        max_upload_mb=int(_get("KB_MAX_UPLOAD_MB", "25")),
        uploads_path=Path(_get("KB_UPLOADS_PATH", "./data/uploads")),
    )
