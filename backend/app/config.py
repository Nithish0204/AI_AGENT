"""
Configuration Management
========================
Uses pydantic-settings to load all config from environment variables or .env file.
This means every threshold, API key, and feature flag is configurable without
changing code — important for production deployments and Docker.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings. Values come from environment variables,
    falling back to the defaults defined here.
    
    KEY CONCEPT - Configuration as Code:
    All guardrail thresholds (confidence levels, amount limits) are config,
    not hardcoded. This lets operators tune the agent's behavior without
    redeploying code.
    """
    
    # --- LLM ---
    gemini_api_key: str = ""
    # Model for reasoning/critic (needs to be strong)
    reasoning_model: str = "gemini-3.5-flash-lite"
    # Model for triage/extraction (can be faster/cheaper)
    fast_model: str = "gemini-3.5-flash-lite"
    
    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/support_agent.db"
    
    # --- Vector Store ---
    chroma_persist_dir: str = "./data/chroma"
    embedding_model: str = "models/gemini-embedding-001"
    
    # --- Retrieval ---
    retrieval_top_k: int = 10          # Candidates from hybrid search
    rerank_top_k: int = 5              # Final chunks after reranking
    bm25_weight: float = 0.4           # Weight for BM25 in RRF
    dense_weight: float = 0.6          # Weight for dense embeddings in RRF
    
    # --- Guardrail Thresholds ---
    # These thresholds determine autonomy levels (Section 4 of the spec)
    auto_resolve_confidence: float = 0.85    # >= this: can auto-resolve
    human_approval_confidence: float = 0.60  # >= this but < auto: needs approval
    auto_resolve_max_amount: float = 2000.0  # Max $ for auto-resolve
    human_approval_max_amount: float = 10000.0  # Above this: always escalate
    max_refund_claims_30_days: int = 3       # Fraud flag threshold
    max_critic_retries: int = 1              # Retry once, then escalate
    
    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    
    # --- Feature Flags ---
    enable_pii_redaction: bool = True
    enable_injection_detection: bool = True
    enable_reranker: bool = True
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore unknown env vars
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Singleton settings instance. Cached so we only read .env once.
    Call this anywhere you need settings:
        from app.config import get_settings
        settings = get_settings()
    """
    return Settings()
