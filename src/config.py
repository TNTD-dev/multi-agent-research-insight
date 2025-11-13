"""
Application configuration management for the Multi-Agent Research System.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, field_validator

# Load environment variables from .env if present
load_dotenv()


class LLMConfig(BaseModel):
    """Configuration for the primary LLM provider."""

    api_key: str
    model_name: str = Field(default="llama-3.1-8b-instant")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=1, le=32000)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if not value or value.strip() == "":
            raise ValueError("GROQ_API_KEY must be set in the environment.")
        return value


class SearchConfig(BaseModel):
    """External search API configuration."""

    serpapi_key: Optional[str] = None
    max_arxiv_results: int = Field(default=8, ge=1, le=50)
    max_web_results: int = Field(default=8, ge=1, le=50)
    max_semantic_scholar_results: int = Field(default=5, ge=1, le=20)
    semantic_scholar_timeout: int = Field(default=10, ge=1, le=60)


class RAGConfig(BaseModel):
    """Retrieval Augmented Generation configuration."""

    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    chunk_size: int = Field(default=1000, ge=200, le=2000)
    chunk_overlap: int = Field(default=200, ge=0, le=500)
    chroma_persist_directory: str = Field(default="./chroma_db")
    similarity_top_k: int = Field(default=5, ge=1, le=20)


class MLConfig(BaseModel):
    """Machine learning analysis configuration."""

    enable_ml: bool = Field(default=True)
    n_topics: int = Field(default=5, ge=2, le=20)
    n_clusters: int = Field(default=3, ge=2, le=10)
    random_state: int = Field(default=42)


class LoggingConfig(BaseModel):
    """Logging preferences for the pipeline."""

    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default="logs/research_pipeline.log")
    console_output: bool = Field(default=True)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper


class ResearchConfig(BaseModel):
    """Top-level configuration aggregating all sub-configs."""

    llm: LLMConfig
    search: SearchConfig = Field(default_factory=SearchConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    ml: MLConfig = Field(default_factory=MLConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    output_dir: Path = Field(default=Path("./outputs"))
    reports_dir: Path = Field(default=Path("./reports"))
    visualisations_dir: Path = Field(default=Path("./visualisations"))

    @classmethod
    def from_env(cls) -> "ResearchConfig":
        """Construct configuration from environment variables."""

        llm_config = LLMConfig(
            api_key=os.getenv("GROQ_API_KEY", ""),
            model_name=os.getenv("MODEL_NAME", "llama-3.1-8b-instant"),
            temperature=float(os.getenv("TEMPERATURE", 0.3)),
            max_tokens=int(os.getenv("MAX_TOKENS", 4000)),
        )

        search_config = SearchConfig(
            serpapi_key=os.getenv("SERPAPI_KEY"),
            max_arxiv_results=int(os.getenv("MAX_ARXIV_RESULTS", 8)),
            max_web_results=int(os.getenv("MAX_WEB_RESULTS", 8)),
            max_semantic_scholar_results=int(os.getenv("MAX_SEMANTIC_SCHOLAR_RESULTS", 5)),
            semantic_scholar_timeout=int(os.getenv("SEMANTIC_SCHOLAR_TIMEOUT", 10)),
        )

        rag_config = RAGConfig(
            embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            chunk_size=int(os.getenv("CHUNK_SIZE", 1000)),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", 200)),
            chroma_persist_directory=os.getenv("CHROMA_PERSIST_DIR", "./chroma_db"),
            similarity_top_k=int(os.getenv("SIMILARITY_TOP_K", 5)),
        )

        ml_config = MLConfig(
            enable_ml=os.getenv("ENABLE_ML", "true").lower() == "true",
            n_topics=int(os.getenv("N_TOPICS", 5)),
            n_clusters=int(os.getenv("N_CLUSTERS", 3)),
            random_state=int(os.getenv("RANDOM_STATE", 42)),
        )

        logging_config = LoggingConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/research_pipeline.log"),
            console_output=os.getenv("CONSOLE_OUTPUT", "true").lower() == "true",
        )

        config = cls(
            llm=llm_config,
            search=search_config,
            rag=rag_config,
            ml=ml_config,
            logging=logging_config,
        )
        config._prepare_directories()
        return config

    def _prepare_directories(self) -> None:
        """Ensure output directories exist."""

        for directory in (self.output_dir, self.reports_dir, self.visualisations_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def get_llm(self) -> ChatGroq:
        """Return a configured ChatGroq client."""

        return ChatGroq(
            api_key=self.llm.api_key,
            model=self.llm.model_name,
            temperature=self.llm.temperature,
            max_tokens=self.llm.max_tokens,
        )

    def summary(self) -> str:
        """Human readable summary of the active configuration."""

        return (
            f"Model: {self.llm.model_name} | Temperature: {self.llm.temperature} | "
            f"Tokens: {self.llm.max_tokens} | ML Enabled: {self.ml.enable_ml}"
        )


config = ResearchConfig.from_env()
