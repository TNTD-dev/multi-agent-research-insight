"""
Discovery Agent - responsible for gathering initial research material.
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List

import arxiv
import requests

try:
    from tavily import TavilyClient  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    TavilyClient = None

from src.agents.state import ResearchSource, ResearchState
from src.config import ResearchConfig
from src.utils.logger import default_logger as logger


class DiscoveryAgent:
    """Autonomous agent orchestrating multi-source discovery."""

    def __init__(self, llm, config: ResearchConfig):
        self.llm = llm
        self.config = config
        self.sources_searched: List[str] = []

    def _log_phase(self, message: str) -> None:
        logger.info("[Discovery] %s", message)

    def search_arxiv(self, query: str, max_results: int | None = None) -> List[ResearchSource]:
        """Search arXiv for relevant publications."""

        max_results = max_results or self.config.search.max_arxiv_results

        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            results: List[ResearchSource] = []
            for paper in search.results():
                arxiv_id = paper.entry_id.split("/")[-1]
                # Ensure URL is always available: use pdf_url, entry_id, or construct from arxiv_id
                url = paper.pdf_url or paper.entry_id or f"https://arxiv.org/abs/{arxiv_id}"
                
                results.append(
                    ResearchSource(
                        id=f"arxiv_{arxiv_id}",
                        title=paper.title or "",
                        authors=[author.name for author in paper.authors],
                        summary=paper.summary or "",
                        full_text=paper.summary or "",
                        url=url,
                        published=paper.published.strftime("%Y-%m-%d") if paper.published else "",
                        categories=list(paper.categories),
                        source_type="arxiv",
                        metadata={
                            "arxiv_id": arxiv_id,
                            "primary_category": paper.primary_category,
                        },
                    )
                )

            self.sources_searched.append("arxiv")
            logger.info("arXiv: %d papers retrieved", len(results))
            return results
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("arXiv search failed: %s", exc)
            return []

    def search_web(self, query: str, num_results: int | None = None) -> List[ResearchSource]:
        """Search general web sources using Tavily API."""

        num_results = num_results or self.config.search.max_web_results

        try:
            if TavilyClient is None:
                logger.warning("tavily package not installed; skipping web search.")
                return []

            if not self.config.search.tavily_key:
                logger.warning("TAVILY_KEY not configured; skipping web search.")
                return []

            client = TavilyClient(api_key=self.config.search.tavily_key)
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=num_results,
            )

            results = response.get("results", [])
            formatted: List[ResearchSource] = []

            for idx, result in enumerate(results):
                url = result.get("url", "")
                # Web search should always have a link, but ensure it's not empty
                if not url:
                    logger.warning("Web search result missing URL, skipping: %s", result.get("title", "Unknown"))
                    continue
                    
                formatted.append(
                    ResearchSource(
                        id=f"web_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                        title=result.get("title", "No title"),
                        summary=result.get("content", ""),
                        full_text=result.get("content", ""),
                        url=url,
                        source_type="web",
                        metadata={
                            "position": idx + 1,
                            "score": result.get("score"),
                        },
                    )
                )

            self.sources_searched.append("web")
            logger.info("Web search: %d results", len(formatted))
            return formatted
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Web search failed: %s", exc)
            return []

    def search_semantic_scholar(self, query: str, limit: int | None = None) -> List[ResearchSource]:
        """Search publications from Semantic Scholar."""

        limit = limit or self.config.search.max_semantic_scholar_results

        try:
            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={
                    "query": query,
                    "limit": limit,
                    "fields": "title,authors,abstract,year,citationCount,url,venue,publicationDate,paperId",
                },
                timeout=self.config.search.semantic_scholar_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Semantic Scholar request failed: %s", exc)
            return []

        data = response.json()
        papers = data.get("data", [])
        results: List[ResearchSource] = []

        for paper in papers:
            paper_id = hashlib.md5(paper.get("title", "").encode()).hexdigest()[:8]
            published = paper.get("publicationDate") or paper.get("year")
            # Ensure URL is always available: use provided URL or construct from paperId if available
            paper_url = paper.get("url") or ""
            if not paper_url and paper.get("paperId"):
                # Construct Semantic Scholar URL from paper ID
                paper_url = f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"
            
            results.append(
                ResearchSource(
                    id=f"scholar_{paper_id}",
                    title=paper.get("title", "Unknown"),
                    authors=[author.get("name", "Unknown") for author in paper.get("authors", [])],
                    summary=(paper.get("abstract") or "")[:500],
                    full_text=paper.get("abstract", "") or "",
                    url=paper_url,
                    published=str(published or ""),
                    citation_count=paper.get("citationCount", 0) or 0,
                    source_type="semantic_scholar",
                    metadata={
                        "venue": paper.get("venue", "Unknown"),
                        "citations": paper.get("citationCount", 0),
                        "paperId": paper.get("paperId", ""),
                    },
                )
            )

        self.sources_searched.append("semantic_scholar")
        logger.info("Semantic Scholar: %d papers", len(results))
        return results

    def reformulate_query(self, query: str) -> List[str]:
        """Generate alternative search queries with the backing LLM."""

        prompt = (
            f'Generate 2 alternative search queries for "{query}".\n'
            "Keep the meaning but change wording. One query per line."
        )

        try:
            response = self.llm.invoke(prompt)
            alternatives = [line.strip() for line in response.content.splitlines() if line.strip()]
            return alternatives[:2]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Query reformulation failed: %s", exc)
            return []

    @staticmethod
    def deduplicate_sources(sources: List[ResearchSource]) -> List[ResearchSource]:
        """Deduplicate sources based on normalised titles."""

        unique: Dict[str, ResearchSource] = {}
        for source in sources:
            title_key = re.sub(r"[^\w\s]", "", source.title.lower()).strip()[:80]
            if title_key and title_key not in unique:
                unique[title_key] = source
        return list(unique.values())

    def discover(self, state: ResearchState) -> Dict[str, object]:
        """Execute the discovery pipeline and return updates to the state."""

        self._log_phase("Starting discovery workflow")
        query = state.query
        depth = state.research_depth

        sources: List[ResearchSource] = []
        sources.extend(self.search_arxiv(query))
        sources.extend(self.search_web(query))
        sources.extend(self.search_semantic_scholar(query))

        if depth in {"standard", "deep"} and len(sources) < 15:
            self._log_phase("Running reformulated searches")
            for alt_query in self.reformulate_query(query):
                self._log_phase(f"Alternative query: {alt_query}")
                sources.extend(self.search_arxiv(alt_query, max_results=3))
                sources.extend(self.search_semantic_scholar(alt_query, limit=3))

        unique_sources = self.deduplicate_sources(sources)
        self._log_phase(f"Discovery complete: {len(unique_sources)} unique sources")

        return {
            "raw_sources": unique_sources,
            "discovery_metadata": {
                "total_found": len(sources),
                "unique_sources": len(unique_sources),
                "sources_searched": sorted(set(self.sources_searched)),
                "timestamp": state.started_at,
            },
        }
