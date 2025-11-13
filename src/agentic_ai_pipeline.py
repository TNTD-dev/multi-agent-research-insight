"""Main orchestration logic for the multi-agent research platform."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import networkx as nx

try:  # pragma: no cover - optional dependency
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - optional dependency
    plt = None

from src.agents import (
    DiscoveryAgent,
    MLAgent,
    MonitoringAgent,
    RAGAgent,
    ReporterAgent,
    SynthesisAgent,
    ValidationAgent,
)
from src.agents.state import KnowledgeGraph, ResearchState
from src.config import config
from src.utils.logger import default_logger as logger


def initialize_state(query: str, research_depth: str = "standard") -> ResearchState:
    """Create an initial application state."""

    return ResearchState(query=query, research_depth=research_depth)


def _build_agents(llm) -> Dict[str, object]:
    """Instantiate all specialised agents."""
        
    return {
        "discovery": DiscoveryAgent(llm, config),
        "validation": ValidationAgent(llm),
        "rag": RAGAgent(llm, config),
        "synthesis": SynthesisAgent(llm),
        "ml": MLAgent(llm, config),
        "reporter": ReporterAgent(llm),
        "monitoring": MonitoringAgent(llm),
    }


def _run_agent(state: ResearchState, name: str, handler) -> None:
    """Execute a single agent and merge its output into the state."""

    logger.info("Running %s agent", name)
    state.current_agent = name

    try:
        updates = handler(state) or {}
        if isinstance(updates, dict):
            state.update(updates)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("%s agent failed", name)
        state.errors.append(f"{name} agent error: {exc}")
        state.workflow_status = "failed"
        raise


def _execute_pipeline(state: ResearchState, agents: Dict[str, object]) -> ResearchState:
    """Run the sequential pipeline across all agents."""

    steps: List[Tuple[str, callable]] = [
        ("discovery", agents["discovery"].discover),
        ("validation", agents["validation"].validate),
        ("rag", agents["rag"].integrate),
        ("synthesis", agents["synthesis"].synthesize),
        ("ml", agents["ml"].analyze),
        ("reporter", agents["reporter"].report),
        ("monitoring", agents["monitoring"].monitor),
    ]

    for name, handler in steps:
        _run_agent(state, name, handler)

    state.workflow_status = "completed"
    state.completed_at = datetime.now().isoformat()
    state.current_agent = "complete"
    logger.info("Pipeline completed successfully")
    return state


def _save_detailed_report(state: ResearchState, query: str) -> Path:
    """Persist the detailed report to disk."""

    report_path = config.reports_dir / f"report_{hashlib.md5(query.encode()).hexdigest()[:8]}.txt"
    report_body = state.detailed_report or "No detailed report generated."

    header = (
        "=" * 80
        + "\nDETAILED RESEARCH REPORT\n"
        + "=" * 80
        + f"\nQuery: {state.query}\nGenerated: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
    )

    report_path.write_text(header + report_body, encoding="utf-8")
    logger.info("Detailed report saved to %s", report_path)
    return report_path


def _visualize_knowledge_graph(knowledge_graph: KnowledgeGraph | None, query: str) -> Path | None:
    """Render the knowledge graph to an image file if possible."""

    if not knowledge_graph or not knowledge_graph.nodes:
        logger.warning("Knowledge graph is empty; skipping visualisation")
        return None

    if plt is None:
        logger.warning("matplotlib not installed; skipping knowledge graph visualisation")
        return None

    graph = nx.Graph()
    for node in knowledge_graph.nodes:
        graph.add_node(node.id, label=node.label, type=node.type, url=node.url)
    for edge in knowledge_graph.edges:
        graph.add_edge(edge.source, edge.target, relation=edge.relation)

    if not graph.nodes:
        return None

    pos = nx.spring_layout(graph, seed=42)
    concept_nodes = [n for n, data in graph.nodes(data=True) if data.get("type") == "concept"]
    source_nodes = [n for n, data in graph.nodes(data=True) if data.get("type") == "source"]

    plt.figure(figsize=(18, 12))
    nx.draw_networkx_nodes(graph, pos, nodelist=concept_nodes, node_color="#4CAF50", node_size=1200, alpha=0.8)
    nx.draw_networkx_nodes(graph, pos, nodelist=source_nodes, node_color="#FF6B6B", node_size=900, alpha=0.7)
    nx.draw_networkx_edges(graph, pos, alpha=0.3)
    nx.draw_networkx_labels(graph, pos, {n: graph.nodes[n]["label"][:40] for n in graph.nodes()}, font_size=8)

    output_path = config.visualisations_dir / f"kg_{hashlib.md5(query.encode()).hexdigest()[:8]}.png"
    plt.title("Research Knowledge Graph", fontsize=18)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info("Knowledge graph visualisation saved to %s", output_path)
    return output_path


def _summarise_state(state: ResearchState) -> str:
    """Build a concise textual summary of the final state."""

    lines = [
        "=" * 80,
        "FINAL RESEARCH SUMMARY",
        "=" * 80,
        f"Query: {state.query}",
        f"Depth: {state.research_depth}",
        f"Sources discovered: {len(state.raw_sources)}",
        f"Sources validated: {len(state.validated_sources)}",
        f"Average quality score: {state.source_quality_avg:.1f}",
        f"Key concepts: {len(state.key_concepts)}",
        f"Consensus findings: {len(state.consensus_findings)}",
        f"Research gaps: {len(state.research_gaps)}",
        f"Contradictions: {len(state.contradictions)}",
        f"Monitoring triggers: {len(state.alert_triggers)}",
        f"Errors: {len(state.errors)}",
        "=" * 80,
    ]
    return "\n".join(lines)


def run_research_pipeline(query: str, research_depth: str = "standard") -> ResearchState:
    """Public entry point to execute the full research workflow."""

    logger.info("Starting research pipeline | query=%s | depth=%s", query, research_depth)

    llm = config.get_llm()
    state = initialize_state(query, research_depth)
    agents = _build_agents(llm)

    try:
        state = _execute_pipeline(state, agents)
    except Exception:  # already logged within _run_agent
        logger.error("Pipeline terminated early due to errors")
        return state
    
    summary = _summarise_state(state)
    logger.info("\n%s", summary)

    _save_detailed_report(state, query)
    _visualize_knowledge_graph(state.knowledge_graph, query)
    return state
    

def main() -> None:
    """Interactive CLI entry point."""

    print("\n" + "=" * 80)
    print("WELCOME TO THE MULTI-AGENT RESEARCH INTELLIGENCE PLATFORM")
    print("=" * 80)
    query = input("Enter your research question: ").strip()
    if not query:
        print("Query cannot be empty. Exiting.")
        return

    depth_choice = input("Choose depth [quick|standard|deep] (default: standard): ").strip().lower()
    if depth_choice not in {"quick", "standard", "deep"}:
        depth_choice = "standard"

    state = run_research_pipeline(query, depth_choice)
    if state.workflow_status == "completed":
        print("\nPipeline completed successfully. Check the reports directory for outputs.")
    else:
        print("\nPipeline finished with errors. See logs for details.")


if __name__ == "__main__":
    main()
