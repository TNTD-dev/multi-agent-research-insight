"""
Validation Agent - evaluates discovered sources for credibility and relevance.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from src.agents.state import (
    CredibilityReport,
    ResearchSource,
    ResearchState,
    ValidationScore,
)
from src.config import ResearchDepthConfig
from src.utils.logger import default_logger as logger


class ValidationAgent:
    """Agent responsible for validating discovered sources."""

    def __init__(self, llm, depth_config: ResearchDepthConfig | None = None):
        self.llm = llm
        self.depth_config = depth_config

    def calculate_source_score(self, source: ResearchSource) -> Dict[str, object]:
        """Compute a heuristic credibility score for a source."""

        score = 0
        factors: List[str] = []

        source_type = source.get("source_type", "")
        if source_type == "semantic_scholar":
            score += 28
            factors.append("Peer-reviewed (+28)")
        elif source_type == "arxiv":
            score += 25
            factors.append("arXiv preprint (+25)")
        else:
            score += 15
            factors.append("Web source (+15)")

        citations = source.get("citation_count", 0) or 0
        if citations > 100:
            citation_score = 25
        elif citations > 50:
            citation_score = 20
        elif citations > 10:
            citation_score = 15
        else:
            citation_score = 5
        score += citation_score
        factors.append(f"Citations: {citations} (+{citation_score})")

        published = source.get("published", "")
        try:
            if published:
                year = int(str(published).split("-")[0])
                age = datetime.now().year - year
                if age <= 1:
                    recency_score = 20
                elif age <= 3:
                    recency_score = 15
                elif age <= 5:
                    recency_score = 10
                else:
                    recency_score = 5
                score += recency_score
                factors.append(f"Age: {age}y (+{recency_score})")
        except Exception:  # pragma: no cover - defensive
            score += 10

        summary_length = len(source.get("summary", ""))
        if summary_length > 200:
            score += 20
            factors.append("Substantial summary (+20)")
        elif summary_length > 100:
            score += 15
            factors.append("Moderate summary (+15)")
        else:
            score += 5
            factors.append("Brief summary (+5)")

        final_score = min(score, 100)
        return {
            "score": final_score,
            "factors": factors,
            "grade": self._score_to_grade(final_score),
        }

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 85:
            return "A - Excellent"
        if score >= 70:
            return "B - Good"
        if score >= 55:
            return "C - Fair"
        if score >= 40:
            return "D - Poor"
        return "F - Very Poor"

    def check_relevance(self, source: ResearchSource, query: str) -> Dict[str, object]:
        """Use the LLM to determine relevance of a source."""

        prompt = f"""Assess relevance to query.

Query: {query}
Title: {source.get('title', 'Unknown')}
Summary: {source.get('summary', '')[:300]}

Format strictly as:
RELEVANT: [YES/NO]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASON: [One sentence]"""

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()

            lines = [line.strip() for line in content.splitlines() if line.strip()]
            relevance_line = next((line for line in lines if line.upper().startswith("RELEVANT")), "")
            confidence_line = next((line for line in lines if line.upper().startswith("CONFIDENCE")), "")
            reason_line = next((line for line in lines if line.upper().startswith("REASON")), "")

            is_relevant = "YES" in relevance_line.upper()
            confidence = confidence_line.split(":", 1)[-1].strip() if ":" in confidence_line else "MEDIUM"
            reason = reason_line.split(":", 1)[-1].strip() if ":" in reason_line else "No reason provided."

            return {
                "is_relevant": is_relevant,
                "confidence": confidence,
                "reason": reason,
            }
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Relevance check failed: %s", exc)
            return {"is_relevant": True, "confidence": "LOW", "reason": "LLM error"}

    def validate(self, state: ResearchState) -> Dict[str, object]:
        """Validate discovered sources and return state updates."""

        logger.info("=" * 70)
        logger.info("VALIDATION AGENT")
        logger.info("=" * 70)

        raw_sources = state.raw_sources
        query = state.query

        validated: List[ResearchSource] = []
        score_records: List[ValidationScore] = []

        logger.info("Validating %d sources", len(raw_sources))
        for idx, source in enumerate(raw_sources, start=1):
            score_result = self.calculate_source_score(source)
            relevance = self.check_relevance(source, query)

            min_score = (
                self.depth_config.validation_min_score
                if self.depth_config
                else 40
            )

            if relevance["is_relevant"] and score_result["score"] >= min_score:
                validated.append(source)
                score_records.append(
                    ValidationScore(
                        source_id=source.get("id", ""),
                        source_title=source.get("title", ""),
                        credibility_score=score_result["score"],
                        grade=score_result["grade"],
                        factors=score_result["factors"],
                        relevance=relevance,
                    )
                )
                logger.info("✓ Source %d accepted (%s)", idx, score_result["grade"])
            else:
                logger.info("✗ Source %d rejected", idx)

        avg_score = (
            sum(record.credibility_score for record in score_records) / len(score_records)
            if score_records
            else 0.0
        )

        credibility_report = CredibilityReport(
            total_validated=len(validated),
            average_quality_score=round(avg_score, 2),
            score_distribution={
                "excellent": len([record for record in score_records if record.credibility_score >= 85]),
                "good": len(
                    [record for record in score_records if 70 <= record.credibility_score < 85]
                ),
                "fair": len(
                    [record for record in score_records if 55 <= record.credibility_score < 70]
                ),
            },
        )

        logger.info(
            "Validation complete. %d/%d accepted. Avg score: %.1f",
            len(validated),
            len(raw_sources),
            avg_score,
        )

        return {
            "validated_sources": validated,
            "validation_scores": score_records,
            "credibility_report": credibility_report,
            "source_quality_avg": float(avg_score),
        }