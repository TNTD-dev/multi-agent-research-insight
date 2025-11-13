"""
Monitoring Agent - sets up alerting and trend tracking for ongoing research.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List

from datetime import datetime

from src.agents.state import AlertTrigger, ResearchState, TrendAnalysis
from src.utils.logger import default_logger as logger


class MonitoringAgent:
    """Agent in charge of monitoring configurations and analytics."""

    def __init__(self, llm):
        self.llm = llm

    def create_alert_triggers(self, query: str, concepts: List[str]) -> List[AlertTrigger]:
        """Generate alert triggers based on query and extracted concepts."""

        triggers: List[AlertTrigger] = []

        for concept in concepts[:8]:
            triggers.append(
                AlertTrigger(
                    type="keyword_match",
                    keyword=concept,
                    priority="high" if len(concept.split()) > 1 else "medium",
                    action="notify",
                )
            )

        triggers.append(
            AlertTrigger(
                type="citation_threshold",
                threshold=50,
                priority="high",
                action="alert",
            )
        )

        triggers.append(
            AlertTrigger(
                type="new_publication",
                timeframe_days=7,
                priority="medium",
                action="daily_digest",
            )
        )

        return triggers

    def analyse_trends(self, sources: List, concepts: List[str]) -> TrendAnalysis:
        """Build trend analytics from validated sources."""

        emerging_topics: List[Dict[str, object]] = []
        concept_counts = Counter()
        for source in sources:
            text = f"{source.get('title', '')} {source.get('summary', '')}".lower()
            for concept in concepts:
                if concept.lower() in text:
                    concept_counts[concept] += 1

        for topic, count in concept_counts.most_common(8):
            emerging_topics.append({"topic": topic, "frequency": count, "trend": "rising"})

        year_counts: Dict[str, int] = defaultdict(int)
        for source in sources:
            published = source.get("published", "")
            try:
                year = int(str(published).split("-")[0])
                year_counts[str(year)] += 1
            except Exception:  # pragma: no cover
                continue

        avg_citations: Dict[str, float] = defaultdict(float)
        citation_totals: Dict[str, List[int]] = defaultdict(list)
        for source in sources:
            try:
                year = int(str(source.get("published", "")).split("-")[0])
                citation_totals[str(year)].append(source.get("citation_count", 0))
            except Exception:  # pragma: no cover
                continue

        for year, citations in citation_totals.items():
            if citations:
                avg_citations[year] = sum(citations) / len(citations)

        author_counts = Counter()
        for source in sources:
            for author in source.get("authors", [])[:2]:
                author_counts[author] += 1

        author_networks = [{"author": author, "papers": count} for author, count in author_counts.most_common(10)]

        return TrendAnalysis(
            emerging_topics=emerging_topics,
            publication_velocity=dict(year_counts),
            citation_trends=dict(avg_citations),
            author_networks=author_networks,
        )

    def monitor(self, state: ResearchState) -> Dict[str, object]:
        """Set up monitoring artefacts based on the final state."""

        triggers = self.create_alert_triggers(state.query, state.key_concepts)
        trends = self.analyse_trends(state.validated_sources, state.key_concepts)

        monitoring_config = {
            "enabled": True,
            "check_frequency": "daily",
            "last_check": datetime.now().isoformat(),
        }

        logger.info(
            "Monitoring: configured %d triggers, %d emerging topics",
            len(triggers),
            len(trends.emerging_topics),
        )

        return {
            "monitoring_enabled": monitoring_config["enabled"],
            "alert_triggers": triggers,
            "trend_analysis": trends,
        }
