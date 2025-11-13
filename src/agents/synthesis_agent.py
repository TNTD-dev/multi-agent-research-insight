"""
Synthesis Agent - extracts insights, knowledge graphs, and gaps from validated sources.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from src.agents.state import (
    Contradiction,
    KnowledgeGraph,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    ResearchGap,
    ResearchSource,
    ResearchState,
)
from src.utils.logger import default_logger as logger


class SynthesisAgent:
    """Agent responsible for synthesising research findings."""

    def __init__(self, llm):
        self.llm = llm

    def extract_key_concepts(self, sources: List[ResearchSource]) -> List[str]:
        """Identify key concepts across validated sources."""

        combined_text = "\n".join(
            f"{source.get('title', '')} {source.get('summary', '')[:200]}" for source in sources[:10]
        )
        prompt = (
            "Extract 10-15 key technical concepts from the following research snippets.\n"
            f"{combined_text}\n"
            "Return a comma-separated list."
        )

        try:
            response = self.llm.invoke(prompt)
            concepts = [concept.strip() for concept in response.content.split(",") if concept.strip()]
            logger.info("Synthesis: extracted %d concepts", len(concepts))
            return concepts[:15]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Concept extraction failed: %s", exc)
            return []

    def find_consensus(self, sources: List[ResearchSource], query: str) -> List[str]:
        """Determine consensus findings across sources."""

        summaries = "\n\n".join(
            f"Source {i + 1}: {source.get('title', '')}\n{source.get('summary', '')[:300]}"
            for i, source in enumerate(sources[:8])
        )
        prompt = (
            f"Identify consensus findings about {query} from the following summaries:\n{summaries}\n"
            "List 5-7 findings prefixed with '-'."
        )

        try:
            response = self.llm.invoke(prompt)
            findings = [
                line.strip("- ").strip()
                for line in response.content.splitlines()
                if line.strip().startswith("-")
            ]
            logger.info("Synthesis: identified %d consensus findings", len(findings))
            return findings
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Consensus extraction failed: %s", exc)
            return []

    def detect_contradictions(self, sources: List[ResearchSource]) -> List[Contradiction]:
        """Detect contradictory evidence using simple heuristics."""

        positive_terms = {"improve", "enhance", "effective", "successful", "increase"}
        negative_terms = {"not", "no", "without", "fails", "decrease", "poor"}

        positive_sources: List[str] = []
        negative_sources: List[str] = []

        for source in sources:
            text = f"{source.get('title', '').lower()} {source.get('summary', '').lower()}"
            if any(term in text for term in positive_terms):
                positive_sources.append(source.get("title", ""))
            if any(term in text for term in negative_terms):
                negative_sources.append(source.get("title", ""))

        contradictions: List[Contradiction] = []
        if positive_sources and negative_sources:
            contradictions.append(
                Contradiction(
                    type="effectiveness_debate",
                    description=(
                        f"Mixed conclusions: {len(positive_sources)} positive vs "
                        f"{len(negative_sources)} negative assessments."
                    ),
                    severity="medium",
                    sources_positive=positive_sources[:3],
                    sources_negative=negative_sources[:3],
                )
            )
            logger.info("Synthesis: detected contradictions")

        return contradictions

    def identify_research_gaps(self, concepts: List[str]) -> List[ResearchGap]:
        """Generate research gap hypotheses using the LLM."""

        prompt = (
            "Given the following key concepts, identify 3-5 research gaps.\n"
            f"Concepts: {', '.join(concepts[:10])}\n"
            "Format each gap as:\nGAP: <name>\nWHY: <importance>\n---"
        )

        try:
            response = self.llm.invoke(prompt)
            gaps: List[ResearchGap] = []
            current: Dict[str, str] = {}

            for line in response.content.splitlines():
                line = line.strip()
                if line.startswith("GAP:"):
                    if current:
                        gaps.append(ResearchGap(**current))
                        current = {}
                    current["gap"] = line.replace("GAP:", "").strip()
                elif line.startswith("WHY:"):
                    current["importance"] = line.replace("WHY:", "").strip()
                elif line == "---" and current:
                    gaps.append(ResearchGap(**current))
                    current = {}

            if current:
                gaps.append(ResearchGap(**current))

            logger.info("Synthesis: identified %d research gaps", len(gaps))
            return gaps
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Gap identification failed: %s", exc)
            return []

    def build_knowledge_graph(self, sources: List[ResearchSource], concepts: List[str]) -> KnowledgeGraph:
        """Construct a simple knowledge graph from concepts and sources."""

        nodes: List[KnowledgeGraphNode] = []
        edges: List[KnowledgeGraphEdge] = []

        concept_ids = {}
        for concept in concepts[:15]:
            if len(concept.strip()) <= 2:
                continue
            concept_id = concept.lower().replace(" ", "_").replace("-", "_")
            concept_ids[concept_id] = concept
            nodes.append(
                KnowledgeGraphNode(id=concept_id, label=concept, type="concept")
            )

        for source in sources[:10]:
            nodes.append(
                KnowledgeGraphNode(
                    id=source.get("id", ""),
                    label=source.get("title", "")[:60],
                    type="source",
                    url=source.get("url", ""),
                )
            )

        for source in sources[:10]:
            text = f"{source.get('title', '').lower()} {source.get('summary', '').lower()}"
            added = False
            for concept_id, concept_label in concept_ids.items():
                words = concept_label.lower().split()
                if concept_label.lower() in text or any(
                    word in text for word in words if len(word) > 3
                ):
                    edges.append(
                        KnowledgeGraphEdge(
                            source=source.get("id", ""),
                            target=concept_id,
                            relation="discusses",
                        )
                    )
                    added = True
            if not added and concept_ids:
                first_concept = next(iter(concept_ids))
                edges.append(
                    KnowledgeGraphEdge(
                        source=source.get("id", ""),
                        target=first_concept,
                        relation="mentions",
                    )
                )

        cooccurrence: Dict[tuple[str, str], set[str]] = defaultdict(set)
        for source in sources[:10]:
            text = f"{source.get('title', '').lower()} {source.get('summary', '').lower()}"
            mentioned = [
                concept_id
                for concept_id, label in concept_ids.items()
                if label.lower() in text
            ]
            for i, c1 in enumerate(mentioned):
                for c2 in mentioned[i + 1 :]:
                    key = tuple(sorted((c1, c2)))
                    cooccurrence[key].add(source.get("id", ""))

        for (c1, c2), support in cooccurrence.items():
            if len(support) >= 2:
                edges.append(
                    KnowledgeGraphEdge(source=c1, target=c2, relation="related_to")
                )

        graph = KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            metadata={
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        )
        logger.info(
            "Synthesis: knowledge graph built with %d nodes and %d edges",
            len(nodes),
            len(edges),
        )
        return graph

    def synthesize(self, state: ResearchState) -> Dict[str, object]:
        """Run the full synthesis flow and return updates."""

        sources = state.validated_sources
        if not sources:
            logger.warning("Synthesis: no validated sources available.")
            return {
                "knowledge_graph": KnowledgeGraph(),
                "research_gaps": [],
                "consensus_findings": [],
                "contradictions": [],
                "key_concepts": [],
                "conflicts_detected": [],
            }

        concepts = self.extract_key_concepts(sources)
        consensus = self.find_consensus(sources, state.query)
        contradictions = self.detect_contradictions(sources)
        gaps = self.identify_research_gaps(concepts)
        knowledge_graph = self.build_knowledge_graph(sources, concepts)

        return {
            "key_concepts": concepts,
            "consensus_findings": consensus,
            "contradictions": contradictions,
            "research_gaps": gaps,
            "knowledge_graph": knowledge_graph,
            "conflicts_detected": contradictions,
        }
