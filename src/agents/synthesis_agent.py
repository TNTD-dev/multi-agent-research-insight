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
from src.config import ResearchDepthConfig
from src.utils.logger import default_logger as logger


class SynthesisAgent:
    """Agent responsible for synthesising research findings."""

    def __init__(self, llm, depth_config: ResearchDepthConfig | None = None):
        self.llm = llm
        self.depth_config = depth_config

    def extract_key_concepts(self, sources: List[ResearchSource], query: str = "") -> List[str]:
        """Identify key concepts across validated sources."""

        max_concepts = (
            self.depth_config.max_concepts
            if self.depth_config
            else 15
        )
        max_sources = min(10, len(sources))
        combined_text = "\n".join(
            f"{source.get('title', '')} {source.get('summary', '')[:200]}" for source in sources[:max_sources]
        )
        query_context = f" related to '{query}'" if query else ""
        prompt = (
            f"Extract {max_concepts} key technical concepts{query_context} from the following research snippets.\n"
            f"{'IMPORTANT: Only extract concepts that are directly relevant to the research topic. ' if query else ''}"
            f"{combined_text}\n"
            "Return ONLY a comma-separated list of concepts, without any introductory text or explanation."
        )

        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Remove common intro phrases that LLM might add
            intro_phrases = [
                "Here are",
                "The key concepts are",
                "Key concepts:",
                "Concepts:",
                "Here are the key concepts:",
                "Here are 15 key technical concepts extracted from the research snippets:",
                "Here are the technical concepts:",
            ]
            
            for phrase in intro_phrases:
                if content.lower().startswith(phrase.lower()):
                    # Find the colon after the phrase
                    colon_idx = content.find(":")
                    if colon_idx != -1:
                        content = content[colon_idx + 1:].strip()
                    else:
                        # If no colon, try to find where the list starts
                        words = phrase.split()
                        for word in words:
                            if word.lower() in content.lower():
                                idx = content.lower().find(word.lower())
                                content = content[idx + len(word):].strip()
                                if content.startswith(":"):
                                    content = content[1:].strip()
                    break
            
            # Split by comma and clean up
            concepts = []
            for concept in content.split(","):
                concept = concept.strip()
                # Remove any remaining intro text
                if concept and not any(phrase.lower() in concept.lower() for phrase in intro_phrases):
                    # Remove common prefixes
                    concept = concept.lstrip("- •*").strip()
                    if concept:
                        concepts.append(concept)
            
            max_concepts = (
                self.depth_config.max_concepts
                if self.depth_config
                else 15
            )
            logger.info("Synthesis: extracted %d concepts", len(concepts))
            return concepts[:max_concepts]
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Concept extraction failed: %s", exc)
            return []

    def find_consensus(self, sources: List[ResearchSource], query: str) -> List[str]:
        """Determine consensus findings across sources."""

        max_findings = (
            self.depth_config.max_consensus_findings
            if self.depth_config
            else 7
        )
        max_sources = min(8, len(sources))
        summaries = "\n\n".join(
            f"Source {i + 1}: {source.get('title', '')}\n{source.get('summary', '')[:300]}"
            for i, source in enumerate(sources[:max_sources])
        )
        prompt = (
            f"Identify consensus findings SPECIFICALLY about '{query}' from the following summaries.\n"
            f"IMPORTANT: Only include findings that are DIRECTLY related to '{query}'. "
            f"Exclude any information about unrelated topics (e.g., if query is about mental health, "
            f"do NOT include findings about financial data, unless they are specifically about mental health AND finance).\n\n"
            f"Summaries:\n{summaries}\n\n"
            f"List {max_findings} findings prefixed with '-'. Each finding must be directly relevant to '{query}'."
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

        max_gaps = (
            self.depth_config.max_research_gaps
            if self.depth_config
            else 5
        )
        prompt = (
            f"Given the following key concepts, identify {max_gaps} research gaps.\n"
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

        max_concepts = (
            self.depth_config.max_concepts
            if self.depth_config
            else 15
        )
        concept_ids = {}
        for concept in concepts[:max_concepts]:
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

        concepts = self.extract_key_concepts(sources, state.query)
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
