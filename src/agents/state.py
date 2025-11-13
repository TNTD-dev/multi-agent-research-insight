"""
Shared State Definition for Multi-Agent Research System
Using Pydantic models for validation and serialization.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DictLikeModel(BaseModel):
    """Base Pydantic model that mimics dict-like access used in legacy code."""

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        extra = "allow"

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, self.__dict__.get(item, default))

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def update(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            setattr(self, key, value)


class ResearchSource(DictLikeModel):
    """Research source information."""

    id: str
    title: str
    authors: List[str] = Field(default_factory=list)
    summary: str = ""
    full_text: str = ""
    url: str = ""
    published: str = ""
    categories: List[str] = Field(default_factory=list)
    source_type: str = "unknown"
    citation_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationScore(DictLikeModel):
    source_id: str
    source_title: str
    credibility_score: float
    grade: str
    factors: List[str] = Field(default_factory=list)
    relevance: Dict[str, Any] = Field(default_factory=dict)


class CredibilityReport(DictLikeModel):
    total_validated: int = 0
    average_quality_score: float = 0.0
    score_distribution: Dict[str, int] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ResearchGap(DictLikeModel):
    gap: str
    importance: str = ""


class Contradiction(DictLikeModel):
    type: str
    description: str
    severity: str
    sources_positive: List[str] = Field(default_factory=list)
    sources_negative: List[str] = Field(default_factory=list)


class KnowledgeGraphNode(DictLikeModel):
    id: str
    label: str
    type: str
    url: Optional[str] = None


class KnowledgeGraphEdge(DictLikeModel):
    source: str
    target: str
    relation: str


class KnowledgeGraph(DictLikeModel):
    nodes: List[KnowledgeGraphNode] = Field(default_factory=list)
    edges: List[KnowledgeGraphEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CitationMap(DictLikeModel):
    total_sources: int = 0
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_year: Dict[str, int] = Field(default_factory=dict)
    top_cited: List[Any] = Field(default_factory=list)
    citation_network: List[Dict[str, Any]] = Field(default_factory=list)


class AlertTrigger(DictLikeModel):
    type: str
    keyword: Optional[str] = None
    threshold: Optional[int] = None
    timeframe_days: Optional[int] = None
    priority: str = "medium"
    action: str = "notify"


class TrendAnalysis(DictLikeModel):
    emerging_topics: List[Dict[str, Any]] = Field(default_factory=list)
    publication_velocity: Dict[str, Any] = Field(default_factory=dict)
    citation_trends: Dict[str, Any] = Field(default_factory=dict)
    author_networks: List[Dict[str, Any]] = Field(default_factory=list)


class PaperCluster(DictLikeModel):
    n_clusters: int = 0
    clusters: Dict[str, Any] = Field(default_factory=dict)
    cluster_themes: Dict[str, Any] = Field(default_factory=dict)
    cluster_sizes: Dict[str, int] = Field(default_factory=dict)


class ResearchState(DictLikeModel):
    """Complete application state tracked across agents."""

    # User Input
    query: str
    research_depth: str = "standard"
    user_id: Optional[str] = None

    # Discovery Phase
    raw_sources: List[ResearchSource] = Field(default_factory=list)
    discovery_metadata: Dict[str, Any] = Field(default_factory=dict)

    # Validation Phase
    validated_sources: List[ResearchSource] = Field(default_factory=list)
    validation_scores: List[ValidationScore] = Field(default_factory=list)
    credibility_report: Optional[CredibilityReport] = None

    # Synthesis Phase
    knowledge_graph: Optional[KnowledgeGraph] = None
    research_gaps: List[ResearchGap] = Field(default_factory=list)
    consensus_findings: List[str] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)

    # RAG Phase
    vector_store_id: str = ""
    embeddings_created: bool = False
    rag_ready: bool = False

    # Reporter Phase
    executive_summary: str = ""
    detailed_report: str = ""
    citation_map: Optional[CitationMap] = None
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)

    # Monitoring Phase
    monitoring_enabled: bool = False
    alert_triggers: List[AlertTrigger] = Field(default_factory=list)
    trend_analysis: Optional[TrendAnalysis] = None

    # ML Analysis Phase
    ml_topics: List[Dict[str, Any]] = Field(default_factory=list)
    paper_clusters: Optional[PaperCluster] = None
    ml_quality_scores: List[Dict[str, Any]] = Field(default_factory=list)
    ml_insights: Dict[str, Any] = Field(default_factory=dict)

    # Quality Metrics
    source_quality_avg: float = 0.0
    citation_counts: Dict[str, Any] = Field(default_factory=dict)
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list)

    # Orchestration
    current_agent: str = "orchestrator"
    workflow_status: str = "initialized"
    errors: List[str] = Field(default_factory=list)
    synthesis_ready: bool = False

    # Timestamps
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""

