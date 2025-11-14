"""
Validation Agent - evaluates discovered sources for credibility and relevance.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

from src.agents.state import (
    CredibilityReport,
    ResearchSource,
    ResearchState,
    ValidationScore,
)
from src.utils.logger import default_logger as logger


class ValidationAgent:
    """Agent responsible for validating discovered sources."""

    def __init__(self, llm):
        self.llm = llm

    def _check_domain_reputation(self, url: str) -> tuple[int, str]:
        """Check domain reputation and return bonus score and reason."""
        if not url:
            return 0, ""
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check TLD
            if domain.endswith('.edu'):
                return 5, "Educational domain (+5)"
            elif domain.endswith('.gov'):
                return 5, "Government domain (+5)"
            elif domain.endswith('.org'):
                return 3, "Organization domain (+3)"
            
            # Check for known academic domains
            academic_keywords = ['university', 'college', 'academy', 'institute', 'research', 'scholar']
            if any(keyword in domain for keyword in academic_keywords):
                return 3, "Academic domain (+3)"
            
            return 0, ""
        except Exception:  # pragma: no cover
            return 0, ""

    def _check_content_quality(self, summary: str) -> tuple[int, str]:
        """Check summary content quality."""
        if not summary:
            return -5, "Missing summary (-5)"  # Reduced from -10 to -5
        
        summary_lower = summary.lower()
        
        # Check for spam indicators
        spam_indicators = ['click here', 'buy now', 'limited time', 'act now']
        if any(indicator in summary_lower for indicator in spam_indicators):
            return -15, "Spam indicators detected (-15)"
        
        # Check for meaningful content (more lenient)
        meaningful_words = len([w for w in summary.split() if len(w) > 3])
        if meaningful_words < 5:  # Reduced from 10 to 5
            return -3, "Low content quality (-3)"  # Reduced from -5 to -3
        
        return 0, ""

    def calculate_source_score(self, source: ResearchSource) -> Dict[str, object]:
        """Compute an improved heuristic credibility score for a source."""

        score = 0
        factors: List[str] = []

        # 1. Source Type Scoring (improved)
        source_type = source.get("source_type", "")
        url = source.get("url", "")
        
        if source_type == "semantic_scholar":
            score += 28
            factors.append("Peer-reviewed (+28)")
        elif source_type == "arxiv":
            score += 25
            factors.append("arXiv preprint (+25)")
        else:
            # Web source with domain reputation check
            base_score = 18  # Increased from 12 to be more balanced
            domain_bonus, domain_reason = self._check_domain_reputation(url)
            score += base_score + domain_bonus
            factors.append(f"Web source (+{base_score})")
            if domain_reason:
                factors.append(domain_reason)

        # 2. Citation Scoring (improved with more granular levels)
        citations = source.get("citation_count", 0) or 0
        if citations >= 500:
            citation_score = 30
        elif citations >= 200:
            citation_score = 25
        elif citations >= 100:
            citation_score = 20
        elif citations >= 50:
            citation_score = 15
        elif citations >= 20:
            citation_score = 12
        elif citations >= 10:
            citation_score = 10
        elif citations >= 5:
            citation_score = 7
        elif citations >= 1:
            citation_score = 5
        else:
            # Give small bonus even for 0 citations (web sources often don't have citation counts)
            citation_score = 2 if source_type == "web" else 0
        score += citation_score
        factors.append(f"Citations: {citations} (+{citation_score})")

        # 3. Recency Scoring (improved - less penalty for older sources)
        published = source.get("published", "")
        has_published_date = False
        try:
            if published:
                year = int(str(published).split("-")[0])
                age = datetime.now().year - year
                has_published_date = True
                if age <= 1:
                    recency_score = 20
                elif age <= 2:
                    recency_score = 18
                elif age <= 3:
                    recency_score = 15
                elif age <= 5:
                    recency_score = 12
                elif age <= 10:
                    recency_score = 8
                else:
                    recency_score = 5  # Less penalty for older sources
                score += recency_score
                factors.append(f"Age: {age}y (+{recency_score})")
        except Exception:  # pragma: no cover - defensive
            pass
        
        # Penalty for missing published date (reduced penalty)
        if not has_published_date:
            score -= 2  # Reduced from -5 to -2
            factors.append("Missing published date (-2)")

        # 4. Author Information (new, with reduced penalty)
        authors = source.get("authors", [])
        if len(authors) >= 3:
            score += 5
            factors.append(f"Multiple authors ({len(authors)}) (+5)")
        elif len(authors) >= 1:
            score += 3
            factors.append(f"Has authors ({len(authors)}) (+3)")
        else:
            # Reduced penalty, especially for web sources where authors may not be available
            penalty = -2 if source_type == "web" else -3
            score += penalty
            factors.append(f"No authors ({penalty})")

        # 5. Summary Quality (improved - checks content quality, not just length)
        summary = source.get("summary", "")
        content_penalty, content_reason = self._check_content_quality(summary)
        score += content_penalty
        if content_reason:
            factors.append(content_reason)
        
        summary_length = len(summary)
        if summary_length > 300:
            score += 15
            factors.append("Comprehensive summary (+15)")
        elif summary_length > 200:
            score += 12
            factors.append("Substantial summary (+12)")
        elif summary_length > 100:
            score += 8
            factors.append("Moderate summary (+8)")
        elif summary_length > 50:
            score += 5
            factors.append("Brief summary (+5)")
        elif summary_length > 20:
            score += 2  # Small bonus for very brief summaries
            factors.append("Very brief summary (+2)")
        # Note: Missing summary penalty is already handled in _check_content_quality

        # 6. URL Validity Check (new, with reduced penalty)
        if not url or url.strip() == "":
            score -= 8  # Reduced from -15 to -8
            factors.append("Missing URL (-8)")
        elif not url.startswith(("http://", "https://")):
            score -= 3  # Reduced from -5 to -3
            factors.append("Invalid URL format (-3)")

        # Ensure score is within bounds
        final_score = max(0, min(score, 100))
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
        """Use the LLM to determine relevance of a source with improved prompt."""

        title = source.get('title', 'Unknown')
        summary = source.get('summary', '')[:500]  # Increased from 300
        authors = source.get('authors', [])
        source_type = source.get('source_type', 'unknown')
        
        authors_str = ', '.join(authors[:3]) if authors else "Unknown"
        if len(authors) > 3:
            authors_str += f" and {len(authors) - 3} more"

        prompt = f"""You are an expert research evaluator. Assess the relevance of this source to the research query.

RESEARCH QUERY: {query}

SOURCE INFORMATION:
- Title: {title}
- Authors: {authors_str}
- Source Type: {source_type}
- Summary: {summary}

EVALUATION CRITERIA:
1. Does the source directly address the query topic?
2. Does it provide relevant information, data, or insights?
3. Is it from a credible source type for this query?
4. Does the summary indicate meaningful content related to the query?

Be strict: Only mark as RELEVANT if the source clearly relates to the query topic.

Format your response EXACTLY as:
RELEVANT: [YES/NO]
CONFIDENCE: [HIGH/MEDIUM/LOW]
REASON: [One clear sentence explaining your decision]"""

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
        
        # Calculate dynamic threshold based on average scores
        preliminary_scores = []
        for source in raw_sources:
            score_result = self.calculate_source_score(source)
            preliminary_scores.append(score_result["score"])
        
        avg_preliminary = sum(preliminary_scores) / len(preliminary_scores) if preliminary_scores else 45
        # Dynamic threshold: at least 40 (reduced from 50), or 15 points below average (whichever is higher)
        # More lenient to allow more sources through while still maintaining quality
        dynamic_threshold = max(40, int(avg_preliminary - 15))
        logger.info("Using validation threshold: %d (avg preliminary score: %.1f)", dynamic_threshold, avg_preliminary)
        
        for idx, source in enumerate(raw_sources, start=1):
            score_result = self.calculate_source_score(source)
            relevance = self.check_relevance(source, query)

            # Improved acceptance criteria: higher threshold and relevance confidence check
            is_relevant = relevance["is_relevant"]
            confidence = relevance.get("confidence", "MEDIUM")
            score = score_result["score"]
            
            # Accept if: relevant AND (high confidence OR score >= threshold)
            # OR: medium confidence AND score >= threshold + 5
            should_accept = (
                is_relevant and (
                    confidence == "HIGH" or
                    score >= dynamic_threshold or
                    (confidence == "MEDIUM" and score >= dynamic_threshold + 5)
                )
            )

            if should_accept:
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
                logger.info(
                    "✓ Source %d accepted (%s, score: %.1f, confidence: %s)",
                    idx, score_result["grade"], score, confidence
                )
            else:
                rejection_reason = []
                if not is_relevant:
                    rejection_reason.append("not relevant")
                if score < dynamic_threshold:
                    rejection_reason.append(f"score too low ({score:.1f} < {dynamic_threshold})")
                if confidence == "LOW":
                    rejection_reason.append("low confidence")
                logger.info(
                    "✗ Source %d rejected (%s)",
                    idx, ", ".join(rejection_reason) if rejection_reason else "unknown reason"
                )

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
