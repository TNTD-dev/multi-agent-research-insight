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

    tavily_key: Optional[str] = None
    max_arxiv_results: int = Field(default=8, ge=1, le=50)
    max_web_results: int = Field(default=8, ge=1, le=50)
    max_semantic_scholar_results: int = Field(default=5, ge=1, le=20)
    semantic_scholar_timeout: int = Field(default=10, ge=1, le=60)


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


class ResearchDepthConfig(BaseModel):
    """Configuration for research depth levels (quick, standard, deep)."""

    # Discovery settings
    max_arxiv_results: int = Field(ge=1, le=50)
    max_web_results: int = Field(ge=1, le=50)
    max_semantic_scholar_results: int = Field(ge=1, le=20)
    enable_reformulated_searches: bool = Field(default=False)
    reformulated_search_condition: Optional[str] = Field(
        default=None, description="Condition for reformulated searches: 'always', 'if_less_than_15', or None"
    )

    # Validation settings
    validation_min_score: int = Field(ge=0, le=100)

    # Synthesis settings
    max_concepts: int = Field(ge=1, le=30)
    max_consensus_findings: int = Field(ge=1, le=20)
    max_research_gaps: int = Field(ge=1, le=15)

    # Reporter settings
    report_detail_level: str = Field(default="standard", description="brief, standard, or detailed")
    max_sources_in_report: int = Field(ge=1, le=50)

    @classmethod
    def get_depth_config(cls, depth: str) -> "ResearchDepthConfig":
        """Get configuration for a specific research depth level."""
        depth_lower = depth.lower()
        
        if depth_lower == "quick":
            return cls(
                max_arxiv_results=3,
                max_web_results=3,
                max_semantic_scholar_results=2,
                enable_reformulated_searches=False,
                reformulated_search_condition=None,
                validation_min_score=40,
                max_concepts=8,
                max_consensus_findings=3,
                max_research_gaps=2,
                report_detail_level="brief",
                max_sources_in_report=5,
            )
        elif depth_lower == "deep":
            return cls(
                max_arxiv_results=15,
                max_web_results=12,
                max_semantic_scholar_results=10,
                enable_reformulated_searches=True,
                reformulated_search_condition="always",
                validation_min_score=50,
                max_concepts=20,
                max_consensus_findings=10,
                max_research_gaps=8,
                report_detail_level="detailed",
                max_sources_in_report=20,
            )
        else:  # standard (default)
            return cls(
                max_arxiv_results=8,
                max_web_results=8,
                max_semantic_scholar_results=5,
                enable_reformulated_searches=True,
                reformulated_search_condition="if_less_than_15",
                validation_min_score=40,
                max_concepts=15,
                max_consensus_findings=7,
                max_research_gaps=5,
                report_detail_level="standard",
                max_sources_in_report=10,
            )


class ResearchConfig(BaseModel):
    """Top-level configuration aggregating all sub-configs."""

    llm: LLMConfig
    search: SearchConfig = Field(default_factory=SearchConfig)
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
            tavily_key=os.getenv("TAVILY_KEY"),
            max_arxiv_results=int(os.getenv("MAX_ARXIV_RESULTS", 8)),
            max_web_results=int(os.getenv("MAX_WEB_RESULTS", 8)),
            max_semantic_scholar_results=int(os.getenv("MAX_SEMANTIC_SCHOLAR_RESULTS", 5)),
            semantic_scholar_timeout=int(os.getenv("SEMANTIC_SCHOLAR_TIMEOUT", 10)),
        )

        logging_config = LoggingConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/research_pipeline.log"),
            console_output=os.getenv("CONSOLE_OUTPUT", "true").lower() == "true",
        )

        config = cls(
            llm=llm_config,
            search=search_config,
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
            f"Tokens: {self.llm.max_tokens}"
        )


config = ResearchConfig.from_env()
