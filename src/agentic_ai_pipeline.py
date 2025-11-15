"""Main orchestration logic for the multi-agent research platform."""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, TypedDict, Any

import networkx as nx

try:  # pragma: no cover - optional dependency
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - optional dependency
    plt = None

from langgraph.graph import StateGraph, END

from src.agents import (
    DiscoveryAgent,
    ReporterAgent,
    SynthesisAgent,
    ValidationAgent,
)
from src.agents.state import KnowledgeGraph, ResearchState
from src.config import config, ResearchDepthConfig
from src.utils.logger import default_logger as logger


def initialize_state(query: str, research_depth: str = "standard") -> ResearchState:
    """Create an initial application state."""

    return ResearchState(query=query, research_depth=research_depth)


def _build_agents(llm, depth_config: ResearchDepthConfig | None = None) -> Dict[str, object]:
    """Instantiate all specialised agents."""
        
    return {
        "discovery": DiscoveryAgent(llm, config, depth_config),
        "validation": ValidationAgent(llm, depth_config),
        "synthesis": SynthesisAgent(llm, depth_config),
        "reporter": ReporterAgent(llm, depth_config),
    }


def _state_to_dict(state: ResearchState) -> Dict[str, Any]:
    """Convert ResearchState Pydantic model to dict for LangGraph compatibility."""
    # Use model_dump with mode="python" to get native Python types
    # This ensures nested Pydantic models are converted to dicts
    return state.model_dump(mode="python", exclude_none=False)


def _dict_to_state(state_dict: Dict[str, Any]) -> ResearchState:
    """Convert dict back to ResearchState Pydantic model."""
    # Pydantic will automatically reconstruct nested models from dicts
    # because of the type hints in ResearchState
    return ResearchState.model_validate(state_dict)


def _create_graph_nodes(agents: Dict[str, object]) -> Dict[str, callable]:
    """Create LangGraph node functions that wrap agent methods."""
    
    def discovery_node(state_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Discovery agent node."""
        logger.info("Running discovery agent")
        state = _dict_to_state(state_dict)
        state.current_agent = "discovery"
        
        try:
            updates = agents["discovery"].discover(state) or {}
            if isinstance(updates, dict):
                state.update(updates)
            return _state_to_dict(state)
        except Exception as exc:
            logger.exception("Discovery agent failed")
            state.errors.append(f"discovery agent error: {exc}")
            state.workflow_status = "failed"
            raise
    
    def validation_node(state_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validation agent node."""
        logger.info("Running validation agent")
        state = _dict_to_state(state_dict)
        state.current_agent = "validation"
        
        try:
            updates = agents["validation"].validate(state) or {}
            if isinstance(updates, dict):
                state.update(updates)
            return _state_to_dict(state)
        except Exception as exc:
            logger.exception("Validation agent failed")
            state.errors.append(f"validation agent error: {exc}")
            state.workflow_status = "failed"
            raise
    
    def synthesis_node(state_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesis agent node."""
        logger.info("Running synthesis agent")
        state = _dict_to_state(state_dict)
        state.current_agent = "synthesis"
        
        try:
            updates = agents["synthesis"].synthesize(state) or {}
            if isinstance(updates, dict):
                state.update(updates)
            return _state_to_dict(state)
        except Exception as exc:
            logger.exception("Synthesis agent failed")
            state.errors.append(f"synthesis agent error: {exc}")
            state.workflow_status = "failed"
            raise
    
    def reporter_node(state_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Reporter agent node."""
        logger.info("Running reporter agent")
        state = _dict_to_state(state_dict)
        state.current_agent = "reporter"
        
        try:
            updates = agents["reporter"].report(state) or {}
            if isinstance(updates, dict):
                state.update(updates)
            state.workflow_status = "completed"
            state.completed_at = datetime.now().isoformat()
            state.current_agent = "complete"
            logger.info("Pipeline completed successfully")
            return _state_to_dict(state)
        except Exception as exc:
            logger.exception("Reporter agent failed")
            state.errors.append(f"reporter agent error: {exc}")
            state.workflow_status = "failed"
            raise
    
    return {
        "discovery": discovery_node,
        "validation": validation_node,
        "synthesis": synthesis_node,
        "reporter": reporter_node,
    }


def _build_research_graph(agents: Dict[str, object]) -> Any:
    """Build and compile the LangGraph state machine for research pipeline.
    
    Returns:
        Compiled LangGraph that can be invoked with state dict.
    """
    
    # Define state schema as TypedDict for LangGraph
    class ResearchStateDict(TypedDict):
        """State schema for LangGraph - mirrors ResearchState fields."""
        query: str
        research_depth: str
        user_id: str | None
        raw_sources: List[Dict[str, Any]]
        discovery_metadata: Dict[str, Any]
        validated_sources: List[Dict[str, Any]]
        validation_scores: List[Dict[str, Any]]
        credibility_report: Dict[str, Any] | None
        knowledge_graph: Dict[str, Any] | None
        research_gaps: List[Dict[str, Any]]
        consensus_findings: List[str]
        contradictions: List[Dict[str, Any]]
        key_concepts: List[str]
        executive_summary: str
        detailed_report: str
        citation_map: Dict[str, Any] | None
        visualizations: List[Dict[str, Any]]
        source_quality_avg: float
        citation_counts: Dict[str, Any]
        conflicts_detected: List[Dict[str, Any]]
        current_agent: str
        workflow_status: str
        errors: List[str]
        synthesis_ready: bool
        started_at: str
        completed_at: str
    
    # Create graph
    graph = StateGraph(ResearchStateDict)
    
    # Create node functions
    nodes = _create_graph_nodes(agents)
    
    # Add nodes to graph
    graph.add_node("discovery", nodes["discovery"])
    graph.add_node("validation", nodes["validation"])
    graph.add_node("synthesis", nodes["synthesis"])
    graph.add_node("reporter", nodes["reporter"])
    
    # Define sequential edges
    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "validation")
    graph.add_edge("validation", "synthesis")
    graph.add_edge("synthesis", "reporter")
    graph.add_edge("reporter", END)
    
    # Compile graph and return compiled version
    return graph.compile()


def _execute_pipeline(state: ResearchState, agents: Dict[str, object]) -> ResearchState:
    """Run the sequential pipeline across all agents using LangGraph."""

    # Build and compile the graph
    compiled_graph = _build_research_graph(agents)
    
    # Convert state to dict for LangGraph
    state_dict = _state_to_dict(state)
    
    # Execute the graph
    try:
        final_state_dict = compiled_graph.invoke(state_dict)
        # Convert back to ResearchState
        return _dict_to_state(final_state_dict)
    except Exception as exc:
        logger.exception("Pipeline execution failed")
        state.workflow_status = "failed"
        state.errors.append(f"Pipeline execution error: {exc}")
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
        f"Errors: {len(state.errors)}",
        "=" * 80,
    ]
    return "\n".join(lines)


def run_research_pipeline(query: str, research_depth: str = "standard") -> ResearchState:
    """Public entry point to execute the full research workflow."""

    logger.info("Starting research pipeline | query=%s | depth=%s", query, research_depth)

    llm = config.get_llm()
    state = initialize_state(query, research_depth)
    
    # Create depth configuration
    depth_config = ResearchDepthConfig.get_depth_config(research_depth)
    logger.info("Depth config: arxiv=%d, web=%d, scholar=%d, validation_min=%d",
                depth_config.max_arxiv_results,
                depth_config.max_web_results,
                depth_config.max_semantic_scholar_results,
                depth_config.validation_min_score)
    
    agents = _build_agents(llm, depth_config)

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
