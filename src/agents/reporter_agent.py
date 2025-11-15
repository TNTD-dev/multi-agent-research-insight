"""
Reporter Agent - generates human-readable outputs and visualisations.
"""
from __future__ import annotations

import re
from typing import Dict, List

from src.agents.state import CitationMap, ResearchState
from src.config import ResearchDepthConfig
from src.utils.logger import default_logger as logger


class ReporterAgent:
    """Agent responsible for compiling reports and summaries."""

    def __init__(self, llm, depth_config: ResearchDepthConfig | None = None):
        self.llm = llm
        self.depth_config = depth_config

    def generate_executive_summary(self, state: ResearchState) -> str:
        detail_level = (
            self.depth_config.report_detail_level
            if self.depth_config
            else "standard"
        )
        
        if detail_level == "brief":
            max_findings = 3
            max_gaps = 2
            sentence_count = "2-3"
        elif detail_level == "detailed":
            max_findings = 7
            max_gaps = 5
            sentence_count = "5-6"
        else:  # standard
            max_findings = 5
            max_gaps = 3
            sentence_count = "3-4"
        
        consensus = state.consensus_findings[:max_findings]
        gaps = [gap.get("gap", "") for gap in state.research_gaps[:max_gaps]]

        prompt = (
            f"Create a {sentence_count} sentence executive summary for the following research findings.\n"
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
        detail_level = (
            self.depth_config.report_detail_level
            if self.depth_config
            else "standard"
        )
        max_sources = (
            self.depth_config.max_sources_in_report
            if self.depth_config
            else 10
        )
        
        sources = state.validated_sources[:max_sources]
        consensus = state.consensus_findings
        gaps = state.research_gaps
        contradictions = state.contradictions
        concepts = state.key_concepts

        sources_text = "\n".join(
            f"[{idx+1}] {source.get('title', '')} - {source.get('summary', '')[:200]}"
            for idx, source in enumerate(sources)
        )

        if detail_level == "brief":
            sections = (
                "Sections:\n"
                "1. Executive Summary\n"
                "2. Key Findings\n"
                "3. Conclusion\n"
            )
            concepts_text = f"KEY CONCEPTS: {', '.join(concepts[:5])}\n\n"
        elif detail_level == "detailed":
            sections = (
                "Sections:\n"
                "1. Executive Summary\n"
                "2. Key Findings\n"
                "3. Notable Insights\n"
                "4. Research Gaps & Future Directions\n"
                "5. Conflicting Evidence\n"
                "6. Methodology & Sources\n"
                "7. Conclusion\n"
            )
            concepts_text = f"KEY CONCEPTS: {', '.join(concepts[:15])}\n\n"
        else:  # standard
            sections = (
                "Sections:\n"
                "1. Executive Summary\n"
                "2. Key Findings\n"
                "3. Notable Insights\n"
                "4. Research Gaps & Future Directions\n"
                "5. Conflicting Evidence\n"
                "6. Conclusion\n"
            )
            concepts_text = f"KEY CONCEPTS: {', '.join(concepts[:10])}\n\n"
        
        # Add instruction to NOT create References section
        no_references_note = (
            "\n\nIMPORTANT: Do NOT create a 'References' or 'Sources' section. "
            "Do NOT add any citation lists like [1], [2], etc. in the Conclusion. "
            "The sources will be added automatically after your report. "
            "End your report with the Conclusion section only - just the conclusion text, nothing else."
        )

        prompt = (
            f"Generate a structured research report about: {state.query}\n\n"
            f"CRITICAL: The report must ONLY discuss topics directly related to '{state.query}'. "
            f"Do NOT include information about unrelated topics. If a finding mentions other domains "
            f"(e.g., financial data, other technologies), only include it if it is SPECIFICALLY about "
            f"how that domain relates to '{state.query}'.\n\n"
            f"SOURCES:\n{sources_text}\n\n"
            "CONSENSUS FINDINGS:\n"
            f"{chr(10).join('- ' + finding for finding in consensus)}\n\n"
            "RESEARCH GAPS:\n"
            f"{chr(10).join('- ' + gap.get('gap', '') for gap in gaps)}\n\n"
            f"{concepts_text}"
            f"{sections}"
            f"{no_references_note}"
        )

        try:
            response = self.llm.invoke(prompt)
            report = response.content
            
            # Remove any References or Sources section that LLM might have added
            # Look for common patterns: "References", "Sources", "Bibliography", etc.
            # Pattern to match section headers like "## References", "**References**", "Sources:", etc.
            # This pattern matches:
            # - Markdown headers: ## References, **References**, etc.
            # - Plain text: Sources:, References:, etc.
            references_pattern = r'(?i)(\n|^)(\*{0,2}#{0,2}\s*)?(References?|Sources?|Bibliography)(\*{0,2}#{0,2})?\s*:?\s*\n'
            # Find where References/Sources section starts
            match = re.search(references_pattern, report)
            if match:
                # Remove everything from References/Sources section onwards
                report = report[:match.start()].rstrip()
                logger.info("Reporter: removed LLM-generated References/Sources section")
            
            # Also check for citation lists that might appear without a header
            # Pattern to match lines starting with [1], [2], [10], etc. (citation format)
            # This matches any line that starts with [number] followed by text
            citation_list_pattern = r'\n\s*\[\d+\]\s+[^\n]+'
            citation_match = re.search(citation_list_pattern, report)
            if citation_match:
                # Find the start of the citation list (could be after "Sources:" or standalone)
                # Look backwards to find if there's a "Sources:" header before it
                before_citation = report[:citation_match.start()]
                sources_header_match = re.search(r'(?i)(Sources?|References?)\s*:?\s*$', before_citation, re.MULTILINE)
                
                if sources_header_match:
                    # Remove from "Sources:" header onwards
                    report = report[:sources_header_match.start()].rstrip()
                else:
                    # Remove from first citation onwards
                    report = report[:citation_match.start()].rstrip()
                logger.info("Reporter: removed LLM-generated citation list")
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Detailed report generation failed: %s", exc)
            return "Detailed report generation failed."

        # Ensure report ends with proper spacing before adding sections
        if not report.endswith("\n\n"):
            if report.endswith("\n"):
                report += "\n"
            else:
                report += "\n\n"
        
        citations_section = "\n\n---\n\n## SOURCES\n\n"
        for idx, source in enumerate(sources, 1):
            citations_section += f"[{idx}] {source.get('title', 'Unknown')}\n"
            if detail_level in {"standard", "detailed"}:
                if source.get("authors"):
                    citations_section += f"    Authors: {', '.join(source.get('authors', [])[:3])}\n"
                citations_section += f"    URL: {source.get('url', 'N/A')}\n"
                citations_section += f"    Source: {source.get('source_type', 'Unknown')}\n"
                if detail_level == "detailed":
                    if source.get("published"):
                        citations_section += f"    Published: {source.get('published', 'N/A')}\n"
                    if source.get("citation_count", 0) > 0:
                        citations_section += f"    Citations: {source.get('citation_count', 0)}\n"
            citations_section += "\n"

        if contradictions:
            report += "\n\n---\n\n## CONFLICTING EVIDENCE\n\n"
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
