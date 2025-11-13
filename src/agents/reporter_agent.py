"""
Reporter Agent - generates human-readable outputs and visualisations.
"""
from __future__ import annotations

from typing import Dict, List

from src.agents.state import CitationMap, ResearchState
from src.utils.logger import default_logger as logger


class ReporterAgent:
    """Agent responsible for compiling reports and summaries."""

    def __init__(self, llm):
        self.llm = llm

    def generate_executive_summary(self, state: ResearchState) -> str:
        consensus = state.consensus_findings[:5]
        gaps = [gap.get("gap", "") for gap in state.research_gaps[:3]]

        prompt = (
            "Create a 3-4 sentence executive summary for the following research findings.\n"
            f"Query: {state.query}\n"
            f"Key Findings: {', '.join(consensus)}\n"
            f"Research Gaps: {', '.join(gaps)}\n"
            "Be concise and actionable."
        )

        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Executive summary generation failed: %s", exc)
            return "Executive summary unavailable."

    def generate_detailed_report(self, state: ResearchState) -> str:
        sources = state.validated_sources[:10]
        consensus = state.consensus_findings
        gaps = state.research_gaps
        contradictions = state.contradictions
        concepts = state.key_concepts

        sources_text = "\n".join(
            f"[{idx+1}] {source.get('title', '')} - {source.get('summary', '')[:200]}"
            for idx, source in enumerate(sources)
        )

        prompt = (
            "Generate a structured research report.\n"
            f"Query: {state.query}\n\nSOURCES:\n{sources_text}\n\n"
            "CONSENSUS FINDINGS:\n"
            f"{chr(10).join('- ' + finding for finding in consensus)}\n\n"
            "RESEARCH GAPS:\n"
            f"{chr(10).join('- ' + gap.get('gap', '') for gap in gaps)}\n\n"
            f"KEY CONCEPTS: {', '.join(concepts[:10])}\n\n"
            "Sections:\n"
            "1. Executive Summary\n"
            "2. Key Findings\n"
            "3. Notable Insights\n"
            "4. Research Gaps & Future Directions\n"
            "5. Conflicting Evidence\n"
            "6. Conclusion\n"
        )

        try:
            response = self.llm.invoke(prompt)
            report = response.content
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Detailed report generation failed: %s", exc)
            return "Detailed report generation failed."

        citations_section = "\n\n## SOURCES\n\n"
        for idx, source in enumerate(sources, 1):
            citations_section += f"[{idx}] {source.get('title', 'Unknown')}\n"
            if source.get("authors"):
                citations_section += f"    Authors: {', '.join(source.get('authors', [])[:3])}\n"
            citations_section += f"    URL: {source.get('url', 'N/A')}\n"
            citations_section += f"    Source: {source.get('source_type', 'Unknown')}\n\n"

        if contradictions:
            report += "\n\n## CONFLICTING EVIDENCE\n"
            for contradiction in contradictions:
                report += f"- {contradiction.get('description', '')}\n"

        return report + citations_section

    @staticmethod
    def create_citation_map(sources: List) -> CitationMap:
        """Build a citation map from validated sources."""

        citation_map = CitationMap()
        citation_map.total_sources = len(sources)

        for source in sources:
            source_type = source.get("source_type", "unknown")
            citation_map.by_type[source_type] = citation_map.by_type.get(source_type, 0) + 1

            published = str(source.get("published", ""))
            if published:
                year = published.split("-")[0]
                citation_map.by_year[year] = citation_map.by_year.get(year, 0) + 1

        # Include all sources, not just those with citation_count > 0
        # This ensures all sources from the report appear in top_cited
        # Format: [(title, citation_count, url), ...]
        cited = [
            (
                source.get("title", ""),
                source.get("citation_count", 0) or 0,
                source.get("url", "") or ""
            )
            for source in sources
        ]
        # Sort by citation count (descending), then by title (ascending) for sources with same count
        cited.sort(key=lambda item: (-item[1], item[0]))
        citation_map.top_cited = cited  # Return all sources, not just top 10

        return citation_map

    def generate_visualisations(self, state: ResearchState) -> List[Dict[str, object]]:
        """Prepare metadata describing visualisations to render."""

        visuals: List[Dict[str, object]] = []

        if state.knowledge_graph and state.knowledge_graph.nodes:
            visuals.append(
                {
                    "type": "knowledge_graph",
                    "title": "Research Knowledge Graph",
                    "description": f"{len(state.knowledge_graph.nodes)} nodes",
                    "data": state.knowledge_graph.dict(),
                }
            )

        if state.citation_map:
            visuals.append(
                {
                    "type": "citation_distribution",
                    "title": "Source Distribution",
                    "data": state.citation_map.dict(),
                }
            )

        if state.validation_scores:
            visuals.append(
                {
                    "type": "quality_scores",
                    "title": "Source Quality Scores",
                    "data": [
                        {"source": record.source_title[:40], "score": record.credibility_score}
                        for record in state.validation_scores[:10]
                    ],
                }
            )

        return visuals

    def report(self, state: ResearchState) -> Dict[str, object]:
        """Generate full report artifacts."""

        logger.info("Reporter: compiling artefacts")

        executive_summary = self.generate_executive_summary(state)
        detailed_report = self.generate_detailed_report(state)
        citation_map = self.create_citation_map(state.validated_sources)
        visualisations = self.generate_visualisations(state)

        logger.info(
            "Reporter: generated report (%d chars), %d visuals",
            len(detailed_report),
            len(visualisations),
        )

        return {
            "executive_summary": executive_summary,
            "detailed_report": detailed_report,
            "citation_map": citation_map,
            "visualizations": visualisations,
        }
